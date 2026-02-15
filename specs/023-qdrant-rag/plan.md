# Implementation Plan: Qdrant RAG Migration

**Branch**: `023-qdrant-rag` | **Date**: 2026-02-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/023-qdrant-rag/spec.md`

## Summary

Replace RAGFlow (3.5GB+ with Elasticsearch) with Qdrant (69MB Docker) as the vector database for LKAP. Implement document ingestion using Docling parser with semantic chunking (512-768 tokens, 10-20% overlap), Ollama embeddings (bge-large-en-v1.5, 1024 dimensions), and MCP tools for search/retrieval. Remove all RAGFlow dependencies.

## Technical Context

**Language/Version**: Python 3.11+ (MCP server patches), TypeScript/Bun (CLI tools)
**Primary Dependencies**: Docling (PDF parsing), Qdrant Python client, Ollama Python SDK, FastMCP
**Storage**: Qdrant vector database (Docker container, persistent volume)
**Testing**: pytest (Python), Bun test (TypeScript)
**Target Platform**: Linux server (Docker containers)
**Project Type**: Single project with Python patches + TypeScript CLI
**Performance Goals**: <500ms search latency, 10+ docs/min ingestion throughput
**Constraints**: <200MB RAM for vector DB, 1024-dim embeddings, offline-capable embeddings
**Scale/Scope**: 100,000+ chunks, single-user local deployment

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Container-First | ✅ PASS | Qdrant runs in Docker container with health checks |
| II. Graph-Centric | ✅ PASS | RAG complements graph, doesn't replace it |
| III. Zero-Friction | ✅ PASS | CLI and MCP tools for ingestion, no manual organization |
| IV. Query Resilience | ✅ PASS | Graceful degradation when Qdrant unavailable |
| V. Graceful Degradation | ✅ PASS | Error handling for Qdrant/Ollama unavailability |
| VI. Codanna-First | ✅ PASS | Will use Codanna for codebase exploration |
| VII. Language Separation | ✅ PASS | Python in docker/patches/, TypeScript in src/ |
| VIII. Dual-Audience | ✅ PASS | Documentation will include AI-friendly summaries |
| IX. Observability | ✅ PASS | Will add metrics for ingestion/search |
| X. Environment Prefixing | ✅ PASS | Using MADEINOZ_KNOWLEDGE_QDRANT_* prefix |

**Gate Result**: ✅ All gates passed - proceed to implementation

## Project Structure

### Documentation (this feature)

```text
specs/023-qdrant-rag/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Research decisions
├── data-model.md        # Entity models
├── quickstart.md        # Quick start guide
├── contracts/           # MCP tool contracts
└── tasks.md             # Task list
```

### Source Code (repository root)

```text
docker/
├── patches/
│   ├── qdrant_client.py       # Qdrant client (EXISTS - update)
│   ├── docling_ingester.py    # NEW: Docling-based ingestion
│   ├── semantic_chunker.py    # NEW: Semantic chunking
│   ├── ollama_embedder.py     # NEW: Ollama embedding client
│   └── graphiti_mcp_server.py # UPDATE: Replace RAGFlow imports
├── docker-compose-qdrant.yml  # NEW: Qdrant container
└── Dockerfile                 # UPDATE: Add Docling deps

src/
├── skills/server/lib/
│   ├── rag-cli.ts             # UPDATE: Use Qdrant endpoints
│   └── qdrant.ts              # NEW: TypeScript Qdrant wrapper

config/
├── qdrant.yaml                # NEW: Qdrant configuration
└── .env.example               # UPDATE: Add Qdrant env vars

knowledge/
├── inbox/                     # Documents to ingest
└── processed/                 # Successfully ingested
```

**Structure Decision**: Follows existing project patterns. Python patches in `docker/patches/`, TypeScript CLI in `src/skills/server/lib/`. Respects Principle VII (Language Separation).

## Complexity Tracking

No violations requiring justification. All changes follow existing patterns.
