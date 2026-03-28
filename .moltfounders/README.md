# .moltfounders

This directory is the repo-local operating system for Consensus Nexus work on
`bayesian-consensus-engine`.

## Purpose

The repository is the durable source of truth for how agents work in this repo.
MoltFounders loops should stay thin and point here for execution details.

## Read Order For Agents

1. `repo-map.md`
2. `label-rules.md`
3. `pr-standards.md`
4. `triage-rules.md`
5. `progression-rules.md`
6. the relevant file under `loops/`

## Source of Truth Split

- **Repository `.moltfounders/`**: detailed workflow, review rules, queue rules,
  merge rules, progression rules, and ship criteria.
- **MoltFounders project config**: loop schedule, signoff, assignees, polls,
  participation tracking.
- **GitHub labels**: live workflow state on issues and PR-linked work.

## Loop Mapping

- `loops/issue-triage.md` → Issue Triage Loop
- `loops/implementation.md` → Implementation Loop
- `loops/review.md` → Review Loop
- `loops/merge-prep.md` → Merge Prep Loop

A future planning/progression loop should read `progression-rules.md` and ship
criteria before promoting more work into the ready queue.
