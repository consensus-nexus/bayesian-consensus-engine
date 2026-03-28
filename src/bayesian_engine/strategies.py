"""Plugin system for update/decay strategies.

Implements issue #21: Plugin System for Update/Decay Strategies

This module provides a Strategy Pattern implementation for customizing
reliability update and decay behaviors. Strategies can be:
1. Built-in (exponential, linear, none)
2. Custom (loaded from external modules)

Design Decision: Strategy Pattern (Option A)
- Simpler than dynamic loading
- Type-safe with Protocol validation
- Easy to test and reason about
- Can be extended to dynamic loading in v0.3 if needed

Usage:
    from bayesian_engine.strategies import DecayStrategy, ExponentialDecay
    
    # Use built-in strategy
    strategy = ExponentialDecay(half_life_days=30, min_reliability=0.1)
    decayed = strategy.apply(0.8, elapsed_days=15)
    
    # Custom strategy
    class MyDecay(DecayStrategy):
        def apply(self, reliability: float, elapsed_days: float) -> float:
            return reliability * 0.99 ** elapsed_days
    
    strategy = MyDecay()
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Type, Optional
from dataclasses import dataclass

from bayesian_engine.config import (
    DECAY_HALF_LIFE_DAYS,
    DECAY_MINIMUM,
)


@runtime_checkable
class DecayStrategy(Protocol):
    """Protocol for reliability decay strategies.
    
    Implement this to create custom decay behaviors.
    
    The strategy receives:
    - current_reliability: Score in [0, 1]
    - elapsed_days: Time since last update
    - config: Strategy-specific parameters
    
    Returns:
    - Decayed reliability in [0, 1]
    """
    
    def apply(
        self,
        current_reliability: float,
        elapsed_days: float,
    ) -> float:
        """Apply decay to reliability score.
        
        Args:
            current_reliability: Current reliability [0, 1]
            elapsed_days: Days since last update
            
        Returns:
            Decayed reliability [0, 1]
        """
        ...
    
    def configure(self, **kwargs) -> None:
        """Configure strategy parameters.
        
        Optional method for runtime configuration.
        """
        ...


class ExponentialDecay:
    """Exponential decay strategy (default).
    
    Decay formula:
        decayed = min + (current - min) * 2^(-elapsed/half_life)
    
    This is the v0.1 default behavior, now extracted as a strategy.
    
    Args:
        half_life_days: Days until reliability is halfway to floor
        min_reliability: Floor reliability never drops below
    
    Example:
        >>> strategy = ExponentialDecay(half_life_days=30, min_reliability=0.1)
        >>> strategy.apply(0.8, 30)  # One half-life
        0.45
    """
    
    def __init__(
        self,
        half_life_days: float = DECAY_HALF_LIFE_DAYS,
        min_reliability: float = DECAY_MINIMUM,
    ):
        self.half_life_days = half_life_days
        self.min_reliability = min_reliability
    
    def apply(self, current_reliability: float, elapsed_days: float) -> float:
        """Apply exponential decay."""
        if elapsed_days <= 0:
            return current_reliability
        
        # Exponential decay factor
        exponent = -elapsed_days / self.half_life_days
        decay_factor = 2.0 ** exponent
        
        # Decay toward floor
        decayed = self.min_reliability + (current_reliability - self.min_reliability) * decay_factor
        
        # Clamp to valid range
        return max(self.min_reliability, min(1.0, decayed))
    
    def configure(self, **kwargs) -> None:
        """Update strategy parameters."""
        if "half_life_days" in kwargs:
            self.half_life_days = kwargs["half_life_days"]
        if "min_reliability" in kwargs:
            self.min_reliability = kwargs["min_reliability"]


class LinearDecay:
    """Linear decay strategy.
    
    Decay formula:
        decayed = current - (rate * elapsed_days)
        decayed = max(min_reliability, decayed)
    
    Args:
        decay_rate: Reliability lost per day (e.g., 0.01 = 1% per day)
        min_reliability: Floor reliability
    
    Example:
        >>> strategy = LinearDecay(decay_rate=0.01, min_reliability=0.1)
        >>> strategy.apply(0.8, 30)  # 30 days
        0.5  # Lost 0.3 over 30 days
    """
    
    def __init__(
        self,
        decay_rate: float = 0.01,
        min_reliability: float = DECAY_MINIMUM,
    ):
        self.decay_rate = decay_rate
        self.min_reliability = min_reliability
    
    def apply(self, current_reliability: float, elapsed_days: float) -> float:
        """Apply linear decay."""
        if elapsed_days <= 0:
            return current_reliability
        
        # Linear decay
        decayed = current_reliability - (self.decay_rate * elapsed_days)
        
        # Clamp to floor
        return max(self.min_reliability, min(1.0, decayed))
    
    def configure(self, **kwargs) -> None:
        """Update strategy parameters."""
        if "decay_rate" in kwargs:
            self.decay_rate = kwargs["decay_rate"]
        if "min_reliability" in kwargs:
            self.min_reliability = kwargs["min_reliability"]


class NoDecay:
    """No decay strategy (reliability stays constant).
    
    Useful for testing or markets where reliability shouldn't decay.
    
    Example:
        >>> strategy = NoDecay()
        >>> strategy.apply(0.8, 1000)  # Any elapsed time
        0.8  # No change
    """
    
    def apply(self, current_reliability: float, elapsed_days: float) -> float:
        """No decay applied."""
        return current_reliability
    
    def configure(self, **kwargs) -> None:
        """No configuration needed."""
        pass


# Strategy registry for CLI/config lookup
STRATEGY_REGISTRY: dict[str, Type[DecayStrategy]] = {
    "exponential": ExponentialDecay,
    "linear": LinearDecay,
    "none": NoDecay,
}


def get_strategy(name: str, **kwargs) -> DecayStrategy:
    """Get a strategy by name with optional configuration.
    
    Args:
        name: Strategy name ("exponential", "linear", "none")
        **kwargs: Strategy-specific parameters
        
    Returns:
        Configured strategy instance
        
    Raises:
        ValueError: If strategy name not found
        
    Example:
        >>> strategy = get_strategy("exponential", half_life_days=60)
        >>> strategy.apply(0.8, 30)
        0.45
    """
    if name not in STRATEGY_REGISTRY:
        available = ", ".join(STRATEGY_REGISTRY.keys())
        raise ValueError(f"Unknown strategy '{name}'. Available: {available}")
    
    strategy_class = STRATEGY_REGISTRY[name]
    return strategy_class(**kwargs)


def register_strategy(name: str, strategy_class: Type[DecayStrategy]) -> None:
    """Register a custom strategy.
    
    This allows extending the system with custom strategies
    without modifying the core code.
    
    Args:
        name: Strategy name for CLI/config lookup
        strategy_class: Strategy class (must implement DecayStrategy)
        
    Example:
        >>> class TimeWindowedDecay:
        ...     def __init__(self, window_days=30):
        ...         self.window_days = window_days
        ...     def apply(self, reliability, elapsed):
        ...         if elapsed > self.window_days:
        ...             return 0.1  # Reset to floor
        ...         return reliability
        >>> register_strategy("time-windowed", TimeWindowedDecay)
        >>> strategy = get_strategy("time-windowed", window_days=60)
    """
    STRATEGY_REGISTRY[name] = strategy_class
