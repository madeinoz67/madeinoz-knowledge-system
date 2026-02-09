"""
LKAP Entity Models (Feature 022)
Local Knowledge Augmentation Platform

Entity definitions for Document Memory (RAG) and Knowledge Memory (Graph) tiers.
All entities use Pydantic BaseModel for validation and serialization.

Data Model Reference: specs/022-self-hosted-rag/data-model.md
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class Domain(str, Enum):
    """Domain classification for documents"""
    EMBEDDED = "embedded"
    SOFTWARE = "software"
    SECURITY = "security"
    CLOUD = "cloud"
    STANDARDS = "standards"


class DocumentType(str, Enum):
    """Document type classification"""
    PDF = "pdf"
    MARKDOWN = "markdown"
    TEXT = "text"
    HTML = "html"


class Sensitivity(str, Enum):
    """Sensitivity level for documents"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class FactType(str, Enum):
    """Fact types for Knowledge Graph"""
    CONSTRAINT = "Constraint"
    ERRATUM = "Erratum"
    WORKAROUND = "Workaround"
    API = "API"
    BUILD_FLAG = "BuildFlag"
    PROTOCOL_RULE = "ProtocolRule"
    DETECTION = "Detection"
    INDICATOR = "Indicator"


class ResolutionStrategy(str, Enum):
    """Conflict resolution strategies"""
    DETECT_ONLY = "detect_only"
    KEEP_BOTH = "keep_both"
    PREFER_NEWEST = "prefer_newest"
    REJECT_INCOMING = "reject_incoming"


class IngestionStatus(str, Enum):
    """Document ingestion status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REVIEW_REQUIRED = "review_required"


class ConflictStatus(str, Enum):
    """Conflict resolution status"""
    OPEN = "open"
    RESOLVED = "resolved"
    DEFERRED = "deferred"


class ConfidenceBand(str, Enum):
    """Classification confidence band"""
    HIGH = "high"  # ≥0.85
    MEDIUM = "medium"  # 0.70-0.84
    LOW = "low"  # <0.70


# ============================================================================
# Document Memory (RAG) Tier Entities
# ============================================================================

class Document(BaseModel):
    """
    Source file with metadata, tracked through ingestion lifecycle

    Storage: RAGFlow vector database + filesystem
    Relationships: 1:N DocumentChunk, 1:N Evidence, 1:1 IngestionState
    """
    doc_id: str = Field(..., description="Unique document identifier (UUID)")
    hash: str = Field(..., description="SHA-256 hash of source file (idempotency check)")
    filename: str = Field(..., description="Original filename")
    path: str = Field(..., description="Canonical storage path")
    domain: Domain = Field(..., description="Domain classification")
    type: Optional[DocumentType] = Field(None, description="Document type")
    vendor: Optional[str] = Field(None, description="Vendor name (e.g., ST, NXP, ARM)")
    component: Optional[str] = Field(None, description="Component name (e.g., STM32H7)")
    version: Optional[str] = Field(None, description="Document version (e.g., v1.0, Rev C)")
    projects: List[str] = Field(default_factory=list, description="Associated project tags")
    sensitivity: Sensitivity = Field(Sensitivity.PUBLIC, description="Sensitivity level")
    upload_date: datetime = Field(default_factory=datetime.now, description="Timestamp of initial upload")
    content_hash: str = Field(..., description="Hash of content (for change detection)")


class DocumentChunk(BaseModel):
    """
    Segment of document content with embedding vector

    Storage: RAGFlow vector database
    Relationships: N:1 Document, 1:N Evidence
    """
    chunk_id: str = Field(..., description="Unique chunk identifier (UUID)")
    doc_id: str = Field(..., description="Parent document reference")
    text: str = Field(..., description="Chunk text content")
    page_section: Optional[str] = Field(None, description="Page number or section identifier")
    position: int = Field(..., description="Position in document (sequence)")
    token_count: int = Field(..., ge=256, le=1024, description="Token count (256-1024 range)")
    embedding_vector: Optional[List[float]] = Field(None, description="Embedding vector (1024+ dimensions)")
    created_at: datetime = Field(default_factory=datetime.now, description="Timestamp of chunk creation")


class Evidence(BaseModel):
    """
    Reference from document chunk to promoted fact (provenance link)

    Storage: Knowledge Graph (as :Evidence nodes)
    Relationships: N:1 DocumentChunk, N:M Fact
    """
    evidence_id: str = Field(..., description="Unique evidence identifier (UUID)")
    chunk_id: str = Field(..., description="Source chunk reference")
    fact_ids: List[str] = Field(..., min_items=1, description="Facts this evidence supports")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    created_at: datetime = Field(default_factory=datetime.now, description="Timestamp of evidence creation")


# ============================================================================
# Knowledge Memory (Graph) Tier Entities
# ============================================================================

class Fact(BaseModel):
    """
    Typed knowledge in Knowledge Graph with conflict awareness

    Storage: Neo4j/FalkorDB (as :Fact nodes with type labels)
    Relationships: N:M Evidence, N:1 Conflict (optional)
    """
    fact_id: str = Field(..., description="Unique fact identifier (UUID)")
    type: FactType = Field(..., description="Fact type")
    entity: str = Field(..., description="Entity name (e.g., STM32H7.GPIO.max_speed)")
    value: str = Field(..., min_length=1, description="Fact value")
    scope: Optional[str] = Field(None, description="Scope constraint")
    version: Optional[str] = Field(None, description="Applicable version")
    valid_until: Optional[datetime] = Field(None, description="Expiration timestamp")
    conflict_id: Optional[str] = Field(None, description="Reference to conflict record")
    evidence_ids: List[str] = Field(..., min_items=1, description="Source evidence references")
    created_at: datetime = Field(default_factory=datetime.now, description="Timestamp of fact creation")
    deprecated_at: Optional[datetime] = Field(None, description="Deprecation timestamp")
    deprecated_by: Optional[str] = Field(None, description="Who deprecated the fact")


class Conflict(BaseModel):
    """
    Detected contradiction between facts

    Storage: Neo4j/FalkorDB (as :Conflict nodes)
    Relationships: 1:N Fact
    """
    conflict_id: str = Field(..., description="Unique conflict identifier (UUID)")
    fact_ids: List[str] = Field(..., min_items=2, description="Conflicting fact references (2+)")
    detection_date: datetime = Field(default_factory=datetime.now, description="Timestamp of conflict detection")
    resolution_strategy: ResolutionStrategy = Field(..., description="Resolution strategy")
    status: ConflictStatus = Field(..., description="Conflict status")
    resolved_at: Optional[datetime] = Field(None, description="Timestamp of resolution")
    resolved_by: Optional[str] = Field(None, description="User who resolved conflict")


# ============================================================================
# Classification & Ingestion State Entities
# ============================================================================

class IngestionState(BaseModel):
    """
    Processing status tracking for document ingestion

    Relationships: 1:1 Document
    """
    doc_id: str = Field(..., description="Document reference")
    status: IngestionStatus = Field(..., description="Processing status")
    confidence_band: Optional[ConfidenceBand] = Field(None, description="Classification confidence band")
    chunks_processed: int = Field(..., ge=0, description="Number of chunks created")
    chunks_total: Optional[int] = Field(None, description="Expected total chunks")
    error_message: Optional[str] = Field(None, description="Error details if status is failed")
    last_update: datetime = Field(default_factory=datetime.now, description="Timestamp of last status change")


class Classification(BaseModel):
    """
    Metadata inference result with confidence tracking

    Relationships: N:1 Document
    """
    classification_id: str = Field(..., description="Unique classification identifier (UUID)")
    doc_id: str = Field(..., description="Document reference")
    field_name: str = Field(..., description="Field being classified (domain, type, vendor, component)")
    value: str = Field(..., description="Classified value")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    signal_sources: List[str] = Field(..., min_items=1, description="Sources that contributed to classification")
    user_override: bool = Field(default=False, description="Whether user overrode automatic classification")
    created_at: datetime = Field(default_factory=datetime.now, description="Timestamp of classification")


# ============================================================================
# API Request/Response Models
# ============================================================================

class SearchResult(BaseModel):
    """Search result from RAGFlow semantic search"""
    chunk_id: str
    text: str
    source_document: str
    page_section: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    metadata: dict


class PromoteFromEvidenceRequest(BaseModel):
    """Request to promote evidence chunk to Knowledge Graph fact"""
    evidence_id: str
    fact_type: FactType
    value: str
    scope: Optional[str] = None
    version: Optional[str] = None


class PromoteFromQueryRequest(BaseModel):
    """Request to search and promote in one step"""
    query: str
    fact_type: FactType
    top_k: int = Field(default=3, ge=1, le=10)


class ReviewConflictsRequest(BaseModel):
    """Request to review conflicts with filters"""
    entity: Optional[str] = None
    fact_type: Optional[FactType] = None
    status: Optional[ConflictStatus] = None
    limit: int = Field(default=50, ge=1, le=100)


class ProvenanceGraph(BaseModel):
    """Provenance graph result for a fact"""
    fact: Fact
    evidence_chain: List[Evidence]
    documents: List[Document]
