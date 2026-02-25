"""Tests for plugin system."""

import pytest

from bayesian_engine.plugins import (
    UpdateStrategy,
    DecayStrategy,
    UpdateContext,
    DecayContext,
    UpdateResult,
    DecayResult,
    StrategyRegistry,
    get_registry,
    get_update_strategy,
    get_decay_strategy,
    register_update_strategy,
    register_decay_strategy,
    DefaultUpdateStrategy,
    ConservativeUpdateStrategy,
    AggressiveUpdateStrategy,
    ExponentialDecayStrategy,
    LinearDecayStrategy,
    NoDecayStrategy,
)
from bayesian_engine.config import DEFAULT_RELIABILITY, DEFAULT_CONFIDENCE


class TestUpdateStrategies:
    """Test update strategies."""
    
    def test_default_strategy_correct_increases(self):
        """Correct outcome increases reliability."""
        strategy = DefaultUpdateStrategy()
        ctx = UpdateContext(
            current_reliability=0.5,
            current_confidence=0.5,
            outcome_correct=True,
            source_id="test",
            market_id="test",
            history=[],
        )
        result = strategy.compute_update(ctx)
        
        assert result.reliability > 0.5
        assert result.confidence > 0.5
    
    def test_default_strategy_wrong_decreases(self):
        """Wrong outcome decreases reliability."""
        strategy = DefaultUpdateStrategy()
        ctx = UpdateContext(
            current_reliability=0.5,
            current_confidence=0.5,
            outcome_correct=False,
            source_id="test",
            market_id="test",
            history=[],
        )
        result = strategy.compute_update(ctx)
        
        assert result.reliability < 0.5
    
    def test_default_strategy_caps_step(self):
        """Default strategy caps at 10% max step."""
        strategy = DefaultUpdateStrategy()
        
        # Start at 0.5, max step should be 0.10
        ctx = UpdateContext(
            current_reliability=0.5,
            current_confidence=0.5,
            outcome_correct=True,
            source_id="test",
            market_id="test",
            history=[],
        )
        result = strategy.compute_update(ctx)
        
        # Should not increase by more than 0.10
        assert result.reliability <= 0.6
    
    def test_conservative_strategy_smaller_step(self):
        """Conservative strategy uses smaller steps."""
        strategy = ConservativeUpdateStrategy()
        ctx = UpdateContext(
            current_reliability=0.5,
            current_confidence=0.5,
            outcome_correct=True,
            source_id="test",
            market_id="test",
            history=[],
        )
        result = strategy.compute_update(ctx)
        
        # Should not increase by more than 0.05
        assert result.reliability <= 0.55
    
    def test_aggressive_strategy_larger_step(self):
        """Aggressive strategy uses larger steps."""
        strategy = AggressiveUpdateStrategy()
        ctx = UpdateContext(
            current_reliability=0.5,
            current_confidence=0.5,
            outcome_correct=True,
            source_id="test",
            market_id="test",
            history=[],
        )
        result = strategy.compute_update(ctx)
        
        # Can increase by up to 0.20
        assert result.reliability > 0.55
    
    def test_history_weighted_uses_history(self):
        """History-weighted strategy considers past outcomes."""
        strategy = AggressiveUpdateStrategy()
        # This strategy would need more complex testing
        # For now just verify it runs
        ctx = UpdateContext(
            current_reliability=0.5,
            current_confidence=0.5,
            outcome_correct=True,
            source_id="test",
            market_id="test",
            history=[True, True, True],  # Good history
        )
        result = strategy.compute_update(ctx)
        
        assert 0 <= result.reliability <= 1


class TestDecayStrategies:
    """Test decay strategies."""
    
    def test_exponential_decay_reduces_reliability(self):
        """Exponential decay reduces reliability over time."""
        strategy = ExponentialDecayStrategy()
        ctx = DecayContext(
            current_reliability=0.8,
            current_confidence=0.5,
            elapsed_days=30,
            source_id="test",
            market_id="test",
        )
        result = strategy.compute_decay(ctx)
        
        assert result.reliability < 0.8
    
    def test_exponential_decay_no_time_no_change(self):
        """No time elapsed means no decay."""
        strategy = ExponentialDecayStrategy()
        ctx = DecayContext(
            current_reliability=0.8,
            current_confidence=0.5,
            elapsed_days=0,
            source_id="test",
            market_id="test",
        )
        result = strategy.compute_decay(ctx)
        
        assert result.reliability == 0.8
    
    def test_exponential_decay_hits_floor(self):
        """Decay doesn't go below floor."""
        strategy = ExponentialDecayStrategy()
        ctx = DecayContext(
            current_reliability=0.8,
            current_confidence=0.5,
            elapsed_days=1000,  # Very long time
            source_id="test",
            market_id="test",
        )
        result = strategy.compute_decay(ctx)
        
        assert result.reliability >= 0.10  # DECAY_MINIMUM
    
    def test_linear_decay(self):
        """Linear decay reduces reliability linearly."""
        strategy = LinearDecayStrategy()
        ctx = DecayContext(
            current_reliability=0.8,
            current_confidence=0.5,
            elapsed_days=10,
            source_id="test",
            market_id="test",
        )
        result = strategy.compute_decay(ctx)
        
        assert result.reliability < 0.8
    
    def test_no_decay_strategy(self):
        """No decay strategy keeps reliability constant."""
        strategy = NoDecayStrategy()
        ctx = DecayContext(
            current_reliability=0.8,
            current_confidence=0.5,
            elapsed_days=100,
            source_id="test",
            market_id="test",
        )
        result = strategy.compute_decay(ctx)
        
        assert result.reliability == 0.8


class TestStrategyRegistry:
    """Test strategy registry."""
    
    def test_registry_has_defaults(self):
        """Registry has default strategies."""
        registry = StrategyRegistry()
        
        assert "default" in registry.list_update_strategies()
        assert "conservative" in registry.list_update_strategies()
        assert "aggressive" in registry.list_update_strategies()
        
        assert "exponential" in registry.list_decay_strategies()
        assert "linear" in registry.list_decay_strategies()
        assert "none" in registry.list_decay_strategies()
    
    def test_registry_get_update_strategy(self):
        """Can get update strategy by name."""
        registry = StrategyRegistry()
        strategy = registry.get_update("default")
        
        assert strategy.name == "default"
    
    def test_registry_get_unknown_raises(self):
        """Unknown strategy raises error."""
        registry = StrategyRegistry()
        
        with pytest.raises(ValueError):
            registry.get_update("nonexistent")
    
    def test_registry_register_custom(self):
        """Can register custom strategy."""
        registry = StrategyRegistry()
        
        class CustomStrategy(UpdateStrategy):
            @property
            def name(self):
                return "custom"
            
            def compute_update(self, ctx):
                return UpdateResult(reliability=0.5, confidence=0.5)
        
        registry.register_update(CustomStrategy())
        
        assert "custom" in registry.list_update_strategies()
        assert registry.get_update("custom").name == "custom"


class TestGlobalRegistry:
    """Test global registry functions."""
    
    def test_get_update_strategy(self):
        """Get update strategy from global registry."""
        strategy = get_update_strategy("default")
        assert strategy.name == "default"
    
    def test_get_decay_strategy(self):
        """Get decay strategy from global registry."""
        strategy = get_decay_strategy("exponential")
        assert strategy.name == "exponential"
    
    def test_register_custom_strategy(self):
        """Register custom strategy globally."""
        class MyStrategy(UpdateStrategy):
            @property
            def name(self):
                return "my-test-strategy"
            
            def compute_update(self, ctx):
                return UpdateResult(reliability=0.99, confidence=0.99)
        
        register_update_strategy(MyStrategy())
        
        strategy = get_update_strategy("my-test-strategy")
        assert strategy.name == "my-test-strategy"
