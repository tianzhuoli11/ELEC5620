# Device tools and adapters

Store DeviceControlTool, command schemas, device adapters, state queries and verification interfaces here. Yang Yang integrates this layer; domain owners provide action requirements and tests.

Simulated device state lives in `simulation/`; this directory provides the common entry point used by DeviceAutomationAgent. Future real adapters must follow the same contract.

Reuse `models/`. Never bypass safety policy or required confirmation. Distinguish command dispatch, device response and verified observed state. Offline, denied and mismatched results must report failure clearly. Do not put UI code or duplicate LLM clients here.
