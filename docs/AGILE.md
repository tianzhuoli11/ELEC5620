# Agile evidence, recovered history and remaining gaps

This document reconciles the team's Jira records with dated Git commits, pull requests, CI runs and acceptance evidence. It was refreshed on 1 November 2026. It does not backdate Jira activity or present reconstructed notes as contemporaneous minutes.

Sources: [Jira backlog](https://f1orestyinlem.atlassian.net/jira/software/projects/SCRUM/boards/1/backlog), [Jira sprint burndown](https://f1orestyinlem.atlassian.net/jira/software/projects/SCRUM/boards/1/reports/burndown?source=overview), Git history, [selected PR evidence](evidence/pr_history.json), and the linked repository evidence below.

## Iterations and recoverable evidence

The team reports that the iterations were carried out during the planned periods, while some Jira start/complete/status administration was performed later because the team was learning the tool. Jira therefore remains useful evidence, but its recorded administration dates are read together with independently dated Git and PR activity.

| Iteration | Intended period and scope | Authentic Jira evidence | Independently dated implementation evidence | Honest interpretation |
| --- | --- | --- | --- | --- |
| Sprint 0 | 14–20 Oct: shared contracts, framework and five Core 1 minimum scenarios | Jira report retains Sprint 0 for 14–20 Oct and records a 13-work-item scope increase; its completed-work table is still available | Repository setup on 18 Oct (`fe40a0a`), Pet/AI work and dashboard on 19 Oct (`3f5e636`, `b6a64f8`, `4c9732a`), shared graph and Pet integration on 20 Oct (`4d0af7a`, `761d829`) | Strong evidence for shared framework and Pet progress exists inside the period. Other domain work was merged shortly after the planned boundary, so the report must not claim every Core 1 increment was already integrated by 20 Oct without additional owner evidence. |
| Sprint 1 | 21–27 Oct: Core 2 workflows and optional extensions | Jira report shows a later one-day administration window and a completed-work table | Elderly/Security/Energy on 21 Oct (`d9b42a7`, `364206c`, `2eaa35c`–`6a6720a`); Smart Home and Pet review work on 24–25 Oct (`75cd954`, `a9b3a99`, `53749aa`, `dd5a7e2`); Elderly work through 27 Oct (`590fa61`, `98b2f16`) | Dated Git/PR history supports real iteration activity during 21–27 Oct. Jira sprint administration was late and is not rewritten as if it happened earlier. |
| Sprint 2 | 28–31 Oct: acceptance, integration, deployment and safety review | Jira retains Sprint 2 for 30–31 Oct. Its close report lists several acceptance/release items as incomplete at sprint close and later completed outside it or carried into Sprint 3 | Acceptance/integration on 28–29 Oct (`ec2d130`, `d66f324`, `50d1604`, `4e7607e`); CI/Docker evidence on 30 Oct (`3c81277`, `986de17`); Smart Home/Elderly evidence and reviews on 31 Oct (`78c3506`, `a84e781`, `c9d9570`) | Real work spans the intended 28–31 Oct period. Jira honestly shows incomplete work at the sprint boundary and later carry-over rather than a perfect historical burn. |
| Sprint 3 | 31 Oct–1 Nov: final acceptance, release evidence and Canvas preparation | On 1 Nov the active sprint contained eight items: seven Done and SCRUM-43 (contribution statement/Canvas submission) In Progress. The backlog was empty | Latest `main` is `c9d9570`; its [Prototype verification run](https://github.com/tianzhuoli11/ELEC5620/actions/runs/41178514735) passed | Finish SCRUM-43 only after the real contribution statement and Canvas submission are complete, then complete the sprint and retain the final report. |

## Authentic burndown evidence

All four sprints remain selectable in Jira's Sprint burndown report even though completed sprints no longer appear on the active backlog. The report initially looks empty because no historical Story Point estimates were entered. Selecting **Work item count** displays the authentic item-count trend and completed/incomplete tables.

- Do not add retrospective Story Points merely to manufacture a chart.
- Capture the final Sprint 0–3 reports with `Estimation field = Work item count` after SCRUM-43 is genuinely complete.
- The historical charts are evidence of the recorded Jira workflow, including late administration, carry-over and scope changes; they are not proof that every action happened exactly when Jira was updated.
- The earlier image below is retained as a 30 Oct historical snapshot, not as the current burndown.

![Historical Jira backlog state captured on 30 October; not a burndown chart](evidence/jira-sprint-state.png)

## User stories and ownership

The following are concise reformulations of the implemented issue scope. Jira remains authoritative for assignment and acceptance criteria.

| Jira | Owner | Story | Acceptance / evidence |
| --- | --- | --- | --- |
| SCRUM-12 / 24 / 25 | Yuanbo Zhang | As a resident, I want a suspected fall assessed and clarified so that help can be requested when needed. | Fall, safe/help/unclear reply, escalation and acceptance tests |
| SCRUM-13 / 26 / 27 | Yang Yang | As a homeowner, I want a supported home command applied and verified so that I can trust the displayed outcome. | Multi-device, approval, offline and readback tests; PRs #6/#7 and SCRUM-35 evidence |
| SCRUM-14 / 28 / 29 | Jinjing Huang | As a pet owner, I want food/activity alerts and explicitly authorised simulated feeding so that monitoring works even when the feeder fails. | Pet monitoring/integration/Sprint 2 tests; PR #8 |
| SCRUM-15 / 30 / 31 | Yan Li (Flora) | As a homeowner, I want hazard/intrusion warnings assessed and safely handled so that unsafe or unapproved actions do not run. | Security, confirmation and external-warning tests |
| SCRUM-16 / 32 / 33 | Tianzhuo Li | As a resident, I want comfort and energy context assessed and permitted adjustments verified so that safety takes priority. | Energy assessment/eligibility/control tests; cross-domain work in PR #17 |
| SCRUM-34–38 | Respective domain owners | As a reviewer, I want repeatable expected/actual scenarios so that integration failures can be reproduced. | Domain acceptance runners and page tests |
| SCRUM-39 / 42 | Shared integration / safety owners | As a reviewer, I want invalid goals and active safety incidents to block comfort actions so that optional automation cannot override protection. | Faulty-proposal regression and actual cross-page safety test |
| SCRUM-41 / 43 | Release owners | As a demonstrator, I want the exact submitted source rebuilt and contribution evidence attached so that delivery can be reproduced and assessed. | CI/container checks plus the still-required exact Canvas-archive rehearsal and submission record |

## Documented feedback loops

| Real evidence | Feedback / observation | Actual refinement | Verification |
| --- | --- | --- | --- |
| [PR #8 requested changes](https://github.com/tianzhuoli11/ELEC5620/pull/8#pullrequestreview-5637402410) | Feeder read timeout stopped core assessment/alert/audit; widget reset warning | Commits `ce5a131`, `dd5a7e2`: UNAVAILABLE boundary, regressions and widget fix | Reviewer [approved after rerunning 134 tests](https://github.com/tianzhuoli11/ELEC5620/pull/8#pullrequestreview-5640680543) |
| PR #17 inspection and commits `50d1604`, `4e7607e` | A model proposal could reverse a negated goal; Energy lacked cross-domain clearance | Pre-model negation guard, target consistency, executable simulation and fresh safety interlocks | Historical 275-test run plus cross-page success→smoke→block evidence |
| PR #20 and [first container CI failure](https://github.com/tianzhuoli11/ELEC5620/actions/runs/41048246193) | Tests wrote temporary files below the non-root read-only `/app` source | Commits `546400d`, `986de17` moved affected fixtures to the system temporary directory | [Independent Python and container verification passed](https://github.com/tianzhuoli11/ELEC5620/actions/runs/41048545525) |
| [PR #26 review 1](https://github.com/tianzhuoli11/ELEC5620/pull/26#pullrequestreview-5721373656) | Prefix matching treated “No idea” and injury reports as safe | Commit `0dffe44` made negative-response handling phrase-aware and added regressions | Reviewer's five reproductions no longer closed the event |
| [PR #26 review 2](https://github.com/tianzhuoli11/ELEC5620/pull/26#pullrequestreview-5721486340) | A word whitelist still accepted “Okay, I am down” and could discard non-English context | Commit `a84e781` accepts only complete listed safe replies; other replies remain unclear/escalate | New workflow regressions, green CI and merge commit `c9d9570` |

PR #17 has no written GitHub review approval in the queried review array and is not presented as one. PR #26 was merged after the second fix and green CI; the two requested-changes reviews are the feedback-loop evidence, not an invented approval.

## Review and retrospective recovery

Jira retains SCRUM-1, SCRUM-2 and SCRUM-3 as Done review/retrospective tasks, but their descriptions are planning text and explicitly say that actual notes and outcomes are required. At the 1 Nov inspection they had no substantive meeting comment or attachment. A Done status alone is therefore not evidence that the acceptance criteria were recorded.

If the meetings occurred but notes were omitted, add a transparent retrospective record now: state when the record was created, the actual meeting date if the team can verify it, participants, demonstrated work, feedback, resulting changes, verification and remaining actions. Link the dated PR/commit/CI evidence above. Do not make the new Jira comment appear contemporaneous or invent participants. The ready-to-complete checklist is in [SPRINT_REVIEW_RETRO_RECOVERY.md](SPRINT_REVIEW_RETRO_RECOVERY.md).

## Two-minute demonstration evidence

1. Open Jira's Sprint 3 burndown with **Work item count**, then use the Sprint selector to show that Sprint 0–2 remain available.
2. Explain that Git/PR dates support real iteration work while some Jira administration was late.
3. Show PR #8's requested changes→fix→approval and PR #26's two requested-changes→fix→green-CI sequence.
4. Show the latest passing Actions run and the exact Canvas-source deployment evidence after it is complete.
