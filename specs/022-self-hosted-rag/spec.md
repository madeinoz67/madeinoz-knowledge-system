# Feature Specification: Local Knowledge Augmentation Platform (LKAP)

**Feature Branch**: `022-self-hosted-rag`
**Created**: 2026-02-09
**Status**: Draft
**Input**: PRD.md (Product Requirements Document)

## Overview

The Local Knowledge Augmentation Platform (LKAP) is a local-first, self-hosted knowledge platform that combines Retrieval-Augmented Generation (RAG) with a durable Knowledge Graph. It automatically ingests technical documents, provides citation-backed retrieval, and enables evidence-bound promotion of facts into long-lived knowledge.

**Key Value Proposition**: LKAP treats documents as evidence (transient, noisy, versioned) and knowledge as curated truth (durable, typed, conflict-aware). Users are validators, not data entry clerks. The system is fast when confident, careful when uncertain, and always explicit about provenance.

**Two-Tier Memory Model**:
- **Document Memory (RAG)**: High-volume, versioned, citation-centric, short-lived relevance
- **Knowledge Memory (KG)**: Low-volume, high-signal, typed, version-aware, long-lived

## Clarifications

### Session 2026-02-09

- Q: What is the target chunk size (in tokens) for document splitting? → A: 512-768 tokens balanced, respecting document heading boundaries
- Q: What level of observability should the system provide? → A: Basic logs only (errors, ingestion status)
- Q: What backup and recovery strategy should the self-hosted system support? → A: User-managed backups (export scripts, manual snapshots)
- Q: Should the system support fully offline operation? → A: System self-hosted (not online), LLM models flexible (OpenRouter external or Ollama local), ALL data stored locally on-premise
- Q: What is the target embedding vector dimension for the system? → A: 1024+ dimensions (high quality, larger storage)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Document Ingestion (Priority: P1)

User drops technical documents (PDFs, SDK docs, standards, detections, reports) into an inbox folder. System automatically classifies them by domain, type, vendor, and component with minimal user intervention.

**Why this priority**: Ingestion is the foundation. Without automatic document processing, the system has no content to index or retrieve.

**Independent Test**: Can be fully tested by dropping sample documents into the inbox, verifying automatic classification occurs, and confirming files are moved to processed storage with proper metadata.

**Acceptance Scenarios**:

1. **Given** a PDF document in the inbox, **When** the filesystem watcher triggers, **Then** document is converted to structured format, classified by domain/type/vendor, and moved to processed storage
2. **Given** a document with high-confidence classification (≥0.85), **When** processed, **Then** system auto-accepts without user prompt
3. **Given** a document with low-confidence classification (<0.70), **When** processed, **Then** system presents one-screen review UI for confirmation
4. **Given** a document that was already ingested (same hash), **When** detected again, **Then** system skips re-processing (idempotent)
5. **Given** 100 documents dropped simultaneously, **When** processed, **Then** all complete within 5 minutes with proper concurrency handling

---

### User Story 2 - Semantic Search and Evidence Retrieval (Priority: P1)

User searches for technical information using natural language queries. System returns relevant document chunks with citations, confidence scores, and supporting metadata.

**Why this priority**: Search is the primary interface to document memory. Without retrieval, ingested documents are inaccessible.

**Independent Test**: Can be fully tested by indexing a corpus of technical documents, running semantic queries across different domains, and verifying relevant chunks are returned with proper attribution.

**Acceptance Scenarios**:

1. **Given** indexed documents about embedded development, **When** user searches "how to configure GPIO interrupts", **Then** system returns relevant chunks with source document, page/section, and confidence >0.7
2. **Given** a search query, **When** results are returned, **Then** each chunk includes text, source document, page/section, confidence score, and metadata filters
3. **Given** a query across multiple domains, **When** executed, **Then** results can be filtered by domain, document type, component, project, or version
4. **Given** a search with no high-quality matches, **When** executed, **Then** system returns empty results rather than low-confidence noise

---

### User Story 3 - Evidence-Based Knowledge Promotion (Priority: P1)

User promotes high-value facts from document evidence into the durable Knowledge Graph. Facts are typed, conflict-aware, and permanently linked to their source evidence.

**Why this priority**: Promotion is the bridge between transient documents and durable knowledge. Without it, the system is just another RAG tool.

**Independent Test**: Can be fully tested by searching for evidence, promoting a fact to the Knowledge Graph, and verifying the fact appears in graph queries with provenance links.

**Acceptance Scenarios**:

1. **Given** a document chunk containing a constraint (e.g., "max clock frequency is 120MHz"), **When** user promotes this fact, **Then** system stores typed fact with link to evidence chunk and original document
2. **Given** a promoted fact, **When** querying the Knowledge Graph, **Then** system returns fact with provenance subgraph showing source chunk and document
3. **Given** conflicting facts (e.g., "120MHz" vs "150MHz" for same component), **When** detected, **Then** system stores conflict explicitly and presents resolution options
4. **Given** a promoted fact, **When** original document is updated, **Then** system can detect version changes and flag affected facts for review

---

### User Story 4 - Ingestion Review and Classification Override (Priority: P2)

System presents a calm, single-screen review interface when classification confidence is low. User can review evidence, override classifications, and provide corrections that the system learns from.

**Why this priority**: Reduces friction for high-confidence cases while providing oversight when needed. Works without it, but UX suffers.

**Independent Test**: Can be tested by triggering low-confidence classifications, verifying review UI appears with correct information, and confirming corrections are applied and remembered.

**Acceptance Scenarios**:

1. **Given** a document with classification confidence 0.65, **When** processed, **Then** system shows review UI with document summary, classification, confidence band, evidence preview, and action buttons
2. **Given** the review UI, **When** user overrides classification, **Then** system applies new metadata and remembers correction for future documents from same source
3. **Given** the review UI, **When** user clicks "Accept and Ingest", **Then** system proceeds with ingestion using suggested metadata
4. **Given** the review UI, **When** user clicks "Cancel", **Then** system leaves document in inbox for manual intervention

---

### User Story 5 - Conflict Resolution and Provenance Tracking (Priority: P3)

User reviews conflicting facts in the Knowledge Graph, traces provenance to source documents, and applies resolution strategies (detect only, keep both with scope, prefer newest, reject incoming).

**Why this priority**: Advanced feature. Core functionality works without manual conflict resolution, but long-term usability requires it.

**Independent Test**: Can be tested by promoting conflicting facts, triggering conflict detection, and applying resolution strategies to verify proper behavior.

**Acceptance Scenarios**:

1. **Given** conflicting facts for the same entity, **When** detected, **Then** system stores conflict explicitly and surfaces in conflict review tool
2. **Given** a conflict, **When** user chooses "Keep both with scope", **Then** system retains both facts with scope metadata (e.g., "version 1.0 only")
3. **Given** a fact in the Knowledge Graph, **When** user requests provenance, **Then** system returns subgraph showing fact, evidence chunks, and original documents
4. **Given** resolved conflicts, **When** new evidence arrives, **Then** system can re-evaluate based on resolution strategy

---

### Edge Cases

- What happens when ingestion fails mid-process (partial chunks, database error)?
- How does system handle documents with no clear domain classification?
- What happens when PDF contains only images/scanned content (no extractable text)?
- How does system handle very large documents (>1000 pages)?
- What happens when vector database storage is exhausted?
- How does system handle concurrent promotion of the same fact by multiple users?
- What happens when a promoted fact's source document is deleted or updated?
- How does system handle documents with conflicting internal metadata?
- What happens when embedding model fails or times out?
- How does system handle special characters, Unicode, or right-to-left text in documents?

## Requirements *(mandatory)*

### Functional Requirements

#### Ingestion (FR-001 to FR-004)
- **FR-001**: System MUST automatically classify documents by domain, document type, vendor, and component using progressive classification (hard signals, content analysis, LLM-assisted, user confirmation)
- **FR-002**: System MUST assign confidence scores to each classification and trigger review UI when confidence <0.70
- **FR-002a**: System MUST split documents into chunks of 512-768 tokens, respecting document heading boundaries for semantic coherence
- **FR-003**: System MUST auto-accept classifications with confidence ≥0.85 without user intervention
- **FR-004**: System MUST freeze metadata after successful ingestion and move files from inbox to processed storage
- **FR-005**: System MUST support idempotent ingestion based on document hash (skip if already processed)
- **FR-006**: System MUST convert PDFs to structured format (Markdown/JSON) preserving tables, sections, and errata
- **FR-007**: System MUST watch the inbox folder for new files and trigger ingestion on detection
- **FR-008**: System MUST support scheduled reconciliation (e.g., nightly) as secondary ingestion trigger
- **FR-009**: System MUST handle ingestion atomically (all-or-nothing per document with rollback on failure)

#### Retrieval (FR-010 to FR-013)
- **FR-010**: System MUST support semantic search queries that return top-k most similar document chunks
- **FR-011**: System MUST return search results with chunk text, source document, page/section, confidence score, and metadata
- **FR-012**: System MUST support filtering search results by domain, document type, component, project, and version
- **FR-013**: System MUST complete local retrieval in under 500ms for typical queries

#### Knowledge Promotion (FR-014 to FR-017)
- **FR-014**: System MUST support promotion of typed facts from evidence chunks or search queries
- **FR-015**: System MUST support fact types: Constraint, Erratum, Workaround, API, BuildFlag, ProtocolRule, Detection, Indicator
- **FR-016**: System MUST link every promoted fact to its source evidence chunk and original document
- **FR-017**: System MUST return provenance subgraphs on request (fact → evidence → document)

#### Conflict Handling (FR-018 to FR-021)
- **FR-018**: System MUST detect conflicting facts for the same entity or constraint
- **FR-019**: System MUST store conflicts explicitly in the Knowledge Graph
- **FR-020**: System MUST support conflict resolution strategies: detect only, keep both with scope, prefer newest, reject incoming
- **FR-021**: System MUST allow reversible promotion (facts can be deprecated or removed)

#### MCP Interface (FR-022 to FR-027)
- **FR-022**: System MUST expose `rag.search` tool for evidence retrieval
- **FR-023**: System MUST expose `rag.getChunk` tool for fetching exact chunks by ID
- **FR-024**: System MUST expose `kg.promoteFromEvidence` tool for promoting from specific evidence
- **FR-025**: System MUST expose `kg.promoteFromQuery` tool for searching and promoting in one operation
- **FR-026**: System MUST expose `kg.reviewConflicts` tool for conflict detection and resolution
- **FR-027**: System MUST expose `kg.getProvenance` tool for tracing fact provenance

#### Metadata and Taxonomy (FR-028 to FR-032)
- **FR-028**: System MUST use domain-first, project-overlay taxonomy (domain defines what, project defines where)
- **FR-029**: System MUST infer default metadata from directory structure while allowing explicit override
- **FR-030**: System MUST include confidence score and signal sources with each inferred metadata field
- **FR-031**: System MUST support sensitivity tagging for security-specific documents
- **FR-032**: System MUST support time-scoped metadata (observed_at, published_at, valid_until, TTL) for security indicators

#### Security-Specific (FR-033 to FR-036)
- **FR-033**: System MUST support optional retention policies for indicators of compromise
- **FR-034**: System MUST maintain separation between document storage and operational data
- **FR-035**: System MUST support version-aware and conflict-aware knowledge for time-sensitive security data
- **FR-036**: System MUST be self-hosted with all data (documents, embeddings, knowledge graph) stored locally on-premise
- **FR-036a**: System MUST support LLM models hosted externally (e.g., OpenRouter) or locally (e.g., Ollama), with data never leaving on-premise storage
- **FR-036b**: System MUST provide basic logging for errors and ingestion status
- **FR-036c**: System MUST support user-managed backups through export scripts and manual snapshots

### Key Entities

- **Document**: Source file with metadata (doc_id, hash, filename, domain, type, vendor, component, version, projects, sensitivity, upload_date)
- **DocumentChunk**: Segment of document content (chunk_id, doc_id, text, page/section, token_count, embedding_vector[1024+])
- **Evidence**: Reference to document chunk used as fact source (evidence_id, chunk_id, fact_ids, confidence)
- **Fact**: Typed knowledge in Knowledge Graph (fact_id, type, entity, value, scope, version, valid_until, conflict_id, evidence_ids)
- **Conflict**: Detected contradiction between facts (conflict_id, fact_ids, detection_date, resolution_strategy, status)
- **IngestionState**: Processing status (doc_id, status, confidence_band, chunks_processed, error_message, last_update)
- **Classification**: Metadata inference result (field_name, value, confidence, signal_sources, user_override)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Local document retrieval completes in under 500ms for typical queries
- **SC-002**: Document ingestion completes within 5 minutes for batches up to 100 documents
- **SC-003**: System achieves ≥85% auto-acceptance rate (confidence ≥0.85) for domain-classified documents
- **SC-004**: User interruptions during ingestion are <15% (only when confidence <0.70)
- **SC-005**: Semantic search achieves ≥0.7 average confidence score on domain-specific test queries
- **SC-006**: 100% of promoted facts maintain provenance links to source evidence and documents
- **SC-007**: Conflict detection identifies 95% of contradictory facts within 24 hours of promotion
- **SC-008**: Knowledge Graph contains at least 10x fewer facts than document chunks (high-signal curation)
- **SC-009**: Claude answers are increasingly backed by Knowledge Graph facts (measured by provenance citation rate)

## Assumptions

- Docling will be used for PDF-to-structured conversion (tables, sections, errata preservation)
- RAGFlow will provide RAG indexing and retrieval capabilities
- Ollama will provide local embeddings and optional local LLM for classification
- Existing Graphiti knowledge graph system will be extended for Knowledge Memory tier
- Bun-based MCP server will wrap all capabilities for Claude integration
- Single-user workflows initially (multi-user support out of MVP scope)
- Documents are primarily text-based (OCR for scanned images out of MVP scope)
- Domain classification follows technical domains: embedded, software, security, cloud, standards

## Dependencies

- Existing Graphiti knowledge graph system (Neo4j/FalkorDB backend)
- MCP server infrastructure for tool exposure
- Docling for PDF ingestion and conversion
- RAGFlow for vector storage and semantic search
- Ollama for local embeddings and classification
- Filesystem watcher for inbox monitoring
- Bun runtime for MCP server

## Scope Boundaries

### In Scope (MVP)
- Automatic document ingestion with classification
- Docling-based PDF conversion to structured format
- RAGFlow for semantic search and retrieval
- MCP wrapper exposing all capabilities
- One-screen ingestion review UI for low-confidence cases
- Knowledge promotion with evidence links
- Typed facts: Constraint, Erratum, API (additional types post-MVP)
- Conflict detection and manual resolution
- Provenance tracking for all facts
- Local-first, self-hosted deployment
- Single-user workflows

### Out of Scope (Post-MVP)
- Visual diagram semantic understanding
- Autonomous conflict resolution without human oversight
- Multi-user workflows and collaboration
- OCR for scanned PDFs or images
- Web-based document management UI (CLI + review screen only)
- Real-time document synchronization from external sources
- Distributed deployment for high availability
- Advanced retrieval (reranking, hybrid search, query expansion)
- Additional fact types beyond Constraint, Erratum, API (Workaround, BuildFlag, ProtocolRule, Detection, Indicator)
