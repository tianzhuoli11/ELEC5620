# ELEC5620 Smart Home

Wed 09-11 Group 11 Stage 2 shared repository.

**Option A: Python + LangGraph + Streamlit**, using the course API proxy and the `campus-qwen` model. All five domains reuse the same agents, models and user interface.

The root `app.py` runs one Streamlit dashboard with Pet Care, Smart Home Control, Elderly Safety, Home Security and Energy & Comfort demonstrations. Each domain uses the shared agents and contracts. Pet Care includes simulated monitoring and feeding; Smart Home Control runs policy-validated multi-device plans; Elderly Safety handles fall assessment, confirmation and escalation; Home Security handles UC-04 monitoring, risk-based response and simulated OR-06 external warnings; Energy & Comfort runs assessment-only shared-workflow evaluation with fail-closed eligibility and deterministic explanations. Formal Energy & Comfort device control remains pending. Real notification delivery and physical-device adapters are not connected.

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

On macOS/Linux, use `.venv/bin/python` in place of `.venv\Scripts\python`. The framework demo needs no API key after dependencies are installed. Overview and Pet Care provide editable simulated readings, risk assessments and saved local history in the ignored `data/runtime/pet_events.jsonl` file. The Pet Care page also includes an optional simulated feeder demonstration with an explicit request, feature flag and offline-failure controls. **Reset inputs** clears the current input and result without deleting history.

Campus AI is optional in the implemented domain pages. Set `ELEC5620_API_KEY` in your local environment and connect to the university network or VPN, then enable the relevant page option. The key is not entered into the page or stored in the repository. Invalid, timed-out or unsafe model proposals fall back to deterministic rules and cannot directly authorise device commands. Owner alerts and device actions are simulated locally.

For a repeatable Pet Care acceptance check, run `python -m simulation.pet_demo --scenario empty_bowl` for core monitoring and notification, then `python -m simulation.pet_demo --scenario empty_bowl --enable-feeding --feed-grams 20` for one verified simulated feed. Add `--feeder-offline` or `--stale-readback` to check failure reporting. See [Jinjing's Sprint 2 evidence](docs/JINJING_SPRINT2.md) for the complete scenario list.

For Home Security, run `.venv\Scripts\python -m simulation.security_demo --scenario smoke` for immediate HIGH response, `--scenario unusual_door --reply approve` for MEDIUM confirmation, or `--scenario device_failure` for failed simulated actions. `normal` demonstrates LOW. Its Streamlit page also provides simulated OR-06 external warning scenarios. Add `--use-campus-llm` only when the local key and university network are available. The command prints the shared workflow result and saves local JSONL records at `data/runtime/security_events.jsonl`. See [Home Security](domains/home_security/README.md) for rules and scope.

For Energy & Comfort assessment preparation, run `.venv\Scripts\python -m simulation.energy_comfort_demo` and `.venv\Scripts\python -m simulation.energy_comfort_acceptance`. The Streamlit page assesses simulated temperature, occupancy, preference and energy context through the shared workflow, shows fail-closed eligibility and explanations, and labels the scope as assessment-only. It does not dispatch devices; formal control remains pending. Local assessment evidence is appended to ignored `data/runtime/energy_comfort.jsonl`.

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

For sensor events, the coordinator routes to monitoring and domain policy, then optional confirmation, device execution and notification. For direct user goals, it calls the configured interpreter and routes to a policy-validated domain plan; monitoring is skipped. Device plans execute in order and independently verify returned state. Each plan sets bounded retry and continuation rules, so a permitted safe warning can proceed after a failed protective command. The final result identifies complete, partial and failed outcomes with an agent trace. Smart Home Control provides a bilingual deterministic interpreter and an optional structured `campus-qwen` proposal path behind the same `GoalInterpreter` contract.

Sending a command is not proof of success. LLM proposals must not bypass safety rules. Domain modules must not directly operate physical devices. The implemented contracts are in [INTERFACES.md](docs/INTERFACES.md), and [INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md) shows how each owner connects their work.

## Collaboration

Develop on your named branch and open a Pull Request targeting `main`. Ask a teammate to review the change. Reference the Jira issue in commit messages and attach actual verification evidence before marking a task Done.

Synchronise your branch with the latest `main` before development. Personal branches do not automatically receive later changes from `main`. See [CONTRIBUTING.md](docs/CONTRIBUTING.md).

## Configuration and delivery

Use [.env.example](.env.example) for variable names. Real keys belong only in local environment variables or an ignored `.env` file. Pet Care reads environment variables directly; `.env` is not loaded automatically. The framework demo needs no key. Pet Care and Smart Home Control can optionally use the shared Campus Qwen proxy, while deterministic validated fallbacks remain available when the proxy is disabled or fails.

Do not commit real resident data, private contacts, credentials, virtual environments or runtime logs. Clearly label simulated data and devices.

The final application still needs the remaining domains integrated, real notification delivery decisions, a unified audit view and a clean-deploy rehearsal. Smart Home Control appends its simulated workflow evidence to ignored `data/runtime/smart_home_control.jsonl`. Rehearse deployment from a clean directory by 31 October. Canvas submission is due **1 November 2026, 23:59 Australia/Sydney**. All members must download the submitted source and redeploy it during the Week 13 demonstration.
