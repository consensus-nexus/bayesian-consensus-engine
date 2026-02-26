"""Plugin system for update and decay strategies.

This module provides a Strategy Pattern implementation for customizing
how reliability is updated and decayed.

Usage:
    from bayesian_engine.plugins import (
        UpdateStrategy,
        DecayStrategy,
        StrategyRegistry,
        get_update_strategy,
        get_decay_strategy,
    )
    
    # Register custom strategy
    registry = StrategyRegistry()
    registry.register_update("my-update", MyUpdateStrategy())
    registry.register_decay("my-decay", MyDecayStrategy())
    
    # Use in reliability store
    strategy = get_update_strategy("my-update")

Built-in strategies:
- "default" - Standard Bayesian update (10% max step)
- "conservative" - Slower updates (5% max step)
- "aggressive" - Faster updates (20% max step)
- "exponential" - Exponential decay (default)
- "linear" - Linear decay
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

from bayesian_engine.config import (
    MAX_UPDATE_STEP,
    DECAY_HALF_LIFE_DAYS,
    DECAY_MINIMUM,
)


@dataclass
class UpdateContext:
    """Context passed to update strategies."""
    
    current_reliability: float
    current_confidence: float
    outcome_correct: bool
    source_id: str
    market_id: str
    history: list[bool]  # Past outcomes (True=correct, False=wrong)


@dataclass
class DecayContext:
    """Context passed to decay strategies."""
    
    current_reliability: float
    current_confidence: float
    elapsed_days: float
    source_id: str
    market_id: str


@dataclass
class UpdateResult:
    """Result from an update strategy."""
    
    reliability: float
    confidence: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class DecayResult:
    """Result from a decay strategy."""
    
    reliability: float
    confidence: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class UpdateStrategy(ABC):
    """Base class for reliability update strategies.
    
    Implement this to create custom update logic.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name for registration."""
        ...
    
    @abstractmethod
    def compute_update(self, ctx: UpdateContext) -> UpdateResult:
        """Compute new reliability based on outcome.
        
        Args:
            ctx: Update context with current state and outcome
            
        Returns:
            UpdateResult with new reliability and confidence
        """
        ...
    
    def validate(self, reliability: float, confidence: float) -> tuple[float, float]:
        """Validate and clamp values to valid range."""
        reliability = max(0.0, min(1.0, reliability))
        confidence = max(0.0, min(1.0, confidence))
        return reliability, confidence


class DecayStrategy(ABC):
    """Base class for reliability decay strategies.
    
    Implement this to create custom decay logic.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name for registration."""
        ...
    
    @abstractmethod
    def compute_decay(self, ctx: DecayContext) -> DecayResult:
        """Compute decayed reliability based on time elapsed.
        
        Args:
            ctx: Decay context with current state and elapsed time
            
        Returns:
            DecayResult with decayed reliability and confidence
        """
        ...
    
    def validate(self, reliability: float, confidence: float, min_reliability: float) -> tuple[float, float]:
        """Validate and clamp values to valid range."""
        reliability = max(min_reliability, min(1.0, reliability))
        confidence = max(0.0, min(1.0, confidence))
        return reliability, confidence


# ============================================================================
# Built-in Update Strategies
# ============================================================================

class DefaultUpdateStrategy(UpdateStrategy):
    """Standard Bayesian update with capped step size."""
    
    @property
    def name(self) -> str:
        return "default"
    
    def compute_update(self, ctx: UpdateContext) -> UpdateResult:
        direction = 1.0 if ctx.outcome_correct else -1.0
        learning_rate = 0.15
        raw_delta = learning_rate * direction
        
        # Cap the step
        capped_delta = max(-MAX_UPDATE_STEP, min(MAX_UPDATE_STEP, raw_delta))
        new_reliability = ctx.current_reliability + capped_delta
        
        # Confidence grows toward 1.0
        new_confidence = ctx.current_confidence + (1.0 - ctx.current_confidence) * 0.10
        
        new_reliability, new_confidence = self.validate(new_reliability, new_confidence)
        
        return UpdateResult(
            reliability=new_reliability,
            confidence=new_confidence,
            metadata={"raw_delta": raw_delta, "capped_delta": capped_delta},
        )


class ConservativeUpdateStrategy(UpdateStrategy):
    """Conservative updates with smaller step size."""
    
    @property
    def name(self) -> str:
        return "conservative"
    
    def compute_update(self, ctx: UpdateContext) -> UpdateResult:
        direction = 1.0 if ctx.outcome_correct else -1.0
        max_step = 0.05  # 5% max change
        
        delta = max(-max_step, min(max_step, 0.10 * direction))
        new_reliability = ctx.current_reliability + delta
        
        # Slower confidence growth
        new_confidence = ctx.current_confidence + (1.0 - ctx.current_confidence) * 0.05
        
        new_reliability, new_confidence = self.validate(new_reliability, new_confidence)
        
        return UpdateResult(
            reliability=new_reliability,
            confidence=new_confidence,
            metadata={"delta": delta},
        )


class AggressiveUpdateStrategy(UpdateStrategy):
    """Aggressive updates with larger step size."""
    
    @property
    def name(self) -> str:
        return "aggressive"
    
    def compute_update(self, ctx: UpdateContext) -> UpdateResult:
        direction = 1.0 if ctx.outcome_correct else -1.0
        max_step = 0.20  # 20% max change
        
        delta = max(-max_step, min(max_step, 0.25 * direction))
        new_reliability = ctx.current_reliability + delta
        
        # Faster confidence growth
        new_confidence = ctx.current_confidence + (1.0 - ctx.current_confidence) * 0.15
        
        new_reliability, new_confidence = self.validate(new_reliability, new_confidence)
        
        return UpdateResult(
            reliability=new_reliability,
            confidence=new_confidence,
            metadata={"delta": delta},
        )


class HistoryWeightedUpdateStrategy(UpdateStrategy):
    """Updates weighted by recent history."""
    
    @property
    def name(self) -> str:
        return "history-weighted"
    
    def compute_update(self, ctx: UpdateContext) -> UpdateResult:
        direction = 1.0 if ctx.outcome_correct else -1.0
        
        # Weight by recent accuracy
        if ctx.history:
            recent = ctx.history[-10:]  # Last 10 outcomes
            accuracy = sum(recent) / len(recent)
            # Adjust learning rate based on consistency
            learning_rate = 0.10 + 0.10 * abs(accuracy - 0.5)
        else:
            learning_rate = 0.15
        
        delta = max(-MAX_UPDATE_STEP, min(MAX_UPDATE_STEP, learning_rate * direction))
        new_reliability = ctx.current_reliability + delta
        
        new_confidence = ctx.current_confidence + (1.0 - ctx.current_confidence) * 0.10
        
        new_reliability, new_confidence = self.validate(new_reliability, new_confidence)
        
        return UpdateResult(
            reliability=new_reliability,
            confidence=new_confidence,
            metadata={"learning_rate": learning_rate, "delta": delta},
        )


# ============================================================================
# Built-in Decay Strategies
# ============================================================================

class ExponentialDecayStrategy(DecayStrategy):
    """Exponential decay toward floor reliability."""
    
    @property
    def name(self) -> str:
        return "exponential"
    
    def compute_decay(self, ctx: DecayContext) -> DecayResult:
        if ctx.elapsed_days <= 0:
            return DecayResult(
                reliability=ctx.current_reliability,
                confidence=ctx.current_confidence,
            )
        
        # Exponential decay: factor = 2^(-t/half_life)
        factor = 2.0 ** (-ctx.elapsed_days / DECAY_HALF_LIFE_DAYS)
        
        # Decay toward minimum
        decayed = DECAY_MINIMUM + (ctx.current_reliability - DECAY_MINIMUM) * factor
        
        # Confidence also decays slightly
        new_confidence = ctx.current_confidence * (1.0 - 0.01 * min(ctx.elapsed_days, 30))
        
        decayed, new_confidence = self.validate(decayed, new_confidence, DECAY_MINIMUM)
        
        return DecayResult(
            reliability=decayed,
            confidence=new_confidence,
            metadata={"decay_factor": factor},
        )


class LinearDecayStrategy(DecayStrategy):
    """Linear decay toward floor reliability."""
    
    @property
    def name(self) -> str:
        return "linear"
    
    def compute_decay(self, ctx: DecayContext) -> DecayResult:
        if ctx.elapsed_days <= 0:
            return DecayResult(
                reliability=ctx.current_reliability,
                confidence=ctx.current_confidence,
            )
        
        # Linear decay: lose 1% per day toward floor
        decay_rate = 0.01
        total_decay = decay_rate * ctx.elapsed_days
        
        decayed = ctx.current_reliability - (ctx.current_reliability - DECAY_MINIMUM) * min(total_decay, 0.9)
        
        # Confidence decays
        new_confidence = ctx.current_confidence * (1.0 - 0.005 * min(ctx.elapsed_days, 30))
        
        decayed, new_confidence = self.validate(decayed, new_confidence, DECAY_MINIMUM)
        
        return DecayResult(
            reliability=decayed,
            confidence=new_confidence,
            metadata={"total_decay": total_decay},
        )


class NoDecayStrategy(DecayStrategy):
    """No decay - reliability stays constant."""
    
    @property
    def name(self) -> str:
        return "none"
    
    def compute_decay(self, ctx: DecayContext) -> DecayResult:
        return DecayResult(
            reliability=ctx.current_reliability,
            confidence=ctx.current_confidence,
            metadata={"decay": False},
        )


# ============================================================================
# Strategy Registry
# ============================================================================

class StrategyRegistry:
    """Registry for update and decay strategies.
    
    Allows registration and retrieval of strategies by name.
    Supports custom strategies via registration.
    """
    
    def __init__(self):
        self._update_strategies: Dict[str, UpdateStrategy] = {}
        self._decay_strategies: Dict[str, DecayStrategy] = {}
        self._register_defaults()
    
    def _register_defaults(self) -> None:
        """Register built-in strategies."""
        # Update strategies
        self.register_update(DefaultUpdateStrategy())
        self.register_update(ConservativeUpdateStrategy())
        self.register_update(AggressiveUpdateStrategy())
        self.register_update(HistoryWeightedUpdateStrategy())
        
        # Decay strategies
        self.register_decay(ExponentialDecayStrategy())
        self.register_decay(LinearDecayStrategy())
        self.register_decay(NoDecayStrategy())
    
    def register_update(self, strategy: UpdateStrategy) -> None:
        """Register an update strategy."""
        self._update_strategies[strategy.name] = strategy
    
    def register_decay(self, strategy: DecayStrategy) -> None:
        """Register a decay strategy."""
        self._decay_strategies[strategy.name] = strategy
    
    def get_update(self, name: str) -> UpdateStrategy:
        """Get an update strategy by name."""
        if name not in self._update_strategies:
            raise ValueError(f"Unknown update strategy: {name}. Available: {list(self._update_strategies.keys())}")
        return self._update_strategies[name]
    
    def get_decay(self, name: str) -> DecayStrategy:
        """Get a decay strategy by name."""
        if name not in self._decay_strategies:
            raise ValueError(f"Unknown decay strategy: {name}. Available: {list(self._decay_strategies.keys())}")
        return self._decay_strategies[name]
    
    def list_update_strategies(self) -> list[str]:
        """List available update strategies."""
        return list(self._update_strategies.keys())
    
    def list_decay_strategies(self) -> list[str]:
        """List available decay strategies."""
        return list(self._decay_strategies.keys())


# Global registry instance
_global_registry: Optional[StrategyRegistry] = None


def get_registry() -> StrategyRegistry:
    """Get the global strategy registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = StrategyRegistry()
    return _global_registry


def get_update_strategy(name: str = "default") -> UpdateStrategy:
    """Get an update strategy by name from global registry."""
    return get_registry().get_update(name)


def get_decay_strategy(name: str = "exponential") -> DecayStrategy:
    """Get a decay strategy by name from global registry."""
    return get_registry().get_decay(name)


def register_update_strategy(strategy: UpdateStrategy) -> None:
    """Register a custom update strategy."""
    get_registry().register_update(strategy)


def register_decay_strategy(strategy: DecayStrategy) -> None:
    """Register a custom decay strategy."""
    get_registry().register_decay(strategy)
