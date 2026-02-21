"""Tests for SQLiteReliabilityStore."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from bayesian_engine.reliability import (
    DEFAULT_CONFIDENCE,
    DEFAULT_RELIABILITY,
    MAX_UPDATE_STEP,
    ReliabilityRecord,
    SQLiteReliabilityStore,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def store() -> SQLiteReliabilityStore:
    """In-memory store for fast unit tests."""
    s = SQLiteReliabilityStore(":memory:")
    yield s
    s.close()


@pytest.fixture()
def file_store(tmp_path: Path) -> SQLiteReliabilityStore:
    """File-backed store for persistence integration tests."""
    db_file = tmp_path / "reliability.db"
    s = SQLiteReliabilityStore(db_file)
    yield s
    s.close()


# ---------------------------------------------------------------------------
# Cold-start defaults
# ---------------------------------------------------------------------------


class TestColdStart:
    def test_unseen_source_returns_defaults(self, store: SQLiteReliabilityStore) -> None:
        rec = store.get_reliability("unknown-src", "market-1")
        assert rec.source_id == "unknown-src"
        assert rec.market_id == "market-1"
        assert rec.reliability == DEFAULT_RELIABILITY
        assert rec.confidence == DEFAULT_CONFIDENCE
        assert rec.updated_at == ""  # never persisted

    def test_cold_start_does_not_persist(self, store: SQLiteReliabilityStore) -> None:
        """Calling get_reliability on an unseen source must NOT create a row."""
        store.get_reliability("ghost", "market-1")
        rows = store.list_sources()
        assert len(rows) == 0


# ---------------------------------------------------------------------------
# update_reliability
# ---------------------------------------------------------------------------


class TestUpdateReliability:
    def test_correct_outcome_increases_reliability(
        self, store: SQLiteReliabilityStore
    ) -> None:
        rec = store.update_reliability("src-a", "m-1", outcome_correct=True)
        assert rec.reliability > DEFAULT_RELIABILITY

    def test_incorrect_outcome_decreases_reliability(
        self, store: SQLiteReliabilityStore
    ) -> None:
        rec = store.update_reliability("src-a", "m-1", outcome_correct=False)
        assert rec.reliability < DEFAULT_RELIABILITY

    def test_update_step_never_exceeds_cap(
        self, store: SQLiteReliabilityStore
    ) -> None:
        rec = store.update_reliability("src-a", "m-1", outcome_correct=True)
        delta = abs(rec.reliability - DEFAULT_RELIABILITY)
        assert delta <= MAX_UPDATE_STEP + 1e-9  # float tolerance

    def test_reliability_clamped_to_zero(
        self, store: SQLiteReliabilityStore
    ) -> None:
        """Reliability should never go below 0."""
        # Drive reliability down many times
        for _ in range(20):
            store.update_reliability("low-src", "m-1", outcome_correct=False)
        rec = store.get_reliability("low-src", "m-1")
        assert rec.reliability >= 0.0

    def test_reliability_clamped_to_one(
        self, store: SQLiteReliabilityStore
    ) -> None:
        """Reliability should never exceed 1."""
        for _ in range(20):
            store.update_reliability("high-src", "m-1", outcome_correct=True)
        rec = store.get_reliability("high-src", "m-1")
        assert rec.reliability <= 1.0

    def test_confidence_grows_with_updates(
        self, store: SQLiteReliabilityStore
    ) -> None:
        store.update_reliability("src-a", "m-1", outcome_correct=True)
        rec1 = store.get_reliability("src-a", "m-1")

        store.update_reliability("src-a", "m-1", outcome_correct=False)
        rec2 = store.get_reliability("src-a", "m-1")

        assert rec2.confidence > rec1.confidence

    def test_update_persists_record(
        self, store: SQLiteReliabilityStore
    ) -> None:
        store.update_reliability("src-a", "m-1", outcome_correct=True)
        rec = store.get_reliability("src-a", "m-1")
        assert rec.updated_at != ""
        assert rec.reliability != DEFAULT_RELIABILITY

    def test_multiple_updates_accumulate(
        self, store: SQLiteReliabilityStore
    ) -> None:
        store.update_reliability("src-a", "m-1", outcome_correct=True)
        r1 = store.get_reliability("src-a", "m-1").reliability

        store.update_reliability("src-a", "m-1", outcome_correct=True)
        r2 = store.get_reliability("src-a", "m-1").reliability

        assert r2 > r1

    def test_per_market_isolation(
        self, store: SQLiteReliabilityStore
    ) -> None:
        """Different markets maintain independent reliability scores."""
        store.update_reliability("src-a", "market-1", outcome_correct=True)
        store.update_reliability("src-a", "market-2", outcome_correct=False)

        rec1 = store.get_reliability("src-a", "market-1")
        rec2 = store.get_reliability("src-a", "market-2")

        assert rec1.reliability > DEFAULT_RELIABILITY
        assert rec2.reliability < DEFAULT_RELIABILITY


# ---------------------------------------------------------------------------
# list_sources
# ---------------------------------------------------------------------------


class TestListSources:
    def test_empty_store_returns_empty(self, store: SQLiteReliabilityStore) -> None:
        assert store.list_sources() == []

    def test_lists_all_sources(self, store: SQLiteReliabilityStore) -> None:
        store.update_reliability("src-a", "m-1", outcome_correct=True)
        store.update_reliability("src-b", "m-1", outcome_correct=False)

        sources = store.list_sources()
        assert len(sources) == 2
        ids = {s.source_id for s in sources}
        assert ids == {"src-a", "src-b"}

    def test_filter_by_market(self, store: SQLiteReliabilityStore) -> None:
        store.update_reliability("src-a", "m-1", outcome_correct=True)
        store.update_reliability("src-a", "m-2", outcome_correct=True)

        m1 = store.list_sources(market_id="m-1")
        assert len(m1) == 1
        assert m1[0].market_id == "m-1"

    def test_list_returns_sorted(self, store: SQLiteReliabilityStore) -> None:
        store.update_reliability("src-c", "m-1", outcome_correct=True)
        store.update_reliability("src-a", "m-1", outcome_correct=True)
        store.update_reliability("src-b", "m-1", outcome_correct=True)

        sources = store.list_sources()
        ids = [s.source_id for s in sources]
        assert ids == sorted(ids)


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class TestContextManager:
    def test_context_manager_closes(self, tmp_path: Path) -> None:
        db_file = tmp_path / "ctx.db"
        with SQLiteReliabilityStore(db_file) as store:
            store.update_reliability("src-a", "m-1", outcome_correct=True)
        # After exiting, the connection should be closed; opening again
        # should still see the data.
        with SQLiteReliabilityStore(db_file) as store2:
            rec = store2.get_reliability("src-a", "m-1")
            assert rec.reliability > DEFAULT_RELIABILITY


# ---------------------------------------------------------------------------
# Persistence (file-backed integration)
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_data_survives_reconnect(self, tmp_path: Path) -> None:
        db_file = tmp_path / "persist.db"

        # Write
        with SQLiteReliabilityStore(db_file) as store:
            store.update_reliability("src-a", "m-1", outcome_correct=True)

        # Read from fresh connection
        with SQLiteReliabilityStore(db_file) as store2:
            rec = store2.get_reliability("src-a", "m-1")
            assert rec.reliability > DEFAULT_RELIABILITY
            assert rec.confidence > DEFAULT_CONFIDENCE

    def test_schema_created_on_new_db(self, tmp_path: Path) -> None:
        db_file = tmp_path / "fresh.db"
        with SQLiteReliabilityStore(db_file):
            # Verify table exists
            conn = sqlite3.connect(str(db_file))
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='sources'"
            )
            assert cursor.fetchone() is not None
            conn.close()


# ---------------------------------------------------------------------------
# ReliabilityRecord dataclass
# ---------------------------------------------------------------------------


class TestReliabilityRecord:
    def test_frozen(self) -> None:
        rec = ReliabilityRecord("s", "m", 0.5, 0.5, "")
        with pytest.raises(AttributeError):
            rec.reliability = 0.9  # type: ignore[misc]

    def test_equality(self) -> None:
        a = ReliabilityRecord("s", "m", 0.5, 0.5, "t")
        b = ReliabilityRecord("s", "m", 0.5, 0.5, "t")
        assert a == b
