"""campus-qwen adapter for Elderly Safety.

Default tests use a patched HTTP layer (no network, fake key) and check the
request content for privacy, parsing, and the domain's fallback when the
model fails. One live test runs only when explicitly enabled:

    $env:ELEC5620_API_KEY = "<your key>"         # on campus network / USYD VPN
    $env:ELEC5620_RUN_REAL_PROXY = "1"
    python -m unittest tests.test_elderly_llm -v
"""

from __future__ import annotations

import json
import os
import unittest
from io import BytesIO
from unittest.mock import patch

from domains.elderly_safety import ElderlySafetyHandler, assess_fall, default_devices
from domains.elderly_safety.confirmation import interpret
from domains.elderly_safety.context import collect_context
from domains.elderly_safety.integration import build_workflow, resume_elderly_safety, run_elderly_safety
from services.campus_proxy import CampusProxyConfig
from services.elderly_llm import campus_providers, interpret_resident_reply, propose_fall_risk
from simulation.devices import SimulatedDeviceTool
from simulation.elderly_scenarios import make_fall_scenario

FAKE = CampusProxyConfig(api_key="fake-test-key", base_url="http://proxy.invalid/v1", model="campus-qwen")


def reply_with(content: str):
    body = json.dumps({"choices": [{"message": {"content": content}}]}).encode("utf-8")

    class Response(BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    return Response(body)


class AdapterTests(unittest.TestCase):
    def test_fall_request_is_de_identified_and_parsed(self):
        event = make_fall_scenario("high_floor")
        event.context.update({"resident_name": "A. Person", "address": "1 Example St", "caregiver_phone": "0400000000"})
        view = collect_context(event).for_llm()
        with patch("services.elderly_llm.urlopen", return_value=reply_with('{"risk_level": "HIGH", "rationale": "on the floor"}')) as call:
            proposal = propose_fall_risk(view, FAKE)
        self.assertEqual(proposal, {"risk_level": "HIGH", "rationale": "on the floor"})
        request = call.call_args.args[0]
        body = request.data.decode("utf-8")
        for private in ("A. Person", "Example St", "0400000000", event.event_id, "fake-test-key"):
            self.assertNotIn(private, body)
        self.assertEqual(request.get_header("Authorization"), "Bearer fake-test-key")
        self.assertTrue(request.full_url.endswith("/chat/completions"))
        sent = json.loads(json.loads(body)["messages"][1]["content"])
        self.assertEqual(sent["room_category"], "bathroom")

    def test_reply_request_contains_only_reply_and_attempt(self):
        with patch("services.elderly_llm.urlopen", return_value=reply_with('{"verdict": "safe", "rationale": "ok"}')) as call:
            out = interpret_resident_reply({"reply": "I'm fine", "attempt": 1, "event_id": "leak"}, FAKE)
        self.assertEqual(out["verdict"], "safe")
        sent = json.loads(json.loads(call.call_args.args[0].data)["messages"][1]["content"])
        self.assertEqual(sent, {"reply": "I'm fine", "attempt": 1})

    def test_markdown_fenced_json_is_accepted(self):
        with patch("services.elderly_llm.urlopen", return_value=reply_with('```json\n{"verdict": "help", "rationale": "pain"}\n```')):
            self.assertEqual(interpret_resident_reply({"reply": "my hip", "attempt": 1}, FAKE)["verdict"], "help")

    def test_non_json_reply_raises_for_the_domain_to_fall_back(self):
        with patch("services.elderly_llm.urlopen", return_value=reply_with("I think they are fine")):
            with self.assertRaises(ValueError):
                propose_fall_risk({}, FAKE)

    def test_campus_providers_require_a_key(self):
        with patch.dict(os.environ, {"ELEC5620_API_KEY": ""}):
            with self.assertRaises(ValueError):
                campus_providers()


class DomainWithModelTests(unittest.TestCase):
    def test_model_confirms_fall_level(self):
        with patch("services.elderly_llm.urlopen", return_value=reply_with('{"risk_level": "MEDIUM", "rationale": "brief stillness"}')):
            fall_provider, _ = campus_providers(FAKE)
            a = assess_fall(make_fall_scenario("medium_wait"), fall_provider)
        self.assertEqual((a.risk_level, a.evidence_source, a.fallback_used), ("MEDIUM", "llm_confirmed", False))

    def test_model_cannot_lower_high(self):
        with patch("services.elderly_llm.urlopen", return_value=reply_with('{"risk_level": "LOW", "rationale": "fine"}')):
            fall_provider, _ = campus_providers(FAKE)
            a = assess_fall(make_fall_scenario("high_floor"), fall_provider)
        self.assertEqual(a.risk_level, "HIGH")
        self.assertTrue(a.policy_override)

    def test_network_timeout_uses_medium_fallback(self):
        with patch("services.elderly_llm.urlopen", side_effect=TimeoutError("proxy timeout")):
            fall_provider, _ = campus_providers(FAKE)
            a = assess_fall(make_fall_scenario("low_dropped_object"), fall_provider)
        self.assertEqual((a.risk_level, a.evidence_source, a.fallback_used), ("MEDIUM", "llm_fallback", True))

    def test_model_reply_interpretation_through_workflow(self):
        with patch("services.elderly_llm.urlopen", return_value=reply_with('{"verdict": "safe", "rationale": "reassured"}')):
            _, interpreter = campus_providers(FAKE)
            r = interpret(make_fall_scenario("medium_wait"), 1, "all good, just resting", interpreter)
        self.assertEqual((r.verdict, r.interpreted_by), ("safe", "llm"))

    def test_model_cannot_turn_help_into_safe(self):
        with patch("services.elderly_llm.urlopen", return_value=reply_with('{"verdict": "safe", "rationale": "x"}')):
            _, interpreter = campus_providers(FAKE)
            r = interpret(make_fall_scenario("medium_wait"), 1, "help I can't get up", interpreter)
        self.assertEqual(r.verdict, "help")


@unittest.skipUnless(
    os.getenv("ELEC5620_RUN_REAL_PROXY") == "1" and os.getenv("ELEC5620_API_KEY", "").strip(),
    "live campus proxy test; set ELEC5620_RUN_REAL_PROXY=1 and ELEC5620_API_KEY on the campus network / VPN",
)
class LiveCampusProxyTests(unittest.TestCase):
    """Records what the real model did; rules still decide. Never prints the key."""

    def test_live_fall_and_reply(self):
        fall_provider, interpreter = campus_providers()
        workflow, handler = build_workflow(device_tool=SimulatedDeviceTool(default_devices()),
                                           proposal_provider=fall_provider, reply_interpreter=interpreter)
        result = run_elderly_safety(make_fall_scenario("medium_wait"), workflow=workflow, handler=handler, record_path=None)
        fall = handler.fall_assessment
        print(f"\nlive fall: {fall.risk_level} source={fall.evidence_source} model={fall.model_rationale!r}")
        self.assertIn(fall.evidence_source, ("llm_confirmed", "llm_fallback"))
        if result.pending_confirmation is not None:
            done = resume_elderly_safety(result, "I'm okay, I just sat down to rest", workflow=workflow, handler=handler, record_path=None)
            reply = done.confirmation_replies[-1]
            print(f"live reply: {reply.verdict} by {reply.interpreted_by}")
            self.assertIn(reply.verdict, ("safe", "unclear"))


if __name__ == "__main__":
    unittest.main()
