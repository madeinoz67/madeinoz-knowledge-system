"""
Memory Lifecycle Manager

Feature: 009-memory-decay-scoring
See: specs/009-memory-decay-scoring/data-model.md

This module manages memory lifecycle state transitions:
    ACTIVE -> DORMANT (30 days inactive)
    DORMANT -> ARCHIVED (90 days inactive)
    ARCHIVED -> EXPIRED (180 days inactive, importance < 3)
    EXPIRED -> SOFT_DELETED (maintenance run)
    SOFT_DELETED -> (purged after 90 days)

Any access event reactivates DORMANT/ARCHIVED memories back to ACTIVE.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional, Any

from utils.decay_config import get_decay_config
from utils.decay_types import LifecycleState, is_permanent
from utils.metrics_exporter import get_decay_metrics_exporter

logger = logging.getLogger(__name__)


# ==============================================================================
# Lifecycle Manager
# ==============================================================================

class LifecycleManager:
    """
    Manage memory lifecycle state transitions.

    State machine:
    - ACTIVE: Recently accessed, full relevance
    - DORMANT: Not accessed for 30+ days
    - ARCHIVED: Not accessed for 90+ days
    - EXPIRED: Marked for deletion
    - SOFT_DELETED: Deleted but recoverable for 90 days
    """

    def __init__(self):
        """Initialize lifecycle manager with configuration."""
        config = get_decay_config()
        self.thresholds = config.decay.thresholds
        self.retention_days = config.decay.retention.soft_delete_days

    def calculate_next_state(
        self,
        current_state: str,
        days_inactive: float,
        decay_score: float,
        importance: int,
        stability: int
    ) -> Optional[str]:
        """
        Calculate the next lifecycle state based on thresholds.

        Args:
            current_state: Current lifecycle state
            days_inactive: Days since last access
            decay_score: Current decay score (0.0-1.0)
            importance: Importance score (1-5)
            stability: Stability score (1-5)

        Returns:
            Next state if transition should occur, None otherwise
        """
        # Permanent memories never transition
        if is_permanent(importance, stability):
            return None

        # SOFT_DELETED is terminal (handled by purge logic)
        if current_state == LifecycleState.SOFT_DELETED.value:
            return None

        # Check transitions in order of severity
        if current_state == LifecycleState.EXPIRED.value:
            # EXPIRED -> SOFT_DELETED happens during maintenance
            return LifecycleState.SOFT_DELETED.value

        if current_state == LifecycleState.ARCHIVED.value:
            # Check for ARCHIVED -> EXPIRED
            threshold = self.thresholds.expired
            if (days_inactive >= threshold.days and
                decay_score >= threshold.decay_score and
                importance <= (threshold.max_importance or 5)):
                return LifecycleState.EXPIRED.value
            return None

        if current_state == LifecycleState.DORMANT.value:
            # Check for DORMANT -> ARCHIVED
            threshold = self.thresholds.archived
            if days_inactive >= threshold.days and decay_score >= threshold.decay_score:
                return LifecycleState.ARCHIVED.value
            return None

        if current_state == LifecycleState.ACTIVE.value:
            # Check for ACTIVE -> DORMANT
            threshold = self.thresholds.dormant
            if days_inactive >= threshold.days and decay_score >= threshold.decay_score:
                return LifecycleState.DORMANT.value
            return None

        # Unknown state - no transition
        logger.warning(f"Unknown lifecycle state: {current_state}")
        return None

    def should_reactivate(self, current_state: str) -> bool:
        """
        Check if state should be reactivated on access.

        DORMANT and ARCHIVED memories become ACTIVE when accessed.

        Args:
            current_state: Current lifecycle state

        Returns:
            True if state should transition to ACTIVE
        """
        return current_state in (
            LifecycleState.DORMANT.value,
            LifecycleState.ARCHIVED.value
        )

    def can_recover(self, soft_deleted_at: Optional[str]) -> bool:
        """
        Check if a soft-deleted memory can still be recovered.

        Recovery is allowed within 90-day retention window.

        Args:
            soft_deleted_at: ISO timestamp when memory was soft-deleted

        Returns:
            True if recovery is still possible
        """
        if soft_deleted_at is None:
            return False

        try:
            deleted_time = datetime.fromisoformat(soft_deleted_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            days_since_delete = (now - deleted_time).days
            return days_since_delete < self.retention_days
        except Exception as e:
            logger.warning(f"Error parsing soft_deleted_at: {e}")
            return False

    def should_purge(self, soft_deleted_at: Optional[str]) -> bool:
        """
        Check if a soft-deleted memory should be permanently deleted.

        Purge happens after 90-day retention window expires.

        Args:
            soft_deleted_at: ISO timestamp when memory was soft-deleted

        Returns:
            True if memory should be permanently deleted
        """
        if soft_deleted_at is None:
            return False

        try:
            deleted_time = datetime.fromisoformat(soft_deleted_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            days_since_delete = (now - deleted_time).days
            return days_since_delete >= self.retention_days
        except Exception as e:
            logger.warning(f"Error parsing soft_deleted_at: {e}")
            return False


# ==============================================================================
# Cypher Queries for Batch Operations
# ==============================================================================

# Reactivation on access (atomic update) - returns metadata for metrics
REACTIVATE_ON_ACCESS_QUERY = """
CALL {
    WITH $nodeUuid AS uuid
    MATCH (n:Entity {uuid: uuid})
    WHERE n.`attributes.lifecycle_state` IN ['DORMANT', 'ARCHIVED']
    WITH n,
         n.`attributes.lifecycle_state` AS prevState,
         coalesce(n.`attributes.importance`, 3) AS importance,
         CASE
             WHEN n.`attributes.last_accessed_at` IS NOT NULL
                 THEN duration.between(datetime(n.`attributes.last_accessed_at`), datetime()).days
             ELSE 0
         END AS daysSinceAccess
    SET n.`attributes.lifecycle_state` = 'ACTIVE',
        n.`attributes.last_accessed_at` = toString(datetime()),
        n.`attributes.access_count` = coalesce(n.`attributes.access_count`, 0) + 1,
        n.`attributes.decay_score` = 0.0
    RETURN n.uuid AS updated, prevState, importance, daysSinceAccess
}
RETURN updated, prevState, importance, daysSinceAccess
"""

# Update access timestamp without state change - returns metadata for metrics
UPDATE_ACCESS_QUERY = """
MATCH (n:Entity {uuid: $nodeUuid})
WITH n,
     n.`attributes.lifecycle_state` AS currentState,
     coalesce(n.`attributes.importance`, 3) AS importance,
     CASE
         WHEN n.`attributes.last_accessed_at` IS NOT NULL
             THEN duration.between(datetime(n.`attributes.last_accessed_at`), datetime()).days
         ELSE 0
     END AS daysSinceAccess
SET n.`attributes.last_accessed_at` = toString(datetime()),
    n.`attributes.access_count` = coalesce(n.`attributes.access_count`, 0) + 1,
    n.`attributes.decay_score` = 0.0
RETURN n.uuid AS updated, currentState, importance, daysSinceAccess
"""

# Batch state transitions
BATCH_STATE_TRANSITION_QUERY = """
MATCH (n:Entity)
WHERE n.`attributes.lifecycle_state` IS NOT NULL
  AND n.`attributes.lifecycle_state` <> 'SOFT_DELETED'
  AND NOT (coalesce(n.`attributes.importance`, 3) >= 4 AND coalesce(n.`attributes.stability`, 3) >= 4)

WITH n,
     CASE
         WHEN n.`attributes.last_accessed_at` IS NOT NULL
             THEN duration.between(datetime(n.`attributes.last_accessed_at`), datetime()).days
         WHEN n.created_at IS NOT NULL
             THEN duration.between(datetime(n.created_at), datetime()).days
         ELSE 0
     END AS daysInactive,
     coalesce(n.`attributes.decay_score`, 0.0) AS decayScore,
     coalesce(n.`attributes.importance`, 3) AS importance,
     n.`attributes.lifecycle_state` AS currentState

WITH n, daysInactive, decayScore, importance, currentState,
     CASE
         WHEN currentState = 'ACTIVE' AND daysInactive >= $dormantDays AND decayScore >= $dormantDecay
             THEN 'DORMANT'
         WHEN currentState = 'DORMANT' AND daysInactive >= $archivedDays AND decayScore >= $archivedDecay
             THEN 'ARCHIVED'
         WHEN currentState = 'ARCHIVED' AND daysInactive >= $expiredDays AND decayScore >= $expiredDecay AND importance <= $expiredMaxImportance
             THEN 'EXPIRED'
         WHEN currentState = 'EXPIRED'
             THEN 'SOFT_DELETED'
         ELSE null
     END AS newState

WHERE newState IS NOT NULL
SET n.`attributes.lifecycle_state` = newState,
    n.`attributes.soft_deleted_at` = CASE WHEN newState = 'SOFT_DELETED' THEN toString(datetime()) ELSE n.`attributes.soft_deleted_at` END

RETURN
    sum(CASE WHEN currentState = 'ACTIVE' AND newState = 'DORMANT' THEN 1 ELSE 0 END) AS active_to_dormant,
    sum(CASE WHEN currentState = 'DORMANT' AND newState = 'ARCHIVED' THEN 1 ELSE 0 END) AS dormant_to_archived,
    sum(CASE WHEN currentState = 'ARCHIVED' AND newState = 'EXPIRED' THEN 1 ELSE 0 END) AS archived_to_expired,
    sum(CASE WHEN currentState = 'EXPIRED' AND newState = 'SOFT_DELETED' THEN 1 ELSE 0 END) AS expired_to_soft_deleted
"""

# Purge soft-deleted memories past retention window
PURGE_SOFT_DELETED_QUERY = """
MATCH (n:Entity)
WHERE n.`attributes.lifecycle_state` = 'SOFT_DELETED'
  AND n.`attributes.soft_deleted_at` IS NOT NULL
  AND duration.between(datetime(n.`attributes.soft_deleted_at`), datetime()).days >= $retentionDays

DETACH DELETE n

RETURN count(*) AS purged
"""

# Recover soft-deleted memory
RECOVER_SOFT_DELETED_QUERY = """
MATCH (n:Entity {uuid: $nodeUuid})
WHERE n.`attributes.lifecycle_state` = 'SOFT_DELETED'
  AND n.`attributes.soft_deleted_at` IS NOT NULL
  AND duration.between(datetime(n.`attributes.soft_deleted_at`), datetime()).days < $retentionDays

SET n.`attributes.lifecycle_state` = 'ARCHIVED',
    n.`attributes.soft_deleted_at` = null,
    n.`attributes.decay_score` = 0.5

RETURN n.uuid AS recovered, n.name AS name
"""


@dataclass
class StateTransitionResult:
    """Result of batch state transitions."""
    active_to_dormant: int = 0
    dormant_to_archived: int = 0
    archived_to_expired: int = 0
    expired_to_soft_deleted: int = 0

    @property
    def total(self) -> int:
        return (
            self.active_to_dormant +
            self.dormant_to_archived +
            self.archived_to_expired +
            self.expired_to_soft_deleted
        )

    def to_dict(self) -> dict:
        return {
            "active_to_dormant": self.active_to_dormant,
            "dormant_to_archived": self.dormant_to_archived,
            "archived_to_expired": self.archived_to_expired,
            "expired_to_soft_deleted": self.expired_to_soft_deleted,
        }


async def update_access_on_retrieval(driver, node_uuid: str, previous_state: Optional[str] = None) -> bool:
    """
    Update access tracking when a node is retrieved.

    This reactivates DORMANT/ARCHIVED memories and resets decay score.
    Also records access pattern metrics for observability.

    Args:
        driver: Neo4j driver instance
        node_uuid: UUID of the retrieved node
        previous_state: Optional previous state for metrics tracking

    Returns:
        True if node was updated
    """
    decay_metrics = get_decay_metrics_exporter()

    async with driver.session() as session:
        # Try reactivation first (handles DORMANT/ARCHIVED)
        result = await session.run(REACTIVATE_ON_ACCESS_QUERY, nodeUuid=node_uuid)
        record = await result.single()
        if record and record["updated"]:
            logger.debug(f"Reactivated node {node_uuid}")

            # Extract metrics data from query result
            prev_state = record.get("prevState", previous_state or "DORMANT")
            importance = record.get("importance", 3)
            days_since_access = record.get("daysSinceAccess", 0)

            if decay_metrics:
                # Record lifecycle transition and reactivation
                decay_metrics.record_lifecycle_transition(prev_state, "ACTIVE")
                decay_metrics.record_reactivation(prev_state)
                # Record access pattern metrics
                decay_metrics.record_access_pattern(
                    importance=importance,
                    lifecycle_state=prev_state,
                    days_since_last_access=float(days_since_access) if days_since_access else None
                )

            return True

        # Fall back to simple access update (for ACTIVE nodes)
        result = await session.run(UPDATE_ACCESS_QUERY, nodeUuid=node_uuid)
        record = await result.single()
        if record and record["updated"]:
            logger.debug(f"Updated access for node {node_uuid}")

            # Extract metrics data from query result
            current_state = record.get("currentState", "ACTIVE")
            importance = record.get("importance", 3)
            days_since_access = record.get("daysSinceAccess", 0)

            # Record access pattern metrics for regular access
            if decay_metrics:
                decay_metrics.record_access_pattern(
                    importance=importance,
                    lifecycle_state=current_state,
                    days_since_last_access=float(days_since_access) if days_since_access else None
                )

            return True

        return False


async def batch_transition_states(driver) -> StateTransitionResult:
    """
    Run batch state transitions for all eligible memories.

    Transitions are determined by decay thresholds and time inactive.

    Args:
        driver: Neo4j driver instance

    Returns:
        StateTransitionResult with transition counts
    """
    config = get_decay_config()
    thresholds = config.decay.thresholds

    async with driver.session() as session:
        result = await session.run(
            BATCH_STATE_TRANSITION_QUERY,
            dormantDays=thresholds.dormant.days,
            dormantDecay=thresholds.dormant.decay_score,
            archivedDays=thresholds.archived.days,
            archivedDecay=thresholds.archived.decay_score,
            expiredDays=thresholds.expired.days,
            expiredDecay=thresholds.expired.decay_score,
            expiredMaxImportance=thresholds.expired.max_importance or 5,
        )
        record = await result.single()

        if record:
            return StateTransitionResult(
                active_to_dormant=record["active_to_dormant"],
                dormant_to_archived=record["dormant_to_archived"],
                archived_to_expired=record["archived_to_expired"],
                expired_to_soft_deleted=record["expired_to_soft_deleted"],
            )

        return StateTransitionResult()


async def purge_expired_soft_deletes(driver) -> int:
    """
    Permanently delete soft-deleted memories past retention window.

    Args:
        driver: Neo4j driver instance

    Returns:
        Number of memories permanently deleted
    """
    config = get_decay_config()
    retention_days = config.decay.retention.soft_delete_days

    async with driver.session() as session:
        result = await session.run(PURGE_SOFT_DELETED_QUERY, retentionDays=retention_days)
        record = await result.single()
        purged = record["purged"] if record else 0

        if purged > 0:
            logger.info(f"Purged {purged} soft-deleted memories past {retention_days}-day retention")

        return purged


async def recover_soft_deleted(driver, node_uuid: str) -> Optional[dict]:
    """
    Recover a soft-deleted memory within retention window.

    Args:
        driver: Neo4j driver instance
        node_uuid: UUID of the memory to recover

    Returns:
        Dictionary with recovered memory info, or None if recovery failed
    """
    config = get_decay_config()
    retention_days = config.decay.retention.soft_delete_days

    async with driver.session() as session:
        result = await session.run(
            RECOVER_SOFT_DELETED_QUERY,
            nodeUuid=node_uuid,
            retentionDays=retention_days
        )
        record = await result.single()

        if record and record["recovered"]:
            logger.info(f"Recovered soft-deleted memory: {record['name']} ({node_uuid})")

            # Record recovery as reverse transition
            decay_metrics = get_decay_metrics_exporter()
            if decay_metrics:
                decay_metrics.record_lifecycle_transition("SOFT_DELETED", "ARCHIVED")

            return {
                "uuid": record["recovered"],
                "name": record["name"],
                "new_state": LifecycleState.ARCHIVED.value,
            }

        return None
