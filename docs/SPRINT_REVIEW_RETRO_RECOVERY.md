# Sprint Review and Retrospective recovery checklist

Status: **team confirmation required**. This is not a completed meeting record.

Use this checklist to transparently record omitted notes in Jira SCRUM-1, SCRUM-2 and SCRUM-3. The comments must identify the record as retrospective and must contain only confirmed participants, dates and outcomes.

## Required header for each Jira record

```text
Retrospective record created: 1 November 2026
Actual review date: [team-confirmed date, or "not independently recorded"]
Participants: [only people who actually participated]

The team conducted the iteration work during the planned period, but the
review notes were not entered into Jira at that time because the team was
still learning Jira sprint administration. This record is reconstructed from
the participants' recollection and the dated Git, PR, CI and acceptance
evidence linked below.
```

## Questions the team must answer

For each sprint, record concise, specific answers:

1. What was actually demonstrated?
2. What succeeded?
3. What failed, remained incomplete or was simulated?
4. What feedback did another member give?
5. Which issue, commit or PR implemented the response?
6. Who verified the change and how?
7. What moved to the next sprint?

## Evidence anchors

### Sprint 0 — 14–20 October

- Jira: [SCRUM-1](https://f1orestyinlem.atlassian.net/browse/SCRUM-1)
- Shared structure/configuration: `fe40a0a` and neighbouring 18 Oct documentation commits.
- Pet monitoring, simulated events and campus proposal validation: `3f5e636`, `b6a64f8`, `a3156bc`.
- Shared dashboard/graph and Pet integration: `4c9732a`, `4d0af7a`, merge `761d829`.
- Limitation: Git evidence inside the planned window is strongest for shared/Pet work; do not claim all five Core 1 increments were integrated by 20 Oct unless owners provide additional dated evidence.

### Sprint 1 — 21–27 October

- Jira: [SCRUM-2](https://f1orestyinlem.atlassian.net/browse/SCRUM-2)
- Elderly/Security/Energy on 21 Oct: `d9b42a7`, `364206c`, `2eaa35c`–`6a6720a`.
- Smart Home PRs #6/#7 on 24 Oct: `75cd954`, `a9b3a99`.
- Pet PR #8 feedback and fix on 24–25 Oct: review `5637402410`, commits `ce5a131`, `dd5a7e2`, approval `5640680543`.
- Elderly confirmation/escalation on 25–27 Oct: `590fa61`, `98b2f16`.
- Limitation: Jira records a later one-day administration window even though Git/PR evidence exists during the planned dates.

### Sprint 2 — 28–31 October

- Jira: [SCRUM-3](https://f1orestyinlem.atlassian.net/browse/SCRUM-3)
- Acceptance and integration: `ec2d130`, `d66f324`, `50d1604`, `4e7607e`.
- CI/Docker failure→fix→pass: run `41048246193`, commits `546400d`, `986de17`, passing run `41048545525`.
- Smart Home acceptance/UI evidence: PRs #24/#25, commits `d704cae`, `5368539`, `beafa78`.
- Elderly reply evaluation and PR #26 reviews: reviews `5721373656`, `5721486340`; fixes `0dffe44`, `a84e781`; merge `c9d9570`.
- Limitation: the Jira close report shows several acceptance/release items incomplete at the Sprint 2 boundary and later completed/carried over.

## Final action list

- [ ] Team confirms actual dates and participants.
- [ ] Team supplies one success, one problem and one improvement per sprint.
- [ ] Jira comments are posted to SCRUM-1, SCRUM-2 and SCRUM-3 with evidence links.
- [ ] Sprint 0–3 burndown reports are captured using **Work item count**.
- [ ] SCRUM-43 is completed only after the contribution statement and Canvas submission are real.
- [ ] Sprint 3 is completed and its final report retained.
- [ ] `docs/AGILE.md` is updated if Jira state changes after this checklist was created.

