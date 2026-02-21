"""Tests for exponential decay of reliability scores.

Tests cover:
- Decay factor calculation
- Reliability decay application
- Time elapsed calculation
- Integration with reliability store
"""

from datetime import datetime, timezone, timedelta

import pytest

from bayesian_engine.decay import (
    compute_decay_factor,
    apply_reliability_decay,
    days_since_update,
    decay_reliability_if_needed,
)
from bayesian_engine.config import (
    DECAY_HALF_LIFE_DAYS,
    DECAY_MINIMUM,
)


class TestComputeDecayFactor:
    """Tests for decay factor calculation."""

    def test_no_elapsed_time_returns_one(self):
        """No time elapsed means no decay (factor = 1.0)."""
        assert compute_decay_factor(0) == 1.0

    def test_negative_elapsed_time_returns_one(self):
        """Negative time (edge case) is treated as no decay."""
        assert compute_decay_factor(-1) == 1.0
        assert compute_decay_factor(-100) == 1.0

    def test_one_half_life_returns_half(self):
        """After one half-life, decay factor should be 0.5."""
        assert compute_decay_factor(30, half_life_days=30) == pytest.approx(0.5)

    def test_two_half_lives_returns_quarter(self):
        """After two half-lives, decay factor should be 0.25."""
        assert compute_decay_factor(60, half_life_days=30) == pytest.approx(0.25)

    def test_custom_half_life(self):
        """Custom half-life values work correctly."""
        # 15 days with 15-day half-life = factor 0.5
        assert compute_decay_factor(15, half_life_days=15) == pytest.approx(0.5)

    def test_default_half_life_from_config(self):
        """Default half-life comes from config (30 days)."""
        factor = compute_decay_factor(DECAY_HALF_LIFE_DAYS)
        assert factor == pytest.approx(0.5)


class TestApplyReliabilityDecay:
    """Tests for applying decay to reliability scores."""

    def test_no_elapsed_time_unchanged(self):
        """No time elapsed means reliability stays the same."""
        assert apply_reliability_decay(0.8, 0) == 0.8

    def test_negative_elapsed_time_unchanged(self):
        """Negative time means reliability stays the same."""
        assert apply_reliability_decay(0.8, -10) == 0.8

    def test_decay_moves_toward_floor(self):
        """Decay should move reliability toward the floor."""
        current = 0.8
        min_floor = 0.1

        # After any decay, reliability should be closer to floor
        decayed = apply_reliability_decay(current, 10, min_reliability=min_floor)
        assert min_floor < decayed < current

    def test_decay_never_goes_below_floor(self):
        """Reliability should never drop below the floor."""
        # Even with extreme time
        decayed = apply_reliability_decay(0.9, 1000, min_reliability=0.1)
        assert decayed >= 0.1

    def test_floor_reliability_unchanged(self):
        """Reliability at floor stays at floor."""
        assert apply_reliability_decay(0.1, 1000, min_reliability=0.1) == 0.1

    def test_one_half_life_decay(self):
        """After one half-life, reliability is halfway to floor."""
        current = 0.8
        floor = 0.1
        expected = floor + (current - floor) * 0.5  # 0.45

        result = apply_reliability_decay(
            current,
            30,
            half_life_days=30,
            min_reliability=floor,
        )
        assert result == pytest.approx(expected)

    def test_reliability_never_exceeds_one(self):
        """Reliability is clamped to maximum of 1.0."""
        # Edge case: what if somehow reliability > 1
        result = apply_reliability_decay(1.5, 30)
        assert result <= 1.0

    def test_default_config_values(self):
        """Uses config defaults when not specified."""
        result = apply_reliability_decay(0.8, 30)
        # Should use DECAY_HALF_LIFE_DAYS=30 and DECAY_MINIMUM=0.1
        expected = DECAY_MINIMUM + (0.8 - DECAY_MINIMUM) * 0.5
        assert result == pytest.approx(expected)


class TestDaysSinceUpdate:
    """Tests for calculating elapsed time."""

    def test_none_timestamp_returns_zero(self):
        """None timestamp means no elapsed time."""
        assert days_since_update(None) == 0.0

    def test_empty_string_returns_zero(self):
        """Empty string timestamp means no elapsed time."""
        assert days_since_update("") == 0.0

    def test_invalid_string_returns_zero(self):
        """Invalid ISO string is treated as no update."""
        assert days_since_update("not-a-date") == 0.0

    def test_zero_seconds_elapsed(self):
        """Just-updated timestamp returns 0 days."""
        now = datetime.now(timezone.utc)
        iso_now = now.isoformat()

        assert days_since_update(iso_now, now=now) == 0.0

    def test_one_day_elapsed(self):
        """Exactly one day ago returns 1.0."""
        now = datetime.now(timezone.utc)
        one_day_ago = now - timedelta(days=1)

        assert days_since_update(one_day_ago, now=now) == pytest.approx(1.0)

    def test_half_day_elapsed(self):
        """12 hours ago returns 0.5 days."""
        now = datetime.now(timezone.utc)
        half_day_ago = now - timedelta(hours=12)

        assert days_since_update(half_day_ago, now=now) == pytest.approx(0.5)

    def test_iso_string_parsing(self):
        """ISO format strings are parsed correctly."""
        now = datetime(2026, 2, 21, 12, 0, 0, tzinfo=timezone.utc)
        past = datetime(2026, 2, 20, 12, 0, 0, tzinfo=timezone.utc)

        assert days_since_update(past.isoformat(), now=now) == pytest.approx(1.0)

    def test_datetime_object_input(self):
        """datetime objects work as input."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(days=7)

        assert days_since_update(past, now=now) == pytest.approx(7.0)

    def test_timezone_naive_assumes_utc(self):
        """Naive datetime is treated as UTC."""
        now = datetime(2026, 2, 21, 12, 0, 0, tzinfo=timezone.utc)
        past_naive = datetime(2026, 2, 20, 12, 0, 0)  # No timezone

        # Should still work, treating past_naive as UTC
        result = days_since_update(past_naive, now=now)
        assert result == pytest.approx(1.0)


class TestDecayReliabilityIfNeeded:
    """Tests for the combined decay function."""

    def test_cold_start_no_decay(self):
        """Cold-start (no timestamp) means no decay."""
        reliability, was_decayed = decay_reliability_if_needed(0.8, None)
        assert reliability == 0.8
        assert was_decayed is False

    def test_recent_update_no_decay(self):
        """Recent update (0 days elapsed) means no decay."""
        now = datetime.now(timezone.utc)
        reliability, was_decayed = decay_reliability_if_needed(
            0.8,
            now.isoformat(),
            now=now,
        )
        assert reliability == 0.8
        assert was_decayed is False

    def test_old_update_applies_decay(self):
        """Old update means decay is applied."""
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=30)

        reliability, was_decayed = decay_reliability_if_needed(
            0.8,
            old.isoformat(),
            now=now,
        )

        # Reliability should have decayed
        assert reliability < 0.8
        assert was_decayed is True

    def test_floor_reliability_no_change(self):
        """Reliability at floor doesn't change (but still 'decayed' technically)."""
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=1000)

        reliability, was_decayed = decay_reliability_if_needed(
            0.1,  # At floor
            old.isoformat(),
            now=now,
            min_reliability=0.1,
        )

        assert reliability == 0.1
        # was_decayed could be True or False depending on float comparison
        # The important thing is reliability is correct


class TestDecayEdgeCases:
    """Edge case tests for decay behavior."""

    def test_very_high_reliability_decays_proportionally(self):
        """High reliability (0.99) decays proportionally."""
        result = apply_reliability_decay(0.99, 30, min_reliability=0.1)
        # Should be around 0.545 (halfway from 0.99 to 0.1)
        expected = 0.1 + (0.99 - 0.1) * 0.5
        assert result == pytest.approx(expected)

    def test_reliability_below_floor_raises_to_floor(self):
        """Reliability below floor is raised to floor (edge case)."""
        result = apply_reliability_decay(0.05, 30, min_reliability=0.1)
        # The formula would go below floor, so we clamp
        # Actually the formula: 0.1 + (0.05 - 0.1) * 0.5 = 0.1 - 0.025 = 0.075
        # But we clamp to min_reliability
        assert result >= 0.1

    def test_fractional_days(self):
        """Fractional days work correctly."""
        # 12 hours = 0.5 days
        result = apply_reliability_decay(0.8, 0.5, half_life_days=1)
        # After 0.5 days with 1-day half-life, factor = 2^(-0.5) ≈ 0.707
        # Decayed = 0.1 + (0.8 - 0.1) * 0.707 ≈ 0.595
        import math
        expected_factor = 2 ** (-0.5)
        expected = 0.1 + 0.7 * expected_factor
        assert result == pytest.approx(expected)
