# Domain business logic

Each member implements scenario rules, assessment, domain handlers and domain prompts in their own directory. Shared agents coordinate cross-domain workflows.

| Directory | Owner |
| --- | --- |
| `elderly_safety/` | Yuanbo Zhang |
| `smart_home_control/` | Yang Yang |
| `pet_care/` | Jinjing Huang |
| `home_security/` | Yan Li |
| `energy_comfort/` | Tianzhuo Li |

Domain code must not depend on Streamlit. Put views in `ui/`, shared types in `models/`, generators in `simulation/`, fictional fixtures in `data/samples/`, and tests in `tests/`. Discuss shared contract changes before submitting a PR.
