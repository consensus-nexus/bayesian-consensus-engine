"""Tests for multi-market abstraction."""

import pytest

from bayesian_engine.market import (
    MarketId,
    Market,
    MarketStatus,
    MarketStore,
    CrossMarketAggregator,
    SourcePerformance,
)


class TestMarketId:
    """Test MarketId."""
    
    def test_create_market_id(self):
        """Create a market ID."""
        mid = MarketId("crypto-btc-1")
        assert str(mid) == "crypto-btc-1"
    
    def test_empty_market_id_raises(self):
        """Empty market ID raises error."""
        with pytest.raises(ValueError):
            MarketId("")
    
    def test_category_extraction(self):
        """Extract category from categorized ID."""
        mid = MarketId("crypto:btc:price")
        assert mid.category == "crypto"
    
    def test_no_category(self):
        """No category for simple ID."""
        mid = MarketId("simple-id")
        assert mid.category is None
    
    def test_parts(self):
        """Split into parts."""
        mid = MarketId("crypto:btc:price")
        assert mid.parts == ["crypto", "btc", "price"]
    
    def test_matches_exact(self):
        """Exact match."""
        mid = MarketId("crypto:btc:1")
        assert mid.matches("crypto:btc:1")
        assert not mid.matches("crypto:btc:2")
    
    def test_matches_wildcard(self):
        """Wildcard match."""
        mid = MarketId("crypto:btc:1")
        assert mid.matches("crypto:*:1")
        assert mid.matches("crypto:*")
        assert mid.matches("*")
        assert not mid.matches("sports:*")


class TestMarket:
    """Test Market."""
    
    def test_create_market(self):
        """Create a market."""
        market = Market(id=MarketId("test-1"))
        assert market.status == MarketStatus.OPEN
        assert len(market.signals) == 0
    
    def test_add_signal(self):
        """Add signal to market."""
        market = Market(id=MarketId("test-1"))
        market.add_signal({"sourceId": "agent-a", "probability": 0.7})
        assert len(market.signals) == 1
    
    def test_add_signal_to_closed_market_raises(self):
        """Cannot add signal to closed market."""
        market = Market(id=MarketId("test-1"), status=MarketStatus.CLOSED)
        with pytest.raises(ValueError):
            market.add_signal({"sourceId": "agent-a", "probability": 0.7})
    
    def test_compute_consensus_empty(self):
        """Consensus on empty market returns None."""
        market = Market(id=MarketId("test-1"))
        result = market.compute_consensus()
        assert result["consensus"] is None
    
    def test_compute_consensus_with_signals(self):
        """Consensus with signals."""
        market = Market(id=MarketId("test-1"))
        market.add_signal({"sourceId": "agent-a", "probability": 0.7})
        market.add_signal({"sourceId": "agent-b", "probability": 0.8})
        result = market.compute_consensus()
        assert result["consensus"] == 0.75  # Average
    
    def test_resolve_market(self):
        """Resolve market with outcome."""
        market = Market(id=MarketId("test-1"))
        market.resolve(outcome=True)
        assert market.status == MarketStatus.RESOLVED
        assert market.outcome is True
        assert market.resolved_at is not None


class TestMarketStore:
    """Test MarketStore."""
    
    def test_create_and_get_market(self):
        """Create and retrieve market."""
        store = MarketStore()
        market = store.create_market(MarketId("test-1"))
        
        retrieved = store.get_market(MarketId("test-1"))
        assert retrieved is market
    
    def test_create_duplicate_raises(self):
        """Cannot create duplicate market."""
        store = MarketStore()
        store.create_market(MarketId("test-1"))
        
        with pytest.raises(ValueError):
            store.create_market(MarketId("test-1"))
    
    def test_get_or_create(self):
        """Get or create returns existing or new."""
        store = MarketStore()
        
        m1 = store.get_or_create(MarketId("test-1"))
        assert m1.status == MarketStatus.OPEN
        
        m2 = store.get_or_create(MarketId("test-1"))
        assert m2 is m1
    
    def test_add_signal_creates_market(self):
        """Adding signal creates market if needed."""
        store = MarketStore()
        store.add_signal(MarketId("test-1"), {"sourceId": "agent-a", "probability": 0.7})
        
        market = store.get_market(MarketId("test-1"))
        assert market is not None
        assert len(market.signals) == 1
    
    def test_list_markets_by_status(self):
        """List markets filtered by status."""
        store = MarketStore()
        store.create_market(MarketId("open-1"))
        m2 = store.create_market(MarketId("resolved-1"))
        m2.resolve(True)
        
        open_markets = store.list_markets(status=MarketStatus.OPEN)
        assert len(open_markets) == 1
        assert open_markets[0].id.value == "open-1"
    
    def test_list_markets_by_pattern(self):
        """List markets matching pattern."""
        store = MarketStore()
        store.create_market(MarketId("crypto:btc:1"))
        store.create_market(MarketId("crypto:eth:1"))
        store.create_market(MarketId("sports:nba:1"))
        
        crypto_markets = store.list_markets(pattern="crypto:*")
        assert len(crypto_markets) == 2


class TestCrossMarketAggregator:
    """Test CrossMarketAggregator."""
    
    @pytest.fixture
    def populated_store(self):
        """Create store with resolved markets."""
        store = MarketStore()
        
        # Market 1: both correct
        m1 = store.create_market(MarketId("crypto:btc:1"))
        m1.add_signal({"sourceId": "agent-a", "probability": 0.8})
        m1.add_signal({"sourceId": "agent-b", "probability": 0.7})
        m1.resolve(outcome=True)  # Both predicted True
        
        # Market 2: agent-a correct, agent-b wrong
        m2 = store.create_market(MarketId("crypto:btc:2"))
        m2.add_signal({"sourceId": "agent-a", "probability": 0.6})
        m2.add_signal({"sourceId": "agent-b", "probability": 0.3})
        m2.resolve(outcome=True)  # agent-a right, agent-b wrong
        
        return store
    
    def test_summarize_sources(self, populated_store):
        """Summarize source performance."""
        aggregator = CrossMarketAggregator(populated_store)
        performance = aggregator.summarize_sources()
        
        assert "agent-a" in performance
        assert "agent-b" in performance
        
        # agent-a: 2 correct, 0 wrong
        assert performance["agent-a"].correct_predictions == 2
        assert performance["agent-a"].accuracy == 1.0
        
        # agent-b: 1 correct, 1 wrong
        assert performance["agent-b"].correct_predictions == 1
        assert performance["agent-b"].accuracy == 0.5
    
    def test_summarize_with_pattern(self, populated_store):
        """Summarize with pattern filter."""
        aggregator = CrossMarketAggregator(populated_store)
        performance = aggregator.summarize_sources(patterns=["crypto:*"])
        
        assert len(performance) == 2
    
    def test_summarize_category(self, populated_store):
        """Summarize category."""
        aggregator = CrossMarketAggregator(populated_store)
        summary = aggregator.summarize_category("crypto")
        
        assert summary["category"] == "crypto"
        assert summary["resolved"] == 2
    
    def test_aggregate_consensus_weighted_average(self, populated_store):
        """Aggregate consensus with weighted average."""
        # Compute consensus first
        for market in populated_store.list_markets():
            market.compute_consensus()
        
        aggregator = CrossMarketAggregator(populated_store)
        result = aggregator.aggregate_consensus(
            patterns=["crypto:*"],
            method="weighted_average",
        )
        
        assert result["consensus"] is not None
        assert result["marketsIncluded"] == 2
    
    def test_aggregate_consensus_majority(self, populated_store):
        """Aggregate consensus with majority vote."""
        for market in populated_store.list_markets():
            market.compute_consensus()
        
        aggregator = CrossMarketAggregator(populated_store)
        result = aggregator.aggregate_consensus(
            patterns=["crypto:*"],
            method="majority",
        )
        
        assert result["method"] == "majority"


class TestSourcePerformance:
    """Test SourcePerformance."""
    
    def test_accuracy_calculation(self):
        """Calculate accuracy rate."""
        perf = SourcePerformance(
            source_id="agent-a",
            total_markets=10,
            correct_predictions=7,
            wrong_predictions=3,
            reliability=0.7,
        )
        
        assert perf.accuracy == 0.7
    
    def test_accuracy_no_predictions(self):
        """Accuracy is 0 when no predictions."""
        perf = SourcePerformance(
            source_id="agent-a",
            total_markets=0,
            correct_predictions=0,
            wrong_predictions=0,
            reliability=0.5,
        )
        
        assert perf.accuracy == 0.0
