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


class ImageType(str, Enum):
    """Classification of image content from technical documents"""
    SCHEMATIC = "schematic"      # Circuit diagrams, block diagrams
    PINOUT = "pinout"           # Pin configuration diagrams
    WAVEFORM = "waveform"       # Timing diagrams, signal plots
    PHOTO = "photo"             # Product photos
    TABLE = "table"             # Tables (if extracted as image)
    GRAPH = "graph"             # Charts, graphs
    FLOWCHART = "flowchart"     # Process diagrams
    UNKNOWN = "unknown"         # Unclassified


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

    Storage: Qdrant vector database + filesystem
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

    Storage: Qdrant vector database
    Relationships: N:1 Document, 1:N Evidence

    T057: Added headings field for heading-aware chunk tracking via Docling HybridChunker.
    """
    chunk_id: str = Field(..., description="Unique chunk identifier (UUID)")
    doc_id: str = Field(..., description="Parent document reference")
    text: str = Field(..., description="Chunk text content")
    page_section: Optional[str] = Field(None, description="Page number or section identifier")
    position: int = Field(..., description="Position in document (sequence)")
    token_count: int = Field(..., ge=256, le=1024, description="Token count (256-1024 range)")
    headings: List[str] = Field(default_factory=list, description="Parent headings for provenance (H1 > H2 > H3)")
    embedding_vector: Optional[List[float]] = Field(None, description="Embedding vector (1024+ dimensions)")
    created_at: datetime = Field(default_factory=datetime.now, description="Timestamp of chunk creation")


class ImageChunk(BaseModel):
    """
    Extracted image from document with Vision LLM enrichment.

    Storage: Qdrant vector database (same collection as DocumentChunk with content_type='image')
    Relationships: N:1 Document, N:M DocumentChunk (related text chunks)

    Feature 024: Multimodal image extraction for technical documents.
    """
    image_id: str = Field(..., description="Unique image identifier (UUID)")
    doc_id: str = Field(..., description="Parent document reference")

    # Image data (one of these required)
    image_data: Optional[str] = Field(None, description="Base64 encoded image (PNG/JPEG)")
    image_path: Optional[str] = Field(None, description="Path to stored image file (if external storage)")

    # Metadata
    image_format: str = Field(default="PNG", description="Image format (PNG, JPEG)")
    dimensions: tuple[int, int] = Field(..., description="(width, height) in pixels")
    source_page: int = Field(..., description="Page number in source document")
    source_position: Optional[dict] = Field(None, description="Bounding box on page {x, y, width, height}")

    # Enrichment (Vision LLM)
    classification: ImageType = Field(default=ImageType.UNKNOWN, description="Image content type")
    description: str = Field(..., description="LLM-generated description for search indexing")
    ocr_text: Optional[str] = Field(None, description="Text extracted from image via OCR")

    # Linking
    related_chunk_ids: List[str] = Field(default_factory=list, description="Linked text chunk IDs")
    headings: List[str] = Field(default_factory=list, description="Parent headings for provenance")

    # Embeddings
    text_embedding: Optional[List[float]] = Field(None, description="Embedding of description (bge-large, 1024 dim)")
    image_embedding: Optional[List[float]] = Field(None, description="CLIP visual embedding (512 dim, Phase 2)")

    # Content type marker for unified collection
    content_type: str = Field(default="image", description="Content type marker ('image' or 'text')")

    created_at: datetime = Field(default_factory=datetime.now, description="Timestamp of image extraction")


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

    T077: Added severity field for conflict prioritization.
    """
    conflict_id: str = Field(..., description="Unique conflict identifier (UUID)")
    fact_ids: List[str] = Field(..., min_items=2, description="Conflicting fact references (2+)")
    facts: List[Fact] = Field(..., min_items=2, description="Conflicting fact objects (hydrated)")
    detection_date: datetime = Field(default_factory=datetime.now, description="Timestamp of conflict detection")
    resolution_strategy: ResolutionStrategy = Field(..., description="Resolution strategy")
    status: ConflictStatus = Field(..., description="Conflict status")
    resolved_at: Optional[datetime] = Field(None, description="Timestamp of resolution")
    resolved_by: Optional[str] = Field(None, description="User who resolved conflict")
    severity: Optional[str] = Field(None, description="Severity level: critical, major, or minor")


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
    """Search result from Qdrant semantic search"""
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


class ProvenanceReference(BaseModel):
    """
    Provenance chain link for a fact (T069).

    Represents one link in the provenance chain:
    Fact → Evidence → Chunk → Document
    """
    fact_id: str = Field(..., description="Fact identifier")
    evidence_id: str = Field(..., description="Evidence identifier")
    chunk_id: str = Field(..., description="Chunk identifier")
    chunk_text: str = Field(..., description="Chunk text content")
    chunk_confidence: float = Field(..., ge=0.0, le=1.0, description="RAG search confidence")
    doc_id: str = Field(..., description="Document identifier")
    doc_filename: str = Field(..., description="Document filename")
    doc_path: str = Field(..., description="Document storage path")
    page_section: Optional[str] = Field(None, description="Page or section identifier")


# ============================================================================
# Complete MCP Tool Request Models (T087)
# ============================================================================

class PromoteFromEvidenceRequest(BaseModel):
    """
    Complete request model for kg_promoteFromEvidence MCP tool.

    T087: Pydantic model for MCP tool input validation.
    """
    evidence_id: str = Field(..., min_length=1, description="Source evidence/chunk identifier from Qdrant")
    fact_type: FactType = Field(..., description="Type of fact to create")
    value: str = Field(..., min_length=1, description="Fact value (e.g., '120MHz', 'Enable FIFO flush')")
    entity: Optional[str] = Field(None, description="Optional entity name (e.g., 'STM32H7.GPIO.max_speed')")
    scope: Optional[str] = Field(None, description="Optional scope constraint for fact applicability")
    version: Optional[str] = Field(None, description="Optional version this fact applies to")
    valid_until: Optional[str] = Field(None, description="Optional expiration timestamp (ISO 8601)")
    resolution_strategy: ResolutionStrategy = Field(
        default=ResolutionStrategy.DETECT_ONLY,
        description="How to handle conflicts (detect_only, keep_both, prefer_newest, reject_incoming)"
    )


class PromoteFromQueryRequest(BaseModel):
    """
    Complete request model for kg_promoteFromQuery MCP tool.

    T087: Pydantic model for MCP tool input validation.
    """
    query: str = Field(..., min_length=1, description="Natural language search query for finding evidence")
    fact_type: FactType = Field(..., description="Type of facts to create")
    top_k: int = Field(default=5, ge=1, le=100, description="Maximum number of evidence chunks to promote")
    scope: Optional[str] = Field(None, description="Optional scope constraint for facts")
    version: Optional[str] = Field(None, description="Optional version facts apply to")
    valid_until: Optional[str] = Field(None, description="Optional expiration timestamp (ISO 8601)")


class ReviewConflictsRequest(BaseModel):
    """
    Complete request model for kg_reviewConflicts MCP tool.

    T087: Pydantic model for MCP tool input validation.
    """
    entity: Optional[str] = Field(None, description="Optional entity filter (e.g., 'STM32H7.GPIO.max_speed')")
    fact_type: Optional[FactType] = Field(None, description="Optional fact type filter")
    status: Optional[ConflictStatus] = Field(None, description="Optional status filter (open, resolved, deferred)")
    limit: int = Field(default=50, ge=1, le=1000, description="Maximum results to return")


class GetProvenanceRequest(BaseModel):
    """
    Request model for kg_getProvenance MCP tool.

    T087: Pydantic model for MCP tool input validation.
    """
    fact_id: str = Field(..., min_length=1, description="Fact identifier (UUID)")


class PromoteFromEvidenceResponse(BaseModel):
    """Response model for kg_promoteFromEvidence"""
    success: bool
    fact: Fact


class PromoteFromQueryResponse(BaseModel):
    """Response model for kg_promoteFromQuery"""
    success: bool
    facts: List[Fact]
    total_count: int


class ReviewConflictsResponse(BaseModel):
    """Response model for kg_reviewConflicts"""
    success: bool
    conflict_count: int
    conflicts: List[Conflict]


class GetProvenanceResponse(BaseModel):
    """Response model for kg_getProvenance"""
    success: bool
    fact_id: str
    provenance: List[ProvenanceReference]


# ============================================================================
# Qdrant RAG Models (Feature 023)
# ============================================================================

class IngestionResult(BaseModel):
    """
    Result of document ingestion operation (T011 - Feature 023)

    Returned by DoclingIngester.ingest() after parsing → chunking → embedding → storage.

    Attributes:
        doc_id: Unique document identifier (UUID)
        chunk_count: Number of chunks created and stored
        status: Processing status (completed, failed, partial)
        error_message: Error details if status is failed
        filename: Original filename processed
        processing_time_ms: Total ingestion time in milliseconds
    """
    doc_id: str = Field(..., description="Unique document identifier (UUID)")
    chunk_count: int = Field(..., ge=0, description="Number of chunks created and stored")
    status: IngestionStatus = Field(..., description="Processing status")
    error_message: Optional[str] = Field(None, description="Error details if status is failed")
    filename: str = Field(..., description="Original filename processed")
    processing_time_ms: Optional[int] = Field(None, description="Total ingestion time in milliseconds")


class QdrantSearchResult(BaseModel):
    """
    Search result from Qdrant semantic search (T031 - Feature 023)

    Enhanced SearchResult with Qdrant-specific fields.

    Attributes:
        chunk_id: Unique chunk identifier
        text: Chunk text content
        source: Source document filename
        page: Page number or section identifier
        confidence: Similarity score (0.0-1.0)
        metadata: Additional payload (domain, project, component, type)
    """
    chunk_id: str = Field(..., description="Unique chunk identifier")
    text: str = Field(..., description="Chunk text content")
    source: str = Field(..., description="Source document filename")
    page: Optional[str] = Field(None, description="Page number or section identifier")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0.0-1.0)")
    metadata: dict = Field(default_factory=dict, description="Additional payload")
