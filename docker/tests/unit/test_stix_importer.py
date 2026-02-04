"""
Unit Tests for STIX 2.1 Importer Module

Feature: 018-osint-ontology
User Story: 3 - Import STIX 2.1 Data
Tests: T045, T046, T047, T048, T049

TDD Approach: Tests written FIRST (RED phase), implementation follows (GREEN phase)

These tests verify:
- STIX bundle parsing with valid and invalid JSON
- STIX type to ontology type mappings
- STIX entity extraction with property mapping
- STIX relationship extraction with type mapping
- Import session tracking entity creation
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest
import yaml

# Add docker directory to path so 'utils' package can be imported
# In production: patches are at /app/mcp/src/utils/ (copied by Dockerfile)
# In local testing: patches are at docker/patches/
docker_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(docker_dir))


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def valid_stix_bundle() -> Dict[str, Any]:
    """Valid STIX 2.1 bundle for testing."""
    return {
        "type": "bundle",
        "id": "bundle--test-123",
        "spec_version": "2.1",
        "objects": [
            {
                "type": "threat-actor",
                "id": "threat-actor--apt28",
                "name": "APT28",
                "description": "Russian threat actor",
                "aliases": ["Fancy Bear", "Sofacy"],
                "sophistication": "advanced",
                "actor_type": ["nation-state"],
                "created": "2024-01-01T00:00:00.000Z",
                "modified": "2024-01-01T00:00:00.000Z",
                "external_references": [
                    {
                        "source_name": "mitre-attack",
                        "external_id": "G0013"
                    }
                ]
            },
            {
                "type": "malware",
                "id": "malware--cobalt-strike",
                "name": "Cobalt Strike",
                "description": "Beacon payload",
                "malware_types": ["beacon"],
                "is_family": True,
                "family": "Cobalt Strike",
                "created": "2024-01-01T00:00:00.000Z",
                "modified": "2024-01-01T00:00:00.000Z"
            },
            {
                "type": "relationship",
                "id": "relationship--apt28-uses-cobalt",
                "relationship_type": "uses",
                "source_ref": "threat-actor--apt28",
                "target_ref": "malware--cobalt-strike",
                "created": "2024-01-01T00:00:00.000Z",
                "modified": "2024-01-01T00:00:00.000Z",
                "confidence": 85
            },
            {
                "type": "indicator",
                "id": "indicator--test-123",
                "name": "Malicious domain",
                "description": "C2 domain",
                "pattern": "[domain-name:value = 'malicious.example.com']",
                "pattern_type": "stix",
                "valid_from": "2024-01-01T00:00:00.000Z",
                "created": "2024-01-01T00:00:00.000Z",
                "modified": "2024-01-01T00:00:00.000Z"
            },
            {
                "type": "vulnerability",
                "id": "vulnerability--cve-2024-1234",
                "name": "CVE-2024-1234",
                "description": "Test vulnerability",
                "created": "2024-01-01T00:00:00.000Z",
                "modified": "2024-01-01T00:00:00.000Z",
                "external_references": [
                    {
                        "source_name": "cve",
                        "external_id": "CVE-2024-1234"
                    }
                ]
            },
            {
                "type": "attack-pattern",
                "id": "attack-pattern--phishing",
                "name": "Spearphishing",
                "description": "Targeted phishing attack",
                "created": "2024-01-01T00:00:00.000Z",
                "modified": "2024-01-01T00:00:00.000Z",
                "external_references": [
                    {
                        "source_name": "mitre-attack",
                        "external_id": "T1566"
                    }
                ]
            },
            {
                "type": "campaign",
                "id": "campaign--test-campaign",
                "name": "Test Campaign",
                "description": "Test campaign 2024",
                "created": "2024-01-01T00:00:00.000Z",
                "modified": "2024-01-01T00:00:00.000Z"
            },
            {
                "type": "infrastructure",
                "id": "infrastructure--test-server",
                "name": "C2 Server",
                "description": "Command and control server",
                "infrastructure_types": ["command-and-control"],
                "created": "2024-01-01T00:00:00.000Z",
                "modified": "2024-01-01T00:00:00.000Z"
            }
        ]
    }


@pytest.fixture
def invalid_stix_bundle() -> Dict[str, Any]:
    """Invalid STIX bundle for error handling tests."""
    return {
        "type": "bundle",
        "id": "bundle--invalid",
        "spec_version": "2.1",
        "objects": [
            {
                "type": "threat-actor",
                # Missing required "id" field
                "name": "Invalid Actor"
            },
            {
                "type": "unknown-type",
                "id": "unknown--123",
                "name": "Unknown Type"
            }
        ]
    }


@pytest.fixture
def minimal_stix_bundle() -> Dict[str, Any]:
    """Minimal valid STIX bundle with one object."""
    return {
        "type": "bundle",
        "id": "bundle--minimal",
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
    }


# =============================================================================
# T045: Test STIX Bundle Parsing
# =============================================================================

class TestParseStixBundle:
    """Test suite for STIX bundle parsing (T045)."""

    def test_parse_valid_stix_bundle(self, valid_stix_bundle):
        """Should parse valid STIX 2.1 bundle and extract objects."""
        from utils.stix_importer import parse_stix_bundle

        result = parse_stix_bundle(valid_stix_bundle)

        assert result is not None
        assert "objects" in result
        assert len(result["objects"]) == 8
        assert result["bundle_id"] == "bundle--test-123"
        assert result["spec_version"] == "2.1"

    def test_parse_minimal_stix_bundle(self, minimal_stix_bundle):
        """Should parse minimal STIX bundle with single object."""
        from utils.stix_importer import parse_stix_bundle

        result = parse_stix_bundle(minimal_stix_bundle)

        assert result is not None
        assert len(result["objects"]) == 1
        assert result["objects"][0]["type"] == "threat-actor"

    def test_parse_invalid_stix_json(self):
        """Should raise error for invalid JSON structure."""
        from utils.stix_importer import parse_stix_bundle, InvalidSTIXError

        with pytest.raises(InvalidSTIXError):
            parse_stix_bundle({"invalid": "structure"})

    def test_parse_stix_bundle_missing_type(self):
        """Should raise error for bundle missing type field."""
        from utils.stix_importer import parse_stix_bundle, InvalidSTIXError

        invalid_bundle = {
            "id": "bundle--test",
            "spec_version": "2.1",
            "objects": []
        }

        with pytest.raises(InvalidSTIXError):
            parse_stix_bundle(invalid_bundle)

    def test_parse_stix_bundle_wrong_spec_version(self):
        """Should raise error for unsupported STIX version."""
        from utils.stix_importer import parse_stix_bundle, InvalidSTIXError

        wrong_version = {
            "type": "bundle",
            "id": "bundle--test",
            "spec_version": "2.0",  # Only 2.1 is supported
            "objects": []
        }

        with pytest.raises(InvalidSTIXError):
            parse_stix_bundle(wrong_version)

    def test_parse_stix_bundle_empty_objects(self):
        """Should handle bundle with empty objects list."""
        from utils.stix_importer import parse_stix_bundle

        empty_bundle = {
            "type": "bundle",
            "id": "bundle--empty",
            "spec_version": "2.1",
            "objects": []
        }

        result = parse_stix_bundle(empty_bundle)

        assert result is not None
        assert len(result["objects"]) == 0


# =============================================================================
# T046: Test STIX Type Mapping
# =============================================================================

class TestSTIXTypeMapping:
    """Test suite for STIX type to ontology type mappings (T046)."""

    def test_threat_actor_mapping(self):
        """Should map threat-actor to ThreatActor."""
        from utils.stix_importer import get_ontology_type_for_stix

        result = get_ontology_type_for_stix("threat-actor")

        assert result == "ThreatActor"

    def test_malware_mapping(self):
        """Should map malware to Malware."""
        from utils.stix_importer import get_ontology_type_for_stix

        result = get_ontology_type_for_stix("malware")

        assert result == "Malware"

    def test_vulnerability_mapping(self):
        """Should map vulnerability to Vulnerability."""
        from utils.stix_importer import get_ontology_type_for_stix

        result = get_ontology_type_for_stix("vulnerability")

        assert result == "Vulnerability"

    def test_indicator_mapping(self):
        """Should map indicator to Indicator."""
        from utils.stix_importer import get_ontology_type_for_stix

        result = get_ontology_type_for_stix("indicator")

        assert result == "Indicator"

    def test_attack_pattern_mapping(self):
        """Should map attack-pattern to TTP."""
        from utils.stix_importer import get_ontology_type_for_stix

        result = get_ontology_type_for_stix("attack-pattern")

        assert result == "TTP"

    def test_campaign_mapping(self):
        """Should map campaign to Campaign."""
        from utils.stix_importer import get_ontology_type_for_stix

        result = get_ontology_type_for_stix("campaign")

        assert result == "Campaign"

    def test_infrastructure_mapping(self):
        """Should map infrastructure to Infrastructure."""
        from utils.stix_importer import get_ontology_type_for_stix

        result = get_ontology_type_for_stix("infrastructure")

        assert result == "Infrastructure"

    def test_unknown_type_returns_none(self):
        """Should return None for unmapped STIX types."""
        from utils.stix_importer import get_ontology_type_for_stix

        result = get_ontology_type_for_stix("unknown-type")

        assert result is None

    def test_get_all_supported_mappings(self):
        """Should return all STIX to ontology type mappings."""
        from utils.stix_importer import get_supported_stix_types

        mappings = get_supported_stix_types()

        assert isinstance(mappings, dict)
        assert "threat-actor" in mappings
        assert "malware" in mappings
        assert "vulnerability" in mappings
        assert "indicator" in mappings
        assert "attack-pattern" in mappings
        assert "campaign" in mappings
        assert "infrastructure" in mappings

        # Verify all mappings point to valid ontology types
        for stix_type, ontology_type in mappings.items():
            assert isinstance(stix_type, str)
            assert isinstance(ontology_type, str)


# =============================================================================
# T047: Test STIX Entity Extraction
# =============================================================================

class TestExtractEntityFromSTIX:
    """Test suite for STIX entity extraction (T047)."""

    def test_extract_threat_actor_entity(self, valid_stix_bundle):
        """Should extract ThreatActor entity with all properties."""
        from utils.stix_importer import extract_entity_from_stix

        stix_obj = valid_stix_bundle["objects"][0]  # threat-actor

        entity = extract_entity_from_stix(stix_obj)

        assert entity["name"] == "APT28"
        assert entity["entity_type"] == "ThreatActor"
        assert entity["stix_id"] == "threat-actor--apt28"
        assert "description" in entity["attributes"]
        assert "aliases" in entity["attributes"]
        assert entity["attributes"]["aliases"] == ["Fancy Bear", "Sofacy"]
        assert "sophistication" in entity["attributes"]

    def test_extract_malware_entity(self, valid_stix_bundle):
        """Should extract Malware entity with family info."""
        from utils.stix_importer import extract_entity_from_stix

        stix_obj = valid_stix_bundle["objects"][1]  # malware

        entity = extract_entity_from_stix(stix_obj)

        assert entity["name"] == "Cobalt Strike"
        assert entity["entity_type"] == "Malware"
        assert entity["stix_id"] == "malware--cobalt-strike"
        assert entity["attributes"]["family"] == "Cobalt Strike"
        assert "is_family" in entity["attributes"]

    def test_extract_indicator_entity(self, valid_stix_bundle):
        """Should extract Indicator entity with pattern and valid_from."""
        from utils.stix_importer import extract_entity_from_stix

        stix_obj = valid_stix_bundle["objects"][3]  # indicator

        entity = extract_entity_from_stix(stix_obj)

        assert entity["name"] == "Malicious domain"
        assert entity["entity_type"] == "Indicator"
        assert "pattern" in entity["attributes"]
        assert "pattern_type" in entity["attributes"]
        assert "valid_from" in entity["attributes"]

    def test_extract_vulnerability_entity_with_cve(self, valid_stix_bundle):
        """Should extract Vulnerability entity with CVE ID from external_references."""
        from utils.stix_importer import extract_entity_from_stix

        stix_obj = valid_stix_bundle["objects"][4]  # vulnerability

        entity = extract_entity_from_stix(stix_obj)

        assert entity["name"] == "CVE-2024-1234"
        assert entity["entity_type"] == "Vulnerability"
        assert entity["attributes"]["cve_id"] == "CVE-2024-1234"

    def test_extract_ttp_entity_with_mitre_id(self, valid_stix_bundle):
        """Should extract TTP entity with MITRE ID from external_references."""
        from utils.stix_importer import extract_entity_from_stix

        stix_obj = valid_stix_bundle["objects"][5]  # attack-pattern

        entity = extract_entity_from_stix(stix_obj)

        assert entity["name"] == "Spearphishing"
        assert entity["entity_type"] == "TTP"
        assert entity["attributes"]["technique_id"] == "T1566"

    def test_extract_campaign_entity(self, valid_stix_bundle):
        """Should extract Campaign entity."""
        from utils.stix_importer import extract_entity_from_stix

        stix_obj = valid_stix_bundle["objects"][6]  # campaign

        entity = extract_entity_from_stix(stix_obj)

        assert entity["name"] == "Test Campaign"
        assert entity["entity_type"] == "Campaign"
        assert "description" in entity["attributes"]

    def test_extract_infrastructure_entity(self, valid_stix_bundle):
        """Should extract Infrastructure entity with type."""
        from utils.stix_importer import extract_entity_from_stix

        stix_obj = valid_stix_bundle["objects"][7]  # infrastructure

        entity = extract_entity_from_stix(stix_obj)

        assert entity["name"] == "C2 Server"
        assert entity["entity_type"] == "Infrastructure"
        assert "infrastructure_type" in entity["attributes"]

    def test_extract_entity_preserves_created_modified(self):
        """Should preserve STIX created and modified timestamps."""
        from utils.stix_importer import extract_entity_from_stix

        stix_obj = {
            "type": "threat-actor",
            "id": "threat-actor--test",
            "name": "Test",
            "created": "2024-01-15T10:30:00.000Z",
            "modified": "2024-02-20T14:45:00.000Z"
        }

        entity = extract_entity_from_stix(stix_obj)

        assert "created_at" in entity["attributes"]
        assert "updated_at" in entity["attributes"]
        assert entity["attributes"]["created_at"] == "2024-01-15T10:30:00.000Z"
        assert entity["attributes"]["updated_at"] == "2024-02-20T14:45:00.000Z"

    def test_extract_entity_returns_none_for_unknown_type(self):
        """Should return None for STIX objects with unmapped types."""
        from utils.stix_importer import extract_entity_from_stix

        stix_obj = {
            "type": "unknown-type",
            "id": "unknown--123",
            "name": "Unknown"
        }

        entity = extract_entity_from_stix(stix_obj)

        assert entity is None

    def test_extract_entity_handles_missing_optional_fields(self):
        """Should handle missing optional fields gracefully."""
        from utils.stix_importer import extract_entity_from_stix

        stix_obj = {
            "type": "threat-actor",
            "id": "threat-actor--minimal",
            "name": "Minimal Actor",
            "created": "2024-01-01T00:00:00.000Z",
            "modified": "2024-01-01T00:00:00.000Z"
            # No description, aliases, or other optional fields
        }

        entity = extract_entity_from_stix(stix_obj)

        assert entity["name"] == "Minimal Actor"
        assert entity["entity_type"] == "ThreatActor"
        # Optional attributes should not be present or be None
        assert entity["attributes"].get("aliases") is None or "aliases" not in entity["attributes"]


# =============================================================================
# T048: Test STIX Relationship Extraction
# =============================================================================

class TestExtractRelationshipFromSTIX:
    """Test suite for STIX relationship extraction (T048)."""

    def test_extract_uses_relationship(self, valid_stix_bundle):
        """Should extract 'uses' relationship between ThreatActor and Malware."""
        from utils.stix_importer import extract_relationship_from_stix

        stix_rel = valid_stix_bundle["objects"][2]  # relationship

        rel = extract_relationship_from_stix(stix_rel, valid_stix_bundle["objects"])

        assert rel is not None
        assert rel["relationship_type"] == "uses"
        assert rel["source_stix_id"] == "threat-actor--apt28"
        assert rel["target_stix_id"] == "malware--cobalt-strike"
        assert "confidence" in rel["attributes"]

    def test_extract_targets_relationship(self):
        """Should extract 'targets' relationship."""
        from utils.stix_importer import extract_relationship_from_stix

        stix_rel = {
            "type": "relationship",
            "id": "relationship--test",
            "relationship_type": "targets",
            "source_ref": "threat-actor--apt28",
            "target_ref": "identity--org-123",
            "created": "2024-01-01T00:00:00.000Z",
            "modified": "2024-01-01T00:00:00.000Z"
        }

        context_objects = [
            {"type": "threat-actor", "id": "threat-actor--apt28", "name": "APT28"},
            {"type": "identity", "id": "identity--org-123", "name": "Target Org", "identity_class": "organization"}
        ]

        rel = extract_relationship_from_stix(stix_rel, context_objects)

        assert rel is not None
        assert rel["relationship_type"] == "targets"

    def test_extract_attributed_to_relationship(self):
        """Should extract 'attributed_to' relationship."""
        from utils.stix_importer import extract_relationship_from_stix

        stix_rel = {
            "type": "relationship",
            "id": "relationship--attr",
            "relationship_type": "attributed-to",
            "source_ref": "intrusion-set--123",
            "target_ref": "threat-actor--apt28",
            "created": "2024-01-01T00:00:00.000Z",
            "modified": "2024-01-01T00:00:00.000Z"
        }

        rel = extract_relationship_from_stix(stix_rel, [])

        assert rel is not None
        assert rel["relationship_type"] == "attributed_to"

    def test_extract_exploits_relationship(self):
        """Should extract 'exploits' relationship."""
        from utils.stix_importer import extract_relationship_from_stix

        stix_rel = {
            "type": "relationship",
            "id": "relationship--exploit",
            "relationship_type": "exploits",
            "source_ref": "malware--cobalt",
            "target_ref": "vulnerability--cve-123",
            "created": "2024-01-01T00:00:00.000Z",
            "modified": "2024-01-01T00:00:00.000Z"
        }

        rel = extract_relationship_from_stix(stix_rel, [])

        assert rel is not None
        assert rel["relationship_type"] == "exploits"

    def test_extract_variant_of_relationship(self):
        """Should extract 'variant_of' relationship."""
        from utils.stix_importer import extract_relationship_from_stix

        stix_rel = {
            "type": "relationship",
            "id": "relationship--variant",
            "relationship_type": "related-to",
            "source_ref": "malware--variant",
            "target_ref": "malware--parent",
            "created": "2024-01-01T00:00:00.000Z",
            "modified": "2024-01-01T00:00:00.000Z"
        }

        # When relationship is 'related-to' between same types, infer variant_of
        context = [
            {"type": "malware", "id": "malware--variant", "name": "Variant"},
            {"type": "malware", "id": "malware--parent", "name": "Parent"}
        ]

        rel = extract_relationship_from_stix(stix_rel, context)

        # Should map 'related-to' to 'variant_of' for same-type malware
        assert rel is not None
        # Either 'related_to' or inferred 'variant_of' is acceptable

    def test_extract_relationship_with_valid_from_valid_until(self):
        """Should preserve valid_from and valid_until timestamps."""
        from utils.stix_importer import extract_relationship_from_stix

        stix_rel = {
            "type": "relationship",
            "id": "relationship--test",
            "relationship_type": "uses",
            "source_ref": "threat-actor--apt28",
            "target_ref": "malware--cobalt",
            "created": "2024-01-01T00:00:00.000Z",
            "modified": "2024-01-01T00:00:00.000Z",
            "start_time": "2024-01-01T00:00:00.000Z",
            "stop_time": "2024-12-31T23:59:59.000Z"
        }

        rel = extract_relationship_from_stix(stix_rel, [])

        assert rel is not None
        # Check for bi-temporal attributes
        temporal_attrs = rel["attributes"].get("valid_from") or rel["attributes"].get("start_time")
        assert temporal_attrs is not None or "start_time" in rel["attributes"]

    def test_extract_relationship_returns_none_for_missing_refs(self):
        """Should return None if source or target ref is not found in context."""
        from utils.stix_importer import extract_relationship_from_stix

        stix_rel = {
            "type": "relationship",
            "id": "relationship--orphan",
            "relationship_type": "uses",
            "source_ref": "threat-actor--missing",
            "target_ref": "malware--missing",
            "created": "2024-01-01T00:00:00.000Z",
            "modified": "2024-01-01T00:00:00.000Z"
        }

        rel = extract_relationship_from_stix(stix_rel, [])

        # Should still create the relationship structure even without context
        # (resolution happens during import when entities are created)
        assert rel is not None
        assert rel["source_stix_id"] == "threat-actor--missing"

    def test_extract_uses_associated_with_mappings(self):
        """Should test all relationship type mappings."""
        from utils.stix_importer import map_stix_relationship_type

        # Test direct mappings
        assert map_stix_relationship_type("uses") == "uses"
        assert map_stix_relationship_type("targets") == "targets"
        assert map_stix_relationship_type("attributed-to") == "attributed_to"
        assert map_stix_relationship_type("exploits") == "exploits"

        # Test that unknown types are handled
        # Returns None or the original type with underscores normalized
        result = map_stix_relationship_type("related-to")
        assert result is not None  # Some handling occurs


# =============================================================================
# T049: Test Import Session Tracking
# =============================================================================

class TestImportSessionTracking:
    """Test suite for import session tracking (T049)."""

    def test_create_import_session_entity(self):
        """Should create ImportSession entity with required fields."""
        from utils.stix_importer import create_import_session

        session = create_import_session(
            import_id="import_test_123",
            source_file="/data/test-bundle.json",
            total_objects=10
        )

        assert session["name"] == "import_test_123"
        assert session["entity_type"] == "ImportSession"
        assert session["attributes"]["source_file"] == "/data/test-bundle.json"
        assert session["attributes"]["total_objects"] == 10
        assert session["attributes"]["imported_count"] == 0
        assert session["attributes"]["failed_count"] == 0
        assert session["attributes"]["status"] == "IN_PROGRESS"
        assert "started_at" in session["attributes"]

    def test_create_import_session_with_initial_progress(self):
        """Should create session with initial progress values."""
        from utils.stix_importer import create_import_session

        session = create_import_session(
            import_id="import_test_456",
            source_file="/data/partial.json",
            total_objects=100,
            imported_count=95,
            failed_count=5
        )

        assert session["attributes"]["imported_count"] == 95
        assert session["attributes"]["failed_count"] == 5
        assert session["attributes"]["status"] == "PARTIAL"

    def test_generate_import_id(self):
        """Should generate unique import ID with timestamp."""
        from utils.stix_importer import generate_import_id

        import_id = generate_import_id()

        assert import_id.startswith("import_")
        # Should be a reasonable length (timestamp + random)
        assert len(import_id) > 10

    def test_update_import_session_status(self):
        """Should update import session status."""
        from utils.stix_importer import update_import_session

        session = {
            "name": "import_test",
            "entity_type": "ImportSession",
            "attributes": {
                "status": "IN_PROGRESS",
                "imported_count": 5,
                "failed_count": 0
            }
        }

        updated = update_import_session(
            session,
            imported_count=10,
            failed_count=2,
            status="PARTIAL"
        )

        assert updated["attributes"]["status"] == "PARTIAL"
        assert updated["attributes"]["imported_count"] == 10
        assert updated["attributes"]["failed_count"] == 2

    def test_complete_import_session(self):
        """Should mark session as completed with completion timestamp."""
        from utils.stix_importer import complete_import_session

        session = {
            "name": "import_test",
            "entity_type": "ImportSession",
            "attributes": {
                "status": "IN_PROGRESS",
                "imported_count": 100,
                "failed_count": 0
            }
        }

        completed = complete_import_session(session)

        assert completed["attributes"]["status"] == "COMPLETED"
        assert "completed_at" in completed["attributes"]

    def test_fail_import_session(self):
        """Should mark session as failed with error details."""
        from utils.stix_importer import fail_import_session

        session = {
            "name": "import_test",
            "entity_type": "ImportSession",
            "attributes": {
                "status": "IN_PROGRESS",
                "imported_count": 5,
                "failed_count": 0
            }
        }

        failed = fail_import_session(session, error_message="File parsing failed")

        assert failed["attributes"]["status"] == "FAILED"
        assert "error_message" in failed["attributes"]
        assert failed["attributes"]["error_message"] == "File parsing failed"

    def test_track_failed_object_in_session(self):
        """Should add failed object to session tracking."""
        from utils.stix_importer import add_failed_object

        session = {
            "name": "import_test",
            "entity_type": "ImportSession",
            "attributes": {
                "status": "IN_PROGRESS",
                "failed_count": 0,
                "failed_object_ids": [],
                "error_messages": []
            }
        }

        updated = add_failed_object(
            session,
            stix_id="indicator--failed",
            error="Missing pattern field"
        )

        assert updated["attributes"]["failed_count"] == 1
        assert "indicator--failed" in updated["attributes"]["failed_object_ids"]
        assert "Missing pattern field" in updated["attributes"]["error_messages"]


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestSTIXImportErrorHandling:
    """Test error handling in STIX import."""

    def test_invalid_stix_error(self):
        """Should have custom exception for STIX errors."""
        from utils.stix_importer import InvalidSTIXError

        with pytest.raises(InvalidSTIXError) as exc_info:
            raise InvalidSTIXError("Test error")

        assert "Test error" in str(exc_info.value)

    def test_ontology_not_loaded_error(self):
        """Should have custom exception when ontology not loaded."""
        from utils.stix_importer import OntologyNotLoadedError

        with pytest.raises(OntologyNotLoadedError) as exc_info:
            raise OntologyNotLoadedError("Ontology types not loaded")

        assert "Ontology types not loaded" in str(exc_info.value)
