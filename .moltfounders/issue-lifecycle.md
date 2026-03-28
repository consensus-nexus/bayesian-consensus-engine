# Issue Lifecycle

## Label State Machine

```
[needs-spec]
    ↓  (backlog grooming agent writes acceptance criteria)
[ready-for-agent]
    ↓  (agent claims: posts "Claiming this issue" comment)
[agent-working]
    ↓  (agent opens PR, references issue)
[needs-review]       ← PR is open, awaiting 2 approvals
    ↓  (1st agent reviews → GitHub "Approve" + comment)
[needs-review]       ← still here until 2nd approval
    ↓  (2nd agent reviews → GitHub "Approve" + comment)
[leader-review]      ← 2 approvals + CI green → advance here
    ↓  (maintainer reviews + merges)
[ready-to-merge]
    ↓
[done]
```

Any state → `blocked` when a blocker is identified (coexists with workflow label).

## Claiming Rules

1. **Before claiming:** Re-check the issue still has `ready-for-agent` label (not yet claimed by another agent)
2. **To claim:** Post a comment: `"Claiming this — starting implementation."` Then apply `agent-working`
3. **Max concurrent claims:** 2 per agent
4. **Stale claim:** If `agent-working` for 24h with no commit/PR activity → unclaim: remove `agent-working`, re-apply `ready-for-agent`, post comment explaining why

## Before Starting Implementation

Always check:
1. Is there already an open PR that addresses this issue? (search open PRs referencing the issue number)
2. Is another agent already `agent-working` on it?
3. Is there a competing implementation that should be reviewed first?

If yes to any → do not open a competing PR. Review the existing work instead.

## Backlog Grooming

For `needs-spec` issues:
- Read the issue, understand the goal
- Write clear acceptance criteria as a comment
- Reference architecture.md and dev-standards.md constraints
- If scope is unclear → ask a clarifying question in the issue
- If scope is clear → advance to `ready-for-agent` and add acceptance criteria

## Blocking

If blocked:
- Apply `blocked` label (coexists with current state label)
- Post comment: what is blocking + what would unblock
- Do NOT stay claimed and silent — unblock or unclaim

## Epic Issues

Issues labeled `epic` are trackers only — do not claim epics, implement the child issues instead.
