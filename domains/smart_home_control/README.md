# Smart Home Control

Owner: Yang Yang. Requirements: AR-02 / UC-02; optional OR-02, with UC-07 integration.

This implementation covers the Stage 1 core features and optional operating modes:

- bilingual deterministic interpretation for night, away and relax modes;
- optional structured `campus-qwen` proposals with strict validation and safe fallback;
- four simulated device types: light, curtain, front-door lock and air conditioner;
- ordered, allow-listed plans with an expected state for every command;
- independent readback and `COMPLETE`, `PARTIAL`, `FAILED` or clarification results;
- fail-closed handling for exterior-door unlock requests;
- local JSONL workflow evidence for the demonstration.

`handler.py` owns domain policy and plans, `devices.py` defines the fictional demo inventory, and `integration.py` assembles the shared workflow and records its result. The reusable interpreters are in `services/smart_home_goals.py`; the campus request adapter is in `services/campus_proxy.py`. Run `python -m simulation.smart_home_demo --scenario good-night` for the offline acceptance demonstration.

Shared LLM transport remains in `services/`, device interfaces remain in `tools/`, and orchestration remains in `agents/`. Credentials are read only from local environment variables. Tests are in `tests/test_smart_home_control.py` and `tests/test_smart_home_ui.py`; the page is `ui/smart_home_control.py`.
