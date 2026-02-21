"""Exponential decay helpers for reliability scores.

Implements PRD §7.B (Reliability System): exponential time decay for
reliability scores based on time since last update.

The decay formula uses a half-life model:
    decayed_reliability = min_reliability + 
        (current_reliability - min_reliability) * 2^(-elapsed_days / half_life)

Where:
    - half_life: Days until reliability decays to halfway to the floor
    - min_reliability: Floor that reliability never drops below

This means:
    - After 30 days (default half-life), reliability is halfway to floor
    - After 60 days, reliability is 75% of the way to floor
    - Reliability asymptotically approaches but never goes below floor
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Union

from bayesian_engine.config import (
    DECAY_HALF_LIFE_DAYS,
    DECAY_MINIMUM,
)


def compute_decay_factor(
    elapsed_days: float,
    half_life_days: float = DECAY_HALF_LIFE_DAYS,
) -> float:
    """Compute the exponential decay factor.

    Args:
        elapsed_days: Time elapsed since last reliability update
        half_life_days: Days until factor drops to 0.5

    Returns:
        Decay factor in [0, 1], where 0 means fully decayed, 1 means no decay

    Examples:
        >>> compute_decay_factor(0)  # No time elapsed
        1.0
        >>> compute_decay_factor(30)  # One half-life
        0.5
        >>> compute_decay_factor(60)  # Two half-lives
        0.25
    """
    if elapsed_days <= 0:
        return 1.0

    # Exponential decay: factor = 2^(-t/half_life)
    # Using the formula: 2^(-n) where n = elapsed / half_life
    exponent = -elapsed_days / half_life_days
    return 2.0 ** exponent


def apply_reliability_decay(
    current_reliability: float,
    elapsed_days: float,
    half_life_days: float = DECAY_HALF_LIFE_DAYS,
    min_reliability: float = DECAY_MINIMUM,
) -> float:
    """Apply exponential decay to a reliability score.

    The reliability decays toward the minimum floor over time, but never
    drops below it. This models the intuition that old predictions become
    less relevant as market conditions change.

    Args:
        current_reliability: Current reliability score [0, 1]
        elapsed_days: Days since the reliability was last updated
        half_life_days: Days until reliability is halfway to floor
        min_reliability: Floor reliability never drops below

    Returns:
        Decayed reliability score, clamped to [min_reliability, 1]

    Examples:
        >>> apply_reliability_decay(0.8, 0)  # No time elapsed
        0.8
        >>> apply_reliability_decay(0.8, 30, min_reliability=0.1)  # One half-life
        0.45
        >>> apply_reliability_decay(0.8, 1000, min_reliability=0.1)  # Very old
        0.1  # Hits floor
    """
    if elapsed_days <= 0:
        return current_reliability

    # Compute how much of the range (current - floor) to preserve
    decay_factor = compute_decay_factor(elapsed_days, half_life_days)

    # Apply decay: move from current toward floor
    decayed = min_reliability + (current_reliability - min_reliability) * decay_factor

    # Ensure we stay in valid range [min, 1]
    return max(min_reliability, min(1.0, decayed))


def days_since_update(
    last_updated_at: Union[str, datetime, None],
    now: Union[datetime, None] = None,
) -> float:
    """Calculate days elapsed since last update timestamp.

    Args:
        last_updated_at: ISO format timestamp string, datetime object, or None
        now: Current time (defaults to utcnow)

    Returns:
        Days elapsed (0 if last_updated_at is None or empty)

    Examples:
        >>> days_since_update(None)
        0.0
        >>> days_since_update("")
        0.0
    """
    if not last_updated_at:
        return 0.0

    # Parse ISO format string if needed
    if isinstance(last_updated_at, str):
        try:
            last_updated = datetime.fromisoformat(last_updated_at)
        except ValueError:
            # Invalid timestamp, treat as no update
            return 0.0
    else:
        last_updated = last_updated_at

    # Use provided 'now' or current UTC time
    if now is None:
        now = datetime.now(timezone.utc)

    # Ensure both datetimes have timezone info for comparison
    if last_updated.tzinfo is None:
        # Assume UTC if no timezone
        last_updated = last_updated.replace(tzinfo=timezone.utc)

    elapsed = now - last_updated
    return max(0.0, elapsed.total_seconds() / 86400.0)  # Seconds per day


def decay_reliability_if_needed(
    current_reliability: float,
    last_updated_at: Union[str, datetime, None],
    now: Union[datetime, None] = None,
    half_life_days: float = DECAY_HALF_LIFE_DAYS,
    min_reliability: float = DECAY_MINIMUM,
) -> tuple[float, bool]:
    """Apply decay to reliability if time has elapsed.

    Convenience function that combines elapsed time calculation with decay.

    Args:
        current_reliability: Current reliability score
        last_updated_at: When the reliability was last updated
        now: Current time (defaults to utcnow)
        half_life_days: Decay half-life in days
        min_reliability: Floor reliability

    Returns:
        Tuple of (decayed_reliability, was_decayed)

    Examples:
        >>> decay_reliability_if_needed(0.8, None)
        (0.8, False)  # Cold-start, no decay
    """
    elapsed = days_since_update(last_updated_at, now)

    if elapsed <= 0:
        return current_reliability, False

    decayed = apply_reliability_decay(
        current_reliability,
        elapsed,
        half_life_days,
        min_reliability,
    )

    return decayed, decayed != current_reliability
