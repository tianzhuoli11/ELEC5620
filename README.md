# ELEC5620 Smart Home

Wed 09-11 Group 11 Stage 2 shared repository.

**Option A: Python + LangGraph + Streamlit**, using the course API proxy and the `campus-qwen` model. All five domains reuse the same agents, models and user interface.

The shared framework has runnable, simulated examples for a **sensor event** and a **direct user goal with two device actions**. The coordinator selects the path, and each action has a separate verified result. The goal interpreter in the demo recognises only an exact fictional phrase; campus AI access, real domain rules, notification delivery and the final Streamlit interface are separate integration work. Do not treat the demo as the completed Stage 1 system.

## Run the framework demo

From a clean checkout with Python 3.11 or newer:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\python -m pip install -r requirements.txt
# macOS/Linux: .venv/bin/python -m pip install -r requirements.txt
.venv\Scripts\python -m simulation.framework_demo
.venv\Scripts\python -m unittest discover -s tests -v
```

On macOS/Linux use `.venv/bin/python` for the last two commands. The demo prints both paths: a sensor event controlling one simulated light and a direct "Good night" goal controlling a simulated light and thermostat. It includes per-device verification and an agent trace. It needs no API key or network after installation. Streamlit is in the shared dependencies for the later UI; there is not yet a root `app.py` in this branch.

On Windows, unzip or clone into a short path such as `C:\ELEC5620` before creating `.venv`; very deep paths can exceed Windows' file-path limit during Streamlit installation. Use that same short-path procedure in the Week 13 clean-deploy rehearsal.

## Project structure

```text
ELEC5620/
|-- agents/                    # Three shared agents and LangGraph orchestration
|-- domains/                   # Domain-specific business logic
|   |-- elderly_safety/        # Yuanbo Zhang
|   |-- smart_home_control/    # Yang Yang
|   |-- pet_care/              # Jinjing Huang
|   |-- home_security/         # Yan Li
|   `-- energy_comfort/        # Tianzhuo Li
|-- models/                    # Shared events, sensors, risks, actions and context
|-- tools/                     # DeviceControlTool, adapters and state queries
|-- services/                  # LLM, notification, configuration and audit services
|-- ui/                        # Streamlit views, navigation, components and styling
|-- simulation/                # Event generation and simulated device state
|-- data/samples/              # Fictional fixtures and demonstration scenarios
|-- tests/                     # Unit, integration and failure-path tests
|-- docs/                      # Interfaces, collaboration and deployment guidance
|-- requirements.txt           # Python dependencies for the shared stack
|-- .env.example               # Configuration example without real credentials
`-- .gitignore                 # Local credentials, environments and generated output
```

Each directory has a README explaining its contents and integration boundaries. Keep business logic independent of Streamlit; do not copy shared agents or LLM clients into individual domains.

## Ownership and branches

| Member | Domain directory | Branch | Shared implementation focus |
| --- | --- | --- | --- |
| Yuanbo Zhang | `domains/elderly_safety/` | `yuanbo-zhang` | Agent framework, coordination and message contracts |
| Yang Yang | `domains/smart_home_control/` | `yang-yang` | Device tools and shared LLM integration |
| Jinjing Huang | `domains/pet_care/` | `jinjing-huang` | Sensor/Event models and event simulation |
| Yan Li (Flora in Jira) | `domains/home_security/` | `yan-li` | Security rules and notification integration |
| Tianzhuo Li | `domains/energy_comfort/` | `tianzhuo-li` | Environment, preference and energy context |

The team must nominate a UI integration lead. Each member supplies the inputs, outputs and demonstration scenarios for their domain. Jira remains the source for task ownership, acceptance criteria and planned dates.

## Shared execution flow

The three shared roles are `HomeCoordinatorAgent`, `MonitoringAgent` and `DeviceAutomationAgent`.

For sensor events, the coordinator routes to monitoring and domain policy, then optional device execution and notification. For direct user goals, it calls the configured interpreter and routes to a policy-validated domain plan, then optional device execution and notification; monitoring is skipped. Device plans execute in order, verify each returned state and stop after failure. The final result identifies complete, partial and failed outcomes, with an in-memory trace. The demo interpreter is deterministic; the campus model adapter still needs to implement the same `GoalInterpreter` contract.

Sending a command is not proof of success. LLM proposals must not bypass safety rules. Domain modules must not directly operate physical devices. The implemented contracts are in [INTERFACES.md](docs/INTERFACES.md), and [INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md) shows how each owner connects their work.

## Collaboration

Develop on your named branch and open a Pull Request targeting `main`. Ask a teammate to review the change. Reference the Jira issue in commit messages and attach actual verification evidence before marking a task Done.

Synchronise your branch with the latest `main` before development. Personal branches do not automatically receive later changes from `main`. See [CONTRIBUTING.md](docs/CONTRIBUTING.md).

## Configuration and delivery

Use [.env.example](.env.example) for the proposed variable names. Real keys belong only in local environment variables or an ignored `.env` file. The framework demo does not load configuration or call the model; the campus AI adapter is still to be implemented.

Do not commit real resident data, private contacts, credentials, virtual environments or runtime logs. Clearly label simulated data and devices.

The final application still needs its Streamlit entry point, campus goal interpreter, configuration loading, integrated domains, notification delivery, persistent audit records and clean-deploy rehearsal. Canvas submission is due **1 November 2026, 23:59 Australia/Sydney**. All members must download the submitted source and redeploy it during the Week 13 demonstration.
