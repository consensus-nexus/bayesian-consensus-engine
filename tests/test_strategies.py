"""Tests for decay strategy plugin system.

Tests the Strategy Pattern implementation for issue #21.
"""

import pytest

from bayesian_engine.strategies import (
    DecayStrategy,
    ExponentialDecay,
    LinearDecay,
    NoDecay,
    get_strategy,
    register_strategy,
    STRATEGY_REGISTRY,
)


class TestExponentialDecay:
    """Test exponential decay strategy (default v0.1 behavior)."""
    
    def test_no_elapsed_time(self):
        """No decay when no time has passed."""
        strategy = ExponentialDecay(half_life_days=30, min_reliability=0.1)
        assert strategy.apply(0.8, 0) == 0.8
    
    def test_one_half_life(self):
        """After one half-life, reliability is halfway to floor."""
        strategy = ExponentialDecay(half_life_days=30, min_reliability=0.1)
        # Start at 0.8, floor at 0.1, range is 0.7
        # After 30 days (one half-life), should be at 0.1 + 0.35 = 0.45
        result = strategy.apply(0.8, 30)
        assert abs(result - 0.45) < 0.01
    
    def test_two_half_lives(self):
        """After two half-lives, reliability is 75% to floor."""
        strategy = ExponentialDecay(half_life_days=30, min_reliability=0.1)
        # Start at 0.8, floor at 0.1, range is 0.7
        # After 60 days (two half-lives), should be at 0.1 + 0.175 = 0.275
        result = strategy.apply(0.8, 60)
        assert abs(result - 0.275) < 0.01
    
    def test_hits_floor(self):
        """Reliability never drops below floor."""
        strategy = ExponentialDecay(half_life_days=30, min_reliability=0.1)
        result = strategy.apply(0.8, 1000)  # Very old
        assert abs(result - 0.1) < 0.001  # Floating-point comparison
    
    def test_configure_updates_params(self):
        """Can update strategy parameters."""
        strategy = ExponentialDecay()
        strategy.configure(half_life_days=60, min_reliability=0.2)
        assert strategy.half_life_days == 60
        assert strategy.min_reliability == 0.2


class TestLinearDecay:
    """Test linear decay strategy."""
    
    def test_no_elapsed_time(self):
        """No decay when no time has passed."""
        strategy = LinearDecay(decay_rate=0.01, min_reliability=0.1)
        assert strategy.apply(0.8, 0) == 0.8
    
    def test_linear_decay(self):
        """Decays linearly over time."""
        strategy = LinearDecay(decay_rate=0.01, min_reliability=0.1)
        # 30 days at 1% per day = 30% loss
        # 0.8 - 0.3 = 0.5
        result = strategy.apply(0.8, 30)
        assert abs(result - 0.5) < 0.01
    
    def test_hits_floor(self):
        """Reliability never drops below floor."""
        strategy = LinearDecay(decay_rate=0.01, min_reliability=0.1)
        result = strategy.apply(0.8, 1000)  # Would be -9.2 without floor
        assert result == 0.1
    
    def test_configure_updates_params(self):
        """Can update strategy parameters."""
        strategy = LinearDecay()
        strategy.configure(decay_rate=0.02, min_reliability=0.15)
        assert strategy.decay_rate == 0.02
        assert strategy.min_reliability == 0.15


class TestNoDecay:
    """Test no decay strategy."""
    
    def test_no_decay_ever(self):
        """Reliability never decays."""
        strategy = NoDecay()
        assert strategy.apply(0.8, 0) == 0.8
        assert strategy.apply(0.8, 30) == 0.8
        assert strategy.apply(0.8, 1000) == 0.8
    
    def test_configure_does_nothing(self):
        """Configure is a no-op."""
        strategy = NoDecay()
        strategy.configure(anything="ignored")
        assert strategy.apply(0.5, 100) == 0.5


class TestStrategyRegistry:
    """Test strategy registry and lookup."""
    
    def test_get_exponential_strategy(self):
        """Can get exponential strategy by name."""
        strategy = get_strategy("exponential", half_life_days=60)
        assert isinstance(strategy, ExponentialDecay)
        assert strategy.half_life_days == 60
    
    def test_get_linear_strategy(self):
        """Can get linear strategy by name."""
        strategy = get_strategy("linear", decay_rate=0.02)
        assert isinstance(strategy, LinearDecay)
        assert strategy.decay_rate == 0.02
    
    def test_get_none_strategy(self):
        """Can get no-decay strategy by name."""
        strategy = get_strategy("none")
        assert isinstance(strategy, NoDecay)
    
    def test_unknown_strategy_raises(self):
        """Unknown strategy name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown strategy 'unknown'"):
            get_strategy("unknown")
    
    def test_register_custom_strategy(self):
        """Can register custom strategy."""
        class CustomDecay:
            def __init__(self, factor=0.5):
                self.factor = factor
            
            def apply(self, reliability, elapsed):
                return reliability * self.factor
            
            def configure(self, **kwargs):
                pass
        
        register_strategy("custom", CustomDecay)
        
        # Verify it's in registry
        assert "custom" in STRATEGY_REGISTRY
        
        # Can get it
        strategy = get_strategy("custom", factor=0.8)
        assert isinstance(strategy, CustomDecay)
        assert strategy.factor == 0.8
        
        # Cleanup
        del STRATEGY_REGISTRY["custom"]


class TestDecayStrategyProtocol:
    """Test DecayStrategy protocol compliance."""
    
    def test_exponential_implements_protocol(self):
        """ExponentialDecay implements DecayStrategy protocol."""
        strategy = ExponentialDecay()
        assert isinstance(strategy, DecayStrategy)
    
    def test_linear_implements_protocol(self):
        """LinearDecay implements DecayStrategy protocol."""
        strategy = LinearDecay()
        assert isinstance(strategy, DecayStrategy)
    
    def test_none_implements_protocol(self):
        """NoDecay implements DecayStrategy protocol."""
        strategy = NoDecay()
        assert isinstance(strategy, DecayStrategy)
