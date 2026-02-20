"""Tests for golden deterministic regression and simulation datasets.

Closes #5: Testing — add golden deterministic regression fixture + 3 simulation datasets.

These tests verify:
1. Golden fixture: identical input → identical output (byte-for-byte determinism)
2. Simulation datasets: valid input that exercises different consensus scenarios
3. Fixture schema compliance: all fixtures pass input validation
"""

import json
import pathlib

import pytest

from bayesian_engine.core import (
    SCHEMA_VERSION,
    ValidationError,
    compute_consensus,
    validate_input_payload,
)

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_fixture(name: str) -> dict:
    """Load a JSON fixture by filename."""
    path = FIXTURES_DIR / name
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _all_fixture_paths() -> list[pathlib.Path]:
    """Return paths for all .json fixtures."""
    return sorted(FIXTURES_DIR.glob("*.json"))


# ---------------------------------------------------------------------------
# Golden regression: deterministic output
# ---------------------------------------------------------------------------

class TestGoldenRegression:
    """Golden fixture must produce byte-identical output on every run."""

    def test_golden_output_matches_expected(self):
        fixture = _load_fixture("golden_regression.json")
        payload = fixture["input"]
        expected = fixture["expectedOutput"]

        validate_input_payload(payload)
        result = compute_consensus(payload["signals"])

        assert result == expected, (
            f"Golden regression mismatch.\n"
            f"Expected:\n{json.dumps(expected, indent=2)}\n"
            f"Got:\n{json.dumps(result, indent=2)}"
        )

    def test_golden_output_deterministic_across_runs(self):
        """Run compute_consensus 10 times — all results must be identical."""
        fixture = _load_fixture("golden_regression.json")
        signals = fixture["input"]["signals"]

        results = [compute_consensus(signals) for _ in range(10)]
        first = results[0]
        for i, r in enumerate(results[1:], start=2):
            assert r == first, f"Run {i} diverged from run 1"

    def test_golden_fixture_schema_version_matches_code(self):
        fixture = _load_fixture("golden_regression.json")
        assert fixture["input"]["schemaVersion"] == SCHEMA_VERSION
        assert fixture["expectedOutput"]["schemaVersion"] == SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Simulation datasets: input validation + structural checks
# ---------------------------------------------------------------------------

class TestSimulationDatasets:
    """All simulation fixtures must be valid inputs and produce well-formed output."""

    @pytest.fixture(params=[
        "sim_uniform_agreement.json",
        "sim_polarized_split.json",
        "sim_single_outlier.json",
    ])
    def sim_fixture(self, request) -> dict:
        return _load_fixture(request.param)

    def test_fixture_passes_input_validation(self, sim_fixture):
        validate_input_payload(sim_fixture["input"])

    def test_fixture_produces_valid_output(self, sim_fixture):
        result = compute_consensus(sim_fixture["input"]["signals"])

        # Output must include all required schema fields
        assert "schemaVersion" in result
        assert result["schemaVersion"] == SCHEMA_VERSION
        assert "consensus" in result
        assert "confidence" in result
        assert "sourceWeights" in result
        assert "normalization" in result
        assert "diagnostics" in result

    def test_fixture_output_is_json_serializable(self, sim_fixture):
        result = compute_consensus(sim_fixture["input"]["signals"])
        # Must round-trip through JSON without error
        serialized = json.dumps(result)
        deserialized = json.loads(serialized)
        assert deserialized == result

    def test_fixture_deterministic(self, sim_fixture):
        """Same fixture input must produce same output twice."""
        signals = sim_fixture["input"]["signals"]
        a = compute_consensus(signals)
        b = compute_consensus(signals)
        assert a == b


# ---------------------------------------------------------------------------
# Fixture integrity: ensure all fixtures are well-formed
# ---------------------------------------------------------------------------

class TestFixtureIntegrity:
    """Verify fixture files themselves are valid."""

    @pytest.fixture(params=[p.name for p in _all_fixture_paths()])
    def fixture_path(self, request) -> pathlib.Path:
        return FIXTURES_DIR / request.param

    def test_fixture_is_valid_json(self, fixture_path):
        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_fixture_has_description(self, fixture_path):
        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "description" in data, f"Fixture {fixture_path.name} missing 'description'"

    def test_fixture_has_schema_version(self, fixture_path):
        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data.get("schemaVersion") == SCHEMA_VERSION

    def test_fixture_has_input(self, fixture_path):
        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "input" in data, f"Fixture {fixture_path.name} missing 'input'"

    def test_fixture_input_passes_validation(self, fixture_path):
        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        validate_input_payload(data["input"])
