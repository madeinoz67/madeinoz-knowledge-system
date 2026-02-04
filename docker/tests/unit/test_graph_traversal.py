"""
Unit Tests for Graph Traversal Module

Feature: 020-investigative-search
Tests: T016 - cycle detection, T017 - connection count warning threshold

Tests verify that:
1. Cycle detection prevents infinite loops (A → B → C → A)
2. Self-referential relationships are handled correctly
3. Connection count warning threshold triggers at 500 connections
4. Depth validation rejects depths > 3
5. Relationship type filtering works correctly
"""

import pytest
from unittest.mock import MagicMock, Mock, patch
from datetime import datetime, timezone, timedelta
import sys
import os

# Add patches directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'patches'))

from utils.graph_traversal import (
    GraphTraversal,
    TraversalResult,
    EntityInfo,
    DepthValidationError,
    EntityNotFoundError,
    GraphTraversalError,
)


class TestGraphTraversalInit:
    """Test GraphTraversal initialization."""

    def test_init_with_neo4j_driver(self):
        """Should initialize with Neo4j driver."""
        mock_driver = MagicMock()
        traversal = GraphTraversal(mock_driver, database_type="neo4j")

        assert traversal.driver == mock_driver
        assert traversal.database_type == "neo4j"
        assert traversal.MAX_DEPTH == 3
        assert traversal.WARNING_THRESHOLD == 500

    def test_init_with_falkordb_driver(self):
        """Should initialize with FalkorDB driver."""
        mock_driver = MagicMock()
        traversal = GraphTraversal(mock_driver, database_type="falkordb")

        assert traversal.driver == mock_driver
        assert traversal.database_type == "falkordb"

    def test_init_with_invalid_database_type(self):
        """Should raise error for unsupported database type."""
        mock_driver = MagicMock()

        with pytest.raises(GraphTraversalError, match="Unsupported database type"):
            GraphTraversal(mock_driver, database_type="invalid")


class TestDepthValidation:
    """Test depth validation (T009)."""

    def test_max_depth_constant(self):
        """MAX_DEPTH should be 3."""
        assert GraphTraversal.MAX_DEPTH == 3

    def test_depth_validation_accepts_valid_depths(self):
        """Should accept depths 1, 2, and 3."""
        mock_driver = MagicMock()
        traversal = GraphTraversal(mock_driver, database_type="neo4j")

        for depth in [1, 2, 3]:
            # Mock the traverse method to avoid actual DB calls
            with patch.object(traversal, '_traverse_neo4j') as mock_traverse:
                mock_traverse.return_value = TraversalResult()
                # Should not raise
                traversal.traverse("entity-uuid", max_depth=depth)

    def test_depth_validation_rejects_depth_4(self):
        """Should reject depth > 3."""
        mock_driver = MagicMock()
        traversal = GraphTraversal(mock_driver, database_type="neo4j")

        with pytest.raises(DepthValidationError, match="exceeds maximum allowed depth of 3"):
            traversal.traverse("entity-uuid", max_depth=4)

    def test_depth_validation_rejects_depth_0(self):
        """Should reject depth < 1."""
        mock_driver = MagicMock()
        traversal = GraphTraversal(mock_driver, database_type="neo4j")

        with pytest.raises(DepthValidationError, match="must be at least 1"):
            traversal.traverse("entity-uuid", max_depth=0)

    def test_depth_validation_rejects_negative_depth(self):
        """Should reject negative depth."""
        mock_driver = MagicMock()
        traversal = GraphTraversal(mock_driver, database_type="neo4j")

        with pytest.raises(DepthValidationError, match="must be at least 1"):
            traversal.traverse("entity-uuid", max_depth=-1)


class TestCycleDetection:
    """Test cycle detection in graph traversal (T006, T016)."""

    @patch('utils.graph_traversal.NEO4J_AVAILABLE', True)
    def test_cycle_detection_in_neo4j_traversal(self):
        """Should detect and skip already-visited entities in Neo4j."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        # Mock entity check - entity exists
        mock_session.run.return_value.single.return_value = {"name": "Test Entity"}

        # Mock traversal results with duplicate UUIDs (cycles)
        def mock_run_side_effect(query, **params):
            """Mock query execution that returns some duplicate entities."""
            result_mock = MagicMock()

            # First call: entity existence check
            if "MATCH (n) WHERE n.uuid" in query:
                result_mock.single.return_value = {"name": "Test"}
            # Second call: traversal query
            else:
                # Simulate records, some with duplicate UUIDs (cycles)
                records = [
                    {
                        "uuid": "entity-1",
                        "name": "Entity One",
                        "labels": ["Person"],
                        "summary": None,
                        "created_at": "2026-02-01T00:00:00Z",
                        "group_id": "main",
                        "attributes": None,
                        "relationship": "KNOWS",
                        "hop_distance": 1
                    },
                    {
                        "uuid": "entity-2",  # Will appear again (cycle)
                        "name": "Entity Two",
                        "labels": ["Organization"],
                        "summary": None,
                        "created_at": "2026-02-01T00:00:00Z",
                        "group_id": "main",
                        "attributes": None,
                        "relationship": "WORKS_FOR",
                        "hop_distance": 1
                    },
                    {
                        "uuid": "entity-2",  # Duplicate - cycle!
                        "name": "Entity Two",
                        "labels": ["Organization"],
                        "summary": None,
                        "created_at": "2026-02-01T00:00:00Z",
                        "group_id": "main",
                        "attributes": None,
                        "relationship": "PARTNER_OF",
                        "hop_distance": 1
                    },
                ]
                result_mock.__iter__ = lambda self: iter(records)

            return result_mock

        mock_session.run.side_effect = mock_run_side_effect

        traversal = GraphTraversal(mock_driver, database_type="neo4j")
        result = traversal.traverse("start-uuid", max_depth=1)

        # Should have 2 unique connections (entity-2 cycle skipped)
        assert len(result.connections) == 2
        # First entity
        assert result.connections[0]["target_entity"]["uuid"] == "entity-1"
        assert result.connections[0]["target_entity"]["name"] == "Entity One"
        # Second entity (only once)
        assert result.connections[1]["target_entity"]["uuid"] == "entity-2"
        assert result.connections[1]["target_entity"]["name"] == "Entity Two"

    @patch('utils.graph_traversal.REDIS_AVAILABLE', True)
    def test_cycle_detection_in_falkordb_traversal(self):
        """Should detect and report cycles in FalkorDB BFS traversal."""
        mock_driver = MagicMock()

        # Mock neighbors that create a cycle
        def mock_get_neighbors(uuid, relationship_types, group_ids):
            """Simulate neighbors including a cycle back to start."""
            if uuid == "start-uuid":
                return [
                    {
                        "uuid": "entity-a",
                        "name": "Entity A",
                        "labels": ["Person"],
                        "summary": None,
                        "created_at": "2026-02-01T00:00:00Z",
                        "group_id": "main",
                        "attributes": None,
                        "relationship": "KNOWS"
                    },
                    {
                        "uuid": "entity-b",
                        "name": "Entity B",
                        "labels": ["Organization"],
                        "summary": None,
                        "created_at": "2026-02-01T00:00:00Z",
                        "group_id": "main",
                        "attributes": None,
                        "relationship": "WORKS_FOR"
                    },
                ]
            elif uuid == "entity-a":
                # entity-a connects back to start (cycle!)
                return [
                    {
                        "uuid": "start-uuid",  # Cycle!
                        "name": "Start Entity",
                        "labels": ["Person"],
                        "summary": None,
                        "created_at": "2026-02-01T00:00:00Z",
                        "group_id": "main",
                        "attributes": None,
                        "relationship": "KNOWS"
                    }
                ]
            return []

        traversal = GraphTraversal(mock_driver, database_type="falkordb")
        traversal._get_falkordb_neighbors = mock_get_neighbors

        result = traversal.traverse("start-uuid", max_depth=2)

        # Should detect 1 cycle
        assert result.cycles_detected == 1
        # The cycle should be pruned
        assert "start-uuid" in result.cycles_pruned
        # Should still have connections from first hop
        assert len(result.connections) == 2

    @patch('utils.graph_traversal.REDIS_AVAILABLE', True)
    def test_self_referential_relationship(self):
        """Should handle self-referential relationships (A → A)."""
        mock_driver = MagicMock()

        def mock_get_neighbors(uuid, relationship_types, group_ids):
            """Simulate entity that references itself."""
            if uuid == "self-referential":
                return [
                    {
                        "uuid": "self-referential",  # Same UUID!
                        "name": "Self Referential",
                        "labels": ["Person"],
                        "summary": None,
                        "created_at": "2026-02-01T00:00:00Z",
                        "group_id": "main",
                        "attributes": None,
                        "relationship": "KNOWS"
                    }
                ]
            return []

        traversal = GraphTraversal(mock_driver, database_type="falkordb")
        traversal._get_falkordb_neighbors = mock_get_neighbors

        result = traversal.traverse("self-referential", max_depth=2)

        # Should detect cycle when trying to traverse self-reference
        assert result.cycles_detected >= 1
        assert "self-referential" in result.cycles_pruned


class TestConnectionWarningThreshold:
    """Test connection count warning threshold (T011, T017)."""

    def test_warning_threshold_constant(self):
        """WARNING_THRESHOLD should be 500."""
        assert GraphTraversal.WARNING_THRESHOLD == 500

    def test_no_warning_below_threshold(self):
        """Should not warn when connections < 500."""
        mock_driver = MagicMock()

        # Mock result with 100 connections
        mock_result = TraversalResult()
        mock_result.total_connections_explored = 100
        mock_result.connections_returned = 100

        with patch.object(GraphTraversal, '_traverse_neo4j', return_value=mock_result):
            traversal = GraphTraversal(mock_driver, database_type="neo4j")
            result = traversal.traverse("entity-uuid", max_depth=1)

        assert result.max_connections_exceeded is False
        assert result.warning is None

    def test_warning_at_threshold(self):
        """Should warn when connections >= 500."""
        mock_driver = MagicMock()

        # Mock result with 600 connections (exceeds threshold)
        mock_result = TraversalResult()
        mock_result.total_connections_explored = 600
        mock_result.connections_returned = 500

        with patch.object(GraphTraversal, '_traverse_neo4j', return_value=mock_result):
            traversal = GraphTraversal(mock_driver, database_type="neo4j")
            result = traversal.traverse("entity-uuid", max_depth=1)

        assert result.max_connections_exceeded is True
        assert result.warning is not None
        assert "600" in result.warning  # Should mention actual count
        assert "500" in result.warning  # Should mention threshold
        assert "--relationship-type" in result.warning  # Should suggest filtering

    def test_warning_exactly_at_threshold(self):
        """Should warn when connections == 500."""
        mock_driver = MagicMock()

        # Mock result with exactly 500 connections
        mock_result = TraversalResult()
        mock_result.total_connections_explored = 500
        mock_result.connections_returned = 500

        with patch.object(GraphTraversal, '_traverse_neo4j', return_value=mock_result):
            traversal = GraphTraversal(mock_driver, database_type="neo4j")
            result = traversal.traverse("entity-uuid", max_depth=1)

        assert result.max_connections_exceeded is True
        assert result.warning is not None


class TestEntityNotFound:
    """Test entity not found handling."""

    @patch('utils.graph_traversal.NEO4J_AVAILABLE', True)
    def test_entity_not_found_in_neo4j(self):
        """Should raise EntityNotFoundError when start entity doesn't exist."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        # Mock entity check - entity not found
        mock_session.run.return_value.single.return_value = None

        traversal = GraphTraversal(mock_driver, database_type="neo4j")

        with pytest.raises(EntityNotFoundError, match="not found"):
            traversal.traverse("nonexistent-uuid", max_depth=1)


class TestRelationshipTypeFiltering:
    """Test relationship type filtering (T010)."""

    def test_neo4j_query_with_relationship_filter(self):
        """Should build query with relationship type filter."""
        mock_driver = MagicMock()

        traversal = GraphTraversal(mock_driver, database_type="neo4j")

        # Build query with relationship filter
        query = traversal._build_neo4j_query(
            start_uuid="test-uuid",
            max_depth=2,
            relationship_types=["KNOWS", "WORKS_FOR"],
            group_ids=None
        )

        # Should include relationship type pattern
        assert "KNOWS" in query or "WORKS_FOR" in query
        # Should use parameterized query (not literal values for security)
        assert "$start_uuid" in query

    def test_neo4j_query_without_relationship_filter(self):
        """Should build query without relationship type filter."""
        mock_driver = MagicMock()

        traversal = GraphTraversal(mock_driver, database_type="neo4j")

        # Build query without relationship filter
        query = traversal._build_neo4j_query(
            start_uuid="test-uuid",
            max_depth=2,
            relationship_types=None,
            group_ids=None
        )

        # Should not include relationship type pattern
        assert "KNOWS" not in query
        # Should use parameterized query (not literal values for security)
        assert "$start_uuid" in query


class TestTraversalResult:
    """Test TraversalResult dataclass."""

    def test_traversal_result_defaults(self):
        """Should create TraversalResult with default values."""
        result = TraversalResult()

        assert result.connections == []
        assert result.depth_explored == 1
        assert result.total_connections_explored == 0
        assert result.connections_returned == 0
        assert result.cycles_detected == 0
        assert result.cycles_pruned == []
        assert result.max_connections_exceeded is False
        assert result.warning is None

    def test_traversal_result_with_values(self):
        """Should create TraversalResult with provided values."""
        result = TraversalResult(
            connections=[{"relationship": "KNOWS"}],
            depth_explored=2,
            total_connections_explored=100,
            connections_returned=95,
            cycles_detected=5,
            cycles_pruned=["uuid-1", "uuid-2"],
            warning="Test warning"
        )

        assert len(result.connections) == 1
        assert result.depth_explored == 2
        assert result.total_connections_explored == 100
        assert result.connections_returned == 95
        assert result.cycles_detected == 5
        assert len(result.cycles_pruned) == 2
        assert result.warning == "Test warning"


# ==============================================================================
# Test: T029 - Multi-hop Traversal (User Story 2)
# ==============================================================================

class TestMultiHopTraversal:
    """Test multi-hop graph traversal (T029)."""

    def test_neo4j_variable_length_path_query(self):
        """Should build correct Cypher query for variable-length paths."""
        mock_driver = MagicMock()
        traversal = GraphTraversal(mock_driver, database_type="neo4j")

        # Test depth 1
        query_1 = traversal._build_neo4j_query(
            start_uuid="test-uuid",
            max_depth=1,
            relationship_types=None,
            group_ids=None
        )
        assert "[r*1..1]" in query_1

        # Test depth 2
        query_2 = traversal._build_neo4j_query(
            start_uuid="test-uuid",
            max_depth=2,
            relationship_types=None,
            group_ids=None
        )
        assert "[r*1..2]" in query_2

        # Test depth 3
        query_3 = traversal._build_neo4j_query(
            start_uuid="test-uuid",
            max_depth=3,
            relationship_types=None,
            group_ids=None
        )
        assert "[r*1..3]" in query_3

    @patch('utils.graph_traversal.REDIS_AVAILABLE', True)
    def test_falkorb_bfs_explores_by_depth(self):
        """FalkorDB BFS should respect max depth during traversal."""
        mock_driver = MagicMock()

        visited_entities = []

        def mock_get_neighbors(uuid, relationship_types, group_ids):
            """Simulate a chain: A -> B -> C -> D -> E"""
            visited_entities.append(uuid)
            chain = {
                "start-uuid": [
                    {"uuid": "entity-b", "name": "B", "labels": ["E"], "summary": None,
                     "created_at": None, "group_id": None, "attributes": None, "relationship": "A_TO"}
                ],
                "entity-b": [
                    {"uuid": "entity-c", "name": "C", "labels": ["E"], "summary": None,
                     "created_at": None, "group_id": None, "attributes": None, "relationship": "B_TO"}
                ],
                "entity-c": [
                    {"uuid": "entity-d", "name": "D", "labels": ["E"], "summary": None,
                     "created_at": None, "group_id": None, "attributes": None, "relationship": "C_TO"}
                ],
                "entity-d": []  # End of chain
            }
            return chain.get(uuid, [])

        traversal = GraphTraversal(mock_driver, database_type="falkordb")
        traversal._get_falkordb_neighbors = mock_get_neighbors

        # Test depth 1
        visited_entities.clear()
        result_1 = traversal.traverse("start-uuid", max_depth=1)
        assert result_1.depth_explored == 1
        assert "entity-b" in visited_entities
        assert "entity-c" not in visited_entities  # Should not reach depth 2

        # Test depth 2
        visited_entities.clear()
        result_2 = traversal.traverse("start-uuid", max_depth=2)
        assert result_2.depth_explored == 2
        assert "entity-b" in visited_entities
        assert "entity-c" in visited_entities
        assert "entity-d" not in visited_entities  # Should not reach depth 3

    @patch('utils.graph_traversal.NEO4J_AVAILABLE', True)
    def test_hop_distance_included_in_connections(self):
        """Should include hop_distance in all connection records."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        # Mock entity exists with multi-hop connections
        def mock_run_side_effect(query, **params):
            result_mock = MagicMock()

            if "MATCH (n) WHERE n.uuid" in query:
                result_mock.single.return_value = {"name": "Test"}
            else:
                result_mock.__iter__ = lambda self: iter([
                    {
                        "uuid": f"entity-{i}",
                        "name": f"Entity {i}",
                        "labels": ["Test"],
                        "summary": None,
                        "created_at": None,
                        "group_id": "main",
                        "attributes": None,
                        "relationship": "CONNECTS",
                        "hop_distance": i
                    }
                    for i in range(1, 4)  # hop_distance 1, 2, 3
                ])

            return result_mock

        mock_session.run.side_effect = mock_run_side_effect

        traversal = GraphTraversal(mock_driver, database_type="neo4j")
        result = traversal.traverse("test-uuid", max_depth=3)

        # All connections should have hop_distance
        for conn in result.connections:
            assert "hop_distance" in conn
            assert 1 <= conn["hop_distance"] <= 3
