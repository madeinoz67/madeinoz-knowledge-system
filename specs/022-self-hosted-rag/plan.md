# Implementation Plan: Local Knowledge Augmentation Platform (LKAP)

**Branch**: `022-self-hosted-rag` | **Date**: 2026-02-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/022-self-hosted-rag/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

LKAP is a local-first, self-hosted knowledge platform combining RAG (Retrieval-Augmented Generation) with a durable Knowledge Graph. The system automatically ingests technical documents (PDFs, markdown, text), performs confidence-based classification, provides semantic search with citations, and enables evidence-bound promotion of facts into long-lived knowledge. Key technical approach: Docling for PDF conversion, RAGFlow for vector storage, Ollama/OpenRouter for embeddings and LLM, existing Graphiti knowledge graph for durable facts, Bun-based MCP server for Claude integration.

## Technical Context

**Language/Version**: Python 3.11+ (Docker container for MCP server), Bun/TypeScript (CLI tools)
**Primary Dependencies**: Docling (PDF ingestion), RAGFlow (vector DB + search), Ollama (local embeddings/LLM, optional), Graphiti (knowledge graph), FastMCP (MCP protocol)
**Storage**: Neo4j (default) or FalkorDB (knowledge graph), RAGFlow vector DB (embeddings), Local filesystem (documents: inbox/, processed/)
**Testing**: pytest (Python), bun test (TypeScript), integration tests with running containers
**Target Platform**: Linux/macOS (self-hosted containers via Podman/Docker)
**Project Type**: Web service (MCP server) + CLI tools
**Performance Goals**: Ingestion: 100 docs in 5 min; Search: <500ms typical queries; Classification: ≥85% auto-accept rate
**Constraints**: ALL data stored locally on-premise; Models use external APIs (OpenRouter) for embeddings/LLM; Chunk size: 512-768 tokens by heading; Embeddings: 1024+ dimensions
**Scale/Scope**: Single-user MVP; 10k+ document chunks; 100k facts in knowledge graph

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Container-First Architecture ✅ PASS

- **Requirement**: All services in containers
- **Compliance**: RAGFlow, Ollama, and MCP server will run in containers via docker-compose/podman-compose
- **Evidence**: Existing infrastructure uses `madeinoz-knowledge-net` bridge network; LKAP adds RAGFlow and Ollama containers

### II. Graph-Centric Design ✅ PASS

- **Requirement**: Knowledge as graph of entities and relationships
- **Compliance**: Knowledge Memory tier uses existing Graphiti knowledge graph; Document Memory (RAG) complements with vector search
- **Evidence**: FR-014 to FR-017 specify fact types, provenance tracking, and graph relationships

### III. Zero-Friction Knowledge Capture ✅ PASS

- **Requirement**: Automatic entity extraction, no manual organization
- **Compliance**: Ingestion automatically classifies by domain/type/vendor/component; Promotion from evidence preserves provenance
- **Evidence**: FR-001 (progressive classification), FR-016 (provenance links), User Stories 1 & 3

### IV. Query Resilience ✅ PASS

- **Requirement**: Handle special characters gracefully
- **Compliance**: Knowledge Graph tier uses existing Graphiti (Neo4j Cypher or FalkorDB with Lucene sanitization)
- **Evidence**: Existing system handles hyphenated identifiers (apt-28, etc.); RAG queries use standard vector search

### V. Graceful Degradation ✅ PASS

- **Requirement**: Fail gracefully when dependencies unavailable
- **Compliance**: FR-036a (basic logging), user-managed backups; Models flexible (Ollama local fallback)
- **Evidence**: System supports offline operation after initial setup; Ingestion is atomic with rollback (FR-009)

### VI. Codanna-First Development ⚠️ PARTIAL

- **Requirement**: Use Codanna CLI for codebase exploration
- **Compliance**: Will use Codanna for exploring existing Graphiti integration and MCP patterns
- **Action**: During Phase 0 research, use `codanna mcp semantic_search_with_context` to find relevant code patterns

### VII. Language Separation ✅ PASS

- **Requirement**: Python in docker/, TypeScript in src/
- **Compliance**: MCP server extensions in `docker/patches/`; CLI tools in `src/server/`
- **Evidence**: Existing structure followed; LKAP adds Python patches for RAG integration

### VIII. Dual-Audience Documentation ✅ PASS

- **Requirement**: Documentation optimized for humans and AI
- **Compliance**: Will generate AI-friendly summaries and quick reference cards
- **Action**: Phase 1 will include documentation templates with hidden AI summaries

### IX. Observability & Metrics ⚠️ DEFERRED

- **Requirement**: All metrics documented and visualized
- **Compliance**: FR-036a specifies basic logging (errors, ingestion status)
- **Justification**: MVP focuses on basic logging; Full observability (metrics, dashboards) deferred post-MVP per scope boundaries
- **Action**: Post-MVP enhancement to add Prometheus metrics and Grafana dashboards

**Constitution Check Result**: PASS (2 partials with actions defined, no blocking violations)

## Project Structure

### Documentation (this feature)

```text
specs/022-self-hosted-rag/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── mcp-tools.yaml   # MCP tool schemas
│   └── api.yaml         # Internal API contracts
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
docker/                              # Python ecosystem (existing)
├── patches/
│   ├── graphiti_mcp_server.py      # [MODIFY] Add RAG tools
│   ├── ragflow_client.py           # [NEW] RAGFlow integration
│   ├── docling_ingester.py         # [NEW] PDF ingestion with Docling
│   ├── classification.py            # [NEW] Progressive classification
│   ├── promotion.py                # [NEW] Evidence-to-KG promotion
│   └── tests/
│       ├── integration/
│       │   ├── test_rag_ingestion.py
│       │   ├── test_classification.py
│       │   ├── test_promotion.py
│       │   └── test_conflict_detection.py
│       └── unit/
│           ├── test_chunking.py
│           ├── test_confidence.py
│           └── test_provenance.py

docker/
├── docker-compose-ragflow.yml      # [NEW] RAGFlow container
└── Dockerfile                       # [MODIFY] Add Docling, RAGFlow client deps

src/                                 # TypeScript ecosystem (existing)
├── server/
│   ├── rag-cli.ts                   # [NEW] RAG management CLI
│   ├── lib/
│   │   ├── ragflow.ts              # [NEW] RAGFlow client wrapper
│   │   └── types.ts                # [MODIFY] Add RAG types
└── hooks/
    └── sync-rag-to-knowledge.ts     # [NEW] Sync RAG metadata to PAI memory

config/
├── ragflow.yaml                     # [NEW] RAGFlow configuration
└── ontologies/
    └── rag-fact-types.yaml          # [NEW] Fact type definitions

knowledge/                            # [NEW] Document storage
├── inbox/                           # Watch folder for ingestion
└── processed/                       # Canonical document storage
    └── <doc_id>/
        └── <version>/

tests/                               # TypeScript tests
└── integration/
    └── test-rag-workflow.ts
```

**Structure Decision**: Option 1 (Single project with server components). LKAP extends the existing MCP server architecture with new Python patches for RAG integration, adds TypeScript CLI tools for document management, and uses containerized services (RAGFlow, Ollama) for vector storage and embeddings. Language separation maintained: Python in docker/, TypeScript in src/.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Principle | Status | Notes |
|-----------|--------|-------|
| VI. Codanna-First | Partial | Will use Codanna during Phase 0 research; no new complexity added |
| IX. Observability | Deferred | Basic logging in MVP (FR-036a); Full metrics/dashboards post-MVP |
| X. Environment Variables | Pass | All .env variables use MADEINOZ_KNOWLEDGE_ prefix per Technical Constraints |

**No blocking violations.** LKAP extends existing architecture without violating core principles. Observability deferred to post-MVP per scope boundaries (Out of Scope: "Advanced retrieval", "Distributed deployment"). Environment variables follow MADEINOZ_KNOWLEDGE_ prefix convention per constitution Technical Constraints section.

## Phase 0: Research & Technical Decisions

**Output**: [research.md](./research.md)

### Unknowns to Resolve

1. **RAGFlow Integration**: Best practices for RAGFlow Python client, container configuration
2. **Docling PDF Processing**: Chunking strategies for tables/sections, heading-aware split
3. **Classification Confidence**: LLM-based classification prompts, confidence calculation
4. **Embedding Model Selection**: Models supporting 1024+ dimensions (e.g., text-embedding-3-large, BGE-large)
5. **Conflict Detection**: Graph patterns for detecting conflicting facts in Neo4j/FalkorDB
6. **MCP Tool Design**: Tool schemas for rag.search, rag.getChunk, kg.promoteFromEvidence, etc.

### Research Tasks

```text
[RT-001] Research RAGFlow Python client integration patterns
[RT-002] Research Docling document parsing and chunking best practices
[RT-003] Research progressive classification confidence calculation methods
[RT-004] Research embedding models with 1024+ dimensions (local and API options)
[RT-005] Research conflict detection patterns in graph databases
[RT-006] Research MCP tool design for RAG + Knowledge Graph workflows
```

## Phase 1: Design & Contracts

**Outputs**: [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

### Data Model

Extract entities from spec:
- Document (metadata, hash, version tracking)
- DocumentChunk (512-768 tokens, heading-aware)
- Evidence (provenance links)
- Fact (typed, conflict-aware)
- Conflict (resolution strategies)
- IngestionState (processing tracking)
- Classification (confidence bands)

### API Contracts

MCP Tools (to be defined in contracts/mcp-tools.yaml):
- rag.search(query, filters) → SearchResult[]
- rag.getChunk(chunk_id) → Chunk
- kg.promoteFromEvidence(evidence_id, fact_type, value) → Fact
- kg.promoteFromQuery(query, fact_type) → Fact[]
- kg.reviewConflicts() → Conflict[]
- kg.getProvenance(fact_id) → ProvenanceGraph

Internal APIs:
- POST /ingest (document upload trigger)
- GET /documents (list ingested documents)
- GET /classification/{doc_id} (classification details)

### Quickstart Guide

User workflow:
1. Start containers: `bun run server-cli start --rag`
2. Drop documents into `knowledge/inbox/`
3. Auto-classification runs (or review UI if low confidence)
4. Search via Claude: `Use the RAG tool to search for "GPIO interrupts"`
5. Promote facts: `Promote this constraint to the Knowledge Graph`

## Testing Strategy

Per user request "include testing":

### Unit Tests (Python)

```text
docker/patches/tests/unit/
├── test_chunking.py          # Heading-aware chunking, 512-768 token limits
├── test_confidence.py         # Confidence band calculation (≥0.85 auto, <0.70 review)
├── test_classification.py     # Progressive classification layers
└── test_provenance.py         # Evidence-to-fact linking
```

### Integration Tests (Python)

```text
docker/patches/tests/integration/
├── test_rag_ingestion.py     # End-to-end: inbox → processed → RAGFlow
├── test_classification.py     # Classification with review UI trigger
├── test_promotion.py          # Evidence → Knowledge Graph with provenance
└── test_conflict_detection.py # Conflicting fact detection and resolution
```

### Integration Tests (TypeScript)

```text
tests/integration/
└── test-rag-workflow.ts      # CLI tools + MCP server integration
```

### Test Coverage Goals

- Unit tests: ≥80% coverage for core logic (chunking, classification, confidence)
- Integration tests: All P1 user stories covered (ingestion, search, promotion)
- Performance tests: 100 docs in 5 min; Search <500ms

## Success Criteria (from spec)

- SC-001: Local retrieval <500ms
- SC-002: Ingestion: 100 docs in 5 min
- SC-003: ≥85% auto-acceptance rate
- SC-004: <15% user interruptions
- SC-005: ≥0.7 search confidence
- SC-006: 100% provenance links maintained
- SC-007: 95% conflict detection within 24h
- SC-008: 10x fewer facts than chunks (high-signal)
- SC-009: Increasing KG citation rate over time
