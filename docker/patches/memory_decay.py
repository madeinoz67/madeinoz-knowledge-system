"""
Memory Decay Calculator

Feature: 009-memory-decay-scoring
See: specs/009-memory-decay-scoring/research.md

This module provides:
- Exponential decay calculation with stability-adjusted half-life
- Weighted search score combining semantic, recency, and importance
- Batch decay score updates for maintenance

Decay Formula:
    decay_score = 1 - exp(-lambda * days_since_access)
    where lambda = ln(2) / half_life_days

Half-Life by Stability:
    1 (volatile):  7 days   (lambda = 0.0990)
    2 (low):      14 days   (lambda = 0.0495)
    3 (moderate): 30 days   (lambda = 0.0231)
    4 (high):     90 days   (lambda = 0.0077)
    5 (permanent): infinity (lambda = 0, never decays)
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from math import exp, log
from typing import Optional, Any

from decay_config import get_decay_config, get_weights
from decay_types import is_permanent

logger = logging.getLogger(__name__)


# ==============================================================================
# Decay Calculator
# ==============================================================================

class DecayCalculator:
    """
    Calculate memory decay scores using exponential half-life model.

    Decay is influenced by:
    - Time since last access (primary factor)
    - Stability level (adjusts half-life)
    - Importance level (slows decay rate)
    """

    def __init__(self, base_half_life: Optional[float] = None):
        """
        Initialize decay calculator.

        Args:
            base_half_life: Base half-life in days. If None, loaded from config.
        """
        if base_half_life is None:
            config = get_decay_config()
            base_half_life = config.decay.base_half_life_days
        self.base_half_life = base_half_life

    def get_stability_adjusted_half_life(self, stability: int) -> float:
        """
        Get half-life adjusted for stability level.

        Higher stability = longer half-life = slower decay.

        Args:
            stability: Stability score (1-5)

        Returns:
            Adjusted half-life in days
        """
        # stability=3 gives base half-life
        # stability=1 gives 1/3 of base (faster decay)
        # stability=5 gives 5/3 of base (slower decay)
        return self.base_half_life * (stability / 3.0)

    def calculate_decay(
        self,
        days_since_access: float,
        importance: int,
        stability: int
    ) -> float:
        """
        Calculate decay score for a memory.

        Args:
            days_since_access: Days since last access or creation
            importance: Importance score (1-5)
            stability: Stability score (1-5)

        Returns:
            Decay score (0.0 = fresh, 1.0 = fully decayed)
        """
        # Permanent memories don't decay
        if is_permanent(importance, stability):
            return 0.0

        # Handle edge case
        if days_since_access <= 0:
            return 0.0

        # Calculate stability-adjusted half-life
        half_life = self.get_stability_adjusted_half_life(stability)

        # Calculate decay rate (lambda)
        lambda_rate = log(2) / half_life

        # Adjust rate by importance (higher importance = slower decay)
        # importance=5 gives 1/5 of rate (very slow)
        # importance=1 gives full rate (fast)
        adjusted_rate = lambda_rate * (6 - importance) / 5.0

        # Calculate decay using exponential formula
        decay_score = 1.0 - exp(-adjusted_rate * days_since_access)

        # Round to 3 decimal places
        return round(decay_score, 3)

    def calculate_from_timestamp(
        self,
        last_accessed_at: Optional[datetime],
        created_at: datetime,
        importance: int,
        stability: int,
        now: Optional[datetime] = None
    ) -> float:
        """
        Calculate decay score from timestamps.

        Args:
            last_accessed_at: Last access timestamp (or None if never accessed)
            created_at: Creation timestamp
            importance: Importance score (1-5)
            stability: Stability score (1-5)
            now: Current timestamp (defaults to now)

        Returns:
            Decay score (0.0 = fresh, 1.0 = fully decayed)
        """
        if now is None:
            now = datetime.now(timezone.utc)

        # Use last access time, or creation time if never accessed
        reference = last_accessed_at or created_at

        # Ensure timezone awareness
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # Calculate days since reference
        days = (now - reference).total_seconds() / 86400.0

        return self.calculate_decay(days, importance, stability)


# ==============================================================================
# Weighted Search Scoring
# ==============================================================================

def calculate_recency_score(
    days_since_access: float,
    half_life: float = 30.0
) -> float:
    """
    Calculate recency score (0-1) for weighted search.

    Uses exponential decay to score freshness.

    Args:
        days_since_access: Days since last access
        half_life: Half-life for recency scoring

    Returns:
        Recency score (1.0 = just accessed, 0.0 = very old)
    """
    if days_since_access <= 0:
        return 1.0

    # Same exponential formula as decay, but inverted interpretation
    lambda_rate = log(2) / half_life
    return exp(-lambda_rate * days_since_access)


def calculate_weighted_score(
    semantic_score: float,
    days_since_access: float,
    importance: int,
    weights: Optional[tuple[float, float, float]] = None,
    recency_half_life: float = 30.0
) -> float:
    """
    Calculate weighted search score combining semantic, recency, and importance.

    Default weights (from spec):
    - Semantic: 60%
    - Recency: 25%
    - Importance: 15%

    Args:
        semantic_score: Vector similarity score (0-1)
        days_since_access: Days since last access
        importance: Importance score (1-5)
        weights: Optional (semantic, recency, importance) weight tuple
        recency_half_life: Half-life for recency calculation

    Returns:
        Weighted score (0-1)
    """
    if weights is None:
        weights = get_weights()

    w_semantic, w_recency, w_importance = weights

    # Calculate component scores
    recency = calculate_recency_score(days_since_access, recency_half_life)
    importance_norm = importance / 5.0  # Normalize to 0-1

    # Combine with weights
    weighted = (
        w_semantic * semantic_score +
        w_recency * recency +
        w_importance * importance_norm
    )

    return round(weighted, 4)


@dataclass
class WeightedSearchResult:
    """
    Search result with weighted scoring breakdown.

    Per contracts/decay-api.yaml WeightedSearchResult schema.
    """
    uuid: str
    name: str
    summary: Optional[str]
    weighted_score: float
    score_breakdown: dict  # {semantic, recency, importance}
    lifecycle_state: str
    importance: int
    stability: int
    decay_score: float
    last_accessed_at: Optional[str]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON response."""
        return {
            "uuid": self.uuid,
            "name": self.name,
            "summary": self.summary,
            "weighted_score": self.weighted_score,
            "score_breakdown": self.score_breakdown,
            "lifecycle_state": self.lifecycle_state,
            "importance": self.importance,
            "stability": self.stability,
            "decay_score": self.decay_score,
            "last_accessed_at": self.last_accessed_at,
        }


def apply_weighted_scoring(
    nodes: list[Any],
    semantic_scores: list[float],
    recency_half_life: float = 30.0
) -> list[WeightedSearchResult]:
    """
    Apply weighted scoring to search results and re-rank.

    Args:
        nodes: List of EntityNode objects from Graphiti search
        semantic_scores: Corresponding semantic similarity scores
        recency_half_life: Half-life for recency calculation

    Returns:
        List of WeightedSearchResult, sorted by weighted_score descending
    """
    weights = get_weights()
    now = datetime.now(timezone.utc)
    results = []

    for node, semantic in zip(nodes, semantic_scores):
        # Extract decay attributes from node
        attrs = node.attributes if hasattr(node, "attributes") else {}
        importance = attrs.get("importance", 3)
        stability = attrs.get("stability", 3)
        decay_score = attrs.get("decay_score", 0.0)
        lifecycle_state = attrs.get("lifecycle_state", "ACTIVE")
        last_accessed_str = attrs.get("last_accessed_at")

        # Calculate days since access
        if last_accessed_str:
            try:
                last_accessed = datetime.fromisoformat(last_accessed_str.replace("Z", "+00:00"))
                days = (now - last_accessed).total_seconds() / 86400.0
            except Exception:
                days = 0.0
        elif hasattr(node, "created_at") and node.created_at:
            created = node.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            days = (now - created).total_seconds() / 86400.0
        else:
            days = 0.0

        # Calculate weighted score
        weighted = calculate_weighted_score(
            semantic_score=semantic,
            days_since_access=days,
            importance=importance,
            weights=weights,
            recency_half_life=recency_half_life
        )

        # Calculate component scores for breakdown
        recency = calculate_recency_score(days, recency_half_life)
        importance_norm = importance / 5.0

        results.append(WeightedSearchResult(
            uuid=node.uuid,
            name=node.name,
            summary=getattr(node, "summary", None),
            weighted_score=weighted,
            score_breakdown={
                "semantic": round(semantic, 4),
                "recency": round(recency, 4),
                "importance": round(importance_norm, 4),
            },
            lifecycle_state=lifecycle_state,
            importance=importance,
            stability=stability,
            decay_score=decay_score,
            last_accessed_at=last_accessed_str,
        ))

    # Sort by weighted score descending
    results.sort(key=lambda r: r.weighted_score, reverse=True)
    return results


# ==============================================================================
# Batch Decay Updates (for maintenance)
# ==============================================================================

BATCH_DECAY_UPDATE_QUERY = """
MATCH (n:Entity)
WHERE n.`attributes.lifecycle_state` IS NOT NULL
  AND n.`attributes.lifecycle_state` <> 'SOFT_DELETED'
  AND NOT (n.`attributes.importance` >= 4 AND n.`attributes.stability` >= 4)

WITH n,
     duration.between(
         datetime(coalesce(n.`attributes.last_accessed_at`, toString(n.created_at))),
         datetime()
     ).days AS daysSinceAccess,
     coalesce(n.`attributes.stability`, 3) AS stability,
     coalesce(n.`attributes.importance`, 3) AS importance

WITH n, daysSinceAccess, stability, importance,
     $baseHalfLife * (stability / 3.0) AS halfLife

WITH n, daysSinceAccess, importance,
     0.693147 / halfLife AS lambdaRate

WITH n, daysSinceAccess,
     lambdaRate * (6 - importance) / 5.0 AS adjustedRate

SET n.`attributes.decay_score` = round(1.0 - exp(-adjustedRate * daysSinceAccess), 3)

RETURN count(n) AS updated
"""


async def batch_update_decay_scores(driver, base_half_life: float = 30.0) -> int:
    """
    Batch update decay scores for all eligible nodes.

    Excludes:
    - SOFT_DELETED nodes
    - PERMANENT nodes (importance >= 4 AND stability >= 4)

    Args:
        driver: Neo4j driver instance
        base_half_life: Base half-life in days

    Returns:
        Number of nodes updated
    """
    async with driver.session() as session:
        result = await session.run(
            BATCH_DECAY_UPDATE_QUERY,
            baseHalfLife=base_half_life
        )
        record = await result.single()
        return record["updated"] if record else 0
