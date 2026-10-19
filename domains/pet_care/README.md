# Pet Care

Owner: Jinjing Huang. Requirements: AR-03 / UC-03; optional OR-01.

Store empty-bowl/inactivity assessment, information needed for owner notifications, and optional feeding decisions here. Sprint 0 covers event monitoring, rule validation, LLM-failure fallback and recording. Sprint 1 adds the notification workflow and optional feeding.

Core monitoring must complete when OR-01 is disabled or no feeder is available. A model proposal must not directly dispense food; optional actions go through shared agents, policy checks, DeviceControlTool and state verification.

Jinjing's shared Sensor/Event models belong in `models/`, the event simulator in `simulation/`, and reusable fixtures in `data/samples/`; do not keep shared code only inside this domain. Put tests in `tests/` and views in `ui/`.

Sprint 0 implementation: `monitoring.py` assesses pet bowl and inactivity observations with deterministic thresholds and validates any optional LLM proposal. `records.py` persists the input and assessment as JSONL. The `monitor_pet_event` function is the Pet Care entry point for the shared MonitoringAgent once Yuanbo's dispatcher is available. See `docs/JINJING_SPRINT0.md`.

The optional `--use-campus-llm` flag in `simulation/pet_demo.py` uses the provisional course proxy client in `services/campus_proxy.py`. It needs a local personal key and campus network/VPN; a model response can add an explanation but cannot change the rule risk level or trigger feeding.
