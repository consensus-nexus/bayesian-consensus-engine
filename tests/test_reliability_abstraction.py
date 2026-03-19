"""Tests for reliability abstraction layer."""

import pytest
import tempfile
import os

from bayesian_engine.reliability_abstraction import (
    ReliabilityNamespace,
    NamespacedReliabilityStore,
    NamespacedReliabilityRecord,
)
from bayesian_engine.config import DEFAULT_RELIABILITY, DEFAULT_CONFIDENCE


class TestNamespacedReliabilityStore:
    """Test namespaced reliability store."""
    
    @pytest.fixture
    def store(self):
        """Create a temporary store for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        store = NamespacedReliabilityStore(db_path)
        yield store
        store.close()
        os.unlink(db_path)
    
    def test_cold_start_returns_defaults(self, store):
        """Unknown source returns cold-start defaults."""
        record = store.get_reliability("unknown-source")
        
        assert record.source_id == "unknown-source"
        assert record.namespace == ReliabilityNamespace.GLOBAL
        assert record.reliability == DEFAULT_RELIABILITY
        assert record.confidence == DEFAULT_CONFIDENCE
        assert record.is_fallback is True
    
    def test_global_reliability_set_and_get(self, store):
        """Can set and get global reliability."""
        store.set_global_reliability("agent-a", reliability=0.8, confidence=0.6)
        
        record = store.get_reliability("agent-a")
        
        assert record.reliability == pytest.approx(0.8)
        assert record.confidence == pytest.approx(0.6)
        assert record.namespace == ReliabilityNamespace.GLOBAL
        # Global is considered a fallback when no specific market/domain is requested
        assert record.is_fallback is True
    
    def test_domain_fallback_to_global(self, store):
        """Domain-specific lookup falls back to global."""
        store.set_global_reliability("agent-a", reliability=0.75, confidence=0.5)
        
        # Request domain-specific, should get global
        record = store.get_reliability("agent-a", domain="crypto")
        
        assert record.reliability == pytest.approx(0.75)
        assert record.namespace == ReliabilityNamespace.GLOBAL
        assert record.is_fallback is True
    
    def test_market_fallback_to_domain(self, store):
        """Market-specific lookup falls back to domain."""
        # Update at domain level
        store.update_reliability("agent-a", outcome_correct=True, domain="crypto")
        
        # Request market-specific, should get domain
        record = store.get_reliability("agent-a", market_id="btc-1", domain="crypto")
        
        assert record.namespace == ReliabilityNamespace.DOMAIN
        assert record.namespace_value == "crypto"
        assert record.is_fallback is True
    
    def test_market_specific_no_fallback(self, store):
        """Market-specific lookup returns market data when available."""
        # Update at market level
        store.update_reliability("agent-a", outcome_correct=True, market_id="btc-1")
        
        # Request market-specific
        record = store.get_reliability("agent-a", market_id="btc-1")
        
        assert record.namespace == ReliabilityNamespace.MARKET
        assert record.namespace_value == "btc-1"
        assert record.is_fallback is False
    
    def test_update_reliability_correct_increases(self, store):
        """Correct outcome increases reliability."""
        record = store.update_reliability("agent-a", outcome_correct=True, domain="crypto")
        
        assert record.reliability > DEFAULT_RELIABILITY
        assert record.namespace == ReliabilityNamespace.DOMAIN
    
    def test_update_reliability_wrong_decreases(self, store):
        """Wrong outcome decreases reliability."""
        record = store.update_reliability("agent-a", outcome_correct=False, domain="crypto")
        
        assert record.reliability < DEFAULT_RELIABILITY
    
    def test_update_global_also(self, store):
        """Can update both domain and global in one call."""
        store.update_reliability(
            "agent-a",
            outcome_correct=True,
            domain="crypto",
            update_global=True,
        )
        
        # Check domain was updated
        domain_record = store.get_reliability("agent-a", domain="crypto")
        assert domain_record.namespace == ReliabilityNamespace.DOMAIN
        
        # Check global was also updated
        global_record = store.get_reliability("agent-a")
        assert global_record.reliability > DEFAULT_RELIABILITY
    
    def test_fallback_chain(self, store):
        """Test full fallback chain: market → domain → global → cold-start."""
        # 1. Cold start (no data)
        r1 = store.get_reliability("agent-a", market_id="m1", domain="crypto")
        assert r1.namespace_value == "cold-start"
        
        # 2. Set global
        store.set_global_reliability("agent-a", 0.7, 0.5)
        r2 = store.get_reliability("agent-a", market_id="m1", domain="crypto")
        assert r2.namespace == ReliabilityNamespace.GLOBAL
        assert r2.reliability == pytest.approx(0.7)
        
        # 3. Set domain
        store.update_reliability("agent-a", True, domain="crypto")
        r3 = store.get_reliability("agent-a", market_id="m1", domain="crypto")
        assert r3.namespace == ReliabilityNamespace.DOMAIN
        
        # 4. Set market
        store.update_reliability("agent-a", True, market_id="m1")
        r4 = store.get_reliability("agent-a", market_id="m1", domain="crypto")
        assert r4.namespace == ReliabilityNamespace.MARKET
        assert r4.namespace_value == "m1"


class TestNamespacedReliabilityRecord:
    """Test namespaced reliability record."""
    
    def test_record_is_frozen(self):
        """Record is immutable."""
        record = NamespacedReliabilityRecord(
            source_id="agent-a",
            namespace=ReliabilityNamespace.GLOBAL,
            namespace_value="global",
            reliability=0.8,
            confidence=0.6,
            updated_at="2024-01-01",
            is_fallback=False,
        )
        
        with pytest.raises(Exception):  # FrozenInstanceError
            record.reliability = 0.9
