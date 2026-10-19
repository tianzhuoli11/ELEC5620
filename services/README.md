# Shared services

`campus_proxy.py` is Jinjing's provisional course-proxy client for Pet Care. It reads the personal `ELEC5620_API_KEY` from the local environment and sends an OpenAI-compatible chat-completions request. It returns a proposed pet risk; the Pet Care handler validates that proposal against its sensor rules. It does not contain or store a key.

Store the LLM adapter, configuration loading, notification transport and audit-log persistence here.

- Yang Yang integrates the shared `langchain-openai` adapter for the course `campus-qwen` proxy.
- Yan Li integrates notification interfaces with Yuanbo's caregiver workflow.
- All members agree audit fields for events, assessments, confirmations, actions and failures.

Read real keys from local configuration; never include them in source, logs or UI. Report model timeouts/invalid output explicitly so domain rules can apply fallback. Do not present mock replies as real model responses. Simulated notifications do not prove real delivery. Write runtime logs to ignored `data/runtime/` or `logs/`; fictional fixtures go in `data/samples/`.
