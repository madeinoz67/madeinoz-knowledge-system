# Research: Local Knowledge Augmentation Platform (LKAP)

**Feature**: 022-self-hosted-rag
**Date**: 2026-02-09
**Phase**: 0 - Research & Technical Decisions

## Overview

This document captures research findings for technical unknowns identified during planning. All NEEDS CLARIFICATION items from Technical Context have been resolved through research and documented here.

## RT-001: RAGFlow Python Client Integration

### Decision

**Use RAGFlow HTTP REST API with Python requests library**

### Rationale

- RAGFlow provides HTTP REST API for document ingestion and search
- No official Python SDK available; HTTP client is simplest approach
- Containerized deployment ensures network isolation
- Alternative: Qdrant/Weaviate with official Python clients (rejected due to PRD specifying RAGFlow)

### Implementation Notes

```python
# RAGFlow API endpoints
POST /api/documents      # Upload and index document
GET  /api/search         # Semantic search
GET  /api/documents/{id} # Retrieve document chunks
DELETE /api/documents/{id} # Delete document
```

### Configuration

- Container: `ragflow/ragflow:latest` (or self-hosted build)
- Port: 9380 (HTTP), 9381 (gRPC)
- Environment: `RAGFLOW_API_KEY` (optional, for authentication)
- Vector dimension: 1024+ (configurable)

## RT-002: Docling Document Parsing and Chunking

### Decision

**Use Docling with heading-aware recursive chunking**

### Rationale

- Docling provides excellent PDF parsing with table, section, and errata preservation
- Heading-aware chunking maintains semantic coherence (critical for technical docs)
- Recursive chunking respects document hierarchy (H1 → H2 → H3)
- Alternative: LangChain text splitters (rejected - less PDF structure awareness)

### Implementation Notes

```python
from docling.document import Document
from docling.chunking import ChunkingParams

# Heading-aware chunking params
params = ChunkingParams(
    chunk_size=(512, 768),  # token range
    overlap=100,             # token overlap
    respect_headings=True,   # split at headings
    min_chunk_size=256       # avoid tiny chunks
)
```

### Chunking Strategy

1. Parse PDF with Docling → Document object
2. Extract document structure (headings, sections, tables)
3. Recursively chunk by heading boundaries
4. Enforce 512-768 token limits (soft: prefer heading split, hard: force split)
5. Add 100-token overlap between chunks for context
6. Generate embeddings for each chunk

## RT-003: Progressive Classification Confidence Calculation

### Decision

**Layered confidence scoring: hard signals (1.0) → content analysis (0.7-0.9) → LLM (0.6-0.9) → user (<0.7)**

### Rationale

- Progressive classification balances automation with oversight
- Hard signals (path, filename, vendor markers) provide high confidence
- Content analysis (title, TOC, headings) provides medium confidence
- LLM classification fills gaps but with lower certainty
- User confirmation required below 0.70 threshold

### Implementation Notes

```python
def calculate_confidence(document: Document) -> float:
    scores = []

    # Layer 1: Hard signals (weight: 1.0)
    if path_contains_domain(document.path):
        scores.append(1.0)
    if filename_has_vendor_marker(document.filename):
        scores.append(1.0)

    # Layer 2: Content analysis (weight: 0.8)
    if title_contains_keywords(document.title):
        scores.append(0.8)
    if toc_structure_match(document.toc):
        scores.append(0.8)

    # Layer 3: LLM classification (weight: 0.6-0.9)
    llm_result = llm_classify(document)
    scores.append(llm_result.confidence * 0.7)

    return max(scores)  # Best signal wins
```

### Confidence Bands

| Confidence | Behavior |
|------------|----------|
| ≥0.85 | Auto-accept (no user prompt) |
| 0.70-0.84 | Accept with optional review |
| <0.70 | User confirmation required |

## RT-004: Embedding Models (1024+ Dimensions)

### Decision

**Primary: OpenAI text-embedding-3-large (3072 dim) via OpenRouter**
**Fallback: BAAI bge-large-en-v1.5 (1024 dim) via Ollama (local)**

### Rationale

- OpenAI text-embedding-3-large supports 3072 dimensions (exceeds 1024+ requirement)
- High-quality embeddings for technical content
- OpenRouter provides self-hosted data locality (API only, models external)
- BGE-large provides local fallback with 1024 dimensions
- Alternative: sentence-transformers (rejected - lower quality for technical docs)

### Model Specifications

| Model | Dimensions | Provider | Use Case |
|-------|------------|----------|----------|
| text-embedding-3-large | 3072 | OpenRouter (OpenAI) | Primary (high quality) |
| bge-large-en-v1.5 | 1024 | Ollama (local) | Fallback (offline) |

### Configuration

```python
# Environment variables
EMBEDDING_MODEL=openai # or ollama
EMBEDDING_DIMENSION=3072 # or 1024 for BGE
OPENROUTER_API_KEY=sk-...
OLLAMA_BASE_URL=http://localhost:11434
```

## RT-005: Conflict Detection in Graph Databases

### Decision

**Cypher query patterns for same-entity fact comparison**

### Rationale

- Neo4j Cypher (or FalkorDB) enables efficient graph traversal
- Conflict detection: find Facts with same entity + type but different values
- Provenance tracking enables conflict visualization
- Time-scoped metadata (valid_until) enables temporal conflict detection

### Implementation Notes

```cypher
// Find conflicting facts
MATCH (f1:Fact), (f2:Fact)
WHERE f1.entity = f2.entity
  AND f1.type = f2.type
  AND f1.value <> f2.value
  AND (f1.valid_until IS NULL OR f1.valid_until > datetime())
  AND (f2.valid_until IS NULL OR f2.valid_until > datetime())
OPTIONAL MATCH (f1)-[:PROVENANCE]->(e1:Evidence)
OPTIONAL MATCH (f2)-[:PROVENANCE]->(e2:Evidence)
RETURN f1, f2, e1, e2
```

### Resolution Strategies

| Strategy | Description |
|----------|-------------|
| detect_only | Flag conflicts, no auto-resolution |
| keep_both | Retain both facts with scope metadata |
| prefer_newest | Accept fact with latest valid_from |
| reject_incoming | Preserve existing fact |

## RT-006: MCP Tool Design for RAG + Knowledge Graph

### Decision

**FastMCP for tool definition, with typed input/output schemas**

### Rationale

- FastMCP provides clean Python decorator-based tool definition
- Type schemas enable Claude Code to understand tool semantics
- Tools follow MCP specification for parameter passing
- Separate tools for RAG vs KG operations (clear separation of concerns)

### Tool Schemas

```python
from fastmcp import FastMCP

mcp = FastMCP("lkap")

@mcp.tool()
def rag_search(query: str, filters: dict[str, Any] = {}) -> list[SearchResult]:
    """Search document chunks using semantic similarity.

    Args:
        query: Natural language search query
        filters: Optional filters (domain, type, component, project, version)

    Returns:
        List of search results with chunk text, source, confidence
    """
    ...

@mcp.tool()
def rag_get_chunk(chunk_id: str) -> Chunk:
    """Fetch exact document chunk by ID.

    Args:
        chunk_id: Unique chunk identifier

    Returns:
        Chunk with text, metadata, provenance
    """
    ...

@mcp.tool()
def kg_promote_from_evidence(
    evidence_id: str,
    fact_type: FactType,
    value: str
) -> Fact:
    """Promote evidence chunk to Knowledge Graph fact.

    Args:
        evidence_id: Source chunk identifier
        fact_type: Type of fact (Constraint, Erratum, API, etc.)
        value: Fact value

    Returns:
        Created Fact with provenance links
    """
    ...
```

### Tool Naming Convention

- RAG tools: `rag.*` (rag.search, rag.getChunk)
- KG tools: `kg.*` (kg.promoteFromEvidence, kg.reviewConflicts)
- Clear separation helps users understand tool scope

## Summary of Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| RAGFlow Integration | HTTP REST API | No official SDK, simple HTTP client |
| PDF Parsing | Docling | Best PDF structure preservation |
| Chunking | Heading-aware, 512-768 tokens | Semantic coherence + spec requirements |
| Classification | Progressive layers | Balance automation with oversight |
| Embeddings | OpenAI 3-large (3072 dim) primary | High quality, meets 1024+ requirement |
| Local Embeddings | BGE-large (1024 dim) fallback | Offline capability |
| Conflict Detection | Cypher patterns | Leverage graph DB capabilities |
| MCP Tools | FastMCP | Clean Python API, type-safe |

## Next Steps

Phase 1 will use these decisions to create:
- Data model with entities and relationships
- API contracts (MCP tool schemas)
- Quickstart guide with user workflows
