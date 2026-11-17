# Retry Kit · the Codex build

Three prompts develop the shared starter into a Python retry library. Each chapter records a fresh proposal, its implementation report, and observed checks. The proposals use the installed Design Proposal skill and the user’s [standing authorization to implement](assets/authorization.md).

Recorded checks describe the build session. Descriptions and navigation have been edited for publication. Use the milestone chapters to follow the build.

| Milestone | Reading and evidence |
| --- | --- |
| 1 · Bounded retries | [Proposal, implementation, and report viewer output](01-bounded-retries.md) |
| 2 · Capped backoff | [Capped waits, recovery, and exhaustion](02-capped-backoff.md) |

Run `git log --oneline --reverse starter..HEAD` on the `codex` branch to see the milestones in order. Each commit includes the implementation and its recording. To run an earlier milestone, use `git switch --detach` with the commit ID shown for its subject, then `git switch codex` to return to the completed build.

[Build prompts](../build-prompts.md) · [Milestone commit subjects](assets/checkpoints.json) · [Skill provenance](assets/skill-provenance.json)
