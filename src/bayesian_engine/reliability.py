"""Reliability storage and update logic (SQLite).

Provides persistent storage for source reliability scores and confidence
values. Supports Bayesian-style post-outcome updates with a capped update
step to prevent wild swings from a single outcome.

Implements PRD §7.B exponential time decay when fetching reliability.

Cold-start defaults (PRD §reliability):
    reliability = 0.50
    confidence  = 0.50

Max update step per outcome: 0.10
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Union

from bayesian_engine.config import (
    DEFAULT_RELIABILITY,
    DEFAULT_CONFIDENCE,
    MAX_UPDATE_STEP,
    DECAY_HALF_LIFE_DAYS,
    DECAY_MINIMUM,
)
from bayesian_engine.decay import apply_reliability_decay, days_since_update

# Learning rate applied before capping
_BASE_LEARNING_RATE: float = 0.15

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sources (
    source_id   TEXT    NOT NULL,
    market_id   TEXT    NOT NULL,
    reliability REAL    NOT NULL DEFAULT 0.5,
    confidence  REAL    NOT NULL DEFAULT 0.5,
    updated_at  TEXT    NOT NULL,
    PRIMARY KEY (source_id, market_id)
);
"""


@dataclass(frozen=True)
class ReliabilityRecord:
    """Immutable snapshot of a source's reliability data."""

    source_id: str
    market_id: str
    reliability: float
    confidence: float
    updated_at: str


class SQLiteReliabilityStore:
    """SQLite-backed store for per-source, per-market reliability scores.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file.  Use ``":memory:"`` for an
        ephemeral in-memory database (useful in tests).
    """

    def __init__(self, db_path: Union[str, Path] = ":memory:") -> None:
        self._db_path = str(db_path)
        self._conn: sqlite3.Connection = sqlite3.connect(
            self._db_path,
            # Enable WAL for better concurrent-read performance
            isolation_level=None,
        )
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.row_factory = sqlite3.Row
        self._ensure_schema()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_reliability(
        self,
        source_id: str,
        market_id: str,
        apply_decay: bool = False,
    ) -> ReliabilityRecord:
        """Return the reliability record for *source_id* in *market_id*.

        If no record exists (cold-start), returns a record populated with
        the PRD default values (reliability=0.5, confidence=0.5).

        Args:
            source_id: Unique identifier for the signal source
            market_id: Market or question identifier
            apply_decay: If True, apply exponential time decay to reliability

        Returns:
            ReliabilityRecord with current (possibly decayed) reliability
        """
        row = self._conn.execute(
            "SELECT source_id, market_id, reliability, confidence, updated_at "
            "FROM sources WHERE source_id = ? AND market_id = ?",
            (source_id, market_id),
        ).fetchone()

        if row is not None:
            reliability = row["reliability"]
            updated_at = row["updated_at"]

            # Apply decay if requested and we have a timestamp
            if apply_decay and updated_at:
                elapsed_days = days_since_update(updated_at)
                if elapsed_days > 0:
                    reliability = apply_reliability_decay(
                        reliability,
                        elapsed_days,
                        DECAY_HALF_LIFE_DAYS,
                        DECAY_MINIMUM,
                    )

            return ReliabilityRecord(
                source_id=row["source_id"],
                market_id=row["market_id"],
                reliability=reliability,
                confidence=row["confidence"],
                updated_at=updated_at,
            )

        # Cold-start: return defaults without persisting
        return ReliabilityRecord(
            source_id=source_id,
            market_id=market_id,
            reliability=DEFAULT_RELIABILITY,
            confidence=DEFAULT_CONFIDENCE,
            updated_at="",
        )

    def update_reliability(
        self,
        source_id: str,
        market_id: str,
        outcome_correct: bool,
    ) -> ReliabilityRecord:
        """Apply a Bayesian-style reliability update after an outcome.

        The update direction depends on *outcome_correct*:
        - ``True``  → reliability moves **up** (source was right)
        - ``False`` → reliability moves **down** (source was wrong)

        The raw delta is ``_BASE_LEARNING_RATE * direction`` and is then
        clamped so the absolute change never exceeds ``MAX_UPDATE_STEP``.
        The final value is clamped to [0, 1].

        Confidence grows toward 1.0 with every update (the store has seen
        more evidence about this source).

        Returns the updated :class:`ReliabilityRecord`.
        """
        current = self.get_reliability(source_id, market_id)

        direction = 1.0 if outcome_correct else -1.0
        raw_delta = _BASE_LEARNING_RATE * direction

        # Cap the absolute step
        capped_delta = max(-MAX_UPDATE_STEP, min(MAX_UPDATE_STEP, raw_delta))

        new_reliability = max(0.0, min(1.0, current.reliability + capped_delta))

        # Confidence grows toward 1.0; each update closes 10% of the gap
        new_confidence = current.confidence + (1.0 - current.confidence) * 0.10
        new_confidence = min(1.0, new_confidence)

        now = datetime.now(timezone.utc).isoformat()

        self._conn.execute(
            """
            INSERT INTO sources (source_id, market_id, reliability, confidence, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(source_id, market_id)
            DO UPDATE SET reliability = excluded.reliability,
                          confidence  = excluded.confidence,
                          updated_at  = excluded.updated_at
            """,
            (source_id, market_id, new_reliability, new_confidence, now),
        )

        return ReliabilityRecord(
            source_id=source_id,
            market_id=market_id,
            reliability=new_reliability,
            confidence=new_confidence,
            updated_at=now,
        )

    def list_sources(
        self,
        market_id: Optional[str] = None,
    ) -> List[ReliabilityRecord]:
        """Return all stored reliability records, optionally filtered by market.

        Useful for diagnostics and admin tooling.
        """
        if market_id is not None:
            rows = self._conn.execute(
                "SELECT source_id, market_id, reliability, confidence, updated_at "
                "FROM sources WHERE market_id = ? ORDER BY source_id",
                (market_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT source_id, market_id, reliability, confidence, updated_at "
                "FROM sources ORDER BY source_id, market_id",
            ).fetchall()

        return [
            ReliabilityRecord(
                source_id=r["source_id"],
                market_id=r["market_id"],
                reliability=r["reliability"],
                confidence=r["confidence"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "SQLiteReliabilityStore":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ensure_schema(self) -> None:
        self._conn.executescript(_CREATE_TABLE_SQL)
