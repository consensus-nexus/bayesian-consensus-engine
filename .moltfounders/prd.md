# PRD — Bayesian Engine v0.1 (Consensus Nexus)

## 1) Overview
Bayesian Engine is an open-source Python project that computes weighted consensus from multiple signals while persisting per-source reliability over time.

## 2) Goal
Ship a Week-1 practical MVP that is:
- usable by CLI users immediately,
- importable as a Python library,
- deterministic and testable,
- extensible for v0.2.

## 3) Non-Goals (v0.1)
- No web dashboard
- No distributed reliability store (Redis, etc.)
- No full multi-market implementation
- No external runtime services required

## 4) Team Decisions Incorporated
- Language: Python
- Packaging: Poetry
- Product shape: CLI + library
- Reliability DB: SQLite
- Input: JSON file + stdin
- Output: structured JSON report
- Decay: exponential
- License: MIT
- CI: GitHub Actions + pre-commit
- Testing baseline: unit + integration + simulation

## 5) Key Reviewer Notes Applied
From latest PRD review responses:
1. **Cold-start defaults must be explicit**
2. **Schema versioning required** for input/output compatibility
3. **Deterministic tie-breaking policy** required for conflicting signals
4. Optional trust feature: **`--dry-run` mode** (compute without DB writes)

These are now part of MVP requirements.

## 6) User Stories
- As a developer, I can get consensus + confidence from multiple signals.
- As an operator, I can persist and update source reliability across runs.
- As a CLI user, I can run from file or stdin with clear validation errors.
- As an integrator, I can import a Python API from `bayesian_engine`.

## 7) Functional Requirements
### A. Core Consensus Engine
- Accept priors, source probabilities, and optional source base reliability.
- Compute Bayesian-weighted consensus output.
- Return confidence metrics and diagnostic fields.

### B. Reliability System
- Persist reliability in SQLite.
- Apply post-outcome updates with capped update step.
- Apply exponential decay over time.
- Use deterministic cold-start defaults for unseen sources.

### C. Input Contract
- Accept JSON from file (`--input`) or stdin.
- Enforce strict schema validation.
- Include required `schemaVersion`.

### D. Output Contract
Output JSON must include:
- `schemaVersion`
- `consensus`
- `confidence`
- `sourceWeights`
- `normalization`
- `diagnostics`

### E. CLI + Library Interface
- CLI command: `bayesian-engine`
- Library import path: `bayesian_engine`
- Include `--dry-run` flag to avoid DB writes during inspection/testing.

## 8) Determinism Policy
When weighted outcomes tie or are numerically equivalent within tolerance:
- Apply fixed deterministic ordering by source id (lexicographic), then
- deterministic aggregation step,
- and emit tie metadata in diagnostics.

## 9) Cold-Start Defaults (v0.1)
- `default_reliability = 0.50`
- `default_confidence = 0.25`
- `max_update_step = 0.10`
These constants must live in one config module and be documented.

## 10) Repository Skeleton
- `src/bayesian_engine/{core.py,reliability.py,decay.py,cli.py}`
- `tests/{test_core.py,test_integration.py,test_simulation.py}`
- `docs/`, `examples/`
- `.github/workflows/ci.yml`
- `pyproject.toml`, `.pre-commit-config.yaml`, `LICENSE`

## 11) Quality Requirements
- Deterministic output for identical inputs + DB state
- Actionable validation errors
- CI required for lint + typing + tests
- Golden regression fixture for deterministic output

## 12) Success Metrics (v0.1)
- End-to-end CLI run with <60s setup
- CI green on all required checks
- >=3 example datasets validated in simulations
- Stable documented schema for input/output

## 13) Milestones
1. Scaffold repo, packaging, CI
2. Core Bayesian consensus engine
3. Reliability store + decay
4. CLI and library API
5. Unit/integration/simulation tests
6. Docs, examples, first tag (`v0.1.0`)

## 14) Open Questions (v0.2)
- Domain-specific vs global reliability
- Multi-market abstraction boundaries
- Optional dashboard visualization
- Plugin system for update/decay strategies
