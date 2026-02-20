"""Deterministic tie-break resolution for conflicting predictions."""

from dataclasses import dataclass
from typing import Dict, List, Tuple
from collections import defaultdict


@dataclass(frozen=True)
class TieBreakDiagnostics:
    """Metadata about tie-break resolution process."""
    
    method: str
    groups: Dict[float, Dict]
    selected_group: float
    tie_resolved_by: str
    confidence_variance: float


@dataclass
class AgentSignal:
    """Single agent prediction with metadata."""
    
    agent_id: str
    prediction: float
    confidence: float
    weight: float = 1.0
    reliability_score: float = 0.5
    
    def __post_init__(self):
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"confidence must be in [0,1], got {self.confidence}")
        if not 0 <= self.reliability_score <= 1:
            raise ValueError(f"reliability_score must be in [0,1], got {self.reliability_score}")


class DeterministicTieBreaker:
    """
    Resolves conflicts when agents predict different outcomes.
    
    Resolution hierarchy:
    1. Weight density (total_weight / count) - primary
    2. Max reliability within group - secondary  
    3. Smallest prediction value - tertiary (deterministic tie-break)
    """
    
    def __init__(self, precision: int = 6):
        self.precision = precision
    
    def _group_by_prediction(self, agents: List[AgentSignal]) -> Dict[float, List[AgentSignal]]:
        """Group agents by their prediction value."""
        groups = defaultdict(list)
        for agent in agents:
            # Round to precision for grouping floating point predictions
            key = round(agent.prediction, self.precision)
            groups[key].append(agent)
        return dict(groups)
    
    def _calculate_group_metrics(self, group: List[AgentSignal]) -> Dict:
        """Calculate aggregate metrics for a prediction group."""
        total_weight = sum(a.weight for a in group)
        avg_confidence = sum(a.confidence for a in group) / len(group)
        max_reliability = max(a.reliability_score for a in group)
        
        return {
            'agents': [a.agent_id for a in group],
            'count': len(group),
            'total_weight': total_weight,
            'weight_density': total_weight / len(group),
            'avg_confidence': avg_confidence,
            'max_reliability': max_reliability,
        }
    
    def resolve(self, agents: List[AgentSignal]) -> Tuple[float, TieBreakDiagnostics]:
        """
        Resolve tie between conflicting predictions.
        
        Args:
            agents: List of agent signals (may have different predictions)
            
        Returns:
            Tuple of (winning_prediction, diagnostics)
            
        Raises:
            ValueError: If agents list is empty
        """
        if not agents:
            raise ValueError("Cannot resolve tie with empty agent list")
        
        if len(agents) == 1:
            return agents[0].prediction, TieBreakDiagnostics(
                method="single_agent",
                groups={agents[0].prediction: {"count": 1}},
                selected_group=agents[0].prediction,
                tie_resolved_by="unanimous",
                confidence_variance=0.0
            )
        
        # Group agents by prediction
        groups = self._group_by_prediction(agents)
        
        # Calculate metrics for each group
        group_metrics = {
            pred: self._calculate_group_metrics(members)
            for pred, members in groups.items()
        }
        
        # Calculate overall confidence variance for diagnostics
        all_confidences = [a.confidence for a in agents]
        mean_conf = sum(all_confidences) / len(all_confidences)
        variance = sum((c - mean_conf) ** 2 for c in all_confidences) / len(all_confidences)
        
        # Sort groups by resolution hierarchy
        sorted_groups = sorted(
            group_metrics.items(),
            key=lambda x: (x[1]['weight_density'], x[1]['max_reliability'], -x[0]),
            reverse=True
        )
        
        # Determine how tie was resolved
        winning_pred = sorted_groups[0][0]
        winning_metrics = sorted_groups[0][1]
        
        if len(sorted_groups) == 1:
            resolution_method = "unanimous"
        elif len(sorted_groups) > 1:
            second = sorted_groups[1]
            if (winning_metrics['weight_density'] == second[1]['weight_density'] and
                winning_metrics['max_reliability'] == second[1]['max_reliability']):
                resolution_method = "prediction_value_smallest"
            else:
                resolution_method = "weight_density"
        else:
            resolution_method = "unknown"
        
        # Build diagnostics
        diagnostics = TieBreakDiagnostics(
            method="prioritized_weight_density",
            groups={
                pred: {
                    'count': data['count'],
                    'weight_density': round(data['weight_density'], 4),
                    'avg_confidence': round(data['avg_confidence'], 4),
                    'max_reliability': round(data['max_reliability'], 4),
                }
                for pred, data in group_metrics.items()
            },
            selected_group=winning_pred,
            tie_resolved_by=resolution_method,
            confidence_variance=round(variance, 6)
        )
        
        return winning_pred, diagnostics
