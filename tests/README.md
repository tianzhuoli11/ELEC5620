# Tests

Store domain-rule, model-validation, service-adapter and agent-workflow tests here. Each member covers their own success, failure and fallback paths; shared contract changes need integration coverage.

Future tests can be organised under `unit/` and `integration/`, using `test_*.py` filenames. Default tests should use fictional data and controlled service doubles without real keys/devices. Real proxy tests must be explicitly selected.

Cover model timeout, unsafe-action rejection, notification failure, offline devices, state mismatch and pet core completion with optional feeding disabled. Record expected versus actual results and link evidence in Jira.

Review and deployment records belong in `docs/`. Sprint 0 now includes `test_pet_monitoring.py`, covering event validation, simulated scenarios, rule fallback, untrusted model proposals and persistent records. Run `python -m unittest discover -s tests -v` from the repository root.
