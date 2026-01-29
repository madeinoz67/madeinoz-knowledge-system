"""
Decay Migration Utilities

Feature: 009-memory-decay-scoring
See: specs/009-memory-decay-scoring/data-model.md

This module provides migration utilities for:
1. Creating Neo4j indexes for lifecycle_state
2. Backfilling existing nodes with default decay attributes
"""

import logging
from datetime import datetime, timezone
from typing import Any

from utils.decay_types import LifecycleState

logger = logging.getLogger(__name__)


# ==============================================================================
# Index Creation
# ==============================================================================

CREATE_LIFECYCLE_STATE_INDEX = """
CREATE INDEX memory_lifecycle_state IF NOT EXISTS
FOR (n:Entity)
ON (n.`attributes.lifecycle_state`)
"""

CREATE_DECAY_COMPOSITE_INDEX = """
CREATE INDEX memory_decay_composite IF NOT EXISTS
FOR (n:Entity)
ON (n.`attributes.lifecycle_state`, n.`attributes.importance`)
"""


async def create_decay_indexes(driver) -> dict[str, bool]:
    """
    Create Neo4j indexes for decay-related queries.

    Args:
        driver: Neo4j driver instance

    Returns:
        Dictionary of index name -> created status
    """
    results = {}

    async with driver.session() as session:
        # Create lifecycle state index
        try:
            await session.run(CREATE_LIFECYCLE_STATE_INDEX)
            results["memory_lifecycle_state"] = True
            logger.info("Created index: memory_lifecycle_state")
        except Exception as e:
            # Index might already exist
            if "already exists" in str(e).lower():
                results["memory_lifecycle_state"] = True
                logger.debug("Index already exists: memory_lifecycle_state")
            else:
                results["memory_lifecycle_state"] = False
                logger.warning(f"Failed to create index memory_lifecycle_state: {e}")

        # Create composite index
        try:
            await session.run(CREATE_DECAY_COMPOSITE_INDEX)
            results["memory_decay_composite"] = True
            logger.info("Created index: memory_decay_composite")
        except Exception as e:
            if "already exists" in str(e).lower():
                results["memory_decay_composite"] = True
                logger.debug("Index already exists: memory_decay_composite")
            else:
                results["memory_decay_composite"] = False
                logger.warning(f"Failed to create index memory_decay_composite: {e}")

    return results


# ==============================================================================
# Backfill Migration
# ==============================================================================

BACKFILL_QUERY = """
MATCH (n:Entity)
WHERE n.`attributes.importance` IS NULL

WITH n, datetime() AS now
SET n.`attributes.importance` = 3,
    n.`attributes.stability` = 3,
    n.`attributes.decay_score` = 0.0,
    n.`attributes.lifecycle_state` = 'ACTIVE',
    n.`attributes.last_accessed_at` = toString(coalesce(n.created_at, now)),
    n.`attributes.access_count` = 0,
    n.`attributes.soft_deleted_at` = null

RETURN count(n) AS backfilled
"""

COUNT_UNINITIALIZED_QUERY = """
MATCH (n:Entity)
WHERE n.`attributes.importance` IS NULL
RETURN count(n) AS count
"""


async def count_uninitialized_nodes(driver) -> int:
    """
    Count nodes without decay attributes.

    Args:
        driver: Neo4j driver instance

    Returns:
        Number of nodes needing backfill
    """
    async with driver.session() as session:
        result = await session.run(COUNT_UNINITIALIZED_QUERY)
        record = await result.single()
        return record["count"] if record else 0


async def backfill_decay_attributes(driver, dry_run: bool = False) -> dict[str, Any]:
    """
    Backfill existing nodes with default decay attributes.

    This migration:
    1. Finds all Entity nodes without importance attribute
    2. Sets default decay attributes (importance=3, stability=3, etc.)
    3. Sets lifecycle_state to ACTIVE
    4. Initializes last_accessed_at to node's created_at

    Args:
        driver: Neo4j driver instance
        dry_run: If True, only count nodes without modifying

    Returns:
        Dictionary with migration results:
        - nodes_found: Number of nodes needing backfill
        - nodes_updated: Number of nodes updated (0 if dry_run)
        - dry_run: Whether this was a dry run
    """
    # First count how many nodes need backfill
    nodes_found = await count_uninitialized_nodes(driver)

    if nodes_found == 0:
        logger.info("No nodes need decay attribute backfill")
        return {
            "nodes_found": 0,
            "nodes_updated": 0,
            "dry_run": dry_run,
        }

    logger.info(f"Found {nodes_found} nodes needing decay attribute backfill")

    if dry_run:
        logger.info("Dry run - no changes made")
        return {
            "nodes_found": nodes_found,
            "nodes_updated": 0,
            "dry_run": True,
        }

    # Run the backfill
    async with driver.session() as session:
        result = await session.run(BACKFILL_QUERY)
        record = await result.single()
        nodes_updated = record["backfilled"] if record else 0

    logger.info(f"Backfilled {nodes_updated} nodes with decay attributes")

    return {
        "nodes_found": nodes_found,
        "nodes_updated": nodes_updated,
        "dry_run": False,
    }


async def run_migration(driver, create_indexes: bool = True, backfill: bool = True, dry_run: bool = False) -> dict[str, Any]:
    """
    Run the complete decay migration.

    Args:
        driver: Neo4j driver instance
        create_indexes: Whether to create indexes
        backfill: Whether to backfill existing nodes
        dry_run: If True, only report what would be done

    Returns:
        Dictionary with complete migration results
    """
    results = {
        "indexes": {},
        "backfill": {},
        "dry_run": dry_run,
    }

    if create_indexes:
        # Note: Index creation is not affected by dry_run
        # because indexes don't modify data
        results["indexes"] = await create_decay_indexes(driver)

    if backfill:
        results["backfill"] = await backfill_decay_attributes(driver, dry_run=dry_run)

    return results
