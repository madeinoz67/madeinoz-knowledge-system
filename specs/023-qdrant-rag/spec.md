# Feature Specification: Qdrant RAG Migration

**Feature Branch**: `023-qdrant-rag`
**Created**: 2026-02-13
**Status**: Draft
**Input**: User description: "Replace RAGFlow with Qdrant as the vector database for LKAP (Feature 022). RAGFlow is too resource-heavy (3.5GB+ with Elasticsearch). Qdrant is lightweight (69MB Docker, 626 QPS, official MCP server). Requirements: (1) Document ingestion pipeline using Docling for parsing + semantic chunking (+9% retrieval improvement) with 512-768 tokens and 10-20% overlap, (2) Ollama embeddings with bge-large-en-v1.5 (1024 dimensions), (3) MCP tools: rag.search, rag.getChunk, rag.ingest, (4) TypeScript CLI wrapper for local operations, (5) Remove all RAGFlow references and docker-compose files, (6) Update existing tests to use Qdrant client instead of RAGFlowClient"

## User Scenarios & Testing

### User Story 1 - Document Ingestion (Priority: P1)

As a knowledge worker, I want to ingest PDF and markdown documents into the vector database so that I can search them later for relevant information.

**Why this priority**: Document ingestion is the foundation of the RAG system. Without documents in the database, search and retrieval are impossible. This is the core capability that enables everything else.

**Independent Test**: Can be fully tested by placing documents in `knowledge/inbox/`, running the ingestion CLI command, and verifying chunks appear in Qdrant with correct embeddings.

**Acceptance Scenarios**:

1. **Given** a PDF document in `knowledge/inbox/`, **When** I run the ingest command, **Then** the document is parsed, chunked, embedded, and stored in Qdrant with metadata (source, page, headings).
2. **Given** a markdown file in `knowledge/inbox/`, **When** I run the ingest command, **Then** the file is parsed with heading awareness, chunked appropriately, and stored with section context.
3. **Given** an already-ingested document, **When** I attempt to re-ingest it, **Then** the system detects the duplicate and skips or updates it (idempotent operation).
4. **Given** a malformed or corrupted document, **When** ingestion is attempted, **Then** the system logs an error and continues with other documents without crashing.

---

### User Story 2 - Semantic Search (Priority: P1)

As a knowledge worker, I want to search my document corpus using natural language queries so that I can find relevant information quickly without knowing exact keywords.

**Why this priority**: Search is the primary user-facing feature of RAG. Users need to retrieve information from their ingested documents. This must work for the system to be useful.

**Independent Test**: Can be fully tested by ingesting sample documents, running search queries via CLI or MCP tool, and verifying relevant chunks are returned with confidence scores above 0.70.

**Acceptance Scenarios**:

1. **Given** documents are ingested, **When** I search for "GPIO configuration on STM32H7", **Then** chunks mentioning GPIO and STM32H7 are returned ranked by relevance.
2. **Given** a search query with no matching documents, **When** I search, **Then** an empty result set is returned (not an error).
3. **Given** documents with metadata filters (domain, project, component), **When** I search with a filter, **Then** only chunks matching the filter are returned.
4. **Given** a search query, **When** results are returned, **Then** each result includes chunk text, source document, page/section, and confidence score.

---

### User Story 3 - Chunk Retrieval (Priority: P2)

As a knowledge worker, I want to retrieve a specific document chunk by its ID so that I can view the full context and provenance of information.

**Why this priority**: Chunk retrieval supports the promotion workflow (evidence to knowledge graph) and allows users to verify source information. Less critical than basic search but essential for the full workflow.

**Independent Test**: Can be fully tested by searching for documents, capturing a chunk ID, and retrieving that chunk directly to verify all metadata is preserved.

**Acceptance Scenarios**:

1. **Given** a valid chunk ID, **When** I retrieve the chunk, **Then** the full chunk content with all metadata (source, page, headings, confidence) is returned.
2. **Given** an invalid chunk ID, **When** I attempt retrieval, **Then** a clear "not found" error is returned.

---

### User Story 4 - MCP Tool Integration (Priority: P2)

As an AI assistant, I want to access RAG capabilities through MCP tools so that I can search documents and retrieve chunks to augment my responses.

**Why this priority**: MCP tools enable AI assistants (like Claude) to use the RAG system. This is the integration point that makes the knowledge accessible to AI workflows.

**Independent Test**: Can be fully tested by calling the MCP tools from a client and verifying search results and chunk retrieval work correctly.

**Acceptance Scenarios**:

1. **Given** the MCP server is running, **When** I call `rag.search` with a query, **Then** matching chunks are returned with metadata.
2. **Given** the MCP server is running, **When** I call `rag.getChunk` with a chunk ID, **Then** the chunk is returned.
3. **Given** the MCP server is running, **When** I call `rag.ingest` with a file path, **Then** the document is ingested and chunks are created.

---

### User Story 5 - RAGFlow Removal (Priority: P3)

As a system administrator, I want all RAGFlow dependencies removed so that the system is lightweight and resource-efficient.

**Why this priority**: Cleanup is important for maintainability but doesn't block core functionality. Can be done after Qdrant is working.

**Independent Test**: Can be fully tested by verifying no RAGFlow imports, no RAGFlow docker-compose files, and all tests pass with Qdrant.

**Acceptance Scenarios**:

1. **Given** the migration is complete, **When** I search the codebase for "ragflow", **Then** no references remain (except in migration documentation).
2. **Given** the migration is complete, **When** I run `docker compose config`, **Then** no RAGFlow containers are defined.

---

### Edge Cases

- What happens when Qdrant is unavailable? → System should return a clear error and log the connection failure.
- What happens when Ollama is unavailable for embeddings? → System should fall back to OpenRouter embeddings or return an error with clear guidance.
- What happens when a document exceeds maximum size? → System should chunk the document and process each chunk independently.
- What happens when embedding dimension mismatches (e.g., different model)? → System should detect mismatch and reject with clear error message.

## Requirements

### Functional Requirements

- **FR-001**: System MUST ingest PDF documents using Docling parser with table extraction support
- **FR-002**: System MUST ingest markdown and plain text files with heading-aware parsing
- **FR-003**: System MUST chunk documents into 512-768 token segments with 10-20% overlap
- **FR-004**: System MUST preserve document metadata: source filename, page number, section headings
- **FR-005**: System MUST generate 1024-dimensional embeddings using Ollama with bge-large-en-v1.5 model
- **FR-006**: System MUST store chunks and embeddings in Qdrant vector database
- **FR-007**: System MUST provide semantic search returning chunks ranked by relevance
- **FR-008**: System MUST filter search results by metadata: domain, project, component, document type
- **FR-009**: System MUST return confidence scores with search results (threshold: 0.70)
- **FR-010**: System MUST provide chunk retrieval by unique chunk ID
- **FR-011**: System MUST expose `rag.search` MCP tool for semantic search
- **FR-012**: System MUST expose `rag.getChunk` MCP tool for chunk retrieval
- **FR-013**: System MUST expose `rag.ingest` MCP tool for document ingestion
- **FR-014**: System MUST provide TypeScript CLI wrapper with commands: search, get-chunk, ingest, health
- **FR-015**: System MUST remove all RAGFlow client code and docker-compose configurations
- **FR-016**: System MUST update existing tests to use Qdrant client instead of RAGFlowClient
- **FR-017**: System MUST support idempotent ingestion (re-ingesting same document updates, not duplicates)
- **FR-018**: System MUST provide health check endpoint for Qdrant connectivity

### Non-Functional Requirements

- **NFR-001**: Search latency MUST be under 500ms for typical queries
- **NFR-002**: Ingestion throughput MUST handle at least 10 documents per minute
- **NFR-003**: Qdrant container MUST use under 200MB RAM (vs 3.5GB+ for RAGFlow)
- **NFR-004**: System MUST support at least 100,000 chunks without performance degradation

### Key Entities

- **Document**: Source file (PDF, markdown, text) with metadata (filename, type, domain, project, ingested_at)
- **Chunk**: Text segment from a document with: chunk_id, text, token_count, page_number, section_headings, source_document_id
- **Embedding**: 1024-dimensional vector representation of chunk text for semantic search
- **SearchResult**: Chunk with relevance score, metadata, and source document reference

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can ingest a 50-page PDF document in under 30 seconds
- **SC-002**: Search queries return relevant results in under 500ms
- **SC-003**: System memory footprint reduced by 95% (from 3.5GB to under 200MB for vector DB)
- **SC-004**: All 365 existing tests pass after migration
- **SC-005**: MCP tools respond successfully to search, getChunk, and ingest operations
- **SC-006**: Zero references to RAGFlow in codebase after migration
- **SC-007**: Document retrieval accuracy maintained or improved (semantic chunking provides +9% improvement)

## Dependencies

- **Docling**: Python library for PDF/document parsing
- **Qdrant**: Vector database (Docker image: qdrant/qdrant)
- **Ollama**: Local embedding model server with bge-large-en-v1.5
- **FastMCP**: MCP protocol implementation for Python
- **Existing QdrantClient**: Already implemented in `docker/patches/qdrant_client.py`

## Assumptions

- Ollama is available locally or via configured endpoint
- Documents are stored in `knowledge/inbox/` for ingestion
- Processed documents are moved to `knowledge/processed/`
- Qdrant runs in a Docker container accessible via HTTP API
- Embedding model produces 1024-dimensional vectors (bge-large-en-v1.5)

## Out of Scope

- RAGFlow web UI replacement (no visual chunk editor)
- Distributed Qdrant cluster (single node sufficient)
- Real-time document watching (manual ingestion trigger)
- Document version control (handled by filesystem)
