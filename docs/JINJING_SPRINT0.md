# Jinjing Huang: Sprint 0 monitoring demonstration

This delivers Jinjing's Sprint 0 portion of AR-03 / UC-03 and the shared Sensor/Event input work. It is a Python standard-library prototype, so no package installation or API key is needed for this demonstration.

From the repository root, run:

```powershell
python -m simulation.pet_demo --scenario empty_bowl
python -m simulation.pet_demo --scenario unusual_inactivity
python -m simulation.pet_demo --scenario normal_activity
python -m unittest discover -s tests -v
```

Each command creates a fresh **simulated** event with a unique ID and a timezone-aware timestamp. The domain assessment uses the same ID, and the demo appends both the input and assessment to `data/runtime/pet_events.jsonl`. This runtime file is ignored by Git. The output says explicitly that no notification or feeding occurred.

The current demonstration thresholds are 10% food level for bowl review, 60 minutes for unusual inactivity, and 120 minutes for a HIGH inactivity flag. These are prototype rules for discussion, not veterinary or medical advice. A missing or invalid sensor value produces a MEDIUM review result without inventing a measurement. An invalid, unavailable or conflicting LLM proposal uses the deterministic rule result; no LLM service is connected yet.

Integration contract: `models.Event` and `models.SensorReading` are shared input types. `domains.pet_care.records.monitor_pet_event(event, record_path=..., proposal_provider=...)` is the Pet Care handler for Yuanbo's future shared `MonitoringAgent`. The caller may provide a proposal function returning `risk_level` and `rationale`; it must not treat a proposal as permission for a device action. The shared agent dispatcher, real LLM service, owner notification and optional feeder control remain separate tasks.

Suggested Sprint 0 review: demonstrate the three scenarios, show the JSONL record for one event, then discuss the shared Event fields and thresholds with the team. Record actual feedback and any agreed changes in Jira rather than treating this document as a completed review.
