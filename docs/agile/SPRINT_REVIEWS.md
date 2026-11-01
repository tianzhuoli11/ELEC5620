# Sprint reviews by milestone

The Sprint 0 summary was **compiled afterwards** from Jira status history, sprint goals, git and PR history; no review meeting was held for Sprint 0, and coordination happened through the group chat, the weekly lab and PR reviews. Sprint 1 was reviewed at an in-person meeting on 28 Oct, which also planned Sprint 2. Sprint 2 ends with the review and retrospective held on 1 Nov. Charts: [burndown and cumulative flow](AGILE.md#burndown-and-flow-reconstructed-from-jira-status-history).

---

## Sprint 0: 14–20 Oct (compiled retrospectively)

**Goal (Jira):** shared architecture and API contracts, plus five Core 1 minimum runnable scenarios.

**Delivered**

| Member | Jira | Outcome | Evidence |
| --- | --- | --- | --- |
| Yuanbo Zhang | SCRUM-12, 17, 18 | Fall risk assessment; agent message contracts; coordinator orchestration | PR #4 (21 Oct), `docs/member-notes/YUANBO_SPRINT0.md` |
| Yang Yang | SCRUM-13, 19, 23 | Natural-language goals, simulated devices, LLM fallback | PR #6 (24 Oct) |
| Jinjing Huang | SCRUM-14, 20 | Pet monitoring; shared sensor/event models; shared LangGraph framework | PR #3 shared framework and PR #2 (20 Oct) |
| Yan Li (Flora) | SCRUM-15, 21 | Hazard/intrusion monitoring; security policy and notifications | Jira Done 21 Oct and 28 Oct |
| Tianzhuo Li | SCRUM-16, 22 | Environment/preference assessment and context | Jira Done 24 Oct |

**Measured result:** 0 of 13 items were Done by the planned end (20 Oct); 12 by 28 Oct and all 13 by 30 Oct. Git shows 52 commits on 18–19 Oct, so work was happening, but Jira status trailed it.

**Problems observed (from records)**

- Two shared agent frameworks were built in parallel. After PR #3 merged on 20 Oct, Yuanbo's separate framework was discarded and the elderly domain was reworked onto the shared one (backup branch `backup-old-framework`).
- Jira statuses were updated days after the work, so the board did not show real progress.

**What changed in Sprint 1:** the shared framework in `agents/` became the single base, and later additions were made only as additive extensions to it (the confirmation pause/resume and `notify` added in PR #5 and reused by other domains).

**Discussion records:** No formal review meeting was held for Sprint 0. Coordination happened through the group chat, the weekly lab and PR comments.

---

## Sprint 1: 21–27 Oct

**Goal (Jira):** five Core 2 workflows and five Optional extensions through the same three agents.

**Delivered**

| Member | Jira | Outcome | Evidence |
| --- | --- | --- | --- |
| Yuanbo Zhang | SCRUM-24, 25 | Resident confirmation, caregiver alert and light; multi-level escalation (OR-04) | PR #5, #9, #10, #11 |
| Yang Yang | SCRUM-26, 27 | Verified multi-device control; home modes (OR-02) | PR #7 (24 Oct) |
| Jinjing Huang | SCRUM-28, 29 | Owner notification and logging; simulated feeding (OR-01) | PR #8 (25 Oct) |
| Yan Li (Flora) | SCRUM-30, 31 | Risk-based protective response; external warnings (OR-06) | PR #12, #15 (28 Oct) |
| Tianzhuo Li | SCRUM-32, 33 | Energy and comfort control; trade-off explanations | PR #13, #14 (28 Oct) |

**Measured result:** 4 of 11 items were Done by the planned end (27 Oct); 7 by 28 Oct 01:42; all 11 by 31 Oct (SCRUM-2 was reopened on 31 Oct and closed again). SCRUM-26 to 29 waited In Review from 24 to 28 Oct until 30 Oct, although PR #7 and PR #8 had already merged.

**Feedback loops that happened**

- **PR #8 review:** changes were requested because a feeder read timeout stopped the core pet alert. The fix added an UNAVAILABLE boundary and regression tests, and the PR was approved after 134 tests were rerun.
- **Elderly UI:** a page test failed with `KeyError: 'workflow'` because escalation records share the log file. Records are now filtered by `record_type`. A Streamlit widget-state error was fixed by moving the reply buttons to callbacks.
- **Integration check:** Elderly Safety was not yet reachable from the shared dashboard; the page was registered in `ui/domain_views.py`.

**Problems observed:** a review bottleneck (items waited up to six days In Review), and several PRs merged by their own author without a second reviewer.

**What changed in Sprint 2:** shared-file changes were opened as PRs for review, and integration was handled as a dedicated task (SCRUM-39, PR #17).

### Sprint 1 review and Sprint 2 planning meeting: 28 Oct 2026 (in person)

_The four discussion topics below are what was discussed at the meeting. The project-state and follow-up sections are taken from Jira and GitHub records._

| Item            | Detail                                                                                                               |
| --------------- | -------------------------------------------------------------------------------------------------------------------- |
| Date and format | Wednesday 28 Oct 2026, in person; the first day of Sprint 2, one day after the planned end of Sprint 1                 |
| Attendees       | Jinjing Huang, Yan Li (Flora), Tianzhuo Li, Yang Yang, Yuanbo Zhang                                                  |
| Duration        | About 1 hour                                                                                                         |
| Purpose         | Review where Sprint 1 stood, agree how the five domains would be integrated, and identify risks for the final sprint |

**State of the project when the meeting took place (from Jira and git)**

- Most Sprint 0 items (shared contracts and Core 1 scenarios) were marked Done on 21–24 Oct, about four days after the planned end of 20 Oct; one (SCRUM-13) was still open.
- Sprint 1 (Core 2 workflows and Optional extensions) had 4 of 11 items Done by its planned end of 27 Oct. Two Smart Home stories had waited In Review since 24 Oct.
- Each domain was still developed on its owner's branch. Elderly Safety, Smart Home Control and Pet Care were on `main`; Home Security and Energy & Comfort were merged later that day (PRs #12–#15).
- No AI call had yet been verified end to end from every domain against the campus proxy.

**Discussion and decisions**

1. **Progress.** The team reviewed progress against the Sprint 1 plan and acknowledged that it was behind schedule. Remaining domain work needed to reach `main` before integration could start.
2. **Integration owner.** Jinjing Huang would carry out the final merge and integration of all five domains into one release, so that one person owned cross-domain conflicts and the final state of `main`.
3. **Overdue Jira tasks.** Several Jira tasks were past their due dates and had not been updated. Tasks needed to be closed or updated so that the board reflected the real state of the work.
4. **VPN and campus model access.** Campus AI works only through the university VPN with a valid personal key, so it might not be reachable on the demonstration machine or the venue network. This was treated as a demonstration risk.

**Action items**

| Action                                                     | Owner             | Due   |
| ---------------------------------------------------------- | ----------------- | ----- |
| Merge remaining domain branches into `main`                | Each domain owner | 30 Oct |
| Integrate all five domains and resolve cross-domain issues | Jinjing Huang     | 30 Oct |
| Bring overdue Jira tasks up to date                        | Each task owner   | 28 Oct |
| Check VPN and campus model access for the demonstration    | Each member       | 28 Oct |

**What happened afterwards (follow-up evidence)**

| Topic | Follow-up | Evidence |
| --- | --- | --- |
| Progress | Home Security and Energy & Comfort reached `main` on 28 Oct; Elderly OR-04 integration followed on 28–29 Oct | PRs #12–#16 (28 Oct), #18 (29 Oct) |
| Integration owner | Jinjing integrated the release, added cross-domain safety interlocks, then CI, Docker and the shared explanation page | PR #17 (30 Oct), #20 (CI and container deployment), #21 (decision explanations) |
| Overdue tasks | Statuses were reconciled on 30 Oct; the delay is visible in the burndown | Burndown and cumulative-flow charts in AGILE.md |
| VPN and campus model | An AI evaluation with real campus-qwen calls was added. On 31 Oct the course key used for the Elderly reply evaluation was rejected (HTTP 401), so that evaluation used another OpenAI-compatible provider and records which | `docs/assessment/AI_EVALUATION.md`, PR #20, PR #26 |

**What the team learned from it**

- Status updates in Jira lagged behind the code by several days, so the board under-reported progress. Updating the Jira status in the same step as merging the PR would have avoided this.
- Naming a single integration owner gave one person responsibility for cross-domain conflicts. The integration PR (#17) found and fixed two cross-domain safety issues.
- External-service dependencies such as the VPN, keys and the campus proxy need to be tested on the demonstration machine early, not on the day.

---

## Sprint 2: 28–31 Oct (unfinished items carried in Jira Sprint 3 until 1 Nov)

**Goal (Jira):** acceptance tests per use case, integration fixes, a safety/privacy/fallback review, and a clean rebuild from the submitted source.

**Delivered**

| Area | Outcome | Evidence |
| --- | --- | --- |
| Integration | All five domains in one release with cross-domain safety interlocks | PR #17 (Jinjing Huang, 30 Oct) |
| Deployment and CI | GitHub Actions on Python 3.11/3.13, Docker image with health check, tests inside the container | PR #20; `docs/deployment/DEPLOYMENT.md` |
| Explanations (OR-03 / UC-06) | Shared "Decision explanations" page for all domains | PR #21 |
| Acceptance per use case | Elderly 18/18 (PR #19), Smart Home 10/10 plus UI screenshots (PR #24, #25), Energy & Comfort (SCRUM-38), Pet Care and Home Security (SCRUM-36, 37) | `docs/acceptance/` |
| Safety review | Elderly reply rules redesigned after two review rounds | PR #26 |
| Evidence | Requirements traceability, AI evaluation, advanced technologies, this sprint record and the burndown charts | `docs/` |

**Measured result:** 10 of 11 Sprint 2 items were Done by the planned end (31 Oct); the contribution statement (SCRUM-43) was closed on 1 Nov. SCRUM-3 and SCRUM-38 had been marked Done early, on 24 Oct.

**Feedback loops in this sprint**
- PR #17 (integration) found that a wrong model proposal could reverse a negated command, and that Energy control lacked cross-domain safety clearance; both were fixed with tests.
- PR #20: the first container CI run failed because tests wrote into the read-only source directory; fixed, and CI passed.
- PR #25: Yuanbo Zhang reviewed the Smart Home UI evidence against a rerun of the automated acceptance (10/10) and approved with two non-blocking notes.
- PR #26: Yang Yang and Jinjing Huang requested changes twice and found three classes of unsafe "safe" verdicts in the Elderly reply rules. This led to a design change, safe only for complete listed phrases, with the reviewers' examples kept as regression and workflow tests. Jinjing retested the final head and reported no remaining blockers.

### Sprint 2 review and final retrospective: 1 Nov 2026 (online)

| Item | Detail |
| --- | --- |
| Date and format | Sunday 1 Nov 2026, 13:34–14:05, online (Zoom) |
| Attendees | Jinjing Huang, Yan Li (Flora), Tianzhuo Li, Yang Yang, Yuanbo Zhang |
| Focus | A full manual end-to-end check of the integrated system before submission, then demonstration and submission planning |

**Review: manual end-to-end walkthrough**

Jinjing Huang ran the current `main` locally with the VPN connected and shared her screen; each owner directed the scenarios for their own page.

| Page | Scenarios run | Observed result | Follow-up |
| --- | --- | --- | --- |
| Elderly Safety (Yuanbo Zhang) | Fall still on the floor; fall then not moving with a resident reply; dropped object then standing again; an unclear reply; all room lights offline; no acknowledgement until the operator is informed | Behaved as designed: immediate alert for HIGH, question and reply handling for MEDIUM, an alert that still goes out when the light fails, escalation on no acknowledgement | None |
| Smart Home Control (Yang Yang) | Good night, Away, Relax and a custom request | Commands ran and were verified. Away switched everything off, which the team checked was intended | Yang to make the verified-result display easier to read (plain-language summary) |
| Home Security (Yan Li) | Normal and response scenarios | Behaved as expected | Flora's evidence PR was still awaiting review at the time |
| Energy & Comfort (Tianzhuo Li) | Adjustment with an occupied room and good comfort, 24 °C setpoint | Plan executed and was verified | None |
| Pet Care (Jinjing Huang) | Page checked during the walkthrough | No issue raised | None |

Result: no blocking defect was found in the five pages. One usability improvement (the Smart Home result display) was agreed.

**Discussion**

1. **Demonstration format** (from the course Ed Discussion): about 15 minutes to deploy from the Canvas download, then a 12-minute demonstration. Show the five modules and their test results, then the architecture, the three agents and the agile evidence. Assessors may ask any member to locate the code behind a function, so each member must know where their code is. About two minutes per member.
2. **Submission:** everything, including deployment instructions and evidence, must be inside the submitted source package, because it is downloaded and deployed on site.
3. **Pull requests:** two PRs were still open. The team agreed that PRs are reviewed on GitHub by another member before merging rather than merged by their author; Jinjing and Flora would review each other's.
4. **Jira and burndown:** because the Jira sprints were started late (30 Oct), Jira's built-in burndown does not reflect the real timeline. The team uses the charts rebuilt from Jira status history and git history, which show the delays as recorded.
5. **Documentation:** the `docs/` folder had become hard to navigate; it is to be organised by marking criterion.
6. **Campus model access:** Yuanbo has no working campus key; Jinjing's environment has working campus AI and VPN access.

**Retrospective: lessons from this project**

- *Went well:* all five domains work end to end on one shared framework; peer reviews on PRs (for example #8 and #26) found real defects before merging; the final walkthrough found no blocking issue.
- *Did not go well:* Jira sprints were not started when they began, so Jira's built-in burndown does not show the real timeline and statuses lagged behind the code; several early PRs were merged by their author without review; not every member had campus model access; documentation grew without structure.
- *Next time:* start each sprint in Jira on its first day and update the status in the same step as merging the PR; require a review before every merge; check external-service access (VPN, keys) early on the demonstration machine; keep one index for the documentation from the start.

**Actions**

| Action | Owner | Due |
| --- | --- | --- |
| Improve the Smart Home verified-result display, then re-check it | Yang Yang | 1 Nov |
| Review and merge the open PRs (cross-review) | Jinjing Huang, Yan Li, Tianzhuo Li | 1 Nov |
| Check whether anything else must be committed before packaging | Each member | 1 Nov, before 17:00 |
| Merge the remaining work, organise `docs/`, add the agile charts and prepare the final package | Yuanbo Zhang | 1 Nov, about 17:00 |
| Submit to Canvas, then download the submission and test the deployment from it | Team | 1 Nov |
| Write a two-minute script for one's own part and share it in the group | Each member | Before the rehearsal |
| Full rehearsal of the demonstration | Team | Mon 2 or Tue 3 Nov (demonstration on Wed) |
