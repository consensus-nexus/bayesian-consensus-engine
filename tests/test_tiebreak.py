"""Tests for deterministic tie-break resolution."""

import pytest
from bayesian_engine.tiebreak import (
    AgentSignal,
    DeterministicTieBreaker,
)


class TestAgentSignal:
    """Test AgentSignal dataclass validation."""
    
    def test_valid_signal(self):
        signal = AgentSignal("agent_1", 0.75, 0.8, 0.9, 0.7)
        assert signal.agent_id == "agent_1"
        assert signal.prediction == 0.75
        
    def test_invalid_confidence_high(self):
        with pytest.raises(ValueError, match="confidence must be in"):
            AgentSignal("agent_1", 0.5, 1.5, 1.0, 0.5)
    
    def test_invalid_confidence_low(self):
        with pytest.raises(ValueError, match="confidence must be in"):
            AgentSignal("agent_1", 0.5, -0.1, 1.0, 0.5)
            
    def test_invalid_reliability(self):
        with pytest.raises(ValueError, match="reliability_score must be in"):
            AgentSignal("agent_1", 0.5, 0.5, 1.0, 1.5)


class TestDeterministicTieBreaker:
    """Test tie-break resolution logic."""
    
    def setup_method(self):
        self.breaker = DeterministicTieBreaker()
    
    def test_empty_agents_raises(self):
        with pytest.raises(ValueError, match="empty agent list"):
            self.breaker.resolve([])
    
    def test_single_agent_unanimous(self):
        agents = [AgentSignal("a1", 0.75, 0.8)]
        pred, diag = self.breaker.resolve(agents)
        
        assert pred == 0.75
        assert diag.method == "single_agent"
        assert diag.tie_resolved_by == "unanimous"
        assert diag.confidence_variance == 0.0
    
    def test_unanimous_prediction(self):
        """All agents agree - no tie to break."""
        agents = [
            AgentSignal("a1", 0.75, 0.8, 0.9, 0.7),
            AgentSignal("a2", 0.75, 0.75, 0.85, 0.6),
            AgentSignal("a3", 0.75, 0.70, 0.80, 0.5),
        ]
        pred, diag = self.breaker.resolve(agents)
        
        assert pred == 0.75
        assert diag.tie_resolved_by == "unanimous"
        assert diag.groups[0.75]['count'] == 3
    
    def test_weight_density_wins(self):
        """Higher weight density should win despite fewer agents."""
        # Group A: 2 agents, high weights -> high density
        # Group B: 3 agents, low weights -> low density
        agents = [
            AgentSignal("a1", 0.75, 0.85, 0.9, 0.82),  # Group A
            AgentSignal("a2", 0.75, 0.80, 0.85, 0.78),  # Group A
            AgentSignal("a3", 0.25, 0.70, 0.6, 0.65),   # Group B
            AgentSignal("a4", 0.25, 0.65, 0.55, 0.70),  # Group B
            AgentSignal("a5", 0.25, 0.60, 0.50, 0.60),  # Group B
        ]
        pred, diag = self.breaker.resolve(agents)
        
        # Group A density: (0.9 + 0.85) / 2 = 0.875
        # Group B density: (0.6 + 0.55 + 0.50) / 3 = 0.55
        assert pred == 0.75
        assert diag.tie_resolved_by == "weight_density"
        assert diag.groups[0.75]['weight_density'] == 0.875
        assert diag.groups[0.25]['weight_density'] == 0.55
    
    def test_reliability_tiebreak(self):
        """When weight density ties, use max reliability."""
        agents = [
            AgentSignal("a1", 0.75, 0.8, 1.0, 0.5),   # density=1.0, rel=0.5
            AgentSignal("a2", 0.25, 0.8, 1.0, 0.9),   # density=1.0, rel=0.9
        ]
        pred, diag = self.breaker.resolve(agents)
        
        # Same weight density, but group 0.25 has higher max reliability
        assert pred == 0.25
        assert diag.tie_resolved_by == "weight_density"
    
    def test_prediction_value_final_tiebreak(self):
        """When all else ties, smallest prediction wins."""
        agents = [
            AgentSignal("a1", 0.75, 0.8, 1.0, 0.9),
            AgentSignal("a2", 0.25, 0.8, 1.0, 0.9),
        ]
        pred, diag = self.breaker.resolve(agents)
        
        # Same weight density (1.0), same reliability (0.9)
        # Should pick smaller prediction value
        assert pred == 0.25
        assert diag.tie_resolved_by == "prediction_value_smallest"
    
    def test_diagnostics_structure(self):
        """Verify diagnostics contains expected fields."""
        agents = [
            AgentSignal("a1", 0.75, 0.8, 0.9, 0.7),
            AgentSignal("a2", 0.25, 0.6, 0.5, 0.5),
        ]
        pred, diag = self.breaker.resolve(agents)
        
        assert diag.method == "prioritized_weight_density"
        assert isinstance(diag.groups, dict)
        assert 0.75 in diag.groups
        assert 0.25 in diag.groups
        assert 'weight_density' in diag.groups[0.75]
        assert 'count' in diag.groups[0.75]
        assert 'avg_confidence' in diag.groups[0.75]
        assert diag.confidence_variance > 0
