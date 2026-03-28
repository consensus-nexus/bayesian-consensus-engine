# Architecture

## Module Map

```
src/bayesian_engine/
├── config.py              # All constants (cold-start defaults, decay params, schema version)
├── core.py                # compute_consensus(), validate_input_payload()
├── reliability.py         # SQLiteReliabilityStore, ReliabilityRecord
├── decay.py               # apply_reliability_decay(), days_since_update()
├── tiebreak.py            # DeterministicTieBreaker, AgentSignal
├── cli.py                 # CLI entrypoint (bayesian-engine command)
├── market.py              # Multi-market abstractions (v0.2)
├── reliability_abstraction.py  # Domain/global reliability layers (v0.2)
└── __init__.py
```

## Key Design Decisions

### Single Config Module
All constants live in `config.py`. Never hardcode values in other modules — always import from config. This includes `DEFAULT_RELIABILITY`, `MAX_UPDATE_STEP`, `DECAY_HALF_LIFE_DAYS`, `SCHEMA_VERSION`, etc.

### Deterministic Everything
- All consensus computation must be deterministic for identical inputs + DB state
- Tie-breaking uses a fixed hierarchy: weight density → max reliability → smallest prediction value (lexicographic on source ID)
- Tests include golden fixture regression (`test_golden_fixtures.py`) — do NOT break it

### Immutable Records
`ReliabilityRecord` is a frozen dataclass. Never mutate reliability state in-place.

### Schema Versioning
Input/output JSON always includes `schemaVersion: "1.0.0"`. This is a strict contract. Any breaking change to the schema requires a version bump and migration path.

### Dry-Run First
The `--dry-run` / `dry_run=True` flag must be respected everywhere. No DB writes in dry-run mode, ever.

### No External Runtime Dependencies
v0.1 has zero runtime dependencies beyond Python stdlib. New features must not add runtime deps unless explicitly approved in an issue. Dev dependencies (pytest, ruff, mypy) are fine.

## Test Layout

```
tests/
├── test_config.py              # Config constants validation
├── test_core.py                # compute_consensus() unit tests
├── test_decay.py               # Decay function tests
├── test_dry_run.py             # Dry-run mode correctness
├── test_golden_fixtures.py     # Deterministic regression (DO NOT BREAK)
├── test_integration.py         # End-to-end CLI + store integration
├── test_multi_market.py        # Multi-market scenarios
├── test_reliability.py         # SQLiteReliabilityStore unit tests
├── test_reliability_abstraction.py
├── test_simulation.py          # Simulation over many rounds
├── test_tiebreak.py            # Tie-breaking correctness
└── fixtures/                   # Golden JSON fixtures
```

## CI Requirements

CI runs on every push and PR:
- `ruff check .` — lint (must pass)
- `mypy src` — type check (must pass)  
- `pytest` — all tests (must pass)

A PR with red CI must not be approved or advanced to `leader-review`.

## What NOT to Touch Without a Discussion Issue

- `config.py` constants — changes affect all behavior globally
- `test_golden_fixtures.py` — changing expected outputs invalidates regression safety
- `pyproject.toml` runtime dependencies — no new deps without explicit approval
- Public API in `core.py` (`compute_consensus`, `validate_input_payload`) — breaking changes need schema version bump
