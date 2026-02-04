"""
Investigative Search Response Types

Feature: 020-investigative-search
See: specs/020-investigative-search/data-model.md

This module defines response types for the investigate_entity MCP tool:
- InvestigateResult: Main response with entity, connections, metadata
- Connection: Relationship edge with target entity
- InvestigationMetadata: Query metadata and statistics
- InvestigateEntityError: Error response type
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class EntityAttributes(BaseModel):
    """
    Extended entity attributes for decay scoring and lifecycle management.

    Feature 009 (Memory Decay Scoring) fields:
    - weighted_score: Weighted search score (0-1)
    - lifecycle_state: Memory lifecycle state (ACTIVE, DORMANT, etc.)
    - importance: Importance score (1-5)
    - stability: Stability score (1-5)
    - decay_score: Decay score (0-1)
    """
    weighted_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Weighted search score combining semantic, recency, and importance"
    )
    score_breakdown: Optional[Dict[str, float]] = Field(
        default=None,
        description="Breakdown of weighted score components (semantic, recency, importance)"
    )
    lifecycle_state: Optional[str] = Field(
        default=None,
        description="Memory lifecycle state (Feature 009)"
    )
    importance: Optional[int] = Field(
        default=None,
        ge=1,
        le=5,
        description="Importance score (1=TRIVIAL, 5=CORE)"
    )
    stability: Optional[int] = Field(
        default=None,
        ge=1,
        le=5,
        description="Stability score (1=VOLATILE, 5=PERMANENT)"
    )
    decay_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Decay score (0=fresh, 1=stale)"
    )
    last_accessed_at: Optional[str] = Field(
        default=None,
        description="Last access timestamp (ISO 8601)"
    )
    custom_attributes: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Custom attributes for CTI entities (Feature 019)"
    )


class Entity(BaseModel):
    """
    Represents a node in the knowledge graph with full context.

    The entity includes the primary entity being investigated and all
    connected entities returned in the connections array.
    """
    uuid: str = Field(description="Unique identifier for the entity")
    name: str = Field(description="Human-readable name")
    labels: List[str] = Field(description="Entity type(s)")
    summary: Optional[str] = Field(default=None, description="Optional summary/description")
    created_at: Optional[str] = Field(default=None, description="When the entity was created (ISO 8601)")
    group_id: Optional[str] = Field(default=None, description="Group ID for multi-tenant scenarios")
    attributes: Optional[EntityAttributes] = Field(default=None, description="Extended attributes")


class Connection(BaseModel):
    """
    Represents a relationship edge between two entities.

    The connection includes the relationship type, direction, target entity,
    and hop distance from the primary entity.
    """
    relationship: str = Field(description="Type of relationship (e.g., OWNED_BY, USES, TARGETS)")
    direction: str = Field(description="Direction: 'outgoing', 'incoming', or 'bidirectional'")
    target_entity: Entity = Field(description="The entity at the other end of this connection")
    hop_distance: int = Field(
        ge=1,
        le=3,
        description="Hops from primary entity (1=direct, 2=friend of friend, etc.)"
    )
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score for the relationship"
    )
    fact: Optional[str] = Field(default=None, description="Human-readable fact description")


class InvestigationMetadata(BaseModel):
    """
    Metadata about the investigation process and results.

    Includes depth explored, connection counts, cycle detection,
    and performance metrics.
    """
    depth_explored: int = Field(
        ge=1,
        le=3,
        description="Number of hops explored"
    )
    total_connections_explored: int = Field(
        ge=0,
        description="Total connections found before filtering"
    )
    connections_returned: int = Field(
        ge=0,
        description="Connections returned after filtering"
    )
    cycles_detected: int = Field(
        ge=0,
        description="Number of cycles detected"
    )
    cycles_pruned: List[str] = Field(
        default_factory=list,
        description="UUIDs of entities where cycles were pruned"
    )
    entities_skipped: Optional[int] = Field(
        default=None,
        description="Number of deleted/soft-deleted entities skipped"
    )
    relationship_types_filtered: Optional[List[str]] = Field(
        default=None,
        description="Relationship types that were filtered"
    )
    query_duration_ms: Optional[float] = Field(
        default=None,
        description="Query execution time in milliseconds"
    )
    max_connections_exceeded: Optional[bool] = Field(
        default=None,
        description="Whether the max connections threshold was exceeded"
    )


class InvestigateResult(BaseModel):
    """
    The primary response structure for an investigate query.

    Contains the entity being investigated, all connected entities,
    metadata about the investigation, and an optional warning message.
    """
    entity: Entity = Field(description="The primary entity that was searched for")
    connections: List[Connection] = Field(
        default_factory=list,
        description="All connected entities found during traversal"
    )
    metadata: InvestigationMetadata = Field(description="Metadata about the investigation")
    warning: Optional[str] = Field(
        default=None,
        description="Optional warning message for edge cases (e.g., too many connections)"
    )


class InvestigateEntityError(BaseModel):
    """
    Error response for investigate_entity operations.

    Used when entity lookup fails or other errors occur.
    """
    error: str = Field(description="Error message")
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )


# Export all types for convenient importing
__all__ = [
    "EntityAttributes",
    "Entity",
    "Connection",
    "InvestigationMetadata",
    "InvestigateResult",
    "InvestigateEntityError",
]
