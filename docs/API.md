# API (Draft)

## Schema Contracts (v1.0.0)

This project uses strict JSON schema contracts for both input and output.

- Input schema: `docs/schema-input-v1.0.0.json`
- Output schema: `docs/schema-output-v1.0.0.json`

### Required versioning field

Both input and output require:

```json
{"schemaVersion": "1.0.0"}
```

Requests/responses without `schemaVersion` or with a mismatched version must fail validation.

### Validation error guidance (examples)

1. Missing `schemaVersion`
   - Error: `schemaVersion is required`
2. Probability outside range
   - Error: `signals[i].probability must be between 0 and 1`
3. Unknown top-level fields
   - Error: `additional properties are not allowed`

These contracts are the compatibility baseline for v0.1.
