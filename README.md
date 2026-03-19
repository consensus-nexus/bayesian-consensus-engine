# Bayesian Consensus Engine

Open-source Python tool for Bayesian-weighted consensus from multiple signals with persistent reliability tracking.

## Features

- **Bayesian-weighted consensus**: Combines predictions from multiple sources weighted by reliability
- **Persistent reliability tracking**: SQLite-backed storage for source reliability scores
- **Exponential decay**: Reliability scores decay over time toward a floor value
- **CLI + library**: Use from command line or import as Python module
- **Dry-run mode**: Compute consensus without database writes
- **Deterministic tie-breaking**: Resolves conflicting predictions with a clear hierarchy

## Installation

```bash
# Using poetry (recommended)
poetry install

# Using pip
pip install bayesian-consensus-engine
```

## Quick Start

### CLI Usage

```bash
# Basic consensus computation
poetry run bayesian-engine --input signals.json

# Dry-run mode (no DB writes)
poetry run bayesian-engine --input signals.json --dry-run

# Pipe via stdin
cat signals.json | poetry run bayesian-engine
```

### Python Library

```python
from bayesian_engine.core import compute_consensus, validate_input_payload

# Prepare signals
payload = {
    "schemaVersion": "1.0.0",
    "marketId": "market-1",
    "signals": [
        {"sourceId": "agent-a", "probability": 0.6},
        {"sourceId": "agent-b", "probability": 0.8},
    ]
}

# Validate and compute
validate_input_payload(payload)
result = compute_consensus(payload["signals"])
print(f"Consensus: {result['consensus']:.2%}")
```

## Input Format

Input must be valid JSON with the following structure:

```json
{
  "schemaVersion": "1.0.0",
  "marketId": "your-market-id",
  "signals": [
    {"sourceId": "source-1", "probability": 0.7},
    {"sourceId": "source-2", "probability": 0.5}
  ]
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `schemaVersion` | string | Must be `"1.0.0"` |
| `marketId` | string | Unique identifier for the market/question |
| `signals` | array | List of signal objects |

### Signal Object

| Field | Type | Description |
|-------|------|-------------|
| `sourceId` | string | Unique identifier for the source |
| `probability` | number | Predicted probability in [0, 1] |

## Output Format

```json
{
  "schemaVersion": "1.0.0",
  "consensus": 0.68,
  "confidence": 0.35,
  "sourceWeights": [
    {"sourceId": "agent-a", "weight": 0.5, "normalizedWeight": 0.5},
    {"sourceId": "agent-b", "weight": 0.5, "normalizedWeight": 0.5}
  ],
  "normalization": {
    "totalWeight": 1.0,
    "sourceCount": 2
  },
  "diagnostics": {
    "status": "computed",
    "sources": 2,
    "uniqueSources": 2,
    "coldStartSources": ["agent-a", "agent-b"]
  }
}
```

## Reliability System

### Cold-Start Defaults

New sources start with:
- **Reliability**: 0.50 (50%)
- **Confidence**: 0.25 (25%)

### Post-Outcome Updates

After an outcome is known, update source reliability:

```python
from bayesian_engine.reliability import SQLiteReliabilityStore

store = SQLiteReliabilityStore("reliability.db")

# Source was correct
store.update_reliability("agent-a", "market-1", outcome_correct=True)

# Source was wrong
store.update_reliability("agent-b", "market-1", outcome_correct=False)
```

### Exponential Decay

Reliability decays over time toward a floor (default 0.10):

- **Half-life**: 30 days
- **Minimum floor**: 0.10 (10%)

After 30 days without updates, reliability is halfway to the floor.

## Configuration

Default values can be modified in `bayesian_engine/config.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `DEFAULT_RELIABILITY` | 0.50 | Cold-start reliability |
| `DEFAULT_CONFIDENCE` | 0.25 | Cold-start confidence |
| `MAX_UPDATE_STEP` | 0.10 | Max single-step reliability change |
| `DECAY_HALF_LIFE_DAYS` | 30 | Days until reliability decays by half |
| `DECAY_MINIMUM` | 0.10 | Floor reliability never decays below |

## Examples

See the `examples/` directory for more usage examples:

- `basic_consensus.py` - Simple consensus computation
- `reliability_tracking.py` - Persistent reliability storage
- `tie_breaking.py` - Handling conflicting predictions

## Development

```bash
# Install dev dependencies
poetry install --with dev

# Run tests
poetry run pytest

# Run linting
poetry run ruff check src/
```

## License

MIT License - see [LICENSE](LICENSE) for details.
