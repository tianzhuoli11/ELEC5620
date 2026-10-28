# Shared data models

Common Python dataclasses and validation live here. `docs/INTERFACES.md` describes the implemented baseline; coordinate any public field changes before integration.

- Jinjing Huang: Sensor, Event, readings and event-related models.
- Yuanbo Zhang: agent messages, risk and workflow-state contracts.
- Yang Yang: goal interpretation, ordered action requests, observed device state and verification results.
- Tianzhuo Li: environment, preference, energy and HomeMode context.
- Yan Li: safety decisions and notification-result fields.

The baseline uses frozen dataclasses. `events.py` defines `Event` and `SensorReading` with timezone-aware timestamp checks and `to_dict()` output. `Event.readings` carries sensor observations, and `Event.simulated` labels test inputs. Do not create incompatible Event definitions in individual domains. Models must not import Streamlit, call an LLM/network service or execute device actions. Coordinate public field changes with the team.

`context.py` adds SCRUM-22 candidate types for environment, preference, whole-home power, HomeMode and observed device state. Unknown values remain `None`; numeric observations must be finite and units are explicit in field names. `HomeContext` is consumed by Energy & Comfort now and is available to home-control and security code through `models`, but those team-owned consumers have not yet integrated it. The candidate vocabulary and fields require M2/M4 and framework-owner review before being treated as a settled shared contract.
