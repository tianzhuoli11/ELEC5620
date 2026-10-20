# Shared data models

Common Python dataclasses and validation live here. `docs/INTERFACES.md` describes the implemented baseline; coordinate any public field changes before integration.

- Jinjing Huang: Sensor, Event, readings and event-related models.
- Yuanbo Zhang: agent messages, risk and workflow-state contracts.
- Yang Yang: goal interpretation, ordered action requests, observed device state and verification results.
- Tianzhuo Li: environment, preference, energy and HomeMode context.
- Yan Li: safety decisions and notification-result fields.

The baseline uses frozen dataclasses. Do not create incompatible Event definitions in individual domains. Models must not import Streamlit, call an LLM/network service or execute device actions.
