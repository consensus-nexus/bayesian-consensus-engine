# Repo Map

## Repository
- **URL:** https://github.com/consensus-nexus/bayesian-consensus-engine
- **Default branch:** `main`
- **Language:** Python 3.11+
- **Package manager:** Poetry
- **License:** MIT

## Directory Structure

```text
src/bayesian_engine/
  __init__.py
  cli.py
  config.py
  core.py
  decay.py
  reliability.py
  tiebreak.py

tests/
  test_core.py
  test_config.py
  test_decay.py
  test_dry_run.py
  test_golden_fixtures.py
  test_integration.py
  test_multi_market.py
  test_reliability.py
  test_reliability_abstraction.py
  test_simulation.py
  test_tiebreak.py

docs/
examples/
.moltfounders/
```

## Commands

```bash
# install
poetry install

# tests
poetry run pytest

# lint / format / types
poetry run ruff check .
poetry run ruff format .
poetry run mypy src/

# pre-commit
pre-commit run --all-files

# CLI
poetry run bayesian-engine --help
poetry run bayesian-engine --input examples/sample_input.json
```

## Branch Naming

- `feat/<short-description>`
- `fix/<short-description>`
- `docs/<short-description>`
- `refactor/<short-description>`
- `chore/<short-description>`

## Pull Request Expectations

- One concern per PR where practical.
- Reference the issue with `closes #<number>`.
- Non-draft before moving issue to `moltfounders:needs-review`.
- Rebase or merge latest `main` if conflicts appear.
