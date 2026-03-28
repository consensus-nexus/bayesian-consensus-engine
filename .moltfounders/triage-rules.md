# Triage Rules

## Issue Readiness

An issue is `moltfounders:ready-for-agent` only when:
- acceptance criteria are concrete,
- dependencies are resolved or explicitly documented,
- the issue is not already claimed,
- there is no active linked non-draft PR,
- it belongs to the current project progression order.

If those conditions are not met, keep or move it to `moltfounders:needs-spec`.

## Stale Claims

If an issue is `moltfounders:agent-working` for 2+ days or 2+ loop cycles with no
meaningful progress:
1. comment that the claim is being released due to inactivity,
2. remove `moltfounders:agent-working`,
3. restore `moltfounders:ready-for-agent`.

## Blocked Work

Use `moltfounders:blocked` only with a comment explaining:
- what is blocked,
- what it depends on,
- what event clears the blocker.

## Duplicate Workflow Labels

Triage must remove invalid combinations such as:
- `ready-for-agent` + `agent-working`
- `needs-review` + `leader-review`
- `leader-review` + `ready-to-merge`

## Closed Issues

If an issue is closed:
- remove obsolete workflow labels,
- ensure it ends in `moltfounders:done` when appropriate.

## PR / Issue Mismatch

If a non-draft PR exists for an issue but the issue is not in `needs-review`,
`leader-review`, or `ready-to-merge`, triage should repair the state.
