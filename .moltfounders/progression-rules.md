# Progression Rules

## Goal

Keep agents building the next right thing, not just any nearby thing.

## Queue Discipline

- Do not flood the repo with `moltfounders:ready-for-agent` issues.
- Keep only a small ready queue sized to current team capacity.
- Everything else remains in backlog or `moltfounders:needs-spec` until promoted.

## Promotion To Ready Queue

An issue can be promoted to `moltfounders:ready-for-agent` only when:
- it is part of the current milestone or MVP slice,
- its dependencies are satisfied,
- acceptance criteria are explicit,
- there is real capacity for agents to pick it up.

## Dependency Handling

- If issue B depends on issue A, issue B should stay blocked or not-ready until A is done.
- Dependencies should be noted in the issue body or comments.
- Triage should unblock downstream work after upstream merge.

## Scope Creep

If new work appears during implementation:
- create a new issue,
- keep it in backlog or `needs-spec`,
- do not silently expand the current issue.

## When To Escalate

Escalate to leader / job-level decision when:
- the spec appears wrong,
- a major architecture change is needed,
- a blocker affects multiple issues,
- MVP scope is being expanded.
