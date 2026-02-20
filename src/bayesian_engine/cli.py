"""CLI entrypoint."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from bayesian_engine.core import ValidationError, compute_consensus, validate_input_payload


def _load_input(input_path: str | None) -> dict[str, Any]:
    if input_path:
        with open(input_path, "r", encoding="utf-8") as f:
            return json.load(f)

    if sys.stdin.isatty():
        raise ValidationError("Input required: provide --input <file> or JSON via stdin")

    return json.load(sys.stdin)


def main() -> None:
    parser = argparse.ArgumentParser(prog="bayesian-engine")
    parser.add_argument("--input", help="Path to JSON input file")
    parser.add_argument("--dry-run", action="store_true", help="Compute output without DB writes")
    args = parser.parse_args()

    try:
        payload = _load_input(args.input)
        validate_input_payload(payload)
        result = compute_consensus(payload["signals"])
        if args.dry_run:
            result["diagnostics"]["dryRun"] = True
        print(json.dumps(result, indent=2))
    except (json.JSONDecodeError, ValidationError) as exc:
        print(f"Validation error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
