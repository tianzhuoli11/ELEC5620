# Documentation

**Start here (assessors):** the four files in the first table map directly to the Stage 2 marking criteria. Everything else is supporting detail.

## By marking criterion

| Criterion | Read first | Supporting detail |
| --- | --- | --- |
| 1. Implementation of Stage 1 requirements | [REQUIREMENTS_TRACEABILITY.md](REQUIREMENTS_TRACEABILITY.md): every MR / AR / OR / NFR mapped to code and tests, with changes from the Stage 1 design | Acceptance reports in [acceptance/](acceptance/) |
| 2. AI agent capabilities | [AI_EVALUATION.md](AI_EVALUATION.md): real model calls, rules versus model, the evaluation-driven fixes | [EXPLANATIONS.md](EXPLANATIONS.md) (UC-06 decision explanations), [INTEGRATED_CONTROL_REVIEW.md](INTEGRATED_CONTROL_REVIEW.md) |
| 3. Agile development | [AGILE.md](AGILE.md): Jira-history and Git-derived burndown evidence, user stories and feedback loops | [SPRINT_REVIEWS.md](SPRINT_REVIEWS.md) (per-sprint goals, results, meetings) and the member sprint notes below |
| 4. Advanced technologies | [ADVANCED_TECHNOLOGIES.md](ADVANCED_TECHNOLOGIES.md) | [DEPLOYMENT.md](DEPLOYMENT.md) (venv, Docker, CI) |

## Acceptance results per use case

- [acceptance/ELDERLY_SAFETY_ACCEPTANCE.md](acceptance/ELDERLY_SAFETY_ACCEPTANCE.md): UC-01, 18 scenarios.
- [acceptance/SMART_HOME_CONTROL_ACCEPTANCE.md](acceptance/SMART_HOME_CONTROL_ACCEPTANCE.md) and [acceptance/SMART_HOME_UI_EVIDENCE.md](acceptance/SMART_HOME_UI_EVIDENCE.md): UC-02, automated and UI.
- [acceptance/PET_CARE_ACCEPTANCE.md](acceptance/PET_CARE_ACCEPTANCE.md): UC-03, with UI screenshots; development history in [JINJING_SPRINT2.md](JINJING_SPRINT2.md).
- [acceptance/HOME_SECURITY_ACCEPTANCE.md](acceptance/HOME_SECURITY_ACCEPTANCE.md): UC-04, with UI screenshots; evidence index in [MEMBER4_HOME_SECURITY_EVIDENCE.md](MEMBER4_HOME_SECURITY_EVIDENCE.md).
- Energy & Comfort (UC-05): [MEMBER5_ENERGY_COMFORT_EVIDENCE.md](MEMBER5_ENERGY_COMFORT_EVIDENCE.md).

## Member sprint notes (development history)

- Yuanbo Zhang, Elderly Safety: [YUANBO_SPRINT0.md](YUANBO_SPRINT0.md), [YUANBO_SPRINT1.md](YUANBO_SPRINT1.md), [YUANBO_SPRINT1_OR04.md](YUANBO_SPRINT1_OR04.md).
- Yang Yang, Smart Home Control: [YANG_SPRINT0.md](YANG_SPRINT0.md), [YANG_SPRINT1.md](YANG_SPRINT1.md).
- Jinjing Huang, Pet Care and integration: [JINJING_SPRINT0.md](JINJING_SPRINT0.md), [JINJING_SPRINT2.md](JINJING_SPRINT2.md).

## For developers

- [INTERFACES.md](INTERFACES.md): shared data contracts and current limitations.
- [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md): how a domain connects to the shared agents.
- [CONTRIBUTING.md](CONTRIBUTING.md): branches, pull requests and the Jira workflow.
- [evidence/](evidence/): raw data behind the reports (Jira history, AI evaluation runs, charts and chart-building scripts).
- [`tools/generate_git_evidence_charts.py`](../tools/generate_git_evidence_charts.py): regenerates the supplementary Git activity, Sprint 0-2 implementation burndowns and verified feedback-loop charts.

Records here are real: deployment and review notes are added as the work happens, and no meeting or test result is pre-filled. Examples never contain real credentials or personal information.
