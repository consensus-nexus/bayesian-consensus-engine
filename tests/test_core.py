from bayesian_engine.core import compute_consensus


def test_compute_consensus_placeholder() -> None:
    result = compute_consensus([])
    assert result["schemaVersion"] == "1.0.0"
