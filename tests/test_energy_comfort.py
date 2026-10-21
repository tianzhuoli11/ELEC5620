"""Shared context and Energy & Comfort Stage 1 behavior tests."""

from __future__ import annotations

from dataclasses import replace
import unittest

from agents.graph import SmartHomeWorkflow
from domains.energy_comfort.integration import (
    EnergyComfortHandler, context_from_event, monitor_energy_comfort_workflow,
)
from domains.energy_comfort.monitoring import assess_energy_comfort
from models import (
    DeviceObservation, EnergyProfile, HomeContext, HomeEnvironment, HomeMode, SensorReading,
    UserPreference,
)
from simulation.energy_comfort_demo import make_energy_comfort_event


class FailingDeviceTool:
    """Any call proves that the assessment-only boundary was violated."""

    def dispatch(self, request):
        raise AssertionError("dispatch must not be called")

    def read_state(self, device_id):
        raise AssertionError("read_state must not be called")


def home_context(
    temperature=22.0, occupied=True, preference=(20.0, 24.0),
    energy=None, devices=(), mode=HomeMode.HOME,
):
    preferred = None if preference is None else UserPreference(*preference)
    return HomeContext(
        HomeEnvironment(temperature, occupied), preferred, energy, mode,
        tuple(devices), True,
    )


class SharedContextTests(unittest.TestCase):
    def test_unknown_occupancy_is_distinct_from_unoccupied(self) -> None:
        unknown = HomeEnvironment(22.0, None)
        unoccupied = HomeEnvironment(22.0, False)
        self.assertIsNone(unknown.occupied)
        self.assertIs(unoccupied.occupied, False)

    def test_invalid_numeric_values_and_reversed_preference_are_rejected(self) -> None:
        for value in (True, float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                HomeEnvironment(value, True)
        with self.assertRaisesRegex(ValueError, "must not exceed"):
            UserPreference(25.0, 20.0)
        with self.assertRaises(ValueError):
            EnergyProfile(current_power_w=True)

    def test_event_round_trip_is_a_shared_context_consumer_example(self) -> None:
        original = home_context(
            21.5, False, (19.0, 23.0), EnergyProfile(350.0, 400.0),
            (DeviceObservation("heater-1", None, {"power": "off"}),), HomeMode.AWAY,
        )
        event = make_energy_comfort_event(original)
        restored = context_from_event(event)
        self.assertEqual(restored, original)
        self.assertTrue(event.simulated)
        self.assertEqual(len(event.readings), 2)
        self.assertNotIn("environment", event.context["energy_comfort"])

    def test_duplicate_environment_source_is_rejected(self) -> None:
        event = make_energy_comfort_event(home_context())
        event.context["energy_comfort"]["temperature_c"] = 18.0
        with self.assertRaisesRegex(ValueError, "only in event readings"):
            context_from_event(event)

    def test_simulation_marker_must_match_event(self) -> None:
        event = make_energy_comfort_event(home_context())
        event.context["energy_comfort"]["simulated"] = False
        with self.assertRaisesRegex(ValueError, "simulation marker"):
            context_from_event(event)

    def test_event_parser_rejects_invalid_types_units_and_duplicate_readings(self) -> None:
        event = make_energy_comfort_event(home_context())
        timestamp = event.timestamp
        invalid_cases = {
            "string occupancy": (
                SensorReading("occupancy", "occupancy", "false", "boolean", timestamp),
            ),
            "boolean temperature": (
                SensorReading("temperature", "indoor_temperature", True, "C", timestamp),
            ),
            "wrong temperature unit": (
                SensorReading("temperature", "indoor_temperature", 72.0, "F", timestamp),
            ),
            "duplicate temperature": (
                SensorReading("temperature-1", "indoor_temperature", 21.0, "C", timestamp),
                SensorReading("temperature-2", "indoor_temperature", 22.0, "C", timestamp),
            ),
        }
        for name, readings in invalid_cases.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                SmartHomeWorkflow([EnergyComfortHandler()], FailingDeviceTool()).run(
                    replace(event, readings=readings)
                )

        invalid_available = make_energy_comfort_event(home_context())
        invalid_available.context["energy_comfort"]["devices"] = [{
            "device_id": "heater-1", "available": "unknown", "observed_state": {"power": "on"},
        }]
        with self.assertRaisesRegex(ValueError, "available"):
            SmartHomeWorkflow([EnergyComfortHandler()], FailingDeviceTool()).run(invalid_available)

    def test_sensor_reading_rejects_non_finite_values_before_domain_routing(self) -> None:
        for value in (float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "finite"):
                SensorReading("temperature", "indoor_temperature", value, "C", "2026-10-21T00:00:00+00:00")


class EnergyComfortRuleTests(unittest.TestCase):
    def assess(self, context):
        return assess_energy_comfort("event-1", context)

    def test_inside_range_and_both_boundaries_need_no_adjustment(self) -> None:
        for temperature in (20.0, 22.0, 24.0):
            with self.subTest(temperature=temperature):
                result = self.assess(home_context(temperature=temperature))
                self.assertEqual(result.decision, "NO_ADJUSTMENT")
                self.assertEqual(result.policy, "occupied_comfort_inclusive_range")

    def test_too_hot_and_too_cold_need_adjustment_without_action(self) -> None:
        for temperature in (19.9, 24.1):
            with self.subTest(temperature=temperature):
                result = self.assess(home_context(temperature=temperature))
                self.assertEqual(result.decision, "ADJUSTMENT_NEEDED")
                self.assertEqual(result.missing_fields, ())

    def test_unknown_occupancy_is_insufficient_not_unoccupied(self) -> None:
        result = self.assess(home_context(occupied=None, energy=EnergyProfile(900, 400)))
        self.assertEqual(result.decision, "INSUFFICIENT_DATA")
        self.assertEqual(result.missing_fields, ("environment.occupied",))

    def test_missing_occupied_temperature_or_preference_is_explicit(self) -> None:
        no_temperature = self.assess(home_context(temperature=None))
        no_preference = self.assess(home_context(preference=None))
        self.assertIn("environment.temperature_c", no_temperature.missing_fields)
        self.assertEqual(no_temperature.decision, "INSUFFICIENT_DATA")
        self.assertEqual(no_preference.decision, "INSUFFICIENT_DATA")
        self.assertIn("preference.temperature_min_c", no_preference.missing_fields)
        self.assertIn("preference.temperature_max_c", no_preference.missing_fields)

    def test_unoccupied_temperature_alone_does_not_request_comfort_adjustment(self) -> None:
        result = self.assess(home_context(temperature=30.0, occupied=False))
        self.assertEqual(result.decision, "INSUFFICIENT_DATA")
        self.assertIn("energy.current_power_w", result.missing_fields)

    def test_unoccupied_explicit_power_and_device_evidence_needs_adjustment(self) -> None:
        result = self.assess(home_context(
            temperature=None, occupied=False, preference=None,
            energy=EnergyProfile(900.0, 400.0),
            devices=(DeviceObservation("heater-1", True, {"power": "on"}),),
        ))
        self.assertEqual(result.decision, "ADJUSTMENT_NEEDED")
        self.assertIn("available_powered_device_candidates=heater-1", result.evidence)
        self.assertIn("does not identify the cause or authorize control", result.rationale)

    def test_unoccupied_excess_power_without_device_evidence_stays_unknown(self) -> None:
        result = self.assess(home_context(
            occupied=False, energy=EnergyProfile(900.0, 400.0), devices=(),
        ))
        self.assertEqual(result.decision, "INSUFFICIENT_DATA")
        self.assertEqual(result.missing_fields, ("devices.available_powered_device",))

    def test_unoccupied_power_at_limit_needs_no_energy_adjustment(self) -> None:
        result = self.assess(home_context(
            temperature=None, occupied=False, preference=None,
            energy=EnergyProfile(400.0, 400.0),
        ))
        self.assertEqual(result.decision, "NO_ADJUSTMENT")


class EnergyComfortWorkflowTests(unittest.TestCase):
    def run_workflow(self, context):
        handler = EnergyComfortHandler()
        result = SmartHomeWorkflow([handler], FailingDeviceTool()).run(
            make_energy_comfort_event(context)
        )
        return handler, result

    def test_real_registry_coordinator_and_monitoring_path(self) -> None:
        handler, result = self.run_workflow(home_context(temperature=26.0))
        self.assertEqual(handler.energy_assessment.decision, "ADJUSTMENT_NEEDED")
        self.assertEqual(result.domain, "energy_comfort")
        self.assertEqual(result.assessment.risk_level, "MEDIUM")
        self.assertIn("decision=ADJUSTMENT_NEEDED", result.assessment.evidence)
        self.assertEqual(result.outcome, "ASSESSED")
        self.assertEqual([item.agent for item in result.trace], [
            "HomeCoordinatorAgent", "MonitoringAgent", "HomeCoordinatorAgent",
        ])

    def test_every_decision_branch_skips_device_dispatch_and_notification(self) -> None:
        contexts = (
            home_context(22.0),
            home_context(27.0),
            home_context(22.0, occupied=None),
            home_context(
                None, False, None, EnergyProfile(900.0, 400.0),
                (DeviceObservation("heater-1", True, {"power": "on"}),),
            ),
        )
        expected = (
            "NO_ADJUSTMENT", "ADJUSTMENT_NEEDED", "INSUFFICIENT_DATA", "ADJUSTMENT_NEEDED",
        )
        for context, decision in zip(contexts, expected):
            with self.subTest(decision=decision):
                outcome = monitor_energy_comfort_workflow(
                    make_energy_comfort_event(context), device_tool=FailingDeviceTool(),
                )
                self.assertEqual(outcome.assessment.decision, decision)
                result = outcome.workflow
                self.assertEqual(result.action_results, ())
                self.assertIsNone(result.notification_result)
                self.assertNotIn("DeviceAutomationAgent", [item.agent for item in result.trace])


if __name__ == "__main__":
    unittest.main()
