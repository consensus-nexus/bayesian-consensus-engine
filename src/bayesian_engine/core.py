"""Core consensus calculations."""

from __future__ import annotations

from typing import Any

from bayesian_engine.config import (
    DEFAULT_RELIABILITY,
    DEFAULT_CONFIDENCE,
    SCHEMA_VERSION,
)


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


def compute_consensus(
    signals: list[dict[str, Any]],
    source_reliability: dict[str, dict[str, float]] | None = None,
) -> dict[str, Any]:
    """Compute Bayesian-weighted consensus from multiple signals.

    Args:
        signals: List of signal dicts, each with sourceId and probability
        source_reliability: Optional dict mapping sourceId to {reliability, confidence}
                          If None, uses cold-start defaults for all sources

    Returns:
        Dict with schemaVersion, consensus, confidence, sourceWeights,
        normalization, and diagnostics

    The consensus is computed as a reliability-weighted average of signal
    probabilities. Sources are weighted by their reliability scores.

    Example:
        >>> signals = [
        ...     {"sourceId": "agent-a", "probability": 0.6},
        ...     {"sourceId": "agent-b", "probability": 0.8},
        ... ]
        >>> result = compute_consensus(signals)
    """
    if not signals:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "consensus": None,
            "confidence": 0.0,
            "sourceWeights": [],
            "normalization": {"totalWeight": 0.0, "sourceCount": 0},
            "diagnostics": {"status": "no_signals", "sources": 0},
        }

    # Use cold-start defaults if no reliability data provided
    if source_reliability is None:
        source_reliability = {}

    # Extract source IDs for sorting (deterministic ordering)
    source_ids = sorted({s["sourceId"] for s in signals})

    # Gather reliability for each source (default to cold-start)
    source_data = []
    total_weight = 0.0
    for sid in source_ids:
        # Get reliability from DB or use cold-start default
        rel_data = source_reliability.get(sid, {})
        reliability = rel_data.get("reliability", DEFAULT_RELIABILITY)
        confidence = rel_data.get("confidence", DEFAULT_CONFIDENCE)

        # Get signals from this source
        source_signals = [s for s in signals if s["sourceId"] == sid]
        avg_prob = sum(s["probability"] for s in source_signals) / len(source_signals)

        # Weight by reliability
        weight = reliability
        total_weight += weight

        source_data.append({
            "sourceId": sid,
            "probability": avg_prob,
            "reliability": reliability,
            "confidence": confidence,
            "weight": weight,
        })

    # Compute weighted consensus
    if total_weight == 0:
        consensus = None
        final_confidence = 0.0
    else:
        weighted_sum = sum(
            sd["probability"] * sd["weight"] for sd in source_data
        )
        consensus = weighted_sum / total_weight

        # Overall confidence is weighted average of source confidences
        confidence_sum = sum(
            sd["confidence"] * sd["weight"] for sd in source_data
        )
        final_confidence = confidence_sum / total_weight

    # Build source weights list (deterministic order by sourceId)
    source_weights = [
        {
            "sourceId": sd["sourceId"],
            "weight": sd["weight"],
            "normalizedWeight": sd["weight"] / total_weight if total_weight > 0 else 0.0,
        }
        for sd in source_data
    ]

    # Build normalization info
    normalization = {
        "totalWeight": total_weight,
        "sourceCount": len(source_ids),
    }

    # Build diagnostics
    diagnostics = {
        "status": "computed",
        "sources": len(signals),
        "uniqueSources": len(source_ids),
        "coldStartSources": [
            sd["sourceId"] for sd in source_data
            if sd["sourceId"] not in source_reliability
        ],
    }

    return {
        "schemaVersion": SCHEMA_VERSION,
        "consensus": consensus,
        "confidence": final_confidence,
        "sourceWeights": source_weights,
        "normalization": normalization,
        "diagnostics": diagnostics,
    }