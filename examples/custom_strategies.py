"""Example custom decay strategies.

This module demonstrates how to create custom decay strategies
for the Bayesian Consensus Engine.

To use a custom strategy:

1. Create a class implementing DecayStrategy protocol
2. Register it with register_strategy()
3. Use it via CLI: --decay-strategy time-windowed

Example:
    from bayesian_engine.strategies import register_strategy
    from examples.custom_strategies import TimeWindowedDecay
    
    register_strategy("time-windowed", TimeWindowedDecay)
"""

from bayesian_engine.strategies import DecayStrategy


class TimeWindowedDecay:
    """Time-windowed decay: reliability stays constant within window, then resets.
    
    This strategy models sources that are reliable for a fixed period,
    then need to re-establish credibility.
    
    Args:
        window_days: Days before reliability resets to floor
        min_reliability: Floor reliability after window expires
    
    Example:
        >>> strategy = TimeWindowedDecay(window_days=30, min_reliability=0.1)
        >>> strategy.apply(0.8, 15)  # Within window
        0.8
        >>> strategy.apply(0.8, 35)  # After window
        0.1
    """
    
    def __init__(
        self,
        window_days: float = 30,
        min_reliability: float = 0.1,
    ):
        self.window_days = window_days
        self.min_reliability = min_reliability
    
    def apply(self, current_reliability: float, elapsed_days: float) -> float:
        """Apply time-windowed decay."""
        if elapsed_days <= self.window_days:
            return current_reliability
        return self.min_reliability
    
    def configure(self, **kwargs) -> None:
        """Update strategy parameters."""
        if "window_days" in kwargs:
            self.window_days = kwargs["window_days"]
        if "min_reliability" in kwargs:
            self.min_reliability = kwargs["min_reliability"]


class StepDecay:
    """Step decay: reliability drops in discrete steps over time.
    
    This strategy models sources that lose credibility in stages.
    
    Args:
        step_days: Days between steps
        step_size: Reliability lost per step
        min_reliability: Floor reliability
    
    Example:
        >>> strategy = StepDecay(step_days=7, step_size=0.1, min_reliability=0.2)
        >>> strategy.apply(0.8, 0)  # Fresh
        0.8
        >>> strategy.apply(0.8, 8)  # One step
        0.7
        >>> strategy.apply(0.8, 15)  # Two steps
        0.6
    """
    
    def __init__(
        self,
        step_days: float = 7,
        step_size: float = 0.1,
        min_reliability: float = 0.2,
    ):
        self.step_days = step_days
        self.step_size = step_size
        self.min_reliability = min_reliability
    
    def apply(self, current_reliability: float, elapsed_days: float) -> float:
        """Apply step decay."""
        if elapsed_days <= 0:
            return current_reliability
        
        # Calculate number of steps
        steps = int(elapsed_days / self.step_days)
        
        # Apply decay
        decayed = current_reliability - (steps * self.step_size)
        
        # Clamp to floor
        return max(self.min_reliability, min(1.0, decayed))
    
    def configure(self, **kwargs) -> None:
        """Update strategy parameters."""
        if "step_days" in kwargs:
            self.step_days = kwargs["step_days"]
        if "step_size" in kwargs:
            self.step_size = kwargs["step_size"]
        if "min_reliability" in kwargs:
            self.min_reliability = kwargs["min_reliability"]


class SigmoidDecay:
    """Sigmoid decay: slow-fast-slow decay curve.
    
    This strategy models sources that maintain reliability initially,
    then decay rapidly, then stabilize near floor.
    
    Args:
        midpoint_days: Days until decay is halfway
        steepness: How sharp the transition (higher = sharper)
        min_reliability: Floor reliability
    
    Example:
        >>> strategy = SigmoidDecay(midpoint_days=30, steepness=0.1)
        >>> strategy.apply(0.8, 0)  # Fresh
        0.8
        >>> strategy.apply(0.8, 30)  # Midpoint
        0.45
    """
    
    def __init__(
        self,
        midpoint_days: float = 30,
        steepness: float = 0.1,
        min_reliability: float = 0.1,
    ):
        self.midpoint_days = midpoint_days
        self.steepness = steepness
        self.min_reliability = min_reliability
    
    def apply(self, current_reliability: float, elapsed_days: float) -> float:
        """Apply sigmoid decay."""
        import math
        
        if elapsed_days <= 0:
            return current_reliability
        
        # Sigmoid function: 1 / (1 + e^(steepness * (elapsed - midpoint)))
        decay_factor = 1.0 / (1.0 + math.exp(self.steepness * (elapsed_days - self.midpoint_days)))
        
        # Decay toward floor
        decayed = self.min_reliability + (current_reliability - self.min_reliability) * decay_factor
        
        return max(self.min_reliability, min(1.0, decayed))
    
    def configure(self, **kwargs) -> None:
        """Update strategy parameters."""
        if "midpoint_days" in kwargs:
            self.midpoint_days = kwargs["midpoint_days"]
        if "steepness" in kwargs:
            self.steepness = kwargs["steepness"]
        if "min_reliability" in kwargs:
            self.min_reliability = kwargs["min_reliability"]
