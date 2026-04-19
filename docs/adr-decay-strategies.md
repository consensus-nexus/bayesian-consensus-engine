# ADR: Plugin System for Update/Decay Strategies

## Status
**Proposed** (Issue #21)

## Context

The Bayesian Consensus Engine currently uses a hard-coded exponential decay model for reliability scores. As the system evolves, users need the ability to:

1. **Customize decay behavior** - Different markets may need different decay rates or models
2. **Experiment with strategies** - Research may reveal better decay approaches
3. **Disable decay** - Some use cases may not want time-based reliability degradation

Issue #21 asks us to design an extensible plugin system for update and decay strategies.

## Decision

We will implement **Option A: Strategy Pattern (Python)** with the following design:

### Strategy Interface

```python
class DecayStrategy(Protocol):
    def apply(self, reliability: float, elapsed_days: float) -> float:
        """Apply decay to reliability score."""
        ...
    
    def configure(self, **kwargs) -> None:
        """Configure strategy parameters."""
        ...
```

### Built-in Strategies

1. **ExponentialDecay** (default) - Current v0.1 behavior
2. **LinearDecay** - Simple linear decay
3. **NoDecay** - Disable decay (useful for testing)

### Registry Pattern

```python
# Get strategy by name
strategy = get_strategy("exponential", half_life_days=60)

# Register custom strategy
register_strategy("my-custom", MyCustomStrategy)
```

### CLI Integration

```bash
# Use built-in strategy
bayesian-consensus --decay-strategy exponential --half-life 60

# Use custom strategy (future: dynamic loading)
bayesian-consensus --decay-strategy path/to/module.py:CustomStrategy
```

## Rationale

### Why Strategy Pattern over Dynamic Loading?

**Pros:**
- **Simpler** - No import machinery, module loading, or sandboxing concerns
- **Type-safe** - Protocol validation catches errors early
- **Testable** - Easy to mock and test
- **Documented** - Strategies are discoverable in code

**Cons:**
- **Requires code change** - Adding strategies requires modifying codebase
- **No runtime plugins** - Users can't drop in .py files without rebuilding

**Decision:** Start with Strategy Pattern for v0.2. Add dynamic loading in v0.3 if users need it.

### Why Protocol Instead of Abstract Base Class?

**Protocol benefits:**
- **Structural subtyping** - Any class with matching methods works
- **No inheritance required** - Cleaner composition
- **Runtime checking** - `isinstance(obj, DecayStrategy)` works with `@runtime_checkable`

### Default Strategy

**Exponential decay** remains the default for v0.2 to maintain backward compatibility with v0.1.

## Consequences

### Positive

1. **Extensible** - Easy to add new strategies without modifying core code
2. **Testable** - Strategies can be unit tested independently
3. **Type-safe** - Protocol ensures all strategies implement required methods
4. **Backward compatible** - Default behavior unchanged from v0.1

### Negative

1. **Limited runtime extension** - Can't load strategies from external files (yet)
2. **Manual registration** - Custom strategies need explicit registration

### Neutral

1. **Configuration approach** - Strategies configured via CLI flags or config file (not both)
2. **Documentation burden** - Need strategy author guide for contributors

## Implementation Plan

### Phase 1: Core Infrastructure (This PR)
- [x] Define DecayStrategy protocol
- [x] Implement ExponentialDecay (extract from decay.py)
- [x] Implement LinearDecay (example alternative)
- [x] Implement NoDecay (for testing)
- [x] Create strategy registry
- [x] Add unit tests

### Phase 2: Integration (Next PR)
- [ ] Update CLI to accept --decay-strategy
- [ ] Update decay.py to use strategy system
- [ ] Add config file support for strategy selection
- [ ] Integration tests

### Phase 3: Documentation (Future)
- [ ] Strategy author guide
- [ ] Example custom strategies
- [ ] Migration guide for v0.1 users

## Alternatives Considered

### Option B: Dynamic Module Loading

```python
# Load strategy from external file
strategy = load_strategy("path/to/custom_decay.py")
```

**Pros:**
- Runtime extensibility
- No code modification needed

**Cons:**
- Security concerns (sandboxing arbitrary code)
- Import machinery complexity
- Harder to debug and test
- Version compatibility issues

**Decision:** Too complex for v0.2. Consider for v0.3 if needed.

### Option C: Hybrid (Built-in + Dynamic)

Combine Strategy Pattern with optional dynamic loading.

**Decision:** Premature optimization. Start simple, add complexity when needed.

## References

- Issue #21: Planning: Plugin System for Update/Decay Strategies
- Issue #17: Epic - v0.2 Reliability Abstraction & Extensibility
- PRD §7.B: Reliability System (exponential decay specification)
