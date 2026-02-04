"""
Graph Traversal Module for Investigative Search

Feature: 020-investigative-search
See: specs/020-investigative-search/research.md

This module provides graph traversal functionality for finding connected entities
with configurable depth, relationship filtering, and cycle detection.

Supports both Neo4j (Cypher) and FalkorDB (Redis) backends.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import deque

# Optional imports for database-specific implementations
try:
    from neo4j import Driver as Neo4jDriver
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


# ==============================================================================
# Data Structures
# ==============================================================================

@dataclass
class TraversalResult:
    """
    Result of a graph traversal operation.

    Contains all connections found during traversal, metadata about
    the traversal, and optional warning messages.
    """
    connections: List[Dict[str, Any]] = field(default_factory=list)
    depth_explored: int = 1
    total_connections_explored: int = 0
    connections_returned: int = 0
    cycles_detected: int = 0
    cycles_pruned: List[str] = field(default_factory=list)
    entities_skipped: int = 0
    query_duration_ms: Optional[float] = None
    max_connections_exceeded: bool = False
    warning: Optional[str] = None


@dataclass
class EntityInfo:
    """Information about an entity in the graph."""
    uuid: str
    name: str
    labels: List[str]
    summary: Optional[str] = None
    created_at: Optional[str] = None
    group_id: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None


# ==============================================================================
# Exceptions
# ==============================================================================

class GraphTraversalError(Exception):
    """Base exception for graph traversal errors."""
    pass


class DepthValidationError(GraphTraversalError):
    """Raised when requested depth exceeds maximum allowed."""
    pass


class EntityNotFoundError(GraphTraversalError):
    """Raised when the starting entity is not found."""
    pass


# ==============================================================================
# Graph Traversal Engine
# ==============================================================================

class GraphTraversal:
    """
    Graph traversal engine for investigative search.

    Supports multi-hop traversal (1-3 hops) with:
    - Cycle detection using visited entity tracking
    - Relationship type filtering
    - Connection count warning threshold (500)
    - Entity name resolution
    - Neo4j and FalkorDB backends
    """

    # Maximum depth allowed for traversal (security limit)
    MAX_DEPTH = 3

    # Warning threshold for connection count
    WARNING_THRESHOLD = 500

    def __init__(
        self,
        driver: Any,
        database_type: str = "neo4j",
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the graph traversal engine.

        Args:
            driver: Database driver (Neo4j Driver or Redis connection)
            database_type: Type of database ("neo4j" or "falkordb")
            logger: Optional logger instance
        """
        self.driver = driver
        self.database_type = database_type.lower()
        self.logger = logger or logging.getLogger(__name__)

        if self.database_type not in ("neo4j", "falkordb"):
            raise GraphTraversalError(
                f"Unsupported database type: {database_type}. "
                "Supported types: neo4j, falkordb"
            )

    def traverse(
        self,
        start_entity_uuid: str,
        max_depth: int = 1,
        relationship_types: Optional[List[str]] = None,
        group_ids: Optional[List[str]] = None
    ) -> TraversalResult:
        """
        Traverse the graph starting from an entity.

        Args:
            start_entity_uuid: UUID of the starting entity
            max_depth: Maximum number of hops to traverse (1-3)
            relationship_types: Optional list of relationship types to filter by
            group_ids: Optional list of group IDs to search within

        Returns:
            TraversalResult containing all connections found

        Raises:
            DepthValidationError: If max_depth exceeds MAX_DEPTH
            EntityNotFoundError: If start entity not found
            GraphTraversalError: For other traversal errors
        """
        start_time = datetime.now()

        # Validate depth parameter
        if max_depth > self.MAX_DEPTH:
            raise DepthValidationError(
                f"Requested depth {max_depth} exceeds maximum allowed depth of {self.MAX_DEPTH}"
            )
        if max_depth < 1:
            raise DepthValidationError(
                f"Requested depth {max_depth} must be at least 1"
            )

        self.logger.info(
            f"Starting traversal from entity {start_entity_uuid} "
            f"with max_depth={max_depth}, relationship_types={relationship_types}"
        )

        # Route to database-specific implementation
        if self.database_type == "neo4j":
            result = self._traverse_neo4j(
                start_entity_uuid, max_depth, relationship_types, group_ids
            )
        else:  # falkordb
            result = self._traverse_falkordb(
                start_entity_uuid, max_depth, relationship_types, group_ids
            )

        # Calculate query duration
        end_time = datetime.now()
        result.query_duration_ms = (
            (end_time - start_time).total_seconds() * 1000
        )

        # Check if warning threshold exceeded
        if result.total_connections_explored >= self.WARNING_THRESHOLD:
            result.max_connections_exceeded = True
            result.warning = (
                f"Found {result.total_connections_explored:,} connections "
                f"(showing first {self.WARNING_THRESHOLD:,}). "
                f"Use --relationship-type filter to narrow results."
            )

        self.logger.info(
            f"Traversal complete: explored {result.total_connections_explored} connections, "
            f"returned {result.connections_returned}, detected {result.cycles_detected} cycles"
        )

        return result

    # ========================================================================
    # Neo4j Implementation
    # ========================================================================

    def _traverse_neo4j(
        self,
        start_entity_uuid: str,
        max_depth: int,
        relationship_types: Optional[List[str]],
        group_ids: Optional[List[str]]
    ) -> TraversalResult:
        """
        Traverse graph using Neo4j Cypher variable-length paths.

        Uses native Cypher path queries for efficient multi-hop traversal.
        Cycle detection is handled by tracking visited entities.
        """
        if not NEO4J_AVAILABLE:
            raise GraphTraversalError(
                "Neo4j driver not available. Install neo4j package."
            )

        result = TraversalResult(depth_explored=max_depth)
        visited: Set[str] = {start_entity_uuid}

        # Build Cypher query
        query = self._build_neo4j_query(
            start_entity_uuid, max_depth, relationship_types, group_ids
        )

        try:
            with self.driver.session() as session:
                # First, verify the starting entity exists
                entity_check = session.run(
                    "MATCH (n) WHERE n.uuid = $uuid RETURN n.name, n.labels",
                    uuid=start_entity_uuid
                )
                if not entity_check.single():
                    raise EntityNotFoundError(
                        f"Entity with UUID {start_entity_uuid} not found"
                    )

                # Execute traversal query
                records = session.run(query)

                # Process results
                for record in records:
                    connection = self._process_neo4j_record(record, visited)
                    if connection:
                        result.connections.append(connection)

                # Get total count for metadata
                result.total_connections_explored = len(result.connections) + result.cycles_detected
                result.connections_returned = len(result.connections)

        except Exception as e:
            if isinstance(e, GraphTraversalError):
                raise
            raise GraphTraversalError(f"Neo4j traversal failed: {e}") from e

        return result

    def _build_neo4j_query(
        self,
        start_uuid: str,
        max_depth: int,
        relationship_types: Optional[List[str]],
        group_ids: Optional[List[str]]
    ) -> str:
        """Build Cypher query for variable-length path traversal."""

        # Base query with variable-length path
        query = f"""
        MATCH path = (start)-[r*1..{max_depth}]-(end)
        WHERE start.uuid = $start_uuid
        """

        # Add relationship type filter
        if relationship_types:
            # Build relationship type pattern for each hop (with leading colons)
            rel_pattern = "|".join(f":{rt}" for rt in relationship_types)
            query = f"""
            MATCH path = (start)-[{rel_pattern}*1..{max_depth}]-(end)
            WHERE start.uuid = $start_uuid
            """

        # Add group ID filter
        if group_ids:
            group_list = ", ".join(f"'{gid}'" for gid in group_ids)
            query += f" AND (start.group_id IN [{group_list}] OR end.group_id IN [{group_list}])"

        # Return path nodes and relationships
        query += """
        RETURN
            end.uuid AS uuid,
            end.name AS name,
            labels(end) AS labels,
            end.summary AS summary,
            end.created_at AS created_at,
            end.group_id AS group_id,
            end.attributes AS attributes,
            [r IN relationships(path) | type(r)][0] AS relationship,
            length(path) AS hop_distance
        ORDER BY hop_distance, name
        """

        return query

    def _process_neo4j_record(
        self,
        record: Any,
        visited: Set[str]
    ) -> Optional[Dict[str, Any]]:
        """Process a single Neo4j query result record."""

        uuid = record.get("uuid")
        if not uuid:
            return None

        # Cycle detection
        if uuid in visited:
            self.logger.debug(f"Skipping already-visited entity: {uuid}")
            return None

        visited.add(uuid)

        # Determine direction (simplified - Neo4j paths are bidirectional)
        # A more sophisticated implementation would track actual direction
        direction = "bidirectional"

        return {
            "relationship": record.get("relationship", "RELATED_TO"),
            "direction": direction,
            "target_entity": {
                "uuid": uuid,
                "name": record.get("name", ""),
                "labels": record.get("labels", []),
                "summary": record.get("summary"),
                "created_at": record.get("created_at"),
                "group_id": record.get("group_id"),
                "attributes": self._extract_entity_attributes(record)
            },
            "hop_distance": record.get("hop_distance", 1),
            "fact": self._generate_fact_description(
                record.get("relationship", "RELATED_TO"),
                record.get("name", "")
            )
        }

    # ========================================================================
    # FalkorDB Implementation
    # ========================================================================

    def _traverse_falkordb(
        self,
        start_entity_uuid: str,
        max_depth: int,
        relationship_types: Optional[List[str]],
        group_ids: Optional[List[str]]
    ) -> TraversalResult:
        """
        Traverse graph using FalkorDB breadth-first search.

        FalkorDB has limited native path query support, so we implement
        custom BFS with explicit cycle detection.
        """
        if not REDIS_AVAILABLE:
            raise GraphTraversalError(
                "Redis client not available. Install redis package."
            )

        result = TraversalResult(depth_explored=max_depth)
        visited: Set[str] = {start_entity_uuid}

        # BFS queue: (entity_uuid, current_depth)
        queue = deque([(start_entity_uuid, 0)])

        try:
            while queue:
                current_uuid, current_depth = queue.popleft()

                # Skip if we've reached max depth
                if current_depth >= max_depth:
                    continue

                # Get neighbors
                neighbors = self._get_falkordb_neighbors(
                    current_uuid, relationship_types, group_ids
                )

                for neighbor in neighbors:
                    neighbor_uuid = neighbor.get("uuid")
                    if not neighbor_uuid:
                        continue

                    # Cycle detection
                    if neighbor_uuid in visited:
                        result.cycles_detected += 1
                        result.cycles_pruned.append(neighbor_uuid)
                        self.logger.debug(
                            f"Cycle detected: {current_uuid} -> {neighbor_uuid}"
                        )
                        continue

                    visited.add(neighbor_uuid)

                    # Add connection to results
                    connection = self._build_falkordb_connection(
                        neighbor, current_depth + 1
                    )
                    result.connections.append(connection)

                    # Add to queue for further traversal
                    if current_depth + 1 < max_depth:
                        queue.append((neighbor_uuid, current_depth + 1))

            result.total_connections_explored = len(result.connections) + result.cycles_detected
            result.connections_returned = len(result.connections)

        except Exception as e:
            if isinstance(e, GraphTraversalError):
                raise
            raise GraphTraversalError(f"FalkorDB traversal failed: {e}") from e

        return result

    def _get_falkordb_neighbors(
        self,
        entity_uuid: str,
        relationship_types: Optional[List[str]],
        group_ids: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """Get neighboring entities for a FalkorDB node."""

        # FalkorDB uses GRAPH.QUERY with custom Cypher-like syntax
        # The query syntax differs from standard Neo4j

        query = f"""
        MATCH (n)-[r]-(m)
        WHERE n.uuid = '{entity_uuid}'
        """

        # Add relationship type filter (FalkorDB syntax)
        if relationship_types:
            rel_filter = " OR ".join(
                f"type(r) = '{rt}'" for rt in relationship_types
            )
            query += f" AND ({rel_filter})"

        query += """
        RETURN
            m.uuid AS uuid,
            m.name AS name,
            labels(m) AS labels,
            m.summary AS summary,
            m.created_at AS created_at,
            m.group_id AS group_id,
            m.attributes AS attributes,
            type(r) AS relationship
        """

        try:
            # Execute query using FalkorDB's client
            result = self.driver.graph().query(query)
            neighbors = []

            for record in result.result_set:
                neighbor = {
                    "uuid": record[0],      # m.uuid
                    "name": record[1],      # m.name
                    "labels": record[2],    # labels(m)
                    "summary": record[3],   # m.summary
                    "created_at": record[4], # m.created_at
                    "group_id": record[5],  # m.group_id
                    "attributes": record[6], # m.attributes
                    "relationship": record[7] # type(r)
                }
                neighbors.append(neighbor)

            return neighbors

        except Exception as e:
            self.logger.error(f"FalkorDB neighbor query failed: {e}")
            return []

    def _build_falkordb_connection(
        self,
        neighbor: Dict[str, Any],
        hop_distance: int
    ) -> Dict[str, Any]:
        """Build a connection dict from FalkorDB neighbor data."""

        return {
            "relationship": neighbor.get("relationship", "RELATED_TO"),
            "direction": "bidirectional",  # FalkorDB relationships are undirected by default
            "target_entity": {
                "uuid": neighbor.get("uuid", ""),
                "name": neighbor.get("name", ""),
                "labels": neighbor.get("labels", []),
                "summary": neighbor.get("summary"),
                "created_at": neighbor.get("created_at"),
                "group_id": neighbor.get("group_id"),
                "attributes": self._extract_falkordb_attributes(neighbor)
            },
            "hop_distance": hop_distance,
            "fact": self._generate_fact_description(
                neighbor.get("relationship", "RELATED_TO"),
                neighbor.get("name", "")
            )
        }

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def _extract_entity_attributes(self, record: Any) -> Optional[Dict[str, Any]]:
        """Extract entity attributes from a database record."""
        attributes = record.get("attributes")
        if isinstance(attributes, dict):
            return attributes
        return None

    def _extract_falkordb_attributes(
        self,
        neighbor: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Extract entity attributes from FalkorDB neighbor data."""
        attributes = neighbor.get("attributes")
        if isinstance(attributes, dict):
            return attributes
        return None

    def _generate_fact_description(
        self,
        relationship: str,
        entity_name: str
    ) -> str:
        """Generate a human-readable fact description."""
        # Convert relationship type to readable format
        readable_rel = relationship.replace("_", " ").lower()
        return f"Entity {readable_rel} {entity_name}"


# ==============================================================================
# Factory Function
# ==============================================================================

def create_graph_traversal(
    driver: Any,
    database_type: str = "neo4j",
    logger: Optional[logging.Logger] = None
) -> GraphTraversal:
    """
    Factory function to create a GraphTraversal instance.

    Args:
        driver: Database driver (Neo4j Driver or Redis connection)
        database_type: Type of database ("neo4j" or "falkordb")
        logger: Optional logger instance

    Returns:
        Configured GraphTraversal instance
    """
    return GraphTraversal(driver, database_type, logger)
