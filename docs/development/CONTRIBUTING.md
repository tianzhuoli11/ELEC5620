# Branches and collaboration

`main` holds integrated code and the shared structure. Develop on your named branch. Branch names do not grant access; pushing still requires repository write permission.

| Member | Branch |
| --- | --- |
| Yuanbo Zhang | `yuanbo-zhang` |
| Yang Yang | `yang-yang` |
| Jinjing Huang | `jinjing-huang` |
| Yan Li | `yan-li` |
| Tianzhuo Li | `tianzhuo-li` |

## Synchronise before development

Commit or safely save local changes first, then:

```bash
git fetch origin
git switch jinjing-huang
git merge origin/main
```

Replace the branch name for other members. If no local branch exists yet, use `git switch --track origin/jinjing-huang`. Resolve conflicts and verify the result; do not force-push over teammates' changes.

Personal branches do not automatically follow later changes to main. Synchronise regularly.

## Commits and Pull Requests

Stage only intended files. Reference the Jira issue, for example `SCRUM-20: add shared event simulator`. Push to your branch, open a PR targeting `main`, explain the changes, validation and limitations, and ask at least one teammate to review before merging.

Agree shared types and public interfaces before changing them. Ask the relevant owner to review edits to another domain. Mark Jira Done only after runnable implementation, acceptance checks and actual evidence. Do not commit credentials, personal data or fabricated meeting/test records.
