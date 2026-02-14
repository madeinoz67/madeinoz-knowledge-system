---
title: "LKAP Quickstart"
description: "Quick start guide for the Local Knowledge Augmentation Platform"
---

<!-- AI-FRIENDLY SUMMARY
System: Local Knowledge Augmentation Platform (LKAP)
Purpose: Self-hosted RAG with Qdrant vector database and knowledge promotion
Feature: 023-qdrant-rag

Two-Tier Memory Model:
1. Document Memory (Qdrant) - High-volume, versioned, citation-centric, short-lived relevance
2. Knowledge Memory (Graphiti) - Low-volume, high-signal, typed, version-aware, long-lived

Key Concepts:
- Documents are evidence (transient, noisy, versioned) - managed via file drop in knowledge/inbox/
- Knowledge is curated truth (durable, typed, conflict-aware)
- Users are validators, not data entry clerks
- System is fast when confident, careful when uncertain, always explicit about provenance

Core Workflows:
1. Drop documents in knowledge/inbox/ for automatic ingestion
2. Ingestion uses Docling for PDF parsing + semantic chunking
3. Search with rag.search() for semantic retrieval with citations
4. Promote facts to knowledge graph with kg.promoteFromEvidence()
5. Trace provenance with kg.getProvenance()

MCP Tools:
- rag.search(query, filters, topK) - Semantic search across documents
- rag.getChunk(chunkId) - Retrieve specific chunk by ID
- rag.ingest(filePath, ingestAll) - Ingest documents from inbox
- rag.health() - Check Qdrant connectivity
- kg.promoteFromEvidence(evidenceId) - Promote fact from evidence
- kg.promoteFromQuery(query) - Search and promote in one operation
- kg.getProvenance(factId) - Trace fact to source documents

Configuration Prefix: MADEINOZ_KNOWLEDGE_QDRANT_*
-->

# LKAP Quickstart Guide

**Local Knowledge Augmentation Platform** - Self-hosted RAG with Qdrant vector database and evidence-based knowledge promotion. Documents are ingested by dropping files in `knowledge/inbox/`.

## What is LKAP?

LKAP extends the knowledge graph system with a two-tier memory model:

1. **Document Memory (RAG)** - Fast semantic search across PDFs, markdown, and text documents (powered by Qdrant)
2. **Knowledge Memory (KG)** - Durable, typed facts with provenance links to source documents

**Key Value Proposition**: Documents are evidence (transient, noisy). Knowledge is curated truth (durable, typed). You validate facts, the system tracks provenance.

## Quick Reference Card

| Task | Command/Action |
|------|----------------|
| **Start LKAP** | `docker compose -f docker/docker-compose-qdrant.yml up -d` |
| **Ingest documents** | Drop files in `knowledge/inbox/` then run `rag.ingest(ingestAll=true)` |
| **Search documents** | `bun run src/skills/server/lib/rag-cli.ts search "<query>"` |
| **Get chunk details** | `bun run src/skills/server/lib/rag-cli.ts get-chunk <id>` |
| **List documents** | `bun run src/skills/server/lib/rag-cli.ts list` |
| **Check health** | `bun run src/skills/server/lib/rag-cli.ts health` |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        LKAP Two-Tier Memory Model                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Document Memory (Qdrant)                                    │  │
│  │  - Drop documents in knowledge/inbox/                        │  │
│  │  - Docling parser: PDF, markdown, text                       │  │
│  │  - Semantic chunking: 512-768 tokens                         │  │
│  │  - Ollama embeddings: bge-large-en-v1.5 (1024 dims)          │  │
│  │  - Processed docs moved to knowledge/processed/              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              ▲                                      │
│                              │ Promote with evidence               │
│                              ▼                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Knowledge Memory (Graphiti)                                  │  │
│  │  - Low-volume, high-signal facts                             │  │
│  │  - Typed: Constraint, Erratum, API, etc.                     │  │
│  │  - Evidence-backed with provenance links                     │  │
│  │  - Conflict-aware, version-aware                             │  │
│  │  - Durable, long-lived, curated truth                        │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Getting Started

### 1. Start Services

```bash
# Start Qdrant vector database
docker compose -f docker/docker-compose-qdrant.yml up -d

# Start Ollama (for local embeddings)
docker compose -f docker/docker-compose-ollama.yml up -d

# Verify services are healthy
bun run src/skills/server/lib/rag-cli.ts health
```

### 2. Ingest Documents

Drop documents in the inbox directory:

```bash
# Place documents for ingestion
cp ~/Downloads/datasheet.pdf knowledge/inbox/
cp ~/Documents/notes.md knowledge/inbox/
```

Then trigger ingestion via MCP tool:

```python
# Ingest all documents in inbox
rag.ingest(ingestAll=true)

# Or ingest a specific file
rag.ingest(filePath="datasheet.pdf")
```

After successful ingestion:
- Documents are moved to `knowledge/processed/`
- Chunks are stored in Qdrant with embeddings
- Original file hash is tracked for idempotency

### 3. Search Documents

Use the CLI or MCP tools:

```bash
# CLI search
bun run src/skills/server/lib/rag-cli.ts search "GPIO configuration"

# Search with filters
bun run src/skills/server/lib/rag-cli.ts search "interrupt handlers" --domain=embedded --top-k=5
```

Results include:
- Chunk text with source document
- Page/section reference
- Confidence score
- Metadata filters (domain, type, component)

### 4. Promote to Knowledge

Promote high-value facts from evidence to the durable knowledge graph:

```bash
# Via MCP (available to Claude)
kg.promoteFromEvidence(evidenceId)
kg.promoteFromQuery("max clock frequency 120MHz")
```

Promoted facts are:
- Typed (Constraint, Erratum, API, etc.)
- Linked to source evidence and documents
- Conflict-aware (detects contradictions)
- Version-aware (tracks document changes)

## Two-Tier Memory Model

### Document Memory (RAG)

**Purpose**: Fast semantic search across all documents.

**Characteristics**:
- High-volume storage (thousands of documents)
- Semantic search with confidence scores
- Heading-aware chunking for coherence
- Citation-centric retrieval
- Short-lived relevance (documents change)

**Best For**:
- Exploring new information
- Finding evidence for decisions
- Cross-referencing specifications
- Understanding context

**Access**:
- **CLI**: `bun run rag-cli.ts search "<query>"`
- **MCP**: `rag.search(query, filters, topK)` for semantic search
- **MCP**: `rag.getChunk(chunkId)` for specific chunk retrieval

### Knowledge Memory (KG)

**Purpose**: Durable, verified facts with provenance.

**Characteristics**:
- Low-volume, high-signal (10x fewer facts than chunks)
- Typed (Constraint, Erratum, API, etc.)
- Evidence-backed with provenance links
- Conflict-aware (detects contradictions)
- Version-aware (tracks source changes)
- Long-lived relevance

**Best For**:
- Verified constraints and requirements
- Errata and workarounds
- API signatures and build flags
- Detection rules and indicators

**Access**:
- `kg.promoteFromEvidence(evidenceId)` - Promote from evidence
- `kg.promoteFromQuery(query)` - Search and promote
- `kg.getProvenance(factId)` - Trace to source documents

## MCP Tools

### rag.search(query, filters, topK)

Semantic search across documents.

```python
rag.search(
    query="GPIO configuration",
    domain="embedded",
    component="gpio-driver",
    top_k=10
)
```

**Returns**:
- Chunk text with source document
- Page/section reference
- Confidence score (0.0-1.0)
- Metadata filters

### rag.getChunk(chunkId)

Retrieve specific chunk by ID.

```python
rag.getChunk(chunk_id="abc123-def456")
```

**Returns**:
- Full chunk text
- Document metadata
- Position and token count
- Section heading

### rag.ingest(filePath, ingestAll)

Ingest documents from inbox.

```python
# Ingest all documents in inbox
rag.ingest(ingest_all=True)

# Ingest specific file
rag.ingest(file_path="datasheet.pdf")
```

**Returns**:
- Document ID
- Chunk count
- Processing status
- Error message (if failed)

### rag.health()

Check Qdrant connectivity.

```python
rag.health()
```

**Returns**:
- Connection status
- Collection status
- Vector count

### kg.promoteFromEvidence(evidenceId)

Promote fact from specific evidence.

```python
kg.promoteFromEvidence(
    evidence_id="ev-123",
    fact_type="Constraint",
    value="max clock frequency is 120MHz"
)
```

**Returns**:
- Fact ID with provenance links
- Conflict detection results
- Knowledge graph subgraph

### kg.promoteFromQuery(query)

Search and promote in one operation.

```python
kg.promoteFromQuery(
    query="SPI clock frequency",
    fact_type="Constraint"
)
```

**Returns**:
- Top evidence chunks
- Promoted fact with provenance
- Conflict detection results

### kg.getProvenance(factId)

Trace fact to source documents.

```python
kg.getProvenance(fact_id="fact-456")
```

**Returns**:
- Fact with type and value
- Source evidence chunks
- Original documents
- Full provenance subgraph

## Configuration

### Required Variables

```bash
# Qdrant API endpoint
MADEINOZ_KNOWLEDGE_QDRANT_URL=http://localhost:6333

# Qdrant collection name
MADEINOZ_KNOWLEDGE_QDRANT_COLLECTION=lkap_documents
```

### Optional Variables

```bash
# Qdrant Configuration
MADEINOZ_KNOWLEDGE_QDRANT_API_KEY=                    # For cloud deployments
MADEINOZ_KNOWLEDGE_QDRANT_CONFIDENCE_THRESHOLD=0.70
MADEINOZ_KNOWLEDGE_QDRANT_DEFAULT_TOP_K=10
MADEINOZ_KNOWLEDGE_QDRANT_MAX_TOP_K=100

# Chunking Configuration
MADEINOZ_KNOWLEDGE_QDRANT_CHUNK_SIZE_MIN=512
MADEINOZ_KNOWLEDGE_QDRANT_CHUNK_SIZE_MAX=768
MADEINOZ_KNOWLEDGE_QDRANT_CHUNK_OVERLAP=100

# Ollama Configuration (for local embeddings)
MADEINOZ_KNOWLEDGE_QDRANT_OLLAMA_URL=http://localhost:11434
MADEINOZ_KNOWLEDGE_QDRANT_OLLAMA_MODEL=bge-large-en-v1.5
```

## CLI Reference

```bash
# Search documents
bun run src/skills/server/lib/rag-cli.ts search "<query>"

# Search with filters
bun run src/skills/server/lib/rag-cli.ts search "<query>" --domain=embedded --type=pdf --component=gpio

# Get chunk details
bun run src/skills/server/lib/rag-cli.ts get-chunk <chunk-id>

# List all documents
bun run src/skills/server/lib/rag-cli.ts list

# List with limit
bun run src/skills/server/lib/rag-cli.ts list --limit=50

# Check health
bun run src/skills/server/lib/rag-cli.ts health

# Show help
bun run src/skills/server/lib/rag-cli.ts help
```

## Document Storage

| Directory | Purpose |
|-----------|---------|
| `knowledge/inbox/` | Drop documents here for ingestion |
| `knowledge/processed/` | Canonical storage after ingestion |

**Supported Formats**:
- **PDF**: `.pdf` files (parsed via Docling)
- **Markdown**: `.md`, `.mdx` files
- **Text**: `.txt` files

## Fact Types

When promoting to knowledge, facts are typed:

| Type | Description | Example |
|------|-------------|---------|
| `Constraint` | System limits and requirements | "max clock frequency is 120MHz" |
| `Erratum` | Known issues and bugs | "SPI FIFO corrupts above 80MHz" |
| `API` | Function signatures | `gpio_init(port, pin, mode)` |
| `Workaround` | Solutions to errata | "Use DMA instead of FIFO" |
| `BuildFlag` | Compiler/build options | `-DUSE_SPI_FIFO=0` |
| `ProtocolRule` | Protocol constraints | "I2C max frequency is 400kHz" |
| `Detection` | Security detection rules | "suspicious GPIO toggling" |
| `Indicator` | IOC/indicator data | "IP 192.168.1.100" |

## Troubleshooting

### Qdrant connection failed

```bash
# Check Qdrant is running
docker ps | grep qdrant

# Check logs
docker logs qdrant

# Restart if needed
docker compose -f docker/docker-compose-qdrant.yml restart
```

### Documents not ingesting

```bash
# Check inbox directory exists
ls -la knowledge/inbox/

# Check file permissions
chmod 644 knowledge/inbox/*

# Check MCP server logs for errors
docker logs madeinoz-knowledge-mcp
```

### Search returns no results

```bash
# Verify documents are ingested
bun run src/skills/server/lib/rag-cli.ts list

# Check health
bun run src/skills/server/lib/rag-cli.ts health

# Lower confidence threshold if needed
MADEINOZ_KNOWLEDGE_QDRANT_CONFIDENCE_THRESHOLD=0.60
```

### Ollama embeddings failing

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Pull the embedding model if needed
ollama pull bge-large-en-v1.5

# Check Ollama logs
docker logs ollama
```

## Next Steps

- [Configuration Reference](../reference/configuration.md#qdrant-configuration-feature-023) - Complete environment variable reference
- [Memory Decay Guide](memory-decay.md) - Knowledge lifecycle management
- [CLI Reference](../reference/cli.md) - Complete CLI documentation
