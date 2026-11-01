# Documentation

**Start here (assessors).** Each folder below matches one part of the Stage 2 marking criteria. The first file named in each row is the entry point; the rest is supporting detail.

| Folder | Marking criterion | Read first | Also in the folder |
| --- | --- | --- | --- |
| [assessment/](assessment/) | 1. Stage 1 requirements and design | [REQUIREMENTS_TRACEABILITY.md](assessment/REQUIREMENTS_TRACEABILITY.md): every MR / AR / OR / NFR mapped to code, tests and acceptance evidence, plus changes from the Stage 1 deployment design | [INTEGRATED_CONTROL_REVIEW.md](assessment/INTEGRATED_CONTROL_REVIEW.md) (cross-domain safety interlocks) |
| [assessment/](assessment/) | 2. AI agent capabilities | [AI_EVALUATION.md](assessment/AI_EVALUATION.md): real model calls, rules versus model, evaluation-driven fixes | [EXPLANATIONS.md](assessment/EXPLANATIONS.md) (UC-06 decision explanations) |
| [agile/](agile/) | 3. Agile development | [AGILE.md](agile/AGILE.md): burndown and flow charts, user stories, feedback loops | [SPRINT_REVIEWS.md](agile/SPRINT_REVIEWS.md) (sprint goals, results, the 28 Oct and 1 Nov meetings) |
| [assessment/](assessment/) | 4. Advanced technologies | [ADVANCED_TECHNOLOGIES.md](assessment/ADVANCED_TECHNOLOGIES.md) | [deployment/DEPLOYMENT.md](deployment/DEPLOYMENT.md) (venv, Docker, CI) |

## Folders

| Folder | Contents |
| --- | --- |
| [acceptance/](acceptance/) | One acceptance report per use case: input, expected, actual, PASS/FAIL, with UI screenshots in `acceptance/assets/` |
| [deployment/](deployment/) | Deploying from the Canvas source (Python venv or Docker), CI verification, and a demonstration script |
| [development/](development/) | Shared contracts, how a domain connects to the shared agents, branch and pull-request workflow |
| [member-notes/](member-notes/) | Each member's development history and delivery evidence, per sprint |
| [evidence/](evidence/) | Raw data behind the reports: Jira history, AI evaluation runs, PR history, charts and the scripts that build them |

## Acceptance results per use case

| Use case | Report |
| --- | --- |
| UC-01 Elderly fall response | [ELDERLY_SAFETY_ACCEPTANCE.md](acceptance/ELDERLY_SAFETY_ACCEPTANCE.md) (18 scenarios) |
| UC-02 Multi-device home command | [SMART_HOME_CONTROL_ACCEPTANCE.md](acceptance/SMART_HOME_CONTROL_ACCEPTANCE.md) and [SMART_HOME_UI_EVIDENCE.md](acceptance/SMART_HOME_UI_EVIDENCE.md) |
| UC-03 Pet monitoring and feeding | [PET_CARE_ACCEPTANCE.md](acceptance/PET_CARE_ACCEPTANCE.md) |
| UC-04 Home security response | [HOME_SECURITY_ACCEPTANCE.md](acceptance/HOME_SECURITY_ACCEPTANCE.md) |
| UC-05 Energy and comfort | [ENERGY_COMFORT_ACCEPTANCE.md](acceptance/ENERGY_COMFORT_ACCEPTANCE.md) |

## Member notes

| Member | Domain | Notes |
| --- | --- | --- |
| Yuanbo Zhang | Elderly Safety | [Sprint 0](member-notes/YUANBO_SPRINT0.md), [Sprint 1](member-notes/YUANBO_SPRINT1.md), [OR-04 and campus AI](member-notes/YUANBO_SPRINT1_OR04.md) |
| Yang Yang | Smart Home Control | [Sprint 0](member-notes/YANG_SPRINT0.md), [Sprint 1](member-notes/YANG_SPRINT1.md) |
| Jinjing Huang | Pet Care, integration | [Sprint 0](member-notes/JINJING_SPRINT0.md), [Sprint 2](member-notes/JINJING_SPRINT2.md) |
| Yan Li (Flora) | Home Security | [Acceptance report](acceptance/HOME_SECURITY_ACCEPTANCE.md) |
| Tianzhuo Li | Energy & Comfort | [Delivery evidence](member-notes/MEMBER5_ENERGY_COMFORT_EVIDENCE.md), [contribution notes](member-notes/MEMBER5_CONTRIBUTION_STATEMENT.md) |

Records here are real: deployment and review notes were added as the work happened, and no meeting or test result is pre-filled. Examples never contain real credentials or personal information. Scripts that regenerate evidence: [`evidence/build_agile_charts.py`](evidence/build_agile_charts.py) and [`tools/generate_git_evidence_charts.py`](../tools/generate_git_evidence_charts.py).
