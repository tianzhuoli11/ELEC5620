# Energy and Comfort

Owner: Tianzhuo Li. Requirements: AR-05 / UC-05; optional OR-05, with UC-06 integration.

Store environment/preference assessment, adjustment decisions, safety-first control policies and evidence-based trade-off explanations here. Sprint 0 covers temperature/occupancy/preference input and initial decisions. Sprint 1 adds control and optional explanations.

Put shared HomeEnvironment, UserPreference, EnergyProfile and HomeMode types in `models/`. Reuse `tools/` and `services/`. Safety overrides comfort and energy goals; missing facts remain unknown. Put tests in `tests/` and views in `ui/`.
