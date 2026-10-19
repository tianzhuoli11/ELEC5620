# Shared services

Store the LLM adapter, configuration loading, notification transport and audit-log persistence here.

- Yang Yang integrates the shared `langchain-openai` adapter for the course `campus-qwen` proxy.
- Yan Li integrates notification interfaces with Yuanbo's caregiver workflow.
- All members agree audit fields for events, assessments, confirmations, actions and failures.

Read real keys from local configuration; never include them in source, logs or UI. Report model timeouts/invalid output explicitly so domain rules can apply fallback. Do not present mock replies as real model responses. Simulated notifications do not prove real delivery. Write runtime logs to ignored `data/runtime/` or `logs/`; fictional fixtures go in `data/samples/`.
