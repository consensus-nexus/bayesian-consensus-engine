#!/usr/bin/env python3
"""Tie-breaking example for conflicting predictions.

This example demonstrates how the deterministic tie-breaker
resolves conflicts when agents predict different outcomes.
"""

from bayesian_engine.tiebreak import AgentSignal, DeterministicTieBreaker


def main():
    # Create tie-breaker
    tiebreaker = DeterministicTieBreaker()

    # Scenario: Agents disagree on the outcome
    # Group A predicts 0.7 (higher reliability)
    # Group B predicts 0.3 (more agents, lower reliability)
    agents = [
        # Group A: 2 agents predicting 0.7 with high reliability
        AgentSignal("agent-a1", prediction=0.7, confidence=0.8, reliability_score=0.9),
        AgentSignal("agent-a2", prediction=0.7, confidence=0.7, reliability_score=0.85),
        
        # Group B: 3 agents predicting 0.3 with lower reliability
        AgentSignal("agent-b1", prediction=0.3, confidence=0.6, reliability_score=0.5),
        AgentSignal("agent-b2", prediction=0.3, confidence=0.5, reliability_score=0.45),
        AgentSignal("agent-b3", prediction=0.3, confidence=0.55, reliability_score=0.4),
    ]

    # Resolve tie
    winning_prediction, diagnostics = tiebreaker.resolve(agents)

    print("=== Tie-Break Resolution ===")
    print(f"Winning prediction: {winning_prediction:.2f}")
    print(f"Resolution method: {diagnostics.tie_resolved_by}")
    print(f"Confidence variance: {diagnostics.confidence_variance:.4f}")

    print("\n=== Group Metrics ===")
    for pred, metrics in diagnostics.groups.items():
        print(f"Prediction {pred:.2f}:")
        print(f"  Count: {metrics['count']}")
        print(f"  Weight density: {metrics['weight_density']:.4f}")
        print(f"  Max reliability: {metrics['max_reliability']:.4f}")
        print(f"  Avg confidence: {metrics['avg_confidence']:.4f}")


if __name__ == "__main__":
    main()
