# Home Security

Owner: Yan Li (Flora in Jira). Requirements: AR-04 / UC-04; optional OR-06.

SCRUM-15 implements simulated smoke, gas, water leak, unusual door and motion monitoring. `monitoring.py` owns the fixed risk rules and validates optional LLM proposals; `integration.py` adapts the result to the shared `DomainHandler` and LangGraph workflow; `llm.py` supplies the Home Security prompt through the shared campus proxy client. No independent SecurityAgent is created.

The event has five binary `state` readings and context for Home Mode, recent activity, authorised entry, door lock and water valve. Missing or invalid readings produce at least MEDIUM risk and request human review. Smoke and gas alarms always produce HIGH risk; a model proposal cannot lower them. The model may provide a matching explanation, but the fixed rule determines the recorded level. The record stores the actual workflow trace and LLM status. Inputs are fictional, and runtime JSONL files are ignored by Git.

From the repository root, run:

```powershell
.venv\Scripts\python -m simulation.security_demo --scenario smoke
.venv\Scripts\python -m simulation.security_demo --scenario suspected_intrusion
.venv\Scripts\python -m streamlit run app.py
```

The first two commands use fixed rules without a network request. To request real campus LLM advice, set `ELEC5620_API_KEY` in the local environment and use `--use-campus-llm`; the university network or VPN must reach the course proxy. The JSON output reports `llm_status` (`ACCEPTED`, `CONFLICT`, `INVALID`, `TIMEOUT`, or `ERROR`), so a failed call is never represented as success. The proxy key is never placed in prompts or records.

SCRUM-15 records assessments only. Owner confirmation, protective device commands, outcome verification, notifications and external disaster warnings belong to SCRUM-21/30/31.

Later actions must use shared `agents/` and `tools/`, never model output alone. Clearly label simulated warnings. Tests are in `tests/test_home_security.py`.
