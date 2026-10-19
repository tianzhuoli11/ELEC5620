# Home Security

Owner: Yan Li (Flora in Jira). Requirements: AR-04 / UC-04; optional OR-06.

Store smoke, gas, water-leak, unusual door/motion assessment, risk-based response policies and external-warning relevance checks here. Sprint 0 covers event input and initial risk assessment. Sprint 1 adds protective response and optional warnings.

Put shared notifications in `services/`; agree cross-domain safety interfaces together. Actions use shared `agents/` and `tools/`, never model output alone. Clearly label simulated warnings. Put tests in `tests/` and fixtures in `data/samples/`.
