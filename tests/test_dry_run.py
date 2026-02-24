"""Tests for --dry-run CLI functionality."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def _run_cli(args: list[str], input_data: dict | None = None) -> subprocess.CompletedProcess:
    """Helper to run CLI with optional stdin input."""
    stdin_input = json.dumps(input_data) if input_data else None
    return subprocess.run(
        [sys.executable, "-m", "bayesian_engine.cli"] + args,
        capture_output=True,
        text=True,
        input=stdin_input,
    )


class TestDryRunReportOutcome:
    """Tests for --dry-run with report-outcome command."""

    def test_dry_run_computes_without_persisting(self):
        """--dry-run should compute update without writing to DB."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            # Report outcome with --dry-run
            proc = _run_cli([
                "--db", str(db_path),
                "--dry-run",
                "report-outcome",
                "--source-id", "agent-a",
                "--market-id", "market-1",
                "--correct",
            ])
            
            assert proc.returncode == 0
            output = json.loads(proc.stdout)
            assert output["sourceId"] == "agent-a"
            assert output["marketId"] == "market-1"
            assert output["dryRun"] is True
            # Reliability should increase from default 0.5
            assert output["reliability"] > 0.5
            
            # Verify nothing was persisted - list-sources should be empty
            proc2 = _run_cli(["--db", str(db_path), "list-sources"])
            assert proc2.returncode == 0
            output2 = json.loads(proc2.stdout)
            assert output2["count"] == 0

    def test_without_dry_run_persists_to_db(self):
        """Without --dry-run, report-outcome should persist to DB."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            # Report outcome without --dry-run
            proc = _run_cli([
                "--db", str(db_path),
                "report-outcome",
                "--source-id", "agent-a",
                "--market-id", "market-1",
                "--correct",
            ])
            
            assert proc.returncode == 0
            output = json.loads(proc.stdout)
            assert output["dryRun"] is False
            
            # Verify it was persisted - list-sources should show 1 source
            proc2 = _run_cli(["--db", str(db_path), "list-sources"])
            assert proc2.returncode == 0
            output2 = json.loads(proc2.stdout)
            assert output2["count"] == 1
            assert output2["sources"][0]["sourceId"] == "agent-a"

    def test_correct_outcome_increases_reliability(self):
        """Correct outcome should increase reliability."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            proc = _run_cli([
                "--db", str(db_path),
                "--dry-run",
                "report-outcome",
                "--source-id", "agent-a",
                "--market-id", "market-1",
                "--correct",
            ])
            
            output = json.loads(proc.stdout)
            # Default is 0.5, should increase
            assert output["reliability"] > 0.5

    def test_incorrect_outcome_decreases_reliability(self):
        """Incorrect outcome should decrease reliability."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            proc = _run_cli([
                "--db", str(db_path),
                "--dry-run",
                "report-outcome",
                "--source-id", "agent-a",
                "--market-id", "market-1",
            ])  # No --correct means incorrect
            
            output = json.loads(proc.stdout)
            # Default is 0.5, should decrease
            assert output["reliability"] < 0.5


class TestListSources:
    """Tests for list-sources command."""

    def test_list_sources_empty_db(self):
        """list-sources on empty DB should return empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            proc = _run_cli(["--db", str(db_path), "list-sources"])
            assert proc.returncode == 0
            output = json.loads(proc.stdout)
            assert output["count"] == 0
            assert output["sources"] == []

    def test_list_sources_with_filter(self):
        """list-sources with --market-id should filter results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            # Add sources for two markets
            _run_cli(["--db", str(db_path), "report-outcome",
                     "--source-id", "agent-a", "--market-id", "market-1", "--correct"])
            _run_cli(["--db", str(db_path), "report-outcome",
                     "--source-id", "agent-b", "--market-id", "market-2", "--correct"])
            
            # Filter by market-1
            proc = _run_cli(["--db", str(db_path), "list-sources", "--market-id", "market-1"])
            output = json.loads(proc.stdout)
            assert output["count"] == 1
            assert output["sources"][0]["sourceId"] == "agent-a"


class TestConsensusWithDb:
    """Tests for consensus command with DB-backed reliability."""

    def test_consensus_uses_db_reliability(self):
        """consensus with --db should use stored reliability values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            # Set up a source with high reliability
            _run_cli(["--db", str(db_path), "report-outcome",
                     "--source-id", "agent-a", "--market-id", "market-1", "--correct"])
            
            # Run consensus
            payload = {
                "schemaVersion": "1.0.0",
                "marketId": "market-1",
                "signals": [
                    {"sourceId": "agent-a", "probability": 0.6},
                    {"sourceId": "agent-b", "probability": 0.4},
                ],
            }
            
            proc = _run_cli([
                "--db", str(db_path),
                "consensus",
            ], input_data=payload)
            
            assert proc.returncode == 0
            output = json.loads(proc.stdout)
            # agent-a should have higher weight due to stored reliability
            weights = {w["sourceId"]: w["weight"] for w in output["sourceWeights"]}
            assert weights["agent-a"] > weights["agent-b"]
