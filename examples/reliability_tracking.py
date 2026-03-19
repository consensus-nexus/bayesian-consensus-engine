#!/usr/bin/env python3
"""Reliability tracking example with persistent storage.

This example demonstrates how to:
1. Store and retrieve reliability scores
2. Update reliability based on outcomes
3. Apply time-based decay
"""

from bayesian_engine.core import compute_consensus
from bayesian_engine.reliability import SQLiteReliabilityStore


def main():
    # Create persistent store
    store = SQLiteReliabilityStore("example_reliability.db")

    # Define signals
    signals = [
        {"sourceId": "agent-alpha", "probability": 0.70},
        {"sourceId": "agent-beta", "probability": 0.55},
    ]
    market_id = "example-market-1"

    # Get current reliability for each source
    reliability_data = {}
    for signal in signals:
        source_id = signal["sourceId"]
        record = store.get_reliability(source_id, market_id, apply_decay=True)
        reliability_data[source_id] = {
            "reliability": record.reliability,
            "confidence": record.confidence,
        }
        print(f"{source_id}: reliability={record.reliability:.2%}, confidence={record.confidence:.2%}")

    # Compute consensus with reliability data
    result = compute_consensus(signals, source_reliability=reliability_data)
    print(f"\nConsensus: {result['consensus']:.2%}")

    # Simulate outcome: agent-alpha was correct, agent-beta was wrong
    print("\n=== Updating reliability based on outcome ===")
    store.update_reliability("agent-alpha", market_id, outcome_correct=True)
    store.update_reliability("agent-beta", market_id, outcome_correct=False)

    # Show updated reliability
    for signal in signals:
        source_id = signal["sourceId"]
        record = store.get_reliability(source_id, market_id)
        print(f"{source_id}: reliability={record.reliability:.2%}, confidence={record.confidence:.2%}")

    # List all sources
    print("\n=== All tracked sources ===")
    for record in store.list_sources():
        print(f"  {record.source_id} @ {record.market_id}: {record.reliability:.2%}")

    store.close()


if __name__ == "__main__":
    main()
