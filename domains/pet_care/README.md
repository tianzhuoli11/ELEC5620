# Pet Care

Owner: Jinjing Huang. Requirements: AR-03 / UC-03; optional OR-01.

Store empty-bowl/inactivity assessment, information needed for owner notifications, and optional feeding decisions here. Sprint 0 covers event monitoring, rule validation, LLM-failure fallback and recording. Sprint 1 adds the notification workflow and optional feeding.

Core monitoring must complete when OR-01 is disabled or no feeder is available. A model proposal must not directly dispense food; optional actions go through shared agents, policy checks, DeviceControlTool and state verification.

Jinjing's shared Sensor/Event models belong in `models/`, the event simulator in `simulation/`, and reusable fixtures in `data/samples/`; do not keep shared code only inside this domain. Put tests in `tests/` and views in `ui/`.
