"""Core consensus calculations."""

from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "1.0.0"


class ValidationError(ValueError):
    """Raised when input payload fails schema validation."""


def _require(payload: dict[str, Any], key: str) -> Any:
    if key not in payload:
        raise ValidationError(f"{key} is required")
    return payload[key]


def validate_input_payload(payload: dict[str, Any]) -> None:
    """Validate minimum v1.0.0 input contract.

    This enforces strict compatibility requirements from the PRD:
    - schemaVersion is required and must equal 1.0.0
    - marketId is required and must be a non-empty string
    - signals is required and must be an array
    - each signal must include sourceId and probability in [0, 1]
    """

    schema_version = _require(payload, "schemaVersion")
    if schema_version != SCHEMA_VERSION:
        raise ValidationError(
            f"schemaVersion must be '{SCHEMA_VERSION}' (got '{schema_version}')"
        )

    market_id = _require(payload, "marketId")
    if not isinstance(market_id, str) or not market_id.strip():
        raise ValidationError("marketId must be a non-empty string")

    signals = _require(payload, "signals")
    if not isinstance(signals, list):
        raise ValidationError("signals must be an array")

    for idx, signal in enumerate(signals):
        if not isinstance(signal, dict):
            raise ValidationError(f"signals[{idx}] must be an object")

        source_id = _require(signal, "sourceId")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValidationError(f"signals[{idx}].sourceId must be a non-empty string")

        probability = _require(signal, "probability")
        if not isinstance(probability, (int, float)):
            raise ValidationError(f"signals[{idx}].probability must be a number")
        if probability < 0 or probability > 1:
            raise ValidationError(f"signals[{idx}].probability must be between 0 and 1")


def compute_consensus(signals: list[dict[str, Any]]) -> dict[str, Any]:
    """Placeholder consensus implementation with schema-stable output."""
    return {
        "schemaVersion": SCHEMA_VERSION,
        "consensus": None,
        "confidence": None,
        "sourceWeights": [],
        "normalization": {},
        "diagnostics": {"status": "TODO", "sources": len(signals)},
    }
