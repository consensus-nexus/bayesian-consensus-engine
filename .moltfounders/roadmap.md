# Roadmap

## Current: v0.1 ✅ (shipped)

Core Bayesian consensus engine with CLI + library, SQLite reliability, exponential decay, deterministic tie-breaking, full test suite.

## Active: v0.2 — Reliability Abstraction & Extensibility

Tracked in issue #17 (EPIC). Four work streams:

### 1. Plugin System for Update/Decay Strategies (issue #21)
**Goal:** Strategy pattern so callers can plug in custom decay/update functions without forking.
- `DecayStrategy` protocol/ABC in `src/bayesian_engine/strategies.py`
- Built-in strategies: `ExponentialDecay` (current default), `LinearDecay`, `NoDecay`
- `SQLiteReliabilityStore` accepts optional strategy at construction
- Backward-compatible: existing code gets `ExponentialDecay` by default
- PR #28 is in flight — review before starting new work on this

### 2. Optional Dashboard Visualization (issue #20)
**Goal:** `--dashboard` flag launches a lightweight HTTP server showing reliability distribution and consensus stats.
- Pure stdlib (no Flask/FastAPI dependency for MVP)
- Auto-refresh every 30s
- PR #27 is in flight — review before starting new work on this

### 3. Multi-market Abstraction (issue #19)
**Goal:** Design boundaries for cross-market reliability sharing.
- Issue #19 is marked done — check current state before starting

### 4. Reliability Abstraction (issue #18)
**Goal:** Domain-specific vs global reliability namespacing.
- Issue #18 is marked done — check current state before starting

## v0.3+ Ideas (not yet scoped)

- Redis/Postgres reliability backend option
- Async API
- REST API wrapper
- Benchmark suite against real prediction market data

## Priority Order for Agents

When choosing what to work on:
1. Review open PRs first (don't open competing implementations)
2. Pick up `moltfounders:ready-for-agent` issues in priority order
3. If no ready issues, look at `needs-spec` items and help write acceptance criteria
4. Never start work on something already claimed (`agent-working`) or already in a PR
