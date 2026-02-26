"""CLI entrypoint."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from bayesian_engine.core import ValidationError, compute_consensus, validate_input_payload
from bayesian_engine.reliability import SQLiteReliabilityStore


def _load_input(input_path: str | None) -> dict[str, Any]:
    if input_path:
        with open(input_path, "r", encoding="utf-8") as f:
            return json.load(f)

    if sys.stdin.isatty():
        raise ValidationError("Input required: provide --input <file> or JSON via stdin")

    return json.load(sys.stdin)


def _run_dashboard(port: int, db_path: str) -> None:
    """Run the dashboard server."""
    try:
        from bayesian_engine.dashboard import DashboardServer
    except ImportError as e:
        print("Dashboard requires extra dependencies: pip install bayesian-consensus-engine[dashboard]", file=sys.stderr)
        raise SystemExit(1) from e
    
    store = SQLiteReliabilityStore(db_path)
    server = DashboardServer(store, port=port)
    try:
        server.start(blocking=True)
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    finally:
        store.close()


def _cmd_consensus(args: argparse.Namespace) -> None:
    """Compute consensus from signals."""
    try:
        payload = _load_input(args.input)
        validate_input_payload(payload)
        
        # Load reliability from DB if specified
        source_reliability = None
        if args.db:
            with SQLiteReliabilityStore(args.db) as store:
                # Get reliability for each source in the signals
                source_reliability = {}
                for signal in payload.get("signals", []):
                    source_id = signal.get("sourceId")
                    if source_id:
                        rec = store.get_reliability(source_id, payload["marketId"], apply_decay=True)
                        source_reliability[source_id] = {
                            "reliability": rec.reliability,
                            "confidence": rec.confidence,
                        }
        
        result = compute_consensus(payload["signals"], source_reliability)
        if args.dry_run:
            result["diagnostics"]["dryRun"] = True
        print(json.dumps(result, indent=2))
    except (json.JSONDecodeError, ValidationError) as exc:
        print(f"Validation error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def _cmd_report_outcome(args: argparse.Namespace) -> None:
    """Report an outcome and update reliability."""
    if not args.db:
        print("Error: --db is required for report-outcome", file=sys.stderr)
        raise SystemExit(1)
    
    try:
        with SQLiteReliabilityStore(args.db) as store:
            result = store.update_reliability(
                source_id=args.source_id,
                market_id=args.market_id,
                outcome_correct=args.correct,
                dry_run=args.dry_run,
            )
        
        output = {
            "sourceId": result.source_id,
            "marketId": result.market_id,
            "reliability": result.reliability,
            "confidence": result.confidence,
            "updatedAt": result.updated_at,
            "dryRun": args.dry_run,
        }
        print(json.dumps(output, indent=2))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def _cmd_list_sources(args: argparse.Namespace) -> None:
    """List all sources with reliability data."""
    if not args.db:
        print("Error: --db is required for list-sources", file=sys.stderr)
        raise SystemExit(1)
    
    try:
        with SQLiteReliabilityStore(args.db) as store:
            sources = store.list_sources(market_id=args.market_id)
        
        output = {
            "sources": [
                {
                    "sourceId": s.source_id,
                    "marketId": s.market_id,
                    "reliability": s.reliability,
                    "confidence": s.confidence,
                    "updatedAt": s.updated_at,
                }
                for s in sources
            ],
            "count": len(sources),
        }
        print(json.dumps(output, indent=2))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def _cmd_dashboard(args: argparse.Namespace) -> None:
    """Launch the web dashboard."""
    _run_dashboard(args.port, args.db)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="bayesian-engine",
        description="Bayesian-weighted consensus engine with reliability tracking",
    )
    parser.add_argument(
        "--db",
        type=str,
        default="reliability.db",
        help="Path to SQLite database file (default: reliability.db)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute without persisting changes (zero DB writes)",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Path to JSON input file (for consensus command)",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # consensus command
    consensus_parser = subparsers.add_parser("consensus", help="Compute consensus from signals")
    consensus_parser.add_argument("--input", help="Path to JSON input file")
    consensus_parser.set_defaults(func=_cmd_consensus)
    
    # report-outcome command
    outcome_parser = subparsers.add_parser("report-outcome", help="Report outcome and update reliability")
    outcome_parser.add_argument("--source-id", required=True, help="Source identifier")
    outcome_parser.add_argument("--market-id", required=True, help="Market identifier")
    outcome_parser.add_argument("--correct", action="store_true", help="Outcome was correct")
    outcome_parser.set_defaults(func=_cmd_report_outcome)
    
    # list-sources command
    list_parser = subparsers.add_parser("list-sources", help="List sources with reliability data")
    list_parser.add_argument("--market-id", help="Filter by market ID")
    list_parser.set_defaults(func=_cmd_list_sources)
    
    # dashboard command
    dashboard_parser = subparsers.add_parser("dashboard", help="Launch web dashboard")
    dashboard_parser.add_argument("--port", type=int, default=8080, help="Dashboard port (default: 8080)")
    dashboard_parser.set_defaults(func=_cmd_dashboard)
    
    args = parser.parse_args()
    
    # Default to consensus for backward compatibility
    if args.command is None:
        # Legacy mode: treat as consensus command with top-level --input
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
    else:
        args.func(args)


if __name__ == "__main__":
    main()
