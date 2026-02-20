from bayesian_engine.core import SCHEMA_VERSION, ValidationError, compute_consensus, validate_input_payload


def _valid_payload() -> dict:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "marketId": "market-1",
        "signals": [
            {"sourceId": "agent-a", "probability": 0.6},
            {"sourceId": "agent-b", "probability": 0.4},
        ],
    }


def test_compute_consensus_output_schema_version() -> None:
    result = compute_consensus([])
    assert result["schemaVersion"] == SCHEMA_VERSION


def test_validate_input_payload_accepts_valid_schema() -> None:
    validate_input_payload(_valid_payload())


def test_validate_input_payload_requires_schema_version() -> None:
    payload = _valid_payload()
    payload.pop("schemaVersion")

    try:
        validate_input_payload(payload)
        assert False, "expected ValidationError"
    except ValidationError as exc:
        assert str(exc) == "schemaVersion is required"


def test_validate_input_payload_rejects_schema_mismatch() -> None:
    payload = _valid_payload()
    payload["schemaVersion"] = "2.0.0"

    try:
        validate_input_payload(payload)
        assert False, "expected ValidationError"
    except ValidationError as exc:
        assert "schemaVersion must be" in str(exc)


def test_validate_input_payload_rejects_probability_out_of_range() -> None:
    payload = _valid_payload()
    payload["signals"][0]["probability"] = 1.2

    try:
        validate_input_payload(payload)
        assert False, "expected ValidationError"
    except ValidationError as exc:
        assert "must be between 0 and 1" in str(exc)
