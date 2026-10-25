# Pet Care

Owner: Jinjing Huang. Requirements: AR-03 / UC-03; optional OR-01.

Store empty-bowl/inactivity assessment, owner-alert outcomes, and optional feeding decisions here. The shared graph handles both core monitoring and the OR-01 simulated feeder path. Owner alerts are local simulated records, not real messages.

Core monitoring must complete when OR-01 is disabled or no feeder is available. A model proposal must not directly dispense food; optional actions go through shared agents, policy checks, DeviceControlTool and state verification.

Jinjing's shared Sensor/Event models belong in `models/`, the event simulator in `simulation/`, and reusable fixtures in `data/samples/`; do not keep shared code only inside this domain. Put tests in `tests/` and views in `ui/`.

`monitoring.py` assesses pet bowl and inactivity observations with deterministic thresholds and validates any optional LLM proposal. `records.py` preserves the original Sprint 0 assessment-only entry point. `integration.py` adapts the same rules to the shared MonitoringAgent, requests a simulated alert for MEDIUM/HIGH readings, and persists the actual workflow, alert and feeding outcome. `feeder.py` validates an explicit 1–50 g feeding goal, the feature flag, a low bowl reading and feeder availability before the shared DeviceAutomationAgent can dispatch one simulated dispense. A readback mismatch is reported as unverified and is never retried blindly. Core monitoring and notification complete even when feeding is disabled or unavailable. See `docs/JINJING_SPRINT0.md` and `docs/JINJING_SPRINT2.md`.

The optional `--use-campus-llm` flag in `simulation/pet_demo.py` uses the provisional course proxy client in `services/campus_proxy.py`. It needs a local personal key and campus network/VPN; a model response can add an explanation but cannot change the rule risk level or trigger feeding.
