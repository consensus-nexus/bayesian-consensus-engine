"""Tests for dashboard module (issue #20)."""

from __future__ import annotations

import json
import threading
import time
from http.client import HTTPConnection
from pathlib import Path
from typing import Any

import pytest

from bayesian_engine.reliability import SQLiteReliabilityStore
from bayesian_engine.dashboard import _get_dashboard_data, start_dashboard


@pytest.fixture
def populated_db(tmp_path: Path) -> str:
    """Create a temp DB with a few sources."""
    db_path = str(tmp_path / "test.db")
    with SQLiteReliabilityStore(db_path) as store:
        store.update_reliability("src_a", "market_1", outcome_correct=True)
        store.update_reliability("src_a", "market_1", outcome_correct=True)
        store.update_reliability("src_b", "market_1", outcome_correct=False)
        store.update_reliability("src_c", "market_2", outcome_correct=True)
    return db_path


class TestGetDashboardData:
    def test_empty_db(self, tmp_path: Path):
        db_path = str(tmp_path / "empty.db")
        with SQLiteReliabilityStore(db_path) as store:
            data = _get_dashboard_data(store)

        assert data["total_sources"] == 0
        assert data["total_markets"] == 0
        assert data["avg_reliability"] == 0.0
        assert data["sources"] == []

    def test_populated_db(self, populated_db: str):
        with SQLiteReliabilityStore(populated_db) as store:
            data = _get_dashboard_data(store)

        assert data["total_sources"] == 3
        assert data["total_markets"] == 2
        assert 0.0 < data["avg_reliability"] < 1.0
        assert data["highest_reliability"]["source_id"] in ("src_a", "src_c")

    def test_sources_sorted_by_reliability(self, populated_db: str):
        with SQLiteReliabilityStore(populated_db) as store:
            data = _get_dashboard_data(store)

        reliabilities = [s["reliability"] for s in data["sources"]]
        assert reliabilities == sorted(reliabilities, reverse=True)

    def test_source_fields(self, populated_db: str):
        with SQLiteReliabilityStore(populated_db) as store:
            data = _get_dashboard_data(store)

        for s in data["sources"]:
            assert "source_id" in s
            assert "market_id" in s
            assert "reliability" in s
            assert "confidence" in s
            assert "updated_at" in s


class TestDashboardHTTP:
    def _start_server(self, db_path: str, port: int):
        """Start dashboard in a background thread."""
        from http.server import HTTPServer
        from bayesian_engine.dashboard import _make_handler

        handler = _make_handler(db_path)
        server = HTTPServer(("127.0.0.1", port), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        time.sleep(0.3)  # Wait for server to bind
        return server

    def test_html_page(self, populated_db: str):
        server = self._start_server(populated_db, 18080)
        try:
            conn = HTTPConnection("127.0.0.1", 18080)
            conn.request("GET", "/")
            resp = conn.getresponse()
            assert resp.status == 200
            body = resp.read().decode()
            assert "Bayesian Consensus Engine" in body
            assert "Dashboard" in body
            conn.close()
        finally:
            server.shutdown()

    def test_api_data_endpoint(self, populated_db: str):
        server = self._start_server(populated_db, 18081)
        try:
            conn = HTTPConnection("127.0.0.1", 18081)
            conn.request("GET", "/api/data")
            resp = conn.getresponse()
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            assert data["total_sources"] == 3
            assert len(data["sources"]) == 3
            conn.close()
        finally:
            server.shutdown()

    def test_404_for_unknown_path(self, populated_db: str):
        server = self._start_server(populated_db, 18082)
        try:
            conn = HTTPConnection("127.0.0.1", 18082)
            conn.request("GET", "/nonexistent")
            resp = conn.getresponse()
            assert resp.status == 404
            conn.close()
        finally:
            server.shutdown()
