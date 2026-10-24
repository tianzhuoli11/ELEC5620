# ELEC5620 Smart Home

Wed 09-11 Group 11 Stage 2 shared repository.

**Option A: Python + LangGraph + Streamlit**, using the course API proxy and the `campus-qwen` model. All five domains reuse the same agents, models and user interface.

The root `app.py` runs a Streamlit dashboard with interactive Pet Care and Smart Home Control demonstrations. Pet Care routes through the shared coordinator and monitoring agent. Smart Home Control interprets bilingual home-mode requests, creates policy-validated multi-device plans, executes them through the shared automation agent, independently verifies returned device state, and records complete, partial, failed or clarification outcomes. The other three domain pages are pending their owners' integrations. Real notification delivery and physical-device adapters are not connected.

## Run the dashboard and framework demo

Use Python 3.11 or newer. On Windows, clone or unzip to a short path such as `C:\ELEC5620` before creating a virtual environment; deep paths can exceed the installation path limit.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m simulation.framework_demo
.venv\Scripts\python -m simulation.smart_home_demo --scenario good-night
.venv\Scripts\python -m streamlit run app.py
```

On macOS/Linux, use `.venv/bin/python` in place of `.venv\Scripts\python`. The framework demo needs no API key after dependencies are installed. Overview and Pet Care provide editable simulated readings, risk assessments and saved local history in the ignored `data/runtime/pet_events.jsonl` file. **Reset inputs** clears the current input and result without deleting history.

Campus AI is optional for Pet Care and Smart Home Control. Set `ELEC5620_API_KEY` in your local environment and connect to the university network or VPN, then enable the AI option on the relevant page. The key is not entered into the page or stored in the repository. Invalid, timed-out or unsafe model proposals fall back to deterministic rules and never directly authorise device commands. Owner alerts and device actions are simulated locally.

## Project structure

```text
ELEC5620/
|-- app.py                     # Streamlit dashboard entry point
|-- requirements.txt           # Tested framework and dashboard dependencies
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

The initial dashboard was created on Jinjing Huang's branch for the Pet Care demonstration. Yang Yang has added the Smart Home Control workspace. The team should nominate a UI integration lead for the remaining domains. Each member supplies the inputs, outputs and demonstration scenarios for their domain. Jira remains the source for task ownership, acceptance criteria and planned dates.

## Shared execution flow

The three shared roles are `HomeCoordinatorAgent`, `MonitoringAgent` and `DeviceAutomationAgent`.

For sensor events, the coordinator routes to monitoring and domain policy, then optional device execution and notification. For direct user goals, it calls the configured interpreter and routes to a policy-validated domain plan, then optional device execution and notification; monitoring is skipped. Device plans execute in order, verify each returned state and stop after failure. The final result identifies complete, partial and failed outcomes, with an in-memory trace. Smart Home Control provides a bilingual deterministic interpreter and an optional structured `campus-qwen` proposal path behind the same `GoalInterpreter` contract.

Sending a command is not proof of success. LLM proposals must not bypass safety rules. Domain modules must not directly operate physical devices. The implemented contracts are in [INTERFACES.md](docs/INTERFACES.md), and [INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md) shows how each owner connects their work.

## Collaboration

Develop on your named branch and open a Pull Request targeting `main`. Ask a teammate to review the change. Reference the Jira issue in commit messages and attach actual verification evidence before marking a task Done.

Synchronise your branch with the latest `main` before development. Personal branches do not automatically receive later changes from `main`. See [CONTRIBUTING.md](docs/CONTRIBUTING.md).

## Configuration and delivery

Use [.env.example](.env.example) for variable names. Real keys belong only in local environment variables or an ignored `.env` file. Pet Care reads environment variables directly; `.env` is not loaded automatically. The framework demo needs no key. Pet Care and Smart Home Control can optionally use the shared Campus Qwen proxy, while deterministic validated fallbacks remain available when the proxy is disabled or fails.

Do not commit real resident data, private contacts, credentials, virtual environments or runtime logs. Clearly label simulated data and devices.

The final application still needs the remaining domains integrated, real notification delivery decisions, a unified audit view and a clean-deploy rehearsal. Smart Home Control appends its simulated workflow evidence to ignored `data/runtime/smart_home_control.jsonl`. Rehearse deployment from a clean directory by 31 October. Canvas submission is due **1 November 2026, 23:59 Australia/Sydney**. All members must download the submitted source and redeploy it during the Week 13 demonstration.
