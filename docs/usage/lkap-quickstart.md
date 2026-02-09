---
title: "LKAP Quickstart"
description: "Quick start guide for the Local Knowledge Augmentation Platform"
---

<!-- AI-FRIENDLY SUMMARY
System: Local Knowledge Augmentation Platform (LKAP)
Purpose: Self-hosted RAG with automatic document ingestion and knowledge promotion
Feature: 022-self-hosted-rag

Two-Tier Memory Model:
1. Document Memory (RAGFlow) - High-volume, versioned, citation-centric, short-lived relevance
2. Knowledge Memory (Graphiti) - Low-volume, high-signal, typed, version-aware, long-lived

Key Concepts:
- Documents are evidence (transient, noisy, versioned)
- Knowledge is curated truth (durable, typed, conflict-aware)
- Users are validators, not data entry clerks
- System is fast when confident, careful when uncertain, always explicit about provenance

Core Workflows:
1. Drop documents in knowledge/inbox/ for automatic ingestion
2. Search with rag.search() for semantic retrieval with citations
3. Promote facts to knowledge graph with kg.promoteFromEvidence()
4. Trace provenance with kg.getProvenance()

MCP Tools:
- rag.search(query, filters, topK) - Semantic search across documents
- rag.getChunk(chunkId) - Retrieve specific chunk by ID
- kg.promoteFromEvidence(evidenceId) - Promote fact from evidence
- kg.promoteFromQuery(query) - Search and promote in one operation
- kg.getProvenance(factId) - Trace fact to source documents

Configuration Prefix: MADEINOZ_KNOWLEDGE_*
-->

# LKAP Quickstart Guide

**Local Knowledge Augmentation Platform** - Self-hosted RAG with automatic document ingestion and evidence-based knowledge promotion. Uses external APIs (OpenRouter) for embeddings and LLM - no local model container required.

## What is LKAP?

LKAP extends the knowledge graph system with a two-tier memory model:

1. **Document Memory (RAG)** - Fast semantic search across PDFs, markdown, and text documents
2. **Knowledge Memory (KG)** - Durable, typed facts with provenance links to source documents

**Key Value Proposition**: Documents are evidence (transient, noisy). Knowledge is curated truth (durable, typed). You validate facts, the system tracks provenance.

## Quick Reference Card

| Task | Command |
|------|---------|
| **Start LKAP** | `docker compose -f docker/docker-compose-ragflow.yml up -d` |
| **Search documents** | `bun run rag-cli.ts search "<query>"` |
| **Get chunk details** | `bun run rag-cli.ts get-chunk <id>` |
| **List documents** | `bun run rag-cli.ts list` |
| **Check health** | `bun run rag-cli.ts health` |
| **Drop documents** | Copy files to `knowledge/inbox/` |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        LKAP Two-Tier Memory Model                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Document Memory (RAGFlow)                                   │  │
│  │  - High-volume storage for PDFs, markdown, text              │  │
│  │  - Semantic search with confidence scores                    │  │
│  │  - Heading-aware chunking (512-768 tokens)                   │  │
│  │  - Citation-centric retrieval                                │  │
│  │  - Fast, versioned, short-lived relevance                    │  │
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
# Start RAGFlow vector database
docker compose -f docker/docker-compose-ragflow.yml up -d

# Verify services are healthy
bun run rag-cli.ts health
```

### 2. Configure Environment

Add to `~/.claude/.env`:

```bash
# RAGFlow Configuration
MADEINOZ_KNOWLEDGE_RAGFLOW_API_URL=http://ragflow:9380
MADEINOZ_KNOWLEDGE_RAGFLOW_CONFIDENCE_THRESHOLD=0.70

# Embedding Configuration (reuses existing Graphiti variables)
# LKAP uses the same embedding provider as the Knowledge Graph
MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER=ollama
MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL=mxbai-embed-large
MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS=1024
MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER_URL=http://host.containers.internal:11434
```

### 3. Drop Documents

Copy documents to the inbox for automatic ingestion:

```bash
cp ~/Documents/technical-spec.pdf knowledge/inbox/
cp ~/docs/api-reference.md knowledge/inbox/
```

Documents are automatically:
- Converted to structured format (PDFs via Docling)
- Classified by domain, type, vendor, component
- Split into heading-aware chunks (512-768 tokens)
- Moved to `knowledge/processed/`

### 4. Search Documents

Use the CLI or MCP tools:

```bash
# CLI search
bun run rag-cli.ts search "GPIO configuration"

# Search with filters
bun run rag-cli.ts search "interrupt handlers" --domain=embedded --top-k=5
```

Results include:
- Chunk text with source document
- Page/section reference
- Confidence score
- Metadata filters (domain, type, component, version)

### 5. Promote to Knowledge

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
- `rag.search(query, filters, topK)` - Semantic search
- `rag.getChunk(chunkId)` - Retrieve specific chunk

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
    filters={"domain": "embedded", "component": "gpio-driver"},
    topK=10
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
rag.getChunk(chunkId="abc123-def456")
```

**Returns**:
- Full chunk text
- Document metadata
- Position and token count
- Section heading

### kg.promoteFromEvidence(evidenceId)

Promote fact from specific evidence.

```python
kg.promoteFromEvidence(
    evidenceId="ev-123",
    factType="Constraint",
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
    factType="Constraint"
)
```

**Returns**:
- Top evidence chunks
- Promoted fact with provenance
- Conflict detection results

### kg.getProvenance(factId)

Trace fact to source documents.

```python
kg.getProvenance(factId="fact-456")
```

**Returns**:
- Fact with type and value
- Source evidence chunks
- Original documents
- Full provenance subgraph

## Configuration

### Required Variables

```bash
MADEINOZ_KNOWLEDGE_RAGFLOW_API_URL=http://ragflow:9380
```

**Note**: Embedding configuration reuses existing Graphiti variables:
- `MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER` (ollama, openai)
- `MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL` (mxbai-embed-large, text-embedding-3-large)
- `MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS` (1024+ required)
- `MADEINOZ_KNOWLEDGE_OPENROUTER_API_KEY` (if using OpenAI embeddings)

### Optional Variables

```bash
# RAGFlow Configuration
MADEINOZ_KNOWLEDGE_RAGFLOW_API_KEY=
MADEINOZ_KNOWLEDGE_RAGFLOW_CONFIDENCE_THRESHOLD=0.70
MADEINOZ_KNOWLEDGE_RAGFLOW_CHUNK_SIZE_MIN=512
MADEINOZ_KNOWLEDGE_RAGFLOW_CHUNK_SIZE_MAX=768
MADEINOZ_KNOWLEDGE_RAGFLOW_CHUNK_OVERLAP=100
MADEINOZ_KNOWLEDGE_RAGFLOW_LOG_LEVEL=INFO
MADEINOZ_KNOWLEDGE_OLLAMA_NUM_THREAD=4
```

## CLI Reference

```bash
# Search documents
bun run rag-cli.ts search "<query>"

# Search with filters
bun run rag-cli.ts search "<query>" --domain=embedded --type=pdf --component=gpio

# Get chunk details
bun run rag-cli.ts get-chunk <chunk-id>

# List all documents
bun run rag-cli.ts list

# List with limit
bun run rag-cli.ts list --limit=50

# Check health
bun run rag-cli.ts health

# Show help
bun run rag-cli.ts help
```

## Document Storage

```
knowledge/
├── inbox/          # Drop documents here for automatic ingestion
│   └── *.pdf       # PDFs, markdown, text files
│
└── processed/      # Canonical storage after successful ingestion
    └── <doc-id>/   # Document with metadata and chunks
```

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

### RAGFlow connection failed

```bash
# Check RAGFlow is running
docker ps | grep ragflow

# Check logs
docker logs madeinoz-knowledge-ragflow

# Restart if needed
docker compose -f docker/docker-compose-ragflow.yml restart
```

### Documents not ingesting

```bash
# Check inbox exists
ls -la knowledge/inbox/

# Check ingestion logs
docker logs madeinoz-knowledge-mcp-server

# Verify document permissions
chmod 644 knowledge/inbox/*
```

### Search returns no results

```bash
# Lower confidence threshold
MADEINOZ_KNOWLEDGE_RAGFLOW_CONFIDENCE_THRESHOLD=0.60

# Check documents are indexed
bun run rag-cli.ts list

# Re-index if needed
docker compose -f docker/docker-compose-ragflow.yml restart
```

## Next Steps

- [Configuration Reference](../reference/configuration.md#lkap-configuration-feature-022) - Complete environment variable reference
- [Memory Decay Guide](memory-decay.md) - Knowledge lifecycle management
- [CLI Reference](../reference/cli.md) - Complete CLI documentation
