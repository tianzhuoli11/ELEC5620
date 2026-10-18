# Shared agents and orchestration

Store the shared `HomeCoordinatorAgent`, `MonitoringAgent`, `DeviceAutomationAgent` and LangGraph state graphs, routing, confirmation/timeouts and result aggregation here. Yuanbo Zhang integrates the framework; every domain owner contributes interface needs and tests.

Suggested future files: `coordinator.py`, `monitoring.py`, `automation.py` and `graph.py`. Create them when implementing the functionality.

Import common types from `models/`, domain handlers from `domains/`, LLM/notification/audit adapters from `services/`, and device operations from `tools/`.

Do not put Streamlit pages here or create a separate copy of all three agents for each domain. Verify returned device states before reporting successful execution.
