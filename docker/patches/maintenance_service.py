"""
Maintenance Service for Memory Decay

Feature: 009-memory-decay-scoring
See: specs/009-memory-decay-scoring/contracts/decay-api.yaml

This module provides:
- Batch decay score recalculation
- Lifecycle state transitions
- Soft-delete cleanup (purge past retention)
- Health metrics aggregation

Performance target: Complete within 10 minutes.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Any

from utils.decay_config import get_decay_config
from utils.decay_types import LifecycleState
from utils.importance_classifier import classify_unclassified_nodes
from utils.lifecycle_manager import (
    batch_transition_states,
    purge_expired_soft_deletes,
    StateTransitionResult,
)
from utils.memory_decay import batch_update_decay_scores
from utils.metrics_exporter import get_decay_metrics_exporter

logger = logging.getLogger(__name__)


# ==============================================================================
# Maintenance Response Types
# ==============================================================================

@dataclass
class ClassificationResult:
    """Result of classifying unclassified nodes."""
    found: int = 0
    classified: int = 0
    failed: int = 0
    using_llm: bool = False

    def to_dict(self) -> dict:
        return {
            "found": self.found,
            "classified": self.classified,
            "failed": self.failed,
            "using_llm": self.using_llm,
        }


@dataclass
class MaintenanceResult:
    """
    Result of a maintenance run.

    Per contracts/decay-api.yaml MaintenanceResponse schema.
    """
    success: bool = True
    memories_processed: int = 0
    nodes_classified: ClassificationResult = field(default_factory=ClassificationResult)
    decay_scores_updated: int = 0
    state_transitions: StateTransitionResult = field(default_factory=StateTransitionResult)
    soft_deleted_purged: int = 0
    duration_seconds: float = 0.0
    completed_at: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "memories_processed": self.memories_processed,
            "nodes_classified": self.nodes_classified.to_dict(),
            "decay_scores_updated": self.decay_scores_updated,
            "state_transitions": self.state_transitions.to_dict(),
            "soft_deleted_purged": self.soft_deleted_purged,
            "duration_seconds": round(self.duration_seconds, 2),
            "completed_at": self.completed_at,
            "error": self.error,
        }


@dataclass
class HealthMetrics:
    """
    Knowledge graph health metrics.

    Per contracts/decay-api.yaml HealthResponse schema.
    """
    # Counts by lifecycle state
    states: dict = field(default_factory=lambda: {
        "active": 0,
        "dormant": 0,
        "archived": 0,
        "expired": 0,
        "soft_deleted": 0,
        "permanent": 0,
    })

    # Aggregates
    aggregates: dict = field(default_factory=lambda: {
        "total": 0,
        "average_decay": 0.0,
        "average_importance": 0.0,
        "average_stability": 0.0,
        "orphan_entities": 0,
    })

    # Age distribution
    age_distribution: dict = field(default_factory=lambda: {
        "under_7_days": 0,
        "days_7_to_30": 0,
        "days_30_to_90": 0,
        "over_90_days": 0,
    })

    # Importance distribution
    importance_distribution: dict = field(default_factory=lambda: {
        "trivial": 0,     # Importance level 1
        "low": 0,         # Importance level 2
        "moderate": 0,    # Importance level 3
        "high": 0,        # Importance level 4
        "core": 0,        # Importance level 5
    })

    # Last maintenance info
    maintenance: dict = field(default_factory=lambda: {
        "last_run": None,
        "duration_seconds": 0.0,
        "processed": 0,
        "transitions": 0,
    })

    # Timestamp
    generated_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "states": self.states,
            "aggregates": self.aggregates,
            "age_distribution": self.age_distribution,
            "importance_distribution": self.importance_distribution,
            "maintenance": self.maintenance,
            "generated_at": self.generated_at,
        }


# ==============================================================================
# Health Metrics Queries
# ==============================================================================

HEALTH_STATES_QUERY = """
MATCH (n:Entity)
WHERE n.`attributes.lifecycle_state` IS NOT NULL

WITH n,
     n.`attributes.lifecycle_state` AS state,
     coalesce(n.`attributes.importance`, 3) AS importance,
     coalesce(n.`attributes.stability`, 3) AS stability

RETURN
    sum(CASE WHEN state = 'ACTIVE' THEN 1 ELSE 0 END) AS active,
    sum(CASE WHEN state = 'DORMANT' THEN 1 ELSE 0 END) AS dormant,
    sum(CASE WHEN state = 'ARCHIVED' THEN 1 ELSE 0 END) AS archived,
    sum(CASE WHEN state = 'EXPIRED' THEN 1 ELSE 0 END) AS expired,
    sum(CASE WHEN state = 'SOFT_DELETED' THEN 1 ELSE 0 END) AS soft_deleted,
    sum(CASE WHEN importance >= 4 AND stability >= 4 THEN 1 ELSE 0 END) AS permanent,
    count(n) AS total
"""

HEALTH_IMPORTANCE_DISTRIBUTION_QUERY = """
MATCH (n:Entity)
WHERE n.`attributes.lifecycle_state` IS NOT NULL
  AND n.`attributes.lifecycle_state` <> 'SOFT_DELETED'

WITH coalesce(n.`attributes.importance`, 3) AS importance

RETURN
    sum(CASE WHEN importance = 1 THEN 1 ELSE 0 END) AS trivial,
    sum(CASE WHEN importance = 2 THEN 1 ELSE 0 END) AS low,
    sum(CASE WHEN importance = 3 THEN 1 ELSE 0 END) AS moderate,
    sum(CASE WHEN importance = 4 THEN 1 ELSE 0 END) AS high,
    sum(CASE WHEN importance = 5 THEN 1 ELSE 0 END) AS core
"""

HEALTH_AGGREGATES_QUERY = """
MATCH (n:Entity)
WHERE n.`attributes.lifecycle_state` IS NOT NULL
  AND n.`attributes.lifecycle_state` <> 'SOFT_DELETED'

RETURN
    avg(coalesce(n.`attributes.decay_score`, 0.0)) AS avg_decay,
    avg(coalesce(n.`attributes.importance`, 3.0)) AS avg_importance,
    avg(coalesce(n.`attributes.stability`, 3.0)) AS avg_stability
"""

HEALTH_AGE_DISTRIBUTION_QUERY = """
MATCH (n:Entity)
WHERE n.created_at IS NOT NULL
  AND n.`attributes.lifecycle_state` IS NOT NULL
  AND n.`attributes.lifecycle_state` <> 'SOFT_DELETED'

WITH duration.between(n.created_at, datetime()).days AS age

RETURN
    sum(CASE WHEN age < 7 THEN 1 ELSE 0 END) AS under_7_days,
    sum(CASE WHEN age >= 7 AND age < 30 THEN 1 ELSE 0 END) AS days_7_to_30,
    sum(CASE WHEN age >= 30 AND age < 90 THEN 1 ELSE 0 END) AS days_30_to_90,
    sum(CASE WHEN age >= 90 THEN 1 ELSE 0 END) AS over_90_days
"""

COUNT_MEMORIES_QUERY = """
MATCH (n:Entity)
WHERE n.`attributes.lifecycle_state` IS NOT NULL
  AND n.`attributes.lifecycle_state` <> 'SOFT_DELETED'
RETURN count(n) AS count
"""

# Query to count orphan entities (entities with no relationships)
ORPHAN_ENTITIES_QUERY = """
MATCH (n:Entity)
WHERE n.`attributes.lifecycle_state` IS NOT NULL
  AND n.`attributes.lifecycle_state` <> 'SOFT_DELETED'
  AND NOT ()-[]->(n)
  AND NOT (n)-[]->()
RETURN count(n) AS orphan_count
"""


# ==============================================================================
# Maintenance Service
# ==============================================================================

class MaintenanceService:
    """
    Orchestrate decay maintenance operations.

    Operations:
    1. Recalculate decay scores for all eligible memories
    2. Transition lifecycle states based on thresholds
    3. Purge soft-deleted memories past retention window

    Performance target: Complete within 10 minutes.
    """

    def __init__(
        self,
        driver,
        llm_client: Any = None,
        batch_size: Optional[int] = None,
        max_duration_minutes: Optional[int] = None
    ):
        """
        Initialize maintenance service.

        Args:
            driver: Neo4j driver instance
            llm_client: Optional Graphiti LLM client for classification
            batch_size: Override batch size from config
            max_duration_minutes: Override max duration from config
        """
        self.driver = driver
        self._llm_client = llm_client  # For importance/stability classification
        config = get_decay_config()
        self.batch_size = batch_size or config.decay.maintenance.batch_size
        self.max_duration_minutes = max_duration_minutes or config.decay.maintenance.max_duration_minutes
        self.base_half_life = config.decay.base_half_life_days

        # Log the driver connection info for debugging
        logger.info(f"MaintenanceService initialized with driver: {driver}")

        # Scheduled maintenance settings
        self.schedule_interval_hours = config.decay.maintenance.schedule_interval_hours
        self._scheduled_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        # Track last maintenance for health metrics
        self._last_result: Optional[MaintenanceResult] = None

    async def run_maintenance(self, dry_run: bool = False) -> MaintenanceResult:
        """
        Run complete maintenance cycle.

        Args:
            dry_run: If True, calculate but don't apply changes

        Returns:
            MaintenanceResult with operation counts
        """
        start_time = time.time()
        result = MaintenanceResult()

        try:
            logger.info(f"Starting maintenance (dry_run={dry_run})")

            # Count total memories to process
            result.memories_processed = await self._count_memories()
            logger.info(f"Found {result.memories_processed} memories to process")

            if dry_run:
                # Dry run - just count without modifying
                result.completed_at = datetime.now(timezone.utc).isoformat()
                result.duration_seconds = time.time() - start_time
                logger.info(f"Dry run completed in {result.duration_seconds:.2f}s")
                return result

            # Check timeout
            elapsed = time.time() - start_time
            max_seconds = self.max_duration_minutes * 60

            # Step 0: Classify unclassified nodes (T012/T013)
            # New nodes created by add_memory need importance/stability classification
            if elapsed < max_seconds:
                logger.info("Step 0: Classifying unclassified nodes")
                classification = await classify_unclassified_nodes(
                    driver=self.driver,
                    llm_client=self._llm_client,  # May be None, will use defaults
                    batch_size=self.batch_size,
                    max_nodes=500,  # Limit per maintenance run
                )
                result.nodes_classified = ClassificationResult(
                    found=classification["found"],
                    classified=classification["classified"],
                    failed=classification["failed"],
                    using_llm=classification["using_llm"],
                )
                if classification["classified"] > 0:
                    logger.info(
                        f"Classified {classification['classified']} new nodes "
                        f"(LLM={classification['using_llm']})"
                    )

            # Step 1: Recalculate decay scores
            elapsed = time.time() - start_time
            if elapsed < max_seconds:
                logger.info("Step 1: Recalculating decay scores")
                result.decay_scores_updated = await batch_update_decay_scores(
                    self.driver,
                    self.base_half_life
                )
                logger.info(f"Updated {result.decay_scores_updated} decay scores")

            # Step 2: Transition lifecycle states
            elapsed = time.time() - start_time
            if elapsed < max_seconds:
                logger.info("Step 2: Transitioning lifecycle states")
                result.state_transitions = await batch_transition_states(self.driver)
                logger.info(f"Transitioned {result.state_transitions.total} memories")

            # Step 3: Purge soft-deleted past retention
            elapsed = time.time() - start_time
            if elapsed < max_seconds:
                logger.info("Step 3: Purging expired soft-deleted memories")
                result.soft_deleted_purged = await purge_expired_soft_deletes(self.driver)
                if result.soft_deleted_purged > 0:
                    logger.info(f"Purged {result.soft_deleted_purged} memories")

            result.success = True
            result.completed_at = datetime.now(timezone.utc).isoformat()
            result.duration_seconds = time.time() - start_time

            # Store for health metrics
            self._last_result = result

            # Record metrics
            self._record_metrics(result)

            logger.info(
                f"Maintenance completed in {result.duration_seconds:.2f}s: "
                f"{result.nodes_classified.classified} classified, "
                f"{result.decay_scores_updated} decay updates, "
                f"{result.state_transitions.total} transitions, "
                f"{result.soft_deleted_purged} purged"
            )

            return result

        except Exception as e:
            result.success = False
            result.error = str(e)
            result.completed_at = datetime.now(timezone.utc).isoformat()
            result.duration_seconds = time.time() - start_time

            # Record failure metrics
            decay_metrics = get_decay_metrics_exporter()
            if decay_metrics:
                decay_metrics.record_maintenance_run(
                    status="failure",
                    duration_seconds=result.duration_seconds,
                    scores_updated=0
                )

            logger.error(f"Maintenance failed after {result.duration_seconds:.2f}s: {e}")
            return result

    async def get_health_metrics(self, group_id: Optional[str] = None) -> HealthMetrics:
        """
        Get health metrics for the knowledge graph.

        Args:
            group_id: Optional group ID to filter metrics

        Returns:
            HealthMetrics with state counts, aggregates, and age distribution
        """
        metrics = HealthMetrics()
        metrics.generated_at = datetime.now(timezone.utc).isoformat()

        try:
            async with self.driver.session() as session:
                # Get state counts
                result = await session.run(HEALTH_STATES_QUERY)
                record = await result.single()
                if record:
                    metrics.states = {
                        "active": record["active"],
                        "dormant": record["dormant"],
                        "archived": record["archived"],
                        "expired": record["expired"],
                        "soft_deleted": record["soft_deleted"],
                        "permanent": record["permanent"],
                    }
                    metrics.aggregates["total"] = record["total"]

                # Get aggregates
                result = await session.run(HEALTH_AGGREGATES_QUERY)
                record = await result.single()
                if record:
                    metrics.aggregates["average_decay"] = round(record["avg_decay"] or 0, 3)
                    metrics.aggregates["average_importance"] = round(record["avg_importance"] or 3, 2)
                    metrics.aggregates["average_stability"] = round(record["avg_stability"] or 3, 2)

                # Get orphan entities count
                result = await session.run(ORPHAN_ENTITIES_QUERY)
                record = await result.single()
                if record:
                    metrics.aggregates["orphan_entities"] = record["orphan_count"] or 0

                # Get age distribution
                result = await session.run(HEALTH_AGE_DISTRIBUTION_QUERY)
                record = await result.single()
                if record:
                    metrics.age_distribution = {
                        "under_7_days": record["under_7_days"],
                        "days_7_to_30": record["days_7_to_30"],
                        "days_30_to_90": record["days_30_to_90"],
                        "over_90_days": record["over_90_days"],
                    }

                # Get importance distribution
                result = await session.run(HEALTH_IMPORTANCE_DISTRIBUTION_QUERY)
                record = await result.single()
                if record:
                    metrics.importance_distribution = {
                        "trivial": record["trivial"],
                        "low": record["low"],
                        "moderate": record["moderate"],
                        "high": record["high"],
                        "core": record["core"],
                    }

                # Add last maintenance info
                if self._last_result:
                    metrics.maintenance = {
                        "last_run": self._last_result.completed_at,
                        "duration_seconds": round(self._last_result.duration_seconds, 2),
                        "processed": self._last_result.memories_processed,
                        "transitions": self._last_result.state_transitions.total,
                    }

                # Update Prometheus gauge metrics
                self._update_gauge_metrics(metrics)

        except Exception as e:
            logger.error(f"Error getting health metrics: {e}")

        return metrics

    def _update_gauge_metrics(self, metrics: HealthMetrics) -> None:
        """Update decay metrics gauges from health check results."""
        decay_metrics = get_decay_metrics_exporter()
        if not decay_metrics:
            return

        # Update state counts
        decay_metrics.update_state_counts({
            "ACTIVE": metrics.states.get("active", 0),
            "DORMANT": metrics.states.get("dormant", 0),
            "ARCHIVED": metrics.states.get("archived", 0),
            "EXPIRED": metrics.states.get("expired", 0),
            "SOFT_DELETED": metrics.states.get("soft_deleted", 0),
            "PERMANENT": metrics.states.get("permanent", 0),
        })

        # Update importance distribution
        decay_metrics.update_importance_counts({
            "TRIVIAL": metrics.importance_distribution.get("trivial", 0),
            "LOW": metrics.importance_distribution.get("low", 0),
            "MODERATE": metrics.importance_distribution.get("moderate", 0),
            "HIGH": metrics.importance_distribution.get("high", 0),
            "CORE": metrics.importance_distribution.get("core", 0),
        })

        # Update averages
        decay_metrics.update_averages(
            decay=metrics.aggregates.get("average_decay", 0.0),
            importance=metrics.aggregates.get("average_importance", 3.0),
            stability=metrics.aggregates.get("average_stability", 3.0),
            total=metrics.aggregates.get("total", 0)
        )

        # Update orphan entities gauge
        decay_metrics.update_orphan_count(metrics.aggregates.get("orphan_entities", 0))

    async def _count_memories(self) -> int:
        """Count total memories to process."""
        async with self.driver.session() as session:
            result = await session.run(COUNT_MEMORIES_QUERY)
            record = await result.single()
            return record["count"] if record else 0

    def _record_metrics(self, result: MaintenanceResult) -> None:
        """Record Prometheus metrics for completed maintenance run."""
        decay_metrics = get_decay_metrics_exporter()
        if not decay_metrics:
            return

        # Record maintenance run
        decay_metrics.record_maintenance_run(
            status="success",
            duration_seconds=result.duration_seconds,
            scores_updated=result.decay_scores_updated
        )

        # Record lifecycle transitions
        transitions = result.state_transitions
        if transitions.active_to_dormant > 0:
            decay_metrics.record_lifecycle_transition("ACTIVE", "DORMANT", transitions.active_to_dormant)
        if transitions.dormant_to_archived > 0:
            decay_metrics.record_lifecycle_transition("DORMANT", "ARCHIVED", transitions.dormant_to_archived)
        if transitions.archived_to_expired > 0:
            decay_metrics.record_lifecycle_transition("ARCHIVED", "EXPIRED", transitions.archived_to_expired)
        if transitions.expired_to_soft_deleted > 0:
            decay_metrics.record_lifecycle_transition("EXPIRED", "SOFT_DELETED", transitions.expired_to_soft_deleted)

        # Record purged memories
        if result.soft_deleted_purged > 0:
            decay_metrics.record_memories_purged(result.soft_deleted_purged)

    async def start_scheduled_maintenance(self) -> None:
        """
        Start the automatic maintenance scheduler.

        Runs maintenance every schedule_interval_hours until shutdown.
        Use stop_scheduled_maintenance() or shutdown_event to stop gracefully.
        """
        if self.schedule_interval_hours <= 0:
            logger.info(f"Scheduled maintenance disabled (schedule_interval_hours={self.schedule_interval_hours})")
            return

        if self._scheduled_task is not None:
            logger.warning("Scheduled maintenance already running")
            return

        interval_seconds = self.schedule_interval_hours * 3600
        logger.info(f"Starting scheduled maintenance every {self.schedule_interval_hours} hours")

        async def maintenance_loop():
            """Background task that runs maintenance periodically."""
            try:
                while not self._shutdown_event.is_set():
                    # Run maintenance
                    try:
                        logger.info("Running scheduled maintenance cycle")
                        result = await self.run_maintenance(dry_run=False)
                        if result.success:
                            logger.info(
                                f"Scheduled maintenance completed: "
                                f"{result.memories_processed} processed, "
                                f"{result.decay_scores_updated} scores updated, "
                                f"{result.state_transitions.total} transitions"
                            )
                        else:
                            logger.error(f"Scheduled maintenance failed: {result.error}")
                    except Exception as e:
                        logger.error(f"Error in scheduled maintenance: {e}")

                    # Wait for next interval or shutdown
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(),
                            timeout=interval_seconds
                        )
                        # If we're here, shutdown was signaled
                        break
                    except asyncio.TimeoutError:
                        # Timeout is expected - means interval elapsed, continue loop
                        continue

            except asyncio.CancelledError:
                logger.info("Scheduled maintenance task cancelled")
            except Exception as e:
                logger.error(f"Scheduled maintenance loop error: {e}")
            finally:
                logger.info("Scheduled maintenance stopped")

        self._scheduled_task = asyncio.create_task(maintenance_loop())

    async def stop_scheduled_maintenance(self) -> None:
        """
        Stop the automatic maintenance scheduler gracefully.
        """
        if self._scheduled_task is None:
            return

        logger.info("Stopping scheduled maintenance...")
        self._shutdown_event.set()

        try:
            # Wait for task to finish (with timeout)
            await asyncio.wait_for(self._scheduled_task, timeout=30)
        except asyncio.TimeoutError:
            logger.warning("Scheduled maintenance task did not stop gracefully, cancelling...")
            self._scheduled_task.cancel()
        except asyncio.CancelledError:
            pass  # Task was cancelled
        finally:
            self._scheduled_task = None
            self._shutdown_event.clear()
            logger.info("Scheduled maintenance stopped")

    def is_scheduled(self) -> bool:
        """Check if scheduled maintenance is currently running."""
        return self._scheduled_task is not None and not self._scheduled_task.done()


# Global maintenance service instance (initialized on first use)
_maintenance_service: Optional[MaintenanceService] = None


def get_maintenance_service(driver, llm_client: Any = None) -> MaintenanceService:
    """
    Get or create the maintenance service singleton.

    Args:
        driver: Neo4j driver instance
        llm_client: Optional Graphiti LLM client for classification
    """
    global _maintenance_service
    if _maintenance_service is None:
        logger.info(f"Creating new MaintenanceService singleton with llm_client={llm_client is not None}")
        _maintenance_service = MaintenanceService(driver, llm_client=llm_client)
    else:
        logger.debug(f"Returning existing MaintenanceService singleton (llm_client={_maintenance_service._llm_client is not None})")
    return _maintenance_service
