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

## RT-002: Docling Document Parsing and Chunking (UPDATED)

### Decision

**Use Docling HybridChunker for token-aware, heading-aware chunking**

### Rationale

- Docling provides excellent PDF parsing with table, section, and errata preservation
- HybridChunker provides token-aware chunking with automatic heading hierarchy tracking
- Heading awareness is built-in (not configurable) via document structure traversal
- Alternative: LangChain text splitters (rejected - less PDF structure awareness)

### Implementation Notes (UPDATED)

```python
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from transformers import AutoTokenizer

# Tokenizer for chunk size estimation
tokenizer = HuggingFaceTokenizer(
    tokenizer=AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2"),
    max_tokens=768,  # CHUNK_SIZE_MAX
)

# HybridChunker automatically tracks heading hierarchy during traversal
chunker = HybridChunker(
    tokenizer=tokenizer,
    merge_peers=True,  # Merge undersized chunks with same headings
)

# Usage
converter = DocumentConverter()
result = converter.convert("document.pdf")
doc = result.document

chunks = list(chunker.chunk(dl_doc=doc))

# Access chunk with heading context
for chunk in chunks:
    print(f"Text: {chunk.text}")
    print(f"Headings: {chunk.meta.headings}")  # List of parent headings
```

### Key Findings from API Research

**NO `ChunkingParams.respect_headings` EXISTS** - The original assumption was incorrect.

Docling's actual chunking API:
- **`HybridChunker`**: Token-aware chunking with heading context
- **`HierarchicalChunker`**: Structure-preserving chunking (one chunk per element)
- Heading hierarchy is **automatically tracked** via `heading_by_level` dict during traversal
- Each chunk includes `chunk.meta.headings` list with parent headings
- `merge_peers=True` merges undersized chunks **only when they share the same heading**

### Chunking Strategy

1. Parse PDF with Docling → DLDocument object
2. **Docling automatically tracks heading hierarchy** (H1 → H2 → H3) via `SectionHeaderItem.level`
3. HybridChunker creates **token-aligned chunks** with heading metadata attached
4. Chunk metadata includes `headings` list for provenance tracking
5. **`merge_peers=True`** prevents tiny chunks by merging same-heading content
6. **Overlap** is implicit (not configurable) via merge behavior

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
# OLLAMA_BASE_URL is OPTIONAL - Ollama container uses default http://localhost:11434
# When running in docker-compose, Ollama is accessible at http://ollama:11434
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

## RT-007: Lightweight RAG Alternatives to RAGFlow

### Decision

**Evaluate RAGFlow alternatives for <4GB RAM deployments**

### Rationale

RAGFlow requires 16GB+ RAM with 4-container stack (ES + MySQL + MinIO + Redis). For resource-constrained environments (edge devices, home labs, minimal VMs), lighter alternatives exist with 1-2 container deployments and <4GB RAM requirements.

### Comparative Analysis (2025)

| Solution | Containers | Min RAM | Rec RAM | Infrastructure | RAG Features | Deployment Complexity |
|----------|------------|---------|---------|----------------|--------------|----------------------|
| **RAGFlow** | 4+ | 16GB | 16GB+ | ES + MySQL + MinIO + Redis | Full pipeline, UI, chunking | High (docker-compose) |
| **Qdrant** | 1 | 1GB | 4GB | Standalone (Rust) | Vector search, filtering | Low (single image) |
| **ChromaDB** | 1 | 4GB | 8GB | Embedded (Python/Rust) | Vector search, metadata | Low (pip/Docker) |
| **LanceDB** | 1 | 1GB | 2GB | Embedded (Rust/Python) | Vector search, hybrid | Low (pip/Docker) |
| **pgvector** | 1 | 2GB | 8GB | PostgreSQL extension | SQL + vectors, FTS | Medium (Postgres req) |
| **sqlite-vec** | 0 | <100MB | 512MB | SQLite extension | SQL + vectors, FTS | Very Low (pip only) |
| **Milvus** | 3+ | 8GB | 16GB+ | etcd + MinIO + standalone | Vector search, distributed | High (kube/docker) |
| **Weaviate** | 1 | 8GB | 16GB+ | Standalone (Go) | Vector search, GraphQL | Medium (single image) |
| **LightRAG** | 1 | 4GB | 8GB | Python + Ollama | Knowledge graph RAG | Medium (docker-compose) |

### Detailed Findings by Solution

#### Qdrant (Best Balance: Performance vs Resources)

**Infrastructure:**
- Single Rust-based container (qdrant/qdrant)
- Disk-based with optional in-memory acceleration
- Built-in quantization reduces RAM by 97%

**Resource Requirements:**
- Minimum: 1GB RAM, 0.5 cores
- Recommended: 4GB RAM, 2 cores
- Serves 1M vectors in ~1.2GB RAM

**RAG Features:**
- Semantic search with filtering
- Hybrid search (vector + keyword)
- Payload indexing
- REST/gRPC APIs

**Deployment:**
```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    deploy:
      resources:
        limits:
          memory: 4G
```

**Sources:**
- [Qdrant Installation](https://qdrant.tech/documentation/guides/installation/)
- [Qdrant Memory Consumption](https://qdrant.tech/articles/memory-consumption/)

#### LanceDB (Lightest: Disk-Based Embedded)

**Infrastructure:**
- Embedded library (no server required) or standalone container
- Lance columnar storage format (Parquet-like)
- Serverless deployment to AWS Lambda (96MB RAM possible)

**Resource Requirements:**
- Minimum: 96MB (serverless), 1GB (container)
- Recommended: 2GB RAM
- Typical Docker: 800MB - 1.6GB RAM

**RAG Features:**
- Vector search with HNSW
- Full-text search (hybrid)
- Multi-modal support (text, images, vectors)
- Python/TypeScript/JavaScript SDKs

**Deployment:**
```bash
# Embedded (no container)
pip install lancedb

# Docker
docker run -p 8080:8080 lancedb/lancedb
```

**Sources:**
- [LanceDB Official Site](https://lancedb.com/)
- [LanceDB GitHub](https://github.com/lancedb/lancedb)

#### ChromaDB (Simplest: Local Development)

**Infrastructure:**
- Embedded (Python) or Docker container
- In-memory by default, persistent option available
- Database size limited by available RAM

**Resource Requirements:**
- Minimum: 4GB RAM
- Recommended: 8GB RAM
- Database cannot grow larger than system RAM

**RAG Features:**
- Vector search with metadata filtering
- Simple Python API
- LangChain/LlamaIndex integration

**Deployment:**
```bash
# Docker
docker run -p 8000:8000 chromadb/chroma

# Embedded
pip install chromadb
```

**Sources:**
- [ChromaDB Docker Guide](https://www.quantlabsnet.com/post/chromadb-docker-complete-guide-to-vector-database-implementation-and-container-deployment)
- [ChromaDB Docs](https://docs.trychroma.com/docs/overview/migration)

#### sqlite-vec (Minimalist: Single-File RAG)

**Infrastructure:**
- SQLite extension (no separate database)
- Single-file database with vector search
- FTS5 full-text search included

**Resource Requirements:**
- Minimum: <100MB RAM overhead
- Recommended: 512MB - 1GB RAM
- Zero additional infrastructure

**RAG Features:**
- Vector similarity search
- Full-text search (FTS5)
- Hybrid search possible
- Serverless operation

**Deployment:**
```bash
# Load extension in SQLite
pip install sqlite-vec
```

**Sources:**
- [Building a RAG on SQLite](https://blog.sqlite.ai/building-a-rag-on-sqlite)
- [sqlite-rag GitHub](https://github.com/sqliteai/sqlite-rag)

#### pgvector (SQL-Native: Extension + PostgreSQL)

**Infrastructure:**
- PostgreSQL extension
- Leverages existing Postgres infrastructure
- Index must fit in RAM for performance

**Resource Requirements:**
- Minimum: 2GB RAM
- Recommended: 8-16GB RAM
- 1M vectors requires ~656MB RAM for index

**RAG Features:**
- Vector similarity search
- SQL queries + vectors
- Full-text search (tsvector)
- ACID compliance

**Deployment:**
```bash
# Docker with pgvector
docker run -p 5432:5432 \
  -e POSTGRES_PASSWORD=password \
  pgvector/pgvector:pg16
```

**Sources:**
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [PostgreSQL pgvector Setup](https://thedbadmin.com/blog/postgresql-pgvector-setup-guide)

#### LightRAG (Graph-Enhanced: Knowledge Graph RAG)

**Infrastructure:**
- Python-based with Ollama integration
- Knowledge graph generation included
- Single container or pip install

**Resource Requirements:**
- Minimum: 4GB RAM
- Recommended: 8GB RAM
- Requires Ollama for embeddings/LLM

**RAG Features:**
- Knowledge graph extraction
- Graph-based retrieval
- Local LLM support via Ollama
- Hybrid (graph + vector) search

**Deployment:**
```bash
# pip
pip install lightrag

# Docker with Ollama
docker compose up  # lightrag + ollama
```

**Sources:**
- [LightRAG GitHub](https://github.com/HKUDS/LightRAG)
- [LightRAG Docker Deployment](https://www.cnblogs.com/JentZhang/p/18801719)

### RAGFlow Stack Comparison

**RAGFlow Infrastructure (Heavy):**
| Component | Purpose | Resource Impact |
|-----------|---------|-----------------|
| Elasticsearch | Full-text search + vector | ~4-8GB RAM |
| MySQL | Metadata storage | ~2-4GB RAM |
| MinIO | Object storage (files) | ~1-2GB RAM |
| Redis | Caching | ~512MB-1GB RAM |
| RAGFlow API | RAG pipeline | ~2-4GB RAM |
| **Total** | | **~16GB+ RAM** |

**Sources:**
- [RAGFlow Configuration](https://ragflow.io/docs/configurations)
- [RAGFlow GitHub README](https://github.com/infiniflow/ragflow/blob/main/README.md)

### Strategic Recommendations

**For <4GB RAM deployments:**

1. **Primary Choice: LanceDB**
   - Lowest resource footprint (1-2GB RAM)
   - Disk-based (scales beyond RAM)
   - Production-ready with Python SDKs
   - Excellent for edge/container-constrained environments

2. **Secondary Choice: Qdrant**
   - Better performance (Rust, HNSW)
   - Slightly higher RAM (4GB recommended)
   - Quantization for memory reduction
   - Production-grade with official Docker image

3. **Tertiary Choice: sqlite-vec**
   - True minimalism (<100MB overhead)
   - Single-file deployment
   - No separate database server
   - Best for embedded/portable applications

**Migration Considerations:**

If migrating from RAGFlow's full pipeline:
- **Document Ingestion**: Retain Docling for PDF parsing
- **Chunking**: Retain Docling HybridChunker
- **Embeddings**: Retain OpenAI/Ollama strategy
- **Vector Storage**: Replace RAGFlow ES with LanceDB/Qdrant
- **Metadata**: Replace MySQL with vector DB payload/SQLite
- **UI**: Build custom simple API (or skip UI)

**Second-Order Effects:**

- **Simpler Stack**: Fewer moving parts = easier debugging
- **Reduced Features**: Lose RAGFlow's visual UI, advanced chunking UI
- **Custom Development**: More code for API layer, monitoring
- **Portability**: Single-container solutions easier to deploy

### Summary Table

| Priority | Solution | RAM | Containers | Best For |
|----------|----------|-----|------------|----------|
| 1 | LanceDB | 1-2GB | 0-1 | Minimal resources, disk-heavy workloads |
| 2 | Qdrant | 1-4GB | 1 | Performance + resource balance |
| 3 | sqlite-vec | <100MB | 0 | Embedded/portable applications |
| 4 | ChromaDB | 4-8GB | 0-1 | Local development |
| 5 | pgvector | 2-16GB | 1 | SQL-heavy workloads |
| X | RAGFlow | 16GB+ | 4+ | Full-featured, UI-driven deployments |

## Next Steps

Phase 1 will use these decisions to create:
- Data model with entities and relationships
- API contracts (MCP tool schemas)
- Quickstart guide with user workflows
