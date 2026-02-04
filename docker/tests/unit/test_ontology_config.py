"""
Unit Tests for Ontology Configuration Module

Feature: 018-osint-ontology
Tests: T012, T013, T014, T015, T016 (Unit tests for User Story 1)
       T030, T031 (Unit tests for User Story 2)
       T065, T066, T067 (Unit tests for User Story 4)
       T078, T079 (Unit tests for User Story 5)

TDD Approach: Tests written FIRST, implementation follows
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

# Mock the module before importing for tests
import sys
from unittest.mock import MagicMock, patch

# Configure test logging
logging.basicConfig(level=logging.DEBUG)


class TestAttributeDefinition:
    """Test suite for AttributeDefinition Pydantic model."""

    def test_valid_string_attribute(self):
        """Test creating a valid string attribute definition."""
        from utils.ontology_config import AttributeDefinition

        attr = AttributeDefinition(
            name="aliases",
            type="string",
            required=False,
            description="Alternative names"
        )

        assert attr.name == "aliases"
        assert attr.type == "string"
        assert attr.required is False
        assert attr.description == "Alternative names"

    def test_valid_list_attribute(self):
        """Test creating a valid list attribute definition."""
        from utils.ontology_config import AttributeDefinition

        attr = AttributeDefinition(
            name="tags",
            type="list",
            required=True
        )

        assert attr.name == "tags"
        assert attr.type == "list"
        assert attr.required is True

    def test_invalid_attribute_type(self):
        """Test that invalid attribute types raise ValidationError."""
        from utils.ontology_config import AttributeDefinition

        with pytest.raises(ValidationError):
            AttributeDefinition(
                name="invalid",
                type="invalid_type"
            )

    def test_all_valid_attribute_types(self):
        """Test that all valid attribute types are accepted."""
        from utils.ontology_config import AttributeDefinition

        valid_types = ["string", "number", "boolean", "datetime", "list"]

        for attr_type in valid_types:
            attr = AttributeDefinition(
                name=f"attr_{attr_type}",
                type=attr_type,
                required=False
            )
            assert attr.type == attr_type


class TestDecayConfigForOntology:
    """Test suite for OntologyDecayConfig Pydantic model."""

    def test_default_decay_config(self):
        """Test creating decay config with defaults."""
        from utils.ontology_config import OntologyDecayConfig

        config = OntologyDecayConfig()

        assert config.half_life_days == 180  # Default for CTI entities
        assert config.importance_floor is None
        assert config.stability_multiplier is None

    def test_custom_decay_config(self):
        """Test creating decay config with custom values."""
        from utils.ontology_config import OntologyDecayConfig

        config = OntologyDecayConfig(
            half_life_days=90,
            importance_floor=0.3,
            stability_multiplier=0.8
        )

        assert config.half_life_days == 90
        assert config.importance_floor == 0.3
        assert config.stability_multiplier == 0.8

    def test_negative_half_life_rejected(self):
        """Test that negative half_life_days is rejected."""
        from utils.ontology_config import OntologyDecayConfig

        with pytest.raises(ValidationError):
            OntologyDecayConfig(half_life_days=-10)


class TestEntityTypeConfig:
    """Test suite for EntityTypeConfig Pydantic model."""

    def test_minimal_entity_type(self):
        """Test creating minimal valid entity type."""
        from utils.ontology_config import EntityTypeConfig

        entity = EntityTypeConfig(
            name="ThreatActor",
            description="Actor responsible for cyber threats"
        )

        assert entity.name == "ThreatActor"
        assert entity.description == "Actor responsible for cyber threats"
        assert entity.parent_type is None
        assert entity.icon is None
        assert entity.decay_config is None
        assert entity.attributes == []

    def test_entity_type_with_attributes(self):
        """Test creating entity type with attributes."""
        from utils.ontology_config import EntityTypeConfig, AttributeDefinition

        entity = EntityTypeConfig(
            name="ThreatActor",
            description="Actor responsible for cyber threats",
            attributes=[
                AttributeDefinition(
                    name="aliases",
                    type="list",
                    required=False
                ),
                AttributeDefinition(
                    name="country",
                    type="string",
                    required=False
                )
            ]
        )

        assert len(entity.attributes) == 2
        assert entity.attributes[0].name == "aliases"
        assert entity.attributes[1].name == "country"

    def test_entity_type_with_decay_config(self):
        """Test creating entity type with custom decay config."""
        from utils.ontology_config import EntityTypeConfig, OntologyDecayConfig

        decay = OntologyDecayConfig(half_life_days=180)
        entity = EntityTypeConfig(
            name="ThreatActor",
            description="Actor responsible for cyber threats",
            decay_config=decay
        )

        assert entity.decay_config.half_life_days == 180

    def test_entity_type_with_parent(self):
        """Test creating entity type with parent."""
        from utils.ontology_config import EntityTypeConfig

        entity = EntityTypeConfig(
            name="APT",
            description="Advanced Persistent Threat group",
            parent_type="ThreatActor"
        )

        assert entity.parent_type == "ThreatActor"

    def test_reserved_attribute_rejection(self):
        """Test that reserved attributes are rejected (T014)."""
        from utils.ontology_config import EntityTypeConfig, AttributeDefinition, RESERVED_ATTRIBUTES

        for reserved in RESERVED_ATTRIBUTES:
            with pytest.raises(ValidationError) as exc_info:
                EntityTypeConfig(
                    name="TestEntity",
                    description="Test entity",
                    attributes=[
                        AttributeDefinition(
                            name=reserved,
                            type="string",
                            required=False
                        )
                    ]
                )
            assert "reserved" in str(exc_info.value).lower()


class TestRelationshipTypeConfig:
    """Test suite for RelationshipTypeConfig Pydantic model (T030)."""

    def test_minimal_relationship_type(self):
        """Test creating minimal valid relationship type."""
        from utils.ontology_config import RelationshipTypeConfig

        rel = RelationshipTypeConfig(
            name="uses",
            description="Threat actor uses malware",
            source_entity_types=["ThreatActor"],
            target_entity_types=["Malware"],
            bidirectional=False
        )

        assert rel.name == "uses"
        assert rel.source_entity_types == ["ThreatActor"]
        assert rel.target_entity_types == ["Malware"]
        assert rel.bidirectional is False

    def test_relationship_type_with_attributes(self):
        """Test creating relationship type with attributes."""
        from utils.ontology_config import RelationshipTypeConfig, AttributeDefinition

        rel = RelationshipTypeConfig(
            name="uses",
            description="Threat actor uses malware",
            source_entity_types=["ThreatActor"],
            target_entity_types=["Malware"],
            bidirectional=False,
            attributes=[
                AttributeDefinition(
                    name="confidence",
                    type="number",
                    required=False
                )
            ]
        )

        assert len(rel.attributes) == 1
        assert rel.attributes[0].name == "confidence"

    def test_bidirectional_relationship(self):
        """Test creating bidirectional relationship."""
        from utils.ontology_config import RelationshipTypeConfig

        rel = RelationshipTypeConfig(
            name="associated_with",
            description="Two entities are associated",
            source_entity_types=["Person"],
            target_entity_types=["Organization"],
            bidirectional=True
        )

        assert rel.bidirectional is True

    def test_relationship_with_inverse(self):
        """Test creating relationship with inverse name."""
        from utils.ontology_config import RelationshipTypeConfig

        rel = RelationshipTypeConfig(
            name="targets",
            description="Threat actor targets organization",
            source_entity_types=["ThreatActor"],
            target_entity_types=["Organization"],
            bidirectional=False,
            inverse_name="targeted_by"
        )

        assert rel.inverse_name == "targeted_by"

    def test_multiple_source_types(self):
        """Test relationship with multiple source types."""
        from utils.ontology_config import RelationshipTypeConfig

        rel = RelationshipTypeConfig(
            name="located_at",
            description="Entity is located at location",
            source_entity_types=["Person", "Organization", "Infrastructure"],
            target_entity_types=["Location"],
            bidirectional=False
        )

        assert len(rel.source_entity_types) == 3


class TestOntologyConfig:
    """Test suite for OntologyConfig Pydantic model."""

    def test_minimal_ontology_config(self):
        """Test creating minimal ontology config."""
        from utils.ontology_config import OntologyConfig

        config = OntologyConfig(
            version="1.0.0",
            entity_types=[],
            relationship_types=[]
        )

        assert config.version == "1.0.0"
        assert config.entity_types == []
        assert config.relationship_types == []

    def test_ontology_config_with_entity_types(self):
        """Test creating ontology config with entity types."""
        from utils.ontology_config import OntologyConfig, EntityTypeConfig

        config = OntologyConfig(
            version="1.0.0",
            entity_types=[
                EntityTypeConfig(
                    name="ThreatActor",
                    description="Actor responsible for cyber threats"
                ),
                EntityTypeConfig(
                    name="Malware",
                    description="Malicious software"
                )
            ],
            relationship_types=[]
        )

        assert len(config.entity_types) == 2

    def test_ontology_config_with_metadata(self):
        """Test creating ontology config with metadata."""
        from utils.ontology_config import OntologyConfig

        config = OntologyConfig(
            version="1.0.0",
            name="CTI Base Ontology",
            description="Core CTI entity and relationship types",
            entity_types=[],
            relationship_types=[]
        )

        assert config.name == "CTI Base Ontology"
        assert config.description == "Core CTI entity and relationship types"


class TestYamlLoader:
    """Test suite for YAML loader functionality (T013)."""

    def test_load_valid_yaml(self, tmp_path):
        """Test loading valid ontology YAML file."""
        from utils.ontology_config import load_ontology_config

        yaml_content = """
        version: "1.0.0"
        name: Test Ontology
        entity_types:
          - name: ThreatActor
            description: Actor responsible for cyber threats
        relationship_types: []
        """

        config_file = tmp_path / "ontology.yaml"
        config_file.write_text(yaml_content)

        config = load_ontology_config(config_file)

        assert config.version == "1.0.0"
        assert config.name == "Test Ontology"
        assert len(config.entity_types) == 1
        assert config.entity_types[0].name == "ThreatActor"

    def test_load_with_cache(self, tmp_path):
        """Test that configuration is cached after first load."""
        from utils.ontology_config import load_ontology_config, reset_ontology_cache

        # Reset cache first
        reset_ontology_cache()

        yaml_content = """
        version: "1.0.0"
        entity_types: []
        relationship_types: []
        """

        config_file = tmp_path / "ontology.yaml"
        config_file.write_text(yaml_content)

        # First load
        config1 = load_ontology_config(config_file)
        # Second load (should be cached)
        config2 = load_ontology_config(config_file)

        assert config1 is config2  # Same object reference

    def test_force_reload(self, tmp_path):
        """Test force_reload parameter bypasses cache."""
        from utils.ontology_config import load_ontology_config, reset_ontology_cache

        reset_ontology_cache()

        yaml_content = """
        version: "1.0.0"
        entity_types: []
        relationship_types: []
        """

        config_file = tmp_path / "ontology.yaml"
        config_file.write_text(yaml_content)

        config1 = load_ontology_config(config_file)

        # Modify file
        yaml_content2 = """
        version: "1.1.0"
        entity_types: []
        relationship_types: []
        """
        config_file.write_text(yaml_content2)

        config2 = load_ontology_config(config_file, force_reload=False)
        config3 = load_ontology_config(config_file, force_reload=True)

        assert config2.version == "1.0.0"  # Cached
        assert config3.version == "1.1.0"  # Reloaded

    def test_load_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML raises error."""
        from utils.ontology_config import load_ontology_config
        import yaml

        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [unclosed")

        with pytest.raises(ValueError):
            load_ontology_config(config_file)

    def test_load_nonexistent_file_returns_default(self, tmp_path):
        """Test that nonexistent file returns default empty config."""
        from utils.ontology_config import load_ontology_config

        nonexistent = tmp_path / "does_not_exist.yaml"

        config = load_ontology_config(nonexistent)

        assert config.version == "1.0.0"
        assert config.entity_types == []
        assert config.relationship_types == []

    def test_environment_variable_path(self, tmp_path, monkeypatch):
        """Test that ONTOLOGY_CONFIG_PATH environment variable is respected."""
        from utils.ontology_config import load_ontology_config, reset_ontology_cache
        import os

        reset_ontology_cache()

        yaml_content = """
        version: "2.0.0"
        entity_types: []
        relationship_types: []
        """

        config_file = tmp_path / "env_ontology.yaml"
        config_file.write_text(yaml_content)

        monkeypatch.setenv("ONTOLOGY_CONFIG_PATH", str(config_file))

        config = load_ontology_config()

        assert config.version == "2.0.0"


class TestCircularDependencyDetection:
    """Test suite for circular dependency detection (T015, T066)."""

    def test_no_circular_dependency(self):
        """Test that acyclic dependency graph passes validation."""
        from utils.ontology_config import check_circular_dependencies

        dependencies = {
            "Malware": ["Software"],
            "Software": [],
            "ThreatActor": [],
        }

        has_cycle, cycle_path = check_circular_dependencies(dependencies)

        assert has_cycle is False
        assert cycle_path is None

    def test_direct_circular_dependency(self):
        """Test detection of direct circular dependency (A -> B -> A)."""
        from utils.ontology_config import check_circular_dependencies

        dependencies = {
            "Malware": ["Software"],
            "Software": ["Malware"],
        }

        has_cycle, cycle_path = check_circular_dependencies(dependencies)

        assert has_cycle is True
        assert "Malware" in cycle_path
        assert "Software" in cycle_path

    def test_complex_circular_dependency(self):
        """Test detection of complex cycle (A -> B -> C -> A)."""
        from utils.ontology_config import check_circular_dependencies

        dependencies = {
            "A": ["B"],
            "B": ["C"],
            "C": ["A"],
        }

        has_cycle, cycle_path = check_circular_dependencies(dependencies)

        assert has_cycle is True
        assert len(cycle_path) == 3

    def test_self_dependency(self):
        """Test that self-dependency is detected as circular."""
        from utils.ontology_config import check_circular_dependencies

        dependencies = {
            "Malware": ["Malware"],
        }

        has_cycle, cycle_path = check_circular_dependencies(dependencies)

        assert has_cycle is True


class TestReservedAttributes:
    """Test suite for reserved attributes validation (T014, T095)."""

    def test_reserved_attributes_constant(self):
        """Test that RESERVED_ATTRIBUTES contains expected values."""
        from utils.ontology_config import RESERVED_ATTRIBUTES

        expected = {
            "uuid", "name", "labels", "created_at",
            "summary", "attributes", "name_embedding"
        }

        assert set(RESERVED_ATTRIBUTES) == expected

    def test_entity_with_reserved_attribute_fails(self):
        """Test that entity type with reserved attribute fails validation."""
        from utils.ontology_config import EntityTypeConfig, AttributeDefinition

        with pytest.raises(ValidationError) as exc_info:
            EntityTypeConfig(
                name="InvalidEntity",
                description="Entity with reserved attribute",
                attributes=[
                    AttributeDefinition(
                        name="uuid",
                        type="string",
                        required=False
                    )
                ]
            )

        assert "reserved" in str(exc_info.value).lower() or "uuid" in str(exc_info.value).lower()

    def test_relationship_with_reserved_attribute_fails(self):
        """Test that relationship type with reserved attribute fails validation."""
        from utils.ontology_config import RelationshipTypeConfig, AttributeDefinition

        with pytest.raises(ValidationError):
            RelationshipTypeConfig(
                name="has_reserved",
                description="Relationship with reserved attribute",
                source_entity_types=["Entity"],
                target_entity_types=["Entity"],
                bidirectional=False,
                attributes=[
                    AttributeDefinition(
                        name="created_at",
                        type="datetime",
                        required=False
                    )
                ]
            )

    def test_valid_attributes_pass(self):
        """Test that non-reserved attributes pass validation."""
        from utils.ontology_config import EntityTypeConfig, AttributeDefinition

        # Should not raise
        entity = EntityTypeConfig(
            name="ValidEntity",
            description="Entity with valid attributes",
            attributes=[
                AttributeDefinition(name="custom_field", type="string", required=False),
                AttributeDefinition(name="score", type="number", required=False),
            ]
        )

        assert len(entity.attributes) == 2


class TestDecayConfigRetrieval:
    """Test suite for per-type decay config retrieval (T078, T085)."""

    def test_get_decay_for_entity_type(self, tmp_path):
        """Test retrieving decay config for specific entity type."""
        from utils.ontology_config import load_ontology_config, get_decay_config_for_type

        yaml_content = """
        version: "1.0.0"
        entity_types:
          - name: ThreatActor
            description: Threat actor
            decay_config:
              half_life_days: 180
              importance_floor: 0.5
          - name: Indicator
            description: Indicator
            decay_config:
              half_life_days: 90
        relationship_types: []
        """

        config_file = tmp_path / "ontology.yaml"
        config_file.write_text(yaml_content)

        load_ontology_config(config_file)

        threat_actor_decay = get_decay_config_for_type("ThreatActor")
        indicator_decay = get_decay_config_for_type("Indicator")
        unknown_decay = get_decay_config_for_type("Unknown")

        assert threat_actor_decay.half_life_days == 180
        assert threat_actor_decay.importance_floor == 0.5

        assert indicator_decay.half_life_days == 90

        # Unknown type should return default
        assert unknown_decay.half_life_days == 180  # Default CTI half-life

    def test_permanent_flag_handling(self, tmp_path):
        """Test that entities can be marked as permanent (T079, T087)."""
        from utils.ontology_config import load_ontology_config, is_entity_type_permanent

        yaml_content = """
        version: "1.0.0"
        entity_types:
          - name: CriticalAPT
            description: Critical APT group
            permanent: true
          - name: ThreatActor
            description: Regular threat actor
        relationship_types: []
        """

        config_file = tmp_path / "ontology.yaml"
        config_file.write_text(yaml_content)

        load_ontology_config(config_file)

        assert is_entity_type_permanent("CriticalAPT") is True
        assert is_entity_type_permanent("ThreatActor") is False


class TestReloadOntology:
    """Test suite for hot-reload functionality (T011, T093)."""

    def test_reload_ontology_detects_version_change(self, tmp_path):
        """Test that reload detects version changes."""
        from utils.ontology_config import load_ontology_config, reload_ontology_config, reset_ontology_cache

        reset_ontology_cache()

        yaml_v1 = """
        version: "1.0.0"
        entity_types:
          - name: ThreatActor
            description: Threat actor
        relationship_types: []
        """

        config_file = tmp_path / "ontology.yaml"
        config_file.write_text(yaml_v1)

        load_ontology_config(config_file)

        # Update file
        yaml_v2 = """
        version: "1.1.0"
        entity_types:
          - name: ThreatActor
            description: Updated threat actor description
          - name: Malware
            description: Malware
        relationship_types: []
        """
        config_file.write_text(yaml_v2)

        result = reload_ontology_config(config_file)

        assert result["reloaded"] is True
        assert result["previous_version"] == "1.0.0"
        assert result["new_version"] == "1.1.0"
        assert result["entity_types_loaded"] == 2

    def test_reload_with_force_flag(self, tmp_path):
        """Test that force flag reloads even with same version."""
        from utils.ontology_config import load_ontology_config, reload_ontology_config, reset_ontology_cache

        reset_ontology_cache()

        yaml_content = """
        version: "1.0.0"
        entity_types: []
        relationship_types: []
        """

        config_file = tmp_path / "ontology.yaml"
        config_file.write_text(yaml_content)

        load_ontology_config(config_file)

        result = reload_ontology_config(config_file, force=True)

        # Even without version change, force=True should reload
        assert result["reloaded"] is True
        assert result["previous_version"] == "1.0.0"
        assert result["new_version"] == "1.0.0"

    def test_reload_detects_breaking_changes(self, tmp_path):
        """Test that reload detects breaking changes (T068, T096)."""
        from utils.ontology_config import load_ontology_config, reload_ontology_config, reset_ontology_cache

        reset_ontology_cache()

        yaml_v1 = """
        version: "1.0.0"
        entity_types:
          - name: ThreatActor
            description: Threat actor
            attributes:
              - name: aliases
                type: list
                required: false
              - name: sophistication
                type: string
                required: false
        relationship_types: []
        """

        config_file = tmp_path / "ontology.yaml"
        config_file.write_text(yaml_v1)

        load_ontology_config(config_file)

        # Update with removed attribute (breaking change)
        yaml_v2 = """
        version: "2.0.0"
        entity_types:
          - name: ThreatActor
            description: Threat actor
            attributes:
              - name: aliases
                type: list
                required: false
        relationship_types: []
        """
        config_file.write_text(yaml_v2)

        result = reload_ontology_config(config_file)

        assert result["reloaded"] is True
        assert len(result["breaking_changes"]) > 0

        # Check that attribute removal is detected
        breaking_types = [bc["type"] for bc in result["breaking_changes"]]
        assert "attribute_removed" in breaking_types


class TestTemplateMerging:
    """Test suite for template merging functionality (T067, T076)."""

    def test_merge_templates(self, tmp_path):
        """Test merging multiple ontology templates."""
        from utils.ontology_config import OntologyConfig, merge_ontologies

        base = OntologyConfig(
            version="1.0.0",
            name="Base",
            entity_types=[
                {"name": "EntityA", "description": "Entity A"}
            ],
            relationship_types=[]
        )

        extension = OntologyConfig(
            version="1.0.0",
            name="Extension",
            entity_types=[
                {"name": "EntityB", "description": "Entity B"}
            ],
            relationship_types=[]
        )

        merged = merge_ontologies([base, extension])

        assert len(merged.entity_types) == 2
        entity_names = {et.name for et in merged.entity_types}
        assert entity_names == {"EntityA", "EntityB"}

    def test_merge_with_overrides(self, tmp_path):
        """Test that later templates override earlier ones."""
        from utils.ontology_config import OntologyConfig, merge_ontologies

        base = OntologyConfig(
            version="1.0.0",
            name="Base",
            entity_types=[
                {"name": "EntityA", "description": "Original description"}
            ],
            relationship_types=[]
        )

        override = OntologyConfig(
            version="1.0.0",
            name="Override",
            entity_types=[
                {"name": "EntityA", "description": "Overridden description"}
            ],
            relationship_types=[]
        )

        merged = merge_ontologies([base, override])

        assert len(merged.entity_types) == 1
        assert merged.entity_types[0].description == "Overridden description"

    def test_merge_relationship_types(self, tmp_path):
        """Test that merge combines relationship types from multiple templates."""
        from utils.ontology_config import OntologyConfig, merge_ontologies

        base = OntologyConfig(
            version="1.0.0",
            name="Base",
            entity_types=[],
            relationship_types=[
                {
                    "name": "relates_to",
                    "description": "Base relationship",
                    "source_entity_types": ["EntityA"],
                    "target_entity_types": ["EntityB"]
                }
            ]
        )

        extension = OntologyConfig(
            version="1.0.0",
            name="Extension",
            entity_types=[],
            relationship_types=[
                {
                    "name": "connects_to",
                    "description": "Extension relationship",
                    "source_entity_types": ["EntityA"],
                    "target_entity_types": ["EntityC"]
                }
            ]
        )

        merged = merge_ontologies([base, extension])

        assert len(merged.relationship_types) == 2
        rel_names = {rt.name for rt in merged.relationship_types}
        assert rel_names == {"relates_to", "connects_to"}

    def test_merge_preserves_metadata(self, tmp_path):
        """Test that merge uses base template metadata."""
        from utils.ontology_config import OntologyConfig, merge_ontologies

        base = OntologyConfig(
            version="1.0.0",
            name="Base",
            description="Base description",
            entity_types=[],
            relationship_types=[]
        )

        extension = OntologyConfig(
            version="2.0.0",
            name="Extension",
            description="Extension description",
            entity_types=[
                {"name": "EntityA", "description": "Entity A"}
            ],
            relationship_types=[]
        )

        merged = merge_ontologies([base, extension])

        # Metadata from base is preserved
        assert merged.version == "1.0.0"
        assert merged.name == "Base"
        assert merged.description == "Base description"
        # But entity types are combined
        assert len(merged.entity_types) == 1


class TestTemplateLoading:
    """Test suite for template loading functionality (T065)."""

    def test_list_available_templates(self, tmp_path):
        """Test listing available templates from templates directory."""
        from utils.ontology_config import list_available_templates

        # Create test templates directory
        templates_dir = tmp_path / "ontologies"
        templates_dir.mkdir()

        # Create test template files
        (templates_dir / "template1.yaml").write_text("version: '1.0.0'\nname: Template1")
        (templates_dir / "template2.yaml").write_text("version: '1.0.0'\nname: Template2")

        # Patch ONTOLOGY_TEMPLATES_DIR
        import utils.ontology_config
        original_dir = utils.ontology_config.ONTOLOGY_TEMPLATES_DIR
        utils.ontology_config.ONTOLOGY_TEMPLATES_DIR = templates_dir

        try:
            templates = list_available_templates()
            template_names = [t.name for t in templates]

            assert len(templates) == 2
            assert "template1.yaml" in template_names
            assert "template2.yaml" in template_names
        finally:
            utils.ontology_config.ONTOLOGY_TEMPLATES_DIR = original_dir

    def test_load_template_by_name(self, tmp_path):
        """Test loading a single template by name."""
        from utils.ontology_config import load_template, OntologyConfig

        # Create test templates directory
        templates_dir = tmp_path / "ontologies"
        templates_dir.mkdir()

        # Create test template file
        template_yaml = """
version: "1.0.0"
name: Test Template
description: Test template for loading
entity_types:
  - name: TestEntity
    description: Test entity
relationship_types: []
"""
        (templates_dir / "test-template.yaml").write_text(template_yaml)

        # Patch ONTOLOGY_TEMPLATES_DIR
        import utils.ontology_config
        original_dir = utils.ontology_config.ONTOLOGY_TEMPLATES_DIR
        utils.ontology_config.ONTOLOGY_TEMPLATES_DIR = templates_dir

        try:
            # Load without .yaml extension
            config = load_template("test-template")

            assert isinstance(config, OntologyConfig)
            assert config.name == "Test Template"
            assert len(config.entity_types) == 1
            assert config.entity_types[0].name == "TestEntity"
        finally:
            utils.ontology_config.ONTOLOGY_TEMPLATES_DIR = original_dir

    def test_load_template_not_found(self, tmp_path):
        """Test loading non-existent template raises FileNotFoundError."""
        from utils.ontology_config import load_template
        import utils.ontology_config

        original_dir = utils.ontology_config.ONTOLOGY_TEMPLATES_DIR
        utils.ontology_config.ONTOLOGY_TEMPLATES_DIR = tmp_path / "nonexistent"

        try:
            with pytest.raises(FileNotFoundError, match="Template.*not found"):
                load_template("nonexistent-template")
        finally:
            utils.ontology_config.ONTOLOGY_TEMPLATES_DIR = original_dir

    def test_load_template_invalid_yaml(self, tmp_path):
        """Test loading template with invalid YAML raises ValueError."""
        from utils.ontology_config import load_template
        import utils.ontology_config

        templates_dir = tmp_path / "ontologies"
        templates_dir.mkdir()

        # Create invalid YAML file
        (templates_dir / "invalid.yaml").write_text("version: '1.0.0\ninvalid: [unclosed")

        original_dir = utils.ontology_config.ONTOLOGY_TEMPLATES_DIR
        utils.ontology_config.ONTOLOGY_TEMPLATES_DIR = templates_dir

        try:
            with pytest.raises(ValueError, match="Invalid YAML"):
                load_template("invalid")
        finally:
            utils.ontology_config.ONTOLOGY_TEMPLATES_DIR = original_dir


class TestDependencyValidation:
    """Test suite for template dependency validation (T066)."""

    def test_validate_template_dependencies_no_deps(self):
        """Test validation of template with no dependencies."""
        from utils.ontology_config import OntologyConfig, validate_template_dependencies

        template = OntologyConfig(
            version="1.0.0",
            name="NoDeps",
            depends_on=None,
            entity_types=[],
            relationship_types=[]
        )

        errors = validate_template_dependencies(template, {})

        assert errors == []

    def test_validate_template_dependencies_satisfied(self):
        """Test validation when dependencies are satisfied."""
        from utils.ontology_config import OntologyConfig, validate_template_dependencies

        # Create dependency
        dependency = OntologyConfig(
            version="1.0.0",
            name="Base",
            entity_types=[],
            relationship_types=[]
        )

        # Create template that depends on it
        template = OntologyConfig(
            version="1.0.0",
            name="Extension",
            depends_on=["Base"],
            entity_types=[],
            relationship_types=[]
        )

        errors = validate_template_dependencies(template, {"Base": dependency})

        assert errors == []

    def test_validate_template_dependencies_missing(self):
        """Test validation when dependencies are missing."""
        from utils.ontology_config import OntologyConfig, validate_template_dependencies

        template = OntologyConfig(
            version="1.0.0",
            name="Extension",
            depends_on=["Base", "Missing"],
            entity_types=[],
            relationship_types=[]
        )

        errors = validate_template_dependencies(template, {})

        assert len(errors) == 2
        assert any("Base" in e for e in errors)
        assert any("Missing" in e for e in errors)

    def test_load_templates_with_dependencies(self, tmp_path):
        """Test loading multiple templates with dependency resolution."""
        from utils.ontology_config import load_templates_with_dependencies
        import utils.ontology_config

        templates_dir = tmp_path / "ontologies"
        templates_dir.mkdir()

        # Create base template
        base_yaml = """
version: "1.0.0"
name: Base
depends_on: []
entity_types:
  - name: BaseEntity
    description: Base entity
relationship_types: []
"""
        (templates_dir / "base.yaml").write_text(base_yaml)

        # Create extension template
        ext_yaml = """
version: "1.0.0"
name: Extension
depends_on:
  - base
entity_types:
  - name: ExtensionEntity
    description: Extension entity
relationship_types: []
"""
        (templates_dir / "extension.yaml").write_text(ext_yaml)

        original_dir = utils.ontology_config.ONTOLOGY_TEMPLATES_DIR
        utils.ontology_config.ONTOLOGY_TEMPLATES_DIR = templates_dir

        try:
            # Load extension should also load base dependency
            merged = load_templates_with_dependencies("extension")

            assert len(merged.entity_types) == 2
            entity_names = {et.name for et in merged.entity_types}
            assert entity_names == {"BaseEntity", "ExtensionEntity"}
        finally:
            utils.ontology_config.ONTOLOGY_TEMPLATES_DIR = original_dir

    def test_load_templates_circular_dependency(self, tmp_path):
        """Test detection of circular dependencies."""
        from utils.ontology_config import load_templates_with_dependencies
        import utils.ontology_config

        templates_dir = tmp_path / "ontologies"
        templates_dir.mkdir()

        # Create template A that depends on B
        a_yaml = """
version: "1.0.0"
name: TemplateA
depends_on:
  - template-b
entity_types: []
relationship_types: []
"""
        (templates_dir / "template-a.yaml").write_text(a_yaml)

        # Create template B that depends on A (circular!)
        b_yaml = """
version: "1.0.0"
name: TemplateB
depends_on:
  - template-a
entity_types: []
relationship_types: []
"""
        (templates_dir / "template-b.yaml").write_text(b_yaml)

        original_dir = utils.ontology_config.ONTOLOGY_TEMPLATES_DIR
        utils.ontology_config.ONTOLOGY_TEMPLATES_DIR = templates_dir

        try:
            with pytest.raises(ValueError, match="Circular dependency"):
                load_templates_with_dependencies("template-a")
        finally:
            utils.ontology_config.ONTOLOGY_TEMPLATES_DIR = original_dir


# Fixtures
@pytest.fixture
def sample_ontology_yaml():
    """Sample ontology YAML content for testing."""
    return """
    version: "1.0.0"
    name: CTI Base Ontology
    description: Core CTI entity and relationship types

    entity_types:
      - name: ThreatActor
        description: Actor responsible for cyber threats
        attributes:
          - name: aliases
            type: list
            required: false
            description: Alternative names
          - name: sophistication
            type: string
            required: false
            description: Skill level
        decay_config:
          half_life_days: 180
          importance_floor: 0.5

      - name: Malware
        description: Malicious software
        attributes:
          - name: family
            type: string
            required: false
          - name: first_seen
            type: datetime
            required: false
        decay_config:
          half_life_days: 90

    relationship_types:
      - name: uses
        description: Threat actor uses malware
        source_entity_types:
          - ThreatActor
        target_entity_types:
          - Malware
        bidirectional: false
        attributes:
          - name: confidence
            type: number
            required: false
            description: Confidence level 0-1
    """
