# Shared agents and orchestration

Store the shared `HomeCoordinatorAgent`, `MonitoringAgent`, `DeviceAutomationAgent` and LangGraph state graphs, routing, confirmation/timeouts and result aggregation here. Yuanbo Zhang integrates the framework; every domain owner contributes interface needs and tests.

Implemented files are `coordinator.py`, `monitoring.py`, `automation.py` and `graph.py`. `SmartHomeWorkflow` assembles the graph once; `run(event)` selects a sensor-assessment path or a direct-goal planning path. The latter skips MonitoringAgent. Both return an assessed, optionally executed, traceable result. The fictional handlers are in `simulation/framework_demo.py`.

Import common types from `models/`, domain handlers from `domains/`, LLM/notification/audit adapters from `services/`, and device operations from `tools/`.

Do not put Streamlit pages here or create a separate copy of all three agents for each domain. Verify returned device states before reporting successful execution.
