# Quickstart Guide: Local Knowledge Augmentation Platform (LKAP)

**Feature**: 022-self-hosted-rag
**Phase**: 1 - Design & Contracts
**Last Updated**: 2026-02-09

## Overview

LKAP (Local Knowledge Augmentation Platform) automatically ingests technical documents, provides semantic search with citations, and enables evidence-bound promotion of facts to a durable Knowledge Graph. This guide will get you started with the core workflows.

## Prerequisites

- Docker or Podman installed
- Bun runtime installed
- Existing madeinoz-knowledge-system installation
- For local embeddings: Ollama installed (optional)
- For API embeddings: OpenRouter API key (optional)

## Installation

### 1. Start the Knowledge System with RAG

```bash
# Start with RAGFlow and Ollama containers
bun run server-cli start --rag

# Or start with RAGFlow only (using external embeddings via OpenRouter)
bun run server-cli start --rag --external-embeddings
```

This starts:
- Neo4j/FalkorDB (Knowledge Graph)
- RAGFlow (Vector DB for semantic search)
- Ollama (Local embeddings/LLM, if included)
- MCP Server (with LKAP tools)

### 2. Verify Installation

```bash
# Check container status
bun run server-cli status

# Should show:
# - knowledge-graph (Neo4j or FalkorDB): running
# - ragflow (RAGFlow): running
# - ollama (Ollama): running (if included)
# - mcp-server (MCP Server): running
```

## Core Workflows

### Workflow 1: Ingest Documents

**Goal**: Automatically classify and index technical documents

**Steps**:

1. **Drop documents into inbox**
   ```bash
   cp ~/Documents/STM32H743_Datasheet.pdf knowledge/inbox/
   cp ~/Docs/API_Reference.md knowledge/inbox/
   ```

2. **Automatic ingestion begins**
   - Filesystem watcher detects new files
   - Docling converts PDFs to structured format
   - Progressive classification assigns domain, type, vendor, component
   - Chunks created (512-768 tokens, heading-aware)
   - Embeddings generated and stored in RAGFlow

3. **Check ingestion status**
   ```bash
   # Via Claude: "Show ingestion status for STM32H743_Datasheet.pdf"
   # Returns: doc_id, status, confidence_band, chunks_processed
   ```

4. **Low confidence? Review UI appears**
   - If confidence < 0.70, one-screen review UI appears
   - Shows document summary, classification, evidence preview
   - Actions: Accept and Ingest, Override, Cancel

### Workflow 2: Semantic Search

**Goal**: Find relevant document chunks using natural language

**Steps**:

1. **Search via Claude**
   ```
   You: "Search the RAG system for how to configure GPIO interrupts on STM32H7"
   ```

2. **Results returned**
   - Chunks with highest similarity (>0.70)
   - Source document and page/section
   - Confidence scores
   - Metadata filters (domain, type, component, version)

3. **Filter results** (optional)
   ```
   You: "Filter by domain: embedded, component: GPIO"
   ```

### Workflow 3: Promote Facts to Knowledge Graph

**Goal**: Promote high-value evidence chunks to durable facts

**Steps**:

1. **From search results**
   ```
   You: "The chunk says max GPIO clock is 120MHz. Promote this as a Constraint."
   Claude: "Using kg.promoteFromEvidence..."
   ```

2. **From query** (search + promote in one step)
   ```
   You: "Search for STM32H7 GPIO constraints and promote the top result"
   Claude: "Using kg.promoteFromQuery..."
   ```

3. **Fact created with provenance**
   - Fact stored in Knowledge Graph with type=Constraint
   - Evidence link created (chunk → fact)
   - Document link preserved (fact → document)

4. **Conflict detection** (automatic)
   - If conflicting fact exists (e.g., "150MHz" for same entity)
   - Conflict stored explicitly
   - Resolution options: detect_only, keep_both, prefer_newest, reject_incoming

### Workflow 4: Review Conflicts

**Goal**: Review and resolve conflicting facts

**Steps**:

1. **Check for conflicts**
   ```
   You: "Review all conflicts for entity STM32H7.GPIO.max_speed"
   Claude: "Using kg.reviewConflicts..."
   ```

2. **Results returned**
   - Conflicting facts (120MHz vs 150MHz)
   - Evidence sources for each
   - Detection date and status

3. **Resolve conflict**
   ```
   You: "Keep both with scope: 120MHz for Rev A, 150MHz for Rev B"
   Claude: "Updating conflict resolution strategy..."
   ```

### Workflow 5: Trace Provenance

**Goal**: Trace fact back to source documents

**Steps**:

1. **Request provenance**
   ```
   You: "Show provenance for the fact about GPIO max speed"
   Claude: "Using kg.getProvenance..."
   ```

2. **Provenance graph returned**
   - Fact → Evidence → Chunks → Documents
   - Full chain with confidence scores
   - Page/section references

## CLI Tools

### RAG Management CLI

```bash
# List all ingested documents
bun run rag-cli list-documents

# Show document details
bun run rag-cli show-document <doc_id>

# Trigger re-indexing
bun run rag-cli reindex <doc_id>

# Show classification details
bun run rag-cli classification <doc_id>

# Search via CLI (for testing)
bun run rag-cli search "GPIO interrupts"
```

## Directory Structure

```
knowledge/
├── inbox/              # Drop PDFs, markdown, text files here
└── processed/          # Canonical storage (managed by system)
    └── <doc_id>/
        └── <version>/
            ├── original.pdf
            └── structured.md
```

## Claude Integration

All LKAP capabilities are exposed as MCP tools:

| Tool | Description | Example |
|------|-------------|---------|
| rag.search | Semantic search | "Search for GPIO configuration" |
| rag.getChunk | Get exact chunk | "Get chunk abc-123" |
| kg.promoteFromEvidence | Promote from evidence | "Promote chunk as Constraint" |
| kg.promoteFromQuery | Search + promote | "Search and promote constraint" |
| kg.reviewConflicts | Review conflicts | "Show all conflicts" |
| kg.getProvenance | Trace fact | "Show provenance for this fact" |

## Troubleshooting

### Ingestion stuck on "processing"

```bash
# Check logs
bun run server-cli logs | grep ingestion

# Trigger re-process
bun run rag-cli reindex <doc_id>
```

### Search returns no results

```bash
# Verify embeddings generated
bun run rag-cli show-document <doc_id>

# Check confidence threshold (must be >0.70)
```

### Classification confidence low

- Review UI should appear automatically
- Override classification if needed
- System learns from corrections for future docs from same source

## Next Steps

- Run `/speckit.tasks` to generate implementation tasks
- See [research.md](./research.md) for technical decisions
- See [data-model.md](./data-model.md) for entity definitions
- See [contracts/mcp-tools.yaml](./contracts/mcp-tools.yaml) for API schemas
