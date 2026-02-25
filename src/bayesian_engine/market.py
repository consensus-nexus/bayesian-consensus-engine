"""Multi-market abstraction for consensus engine.

This module provides abstractions for managing consensus across multiple
markets or questions. Each market has its own reliability tracking, with
optional cross-market aggregation.

Usage:
    from bayesian_engine.market import (
        MarketId,
        MarketStore,
        CrossMarketAggregator,
    )
    
    # Create market
    market = MarketId("crypto-btc-price-2024-01-01")
    
    # Track signals per market
    store = MarketStore()
    store.add_signal(market, {"sourceId": "agent-a", "probability": 0.7})
    
    # Compute consensus for a market
    result = store.compute_consensus(market)
    
    # Cross-market aggregation
    aggregator = CrossMarketAggregator(store)
    summary = aggregator.summarize_sources(["crypto-*", "sports-*"])
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Iterator
import fnmatch
import re

from bayesian_engine.core import compute_consensus
from bayesian_engine.reliability import SQLiteReliabilityStore, ReliabilityRecord


@dataclass(frozen=True)
class MarketId:
    """Unique identifier for a market or question.
    
    Market IDs can be simple strings or structured with categories:
    - Simple: "btc-price-jan-1"
    - Categorized: "crypto:btc:price:2024-01-01"
    """
    
    value: str
    
    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Market ID cannot be empty")
    
    def __str__(self) -> str:
        return self.value
    
    def __repr__(self) -> str:
        return f"MarketId({self.value!r})"
    
    @property
    def category(self) -> Optional[str]:
        """Extract category if using categorized format (cat:subcat:...)."""
        if ":" in self.value:
            return self.value.split(":")[0]
        return None
    
    @property
    def parts(self) -> List[str]:
        """Split into parts if using categorized format."""
        return self.value.split(":")
    
    def matches(self, pattern: str) -> bool:
        """Check if market ID matches a glob pattern.
        
        Patterns support:
        - Exact match: "crypto:btc:price"
        - Wildcards: "crypto:*:price"
        - Prefix: "crypto:*"
        """
        return fnmatch.fnmatch(self.value, pattern)


class MarketStatus(str, Enum):
    """Status of a market."""
    
    OPEN = "open"          # Accepting signals
    CLOSED = "closed"      # No more signals, outcome pending
    RESOLVED = "resolved"  # Outcome known


@dataclass
class Market:
    """A market with metadata and signals."""
    
    id: MarketId
    status: MarketStatus = MarketStatus.OPEN
    signals: List[Dict[str, Any]] = field(default_factory=list)
    consensus_result: Optional[Dict[str, Any]] = None
    outcome: Optional[bool] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_signal(self, signal: Dict[str, Any]) -> None:
        """Add a signal to this market."""
        if self.status != MarketStatus.OPEN:
            raise ValueError(f"Cannot add signal to {self.status} market")
        self.signals.append(signal)
    
    def compute_consensus(
        self,
        source_reliability: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> Dict[str, Any]:
        """Compute consensus for this market."""
        if not self.signals:
            return {
                "schemaVersion": "1.0.0",
                "consensus": None,
                "confidence": 0.0,
                "marketId": str(self.id),
            }
        
        result = compute_consensus(self.signals, source_reliability)
        result["marketId"] = str(self.id)
        self.consensus_result = result
        return result
    
    def resolve(self, outcome: bool) -> None:
        """Resolve the market with a known outcome."""
        self.outcome = outcome
        self.status = MarketStatus.RESOLVED
        self.resolved_at = datetime.now(timezone.utc).isoformat()


class MarketStore:
    """In-memory store for markets.
    
    Provides:
    - Market creation and retrieval
    - Signal collection per market
    - Consensus computation
    - Query by status or pattern
    """
    
    def __init__(self):
        self._markets: Dict[str, Market] = {}
    
    def create_market(
        self,
        market_id: MarketId,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Market:
        """Create a new market."""
        key = str(market_id)
        if key in self._markets:
            raise ValueError(f"Market {market_id} already exists")
        
        market = Market(
            id=market_id,
            metadata=metadata or {},
        )
        self._markets[key] = market
        return market
    
    def get_market(self, market_id: MarketId) -> Optional[Market]:
        """Get a market by ID."""
        return self._markets.get(str(market_id))
    
    def get_or_create(self, market_id: MarketId) -> Market:
        """Get existing market or create new one."""
        market = self.get_market(market_id)
        if market is None:
            market = self.create_market(market_id)
        return market
    
    def add_signal(self, market_id: MarketId, signal: Dict[str, Any]) -> Market:
        """Add a signal to a market."""
        market = self.get_or_create(market_id)
        market.add_signal(signal)
        return market
    
    def list_markets(
        self,
        status: Optional[MarketStatus] = None,
        pattern: Optional[str] = None,
    ) -> List[Market]:
        """List markets, optionally filtered."""
        markets = list(self._markets.values())
        
        if status is not None:
            markets = [m for m in markets if m.status == status]
        
        if pattern is not None:
            markets = [m for m in markets if m.id.matches(pattern)]
        
        return markets
    
    def compute_all_consensus(
        self,
        reliability_store: Optional[SQLiteReliabilityStore] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Compute consensus for all open markets."""
        results = {}
        for market in self.list_markets(status=MarketStatus.OPEN):
            source_rel = None
            if reliability_store:
                source_rel = {}
                for signal in market.signals:
                    sid = signal["sourceId"]
                    if sid not in source_rel:
                        record = reliability_store.get_reliability(
                            sid, str(market.id), apply_decay=True
                        )
                        source_rel[sid] = {
                            "reliability": record.reliability,
                            "confidence": record.confidence,
                        }
            results[str(market.id)] = market.compute_consensus(source_rel)
        return results


@dataclass
class SourcePerformance:
    """Aggregated performance of a source across markets."""
    
    source_id: str
    total_markets: int
    correct_predictions: int
    wrong_predictions: int
    reliability: float
    markets: List[str] = field(default_factory=list)
    
    @property
    def accuracy(self) -> float:
        """Calculate accuracy rate."""
        total = self.correct_predictions + self.wrong_predictions
        if total == 0:
            return 0.0
        return self.correct_predictions / total


class CrossMarketAggregator:
    """Aggregate data across multiple markets.
    
    Provides:
    - Source performance tracking across markets
    - Category-level summaries
    - Cross-market consensus aggregation
    """
    
    def __init__(self, market_store: MarketStore):
        self._store = market_store
    
    def summarize_sources(
        self,
        patterns: Optional[List[str]] = None,
    ) -> Dict[str, SourcePerformance]:
        """Summarize source performance across markets.
        
        Args:
            patterns: Optional list of market ID patterns to filter
            
        Returns:
            Dict mapping source_id to performance summary
        """
        markets = self._store.list_markets(status=MarketStatus.RESOLVED)
        
        if patterns:
            filtered = []
            for market in markets:
                if any(market.id.matches(p) for p in patterns):
                    filtered.append(market)
            markets = filtered
        
        source_stats: Dict[str, Dict[str, Any]] = {}
        
        for market in markets:
            if market.outcome is None:
                continue
            
            for signal in market.signals:
                sid = signal["sourceId"]
                if sid not in source_stats:
                    source_stats[sid] = {
                        "total": 0,
                        "correct": 0,
                        "wrong": 0,
                        "markets": [],
                    }
                
                source_stats[sid]["total"] += 1
                source_stats[sid]["markets"].append(str(market.id))
                
                # Check if prediction was correct
                # Binary: probability > 0.5 and outcome=True, or < 0.5 and outcome=False
                prob = signal.get("probability", 0.5)
                predicted_true = prob >= 0.5
                
                if predicted_true == market.outcome:
                    source_stats[sid]["correct"] += 1
                else:
                    source_stats[sid]["wrong"] += 1
        
        # Build performance records
        results = {}
        for sid, stats in source_stats.items():
            total = stats["correct"] + stats["wrong"]
            reliability = stats["correct"] / total if total > 0 else 0.5
            
            results[sid] = SourcePerformance(
                source_id=sid,
                total_markets=stats["total"],
                correct_predictions=stats["correct"],
                wrong_predictions=stats["wrong"],
                reliability=reliability,
                markets=stats["markets"],
            )
        
        return results
    
    def summarize_category(self, category: str) -> Dict[str, Any]:
        """Summarize all markets in a category."""
        markets = self._store.list_markets(pattern=f"{category}:*")
        
        resolved = [m for m in markets if m.status == MarketStatus.RESOLVED]
        open_markets = [m for m in markets if m.status == MarketStatus.OPEN]
        
        return {
            "category": category,
            "total_markets": len(markets),
            "resolved": len(resolved),
            "open": len(open_markets),
            "markets": [str(m.id) for m in markets],
        }
    
    def aggregate_consensus(
        self,
        patterns: List[str],
        method: str = "weighted_average",
    ) -> Dict[str, Any]:
        """Aggregate consensus across multiple markets.
        
        Args:
            patterns: Market ID patterns to include
            method: Aggregation method ("weighted_average", "majority", "median")
            
        Returns:
            Aggregated consensus result
        """
        markets = []
        for pattern in patterns:
            markets.extend(self._store.list_markets(pattern=pattern))
        
        if not markets:
            return {
                "schemaVersion": "1.0.0",
                "consensus": None,
                "confidence": 0.0,
                "marketsIncluded": 0,
            }
        
        # Collect all consensus values
        consensuses = []
        for market in markets:
            if market.consensus_result and market.consensus_result.get("consensus") is not None:
                consensuses.append({
                    "marketId": str(market.id),
                    "consensus": market.consensus_result["consensus"],
                    "confidence": market.consensus_result.get("confidence", 0.5),
                })
        
        if not consensuses:
            return {
                "schemaVersion": "1.0.0",
                "consensus": None,
                "confidence": 0.0,
                "marketsIncluded": len(markets),
            }
        
        # Aggregate based on method
        if method == "weighted_average":
            total_weight = sum(c["confidence"] for c in consensuses)
            if total_weight == 0:
                aggregated = sum(c["consensus"] for c in consensuses) / len(consensuses)
            else:
                aggregated = sum(
                    c["consensus"] * c["confidence"] for c in consensuses
                ) / total_weight
        elif method == "median":
            sorted_cons = sorted(c["consensus"] for c in consensuses)
            mid = len(sorted_cons) // 2
            aggregated = sorted_cons[mid]
        elif method == "majority":
            # Binary majority vote
            votes = [1 if c["consensus"] >= 0.5 else 0 for c in consensuses]
            aggregated = sum(votes) / len(votes)
        else:
            raise ValueError(f"Unknown aggregation method: {method}")
        
        return {
            "schemaVersion": "1.0.0",
            "consensus": aggregated,
            "confidence": sum(c["confidence"] for c in consensuses) / len(consensuses),
            "marketsIncluded": len(consensuses),
            "method": method,
        }
