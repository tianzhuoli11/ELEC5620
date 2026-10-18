# Shared data models

Store common Python data structures, enums and validation here. Agree the draft in `docs/INTERFACES.md` before implementation.

- Jinjing Huang: Sensor, Event, readings and event-related models.
- Yuanbo Zhang: agent messages, risk and workflow-state contracts.
- Yang Yang: action requests, observed device state and verification results.
- Tianzhuo Li: environment, preference, energy and HomeMode context.
- Yan Li: safety decisions and notification-result fields.

Choose one consistent data-class/validation approach together. Do not create incompatible Event definitions in individual domains. Models must not import Streamlit, call an LLM/network service or execute device actions.
