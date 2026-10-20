# ELEC5620 Smart Home

Wed 09-11 Group 11 Stage 2 shared repository.

**Option A: Python + LangGraph + Streamlit**, using the course API proxy and the `campus-qwen` model. All five domains reuse the same agents, models and user interface.

The root `app.py` now runs a Streamlit dashboard with an interactive Pet Care demonstration. The other domain pages clearly identify modules that are still awaiting integration. The shared agent orchestration is still in progress.

## Run the dashboard

Use Python 3.11 or later. From the repository root:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local address printed by Streamlit (normally `http://localhost:8501`). Overview and Pet Care both provide a working input panel. Choose a scenario, edit the reading if needed, and click **Run check**. The risk, explanation, and event record are produced by the existing Pet Care module. Summary cards update from saved samples; history can be filtered by risk. Results are appended to the ignored local file `data/runtime/pet_events.jsonl`. **Reset inputs** clears the current input/result without deleting history.

Campus AI is optional. To enable it, set `ELEC5620_API_KEY` in your local environment before starting Streamlit and connect to the university network or VPN. The key is never entered into the web page or stored in the repository. Open **AI options** and enable **Include an AI explanation** before running a check. If the proxy fails or disagrees with a safety rule, the rule-based result remains visible. The demo never sends owner notifications or controls a feeder.

Run the existing checks with `python -m unittest discover -s tests -v`. For the Week 13 demonstration, install dependencies first, then download the submitted source from Canvas and run these commands from that downloaded copy.

## Project structure

```text
ELEC5620/
|-- app.py                     # Streamlit dashboard entry point
|-- requirements.txt           # Dashboard dependency
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

The initial dashboard was created on Jinjing Huang's branch for the Pet Care demonstration. The team should nominate a UI integration lead for the remaining domains. Each member supplies the inputs, outputs and demonstration scenarios for their domain. Jira remains the source for task ownership, acceptance criteria and planned dates.

## Shared execution flow

The three shared roles are `HomeCoordinatorAgent`, `MonitoringAgent` and `DeviceAutomationAgent`.

UI or simulated input -> monitoring/coordination -> LLM proposal and rule validation -> permitted tool execution -> returned-state verification -> user feedback and audit log.

Sending a command is not proof of success. LLM proposals must not bypass safety rules. Domain modules must not directly operate physical devices. Proposed shared fields are documented in [INTERFACES.md](docs/INTERFACES.md); agree them as a team before implementation.

## Collaboration

Develop on your named branch and open a Pull Request targeting `main`. Ask a teammate to review the change. Reference the Jira issue in commit messages and attach actual verification evidence before marking a task Done.

Synchronise your branch with the latest `main` before development. Personal branches do not automatically receive later changes from `main`. See [CONTRIBUTING.md](docs/CONTRIBUTING.md).

## Configuration and delivery

Use [.env.example](.env.example) for variable names. Real keys belong only in local environment variables or an ignored `.env` file. The Pet Care flow reads environment variables directly; `.env` is not loaded automatically. Other domain configuration is still pending.

Do not commit real resident data, private contacts, credentials, virtual environments or runtime logs. Clearly label simulated data and devices.

Rehearse deployment from a clean directory by 31 October. Canvas submission is due **1 November 2026, 23:59 Australia/Sydney**. All members must download the submitted source and redeploy it during the Week 13 demonstration.
