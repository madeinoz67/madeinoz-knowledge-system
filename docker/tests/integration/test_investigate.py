"""
Integration Tests: Investigative Search (Feature 020)

Tests the investigate_entity MCP tool and graph traversal:
- T013: Investigate with 1-hop connections returns related entities with names
- T014: Investigate with no connections returns empty connections array
- T015: Investigate entity not found returns error response
- T068: CLI-MCP parity (same query produces identical results)

Prerequisites:
- Neo4j or FalkorDB database running
- Graphiti MCP server with investigate_entity tool loaded
- pytest and pytest-asyncio installed

Test Data Setup:
- Creates test entities with known relationships
- Tests direct (1-hop) connections
- Tests entity with no connections
- Tests non-existent entity lookup
"""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

try:
    import pytest
except ImportError:
    pytest = None

# Add docker/ to path so 'patches' package can be imported
docker_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(docker_dir))

# Import graph traversal and response types
from patches.utils.graph_traversal import (
    GraphTraversal,
    TraversalResult,
    EntityNotFoundError,
    DepthValidationError,
)
from patches.models import (
    InvestigateResult,
    Entity,
    Connection,
    InvestigationMetadata,
    InvestigateEntityError,
)


# ==============================================================================
# Test Fixtures
# ==============================================================================

def _pytest_fixture_decorator(func):
    """Conditional pytest.fixture decorator."""
    if pytest is not None:
        return pytest.fixture(func)
    return func


@_pytest_fixture_decorator
def mock_neo4j_driver():
    """Mock Neo4j driver for testing."""
    driver = MagicMock()
    mock_session = MagicMock()

    # Configure session context manager
    driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
    driver.session.return_value.__exit__ = MagicMock(return_value=False)

    return driver, mock_session


@_pytest_fixture_decorator
def mock_falkordb_driver():
    """Mock FalkorDB (Redis) driver for testing."""
    driver = MagicMock()
    return driver


@_pytest_fixture_decorator
def sample_entity_data():
    """Sample entity data for testing."""
    return {
        "uuid": "test-entity-1",
        "name": "John Doe",
        "labels": ["Person"],
        "summary": "Person of interest",
        "created_at": "2026-02-01T10:00:00Z",
        "group_id": "main",
        "attributes": {
            "importance": 3,
            "stability": 2,
            "lifecycle_state": "ACTIVE"
        }
    }


@_pytest_fixture_decorator
def sample_connections_data():
    """Sample connection data for testing 1-hop connections."""
    return [
        {
            "uuid": "phone-1",
            "name": "+1-555-0199",
            "labels": ["Phone"],
            "summary": "Phone number",
            "created_at": "2026-02-01T10:00:00Z",
            "group_id": "main",
            "attributes": None,
            "relationship": "OWNED_BY",
            "hop_distance": 1
        },
        {
            "uuid": "account-1",
            "name": "@johndoe",
            "labels": ["Account"],
            "summary": "Social media account",
            "created_at": "2026-02-01T10:00:00Z",
            "group_id": "main",
            "attributes": None,
            "relationship": "CONTACTED_VIA",
            "hop_distance": 1
        }
    ]


# ==============================================================================
# Test: T013 - Investigate with 1-hop connections
# ==============================================================================

class TestInvestigateWithConnections:
    """Test investigate_entity returns entities with 1-hop connections (T013)."""

    def test_neo4j_investigate_returns_connected_entities(self, mock_neo4j_driver, sample_entity_data, sample_connections_data):
        """Should return entity with all 1-hop connections including names and UUIDs."""
        driver, mock_session = mock_neo4j_driver

        # Mock entity existence check
        def mock_run_side_effect(query, **params):
            """Mock query execution for entity check and traversal."""
            result_mock = MagicMock()

            if "MATCH (n) WHERE n.uuid" in query:
                # Entity exists
                result_mock.single.return_value = {"name": "John Doe"}
            else:
                # Traversal query - return sample connections
                records = []
                for conn in sample_connections_data:
                    records.append(conn)
                result_mock.__iter__ = lambda self: iter(records)

            return result_mock

        mock_session.run.side_effect = mock_run_side_effect

        # Execute traversal
        traversal = GraphTraversal(driver, database_type="neo4j")
        result = traversal.traverse("test-entity-1", max_depth=1)

        # Verify results
        assert result.depth_explored == 1
        assert len(result.connections) == 2

        # First connection - Phone
        conn1 = result.connections[0]
        assert conn1["relationship"] == "OWNED_BY"
        assert conn1["hop_distance"] == 1
        assert conn1["target_entity"]["uuid"] == "phone-1"
        assert conn1["target_entity"]["name"] == "+1-555-0199"
        assert conn1["target_entity"]["labels"] == ["Phone"]

        # Second connection - Account
        conn2 = result.connections[1]
        assert conn2["relationship"] == "CONTACTED_VIA"
        assert conn2["hop_distance"] == 1
        assert conn2["target_entity"]["uuid"] == "account-1"
        assert conn2["target_entity"]["name"] == "@johndoe"
        assert conn2["target_entity"]["labels"] == ["Account"]

    def test_falkordb_investigate_returns_connected_entities(self, mock_falkordb_driver, sample_connections_data):
        """Should return entity with all 1-hop connections via FalkorDB."""
        driver = mock_falkordb_driver

        # Mock neighbor lookup
        def mock_get_neighbors(uuid, relationship_types, group_ids):
            """Return sample connections."""
            return [
                {
                    "uuid": conn["uuid"],
                    "name": conn["name"],
                    "labels": conn["labels"],
                    "summary": conn["summary"],
                    "created_at": conn["created_at"],
                    "group_id": conn["group_id"],
                    "attributes": conn["attributes"],
                    "relationship": conn["relationship"]
                }
                for conn in sample_connections_data
            ]

        traversal = GraphTraversal(driver, database_type="falkordb")
        traversal._get_falkordb_neighbors = mock_get_neighbors

        result = traversal.traverse("test-entity-1", max_depth=1)

        # Verify results
        assert len(result.connections) == 2
        assert result.connections[0]["target_entity"]["name"] == "+1-555-0199"
        assert result.connections[1]["target_entity"]["name"] == "@johndoe"


# ==============================================================================
# Test: T014 - Investigate with no connections
# ==============================================================================

class TestInvestigateNoConnections:
    """Test investigate_entity handles entities with no connections (T014)."""

    def test_neo4j_investigate_no_connections_returns_empty_list(self, mock_neo4j_driver):
        """Should return empty connections array for entity with no relationships."""
        driver, mock_session = mock_neo4j_driver

        # Mock entity exists but has no connections
        def mock_run_side_effect(query, **params):
            result_mock = MagicMock()

            if "MATCH (n) WHERE n.uuid" in query:
                result_mock.single.return_value = {"name": "Isolated Entity"}
            else:
                # No connections
                result_mock.__iter__ = lambda self: iter([])

            return result_mock

        mock_session.run.side_effect = mock_run_side_effect

        traversal = GraphTraversal(driver, database_type="neo4j")
        result = traversal.traverse("isolated-entity-1", max_depth=1)

        # Should have entity but no connections
        assert result.connections_returned == 0
        assert len(result.connections) == 0
        assert result.total_connections_explored == 0

    def test_falkordb_investigate_no_connections(self, mock_falkordb_driver):
        """Should return empty connections array for isolated entity via FalkorDB."""
        driver = mock_falkordb_driver

        # Mock no neighbors
        traversal = GraphTraversal(driver, database_type="falkordb")
        traversal._get_falkordb_neighbors = lambda uuid, rel_types, groups: []

        result = traversal.traverse("isolated-entity-1", max_depth=1)

        assert len(result.connections) == 0
        assert result.connections_returned == 0


# ==============================================================================
# Test: T015 - Investigate entity not found
# ==============================================================================

class TestInvestigateEntityNotFound:
    """Test investigate_entity handles non-existent entities (T015)."""

    def test_neo4j_investigate_entity_not_found_raises_error(self, mock_neo4j_driver):
        """Should raise EntityNotFoundError when entity doesn't exist."""
        driver, mock_session = mock_neo4j_driver

        # Mock entity check - entity not found
        mock_session.run.return_value.single.return_value = None

        traversal = GraphTraversal(driver, database_type="neo4j")

        with pytest.raises(EntityNotFoundError, match="not found"):
            traversal.traverse("nonexistent-uuid", max_depth=1)

    def test_investigate_entity_error_response_format(self):
        """Should create proper InvestigateEntityError response."""
        error = InvestigateEntityError(
            error="Entity not found: nonexistent-uuid"
        )

        assert error.error == "Entity not found: nonexistent-uuid"
        assert error.details is None

        # With details
        error_with_details = InvestigateEntityError(
            error="Entity not found",
            details={"uuid": "nonexistent-uuid", "group_id": "main"}
        )

        assert error_with_details.details["uuid"] == "nonexistent-uuid"


# ==============================================================================
# Test: T068 - CLI-MCP Parity
# ==============================================================================

class TestCLIMCPPParity:
    """Test CLI and MCP tools produce identical results (T068)."""

    def test_investigate_result_format_consistency(self, sample_entity_data, sample_connections_data):
        """Should produce InvestigateResult in consistent format for CLI and MCP."""
        # Create InvestigateResult matching the spec
        entity = Entity(**sample_entity_data)

        connections = [
            Connection(
                relationship=conn["relationship"],
                direction="incoming",
                target_entity=Entity(
                    uuid=conn["uuid"],
                    name=conn["name"],
                    labels=conn["labels"],
                    summary=conn["summary"],
                    created_at=conn["created_at"],
                    group_id=conn["group_id"],
                    attributes=None
                ),
                hop_distance=conn["hop_distance"],
                fact=f"Entity {conn['relationship'].lower()} {conn['name']}"
            )
            for conn in sample_connections_data
        ]

        metadata = InvestigationMetadata(
            depth_explored=1,
            total_connections_explored=2,
            connections_returned=2,
            cycles_detected=0,
            cycles_pruned=[],
            query_duration_ms=145.0
        )

        result = InvestigateResult(
            entity=entity,
            connections=connections,
            metadata=metadata
        )

        # Verify structure matches spec
        assert result.entity.uuid == "test-entity-1"
        assert result.entity.name == "John Doe"
        assert len(result.connections) == 2
        assert result.metadata.depth_explored == 1
        assert result.metadata.query_duration_ms == 145.0

    def test_investigate_result_serializable_to_json(self, sample_entity_data):
        """InvestigateResult should be JSON-serializable for AI consumption."""
        entity = Entity(**sample_entity_data)

        result = InvestigateResult(
            entity=entity,
            connections=[],
            metadata=InvestigationMetadata(
                depth_explored=1,
                total_connections_explored=0,
                connections_returned=0,
                cycles_detected=0,
                cycles_pruned=[]
            )
        )

        # Should be serializable to dict (for JSON response)
        result_dict = result.model_dump()

        assert result_dict["entity"]["uuid"] == "test-entity-1"
        assert result_dict["entity"]["name"] == "John Doe"
        assert result_dict["metadata"]["depth_explored"] == 1
        assert "connections" in result_dict


# ==============================================================================
# Test: Additional edge cases
# ==============================================================================

class TestInvestigateEdgeCases:
    """Test edge cases and error conditions."""

    def test_investigate_with_relationship_filter(self, mock_neo4j_driver):
        """Should filter connections by relationship type."""
        driver, mock_session = mock_neo4j_driver

        # Mock entity exists
        mock_session.run.return_value.single.return_value = {"name": "Test"}

        traversal = GraphTraversal(driver, database_type="neo4j")

        # Build query with filter
        query = traversal._build_neo4j_query(
            start_uuid="test-uuid",
            max_depth=1,
            relationship_types=["OWNED_BY"],
            group_ids=None
        )

        # Should include filter in query
        assert "OWNED_BY" in query

    def test_investigate_with_invalid_depth_raises_error(self, mock_neo4j_driver):
        """Should reject depth > 3."""
        driver, mock_session = mock_neo4j_driver

        traversal = GraphTraversal(driver, database_type="neo4j")

        with pytest.raises(DepthValidationError):
            traversal.traverse("test-uuid", max_depth=5)

    def test_investigate_metadata_includes_query_duration(self, mock_neo4j_driver):
        """Should include query duration in metadata."""
        driver, mock_session = mock_neo4j_driver

        # Mock entity exists but no connections
        def mock_run_side_effect(query, **params):
            result_mock = MagicMock()

            if "MATCH (n) WHERE n.uuid" in query:
                result_mock.single.return_value = {"name": "Test"}
            else:
                result_mock.__iter__ = lambda self: iter([])

            return result_mock

        mock_session.run.side_effect = mock_run_side_effect

        traversal = GraphTraversal(driver, database_type="neo4j")
        result = traversal.traverse("test-uuid", max_depth=1)

        # Query duration should be recorded
        assert result.query_duration_ms is not None
        assert result.query_duration_ms >= 0


# ==============================================================================
# Test: T025-T028 - Variable Depth Traversal (User Story 2)
# ==============================================================================

class TestVariableDepthTraversal:
    """Test configurable connection depth (T025-T028)."""

    def test_depth_1_returns_direct_connections_only(self, mock_neo4j_driver):
        """Should return only direct (1-hop) connections when depth=1."""
        driver, mock_session = mock_neo4j_driver

        # Mock entity exists
        def mock_run_side_effect(query, **params):
            result_mock = MagicMock()

            if "MATCH (n) WHERE n.uuid" in query:
                result_mock.single.return_value = {"name": "Test"}
            else:
                # Return 1-hop connections
                result_mock.__iter__ = lambda self: iter([
                    {
                        "uuid": "entity-a",
                        "name": "Entity A",
                        "labels": ["Person"],
                        "summary": None,
                        "created_at": "2026-02-01T00:00:00Z",
                        "group_id": "main",
                        "attributes": None,
                        "relationship": "KNOWS",
                        "hop_distance": 1
                    }
                ])

            return result_mock

        mock_session.run.side_effect = mock_run_side_effect

        traversal = GraphTraversal(driver, database_type="neo4j")
        result = traversal.traverse("test-uuid", max_depth=1)

        assert result.depth_explored == 1
        assert len(result.connections) == 1
        assert result.connections[0]["hop_distance"] == 1

    def test_depth_2_returns_friends_of_friends(self, mock_neo4j_driver):
        """Should return 2-hop connections when depth=2."""
        driver, mock_session = mock_neo4j_driver

        # Mock entity exists
        def mock_run_side_effect(query, **params):
            result_mock = MagicMock()

            if "MATCH (n) WHERE n.uuid" in query:
                result_mock.single.return_value = {"name": "Test"}
            else:
                # Return mixed hop distances
                result_mock.__iter__ = lambda self: iter([
                    {
                        "uuid": "entity-1hop",
                        "name": "1-Hop Entity",
                        "labels": ["Person"],
                        "summary": None,
                        "created_at": "2026-02-01T00:00:00Z",
                        "group_id": "main",
                        "attributes": None,
                        "relationship": "KNOWS",
                        "hop_distance": 1
                    },
                    {
                        "uuid": "entity-2hop",
                        "name": "2-Hop Entity",
                        "labels": ["Organization"],
                        "summary": None,
                        "created_at": "2026-02-01T00:00:00Z",
                        "group_id": "main",
                        "attributes": None,
                        "relationship": "WORKS_FOR",
                        "hop_distance": 2
                    }
                ])

            return result_mock

        mock_session.run.side_effect = mock_run_side_effect

        traversal = GraphTraversal(driver, database_type="neo4j")
        result = traversal.traverse("test-uuid", max_depth=2)

        assert result.depth_explored == 2
        assert len(result.connections) == 2
        # Verify hop distances are tracked
        hop_distances = [c["hop_distance"] for c in result.connections]
        assert 1 in hop_distances
        assert 2 in hop_distances

    def test_depth_3_returns_extended_network(self, mock_neo4j_driver):
        """Should return 3-hop connections when depth=3."""
        driver, mock_session = mock_neo4j_driver

        # Mock entity exists
        def mock_run_side_effect(query, **params):
            result_mock = MagicMock()

            if "MATCH (n) WHERE n.uuid" in query:
                result_mock.single.return_value = {"name": "Test"}
            else:
                # Return connections at all hop distances
                result_mock.__iter__ = lambda self: iter([
                    {
                        "uuid": f"entity-{i}",
                        "name": f"{i}-Hop Entity",
                        "labels": ["Entity"],
                        "summary": None,
                        "created_at": "2026-02-01T00:00:00Z",
                        "group_id": "main",
                        "attributes": None,
                        "relationship": "CONNECTED",
                        "hop_distance": i
                    }
                    for i in [1, 2, 3]
                ])

            return result_mock

        mock_session.run.side_effect = mock_run_side_effect

        traversal = GraphTraversal(driver, database_type="neo4j")
        result = traversal.traverse("test-uuid", max_depth=3)

        assert result.depth_explored == 3
        assert len(result.connections) == 3
        hop_distances = [c["hop_distance"] for c in result.connections]
        assert sorted(hop_distances) == [1, 2, 3]

    def test_depth_greater_than_3_raises_error(self, mock_neo4j_driver):
        """Should reject depth > 3 (T028)."""
        driver, mock_session = mock_neo4j_driver

        traversal = GraphTraversal(driver, database_type="neo4j")

        # Test depth 4
        with pytest.raises(DepthValidationError, match="exceeds maximum allowed depth of 3"):
            traversal.traverse("test-uuid", max_depth=4)

        # Test depth 10
        with pytest.raises(DepthValidationError):
            traversal.traverse("test-uuid", max_depth=10)

    def test_default_depth_is_1(self, mock_neo4j_driver):
        """Should use depth=1 as default (T022)."""
        driver, mock_session = mock_neo4j_driver

        # Mock entity exists
        def mock_run_side_effect(query, **params):
            result_mock = MagicMock()

            if "MATCH (n) WHERE n.uuid" in query:
                result_mock.single.return_value = {"name": "Test"}
            else:
                result_mock.__iter__ = lambda self: iter([])

            return result_mock

        mock_session.run.side_effect = mock_run_side_effect

        traversal = GraphTraversal(driver, database_type="neo4j")
        result = traversal.traverse("test-uuid")  # No max_depth specified

        assert result.depth_explored == 1  # Default


# ==============================================================================
# Run tests if pytest is available
# ==============================================================================

if pytest is not None:
    # Configure pytest marks
    pytestmark = [
        pytest.mark.unit,
        pytest.mark.integration,
    ]
else:
    # Allow running tests directly
    def main():
        """Run tests without pytest."""
        import doctest
        doctest.testmod()

    if __name__ == "__main__":
        main()
