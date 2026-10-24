# Smart Home Control

Owner: Yang Yang. Requirements: AR-02 / UC-02; optional OR-02, with UC-07 integration.

This implementation covers the Stage 1 core features and optional operating modes:

- bilingual deterministic interpretation for night, away and relax modes plus direct device-state combinations;
- optional structured `campus-qwen` proposals with strict validation and safe fallback;
- typed `SmartDevice` / `DeviceContext` models for four simulated device types: light, curtain, front-door lock and air conditioner;
- ordered, allow-listed plans with an expected state for every command;
- independent readback and `COMPLETE`, `PARTIAL`, `FAILED` or clarification results;
- bounded retry and continuation of independent safe actions after one device fails;
- explicit approve/decline handling for exterior-door unlock requests before any device dispatch;
- persistent `HomeModeState` updates only after complete verification and exposes the mode to later monitoring context;
- local JSONL workflow evidence for the demonstration.

`handler.py` owns domain policy and plans, `devices.py` defines the fictional typed demo inventory, and `integration.py` assembles the shared workflow, resumes sensitive-action confirmation, and records each result. The reusable interpreters are in `services/smart_home_goals.py`; the campus request adapter is in `services/campus_proxy.py`. Run `python -m simulation.smart_home_demo --scenario direct` for the report-style multi-device demonstration and `--scenario sensitive-approved` for the confirmation flow.

Shared LLM transport remains in `services/`, device interfaces remain in `tools/`, and orchestration remains in `agents/`. Credentials are read only from local environment variables. Tests are in `tests/test_smart_home_control.py` and `tests/test_smart_home_ui.py`; the page is `ui/smart_home_control.py`.
