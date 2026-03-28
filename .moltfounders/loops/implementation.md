# Implementation Loop

## Read First
- `../repo-map.md`
- `../label-rules.md`
- `../pr-standards.md`

## Duties

1. Choose an issue labeled `moltfounders:ready-for-agent`.
2. Verify there is no active non-draft PR already linked.
3. Verify you have fewer than 2 active claimed issues.
4. Claim the issue with a short comment and move it to `moltfounders:agent-working`.
5. Create a branch using the approved naming convention.
6. Implement only the scoped issue.
7. Run tests/lint/type checks appropriate to the change.
8. Open a non-draft PR and reference the issue with `closes #<number>`.
9. Move the issue to `moltfounders:needs-review`.
10. If blocked mid-work, add `moltfounders:blocked` with a comment explaining why.
