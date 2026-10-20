# Tests

Store domain-rule, model-validation, service-adapter and agent-workflow tests here. Each member covers their own success, failure and fallback paths; shared contract changes need integration coverage.

Future tests can be organised under `unit/` and `integration/`, using `test_*.py` filenames. Default tests should use fictional data and controlled service doubles without real keys/devices. Real proxy tests must be explicitly selected.

Cover model timeout, unsafe-action rejection, notification failure, offline devices, state mismatch and pet core completion with optional feeding disabled. Record expected versus actual results and link evidence in Jira.

`test_framework.py` covers sensor and direct-goal routing, two-device verification, partial failure and stop-on-failure behavior, a whole-plan review gate, ambiguity, bad event IDs, offline devices, mismatched and failed readback, and unavailable notifications. Run `python -m unittest discover -s tests -v`. Domain and real proxy tests remain to be added by the relevant owners.
