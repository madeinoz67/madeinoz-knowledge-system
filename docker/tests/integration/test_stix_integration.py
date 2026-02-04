"""
Integration Tests for STIX 2.1 Importer

Feature: 018-osint-ontology
User Story: 3 - Import STIX 2.1 Data
Tests: T050, T051, T052

TDD Approach: Tests written FIRST (RED phase), implementation follows (GREEN phase)

These integration tests verify:
- Batched STIX import with 1000-object batches (T050)
- Partial failure handling with continue-on-error (T051)
- End-to-end MCP tool integration (T052)

Prerequisites:
- Neo4j/FalkorDB database running
- Graphiti MCP server with ontology patches loaded
- pytest-asyncio installed
"""

import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch, Mock
import hashlib

try:
    import pytest
    import pytest_asyncio
except ImportError:
    pytest = None
    pytest_asyncio = None

# Add docker directory to path so 'utils' package can be imported
docker_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(docker_dir))


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_stix_bundle() -> Dict[str, Any]:
    """Sample STIX 2.1 bundle for testing."""
    return {
        "type": "bundle",
        "id": "bundle--test-integration",
        "spec_version": "2.1",
        "objects": [
            # Threat Actor
            {
                "type": "threat-actor",
                "id": "threat-actor--apt29",
                "name": "APT29",
                "description": "Russian threat actor",
                "aliases": ["Cozy Bear", "The Dukes"],
                "sophistication": "advanced",
                "actor_type": ["nation-state"],
                "created": "2024-01-01T00:00:00.000Z",
                "modified": "2024-01-01T00:00:00.000Z",
                "external_references": [
                    {
                        "source_name": "mitre-attack",
                        "external_id": "G0016"
                    }
                ]
            },
            # Malware
            {
                "type": "malware",
                "id": "malware--beacon",
                "name": "Beacon",
                "description": "C2 beacon payload",
                "malware_types": ["remote-access-trojan"],
                "is_family": True,
                "family": "Beacon",
                "created": "2024-01-01T00:00:00.000Z",
                "modified": "2024-01-01T00:00:00.000Z"
            },
            # Relationship
            {
                "type": "relationship",
                "id": "relationship--apt29-uses-beacon",
                "relationship_type": "uses",
                "source_ref": "threat-actor--apt29",
                "target_ref": "malware--beacon",
                "created": "2024-01-01T00:00:00.000Z",
                "modified": "2024-01-01T00:00:00.000Z",
                "confidence": 90
            },
            # Indicator
            {
                "type": "indicator",
                "id": "indicator--c2-domain",
                "name": "C2 Domain",
                "description": "Command and control domain",
                "pattern": "[domain-name:value = 'c2.badactor.com']",
                "pattern_type": "stix",
                "valid_from": "2024-01-01T00:00:00.000Z",
                "created": "2024-01-01T00:00:00.000Z",
                "modified": "2024-01-01T00:00:00.000Z"
            },
            # Vulnerability
            {
                "type": "vulnerability",
                "id": "vulnerability--cve-2024-9999",
                "name": "CVE-2024-9999",
                "description": "Test vulnerability",
                "created": "2024-01-01T00:00:00.000Z",
                "modified": "2024-01-01T00:00:00.000Z",
                "external_references": [
                    {
                        "source_name": "cve",
                        "external_id": "CVE-2024-9999"
                    }
                ]
            }
        ]
    }


@pytest.fixture
def large_stix_bundle() -> Dict[str, Any]:
    """Large STIX bundle with 100+ objects for batch testing."""
    objects = []

    # Add 50 threat actors
    for i in range(50):
        objects.append({
            "type": "threat-actor",
            "id": f"threat-actor--test-{i}",
            "name": f"Test Actor {i}",
            "description": f"Test threat actor {i}",
            "created": "2024-01-01T00:00:00.000Z",
            "modified": "2024-01-01T00:00:00.000Z"
        })

    # Add 50 malware
    for i in range(50):
        objects.append({
            "type": "malware",
            "id": f"malware--test-{i}",
            "name": f"Test Malware {i}",
            "description": f"Test malware {i}",
            "is_family": True,
            "created": "2024-01-01T00:00:00.000Z",
            "modified": "2024-01-01T00:00:00.000Z"
        })

    # Add some relationships
    for i in range(20):
        objects.append({
            "type": "relationship",
            "id": f"relationship--test-{i}",
            "relationship_type": "uses",
            "source_ref": f"threat-actor--test-{i % 50}",
            "target_ref": f"malware--test-{i % 50}",
            "created": "2024-01-01T00:00:00.000Z",
            "modified": "2024-01-01T00:00:00.000Z"
        })

    return {
        "type": "bundle",
        "id": "bundle--large-test",
        "spec_version": "2.1",
        "objects": objects
    }


@pytest.fixture
def invalid_stix_bundle() -> Dict[str, Any]:
    """STIX bundle with some invalid objects for failure handling tests."""
    return {
        "type": "bundle",
        "id": "bundle--invalid-test",
        "spec_version": "2.1",
        "objects": [
            # Valid object
            {
                "type": "threat-actor",
                "id": "threat-actor--valid",
                "name": "Valid Actor",
                "created": "2024-01-01T00:00:00.000Z",
                "modified": "2024-01-01T00:00:00.000Z"
            },
            # Invalid - missing required fields for indicator
            {
                "type": "indicator",
                "id": "indicator--invalid",
                "name": "Invalid Indicator",
                # Missing required 'pattern' field
                "created": "2024-01-01T00:00:00.000Z",
                "modified": "2024-01-01T00:00:00.000Z"
            },
            # Valid object
            {
                "type": "malware",
                "id": "malware--valid",
                "name": "Valid Malware",
                "created": "2024-01-01T00:00:00.000Z",
                "modified": "2024-01-01T00:00:00.000Z"
            },
            # Unknown type (should be skipped with warning)
            {
                "type": "unknown-type",
                "id": "unknown--test",
                "name": "Unknown Type",
                "created": "2024-01-01T00:00:00.000Z",
                "modified": "2024-01-01T00:00:00.000Z"
            }
        ]
    }


@pytest.fixture
def mock_graphiti_client():
    """Mock Graphiti client for testing."""
    client = AsyncMock()

    # Mock add_episode method
    async def mock_add_episode(*args, **kwargs):
        return {"uuid": "test-episode-uuid"}

    client.add_episode = mock_add_episode

    # Mock search_nodes method
    async def mock_search_nodes(*args, **kwargs):
        return []

    client.search_nodes = mock_search_nodes

    return client


@pytest.fixture
def mock_queue_service():
    """Mock queue service for testing."""
    queue = AsyncMock()

    async def mock_extract_entities(content, entity_types):
        return {
            "entities": [],
            "relationships": []
        }

    queue.extract_entities = mock_extract_entities

    return queue


# =============================================================================
# T050: Test Batched STIX Import
# =============================================================================

class TestBatchedSTIXImport:
    """Test suite for batched STIX import (T050)."""

    @pytest.mark.asyncio
    async def test_process_small_bundle_single_batch(self, sample_stix_bundle, mock_graphiti_client):
        """Should process small bundle in single batch."""
        from utils.stix_importer import process_stix_bundle

        result = await process_stix_bundle(
            stix_bundle=sample_stix_bundle,
            graphiti_client=mock_graphiti_client,
            batch_size=1000,
            continue_on_error=True
        )

        assert result["status"] in ["COMPLETED", "IN_PROGRESS"]
        assert result["total_objects"] == 5
        assert result["imported_count"] >= 0
        assert "import_id" in result

    @pytest.mark.asyncio
    async def test_process_large_bundle_multiple_batches(self, large_stix_bundle, mock_graphiti_client):
        """Should process large bundle in multiple batches (default 1000)."""
        from utils.stix_importer import process_stix_bundle

        result = await process_stix_bundle(
            stix_bundle=large_stix_bundle,
            graphiti_client=mock_graphiti_client,
            batch_size=50,  # Small batch size for testing
            continue_on_error=True
        )

        assert result["total_objects"] == 120  # 50 + 50 + 20
        assert result["status"] in ["COMPLETED", "IN_PROGRESS"]
        # Should have processed all objects
        assert result["imported_count"] + result["failed_count"] == result["total_objects"]

    @pytest.mark.asyncio
    async def test_process_stix_bundle_with_custom_batch_size(self, large_stix_bundle, mock_graphiti_client):
        """Should respect custom batch size."""
        from utils.stix_importer import process_stix_bundle

        batch_size = 30
        result = await process_stix_bundle(
            stix_bundle=large_stix_bundle,
            graphiti_client=mock_graphiti_client,
            batch_size=batch_size,
            continue_on_error=True
        )

        # Verify batch size was used
        assert result["total_objects"] == 120
        # With 120 objects and batch size 30, should have 4 batches
        # (but we can't directly verify batch count from result)

    @pytest.mark.asyncio
    async def test_process_bundle_creates_import_session(self, sample_stix_bundle, mock_graphiti_client):
        """Should create ImportSession entity to track progress."""
        from utils.stix_importer import process_stix_bundle

        result = await process_stix_bundle(
            stix_bundle=sample_stix_bundle,
            graphiti_client=mock_graphiti_client,
            batch_size=1000,
            continue_on_error=True
        )

        assert "import_id" in result
        assert result["import_id"].startswith("import_")

    @pytest.mark.asyncio
    async def test_process_bundle_reports_progress(self, large_stix_bundle, mock_graphiti_client):
        """Should report progress during batch processing."""
        from utils.stix_importer import process_stix_bundle

        # Track progress callbacks
        progress_updates = []

        async def progress_callback(update):
            progress_updates.append(update)

        result = await process_stix_bundle(
            stix_bundle=large_stix_bundle,
            graphiti_client=mock_graphiti_client,
            batch_size=50,
            continue_on_error=True,
            progress_callback=progress_callback
        )

        # Should have received progress updates
        assert len(progress_updates) > 0
        # Each update should have batch info
        for update in progress_updates:
            assert "batch_number" in update
            assert "total_imported" in update


# =============================================================================
# T051: Test Partial Failure Handling
# =============================================================================

class TestPartialFailureHandling:
    """Test suite for partial failure handling (T051)."""

    @pytest.mark.asyncio
    async def test_continue_on_error_true(self, invalid_stix_bundle, mock_graphiti_client):
        """Should continue importing on error when continue_on_error=True."""
        from utils.stix_importer import process_stix_bundle

        result = await process_stix_bundle(
            stix_bundle=invalid_stix_bundle,
            graphiti_client=mock_graphiti_client,
            batch_size=1000,
            continue_on_error=True
        )

        # Should import valid objects and track failures
        assert result["total_objects"] == 4
        assert result["imported_count"] >= 2  # At least the 2 valid objects
        assert result["failed_count"] >= 1  # At least one invalid
        assert result["status"] in ["PARTIAL", "COMPLETED"]

    @pytest.mark.asyncio
    async def test_continue_on_error_false(self, invalid_stix_bundle, mock_graphiti_client):
        """Should stop on first error when continue_on_error=False."""
        from utils.stix_importer import process_stix_bundle

        result = await process_stix_bundle(
            stix_bundle=invalid_stix_bundle,
            graphiti_client=mock_graphiti_client,
            batch_size=1000,
            continue_on_error=False
        )

        # Should stop at first error
        assert result["status"] == "FAILED"
        assert result["imported_count"] < result["total_objects"]

    @pytest.mark.asyncio
    async def test_failed_objects_tracked(self, invalid_stix_bundle, mock_graphiti_client):
        """Should track failed object IDs and errors."""
        from utils.stix_importer import process_stix_bundle

        result = await process_stix_bundle(
            stix_bundle=invalid_stix_bundle,
            graphiti_client=mock_graphiti_client,
            batch_size=1000,
            continue_on_error=True
        )

        assert "failed_objects" in result
        # Each failed object should have stix_id, stix_type, and error
        for failed in result["failed_objects"]:
            assert "stix_id" in failed
            assert "stix_type" in failed
            assert "error" in failed

    @pytest.mark.asyncio
    async def test_partial_status_set_when_failures_exist(self, invalid_stix_bundle, mock_graphiti_client):
        """Should set status to PARTIAL when some objects fail."""
        from utils.stix_importer import process_stix_bundle

        result = await process_stix_bundle(
            stix_bundle=invalid_stix_bundle,
            graphiti_client=mock_graphiti_client,
            batch_size=1000,
            continue_on_error=True
        )

        if result["failed_count"] > 0 and result["imported_count"] > 0:
            assert result["status"] == "PARTIAL"

    @pytest.mark.asyncio
    async def test_successful_imports_preserved_on_partial_failure(self, invalid_stix_bundle, mock_graphiti_client):
        """Should keep successfully imported objects when import fails partway."""
        from utils.stix_importer import process_stix_bundle

        result = await process_stix_bundle(
            stix_bundle=invalid_stix_bundle,
            graphiti_client=mock_graphiti_client,
            batch_size=1000,
            continue_on_error=True
        )

        # Successful imports should be counted
        assert result["imported_count"] >= 0
        # Even with failures, we should have imported some valid objects
        if result["status"] in ["PARTIAL", "COMPLETED"]:
            assert result["imported_count"] > 0 or result["failed_count"] == result["total_objects"]

    @pytest.mark.asyncio
    async def test_unknown_type_skipped_with_warning(self, invalid_stix_bundle, mock_graphiti_client):
        """Should skip unmapped STIX types with warning."""
        from utils.stix_importer import process_stix_bundle

        result = await process_stix_bundle(
            stix_bundle=invalid_stix_bundle,
            graphiti_client=mock_graphiti_client,
            batch_size=1000,
            continue_on_error=True
        )

        # Unknown types should be in failed objects or skipped
        # Either way, total should be accounted for
        assert result["imported_count"] + result["failed_count"] <= result["total_objects"]


# =============================================================================
# T052: Test MCP Tool Integration
# =============================================================================

class TestMCPToolIntegration:
    """Test suite for MCP tool integration (T052)."""

    @pytest.mark.asyncio
    async def test_import_stix_bundle_tool_signature(self, sample_stix_bundle):
        """Should have correct MCP tool signature."""
        # The tool should be importable from graphiti_mcp_server
        from patches.graphiti_mcp_server import import_stix_bundle

        # Verify it's an async function
        import inspect
        assert inspect.iscoroutinefunction(import_stix_bundle)

    @pytest.mark.asyncio
    async def test_import_stix_bundle_tool_creates_entities(self, sample_stix_bundle):
        """Should create entities in knowledge graph via MCP tool."""
        from patches.graphiti_mcp_server import import_stix_bundle
        from unittest.mock import AsyncMock, patch

        # Mock the graphiti service
        mock_client = AsyncMock()
        mock_client.add_episode = AsyncMock(return_value={"uuid": "test-episode"})

        with patch('patches.graphiti_mcp_server.get_graphiti_client', return_value=mock_client):
            # Create a temporary STIX file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(sample_stix_bundle, f)
                temp_path = f.name

            try:
                result = await import_stix_bundle(bundle_path=temp_path)

                # Verify result structure
                assert "import_id" in result
                assert "status" in result
                assert "total_objects" in result
            finally:
                os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_get_import_status_tool(self):
        """Should retrieve import session status."""
        from patches.graphiti_mcp_server import get_import_status
        from utils.stix_importer import create_import_session
        from unittest.mock import AsyncMock, patch

        # Create a test import session
        import_id = "import_test_123"
        session = create_import_session(
            import_id=import_id,
            source_file="/test/bundle.json",
            total_objects=10
        )

        # Mock the knowledge graph to return the session
        mock_client = AsyncMock()
        mock_client.search_nodes = AsyncMock(return_value=[
            {"name": import_id, "attributes": session["attributes"]}
        ])

        with patch('patches.graphiti_mcp_server.get_graphiti_client', return_value=mock_client):
            result = await get_import_status(import_id=import_id)

            assert result["import_id"] == import_id
            assert "status" in result

    @pytest.mark.asyncio
    async def test_resume_import_tool(self):
        """Should resume partially failed import."""
        from patches.graphiti_mcp_server import resume_import
        from unittest.mock import AsyncMock, patch

        import_id = "import_test_resume"

        # Mock the knowledge graph
        mock_client = AsyncMock()
        mock_client.search_nodes = AsyncMock(return_value=[
            {
                "name": import_id,
                "attributes": {
                    "status": "PARTIAL",
                    "failed_object_ids": ["indicator--failed1"],
                    "source_file": "/test/bundle.json"
                }
            }
        ])

        with patch('patches.graphiti_mcp_server.get_graphiti_client', return_value=mock_client):
            result = await resume_import(import_id=import_id)

            assert "import_id" in result
            assert "status" in result

    @pytest.mark.asyncio
    async def test_import_tool_returns_import_id(self, sample_stix_bundle):
        """Should return unique import_id for tracking."""
        from patches.graphiti_mcp_server import import_stix_bundle
        from unittest.mock import AsyncMock, patch

        mock_client = AsyncMock()
        mock_client.add_episode = AsyncMock(return_value={"uuid": "test-episode"})

        with patch('patches.graphiti_mcp_server.get_graphiti_client', return_value=mock_client):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(sample_stix_bundle, f)
                temp_path = f.name

            try:
                result = await import_stix_bundle(bundle_path=temp_path)

                # Import ID should be unique and follow pattern
                assert "import_id" in result
                assert result["import_id"].startswith("import_")
                assert len(result["import_id"]) > 10
            finally:
                os.unlink(temp_path)


# =============================================================================
# End-to-End Flow Tests
# =============================================================================

class TestSTIXImportE2E:
    """End-to-end tests for STIX import flow."""

    @pytest.mark.asyncio
    async def test_full_import_flow_entities_and_relationships(self, sample_stix_bundle):
        """Should import both entities and relationships correctly."""
        from utils.stix_importer import process_stix_bundle

        mock_client = AsyncMock()

        # Track created entities and relationships
        created_entities = []
        created_relationships = []

        async def mock_add_episode(name, episode_body, source=None, **kwargs):
            # Parse the episode to extract entities/relationships
            if "ThreatActor" in episode_body:
                created_entities.append({"type": "ThreatActor", "name": "APT29"})
            if "Malware" in episode_body:
                created_entities.append({"type": "Malware", "name": "Beacon"})
            return {"uuid": f"episode-{len(created_entities)}"}

        mock_client.add_episode = mock_add_episode

        result = await process_stix_bundle(
            stix_bundle=sample_stix_bundle,
            graphiti_client=mock_client,
            batch_size=1000,
            continue_on_error=True
        )

        # Should have processed all objects
        assert result["total_objects"] == 5
        assert result["status"] in ["COMPLETED", "IN_PROGRESS", "PARTIAL"]

    @pytest.mark.asyncio
    async def test_import_preserves_stix_metadata(self, sample_stix_bundle):
        """Should preserve STIX metadata in entity attributes."""
        from utils.stix_importer import extract_entity_from_stix

        # Extract a threat actor
        stix_obj = sample_stix_bundle["objects"][0]
        entity = extract_entity_from_stix(stix_obj)

        # Check that metadata is preserved
        assert "stix_id" in entity
        assert entity["stix_id"] == "threat-actor--apt29"
        assert "created_at" in entity["attributes"]

    @pytest.mark.asyncio
    async def test_import_from_file_path(self, sample_stix_bundle):
        """Should import STIX bundle from file path."""
        from utils.stix_importer import load_and_parse_stix_file

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_stix_bundle, f)
            temp_path = f.name

        try:
            result = load_and_parse_stix_file(temp_path)

            assert result is not None
            assert result["bundle_id"] == "bundle--test-integration"
            assert len(result["objects"]) == 5
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_import_from_url(self):
        """Should import STIX bundle from URL."""
        from utils.stix_importer import load_stix_from_url
        from unittest.mock import patch, AsyncMock

        # Mock HTTP request
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={
            "type": "bundle",
            "id": "bundle--url-test",
            "spec_version": "2.1",
            "objects": [
                {
                    "type": "threat-actor",
                    "id": "threat-actor--test",
                    "name": "Test Actor",
                    "created": "2024-01-01T00:00:00.000Z",
                    "modified": "2024-01-01T00:00:00.000Z"
                }
            ]
        })

        with patch('aiohttp.ClientSession.get', return_value=mock_response):
            result = await load_stix_from_url("https://example.com/bundle.json")

            assert result is not None
            assert result["bundle_id"] == "bundle--url-test"


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestSTIXImportEdgeCases:
    """Test edge cases in STIX import."""

    @pytest.mark.asyncio
    async def test_empty_bundle(self):
        """Should handle empty STIX bundle."""
        from utils.stix_importer import process_stix_bundle

        empty_bundle = {
            "type": "bundle",
            "id": "bundle--empty",
            "spec_version": "2.1",
            "objects": []
        }

        mock_client = AsyncMock()
        mock_client.add_episode = AsyncMock(return_value={"uuid": "test"})

        result = await process_stix_bundle(
            stix_bundle=empty_bundle,
            graphiti_client=mock_client,
            batch_size=1000,
            continue_on_error=True
        )

        assert result["total_objects"] == 0
        assert result["imported_count"] == 0
        assert result["status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_bundle_with_only_relationships(self):
        """Should handle bundle with only relationship objects (no entities)."""
        from utils.stix_importer import process_stix_bundle

        relationships_only = {
            "type": "bundle",
            "id": "bundle--relationships-only",
            "spec_version": "2.1",
            "objects": [
                {
                    "type": "relationship",
                    "id": "relationship--test",
                    "relationship_type": "uses",
                    "source_ref": "threat-actor--missing",
                    "target_ref": "malware--missing",
                    "created": "2024-01-01T00:00:00.000Z",
                    "modified": "2024-01-01T00:00:00.000Z"
                }
            ]
        }

        mock_client = AsyncMock()
        mock_client.add_episode = AsyncMock(return_value={"uuid": "test"})

        result = await process_stix_bundle(
            stix_bundle=relationships_only,
            graphiti_client=mock_client,
            batch_size=1000,
            continue_on_error=True
        )

        # Relationships should still be processed even if entities don't exist yet
        assert result["total_objects"] == 1

    @pytest.mark.asyncio
    async def test_very_long_bundle_name(self):
        """Should handle bundles with very long object names."""
        from utils.stix_importer import extract_entity_from_stix

        long_name = "A" * 500
        stix_obj = {
            "type": "threat-actor",
            "id": "threat-actor--long-name",
            "name": long_name,
            "created": "2024-01-01T00:00:00.000Z",
            "modified": "2024-01-01T00:00:00.000Z"
        }

        entity = extract_entity_from_stix(stix_obj)

        # Should truncate or handle long names
        assert entity is not None
        assert len(entity["name"]) <= 1000 or entity["name"] == long_name
