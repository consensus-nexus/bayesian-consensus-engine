"""Configuration constants for the Bayesian consensus engine.

This module centralizes all cold-start defaults and operational parameters
as specified in PRD §9 (Cold-Start Defaults).

Usage:
    from bayesian_engine.config import (
        DEFAULT_RELIABILITY,
        DEFAULT_CONFIDENCE,
        MAX_UPDATE_STEP,
        TIE_TOLERANCE,
    )
"""

# Cold-start defaults (PRD §9)
# Used when a new source has no historical reliability data
DEFAULT_RELIABILITY = 0.50  # 50% reliability for new sources
DEFAULT_CONFIDENCE = 0.25   # 25% confidence for new sources

# Reliability update constraints (PRD §9)
# Maximum single-step change to reliability score
MAX_UPDATE_STEP = 0.10      # 10% max change per outcome

# Tie-breaking configuration (PRD §8)
# Numerical tolerance for detecting tied consensus probabilities
TIE_TOLERANCE = 1e-9        # Epsilon for float comparison

# Decay configuration (PRD §7)
# Time constant for exponential decay of reliability scores
DECAY_HALF_LIFE_DAYS = 30   # Days until reliability decays by half
DECAY_MINIMUM = 0.10        # Floor reliability never decays below this

# Schema versioning
SCHEMA_VERSION = "1.0.0"

# Validation limits
MIN_SOURCE_ID_LENGTH = 1
MAX_SOURCE_ID_LENGTH = 256
MAX_SIGNALS_PER_REQUEST = 1000
