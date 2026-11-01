# Device tools and adapters

`device.py` defines the `DeviceTool` contract (commands, state queries and verification) used by DeviceAutomationAgent. Yang Yang owns this layer.

Simulated device state lives in `simulation/`; this directory provides the common entry point used by DeviceAutomationAgent. Future real adapters must follow the same contract.

Reuse `models/`. Never bypass safety policy or required confirmation. Distinguish command dispatch, device response and verified observed state. Offline, denied and mismatched results must report failure clearly. Do not put UI code or duplicate LLM clients here.
