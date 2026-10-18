# Smart Home Control

Owner: Yang Yang. Requirements: AR-02 / UC-02; optional OR-02, with UC-07 integration.

Store natural-language goal interpretation, constraints, home-mode handling and domain-specific multi-device planning here. Sprint 0 translates requests into structured goals. Sprint 1 adds permitted execution, returned-state verification and mode changes.

Put the shared LLM client in `services/`, device interfaces in `tools/`, and orchestration in `agents/`. Do not store credentials or duplicate shared device simulation here. Put tests in `tests/` and views in `ui/`.
