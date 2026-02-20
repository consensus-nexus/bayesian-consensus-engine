# Bayesian Engine v0.1 (Consensus Nexus)

Open-source Python tool for Bayesian-weighted consensus from multiple signals with persistent reliability tracking.

## MVP Scope
- Python implementation
- CLI + importable library
- SQLite reliability DB
- JSON input via file or stdin
- Structured JSON output report
- Exponential reliability decay

## Quickstart
```bash
poetry install
poetry run bayesian-engine --help
```

## Input contract (v1.0.0)
Input must include `schemaVersion: "1.0.0"`.

Example:
```json
{
  "schemaVersion": "1.0.0",
  "marketId": "market-1",
  "signals": [
    {"sourceId": "agent-a", "probability": 0.6}
  ]
}
```

Missing or mismatched `schemaVersion` fails validation.

## License
MIT
