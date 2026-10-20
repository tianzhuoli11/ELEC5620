# Event and device simulation

`events.py` creates simulated sensor and direct user-goal events. `goals.py` contains an exact-phrase offline interpreter; it is not campus AI. `devices.py` holds in-memory simulated devices with explicit offline/unknown-device failures. `framework_demo.py` shows a sensor light scenario and a two-device night-mode goal. Jinjing Huang integrates Sensor/Event generation; Yang Yang integrates devices; all domain owners provide further scenarios.

- Send inputs conforming to `models/` into the shared monitoring flow.
- Keep static fictional fixtures in `data/samples/`; keep generators and state-transition code here.
- Include normal and abnormal fall, pet, security and temperature inputs.
- Support offline, failed-action and state-mismatch device scenarios.
- Do not represent simulated state or notifications as real device/recipient responses.

Domain rules belong in `domains/`, common device entry points in `tools/`, and shared agent orchestration in `agents/`.
