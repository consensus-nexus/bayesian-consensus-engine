#!/usr/bin/env python3
"""Basic consensus computation example.

This example demonstrates how to compute consensus from multiple signals
without persistent reliability tracking.
"""

from bayesian_engine.core import compute_consensus, validate_input_payload


def main():
    # Define input payload
    payload = {
        "schemaVersion": "1.0.0",
        "marketId": "example-market-1",
        "signals": [
            {"sourceId": "agent-alpha", "probability": 0.65},
            {"sourceId": "agent-beta", "probability": 0.72},
            {"sourceId": "agent-gamma", "probability": 0.58},
        ]
    }

    # Validate input
    validate_input_payload(payload)
    print("✓ Input validated")

    # Compute consensus
    result = compute_consensus(payload["signals"])

    # Display results
    print(f"\n=== Consensus Result ===")
    print(f"Consensus probability: {result['consensus']:.2%}")
    print(f"Confidence: {result['confidence']:.2%}")
    print(f"\nSource weights:")
    for sw in result["sourceWeights"]:
        print(f"  {sw['sourceId']}: {sw['normalizedWeight']:.2%}")

    print(f"\nDiagnostics:")
    print(f"  Status: {result['diagnostics']['status']}")
    print(f"  Cold-start sources: {result['diagnostics']['coldStartSources']}")


if __name__ == "__main__":
    main()
