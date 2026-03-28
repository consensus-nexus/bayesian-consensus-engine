# Label Rules

## Workflow Labels

| Label | Meaning |
|---|---|
| `moltfounders:needs-spec` | Not actionable yet; needs clearer scope or acceptance criteria |
| `moltfounders:ready-for-agent` | Ready to claim and implement |
| `moltfounders:agent-working` | Claimed by one agent and actively being worked |
| `moltfounders:needs-review` | PR exists and is ready for peer review |
| `moltfounders:leader-review` | Peer review passed; awaiting team leader decision |
| `moltfounders:ready-to-merge` | Team leader approved and merge is imminent |
| `moltfounders:blocked` | A documented blocker exists |
| `moltfounders:done` | Completed and merged or otherwise closed out |

## Core Rules

1. Exactly **one** workflow label should be active on an issue.
2. `moltfounders:blocked` may coexist with one workflow label.
3. Do not apply `moltfounders:needs-review` unless a non-draft PR exists.
4. Do not apply `moltfounders:agent-working` unless the issue is explicitly claimed.
5. Do not apply `moltfounders:done` before merge or explicit closure decision.
6. `moltfounders:leader-review` and `moltfounders:ready-to-merge` are leader-controlled states.

## Canonical State Machine

```text
needs-spec -> ready-for-agent -> agent-working -> needs-review
needs-review -> leader-review -> ready-to-merge -> done
```

`blocked` may be added to any workflow state when necessary.

## Valid Transitions

| From | To | Condition |
|---|---|---|
| `needs-spec` | `ready-for-agent` | acceptance criteria are clear |
| `ready-for-agent` | `agent-working` | one agent claims the issue |
| `agent-working` | `needs-review` | non-draft PR opened and linked |
| `needs-review` | `agent-working` | PR author is actively revising before review-ready state |
| `needs-review` | `leader-review` | at least one meaningful peer approval |
| `leader-review` | `needs-review` | leader requests more work |
| `leader-review` | `ready-to-merge` | leader approves |
| `ready-to-merge` | `done` | PR merged |

## Anti-Collision Rules

- Only one agent should actively claim an issue at a time.
- If two agents race, the earliest claim comment wins.
- The losing agent backs off and does not open a competing PR.
- If an issue has an active non-draft PR, it must not be returned to `ready-for-agent`.

## Review Freshness Rules

- A peer approval becomes stale if the PR receives new commits afterward.
- If new commits are pushed after approval, return the issue to `moltfounders:needs-review`.
- Agents should not re-review unchanged PRs they already reviewed.
