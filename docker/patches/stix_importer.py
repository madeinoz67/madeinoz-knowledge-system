"""
STIX 2.1 Importer Module

Feature: 018-osint-ontology
User Story: 3 - Import STIX 2.1 Data
Implementation: T053-T057, T063, T064

This module provides:
- STIX 2.1 bundle parsing using stix2 library
- STIX type to ontology type mapping
- Entity extraction from STIX objects with property mapping
- Relationship extraction from STIX relationships
- Import session tracking for progress and failure handling
- Bi-temporal metadata preservation (valid_from, valid_until)
- External references mapping (MITRE IDs, CVE IDs, etc.)

Dependencies:
- stix2 (Python STIX 2.1 library) - already in Dockerfile
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from pathlib import Path
import time
import hashlib
import random
import string

try:
    import stix2
    import aiohttp
except ImportError:
    stix2 = None
    aiohttp = None


logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================

class InvalidSTIXError(Exception):
    """Raised when STIX 2.1 data is invalid or cannot be parsed."""
    pass


class OntologyNotLoadedError(Exception):
    """Raised when ontology types are not loaded but required."""
    pass


# =============================================================================
# Constants
# =============================================================================

# STIX 2.1 specification version we support
SUPPORTED_STIX_VERSION = "2.1"

# Default batch size for processing large STIX bundles
DEFAULT_BATCH_SIZE = 1000

# STIX type to ontology type mapping
STIX_TYPE_MAPPING: Dict[str, str] = {
    "threat-actor": "ThreatActor",
    "malware": "Malware",
    "vulnerability": "Vulnerability",
    "indicator": "Indicator",
    "attack-pattern": "TTP",
    "campaign": "Campaign",
    "infrastructure": "Infrastructure",
}

# STIX relationship type to ontology relationship type mapping
STIX_RELATIONSHIP_MAPPING: Dict[str, str] = {
    "uses": "uses",
    "targets": "targets",
    "attributed-to": "attributed_to",
    "exploits": "exploits",
    "related-to": "related_to",
    "variant-of": "variant_of",
    "associated-with": "associated_with",
    "located-at": "located_at",
    "communicates-with": "communicates_with",
}

# MITRE ATT&CK external reference sources
MITRE_SOURCES = {"mitre-attack", "attack.mitre.org", "mitre"}

# CVE external reference source
CVE_SOURCES = {"cve", "nvd", "nist"}


# =============================================================================
# Import ID Generation
# =============================================================================

def generate_import_id() -> str:
    """
    Generate a unique import session ID.

    Returns:
        Unique import ID starting with 'import_' followed by timestamp and random suffix
    """
    timestamp = int(time.time() * 1000)
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"import_{timestamp}_{random_suffix}"


# =============================================================================
# T053: STIX Bundle Parsing
# =============================================================================

def parse_stix_bundle(stix_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse and validate STIX 2.1 bundle.

    Args:
        stix_data: Dictionary containing STIX bundle data

    Returns:
        Parsed bundle dictionary with:
        - bundle_id: STIX bundle ID
        - spec_version: STIX specification version
        - objects: List of STIX objects

    Raises:
        InvalidSTIXError: If bundle is invalid or not STIX 2.1
    """
    # Validate bundle structure
    if not isinstance(stix_data, dict):
        raise InvalidSTIXError("STIX bundle must be a dictionary")

    if "type" not in stix_data:
        raise InvalidSTIXError("STIX bundle missing 'type' field")

    if stix_data["type"] != "bundle":
        raise InvalidSTIXError(f"Expected type 'bundle', got '{stix_data['type']}'")

    # Check spec version
    spec_version = stix_data.get("spec_version", "2.1")
    if spec_version != SUPPORTED_STIX_VERSION:
        raise InvalidSTIXError(
            f"Unsupported STIX version: {spec_version}. "
            f"Only version {SUPPORTED_STIX_VERSION} is supported."
        )

    # Extract objects
    objects = stix_data.get("objects", [])
    if not isinstance(objects, list):
        raise InvalidSTIXError("STIX bundle 'objects' field must be a list")

    return {
        "bundle_id": stix_data.get("id", ""),
        "spec_version": spec_version,
        "objects": objects,
    }


def load_and_parse_stix_file(file_path: str) -> Dict[str, Any]:
    """
    Load and parse STIX bundle from file.

    Args:
        file_path: Path to STIX JSON file

    Returns:
        Parsed bundle dictionary

    Raises:
        InvalidSTIXError: If file cannot be read or parsed
    """
    import json

    path = Path(file_path)
    if not path.exists():
        raise InvalidSTIXError(f"STIX file not found: {file_path}")

    try:
        with open(path, 'r') as f:
            stix_data = json.load(f)
    except json.JSONDecodeError as e:
        raise InvalidSTIXError(f"Invalid JSON in STIX file: {e}")
    except Exception as e:
        raise InvalidSTIXError(f"Error reading STIX file: {e}")

    return parse_stix_bundle(stix_data)


async def load_stix_from_url(url: str) -> Dict[str, Any]:
    """
    Load and parse STIX bundle from URL.

    Args:
        url: URL to STIX JSON file

    Returns:
        Parsed bundle dictionary

    Raises:
        InvalidSTIXError: If URL cannot be fetched or parsed
    """
    if aiohttp is None:
        raise InvalidSTIXError("aiohttp library not available for HTTP requests")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    raise InvalidSTIXError(f"HTTP {response.status} when fetching {url}")
                stix_data = await response.json()
    except Exception as e:
        raise InvalidSTIXError(f"Error fetching STIX from URL: {e}")

    return parse_stix_bundle(stix_data)


# =============================================================================
# T054: STIX Type Mapping
# =============================================================================

def get_ontology_type_for_stix(stix_type: str) -> Optional[str]:
    """
    Map STIX object type to ontology entity type.

    Args:
        stix_type: STIX object type (e.g., "threat-actor", "malware")

    Returns:
        Ontology entity type (e.g., "ThreatActor", "Malware") or None if unmapped
    """
    return STIX_TYPE_MAPPING.get(stix_type)


def get_supported_stix_types() -> Dict[str, str]:
    """
    Get all supported STIX to ontology type mappings.

    Returns:
        Dictionary mapping STIX types to ontology types
    """
    return STIX_TYPE_MAPPING.copy()


def map_stix_relationship_type(stix_rel_type: str) -> str:
    """
    Map STIX relationship type to ontology relationship type.

    Converts hyphenated STIX types to underscored ontology types.

    Args:
        stix_rel_type: STIX relationship type (e.g., "attributed-to")

    Returns:
        Ontology relationship type (e.g., "attributed_to")
    """
    # Direct mapping
    if stix_rel_type in STIX_RELATIONSHIP_MAPPING:
        return STIX_RELATIONSHIP_MAPPING[stix_rel_type]

    # Convert hyphens to underscores as default
    return stix_rel_type.replace("-", "_")


# =============================================================================
# T055, T063, T064: Entity Extraction with Property Mapping
# =============================================================================

def extract_entity_from_stix(stix_obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract entity data from STIX object.

    Maps STIX properties to ontology entity attributes including:
    - Basic properties (name, description)
    - External references (MITRE IDs, CVE IDs)
    - Type-specific properties
    - Bi-temporal metadata (created, modified, valid_from, valid_until)

    Args:
        stix_obj: STIX object dictionary

    Returns:
        Entity dictionary with:
        - name: Entity name
        - entity_type: Ontology entity type
        - stix_id: Original STIX object ID
        - attributes: Dictionary of entity attributes

    Returns None for unmapped STIX types.
    """
    stix_type = stix_obj.get("type")
    if not stix_type:
        return None

    ontology_type = get_ontology_type_for_stix(stix_type)
    if not ontology_type:
        return None

    # Basic entity structure
    entity = {
        "name": stix_obj.get("name", stix_obj.get("id", "")),
        "entity_type": ontology_type,
        "stix_id": stix_obj.get("id", ""),
        "attributes": {}
    }

    # Extract description
    if "description" in stix_obj:
        entity["attributes"]["description"] = stix_obj["description"]

    # Extract external references (T063)
    if "external_references" in stix_obj:
        _extract_external_references(stix_obj["external_references"], entity["attributes"], stix_type)

    # Type-specific property mapping
    if stix_type == "threat-actor":
        _extract_threat_actor_properties(stix_obj, entity["attributes"])
    elif stix_type == "malware":
        _extract_malware_properties(stix_obj, entity["attributes"])
    elif stix_type == "vulnerability":
        _extract_vulnerability_properties(stix_obj, entity["attributes"])
    elif stix_type == "indicator":
        _extract_indicator_properties(stix_obj, entity["attributes"])
    elif stix_type == "attack-pattern":
        _extract_attack_pattern_properties(stix_obj, entity["attributes"])
    elif stix_type == "campaign":
        _extract_campaign_properties(stix_obj, entity["attributes"])
    elif stix_type == "infrastructure":
        _extract_infrastructure_properties(stix_obj, entity["attributes"])

    # Bi-temporal metadata (T064)
    entity["attributes"]["created_at"] = stix_obj.get("created", "")
    entity["attributes"]["updated_at"] = stix_obj.get("modified", "")

    # Valid from/until for indicators and time-bounded entities
    if "valid_from" in stix_obj:
        entity["attributes"]["valid_from"] = stix_obj["valid_from"]
    if "valid_until" in stix_obj:
        entity["attributes"]["valid_until"] = stix_obj["valid_until"]

    return entity


def _extract_external_references(
    external_refs: List[Dict[str, Any]],
    attributes: Dict[str, Any],
    stix_type: str
) -> None:
    """
    Extract external references to entity attributes.

    Handles:
    - MITRE ATT&CK IDs (G####, T####)
    - CVE IDs (CVE-YYYY-NNNN)
    - CAPEC IDs
    - Other external identifiers

    Args:
        external_refs: List of external reference dictionaries
        attributes: Entity attributes dict to populate
        stix_type: STIX object type for context
    """
    for ref in external_refs:
        source_name = ref.get("source_name", "").lower()
        external_id = ref.get("external_id", "")

        if not external_id:
            continue

        # MITRE ATT&CK references
        if source_name in MITRE_SOURCES:
            if stix_type == "threat-actor" and external_id.startswith("G"):
                attributes["mitre_id"] = external_id
            elif stix_type == "attack-pattern":
                if external_id.startswith("T"):
                    attributes["technique_id"] = external_id
                elif external_id.startswith("TA"):
                    attributes["tactic_id"] = external_id

        # CVE references
        elif source_name in CVE_SOURCES or external_id.startswith("CVE-"):
            if stix_type == "vulnerability":
                attributes["cve_id"] = external_id

        # Store all external references as list
        if "external_references" not in attributes:
            attributes["external_references"] = []
        attributes["external_references"].append({
            "source_name": ref.get("source_name"),
            "external_id": external_id,
            "url": ref.get("url", "")
        })


def _extract_threat_actor_properties(stix_obj: Dict[str, Any], attributes: Dict[str, Any]) -> None:
    """Extract ThreatActor specific properties."""
    if "aliases" in stix_obj:
        attributes["aliases"] = stix_obj["aliases"]
    if "sophistication" in stix_obj:
        attributes["sophistication"] = stix_obj["sophistication"]
    if "actor_type" in stix_obj:
        attributes["actor_type"] = stix_obj["actor_type"]
    if "resource_level" in stix_obj:
        attributes["resource_level"] = stix_obj["resource_level"]
    if "goals" in stix_obj:
        attributes["goals"] = stix_obj["goals"]


def _extract_malware_properties(stix_obj: Dict[str, Any], attributes: Dict[str, Any]) -> None:
    """Extract Malware specific properties."""
    if "malware_types" in stix_obj:
        attributes["malware_types"] = stix_obj["malware_types"]
    if "is_family" in stix_obj:
        attributes["is_family"] = stix_obj["is_family"]
    if "family" in stix_obj:
        attributes["family"] = stix_obj["family"]
    if "first_seen" in stix_obj:
        attributes["first_seen"] = stix_obj["first_seen"]
    if "operating_systems" in stix_obj:
        attributes["platforms"] = stix_obj["operating_systems"]
    if "capabilities" in stix_obj:
        attributes["capabilities"] = stix_obj["capabilities"]


def _extract_vulnerability_properties(stix_obj: Dict[str, Any], attributes: Dict[str, Any]) -> None:
    """Extract Vulnerability specific properties."""
    if "name" in stix_obj and stix_obj["name"].startswith("CVE-"):
        attributes["cve_id"] = stix_obj["name"]


def _extract_indicator_properties(stix_obj: Dict[str, Any], attributes: Dict[str, Any]) -> None:
    """Extract Indicator specific properties."""
    if "pattern" in stix_obj:
        attributes["pattern"] = stix_obj["pattern"]
    if "pattern_type" in stix_obj:
        attributes["pattern_type"] = stix_obj["pattern_type"]
    if "indicator_types" in stix_obj:
        attributes["indicator_types"] = stix_obj["indicator_types"]
    if "valid_from" in stix_obj:
        attributes["valid_from"] = stix_obj["valid_from"]
    if "valid_until" in stix_obj:
        attributes["valid_until"] = stix_obj["valid_until"]


def _extract_attack_pattern_properties(stix_obj: Dict[str, Any], attributes: Dict[str, Any]) -> None:
    """Extract Attack Pattern (TTP) specific properties."""
    if "aliases" in stix_obj:
        attributes["aliases"] = stix_obj["aliases"]
    if "kill_chain_phases" in stix_obj:
        attributes["kill_chain_phases"] = stix_obj["kill_chain_phases"]


def _extract_campaign_properties(stix_obj: Dict[str, Any], attributes: Dict[str, Any]) -> None:
    """Extract Campaign specific properties."""
    if "aliases" in stix_obj:
        attributes["aliases"] = stix_obj["aliases"]
    if "first_seen" in stix_obj:
        attributes["first_seen"] = stix_obj["first_seen"]
    if "last_seen" in stix_obj:
        attributes["last_seen"] = stix_obj["last_seen"]


def _extract_infrastructure_properties(stix_obj: Dict[str, Any], attributes: Dict[str, Any]) -> None:
    """Extract Infrastructure specific properties."""
    if "infrastructure_types" in stix_obj:
        attributes["infrastructure_type"] = stix_obj["infrastructure_types"]
    if "aliases" in stix_obj:
        attributes["aliases"] = stix_obj["aliases"]
    if "first_seen" in stix_obj:
        attributes["first_seen"] = stix_obj["first_seen"]
    if "last_seen" in stix_obj:
        attributes["last_seen"] = stix_obj["last_seen"]


# =============================================================================
# T056, T064: Relationship Extraction
# =============================================================================

def extract_relationship_from_stix(
    stix_rel: Dict[str, Any],
    context_objects: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Extract relationship data from STIX relationship object.

    Args:
        stix_rel: STIX relationship object
        context_objects: List of all STIX objects for resolving refs

    Returns:
        Relationship dictionary with:
        - relationship_type: Ontology relationship type
        - source_stix_id: Source entity STIX ID
        - target_stix_id: Target entity STIX ID
        - stix_id: Original STIX relationship ID
        - attributes: Relationship attributes

    Returns None if not a relationship object.
    """
    if stix_rel.get("type") != "relationship":
        return None

    stix_rel_type = stix_rel.get("relationship_type", "")
    source_ref = stix_rel.get("source_ref", "")
    target_ref = stix_rel.get("target_ref", "")

    if not stix_rel_type or not source_ref or not target_ref:
        return None

    # Map relationship type
    ontology_rel_type = map_stix_relationship_type(stix_rel_type)

    # Build relationship structure
    relationship = {
        "relationship_type": ontology_rel_type,
        "source_stix_id": source_ref,
        "target_stix_id": target_ref,
        "stix_id": stix_rel.get("id", ""),
        "attributes": {
            "created_at": stix_rel.get("created", ""),
            "updated_at": stix_rel.get("modified", "")
        }
    }

    # Extract confidence if present
    if "confidence" in stix_rel:
        relationship["attributes"]["confidence"] = stix_rel["confidence"]

    # Bi-temporal metadata (T064)
    # STIX uses start_time/stop_time for relationship validity
    if "start_time" in stix_rel:
        relationship["attributes"]["valid_from"] = stix_rel["start_time"]
    if "stop_time" in stix_rel:
        relationship["attributes"]["valid_until"] = stix_rel["stop_time"]

    # Try to resolve source and target entity types from context
    source_obj = _find_object_by_id(source_ref, context_objects)
    target_obj = _find_object_by_id(target_ref, context_objects)

    if source_obj:
        source_type = get_ontology_type_for_stix(source_obj.get("type", ""))
        if source_type:
            relationship["source_entity_type"] = source_type
        elif source_obj.get("type") == "identity":
            # Map identity to Organization or Person
            identity_class = source_obj.get("identity_class", "")
            if identity_class == "organization":
                relationship["source_entity_type"] = "Organization"
            else:
                relationship["source_entity_type"] = "Person"

    if target_obj:
        target_type = get_ontology_type_for_stix(target_obj.get("type", ""))
        if target_type:
            relationship["target_entity_type"] = target_type
        elif target_obj.get("type") == "identity":
            identity_class = target_obj.get("identity_class", "")
            if identity_class == "organization":
                relationship["target_entity_type"] = "Organization"
            else:
                relationship["target_entity_type"] = "Person"

    return relationship


def _find_object_by_id(
    object_id: str,
    objects: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Find STIX object by ID in list."""
    for obj in objects:
        if obj.get("id") == object_id:
            return obj
    return None


# =============================================================================
# T049, T057: Import Session Tracking
# =============================================================================

def create_import_session(
    import_id: str,
    source_file: str,
    total_objects: int,
    imported_count: int = 0,
    failed_count: int = 0
) -> Dict[str, Any]:
    """
    Create ImportSession entity for tracking import progress.

    Args:
        import_id: Unique import session identifier
        source_file: Source file path or URL
        total_objects: Total number of objects to import
        imported_count: Number of successfully imported objects
        failed_count: Number of failed objects

    Returns:
        ImportSession entity dictionary
    """
    # Determine status based on progress
    if failed_count > 0 and imported_count > 0:
        status = "PARTIAL"
    elif failed_count > 0 and imported_count == 0:
        status = "FAILED"
    elif imported_count == total_objects and failed_count == 0:
        status = "COMPLETED"
    else:
        status = "IN_PROGRESS"

    return {
        "name": import_id,
        "entity_type": "ImportSession",
        "attributes": {
            "source_file": source_file,
            "total_objects": total_objects,
            "imported_count": imported_count,
            "failed_count": failed_count,
            "failed_object_ids": [],
            "error_messages": [],
            "status": status,
            "started_at": datetime.utcnow().isoformat() + "Z",
        }
    }


def update_import_session(
    session: Dict[str, Any],
    imported_count: Optional[int] = None,
    failed_count: Optional[int] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update import session progress.

    Args:
        session: Existing import session entity
        imported_count: New imported count (if provided)
        failed_count: New failed count (if provided)
        status: New status (if provided)

    Returns:
        Updated import session entity
    """
    updated = session.copy()
    updated["attributes"] = session["attributes"].copy()

    if imported_count is not None:
        updated["attributes"]["imported_count"] = imported_count
    if failed_count is not None:
        updated["attributes"]["failed_count"] = failed_count
    if status is not None:
        updated["attributes"]["status"] = status

    return updated


def complete_import_session(session: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mark import session as completed.

    Args:
        session: Import session entity

    Returns:
        Updated session with COMPLETED status and completion timestamp
    """
    updated = update_import_session(
        session,
        status="COMPLETED"
    )
    # Add completion timestamp
    updated["attributes"]["completed_at"] = datetime.now().isoformat() + "Z"
    return updated


def fail_import_session(session: Dict[str, Any], error_message: str) -> Dict[str, Any]:
    """
    Mark import session as failed.

    Args:
        session: Import session entity
        error_message: Error message describing the failure

    Returns:
        Updated session with FAILED status
    """
    updated = update_import_session(session, status="FAILED")
    updated["attributes"]["error_message"] = error_message
    return updated


def add_failed_object(
    session: Dict[str, Any],
    stix_id: str,
    error: str
) -> Dict[str, Any]:
    """
    Add failed object to import session tracking.

    Args:
        session: Import session entity
        stix_id: STIX object ID that failed
        error: Error message

    Returns:
        Updated session with failed object tracked
    """
    updated = session.copy()
    updated["attributes"] = session["attributes"].copy()

    if "failed_object_ids" not in updated["attributes"]:
        updated["attributes"]["failed_object_ids"] = []
    if "error_messages" not in updated["attributes"]:
        updated["attributes"]["error_messages"] = []

    updated["attributes"]["failed_object_ids"].append(stix_id)
    updated["attributes"]["error_messages"].append(error)
    updated["attributes"]["failed_count"] = len(updated["attributes"]["failed_object_ids"])

    return updated


# =============================================================================
# T058, T059: Batched Import with Failure Handling
# =============================================================================

async def process_stix_bundle(
    stix_bundle: Dict[str, Any],
    graphiti_client: Any,
    batch_size: int = DEFAULT_BATCH_SIZE,
    continue_on_error: bool = True,
    progress_callback: Optional[callable] = None,
    group_id: str = "default"
) -> Dict[str, Any]:
    """
    Process STIX bundle and import entities/relationships to knowledge graph.

    Processes objects in batches for memory efficiency and progress tracking.
    Handles partial failures based on continue_on_error setting.

    Args:
        stix_bundle: Parsed STIX bundle dictionary
        graphiti_client: Graphiti client instance
        batch_size: Number of objects per batch (default: 1000)
        continue_on_error: Continue importing on individual object failures
        progress_callback: Optional callback for progress updates
        group_id: Knowledge graph group ID

    Returns:
        Import result dictionary with:
        - import_id: Unique import session ID
        - status: Import status (IN_PROGRESS, COMPLETED, PARTIAL, FAILED)
        - total_objects: Total objects in bundle
        - imported_count: Successfully imported objects
        - failed_count: Failed objects
        - failed_objects: List of failed object details
        - duration_seconds: Processing duration
    """
    start_time = time.time()

    # Parse bundle
    parsed = parse_stix_bundle(stix_bundle)
    objects = parsed["objects"]

    # Create import session
    import_id = generate_import_id()
    total_objects = len(objects)

    session = create_import_session(
        import_id=import_id,
        source_file=f"STIX bundle {parsed['bundle_id']}",
        total_objects=total_objects
    )

    # Track results
    imported_count = 0
    failed_objects = []
    entity_map: Dict[str, str] = {}  # STIX ID to Graphiti UUID mapping

    try:
        # Process in batches
        num_batches = (total_objects + batch_size - 1) // batch_size

        for batch_num in range(num_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, total_objects)
            batch_objects = objects[start_idx:end_idx]

            # Extract entities and relationships from batch
            entities = []
            relationships = []

            for stix_obj in batch_objects:
                try:
                    if stix_obj.get("type") == "relationship":
                        rel = extract_relationship_from_stix(stix_obj, objects)
                        if rel:
                            relationships.append(rel)
                    else:
                        entity = extract_entity_from_stix(stix_obj)
                        if entity:
                            entities.append(entity)
                except Exception as e:
                    logger.warning(f"Error extracting from STIX object {stix_obj.get('id')}: {e}")
                    failed_objects.append({
                        "stix_id": stix_obj.get("id", "unknown"),
                        "stix_type": stix_obj.get("type", "unknown"),
                        "error": str(e)
                    })
                    if not continue_on_error:
                        raise

            # Import entities to knowledge graph
            for entity in entities:
                try:
                    # Create episode for entity
                    episode_body = _create_entity_episode(entity)
                    episode_name = f"STIX Import: {entity['name']} ({entity['entity_type']})"

                    result = await graphiti_client.add_episode(
                        name=episode_name,
                        episode_body=episode_body,
                        source=f"STIX Import ({import_id})",
                        group_id=group_id
                    )

                    # Map STIX ID to entity (for relationships)
                    entity_map[entity["stix_id"]] = entity["stix_id"]
                    imported_count += 1

                except Exception as e:
                    logger.warning(f"Error importing entity {entity.get('name')}: {e}")
                    failed_objects.append({
                        "stix_id": entity.get("stix_id", "unknown"),
                        "stix_type": entity.get("entity_type", "unknown"),
                        "error": str(e)
                    })
                    if not continue_on_error:
                        raise

            # Import relationships
            for relationship in relationships:
                try:
                    # Create episode for relationship
                    episode_body = _create_relationship_episode(relationship)
                    episode_name = f"STIX Relationship: {relationship['relationship_type']}"

                    await graphiti_client.add_episode(
                        name=episode_name,
                        episode_body=episode_body,
                        source=f"STIX Import ({import_id})",
                        group_id=group_id
                    )

                    imported_count += 1

                except Exception as e:
                    logger.warning(f"Error importing relationship: {e}")
                    failed_objects.append({
                        "stix_id": relationship.get("stix_id", "unknown"),
                        "stix_type": "relationship",
                        "error": str(e)
                    })
                    if not continue_on_error:
                        raise

            # Update session and report progress
            session = update_import_session(
                session,
                imported_count=imported_count,
                failed_count=len(failed_objects)
            )

            if progress_callback:
                await progress_callback({
                    "batch_number": batch_num + 1,
                    "total_batches": num_batches,
                    "batch_imported_count": imported_count,
                    "total_imported_count": imported_count,
                    "batch_failed_count": len(failed_objects),
                    "total_failed_count": len(failed_objects)
                })

        # Determine final status
        if len(failed_objects) > 0 and imported_count > 0:
            status = "PARTIAL"
        elif len(failed_objects) > 0:
            status = "FAILED"
        else:
            status = "COMPLETED"

        session = update_import_session(session, status=status)

    except Exception as e:
        logger.error(f"Fatal error during STIX import: {e}")
        session = fail_import_session(session, str(e))
        status = "FAILED"

    duration = time.time() - start_time

    return {
        "import_id": import_id,
        "status": status,
        "total_objects": total_objects,
        "imported_count": imported_count,
        "failed_count": len(failed_objects),
        "failed_objects": failed_objects,
        "duration_seconds": round(duration, 2)
    }


def _create_entity_episode(entity: Dict[str, Any]) -> str:
    """Create episode body for entity import."""
    parts = [
        f"Entity Type: {entity['entity_type']}",
        f"Name: {entity['name']}",
        f"STIX ID: {entity['stix_id']}"
    ]

    # Add attributes
    if entity.get("attributes"):
        parts.append("\nAttributes:")
        for key, value in entity["attributes"].items():
            if value:
                parts.append(f"  - {key}: {value}")

    return "\n".join(parts)


def _create_relationship_episode(relationship: Dict[str, Any]) -> str:
    """Create episode body for relationship import."""
    parts = [
        f"Relationship Type: {relationship['relationship_type']}",
        f"Source: {relationship['source_stix_id']}",
        f"Target: {relationship['target_stix_id']}",
        f"STIX ID: {relationship['stix_id']}"
    ]

    # Add attributes
    if relationship.get("attributes"):
        parts.append("\nAttributes:")
        for key, value in relationship["attributes"].items():
            if value:
                parts.append(f"  - {key}: {value}")

    return "\n".join(parts)


# =============================================================================
# Import Session Management for Resume
# =============================================================================

async def get_import_session_status(
    import_id: str,
    graphiti_client: Any
) -> Optional[Dict[str, Any]]:
    """
    Retrieve import session status from knowledge graph.

    Args:
        import_id: Import session ID
        graphiti_client: Graphiti client instance

    Returns:
        Import session status or None if not found
    """
    # Search for ImportSession entity by name
    results = await graphiti_client.search_nodes(
        query=import_id,
        entity_types=["ImportSession"]
    )

    if not results:
        return None

    for result in results:
        if result.get("name") == import_id:
            return {
                "import_id": import_id,
                "source_file": result.get("attributes", {}).get("source_file", ""),
                "started_at": result.get("attributes", {}).get("started_at", ""),
                "completed_at": result.get("attributes", {}).get("completed_at"),
                "status": result.get("attributes", {}).get("status", "UNKNOWN"),
                "total_objects": result.get("attributes", {}).get("total_objects", 0),
                "imported_count": result.get("attributes", {}).get("imported_count", 0),
                "failed_count": result.get("attributes", {}).get("failed_count", 0),
                "failed_object_ids": result.get("attributes", {}).get("failed_object_ids", []),
                "error_messages": result.get("attributes", {}).get("error_messages", [])
            }

    return None


async def resume_import(
    import_id: str,
    stix_bundle: Dict[str, Any],
    graphiti_client: Any,
    retry_failed_only: bool = True,
    batch_size: int = DEFAULT_BATCH_SIZE,
    group_id: str = "default"
) -> Dict[str, Any]:
    """
    Resume a partially failed STIX import.

    Args:
        import_id: Original import session ID
        stix_bundle: Original STIX bundle
        graphiti_client: Graphiti client instance
        retry_failed_only: Only retry previously failed objects
        batch_size: Batch size for reprocessing
        group_id: Knowledge graph group ID

    Returns:
        Resume result with updated import status
    """
    # Get original import session
    session = await get_import_session_status(import_id, graphiti_client)
    if not session:
        raise InvalidSTIXError(f"Import session not found: {import_id}")

    if session["status"] not in ["PARTIAL", "FAILED"]:
        raise InvalidSTIXError(f"Cannot resume import with status: {session['status']}")

    # Parse bundle
    parsed = parse_stix_bundle(stix_bundle)
    objects = parsed["objects"]

    # Determine which objects to retry
    if retry_failed_only and session.get("failed_object_ids"):
        # Only retry failed objects
        failed_ids = set(session["failed_object_ids"])
        objects_to_retry = [obj for obj in objects if obj.get("id") in failed_ids]
    else:
        # Retry all objects
        objects_to_retry = objects

    # Process failed objects
    result = await process_stix_bundle(
        stix_bundle={"type": "bundle", "id": parsed["bundle_id"], "spec_version": "2.1", "objects": objects_to_retry},
        graphiti_client=graphiti_client,
        batch_size=batch_size,
        continue_on_error=True,
        group_id=group_id
    )

    return {
        "import_id": import_id,
        "status": result["status"],
        "retried_count": len(objects_to_retry),
        "imported_count": result["imported_count"],
        "failed_count": result["failed_count"]
    }
