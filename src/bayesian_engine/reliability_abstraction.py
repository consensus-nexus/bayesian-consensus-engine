"""Reliability abstraction layer with domain-specific and global fallback.

This module provides a namespace-aware reliability model:
- Global reliability: Default reliability for a source across all domains
- Domain-specific reliability: Reliability for a source in a specific domain
- Fallback chain: domain → global → cold-start defaults

Usage:
    from bayesian_engine.reliability_abstraction import (
        ReliabilityNamespace,
        NamespacedReliabilityStore,
    )
    
    store = NamespacedReliabilityStore("reliability.db")
    
    # Get reliability for a source in a specific domain
    record = store.get_reliability("agent-a", market_id="m1", domain="crypto")
    
    # Falls back to global if domain-specific not found
    # Falls back to cold-start defaults if global not found
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Protocol, runtime_checkable

from bayesian_engine.config import DEFAULT_RELIABILITY, DEFAULT_CONFIDENCE
from bayesian_engine.reliability import SQLiteReliabilityStore


class ReliabilityNamespace(str, Enum):
    """Namespace levels for reliability tracking."""
    
    GLOBAL = "global"  # Global reliability (fallback)
    DOMAIN = "domain"  # Domain-specific reliability (e.g., "crypto", "sports")
    MARKET = "market"  # Market-specific reliability (most specific)


@dataclass(frozen=True)
class NamespacedReliabilityRecord:
    """Reliability record with namespace context."""
    
    source_id: str
    namespace: ReliabilityNamespace
    namespace_value: str  # The actual domain/market ID
    reliability: float
    confidence: float
    updated_at: str
    is_fallback: bool  # True if this is a fallback from a less specific namespace


@runtime_checkable
class ReliabilityProvider(Protocol):
    """Protocol for reliability data providers.
    
    Implement this to provide custom reliability data sources.
    """
    
    def get_reliability(
        self,
        source_id: str,
        namespace: ReliabilityNamespace,
        namespace_value: str,
    ) -> Optional[NamespacedReliabilityRecord]:
        """Get reliability for a source in a namespace.
        
        Returns None if no record exists.
        """
        ...
    
    def update_reliability(
        self,
        source_id: str,
        namespace: ReliabilityNamespace,
        namespace_value: str,
        outcome_correct: bool,
    ) -> NamespacedReliabilityRecord:
        """Update reliability based on outcome."""
        ...


class NamespacedReliabilityStore:
    """Reliability store with namespace-aware fallback chain.
    
    Fallback order:
    1. Market-specific (most specific)
    2. Domain-specific
    3. Global (fallback)
    4. Cold-start defaults (if nothing found)
    
    Example:
        store = NamespacedReliabilityStore("reliability.db")
        
        # This will:
        # 1. Look for (source_id="agent-a", market_id="btc-price-1")
        # 2. If not found, look for (source_id="agent-a", domain="crypto")
        # 3. If not found, look for (source_id="agent-a", global)
        # 4. If not found, return cold-start defaults
        record = store.get_reliability(
            source_id="agent-a",
            market_id="btc-price-1",
            domain="crypto",
        )
    """
    
    # Special market ID for global reliability
    GLOBAL_MARKET_ID = "__global__"
    
    def __init__(self, db_path: str = ":memory:"):
        """Initialize the namespaced store.
        
        Args:
            db_path: Path to SQLite database file
        """
        self._store = SQLiteReliabilityStore(db_path)
    
    def get_reliability(
        self,
        source_id: str,
        market_id: Optional[str] = None,
        domain: Optional[str] = None,
        apply_decay: bool = True,
    ) -> NamespacedReliabilityRecord:
        """Get reliability with namespace fallback.
        
        Args:
            source_id: Source identifier
            market_id: Specific market ID (optional)
            domain: Domain category (optional, e.g., "crypto", "sports")
            apply_decay: Whether to apply time decay
            
        Returns:
            NamespacedReliabilityRecord with fallback information
        """
        # Try market-specific first
        if market_id:
            record = self._store.get_reliability(source_id, market_id, apply_decay)
            if record.updated_at:  # Has actual data
                return NamespacedReliabilityRecord(
                    source_id=source_id,
                    namespace=ReliabilityNamespace.MARKET,
                    namespace_value=market_id,
                    reliability=record.reliability,
                    confidence=record.confidence,
                    updated_at=record.updated_at,
                    is_fallback=False,
                )
        
        # Try domain-specific
        if domain:
            domain_market_id = f"__domain__:{domain}"
            record = self._store.get_reliability(source_id, domain_market_id, apply_decay)
            if record.updated_at:  # Has actual data
                return NamespacedReliabilityRecord(
                    source_id=source_id,
                    namespace=ReliabilityNamespace.DOMAIN,
                    namespace_value=domain,
                    reliability=record.reliability,
                    confidence=record.confidence,
                    updated_at=record.updated_at,
                    is_fallback=True,  # This is a fallback from market
                )
        
        # Try global
        record = self._store.get_reliability(source_id, self.GLOBAL_MARKET_ID, apply_decay)
        if record.updated_at:  # Has actual data
            return NamespacedReliabilityRecord(
                source_id=source_id,
                namespace=ReliabilityNamespace.GLOBAL,
                namespace_value="global",
                reliability=record.reliability,
                confidence=record.confidence,
                updated_at=record.updated_at,
                is_fallback=True,  # This is a fallback
            )
        
        # Cold-start defaults
        return NamespacedReliabilityRecord(
            source_id=source_id,
            namespace=ReliabilityNamespace.GLOBAL,
            namespace_value="cold-start",
            reliability=DEFAULT_RELIABILITY,
            confidence=DEFAULT_CONFIDENCE,
            updated_at="",
            is_fallback=True,
        )
    
    def update_reliability(
        self,
        source_id: str,
        outcome_correct: bool,
        market_id: Optional[str] = None,
        domain: Optional[str] = None,
        update_global: bool = False,
    ) -> NamespacedReliabilityRecord:
        """Update reliability based on outcome.
        
        Args:
            source_id: Source identifier
            outcome_correct: Whether the source was correct
            market_id: Update at market level (optional)
            domain: Update at domain level (optional)
            update_global: Also update global reliability
            
        Returns:
            Updated NamespacedReliabilityRecord
        """
        # Determine which level to update
        if market_id:
            namespace = ReliabilityNamespace.MARKET
            namespace_value = market_id
            target_market = market_id
        elif domain:
            namespace = ReliabilityNamespace.DOMAIN
            namespace_value = domain
            target_market = f"__domain__:{domain}"
        else:
            namespace = ReliabilityNamespace.GLOBAL
            namespace_value = "global"
            target_market = self.GLOBAL_MARKET_ID
        
        # Update at the target level
        record = self._store.update_reliability(source_id, target_market, outcome_correct)
        
        # Optionally also update global
        if update_global and namespace != ReliabilityNamespace.GLOBAL:
            self._store.update_reliability(source_id, self.GLOBAL_MARKET_ID, outcome_correct)
        
        return NamespacedReliabilityRecord(
            source_id=source_id,
            namespace=namespace,
            namespace_value=namespace_value,
            reliability=record.reliability,
            confidence=record.confidence,
            updated_at=record.updated_at,
            is_fallback=False,
        )
    
    def set_global_reliability(
        self,
        source_id: str,
        reliability: float,
        confidence: float,
    ) -> NamespacedReliabilityRecord:
        """Set global reliability for a source.
        
        This is useful for seeding a source with known reliability
        before any outcomes are observed.
        """
        # Directly insert/update global reliability
        import sqlite3
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc).isoformat()
        
        conn = sqlite3.connect(self._store._db_path)
        conn.execute(
            """
            INSERT INTO sources (source_id, market_id, reliability, confidence, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(source_id, market_id)
            DO UPDATE SET reliability = excluded.reliability,
                          confidence = excluded.confidence,
                          updated_at = excluded.updated_at
            """,
            (source_id, self.GLOBAL_MARKET_ID, reliability, confidence, now),
        )
        conn.commit()
        conn.close()
        
        return NamespacedReliabilityRecord(
            source_id=source_id,
            namespace=ReliabilityNamespace.GLOBAL,
            namespace_value="global",
            reliability=reliability,
            confidence=confidence,
            updated_at=now,
            is_fallback=False,
        )
    
    def close(self) -> None:
        """Close the underlying store."""
        self._store.close()
    
    def __enter__(self) -> "NamespacedReliabilityStore":
        return self
    
    def __exit__(self, *exc_info: object) -> None:
        self.close()
