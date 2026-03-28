# PR Review Standards

## The 2-Approval Rule

A PR advances to `leader-review` only when ALL of:
- ✅ 2 distinct GitHub approvals (not from the PR author)
- ✅ CI is green (ruff + mypy + pytest all pass)
- ✅ No unresolved merge conflicts
- ✅ Branch is up to date with main

The Merge Prep loop enforces this before applying `leader-review`.

## Self-Review Block

**Never review your own PR.** If you are the PR author, skip it entirely.

## What to Check in a Review

### 1. Correctness
- Does the implementation match the acceptance criteria in the linked issue?
- Are edge cases handled? (empty inputs, boundary values, invalid types)
- For math changes: verify the formula against the PRD/architecture

### 2. Tests
- Are new behaviors covered by tests?
- Do existing tests still pass? (trust CI, but also read the test changes)
- Golden fixtures untouched? (`test_golden_fixtures.py` — if modified, flag immediately)
- Dry-run behavior tested if the feature touches DB writes?

### 3. Code Quality
- Constants from `config.py`, not hardcoded?
- Type annotations on all public functions?
- Docstrings on all public functions?
- Module not growing too large (>150 lines is a smell)?
- No new runtime dependencies snuck in?

### 4. Scope
- Is the PR focused on one concern?
- Any drive-by refactors that aren't in scope? (not a blocker, but note them)
- Diff size reasonable (<300 lines excluding tests)?

### 5. Breaking Changes
- Does this change the public JSON schema? (needs version bump)
- Does this change `config.py` constants? (needs explicit issue)
- Does this change the `compute_consensus` or `validate_input_payload` signature?

## How to Write a Review

Be specific. Minimum per review:
- State whether you approve or request changes
- For each issue: exact location + what's wrong + how to fix
- For approval: call out specifically what you verified (e.g. "Ran through edge cases for empty signals, tested dry-run flag, golden fixtures untouched")

No single-line approvals like "LGTM" — at minimum: "LGTM — verified X, Y, Z."

## After Reviewing

- If approving: leave GitHub "Approve" review + detailed comment
- If requesting changes: leave GitHub "Request Changes" review + specifics
- Do NOT advance to `leader-review` yourself — that's Merge Prep loop's job
- Do NOT merge — that's the maintainer's job

## Competing PRs

If two PRs address the same issue (e.g. #24 and #28 both tackle plugin system):
- Flag this in both PRs as a comment
- Apply `needs-human` label to both
- Do not advance either to `leader-review` until the maintainer picks one
- Suggest which one is better if you have a clear opinion

## CI Failures

If CI is red on a PR:
- Do not approve
- Leave a comment identifying what's failing
- If you can see the fix: suggest it clearly
- Apply `blocked` label if the author needs to fix it before review can proceed
