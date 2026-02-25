# Plugin System

The Bayesian Consensus Engine supports pluggable strategies for:

1. **Update strategies** - How reliability changes after outcomes
2. **Decay strategies** - How reliability decays over time

## Built-in Update Strategies

| Strategy | Description | Max Step |
|----------|-------------|----------|
| `default` | Standard Bayesian update | 10% |
| `conservative` | Slower, more cautious updates | 5% |
| `aggressive` | Faster updates for rapid learning | 20% |
| `history-weighted` | Adjusts based on past accuracy | Variable |

## Built-in Decay Strategies

| Strategy | Description |
|----------|-------------|
| `exponential` | Decay toward floor with half-life (default) |
| `linear` | Linear decay toward floor |
| `none` | No decay |

## Using Strategies

```python
from bayesian_engine.plugins import get_update_strategy, get_decay_strategy

# Get a strategy
update = get_update_strategy("conservative")
decay = get_decay_strategy("linear")

# Use in custom logic
from bayesian_engine.plugins import UpdateContext, DecayContext

ctx = UpdateContext(
    current_reliability=0.5,
    current_confidence=0.5,
    outcome_correct=True,
    source_id="agent-a",
    market_id="market-1",
    history=[True, False, True],
)

result = update.compute_update(ctx)
print(f"New reliability: {result.reliability}")
```

## Creating Custom Strategies

### Custom Update Strategy

```python
from bayesian_engine.plugins import UpdateStrategy, UpdateContext, UpdateResult

class MyUpdateStrategy(UpdateStrategy):
    @property
    def name(self):
        return "my-update"
    
    def compute_update(self, ctx: UpdateContext) -> UpdateResult:
        direction = 1.0 if ctx.outcome_correct else -1.0
        
        # Your custom logic here
        delta = direction * 0.05  # 5% step
        new_reliability = ctx.current_reliability + delta
        
        # Confidence grows
        new_confidence = ctx.current_confidence + 0.05
        
        # Validate (clamps to [0, 1])
        new_reliability, new_confidence = self.validate(new_reliability, new_confidence)
        
        return UpdateResult(
            reliability=new_reliability,
            confidence=new_confidence,
            metadata={"custom": True},
        )

# Register it
from bayesian_engine.plugins import register_update_strategy
register_update_strategy(MyUpdateStrategy())

# Use it
strategy = get_update_strategy("my-update")
```

### Custom Decay Strategy

```python
from bayesian_engine.plugins import DecayStrategy, DecayContext, DecayResult

class MyDecayStrategy(DecayStrategy):
    @property
    def name(self):
        return "my-decay"
    
    def compute_decay(self, ctx: DecayContext) -> DecayResult:
        if ctx.elapsed_days <= 0:
            return DecayResult(
                reliability=ctx.current_reliability,
                confidence=ctx.current_confidence,
            )
        
        # Custom decay logic
        decay_factor = 1.0 - (0.02 * ctx.elapsed_days)  # 2% per day
        decayed = ctx.current_reliability * decay_factor
        
        # Validate with floor
        decayed, confidence = self.validate(decayed, ctx.current_confidence, min_reliability=0.10)
        
        return DecayResult(
            reliability=decayed,
            confidence=confidence,
        )

# Register and use
from bayesian_engine.plugins import register_decay_strategy, get_decay_strategy
register_decay_strategy(MyDecayStrategy())
strategy = get_decay_strategy("my-decay")
```

## Strategy Registry

For advanced use, access the global registry directly:

```python
from bayesian_engine.plugins import get_registry

registry = get_registry()

# List available strategies
print(registry.list_update_strategies())
print(registry.list_decay_strategies())

# Get by name
strategy = registry.get_update("default")

# Register custom
registry.register_update(MyUpdateStrategy())
```

## Configuration

Strategies can be configured per-source or per-market by extending the reliability store to use the strategy registry. Future versions will support strategy configuration in the store.
