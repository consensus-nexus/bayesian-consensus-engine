"""Tests for config module constants."""

from bayesian_engine.config import (
    DEFAULT_RELIABILITY,
    DEFAULT_CONFIDENCE,
    MAX_UPDATE_STEP,
    TIE_TOLERANCE,
    DECAY_HALF_LIFE_DAYS,
    DECAY_MINIMUM,
    SCHEMA_VERSION,
    MIN_SOURCE_ID_LENGTH,
    MAX_SOURCE_ID_LENGTH,
    MAX_SIGNALS_PER_REQUEST,
)


class TestColdStartDefaults:
    """Test cold-start default values from PRD §9."""

    def test_default_reliability_is_50_percent(self):
        """Cold-start reliability should be 50% (neutral prior)."""
        assert DEFAULT_RELIABILITY == 0.50

    def test_default_confidence_is_25_percent(self):
        """Cold-start confidence should be 25% (low certainty)."""
        assert DEFAULT_CONFIDENCE == 0.25

    def test_defaults_are_valid_probabilities(self):
        """All probability-like defaults should be in [0, 1]."""
        assert 0.0 <= DEFAULT_RELIABILITY <= 1.0
        assert 0.0 <= DEFAULT_CONFIDENCE <= 1.0


class TestUpdateConstraints:
    """Test reliability update constraints from PRD §9."""

    def test_max_update_step_is_10_percent(self):
        """Maximum single-step reliability change should be 10%."""
        assert MAX_UPDATE_STEP == 0.10

    def test_max_update_step_is_positive(self):
        """Max update step should be positive."""
        assert MAX_UPDATE_STEP > 0


class TestTieBreaking:
    """Test tie-breaking configuration from PRD §8."""

    def test_tie_tolerance_is_small(self):
        """Tie tolerance should be very small (float comparison epsilon)."""
        assert TIE_TOLERANCE == 1e-9

    def test_tie_tolerance_is_positive(self):
        """Tie tolerance should be positive."""
        assert TIE_TOLERANCE > 0


class TestDecayConfiguration:
    """Test decay configuration from PRD §7."""

    def test_decay_half_life_is_30_days(self):
        """Decay half-life should be 30 days."""
        assert DECAY_HALF_LIFE_DAYS == 30

    def test_decay_minimum_is_10_percent(self):
        """Floor reliability should be 10%."""
        assert DECAY_MINIMUM == 0.10

    def test_decay_minimum_is_less_than_default(self):
        """Decay minimum should be below cold-start default."""
        assert DECAY_MINIMUM < DEFAULT_RELIABILITY


class TestSchemaVersion:
    """Test schema versioning."""

    def test_schema_version_is_v1(self):
        """Schema version should be 1.0.0."""
        assert SCHEMA_VERSION == "1.0.0"

    def test_schema_version_is_string(self):
        """Schema version should be a string."""
        assert isinstance(SCHEMA_VERSION, str)


class TestValidationLimits:
    """Test validation limit constants."""

    def test_min_source_id_length_is_1(self):
        """Minimum source ID length should be 1."""
        assert MIN_SOURCE_ID_LENGTH == 1

    def test_max_source_id_length_is_reasonable(self):
        """Maximum source ID length should be reasonable."""
        assert MAX_SOURCE_ID_LENGTH == 256

    def test_max_signals_per_request_is_reasonable(self):
        """Maximum signals per request should be reasonable."""
        assert MAX_SIGNALS_PER_REQUEST == 1000

    def test_validation_limits_are_ordered(self):
        """Min should be less than max."""
        assert MIN_SOURCE_ID_LENGTH < MAX_SOURCE_ID_LENGTH
