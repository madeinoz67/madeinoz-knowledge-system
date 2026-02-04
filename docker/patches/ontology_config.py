"""
Ontology Configuration Module

Feature: 018-osint-ontology
Phase 2: Foundational (T005-T011)

This module provides:
- Pydantic models for ontology configuration (EntityTypeConfig, RelationshipTypeConfig)
- YAML loader with caching and error handling
- Configuration validation (circular dependencies, reserved attributes)
- Hot-reload support with version comparison and breaking change detection
- Per-type decay configuration retrieval
- Template merging functionality

Configuration File: config/ontology-types.yaml
Environment Variable: ONTOLOGY_CONFIG_PATH
"""

import logging
import os
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Dict, List, Set, Tuple, Union

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


logger = logging.getLogger(__name__)

# ==============================================================================
# Constants
# ==============================================================================

# Default configuration file location
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "ontology-types.yaml"

# Environment variable for custom config path
CONFIG_PATH_ENV = "ONTOLOGY_CONFIG_PATH"

# Templates directory
ONTOLOGY_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "config" / "ontologies"

# Reserved attribute names that cannot be used in custom entity/relationship types
# These are used internally by Graphiti and must not be overridden
RESERVED_ATTRIBUTES = [
    "uuid",           # Unique identifier for nodes
    "name",           # Node name
    "labels",         # Node labels in Neo4j
    "created_at",     # Creation timestamp
    "summary",        # Entity summary text
    "attributes",     # Attributes dictionary
    "name_embedding", # Vector embedding of name
]

# Default decay configuration for CTI entities
DEFAULT_CT_HALF_LIFE_DAYS = 180

# ==============================================================================
# Pydantic Models
# ==============================================================================


class AttributeDefinition(BaseModel):
    """
    Definition of an attribute for an entity or relationship type.

    Attributes define the schema for custom fields that can be stored
    in entity/relationship attributes.
    """

    name: str = Field(description="Attribute name (must not be reserved)")
    type: str = Field(description="Attribute type: string, number, boolean, datetime, list")
    required: bool = Field(default=False, description="Whether attribute is required")
    description: Optional[str] = Field(default=None, description="Human-readable description")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate that attribute type is one of the allowed types."""
        valid_types = {"string", "number", "boolean", "datetime", "list"}
        v_lower = v.lower()
        if v_lower not in valid_types:
            raise ValueError(f"Invalid attribute type '{v}'. Must be one of: {', '.join(sorted(valid_types))}")
        return v_lower

    @field_validator("name")
    @classmethod
    def validate_not_reserved(cls, v: str) -> str:
        """Validate that attribute name is not reserved."""
        if v in RESERVED_ATTRIBUTES:
            raise ValueError(
                f"Attribute name '{v}' is reserved and cannot be used. "
                f"Reserved attributes: {', '.join(sorted(RESERVED_ATTRIBUTES))}"
            )
        return v


class OntologyDecayConfig(BaseModel):
    """
    Decay configuration for an entity type.

    Defines how quickly entities of this type should decay.
    """

    half_life_days: float = Field(
        default=DEFAULT_CT_HALF_LIFE_DAYS,
        ge=1.0,
        description="Half-life in days for decay calculation"
    )
    importance_floor: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=5.0,
        description="Minimum importance score (1-5), entities above this decay slower"
    )
    stability_multiplier: Optional[float] = Field(
        default=None,
        ge=0.1,
        le=3.0,
        description="Multiplier for stability score during decay calculation"
    )


class EntityTypeConfig(BaseModel):
    """
    Configuration for a custom entity type.

    Entity types define domain-specific entities (ThreatActor, Malware, etc.)
    that can be automatically extracted from content.
    """

    name: str = Field(description="Entity type name (e.g., ThreatActor, Malware)")
    description: str = Field(description="Human-readable description")
    parent_type: Optional[str] = Field(
        default=None,
        description="Parent entity type for inheritance (optional)"
    )
    icon: Optional[str] = Field(
        default=None,
        description="Icon identifier for UI display (optional)"
    )
    permanent: bool = Field(
        default=False,
        description="If true, entities of this type are exempt from decay"
    )
    decay_config: Optional[OntologyDecayConfig] = Field(
        default=None,
        description="Custom decay configuration (optional)"
    )
    attributes: List[AttributeDefinition] = Field(
        default_factory=list,
        description="Custom attributes for this entity type"
    )

    @model_validator(mode="after")
    def validate_attributes_not_reserved(self) -> "EntityTypeConfig":
        """Validate that no attributes use reserved names."""
        for attr in self.attributes:
            if attr.name in RESERVED_ATTRIBUTES:
                raise ValueError(
                    f"Entity type '{self.name}' has reserved attribute '{attr.name}'. "
                    f"Reserved attributes: {', '.join(sorted(RESERVED_ATTRIBUTES))}"
                )
        return self


class RelationshipTypeConfig(BaseModel):
    """
    Configuration for a custom relationship type.

    Relationship types define domain-specific connections between entities
    (uses, targets, exploits, etc.) that can be extracted from content.
    """

    name: str = Field(description="Relationship type name (e.g., uses, targets)")
    description: str = Field(description="Human-readable description")
    source_entity_types: List[str] = Field(
        description="Valid source entity types for this relationship"
    )
    target_entity_types: List[str] = Field(
        description="Valid target entity types for this relationship"
    )
    bidirectional: bool = Field(
        default=False,
        description="Whether relationship works in both directions"
    )
    inverse_name: Optional[str] = Field(
        default=None,
        description="Name of inverse relationship (e.g., 'targets' -> 'targeted_by')"
    )
    attributes: List[AttributeDefinition] = Field(
        default_factory=list,
        description="Custom attributes for this relationship type"
    )

    @model_validator(mode="after")
    def validate_attributes_not_reserved(self) -> "RelationshipTypeConfig":
        """Validate that no attributes use reserved names."""
        for attr in self.attributes:
            if attr.name in RESERVED_ATTRIBUTES:
                raise ValueError(
                    f"Relationship type '{self.name}' has reserved attribute '{attr.name}'. "
                    f"Reserved attributes: {', '.join(sorted(RESERVED_ATTRIBUTES))}"
                )
        return self


class OntologyConfig(BaseModel):
    """
    Complete ontology configuration loaded from YAML.

    Represents the full set of custom entity and relationship types
    defined in the configuration file.
    """

    version: str = Field(default="1.0.0", description="Configuration version")
    name: Optional[str] = Field(default=None, description="Ontology name")
    description: Optional[str] = Field(default=None, description="Ontology description")
    depends_on: Optional[List[str]] = Field(
        default=None,
        description="Names of ontologies this one depends on (for templates)"
    )
    entity_types: List[EntityTypeConfig] = Field(
        default_factory=list,
        description="Custom entity type definitions"
    )
    relationship_types: List[RelationshipTypeConfig] = Field(
        default_factory=list,
        description="Custom relationship type definitions"
    )

    @model_validator(mode="after")
    def validate_relationship_types_exist(self) -> "OntologyConfig":
        """Validate that referenced entity types in relationships are defined.

        Allows references to both custom entity types defined in this config
        and Graphiti's built-in entity types (Person, Organization, Location, etc.).
        """
        # Built-in Graphiti entity types that are always available
        builtin_entity_types = {
            "Person", "Organization", "Location", "Event", "Object",
            "Document", "Topic", "Preference", "Requirement", "Procedure"
        }

        # Custom entity types from this config
        custom_entity_types = {et.name for et in self.entity_types}

        # All available entity types
        entity_type_names = builtin_entity_types | custom_entity_types

        errors = []

        for rel in self.relationship_types:
            for source_type in rel.source_entity_types:
                if source_type not in entity_type_names:
                    errors.append(
                        f"Relationship '{rel.name}' references undefined source entity type '{source_type}'"
                    )
            for target_type in rel.target_entity_types:
                if target_type not in entity_type_names:
                    errors.append(
                        f"Relationship '{rel.name}' references undefined target entity type '{target_type}'"
                    )

        if errors:
            raise ValueError("Relationship validation failed:\n" + "\n".join(errors))

        return self


# ==============================================================================
# Global State
# ==============================================================================

# Cached configuration
_config_cache: Optional[OntologyConfig] = None

# Previous configuration for breaking change detection
_previous_config: Optional[OntologyConfig] = None


# ==============================================================================
# Configuration Loading
# ==============================================================================


def _resolve_config_path(config_path: Optional[Path] = None) -> Path:
    """
    Resolve the configuration file path.

    Resolution order:
    1. Provided config_path parameter
    2. ONTOLOGY_CONFIG_PATH environment variable
    3. Default path: config/ontology-types.yaml

    Args:
        config_path: Optional explicit path to config file

    Returns:
        Resolved absolute path to config file
    """
    if config_path is not None:
        return config_path.resolve()

    # Check environment variable
    env_path = os.environ.get(CONFIG_PATH_ENV)
    if env_path:
        return Path(env_path).resolve()

    # Use default
    return DEFAULT_CONFIG_PATH.resolve()


def load_ontology_config(
    config_path: Optional[Path] = None,
    force_reload: bool = False
) -> OntologyConfig:
    """
    Load ontology configuration from YAML file.

    Configuration is cached after first load. Use force_reload=True to reload.

    Args:
        config_path: Optional path to config file. If not provided:
                     1. Checks ONTOLOGY_CONFIG_PATH environment variable
                     2. Falls back to config/ontology-types.yaml
        force_reload: Force reload from file even if cached

    Returns:
        OntologyConfig instance with loaded or default values

    Raises:
        ValueError: If config file exists but contains invalid YAML or fails validation
    """
    global _config_cache

    # Return cached config if available
    if _config_cache is not None and not force_reload:
        return _config_cache

    # Determine config path
    resolved_path = _resolve_config_path(config_path)

    # Load from file if exists
    if resolved_path.exists():
        try:
            with open(resolved_path, "r") as f:
                raw_config = yaml.safe_load(f)

            if raw_config is None:
                logger.warning(f"Empty config file at {resolved_path}, using defaults")
                _config_cache = OntologyConfig()
            else:
                # Handle list format for entity/relationship types
                if "entity_types" not in raw_config:
                    raw_config["entity_types"] = []
                if "relationship_types" not in raw_config:
                    raw_config["relationship_types"] = []

                _config_cache = OntologyConfig.model_validate(raw_config)
                logger.info(f"Loaded ontology config v{_config_cache.version} from {resolved_path}")

                # Validate for circular dependencies
                has_cycle, cycle_path = check_circular_dependencies(_config_cache)
                if has_cycle:
                    raise ValueError(
                        f"Circular dependency detected in ontology configuration: {' -> '.join(cycle_path)}"
                    )

        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in {resolved_path}: {e}")
            raise ValueError(f"Invalid YAML configuration: {e}") from e
        except ValueError as e:
            # Re-raise validation errors
            logger.error(f"Validation error in {resolved_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading config from {resolved_path}: {e}")
            raise ValueError(f"Error loading configuration: {e}") from e
    else:
        logger.info(f"Config file not found at {resolved_path}, using defaults")
        _config_cache = OntologyConfig()

    return _config_cache


def reset_ontology_cache() -> None:
    """Reset the configuration cache (for testing)."""
    global _config_cache, _previous_config
    _config_cache = None
    _previous_config = None


# ==============================================================================
# Configuration Validation
# ==============================================================================


def check_circular_dependencies(
    config: Optional[Union[OntologyConfig, Dict[str, List[str]]]] = None
) -> Tuple[bool, Optional[List[str]]]:
    """
    Check for circular dependencies in entity type inheritance.

    Uses topological sort to detect cycles in the parent_type dependency graph.

    Args:
        config: Ontology config to check, or a pre-built dependency graph.
                If OntologyConfig, extracts parent_type relationships.
                If Dict[str, List[str]], treats as direct dependency graph {parent: [children]}.
                If None, loads from default path.

    Returns:
        Tuple of (has_cycle, cycle_path). If no cycle, cycle_path is None.
        If cycle detected, cycle_path is a list of type names forming the cycle.
    """
    # Build dependency graph: parent -> children
    graph: Dict[str, List[str]] = {}
    all_types: Set[str] = set()

    # Handle different input types
    if config is None:
        config = load_ontology_config()

    if isinstance(config, dict):
        # Input is already a dependency graph
        graph = config.copy()
        all_types = set(graph.keys())
        for children in graph.values():
            all_types.update(children)
    else:
        # Input is OntologyConfig, extract parent_type relationships
        for entity_type in config.entity_types:
            all_types.add(entity_type.name)
            if entity_type.parent_type:
                graph[entity_type.parent_type] = graph.get(entity_type.parent_type, [])
                graph[entity_type.parent_type].append(entity_type.name)

    # Add types with no dependencies as empty lists
    for entity_type in all_types:
        if entity_type not in graph:
            graph[entity_type] = []

    # Use Kahn's algorithm with cycle detection
    in_degree: Dict[str, int] = {node: 0 for node in all_types}

    # Calculate in-degrees
    for parent in graph:
        for child in graph[parent]:
            if child in in_degree:
                in_degree[child] += 1

    # Find nodes with no incoming edges
    queue = deque([node for node in in_degree if in_degree[node] == 0])
    visited = []

    while queue:
        node = queue.popleft()
        visited.append(node)

        for neighbor in graph.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # If we didn't visit all nodes, there's a cycle
    if len(visited) != len(all_types):
        # Find the cycle
        unvisited = set(all_types) - set(visited)

        # Trace the cycle from an unvisited node
        start = next(iter(unvisited))
        cycle_path = [start]
        current = start

        # Build the cycle path
        max_iterations = len(all_types) + 1
        for _ in range(max_iterations):
            # For dict input, trace directly through graph
            if isinstance(config, dict):
                # Find a child that points to current as parent
                found = False
                for parent, children in graph.items():
                    if current in children:
                        current = parent
                        if current != start:  # Don't add start twice
                            cycle_path.append(current)
                        found = True
                        break
                if not found:
                    break
            else:
                # For OntologyConfig input, use entity_types
                found = False
                for entity_type in config.entity_types:
                    if entity_type.name == current and entity_type.parent_type:
                        current = entity_type.parent_type
                        if current != start:  # Don't add start twice
                            cycle_path.append(current)
                        found = True
                        break
                if not found:
                    break
            if current == start:
                break

        return True, cycle_path

    return False, None


def validate_ontology_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Validate ontology configuration without loading it.

    Performs comprehensive validation including:
    - YAML syntax
    - Schema validation (Pydantic)
    - Circular dependency detection
    - Reserved attribute check
    - Relationship type references

    Args:
        config_path: Path to config file. If None, uses default resolution.

    Returns:
        Dictionary with validation results:
        {
            "valid": bool,
            "errors": List[Dict[str, str]],
            "warnings": List[Dict[str, str]],
            "breaking_changes": Optional[List[Dict[str, str]]]
        }
    """
    result = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "breaking_changes": None
    }

    resolved_path = _resolve_config_path(config_path)

    # Check file exists
    if not resolved_path.exists():
        result["valid"] = False
        result["errors"].append({
            "path": str(resolved_path),
            "message": f"Configuration file not found: {resolved_path}",
            "line": None
        })
        return result

    # Load and parse YAML
    try:
        with open(resolved_path, "r") as f:
            raw_config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        result["valid"] = False
        result["errors"].append({
            "path": str(resolved_path),
            "message": f"Invalid YAML syntax: {e}",
            "line": getattr(e, 'problem_mark', {}).line if hasattr(e, 'problem_mark') else None
        })
        return result

    # Validate with Pydantic
    try:
        config = OntologyConfig.model_validate(raw_config)
    except ValidationError as e:
        result["valid"] = False
        for error in e.errors():
            loc = " -> ".join(str(part) for part in error["loc"])
            result["errors"].append({
                "path": loc,
                "message": error["msg"],
                "line": None
            })
        return result

    # Check for circular dependencies
    has_cycle, cycle_path = check_circular_dependencies(config)
    if has_cycle:
        result["valid"] = False
        result["errors"].append({
            "path": "entity_types",
            "message": f"Circular dependency detected: {' -> '.join(cycle_path)}",
            "line": None
        })

    # Check for missing decay configs (warning only)
    for entity_type in config.entity_types:
        if entity_type.decay_config is None:
            result["warnings"].append({
                "path": f"entity_types.{entity_type.name}.decay_config",
                "message": f"No decay_config specified, using default {DEFAULT_CT_HALF_LIFE_DAYS}-day half-life",
                "line": None
            })

    # Check for breaking changes if we have previous config
    if _previous_config is not None:
        breaking_changes = detect_breaking_changes(_previous_config, config)
        if breaking_changes:
            result["breaking_changes"] = breaking_changes

    return result


# ==============================================================================
# Hot Reload Support
# ==============================================================================


def detect_breaking_changes(
    old_config: OntologyConfig,
    new_config: OntologyConfig
) -> List[Dict[str, str]]:
    """
    Detect breaking changes between two ontology configurations.

    Breaking changes include:
    - Entity type removed
    - Entity type attribute removed
    - Relationship type removed
    - Relationship type attribute removed
    - Changed attribute type

    Args:
        old_config: Previous ontology configuration
        new_config: New ontology configuration

    Returns:
        List of breaking change dictionaries with type, description, and impact
    """
    breaking_changes = []

    # Map old entity types by name
    old_entity_types = {et.name: et for et in old_config.entity_types}
    new_entity_types = {et.name: et for et in new_config.entity_types}

    # Check for removed entity types
    for name in old_entity_types:
        if name not in new_entity_types:
            breaking_changes.append({
                "type": "entity_type_removed",
                "description": f"Entity type '{name}' removed",
                "impact": f"Existing '{name}' entities will remain but type will be read-only"
            })

    # Check for removed/changed attributes in existing entity types
    for name in set(old_entity_types) & set(new_entity_types):
        old_attrs = {attr.name: attr for attr in old_entity_types[name].attributes}
        new_attrs = {attr.name: attr for attr in new_entity_types[name].attributes}

        for attr_name, old_attr in old_attrs.items():
            if attr_name not in new_attrs:
                breaking_changes.append({
                    "type": "attribute_removed",
                    "description": f"Attribute '{attr_name}' removed from entity type '{name}'",
                    "impact": f"Existing entities with this attribute will retain data but attribute will be read-only"
                })
            elif old_attr.type != new_attrs[attr_name].type:
                breaking_changes.append({
                    "type": "attribute_type_changed",
                    "description": f"Attribute '{attr_name}' type changed from {old_attr.type} to {new_attrs[attr_name].type} in entity type '{name}'",
                    "impact": "Data type conversion may be required"
                })

    # Map old relationship types by name
    old_rel_types = {rt.name: rt for rt in old_config.relationship_types}
    new_rel_types = {rt.name: rt for rt in new_config.relationship_types}

    # Check for removed relationship types
    for name in old_rel_types:
        if name not in new_rel_types:
            breaking_changes.append({
                "type": "relationship_type_removed",
                "description": f"Relationship type '{name}' removed",
                "impact": f"Existing '{name}' relationships will remain but type will be read-only"
            })

    return breaking_changes


def reload_ontology_config(
    config_path: Optional[Path] = None,
    force: bool = False
) -> Dict[str, Any]:
    """
    Reload ontology configuration from YAML file with change detection.

    Args:
        config_path: Optional path to config file
        force: Force reload even if version unchanged

    Returns:
        Dictionary with reload results:
        {
            "reloaded": bool,
            "previous_version": str,
            "new_version": str,
            "entity_types_loaded": int,
            "relationship_types_loaded": int,
            "breaking_changes": List[Dict[str, str]]
        }
    """
    global _previous_config, _config_cache

    # Store current config as previous
    _previous_config = _config_cache

    # Load new config
    new_config = load_ontology_config(config_path, force_reload=True)

    # Check version
    previous_version = _previous_config.version if _previous_config else "none"
    new_version = new_config.version

    # If version unchanged and not forced, skip reload
    if not force and previous_version == new_version and _previous_config:
        return {
            "reloaded": False,
            "previous_version": previous_version,
            "new_version": new_version,
            "entity_types_loaded": 0,
            "relationship_types_loaded": 0,
            "breaking_changes": []
        }

    # Detect breaking changes
    breaking_changes = []
    if _previous_config:
        breaking_changes = detect_breaking_changes(_previous_config, new_config)

    return {
        "reloaded": True,
        "previous_version": previous_version,
        "new_version": new_version,
        "entity_types_loaded": len(new_config.entity_types),
        "relationship_types_loaded": len(new_config.relationship_types),
        "breaking_changes": breaking_changes
    }


# ==============================================================================
# Decay Configuration
# ==============================================================================


def get_decay_config_for_type(entity_type_name: str) -> OntologyDecayConfig:
    """
    Get decay configuration for a specific entity type.

    Args:
        entity_type_name: Name of the entity type

    Returns:
        OntologyDecayConfig for the type, or default if type not found or has no config
    """
    config = _config_cache
    if config is None:
        config = load_ontology_config()

    # Find entity type
    for entity_type in config.entity_types:
        if entity_type.name == entity_type_name:
            if entity_type.decay_config:
                return entity_type.decay_config
            else:
                # Return default for entities without explicit config
                return OntologyDecayConfig()

    # Type not found, return default
    return OntologyDecayConfig()


def is_entity_type_permanent(entity_type_name: str) -> bool:
    """
    Check if an entity type is marked as permanent (exempt from decay).

    Args:
        entity_type_name: Name of the entity type

    Returns:
        True if entity type is permanent, False otherwise
    """
    config = _config_cache
    if config is None:
        config = load_ontology_config()

    for entity_type in config.entity_types:
        if entity_type.name == entity_type_name:
            return entity_type.permanent

    return False


# ==============================================================================
# Template Merging
# ==============================================================================


def merge_ontologies(ontologies: List[OntologyConfig]) -> OntologyConfig:
    """
    Merge multiple ontology configurations into one.

    Later ontologies override earlier ones for duplicate entity/relationship types.
    This is used to combine base templates with extensions.

    Args:
        ontologies: List of ontology configurations to merge

    Returns:
        Merged OntologyConfig
    """
    if not ontologies:
        return OntologyConfig()

    if len(ontologies) == 1:
        return ontologies[0]

    # Use the first ontology as base
    base = ontologies[0]

    # Collect entity types (later ones override)
    entity_types_by_name: Dict[str, EntityTypeConfig] = {}
    for ontology in ontologies:
        for et in ontology.entity_types:
            entity_types_by_name[et.name] = et

    # Collect relationship types (later ones override)
    relationship_types_by_name: Dict[str, RelationshipTypeConfig] = {}
    for ontology in ontologies:
        for rt in ontology.relationship_types:
            relationship_types_by_name[rt.name] = rt

    # Merge metadata from first ontology
    return OntologyConfig(
        version=base.version,
        name=base.name,
        description=base.description,
        depends_on=base.depends_on,
        entity_types=list(entity_types_by_name.values()),
        relationship_types=list(relationship_types_by_name.values())
    )


# ==============================================================================
# Template Loading (for Pre-built Ontology Templates)
# ==============================================================================


def list_available_templates() -> List[Path]:
    """
    List all available ontology templates in the templates directory.

    Returns:
        List of template file paths
    """
    if not ONTOLOGY_TEMPLATES_DIR.exists():
        return []

    return sorted(ONTOLOGY_TEMPLATES_DIR.glob("*.yaml"))


def load_template(template_name: str) -> OntologyConfig:
    """
    Load a single ontology template by name.

    Args:
        template_name: Name of template file (with or without .yaml extension)

    Returns:
        OntologyConfig for the template

    Raises:
        FileNotFoundError: If template file not found
        ValueError: If template YAML is invalid
    """
    # Ensure .yaml extension
    if not template_name.endswith(".yaml"):
        template_name = f"{template_name}.yaml"

    template_path = ONTOLOGY_TEMPLATES_DIR / template_name

    if not template_path.exists():
        available = [t.name for t in list_available_templates()]
        raise FileNotFoundError(
            f"Template '{template_name}' not found in {ONTOLOGY_TEMPLATES_DIR}. "
            f"Available templates: {', '.join(available) if available else 'none'}"
        )

    # Load the template
    try:
        with open(template_path, "r") as f:
            raw_config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in template '{template_name}': {e}")

    # Validate with Pydantic
    try:
        config = OntologyConfig.model_validate(raw_config)
    except Exception as e:
        raise ValueError(f"Invalid ontology schema in template '{template_name}': {e}")

    logger.info(f"Loaded ontology template: {template_name} (version {config.version})")
    return config


def validate_template_dependencies(template: OntologyConfig, loaded: Dict[str, OntologyConfig]) -> List[str]:
    """
    Validate that template dependencies are satisfied and detect circular dependencies.

    Args:
        template: Template to validate
        loaded: Dictionary of already loaded templates by name

    Returns:
        List of error messages (empty if valid)

    Raises:
        ValueError: If circular dependency detected
    """
    errors = []

    if not template.depends_on:
        return errors

    # Check for missing dependencies
    for dep in template.depends_on:
        if dep not in loaded:
            # Check if the template file exists
            dep_path = ONTOLOGY_TEMPLATES_DIR / f"{dep}.yaml"
            if not dep_path.exists():
                errors.append(f"Missing dependency: '{dep}' (template file not found)")
            else:
                errors.append(f"Missing dependency: '{dep}' (must be loaded first)")

    return errors


def load_templates_with_dependencies(*template_names: str) -> OntologyConfig:
    """
    Load multiple templates with dependency resolution and merging.

    Templates are loaded in dependency order (dependencies first).
    Circular dependencies are detected and reported.

    Args:
        *template_names: Names of templates to load (e.g., "cti-base", "osint-base")

    Returns:
        Merged OntologyConfig

    Raises:
        FileNotFoundError: If a template is not found
        ValueError: If circular dependency detected or validation fails
    """
    if not template_names:
        raise ValueError("At least one template name must be provided")

    # Normalize names
    normalized_names = []
    for name in template_names:
        if not name.endswith(".yaml"):
            name = f"{name}.yaml"
        normalized_names.append(name.replace(".yaml", ""))

    # Load all requested templates and their dependencies
    loaded: Dict[str, OntologyConfig] = {}
    load_order: List[str] = []
    loading: Set[str] = set()

    def load_with_deps(template_name: str, depth: int = 0) -> None:
        """Recursively load template and its dependencies."""
        # Prevent infinite recursion
        if depth > 10:
            raise ValueError(f"Dependency depth exceeded 10 for '{template_name}' - possible circular dependency")

        # Already loaded
        if template_name in loaded:
            return

        # Detect circular dependency
        if template_name in loading:
            cycle = " -> ".join(list(loading) + [template_name])
            raise ValueError(f"Circular dependency detected: {cycle}")

        # Mark as loading
        loading.add(template_name)

        # Load the template
        template = load_template(template_name)

        # Load dependencies first
        if template.depends_on:
            for dep in template.depends_on:
                dep_name = dep.replace(".yaml", "")
                load_with_deps(dep_name, depth + 1)

        # Store the template
        loaded[template_name] = template
        load_order.append(template_name)
        loading.remove(template_name)

    # Load all templates
    for name in normalized_names:
        load_with_deps(name)

    # Merge in dependency order
    merged = merge_ontologies([loaded[name] for name in load_order])

    logger.info(f"Loaded {len(load_order)} templates in order: {' -> '.join(load_order)}")
    return merged


# ==============================================================================
# Entity Type Registration (for Graphiti Integration)
# ==============================================================================


def get_entity_types_dict() -> Dict[str, Any]:
    """
    Get entity types as a dictionary for Graphiti registration.

    Returns a dictionary mapping entity type names to dynamically created
    Pydantic BaseModel classes for use with Graphiti's custom entity types.

    Returns:
        Dictionary of {type_name: BaseModel class}
    """
    config = _config_cache
    if config is None:
        config = load_ontology_config()

    from pydantic import BaseModel as PydanticBaseModel

    entity_types = {}

    for entity_type in config.entity_types:
        # Create a dynamic Pydantic model for this entity type
        # This matches the pattern used in GraphitiMcpServer.__init__
        entity_model = type(
            entity_type.name,
            (PydanticBaseModel,),
            {
                "__doc__": entity_type.description,
            }
        )
        entity_types[entity_type.name] = entity_model

    return entity_types


def list_ontology_types(include_builtin: bool = False) -> Dict[str, List[Dict[str, Any]]]:
    """
    List all available ontology types.

    Args:
        include_builtin: Include Graphiti built-in types (Person, Organization, etc.)

    Returns:
        Dictionary with "entity_types" and "relationship_types" keys
    """
    config = _config_cache
    if config is None:
        config = load_ontology_config()

    result = {
        "entity_types": [],
        "relationship_types": []
    }

    for et in config.entity_types:
        entity_dict = {
            "name": et.name,
            "description": et.description,
            "parent_type": et.parent_type,
            "icon": et.icon,
            "permanent": et.permanent,
            "decay_config": et.decay_config.model_dump() if et.decay_config else None,
            "attributes": [
                {
                    "name": attr.name,
                    "type": attr.type,
                    "required": attr.required,
                    "description": attr.description
                }
                for attr in et.attributes
            ]
        }
        result["entity_types"].append(entity_dict)

    for rt in config.relationship_types:
        rel_dict = {
            "name": rt.name,
            "description": rt.description,
            "source_entity_types": rt.source_entity_types,
            "target_entity_types": rt.target_entity_types,
            "bidirectional": rt.bidirectional,
            "inverse_name": rt.inverse_name,
            "attributes": [
                {
                    "name": attr.name,
                    "type": attr.type,
                    "required": attr.required,
                    "description": attr.description
                }
                for attr in rt.attributes
            ]
        }
        result["relationship_types"].append(rel_dict)

    # Optionally add built-in types
    if include_builtin:
        builtin_entities = [
            {"name": "Person", "description": "A human being"},
            {"name": "Organization", "description": "A structured group of people"},
            {"name": "Location", "description": "A geographic place"},
            {"name": "Event", "description": "Something that happens at a specific time"},
            {"name": "Concept", "description": "An abstract idea or category"},
        ]
        result["entity_types"].extend(builtin_entities)

    return result


# ==============================================================================
# Relationship Type Registration (for Graphiti Integration)
# ==============================================================================


def get_relationship_types_dict() -> Dict[str, RelationshipTypeConfig]:
    """
    Get relationship types as a dictionary for Graphiti registration.

    Feature 018 T041: Returns configured relationship types for use in
    relationship extraction and filtering.

    Returns:
        Dictionary of {relationship_type_name: RelationshipTypeConfig}
    """
    config = _config_cache
    if config is None:
        config = load_ontology_config()

    relationship_types = {}

    for rel_type in config.relationship_types:
        relationship_types[rel_type.name] = rel_type

    return relationship_types


def get_relationship_type(name: str) -> Optional[RelationshipTypeConfig]:
    """
    Get a specific relationship type by name.

    Feature 018 T041: Lookup relationship type configuration for validation.

    Args:
        name: Relationship type name (e.g., "uses", "targets")

    Returns:
        RelationshipTypeConfig if found, None otherwise
    """
    relationship_types = get_relationship_types_dict()
    return relationship_types.get(name)


def validate_relationship_types(
    source_type: str,
    target_type: str,
    relationship_name: str
) -> Tuple[bool, Optional[str]]:
    """
    Validate that a relationship is allowed between entity types.

    Feature 018 T043: Validates source_entity_types and target_entity_types
    are defined for the relationship.

    Args:
        source_type: Source entity type name
        target_type: Target entity type name
        relationship_name: Relationship type name

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is None.
    """
    rel_type = get_relationship_type(relationship_name)

    if rel_type is None:
        return False, f"Relationship type '{relationship_name}' is not defined"

    if source_type not in rel_type.source_entity_types:
        return False, (
            f"Source entity type '{source_type}' is not valid for "
            f"relationship '{relationship_name}'. Valid source types: "
            f"{', '.join(rel_type.source_entity_types)}"
        )

    if target_type not in rel_type.target_entity_types:
        return False, (
            f"Target entity type '{target_type}' is not valid for "
            f"relationship '{relationship_name}'. Valid target types: "
            f"{', '.join(rel_type.target_entity_types)}"
        )

    return True, None


# ==============================================================================
# Convenience Functions
# ==============================================================================


def get_ontology_config() -> OntologyConfig:
    """
    Get the current ontology configuration (cached).

    Convenience function that loads config on first call and returns cached version.

    Returns:
        OntologyConfig instance
    """
    return load_ontology_config()
