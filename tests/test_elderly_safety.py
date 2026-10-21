"""Elderly Safety Core 1 domain tests (SCRUM-12, AR-01 / UC-01). No langgraph needed.

Covers: UC-01 context, rule levels, LLM proposal validation (confirm / raise /
overridden / invalid / exception), MEDIUM fallback, de-identified model input
(NFR-03), timing (NFR-02), handler decision mapping, fixtures.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from domains.elderly_safety import ElderlySafetyHandler, assess_fall
from domains.elderly_safety.context import collect_context
from domains.elderly_safety.handler import light_for
from domains.elderly_safety.policy import apply_llm_fallback, apply_policy_floor
from domains.elderly_safety.rules import HIGH_INACTIVITY_S, MEDIUM_INACTIVITY_S, assess_by_rules
from models import Event, SensorReading
from simulation.elderly_scenarios import SCENARIOS, make_fall_scenario

SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"


class PolicyTests(unittest.TestCase):
    def test_policy_floor(self):
        self.assertEqual(apply_policy_floor("HIGH", None), ("HIGH", False))
        self.assertEqual(apply_policy_floor("HIGH", "LOW"), ("HIGH", True))
        self.assertEqual(apply_policy_floor("LOW", "HIGH"), ("HIGH", False))
        self.assertEqual(apply_policy_floor("MEDIUM", "MEDIUM"), ("MEDIUM", False))
        self.assertEqual(apply_policy_floor("MEDIUM", "SEVERE"), ("MEDIUM", False))

    def test_llm_fallback_is_medium_floor(self):
        self.assertEqual(apply_llm_fallback("LOW"), "MEDIUM")
        self.assertEqual(apply_llm_fallback("MEDIUM"), "MEDIUM")
        self.assertEqual(apply_llm_fallback("HIGH"), "HIGH")


class ContextTests(unittest.TestCase):
    def test_collects_uc01_context_and_flags_missing(self):
        ctx = collect_context(make_fall_scenario("medium_missing_duration"))
        self.assertTrue(ctx.impact_detected)
        self.assertIsNone(ctx.seconds_without_motion)
        self.assertEqual((ctx.location, ctx.home_mode, ctx.recent_activity, ctx.time_of_day), ("bedroom", "home", "walking", "day"))
        self.assertIn("seconds_without_motion", ctx.missing)

    def test_llm_view_is_de_identified(self):
        event = make_fall_scenario("high_floor")
        event.context.update({"resident_name": "A. Person", "address": "1 Example St", "caregiver_phone": "0400000000"})
        view = collect_context(event).for_llm()
        text = json.dumps(view)
        for private in ("A. Person", "Example St", "0400000000", event.event_id):
            self.assertNotIn(private, text)
        self.assertEqual(view["room_category"], "bathroom")
        self.assertEqual(set(view), {"impact_detected", "seconds_without_motion", "posture", "room_category", "time_of_day", "home_mode", "recent_activity"})


class RuleTests(unittest.TestCase):
    def test_scenarios_match_expected_levels(self):
        for name, (*_, expected) in SCENARIOS.items():
            with self.subTest(name):
                self.assertEqual(assess_by_rules(collect_context(make_fall_scenario(name))).risk_level, expected)

    def test_thresholds_ordered(self):
        self.assertLess(MEDIUM_INACTIVITY_S, HIGH_INACTIVITY_S)

    def test_upright_is_low_even_at_night(self):
        event = make_fall_scenario("low_dropped_object", observed_at="2026-10-20T03:00:00+00:00")
        self.assertEqual(assess_by_rules(collect_context(event)).risk_level, "LOW")

    def test_floor_posture_with_short_inactivity_is_high(self):
        event = make_fall_scenario("medium_wait")
        event.context["posture"] = "floor"
        self.assertEqual(assess_by_rules(collect_context(event)).risk_level, "HIGH")


class ProposalTests(unittest.TestCase):
    def test_no_provider_uses_medium_fallback_and_says_so(self):
        a = assess_fall(make_fall_scenario("low_dropped_object"))
        self.assertEqual((a.risk_level, a.evidence_source, a.fallback_used), ("MEDIUM", "llm_fallback", True))
        self.assertIn("fallback", a.rationale.lower())
        self.assertGreaterEqual(a.classification_ms, 0.0)

    def test_fallback_keeps_high(self):
        a = assess_fall(make_fall_scenario("high_floor"))
        self.assertEqual(a.risk_level, "HIGH")
        self.assertTrue(a.fallback_used)

    def test_valid_matching_proposal_is_confirmed(self):
        a = assess_fall(make_fall_scenario("medium_wait"), lambda v: {"risk_level": "MEDIUM", "rationale": "brief inactivity after impact"})
        self.assertEqual((a.risk_level, a.evidence_source, a.fallback_used), ("MEDIUM", "llm_confirmed", False))
        self.assertEqual(a.model_rationale, "brief inactivity after impact")

    def test_lower_proposal_is_overridden(self):
        a = assess_fall(make_fall_scenario("high_floor"), lambda v: {"risk_level": "LOW", "rationale": "probably fine"})
        self.assertEqual(a.risk_level, "HIGH")
        self.assertTrue(a.policy_override)

    def test_higher_proposal_is_accepted(self):
        a = assess_fall(make_fall_scenario("medium_wait"), lambda v: {"risk_level": "HIGH", "rationale": "no response pattern"})
        self.assertEqual(a.risk_level, "HIGH")
        self.assertFalse(a.policy_override)

    def test_invalid_or_failing_provider_falls_back(self):
        def explode(v):
            raise TimeoutError("campus proxy timeout")
        for provider in (lambda v: {"risk_level": "SEVERE", "rationale": "x"}, lambda v: "not json", explode):
            with self.subTest(provider):
                a = assess_fall(make_fall_scenario("low_dropped_object"), provider)
                self.assertEqual(a.risk_level, "MEDIUM")
                self.assertTrue(a.fallback_used)

    def test_provider_receives_only_de_identified_view(self):
        seen = {}
        assess_fall(make_fall_scenario("high_floor"), lambda v: seen.update(v) or {"risk_level": "HIGH", "rationale": "ok"})
        self.assertNotIn("event_id", seen)
        self.assertNotIn("room", seen)
        self.assertEqual(seen["room_category"], "bathroom")


class HandlerTests(unittest.TestCase):
    def test_supports_only_fall_events(self):
        h = ElderlySafetyHandler()
        self.assertTrue(h.supports(make_fall_scenario("high_floor")))
        pet = Event("e1", "pet_bowl_level", "s", "2026-10-20T10:00:00+00:00", simulated=True)
        self.assertFalse(h.supports(pet))

    def test_high_plans_light_and_caregiver_notification(self):
        h = ElderlySafetyHandler()
        event = make_fall_scenario("high_floor")
        d = h.assess(event)
        self.assertEqual(d.assessment.risk_level, "HIGH")
        self.assertFalse(d.assessment.requires_human_review)
        self.assertEqual(len(d.actions), 1)
        a = d.actions[0]
        self.assertEqual((a.device_id, a.action, a.parameters, a.expected_state, a.authorization, a.simulated),
                         ("bathroom_light", "set_state", {"power": "on"}, {"power": "on"}, "POLICY", True))
        self.assertIsNotNone(d.notification_request)
        self.assertNotIn("light", d.notification_request.message.lower())  # no claim before readback
        self.assertEqual(d.notification_request.event_id, event.event_id)

    def test_medium_asks_resident_blocks_dispatch_no_notification(self):
        d = ElderlySafetyHandler().assess(make_fall_scenario("medium_wait"))
        self.assertEqual(d.assessment.risk_level, "MEDIUM")
        self.assertTrue(d.assessment.requires_human_review)
        self.assertEqual(d.actions, ())
        self.assertIsNone(d.notification_request)

    def test_shared_assessment_carries_evidence_source(self):
        h = ElderlySafetyHandler()
        d = h.assess(make_fall_scenario("high_floor"))
        self.assertIn("[llm_fallback]", d.assessment.evidence)
        self.assertEqual(h.fall_assessment.evidence_source, "llm_fallback")

    def test_light_for_room(self):
        self.assertEqual(light_for(make_fall_scenario("high_floor")), "bathroom_light")
        self.assertEqual(light_for(make_fall_scenario("medium_wait")), "living_light")
        event = make_fall_scenario("high_floor")
        event.context["room"] = "garage"
        self.assertEqual(light_for(event), "hall_light")


class SampleDataTests(unittest.TestCase):
    def test_fixtures_are_labelled_and_match_rules(self):
        files = sorted(SAMPLES.glob("elderly_fall_*.json"))
        self.assertGreaterEqual(len(files), 3)
        for path in files:
            with self.subTest(path.name):
                doc = json.loads(path.read_text(encoding="utf-8"))
                self.assertTrue(doc["simulated"] and doc["event"]["simulated"])
                self.assertEqual(doc["domain"], "elderly_safety")
                ev = doc["event"]
                event = Event(**{**ev, "readings": tuple(SensorReading(**r) for r in ev["readings"])})
                self.assertEqual(assess_by_rules(collect_context(event)).risk_level, doc["expected"]["rule_level"])
                self.assertEqual(assess_fall(event).risk_level, doc["expected"]["level_without_model"])


if __name__ == "__main__":
    unittest.main()
