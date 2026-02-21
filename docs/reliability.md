# Reliability Persistence — SQLite Store

## Overview

The reliability module (`src/bayesian_engine/reliability.py`) provides
persistent, per-source, per-market reliability scores backed by SQLite.
These scores feed into the Bayesian consensus computation to weight each
source's contribution.

## Database Schema

A single SQLite database file stores the `sources` table:

```sql
CREATE TABLE IF NOT EXISTS sources (
    source_id   TEXT    NOT NULL,
    market_id   TEXT    NOT NULL,
    reliability REAL    NOT NULL DEFAULT 0.5,
    confidence  REAL    NOT NULL DEFAULT 0.5,
    updated_at  TEXT    NOT NULL,
    PRIMARY KEY (source_id, market_id)
);
```

| Column        | Type  | Description                                        |
|---------------|-------|----------------------------------------------------|
| `source_id`   | TEXT  | Unique identifier for the prediction source/agent  |
| `market_id`   | TEXT  | Market or question the prediction applies to       |
| `reliability` | REAL  | Reliability score in \[0, 1\]                      |
| `confidence`  | REAL  | Confidence in the reliability estimate in \[0, 1\] |
| `updated_at`  | TEXT  | ISO-8601 UTC timestamp of last update              |

The primary key is the composite `(source_id, market_id)`, so each source
has an independent reliability score per market.

## Cold-Start Defaults

When a source has no stored record, the store returns:

| Field         | Default |
|---------------|---------|
| `reliability` |   0.50  |
| `confidence`  |   0.50  |

Cold-start lookups do **not** create database rows; a record is only
persisted after the first `update_reliability()` call.

## API

### `SQLiteReliabilityStore(db_path)`

Constructor.  Pass a file path for persistent storage or `":memory:"` for
an ephemeral in-memory database (useful in tests).

The store can also be used as a context manager:

```python
with SQLiteReliabilityStore("data/reliability.db") as store:
    rec = store.get_reliability("agent-a", "market-1")
```

---

### `get_reliability(source_id, market_id) → ReliabilityRecord`

Retrieve the reliability record for a source in a market.

Returns cold-start defaults if the source has never been recorded.

```python
rec = store.get_reliability("agent-a", "market-1")
print(rec.reliability)  # 0.5 if unseen
```

---

### `update_reliability(source_id, market_id, outcome_correct: bool) → ReliabilityRecord`

Apply a post-outcome Bayesian-style update.

- `outcome_correct=True` → reliability **increases** (source was right)
- `outcome_correct=False` → reliability **decreases** (source was wrong)

**Constraints:**

| Parameter       | Value | Description                                 |
|-----------------|-------|---------------------------------------------|
| `MAX_UPDATE_STEP` | 0.10 | Absolute cap on reliability change per call |

The reliability value is always clamped to \[0, 1\].

Confidence increases with every update (closing 10 % of the gap to 1.0
each time), reflecting that more evidence has been observed.

```python
rec = store.update_reliability("agent-a", "market-1", outcome_correct=True)
print(rec.reliability)  # > 0.5
```

---

### `list_sources(market_id=None) → list[ReliabilityRecord]`

List all stored records, optionally filtered by market.  Results are
sorted by `source_id` (and then `market_id` when unfiltered).

```python
all_sources = store.list_sources()
market_sources = store.list_sources(market_id="market-1")
```

---

### `close()`

Close the underlying SQLite connection.  Also called automatically when
the store is used as a context manager.

## Data Model

### `ReliabilityRecord` (frozen dataclass)

| Field         | Type  | Description                               |
|---------------|-------|-------------------------------------------|
| `source_id`   | str   | Source identifier                         |
| `market_id`   | str   | Market identifier                         |
| `reliability` | float | Current reliability score                 |
| `confidence`  | float | Confidence in the reliability estimate    |
| `updated_at`  | str   | ISO-8601 UTC timestamp (empty for unseen) |

## Integration with Consensus Engine

The `compute_consensus()` function in `core.py` accepts an optional
`source_reliability` dict.  To integrate the reliability store:

```python
from bayesian_engine.core import compute_consensus
from bayesian_engine.reliability import SQLiteReliabilityStore

store = SQLiteReliabilityStore("data/reliability.db")

signals = [
    {"sourceId": "agent-a", "probability": 0.7},
    {"sourceId": "agent-b", "probability": 0.4},
]

# Build reliability dict from store
source_reliability = {}
for sig in signals:
    rec = store.get_reliability(sig["sourceId"], "market-1")
    source_reliability[sig["sourceId"]] = {
        "reliability": rec.reliability,
        "confidence": rec.confidence,
    }

result = compute_consensus(signals, source_reliability=source_reliability)
```
