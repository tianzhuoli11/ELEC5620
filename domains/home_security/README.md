# Home Security

Owner: Yan Li (Flora in Jira). Requirements: AR-04 / UC-04; optional OR-06.

SCRUM-15 implements simulated smoke, gas, water leak, unsafe appliance, unusual door/window, suspicious motion and abnormal smart-lock access monitoring. The UC-04 response now covers LOW recording, MEDIUM homeowner confirmation and HIGH emergency action with result verification. `monitoring.py` owns fixed risk rules and checks optional LLM proposals. `response.py` owns approved simulated response policy. `integration.py` adapts both to the shared `DomainHandler`, LangGraph workflow, notification service and device tool. `llm.py` uses the shared campus proxy. No independent SecurityAgent is created.

New simulated events have nine binary `state` readings and context for Home Mode, recent activity, authorised entry, door lock and water valve. The four added readings are optional for older five-sensor events. The appliance inputs represent a fictional overheat alarm and unexpected operation; they are not physical temperature measurements or device commands. An overheat alarm is HIGH, while isolated unexpected operation is MEDIUM. Missing original readings or invalid supplied readings produce at least MEDIUM risk and request human review. Smoke and gas alarms always produce HIGH risk; a model proposal cannot lower them. When multiple conditions occur, the highest fixed-rule risk wins. The model may provide a matching explanation, but the fixed rule determines the recorded level. The record stores the actual workflow trace and LLM status. Inputs are fictional, and runtime JSONL files are ignored by Git.

From the repository root, run:

```powershell
.venv\Scripts\python -m simulation.security_demo --scenario smoke
.venv\Scripts\python -m simulation.security_demo --scenario gas
.venv\Scripts\python -m simulation.security_demo --scenario unusual_door --reply approve
.venv\Scripts\python -m simulation.security_demo --scenario unusual_door --reply reject
.venv\Scripts\python -m simulation.security_demo --scenario unusual_door --reply timeout
.venv\Scripts\python -m simulation.security_demo --scenario device_failure
.venv\Scripts\python -m streamlit run app.py
```

The first two commands use fixed rules without a network request. To request real campus LLM advice, set `ELEC5620_API_KEY` in the local environment and use `--use-campus-llm`; the university network or VPN must reach the course proxy. The JSON output reports `llm_status` (`ACCEPTED`, `CONFLICT`, `INVALID`, `TIMEOUT`, or `ERROR`), so a failed call is never represented as success. The proxy key is never placed in prompts or records.

LOW records without an urgent action. MEDIUM sends a simulated confirmation request and pauses the shared graph. APPROVE executes scenario-appropriate simulated protection; REJECT closes without a device action. A timeout or two unclear replies sends a simulated warning but never counts silence as approval. The page's timeout button **simulates** expiry of the 30-second confirmation window; no background timer or real owner message is used. HIGH uses fixed pre-approved policy immediately. Gas closes a simulated valve; smoke and appliance overheating turn off a simulated appliance; water leaks close a simulated valve; intrusion turns on simulated lights. A siren follows as a safe warning even when a prior command fails. No policy locks an exit during fire or gas incidents. Each device command is verified by reading back its simulated state. Offline, rejected or unverified actions show FAILED or PARTIAL, and a separate simulated failure alert is recorded.

Each run or resume appends the input, rule assessment, LLM status, confirmation replies, notification outcomes, action results and agent trace to the ignored JSONL audit file. All inputs and devices are fictional. The campus LLM can suggest a risk rationale, but fixed rules determine risk and actions. Tests are in `tests/test_home_security.py` and `tests/test_home_security_ui.py`.

## OR-06 simulated external warnings

The same Home Security handler also accepts fictional earthquake, flood, severe storm and bushfire warnings. `external_warnings.py` validates the source allowlist, required fields, issue/expiry times and exact area code before assessing household relevance. The configured fictional home area is `SYDNEY_INNER_WEST`. An invalid or unrelated warning is recorded with its raw input and validation result but cannot notify or operate a device. A relevant warning sends a simulated homeowner notification. Only a relevant `EMERGENCY` warning enables the in-memory `emergency_mode` state; the shared DeviceAutomationAgent reads that state back to verify success. It never locks doors or closes valves based solely on an external warning.

The trusted-source ID is a **simulation allowlist**, not real authentication. No government API, live warning feed, real homeowner message or physical device is connected. Optional campus LLM advice uses the existing proxy client and is checked against the fixed warning rules. The Streamlit Home Security page offers relevant, irrelevant and invalid presets; `tests/test_external_warnings.py` covers all four hazards, rejected inputs, fallback and audit records.
