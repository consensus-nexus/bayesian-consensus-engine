# PR Standards

## Scope

- One concern per PR where practical.
- If a PR grows too large, split it unless the dependency chain makes that worse.
- Repo-setup / workflow PRs may bundle closely related docs and config.

## Quality Bar Before Review

Before moving an issue to `moltfounders:needs-review`:
- tests should pass locally where practical,
- lint should pass,
- type checking should pass if touched code is type-checked,
- the PR must explain what changed and why,
- the linked issue must be referenced with `closes #<number>` if applicable.

## Review Quality

A valid review must include:
- at least one specific observation,
- a clear decision (`approve` or `request changes`),
- mention of tests/CI status or explicit note that they were not run.

Single-word approvals are not sufficient.

## Self-Review

- You may inspect your own PR before submitting it.
- You may not count your own review as peer review.
- You may not advance your own PR to `leader-review` by self-approval.

## Re-Review Rules

Do not review the same unchanged PR repeatedly.

Review again only if:
- new commits were pushed since your last review,
- the leader explicitly requests another look,
- your earlier review was incomplete and not a formal decision.

## Merge Preconditions

A PR is merge-ready only when:
- peer review is meaningful and current,
- approvals are not stale,
- CI is green or an explicit leader-documented exception exists,
- merge conflicts are resolved,
- scope still matches the linked issue.
