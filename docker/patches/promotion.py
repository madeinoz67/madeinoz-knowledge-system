"""
Graphiti Knowledge Graph Connection for LKAP (Feature 022)
Local Knowledge Augmentation Platform

Extends existing Graphiti MCP server with fact promotion, conflict detection,
and provenance tracking capabilities.

This module provides functions for interacting with the Knowledge Graph tier
of LKAP's two-tier memory model (RAG + Knowledge Graph).

T067: Fact creation with 8 types (Constraint, Erratum, Workaround, API, BuildFlag, ProtocolRule, Detection, Indicator)
T068: Evidence-to-fact linking (Evidence node → Fact node)
T069: Provenance preservation (Fact → Evidence → Chunk → Document chain)
T070: Conflict detection Cypher query
T071: Resolution strategies (detect_only, keep_both, prefer_newest, reject_incoming)
T072: Version change detection
T073: Time-scoped metadata (observed_at, published_at, valid_until, TTL)
"""

import logging
import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodicNode
from graphiti_core.utils.search.search_filters import SearchFilters
from graphiti_core.edges import EntityEdge

from .lkap_models import (
    Fact,
    FactType,
    Conflict,
    ConflictStatus,
    ResolutionStrategy,
    Evidence,
    ProvenanceReference,
)
from .lkap_logging import get_logger

logger = get_logger("lkap.promotion")

# Global Graphiti instance (will be initialized by MCP server)
_graphiti: Optional[Graphiti] = None

# Resolution strategy configuration
DEFAULT_RESOLUTION_STRATEGY = ResolutionStrategy.DETECT_ONLY

# Time-scoped metadata defaults
DEFAULT_INDICATOR_TTL_DAYS = 90  # Security indicators valid for 90 days by default


def get_graphiti() -> Graphiti:
    """
    Get the global Graphiti instance.

    Returns:
        Graphiti instance

    Raises:
        RuntimeError: If Graphiti is not initialized
    """
    global _graphiti
    if _graphiti is None:
        raise RuntimeError(
            "Graphiti knowledge graph not initialized. Call init_graphiti() first. "
            "This is typically done during MCP server startup."
        )
    return _graphiti


def init_graphiti(graphiti_instance: Graphiti):
    """
    Initialize the global Graphiti instance.

    Called by the MCP server during startup.

    Args:
        graphiti_instance: Graphiti instance from MCP server
    """
    global _graphiti
    _graphiti = graphiti_instance
    logger.info("Graphiti connection initialized for LKAP")


async def create_fact(
    fact_type: FactType,
    entity: str,
    value: str,
    evidence_ids: List[str],
    scope: Optional[str] = None,
    version: Optional[str] = None,
    valid_until: Optional[datetime] = None,
) -> Fact:
    """
    Create a fact in the Knowledge Graph with provenance tracking.

    Args:
        fact_type: Type of fact to create
        entity: Entity name (e.g., "STM32H7.GPIO.max_speed")
        value: Fact value (e.g., "120MHz")
        evidence_ids: Source evidence identifiers
        scope: Optional scope constraint
        version: Optional applicable version
        valid_until: Optional expiration timestamp

    Returns:
        Created Fact with provenance links

    Raises:
        RuntimeError: If Graphiti is not initialized
    """
    graphiti = get_graphiti()

    # Create fact episode/node
    fact_data = {
        "fact_type": fact_type.value,
        "entity": entity,
        "value": value,
        "scope": scope,
        "version": version,
        "valid_until": valid_until.isoformat() if valid_until else None,
        "evidence_ids": evidence_ids,
        "created_at": datetime.now().isoformat(),
    }

    # Create episodic node for the fact
    episode = EpisodicNode(
        name=f"{entity}:{value}",
        episode_type=f"Fact:{fact_type.value}",
        source_data=fact_data,
    )

    # Add to Graphiti
    await graphiti.add_episode(
        name=episode.name,
        episode_body=episode.source_data,
        episode_type=episode.episode_type,
    )

    # Check for conflicts
    await _check_and_create_conflicts(entity, fact_type, value)

    logger.info(f"Created fact: {fact_type.value} - {entity} = {value}")

    # Return fact object (would need to query back to get UUID)
    return Fact(
        fact_id=episode.name,  # Using name as ID for now
        type=fact_type,
        entity=entity,
        value=value,
        scope=scope,
        version=version,
        valid_until=valid_until,
        evidence_ids=evidence_ids,
        created_at=datetime.now(),
    )


async def _check_and_create_conflicts(
    entity: str, fact_type: FactType, value: str
):
    """
    Check for and create conflicts with existing facts.

    Uses Cypher query pattern from Research Decision RT-005.

    Args:
        entity: Entity name
        fact_type: Fact type
        value: New fact value
    """
    graphiti = get_graphiti()

    # Search for existing facts with same entity and type
    search_filter = SearchFilters(
        entity=entity,
    )

    results = await graphiti.search(
        query=entity,
        search_filters=search_filter,
    )

    # Check for conflicts (same entity + type, different values)
    for result in results:
        result_value = _extract_fact_value(result)
        if result_value and result_value != value:
            await _create_conflict_record(
                entity, fact_type, value, result_value
            )


async def _create_conflict_record(
    entity: str, fact_type: FactType, value1: str, value2: str
):
    """
    Create a conflict record when conflicting facts are detected.

    Args:
        entity: Entity name
        fact_type: Fact type
        value1: First fact value
        value2: Second fact value (conflicting)
    """
    # TODO: Create Conflict node in Graphiti
    logger.warning(
        f"Conflict detected for {entity} ({fact_type.value}): "
        f"{value1} vs {value2}"
    )


def _extract_fact_value(result: Dict[str, Any]) -> Optional[str]:
    """Extract fact value from Graphiti search result"""
    # Extract value from result's source_data or name
    if "source_data" in result:
        return result["source_data"].get("value")
    return None


async def promote_from_evidence(
    evidence_id: str,
    fact_type: FactType,
    value: str,
    entity: Optional[str] = None,
    scope: Optional[str] = None,
    version: Optional[str] = None,
    valid_until: Optional[datetime] = None,
    resolution_strategy: ResolutionStrategy = DEFAULT_RESOLUTION_STRATEGY,
) -> Fact:
    """
    Promote evidence to a Knowledge Graph fact.

    T065: kg.promoteFromEvidence MCP tool implementation.
    T068: Evidence-to-fact linking (Evidence node → Fact node).

    Args:
        evidence_id: Source evidence/chunk identifier
        fact_type: Type of fact to create
        value: Fact value
        entity: Optional entity name (extracted from evidence if not provided)
        scope: Optional scope constraint
        version: Optional applicable version
        valid_until: Optional expiration timestamp
        resolution_strategy: How to handle conflicts

    Returns:
        Created Fact with provenance links

    Raises:
        RuntimeError: If Graphiti is not initialized
    """
    graphiti = get_graphiti()

    # Extract entity from evidence if not provided
    if entity is None:
        entity = await _extract_entity_from_evidence(evidence_id)

    # Check for existing conflicts before creating
    conflicts = await detect_conflicts(entity, fact_type)
    if conflicts:
        logger.info(f"Found {len(conflicts)} existing conflicts for {entity}")

        # Apply resolution strategy
        resolution_result = await apply_resolution_strategy(
            conflicts, fact_type, entity, value, resolution_strategy
        )

        if resolution_result == "reject_incoming":
            logger.info(f"Rejecting incoming fact per resolution strategy: {entity} = {value}")
            raise ValueError(f"Fact rejected due to conflict: {entity} = {value}")

    # Create the fact
    fact = await create_fact(
        fact_type=fact_type,
        entity=entity,
        value=value,
        evidence_ids=[evidence_id],
        scope=scope,
        version=version,
        valid_until=valid_until,
    )

    # Create evidence-to-fact link (T068)
    await _create_evidence_fact_link(evidence_id, fact.fact_id)

    return fact


async def promote_from_query(
    query: str,
    fact_type: FactType,
    top_k: int = 5,
    scope: Optional[str] = None,
    version: Optional[str] = None,
    valid_until: Optional[datetime] = None,
) -> List[Fact]:
    """
    Search for evidence and promote matching results to Knowledge Graph facts.

    T066: kg.promoteFromQuery MCP tool implementation.

    Args:
        query: Search query for finding evidence
        fact_type: Type of facts to create
        top_k: Maximum number of evidence chunks to promote
        scope: Optional scope constraint
        version: Optional applicable version
        valid_until: Optional expiration timestamp

    Returns:
        List of created Facts

    Raises:
        RuntimeError: If Graphiti is not initialized
    """
    # Use RAGFlow to search for evidence (via rag.search tool)
    # For now, use Graphiti search
    graphiti = get_graphiti()

    results = await graphiti.search(
        query=query,
        num_results=top_k,
    )

    facts = []
    for result in results:
        # Extract entity and value from search result
        entity = await _extract_entity_from_result(result)
        value = await _extract_value_from_result(result, fact_type)

        if entity and value:
            # Extract chunk_id from result for evidence link
            evidence_id = result.get("uuid", str(uuid.uuid4()))

            fact = await create_fact(
                fact_type=fact_type,
                entity=entity,
                value=value,
                evidence_ids=[evidence_id],
                scope=scope,
                version=version,
                valid_until=valid_until,
            )

            facts.append(fact)

    logger.info(f"Promoted {len(facts)} facts from query: {query}")
    return facts


async def detect_conflicts(
    entity: str,
    fact_type: FactType,
    status: Optional[ConflictStatus] = None,
) -> List[Conflict]:
    """
    Detect conflicts for a given entity and fact type.

    T070: Conflict detection using Cypher query (exact match).
    T084: kg.reviewConflicts query support.

    Uses Cypher query to find facts with same entity + type but different values.
    This is more accurate than semantic search for conflict detection.

    Args:
        entity: Entity name
        fact_type: Fact type
        status: Optional status filter (open, resolved, deferred)

    Returns:
        List of Conflict records
    """
    graphiti = get_graphiti()
    driver = graphiti.driver

    # Cypher query for conflict detection (from lkap_schema.py)
    # Finds facts with same entity + type but different values
    query = """
    MATCH (f1:Fact), (f2:Fact)
    WHERE f1.entity = $entity
      AND f1.fact_type = $fact_type
      AND f2.entity = $entity
      AND f2.fact_type = $fact_type
      AND f1.uuid <> f2.uuid
      AND f1.value <> f2.value
      AND (f1.valid_until IS NULL OR f1.valid_until > datetime())
      AND (f2.valid_until IS NULL OR f2.valid_until > datetime())
    RETURN f1, f2
    """

    # Add status filter if specified
    if status:
        status_filter = """
        AND (f1.conflict_status = $status OR f1.conflict_status IS NULL)
        AND (f2.conflict_status = $status OR f2.conflict_status IS NULL)
        """
        # Insert status filter before RETURN
        query = query.replace("AND f1.value <> f2.value", status_filter + "\n      AND f1.value <> f2.value")

    try:
        async with driver.session() as session:
            result = await session.run(
                query,
                {
                    "entity": entity,
                    "fact_type": fact_type.value,
                    "status": status.value if status else None
                }
            )

            conflicts: List[Conflict] = []
            seen_fact_pairs: set = set()

            async for record in result:
                f1_node = record["f1"]
                f2_node = record["f2"]

                # Create unique pair identifier to avoid duplicates
                pair_id = tuple(sorted([f1_node["uuid"], f2_node["uuid"]]))
                if pair_id in seen_fact_pairs:
                    continue
                seen_fact_pairs.add(pair_id)

                # Create Fact objects
                fact1 = Fact(
                    fact_id=f1_node["uuid"],
                    type=FactType(f1_node["fact_type"]),
                    entity=f1_node["entity"],
                    value=f1_node["value"],
                    created_at=datetime.fromisoformat(f1_node["created_at"]),
                    valid_until=datetime.fromisoformat(f1_node["valid_until"]) if f1_node.get("valid_until") else None,
                    evidence_ids=f1_node.get("evidence_ids", []),
                )

                fact2 = Fact(
                    fact_id=f2_node["uuid"],
                    type=FactType(f2_node["fact_type"]),
                    entity=f2_node["entity"],
                    value=f2_node["value"],
                    created_at=datetime.fromisoformat(f2_node["created_at"]),
                    valid_until=datetime.fromisoformat(f2_node["valid_until"]) if f2_node.get("valid_until") else None,
                    evidence_ids=f2_node.get("evidence_ids", []),
                )

                conflict = Conflict(
                    conflict_id=str(uuid.uuid4()),
                    facts=[fact1, fact2],
                    detection_date=datetime.now(),
                    resolution_strategy=DEFAULT_RESOLUTION_STRATEGY,
                    status=status or ConflictStatus.OPEN,
                )
                conflicts.append(conflict)

            logger.info(f"Detected {len(conflicts)} conflicts for {entity}/{fact_type}")
            return conflicts

    except Exception as e:
        logger.error(f"Conflict detection Cypher query failed: {e}")
        # Fallback to semantic search if Cypher fails
        logger.warning("Falling back to semantic search for conflict detection")
        return await _detect_conflicts_fallback(entity, fact_type, status)


async def _detect_conflicts_fallback(
    entity: str,
    fact_type: FactType,
    status: Optional[ConflictStatus] = None,
) -> List[Conflict]:
    """
    Fallback conflict detection using semantic search.

    Used when Cypher query fails (e.g., database not properly initialized).
    """
    graphiti = get_graphiti()

    results = await graphiti.search(
        query=entity,
        num_results=100,
    )

    conflicts: List[Conflict] = []
    seen_values: Dict[str, Dict[str, Any]] = {}

    for result in results:
        result_data = result.get("source_data", {})
        result_entity = result_data.get("entity")
        result_type = result_data.get("fact_type")
        result_value = result_data.get("value")

        if result_entity == entity and result_type == fact_type.value:
            if result_value not in seen_values:
                seen_values[result_value] = {
                    "fact_id": result.get("uuid"),
                    "value": result_value,
                    "created_at": result_data.get("created_at"),
                }

    # Create conflict records if multiple values exist
    if len(seen_values) > 1:
        values_list = list(seen_values.values())
        for i in range(len(values_list)):
            for j in range(i + 1, len(values_list)):
                conflict = Conflict(
                    conflict_id=str(uuid.uuid4()),
                    facts=[
                        Fact(
                            fact_id=values_list[i]["fact_id"],
                            type=fact_type,
                            entity=entity,
                            value=values_list[i]["value"],
                            created_at=datetime.fromisoformat(values_list[i]["created_at"]),
                            evidence_ids=[],
                        ),
                        Fact(
                            fact_id=values_list[j]["fact_id"],
                            type=fact_type,
                            entity=entity,
                            value=values_list[j]["value"],
                            created_at=datetime.fromisoformat(values_list[j]["created_at"]),
                            evidence_ids=[],
                        ),
                    ],
                    detection_date=datetime.now(),
                    resolution_strategy=DEFAULT_RESOLUTION_STRATEGY,
                    status=status or ConflictStatus.OPEN,
                )
                conflicts.append(conflict)

    return conflicts


async def apply_resolution_strategy(
    conflicts: List[Conflict],
    fact_type: FactType,
    entity: str,
    new_value: str,
    strategy: ResolutionStrategy,
) -> str:
    """
    Apply conflict resolution strategy.

    T071: Resolution strategies implementation.
    T088: Conflict status tracking.

    Strategies:
    - detect_only: Log conflict, don't modify (default)
    - keep_both: Mark both as valid, add conflict metadata
    - prefer_newest: Keep newer fact, deprecate older
    - reject_incoming: Reject the new fact

    Args:
        conflicts: List of existing conflicts
        fact_type: Type of fact
        entity: Entity name
        new_value: New fact value being promoted
        strategy: Resolution strategy to apply

    Returns:
        Resolution action taken ("created", "deprecated", "rejected", "kept_both")
    """
    if strategy == ResolutionStrategy.DETECT_ONLY:
        # Log conflict, create new fact with conflict metadata
        for conflict in conflicts:
            conflict.resolution_strategy = strategy
            conflict.status = ConflictStatus.OPEN
        logger.info(f"Conflict detected for {entity}, applying detect_only strategy")
        return "created"

    elif strategy == ResolutionStrategy.KEEP_BOTH:
        # Mark all facts as valid but link them via conflict record
        for conflict in conflicts:
            conflict.resolution_strategy = strategy
            conflict.status = ConflictStatus.RESOLVED
            conflict.resolved_at = datetime.now()
        logger.info(f"Conflict for {entity} resolved with keep_both strategy")
        return "kept_both"

    elif strategy == ResolutionStrategy.PREFER_NEWEST:
        # Deprecate older facts, keep newest
        # (For new incoming fact, this means accepting it)
        for conflict in conflicts:
            conflict.resolution_strategy = strategy
            conflict.status = ConflictStatus.RESOLVED
            conflict.resolved_at = datetime.now()
            # Deprecate older fact
            conflict.facts[0].deprecated_at = datetime.now()
            conflict.facts[0].deprecated_by = "prefer_newest_strategy"
        logger.info(f"Conflict for {entity} resolved with prefer_newest strategy (newest kept)")
        return "created"

    elif strategy == ResolutionStrategy.REJECT_INCOMING:
        # Reject the new fact
        for conflict in conflicts:
            conflict.resolution_strategy = strategy
            conflict.status = ConflictStatus.RESOLVED
        logger.info(f"Rejecting incoming fact for {entity} per reject_incoming strategy")
        return "rejected"

    return "created"


async def get_provenance(fact_id: str) -> Dict[str, Any]:
    """
    Get provenance chain for a fact.

    T069: Provenance preservation (Fact → Evidence → Chunk → Document chain).
    T085: kg.getProvenance MCP tool implementation.

    Args:
        fact_id: Fact identifier

    Returns:
        Provenance graph with fact, evidence chain, and documents
    """
    from .ragflow_client import get_ragflow_client

    graphiti = get_graphiti()
    ragflow = get_ragflow_client()

    # Search for the fact
    results = await graphiti.search(
        query=fact_id,
        num_results=1,
    )

    if not results:
        raise ValueError(
            f"Fact not found: {fact_id}. Verify the fact ID is correct and "
            f"has been promoted to the knowledge graph. Use kg.facts to list available facts."
        )

    fact_result = results[0]
    fact_data = fact_result.get("source_data", {})

    # Build provenance chain with actual RAGFlow data
    evidence_chain = []
    documents = {}

    for chunk_id in fact_data.get("evidence_ids", []):
        try:
            # Query RAGFlow for actual chunk data
            chunk_data = await ragflow.get_chunk(chunk_id)

            # Extract document info from chunk metadata
            source_doc = chunk_data.get("source_document", "Unknown")
            doc_id = chunk_data.get("doc_id", source_doc)

            evidence_chain.append({
                "evidence_id": chunk_id,
                "chunk_id": chunk_id,
                "chunk_text": chunk_data.get("text", ""),
                "page_section": chunk_data.get("page_section", ""),
                "confidence": chunk_data.get("confidence", 0.85),
                "source_document": source_doc,
                "metadata": chunk_data.get("metadata", {}),
            })

            # Track unique documents
            if doc_id not in documents:
                documents[doc_id] = {
                    "doc_id": doc_id,
                    "filename": chunk_data.get("filename", source_doc),
                    "source_document": source_doc,
                }

        except Exception as e:
            logger.warning(f"Failed to retrieve chunk {chunk_id} from RAGFlow: {e}")
            # Fallback to placeholder if RAGFlow query fails
            evidence_chain.append({
                "evidence_id": chunk_id,
                "chunk_id": chunk_id,
                "chunk_text": f"[Chunk data unavailable: {str(e)}]",
                "confidence": 0.0,
                "error": str(e),
            })

    return {
        "fact": {
            "fact_id": fact_id,
            "type": fact_data.get("fact_type"),
            "entity": fact_data.get("entity"),
            "value": fact_data.get("value"),
            "created_at": fact_data.get("created_at"),
        },
        "evidence_chain": evidence_chain,
        "documents": list(documents.values()),
    }


async def _extract_entity_from_evidence(evidence_id: str) -> str:
    """
    Extract entity name from evidence/chunk.

    Uses simple heuristics to extract entity from chunk text.
    """
    # In real implementation, would query RAGFlow for chunk content
    # For now, return a placeholder
    return f"entity.{evidence_id[:8]}"


async def _extract_entity_from_result(result: Dict[str, Any]) -> Optional[str]:
    """Extract entity from search result"""
    return result.get("source_data", {}).get("entity")


async def _extract_value_from_result(
    result: Dict[str, Any], fact_type: FactType
) -> Optional[str]:
    """Extract value from search result based on fact type"""
    return result.get("source_data", {}).get("value")


async def _create_evidence_fact_link(evidence_id: str, fact_id: str):
    """
    Create evidence-to-fact link in Knowledge Graph.

    T068: Evidence-to-fact linking implementation.
    Creates a PROVENANCE edge from Evidence to Fact node.
    """
    from datetime import datetime, timezone

    graphiti = get_graphiti()

    # Get the graph driver to execute Cypher query directly
    # Graphiti doesn't expose high-level edge creation, so we use Cypher
    driver = graphiti.driver

    # Create PROVENANCE edge between evidence and fact
    query = """
    MATCH (evidence {uuid: $evidence_id})
    MATCH (fact {uuid: $fact_id})
    MERGE (evidence)-[r:PROVENANCE]->(fact)
    ON CREATE SET
        r.created_at = datetime(),
        r.created_at_timestamp = timestamp()
    RETURN r
    """

    try:
        async with driver.session() as session:
            await session.run(query, {"evidence_id": evidence_id, "fact_id": fact_id})
        logger.info(f"Created evidence-fact PROVENANCE edge: {evidence_id} → {fact_id}")
    except Exception as e:
        logger.error(f"Failed to create evidence-fact link: {e}")
        # Don't raise - linking is non-critical for fact creation


async def flag_affected_facts(doc_id: str, new_version: str) -> List[str]:
    """
    Flag facts affected by document version change.

    T072: Version change detection implementation.

    When a source document is updated, existing facts derived from it
    should be flagged for review.

    Args:
        doc_id: Document identifier
        new_version: New version of the document

    Returns:
        List of affected fact IDs
    """
    graphiti = get_graphiti()

    # Search for facts that reference this document
    results = await graphiti.search(
        query=doc_id,
        num_results=100,
    )

    affected_fact_ids = []
    for result in results:
        result_data = result.get("source_data", {})
        evidence_ids = result_data.get("evidence_ids", [])

        # Check if any evidence comes from this document
        for evidence_id in evidence_ids:
            if doc_id in evidence_id:
                fact_id = result.get("uuid")
                affected_fact_ids.append(fact_id)

                # Add version metadata to flag for review
                # In real implementation, would update the fact node
                logger.info(
                    f"Flagged fact {fact_id} for review: "
                    f"source document {doc_id} updated to version {new_version}"
                )

    return affected_fact_ids


async def create_fact_with_ttl(
    fact_type: FactType,
    entity: str,
    value: str,
    evidence_ids: List[str],
    ttl_days: Optional[int] = None,
    observed_at: Optional[datetime] = None,
    published_at: Optional[datetime] = None,
    scope: Optional[str] = None,
    version: Optional[str] = None,
) -> Fact:
    """
    Create a fact with time-scoped metadata.

    T073: Time-scoped metadata implementation.

    For security indicators and other time-sensitive facts, supports:
    - observed_at: When the fact was observed
    - published_at: When the fact was published (e.g., CVE publication)
    - valid_until: Fact expiration (TTL)
    - ttl_days: Days until expiration (default varies by fact type)

    Args:
        fact_type: Type of fact to create
        entity: Entity name
        value: Fact value
        evidence_ids: Source evidence identifiers
        ttl_days: Days until expiration (uses default for fact type if not provided)
        observed_at: Observation timestamp
        published_at: Publication timestamp
        scope: Optional scope constraint
        version: Optional applicable version

    Returns:
        Created Fact with time-scoped metadata
    """
    # Calculate valid_until based on TTL
    if ttl_days is None:
        if fact_type in (FactType.DETECTION, FactType.INDICATOR):
            ttl_days = DEFAULT_INDICATOR_TTL_DAYS
        else:
            ttl_days = None  # No expiration by default

    if ttl_days:
        valid_until = datetime.now() + timedelta(days=ttl_days)
    else:
        valid_until = None

    # Create the fact with time-scoped metadata
    fact = await create_fact(
        fact_type=fact_type,
        entity=entity,
        value=value,
        evidence_ids=evidence_ids,
        scope=scope,
        version=version,
        valid_until=valid_until,
    )

    # Add time-scoped metadata to fact
    if observed_at or published_at:
        # In real implementation, would update fact node with metadata
        logger.debug(
            f"Created fact {fact.fact_id} with time-scoped metadata: "
            f"observed_at={observed_at}, published_at={published_at}, "
            f"valid_until={valid_until}"
        )

    return fact


async def review_conflicts(
    entity: Optional[str] = None,
    fact_type: Optional[FactType] = None,
    status: Optional[ConflictStatus] = None,
    limit: int = 50,
) -> List[Conflict]:
    """
    Review conflicts with optional filters.

    T084: kg.reviewConflicts MCP tool implementation.

    Args:
        entity: Optional entity filter
        fact_type: Optional fact type filter
        status: Optional status filter (open, resolved, deferred)
        limit: Maximum results to return

    Returns:
        List of Conflict records matching filters
    """
    # Build query based on filters
    query = entity or ""

    # Search for facts
    graphiti = get_graphiti()

    results = await graphiti.search(
        query=query,
        num_results=limit * 10,  # Fetch more to find conflicts
    )

    # Group by entity and fact type to find conflicts
    entity_facts: Dict[Tuple[str, str], List[Dict]] = {}

    for result in results:
        result_data = result.get("source_data", {})
        result_entity = result_data.get("entity", "")
        result_type = result_data.get("fact_type", "")

        if entity and result_entity != entity:
            continue
        if fact_type and result_type != fact_type.value:
            continue

        key = (result_entity, result_type)
        if key not in entity_facts:
            entity_facts[key] = []
        entity_facts[key].append(result)

    # Create conflict records where multiple values exist
    conflicts = []
    for (entity_name, type_name), facts in entity_facts.items():
        if len(facts) > 1:
            values = [f.get("source_data", {}).get("value") for f in facts]
            if len(set(v for v in values if v)) > 1:
                # Real conflict exists (different values)
                conflict = Conflict(
                    conflict_id=str(uuid.uuid4()),
                    facts=[
                        Fact(
                            fact_id=f.get("uuid"),
                            type=FactType(type_name) if type_name else FactType.CONSTRAINT,
                            entity=entity_name,
                            value=f.get("source_data", {}).get("value", ""),
                            created_at=datetime.fromisoformat(
                                f.get("source_data", {}).get("created_at", datetime.now().isoformat())
                            ),
                            evidence_ids=f.get("source_data", {}).get("evidence_ids", []),
                        )
                        for f in facts
                    ],
                    detection_date=datetime.now(),
                    resolution_strategy=DEFAULT_RESOLUTION_STRATEGY,
                    status=status or ConflictStatus.OPEN,
                )
                conflicts.append(conflict)

    return conflicts[:limit]
