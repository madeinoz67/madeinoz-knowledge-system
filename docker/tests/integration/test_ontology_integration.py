"""
Integration Tests: OSINT/CTI Ontology Support (Feature 018)

Tests the complete ontology lifecycle:
- T017: Custom entity type extraction from content (US1)
- T032: Custom relationship type extraction from content (US2)
- T068: Breaking change detection on config reload (US4)
- T069: CTI base template loading (US4)

Prerequisites:
- Neo4j database running (test isolation with separate database)
- Graphiti MCP server with ontology patches loaded
- pytest and pytest-asyncio installed
"""

import asyncio
import os
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
import json

try:
    import pytest
except ImportError:
    pytest = None

# Add docker/ to path so 'patches' package can be imported
docker_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(docker_dir))

# Import ontology modules
from patches.ontology_config import (
    load_ontology_config,
    reset_ontology_cache,
    OntologyConfig,
    EntityTypeConfig,
    RelationshipTypeConfig,
    AttributeDefinition,
    OntologyDecayConfig,
    list_ontology_types,
)


# ==============================================================================
# Test Fixtures
# ==============================================================================

def _pytest_fixture_decorator(func):
    """Conditional pytest.fixture decorator."""
    if pytest is not None:
        return pytest.fixture(func)
    return func


def _pytest_asyncio_decorator(func):
    """Conditional pytest.mark.asyncio decorator."""
    if pytest is not None and hasattr(pytest.mark, 'asyncio'):
        return pytest.mark.asyncio(func)
    return func


@_pytest_fixture_decorator
def sample_ontology_config():
    """Sample ontology configuration with ThreatActor type."""
    return OntologyConfig(
        version="1.0.0",
        name="CTI Base",
        description="Cyber Threat Intelligence ontology",
        entity_types=[
            EntityTypeConfig(
                name="ThreatActor",
                description="Actor responsible for cyber threats",
                attributes=[
                    AttributeDefinition(
                        name="aliases",
                        type="list",
                        required=False,
                        description="Alternative names for the threat actor"
                    ),
                    AttributeDefinition(
                        name="sophistication",
                        type="string",
                        required=False,
                        description="Technical sophistication level"
                    ),
                    AttributeDefinition(
                        name="country",
                        type="string",
                        required=False,
                        description="Country of origin"
                    )
                ],
                decay_config=OntologyDecayConfig(
                    half_life_days=180,
                    importance_floor=0.5,
                    stability_multiplier=1.2
                )
            ),
            EntityTypeConfig(
                name="Malware",
                description="Malicious software",
                attributes=[
                    AttributeDefinition(
                        name="family",
                        type="string",
                        required=False,
                        description="Malware family"
                    ),
                    AttributeDefinition(
                        name="first_seen",
                        type="datetime",
                        required=False,
                        description="When the malware was first observed"
                    )
                ]
            )
        ],
        relationship_types=[
            RelationshipTypeConfig(
                name="uses",
                description="Threat actor uses malware",
                source_entity_types=["ThreatActor"],
                target_entity_types=["Malware"],
                bidirectional=False
            )
        ]
    )


@_pytest_fixture_decorator
def temp_ontology_yaml(sample_ontology_config):
    """Create a temporary ontology YAML file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml_data = {
            "version": "1.0.0",
            "name": "CTI Test",
            "description": "Test ontology for integration tests",
            "entity_types": [
                {
                    "name": "ThreatActor",
                    "description": "Actor responsible for cyber threats",
                    "attributes": [
                        {
                            "name": "aliases",
                            "type": "list",
                            "required": False,
                            "description": "Alternative names"
                        },
                        {
                            "name": "country",
                            "type": "string",
                            "required": False
                        }
                    ],
                    "decay_config": {
                        "half_life_days": 180
                    }
                },
                {
                    "name": "Malware",
                    "description": "Malicious software",
                    "attributes": [
                        {
                            "name": "family",
                            "type": "string",
                            "required": False
                        }
                    ]
                }
            ],
            "relationship_types": [
                {
                    "name": "uses",
                    "description": "Threat actor uses malware",
                    "source_entity_types": ["ThreatActor"],
                    "target_entity_types": ["Malware"]
                }
            ]
        }
        json.dump(yaml_data, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    try:
        os.unlink(temp_path)
    except:
        pass


# ==============================================================================
# T017: Custom Entity Type Extraction (US1)
# ==============================================================================

class TestCustomEntityTypeExtraction:
    """
    Test suite for custom entity type extraction from content.

    T017 [US1]: Integration test for custom entity type extraction.
    Verifies that ThreatActor entities are created from content when type is defined.
    """

    def test_ontology_config_loads_from_yaml(self, temp_ontology_yaml):
        """Test that ontology configuration loads correctly from YAML file."""
        # Reset cache to ensure fresh load
        reset_ontology_cache()

        # Load config from temp file
        with patch.dict(os.environ, {'ONTOLOGY_CONFIG_PATH': temp_ontology_yaml}):
            from patches.ontology_config import _resolve_config_path
            resolved = patch('patches.ontology_config._resolve_config_path', return_value=Path(temp_ontology_yaml))
            resolved.start()
            try:
                config = load_ontology_config()
            finally:
                resolved.stop()

        # Verify entity types loaded
        assert len(config.entity_types) == 2
        entity_type_names = {et.name for et in config.entity_types}
        assert "ThreatActor" in entity_type_names
        assert "Malware" in entity_type_names

        # Verify ThreatActor attributes
        threat_actor = next(et for et in config.entity_types if et.name == "ThreatActor")
        assert len(threat_actor.attributes) == 2
        attr_names = {attr.name for attr in threat_actor.attributes}
        assert "aliases" in attr_names
        assert "country" in attr_names

        # Verify decay config
        assert threat_actor.decay_config is not None
        assert threat_actor.decay_config.half_life_days == 180

    def test_list_ontology_types_returns_entity_and_relationship_types(self, temp_ontology_yaml):
        """Test that list_ontology_types returns all configured types."""
        reset_ontology_cache()

        with patch.dict(os.environ, {'ONTOLOGY_CONFIG_PATH': temp_ontology_yaml}):
            resolved = patch('patches.ontology_config._resolve_config_path', return_value=Path(temp_ontology_yaml))
            resolved.start()
            try:
                result = list_ontology_types()
            finally:
                resolved.stop()

        # Verify structure
        assert "entity_types" in result
        assert "relationship_types" in result

        # Verify entity types
        assert len(result["entity_types"]) == 2
        entity_names = {et["name"] for et in result["entity_types"]}
        assert "ThreatActor" in entity_names
        assert "Malware" in entity_names

        # Verify entity type structure
        threat_actor = next(et for et in result["entity_types"] if et["name"] == "ThreatActor")
        assert threat_actor["description"] == "Actor responsible for cyber threats"
        assert "attributes" in threat_actor
        assert len(threat_actor["attributes"]) == 2
        assert threat_actor["decay_config"]["half_life_days"] == 180

        # Verify relationship types
        assert len(result["relationship_types"]) == 1
        uses_rel = result["relationship_types"][0]
        assert uses_rel["name"] == "uses"
        assert uses_rel["source_entity_types"] == ["ThreatActor"]
        assert uses_rel["target_entity_types"] == ["Malware"]

    def test_get_entity_types_dict_returns_dynamic_models(self, temp_ontology_yaml):
        """Test that get_entity_types_dict creates Pydantic models for each type."""
        reset_ontology_cache()

        with patch.dict(os.environ, {'ONTOLOGY_CONFIG_PATH': temp_ontology_yaml}):
            resolved = patch('patches.ontology_config._resolve_config_path', return_value=Path(temp_ontology_yaml))
            resolved.start()
            try:
                from patches.ontology_config import get_entity_types_dict
                entity_types = get_entity_types_dict()
            finally:
                resolved.stop()

        # Verify models created
        assert "ThreatActor" in entity_types
        assert "Malware" in entity_types

        # Verify they are Pydantic BaseModel classes
        from pydantic import BaseModel
        assert issubclass(entity_types["ThreatActor"], BaseModel)
        assert issubclass(entity_types["Malware"], BaseModel)

    def test_decay_config_retrieval_for_entity_type(self, temp_ontology_yaml):
        """Test retrieving decay configuration for a specific entity type."""
        reset_ontology_cache()

        with patch.dict(os.environ, {'ONTOLOGY_CONFIG_PATH': temp_ontology_yaml}):
            resolved = patch('patches.ontology_config._resolve_config_path', return_value=Path(temp_ontology_yaml))
            resolved.start()
            try:
                from patches.ontology_config import get_decay_config_for_type
                decay_config = get_decay_config_for_type("ThreatActor")
            finally:
                resolved.stop()

        # Verify decay config
        assert decay_config.half_life_days == 180
        assert decay_config.importance_floor == 0.5
        assert decay_config.stability_multiplier == 1.2

    def test_permanent_flag_detection_for_entity_type(self, sample_ontology_config):
        """Test checking if an entity type is marked as permanent."""
        # Create a permanent entity type
        permanent_config = EntityTypeConfig(
            name="CriticalAPT",
            description="Critical APT group that should never decay",
            permanent=True
        )

        assert permanent_config.permanent is True

        # Test with is_entity_type_permanent function
        with patch('patches.ontology_config._config_cache', sample_ontology_config):
            from patches.ontology_config import is_entity_type_permanent
            # Non-permanent type
            assert is_entity_type_permanent("ThreatActor") is False
            # Unknown type
            assert is_entity_type_permanent("UnknownType") is False


# ==============================================================================
# T032: Custom Relationship Type Extraction (US2) - Placeholder
# ==============================================================================

class TestCustomRelationshipTypeExtraction:
    """
    Test suite for custom relationship type extraction from content.

    T032 [US2]: Integration test for custom relationship type extraction.
    Verifies that "uses" relationships are created from content when type is defined.

    T031 [US2]: Unit test for relationship type registration.
    T043 [US2]: Unit test for relationship type validation.
    """

    def test_relationship_type_validation(self, sample_ontology_config):
        """Test that relationship types reference valid entity types."""
        # This should validate successfully
        assert len(sample_ontology_config.relationship_types) == 1

        uses_rel = sample_ontology_config.relationship_types[0]
        assert uses_rel.name == "uses"
        assert "ThreatActor" in uses_rel.source_entity_types
        assert "Malware" in uses_rel.target_entity_types

    def test_get_relationship_types_dict_returns_configured_types(self, temp_ontology_yaml):
        """Test T031: get_relationship_types_dict returns configured relationship types."""
        reset_ontology_cache()

        with patch.dict(os.environ, {'ONTOLOGY_CONFIG_PATH': temp_ontology_yaml}):
            resolved = patch('patches.ontology_config._resolve_config_path', return_value=Path(temp_ontology_yaml))
            resolved.start()
            try:
                from patches.ontology_config import get_relationship_types_dict
                rel_types = get_relationship_types_dict()
            finally:
                resolved.stop()

        # Verify relationship types returned
        assert "uses" in rel_types
        assert rel_types["uses"].name == "uses"
        assert rel_types["uses"].source_entity_types == ["ThreatActor"]
        assert rel_types["uses"].target_entity_types == ["Malware"]

    def test_get_relationship_type_lookup(self, temp_ontology_yaml):
        """Test T031: get_relationship_type looks up specific relationship."""
        reset_ontology_cache()

        with patch.dict(os.environ, {'ONTOLOGY_CONFIG_PATH': temp_ontology_yaml}):
            resolved = patch('patches.ontology_config._resolve_config_path', return_value=Path(temp_ontology_yaml))
            resolved.start()
            try:
                from patches.ontology_config import get_relationship_type
                rel_type = get_relationship_type("uses")
            finally:
                resolved.stop()

        # Verify relationship type found
        assert rel_type is not None
        assert rel_type.name == "uses"
        assert rel_type.description == "Threat actor uses malware"

    def test_get_relationship_type_not_found(self, temp_ontology_yaml):
        """Test T031: get_relationship_type returns None for unknown type."""
        reset_ontology_cache()

        with patch.dict(os.environ, {'ONTOLOGY_CONFIG_PATH': temp_ontology_yaml}):
            resolved = patch('patches.ontology_config._resolve_config_path', return_value=Path(temp_ontology_yaml))
            resolved.start()
            try:
                from patches.ontology_config import get_relationship_type
                rel_type = get_relationship_type("unknown_relationship")
            finally:
                resolved.stop()

        # Verify relationship type not found
        assert rel_type is None

    def test_validate_relationship_types_valid(self, temp_ontology_yaml):
        """Test T043: validate_relationship_types accepts valid combination."""
        reset_ontology_cache()

        with patch.dict(os.environ, {'ONTOLOGY_CONFIG_PATH': temp_ontology_yaml}):
            resolved = patch('patches.ontology_config._resolve_config_path', return_value=Path(temp_ontology_yaml))
            resolved.start()
            try:
                from patches.ontology_config import validate_relationship_types
                is_valid, error = validate_relationship_types("ThreatActor", "Malware", "uses")
            finally:
                resolved.stop()

        # Should be valid
        assert is_valid is True
        assert error is None

    def test_validate_relationship_types_invalid_source(self, temp_ontology_yaml):
        """Test T043: validate_relationship_types rejects invalid source type."""
        reset_ontology_cache()

        with patch.dict(os.environ, {'ONTOLOGY_CONFIG_PATH': temp_ontology_yaml}):
            resolved = patch('patches.ontology_config._resolve_config_path', return_value=Path(temp_ontology_yaml))
            resolved.start()
            try:
                from patches.ontology_config import validate_relationship_types
                is_valid, error = validate_relationship_types("InvalidType", "Malware", "uses")
            finally:
                resolved.stop()

        # Should be invalid
        assert is_valid is False
        assert error is not None
        assert "InvalidType" in error
        assert "not valid" in error

    def test_validate_relationship_types_invalid_target(self, temp_ontology_yaml):
        """Test T043: validate_relationship_types rejects invalid target type."""
        reset_ontology_cache()

        with patch.dict(os.environ, {'ONTOLOGY_CONFIG_PATH': temp_ontology_yaml}):
            resolved = patch('patches.ontology_config._resolve_config_path', return_value=Path(temp_ontology_yaml))
            resolved.start()
            try:
                from patches.ontology_config import validate_relationship_types
                is_valid, error = validate_relationship_types("ThreatActor", "InvalidType", "uses")
            finally:
                resolved.stop()

        # Should be invalid
        assert is_valid is False
        assert error is not None
        assert "InvalidType" in error
        assert "not valid" in error

    def test_validate_relationship_types_unknown_relationship(self, temp_ontology_yaml):
        """Test T043: validate_relationship_types rejects unknown relationship."""
        reset_ontology_cache()

        with patch.dict(os.environ, {'ONTOLOGY_CONFIG_PATH': temp_ontology_yaml}):
            resolved = patch('patches.ontology_config._resolve_config_path', return_value=Path(temp_ontology_yaml))
            resolved.start()
            try:
                from patches.ontology_config import validate_relationship_types
                is_valid, error = validate_relationship_types("ThreatActor", "Malware", "unknown_rel")
            finally:
                resolved.stop()

        # Should be invalid
        assert is_valid is False
        assert error is not None
        assert "unknown_rel" in error
        assert "not defined" in error


# ==============================================================================
# T068, T069: Template Loading and Breaking Changes (US4)
# ==============================================================================

class TestBreakingChangeDetection:
    """
    Test suite for breaking change detection (T068).

    T068 [US4]: Breaking change detection on config reload
    """

    def test_detect_breaking_changes_removes_type(self):
        """Test detection of removed entity types."""
        from patches.ontology_config import detect_breaking_changes

        old_config = OntologyConfig(
            version="1.0.0",
            entity_types=[
                EntityTypeConfig(name="ThreatActor", description="Actor")
            ]
        )

        new_config = OntologyConfig(
            version="2.0.0",
            entity_types=[]
        )

        changes = detect_breaking_changes(old_config, new_config)

        assert len(changes) > 0
        removal = next((c for c in changes if c["type"] == "entity_type_removed"), None)
        assert removal is not None
        assert "ThreatActor" in removal["description"]

    def test_detect_breaking_changes_removes_attribute(self):
        """Test detection of removed entity type attributes."""
        from patches.ontology_config import detect_breaking_changes

        old_config = OntologyConfig(
            version="1.0.0",
            entity_types=[
                EntityTypeConfig(
                    name="ThreatActor",
                    description="Actor",
                    attributes=[
                        AttributeDefinition(name="aliases", type="list", required=False),
                        AttributeDefinition(name="country", type="string", required=False)
                    ]
                )
            ]
        )

        new_config = OntologyConfig(
            version="2.0.0",
            entity_types=[
                EntityTypeConfig(
                    name="ThreatActor",
                    description="Actor",
                    attributes=[
                        AttributeDefinition(name="aliases", type="list", required=False)
                    ]
                )
            ]
        )

        changes = detect_breaking_changes(old_config, new_config)

        assert len(changes) > 0
        removal = next((c for c in changes if c["type"] == "attribute_removed"), None)
        assert removal is not None
        assert "country" in removal["description"]

    def test_detect_breaking_changes_changes_attribute_type(self):
        """Test detection of changed attribute types."""
        from patches.ontology_config import detect_breaking_changes

        old_config = OntologyConfig(
            version="1.0.0",
            entity_types=[
                EntityTypeConfig(
                    name="ThreatActor",
                    description="Actor",
                    attributes=[
                        AttributeDefinition(name="sophistication", type="string", required=False)
                    ]
                )
            ]
        )

        new_config = OntologyConfig(
            version="2.0.0",
            entity_types=[
                EntityTypeConfig(
                    name="ThreatActor",
                    description="Actor",
                    attributes=[
                        AttributeDefinition(name="sophistication", type="number", required=False)
                    ]
                )
            ]
        )

        changes = detect_breaking_changes(old_config, new_config)

        assert len(changes) > 0
        type_change = next((c for c in changes if c["type"] == "attribute_type_changed"), None)
        assert type_change is not None
        assert "sophistication" in type_change["description"]

    def test_detect_breaking_changes_no_changes(self):
        """Test that identical configs have no breaking changes."""
        from patches.ontology_config import detect_breaking_changes

        config = OntologyConfig(
            version="1.0.0",
            entity_types=[
                EntityTypeConfig(
                    name="ThreatActor",
                    description="Actor",
                    attributes=[
                        AttributeDefinition(name="aliases", type="list", required=False)
                    ]
                )
            ]
        )

        changes = detect_breaking_changes(config, config)

        assert len(changes) == 0


class TestCtiBaseTemplate:
    """
    Test suite for CTI base template loading (T069).

    T069 [US4]: CTI base template loading
    """

    def test_cti_base_template_loads(self):
        """Test that cti-base.yaml template loads successfully."""
        from patches.ontology_config import load_template

        config = load_template("cti-base")

        assert config is not None
        assert config.name == "CTI Base Ontology"
        assert len(config.entity_types) == 7

        entity_names = {et.name for et in config.entity_types}
        assert "ThreatActor" in entity_names
        assert "Malware" in entity_names
        assert "Vulnerability" in entity_names
        assert "Campaign" in entity_names
        assert "Indicator" in entity_names
        assert "Infrastructure" in entity_names
        assert "TTP" in entity_names

    def test_cti_base_template_relationships(self):
        """Test that cti-base.yaml has all required relationship types."""
        from patches.ontology_config import load_template

        config = load_template("cti-base")

        assert len(config.relationship_types) == 8

        rel_names = {rt.name for rt in config.relationship_types}
        assert "uses" in rel_names
        assert "targets" in rel_names
        assert "associated_with" in rel_names
        assert "attributed_to" in rel_names
        assert "exploits" in rel_names
        assert "variant_of" in rel_names
        assert "located_at" in rel_names
        assert "communicates_with" in rel_names

    def test_cti_base_template_decay_configs(self):
        """Test that CTI entity types have appropriate decay configs."""
        from patches.ontology_config import load_template

        config = load_template("cti-base")

        # Check ThreatActor decay config
        threat_actor = next((et for et in config.entity_types if et.name == "ThreatActor"), None)
        assert threat_actor is not None
        assert threat_actor.decay_config is not None
        assert threat_actor.decay_config.half_life_days == 180

        # Check Indicator decay config (shorter half-life)
        indicator = next((et for et in config.entity_types if et.name == "Indicator"), None)
        assert indicator is not None
        assert indicator.decay_config is not None
        assert indicator.decay_config.half_life_days == 90

        # Check TTP is permanent
        ttp = next((et for et in config.entity_types if et.name == "TTP"), None)
        assert ttp is not None
        assert ttp.permanent is True

    def test_merge_cti_and_osint_templates(self):
        """Test merging CTI and OSINT base templates."""
        from patches.ontology_config import load_templates_with_dependencies

        merged = load_templates_with_dependencies("cti-base", "osint-base")

        # Should have all entity types from both templates
        entity_names = {et.name for et in merged.entity_types}

        # CTI types
        assert "ThreatActor" in entity_names
        assert "Malware" in entity_names
        assert "TTP" in entity_names

        # OSINT types
        assert "Account" in entity_names
        assert "Domain" in entity_names
        assert "Email" in entity_names
        assert "Phone" in entity_names
        assert "Image" in entity_names
        assert "Investigation" in entity_names


# ==============================================================================
# Test Runner
# ==============================================================================

if pytest is not None:
    # pytest will discover and run tests
    pass
else:
    print("pytest not available - skipping test execution")
