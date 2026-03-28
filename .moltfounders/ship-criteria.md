# Ship Criteria

## MVP Ship Check

Before calling something ready to ship, verify:
- all Must Have scope for the target milestone is complete,
- critical bugs are fixed,
- tests and CI are green,
- documentation for user-facing behavior is updated,
- there is a short launch summary or release note.

## Hardening Instead Of Shipping

Do not ship yet if:
- core flows are still flaky,
- deterministic outputs changed without fixture updates,
- known critical regressions exist,
- CI is red without an explicit emergency exception.

## Pivot Trigger

Escalate to a project-level decision if implementation repeatedly reveals:
- the spec was materially wrong,
- the current architecture is blocking delivery,
- the milestone goal no longer matches user need.
