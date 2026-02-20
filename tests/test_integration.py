import json
import subprocess
import sys


def test_cli_integration_valid_input_outputs_schema_version(tmp_path) -> None:
    payload = {
        "schemaVersion": "1.0.0",
        "marketId": "market-1",
        "signals": [{"sourceId": "agent-a", "probability": 0.5}],
    }
    input_file = tmp_path / "input.json"
    input_file.write_text(json.dumps(payload), encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, "-m", "bayesian_engine.cli", "--input", str(input_file)],
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0
    output = json.loads(proc.stdout)
    assert output["schemaVersion"] == "1.0.0"


def test_cli_integration_missing_schema_version_fails(tmp_path) -> None:
    payload = {
        "marketId": "market-1",
        "signals": [{"sourceId": "agent-a", "probability": 0.5}],
    }
    input_file = tmp_path / "input.json"
    input_file.write_text(json.dumps(payload), encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, "-m", "bayesian_engine.cli", "--input", str(input_file)],
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 1
    assert "schemaVersion is required" in proc.stderr
