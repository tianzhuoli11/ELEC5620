# Tests

Store domain-rule, model-validation, service-adapter and agent-workflow tests here. Each member covers their own success, failure and fallback paths; shared contract changes need integration coverage.

Future tests can be organised under `unit/` and `integration/`, using `test_*.py` filenames. Default tests should use fictional data and controlled service doubles without real keys/devices. Real proxy tests must be explicitly selected.

Cover model timeout, unsafe-action rejection, notification failure, offline devices, state mismatch and pet core completion with optional feeding disabled. Record expected versus actual results and link evidence in Jira.

`test_pet_monitoring.py` covers event validation, simulated pet scenarios, rule fallback, untrusted model proposals and original assessment records. `test_pet_integration.py` covers the shared Pet Care graph path, simulated and failed owner alerts, persistent workflow outcomes, and the no-feeder safety boundary. `test_framework.py` covers sensor and direct-goal routing, two-device verification, partial failure, review gates, readback failures and unavailable notifications. `test_ui.py` covers the Pet Care dashboard's editable inputs, saved results and navigation. Run `python -m unittest discover -s tests -v` from the repository root. Review and deployment records belong in `docs/`; other domains and real proxy tests remain to be added by their owners.

`test_pet_sprint2.py` covers UC-03 core completion without a feeder, explicit optional feeding, invalid/disabled/offline goals, one-time dispatch, unverified readback, model timeout, and independent notification failure reporting. `test_ui.py` also exercises the resident-facing optional feeding controls.

`test_smart_home_control.py` covers bilingual and report-style direct interpretation, validated campus proposals, malicious/invalid output fallback, model timeout, typed device contexts, four-device verification, bounded retry, continued independent actions, offline and readback failures, approve/decline safety handling (including forged-context rejection), HomeMode persistence, traces and local evidence. `test_smart_home_ui.py` covers the successful, partial-failure and sensitive-action confirmation page flows.
