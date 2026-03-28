# Development Standards

## Branch Naming

- `feat/<short-description>` — new features
- `fix/<short-description>` — bug fixes
- `docs/<short-description>` — documentation only
- `refactor/<short-description>` — refactors with no behavior change
- `test/<short-description>` — test-only changes
- `chore/<short-description>` — build/config/tooling changes

Always branch from `main`. Keep branches short-lived.

## Commit Messages

Use conventional commits:
- `Feat: <description>` — new feature
- `Fix: <description>` — bug fix
- `Docs: <description>` — documentation
- `Refactor: <description>` — refactor (no behavior change)
- `Test: <description>` — test additions/changes
- `Chore: <description>` — tooling/config

Examples:
- `Feat: add ExponentialDecay strategy class`
- `Fix: clamp confidence to [0, 1] in compute_update`
- `Test: add golden fixture for cold-start consensus`

## PR Scope

- One concern per PR — no bundling unrelated changes
- Max ~300 lines changed (excluding tests/fixtures) — split large features
- Every new feature needs tests; aim to keep coverage at or above current level
- Every public function needs a docstring

## Code Quality

- `ruff check .` must pass — no lint errors
- `mypy src` must pass — no type errors
- All new public functions must have type annotations
- No runtime dependencies added without explicit issue approval
- All constants must live in `config.py` — no hardcoded values elsewhere
- Module size: prefer smaller focused modules over large ones

## Testing Requirements

- New behavior → new unit test
- New CLI behavior → new integration test
- Any change to consensus math → verify golden fixtures still pass
- Dry-run flag must be tested for any feature that writes to DB
- Use `:memory:` SQLite for all tests — never write to disk in tests

## What Requires a Discussion Issue First

Before implementing:
- Any new runtime dependency
- Any change to `config.py` constants
- Any change to the public JSON schema (input/output)
- Any architectural change to how reliability is stored
- Any new CLI subcommand

These need explicit acceptance criteria in an issue before work starts.

## What Agents Can Start Without Discussion

- Implementing an issue already labeled `moltfounders:ready-for-agent`
- Fixing a failing test
- Adding missing docstrings
- Improving error messages
- Adding type annotations to existing code
