# Event and device simulation

Store event generators, simulated sensor inputs and simulated device state here. Jinjing Huang integrates Sensor/Event generation; Yang Yang integrates devices; all domain owners provide scenarios.

- Send inputs conforming to `models/` into the shared monitoring flow.
- Keep static fictional fixtures in `data/samples/`; keep generators and state-transition code here.
- Include normal and abnormal fall, pet, security and temperature inputs.
- Support offline, failed-action and state-mismatch device scenarios.
- Do not represent simulated state or notifications as real device/recipient responses.

Domain rules belong in `domains/`, common device entry points in `tools/`, and shared agent orchestration in `agents/`.
