---
title: "RAG Quickstart"
description: "Quick start guide for Document Memory using Qdrant vector search"
---

<!-- AI-FRIENDLY SUMMARY
System: Document Memory (RAG) - Qdrant Vector Search
Purpose: Self-hosted RAG for semantic document search
Component: Part 1 of LKAP Two-Tier Memory Model

Core Workflow:
1. Drop files in knowledge/inbox/
2. Ingest via rag.ingest() or CLI
3. Search with rag.search() or CLI
4. Results include chunks, source docs, confidence scores

MCP Tools:
- rag.search(query, filters, topK) - Semantic search
- rag.getChunk(chunkId) - Retrieve specific chunk
- rag.ingest(filePath, ingestAll) - Ingest documents
- rag.health() - Check Qdrant connectivity
-->

# RAG Quickstart Guide

**Document Memory** - Fast semantic search across PDFs, markdown, and text documents using Qdrant vector database.

## Quick Reference Card

| Task | Command/Action |
|------|----------------|
| **Start Qdrant** | `docker compose -f docker/docker-compose-qdrant.yml up -d` |
| **Ingest documents** | Drop files in `knowledge/inbox/` then run `rag.ingest(ingestAll=true)` |
| **Search documents** | `bun run src/skills/server/lib/rag-cli.ts search "<query>"` |
| **Get chunk details** | `bun run src/skills/server/lib/rag-cli.ts get-chunk <id>` |
| **List documents** | `bun run src/skills/server/lib/rag-cli.ts list` |
| **Check health** | `bun run src/skills/server/lib/rag-cli.ts health` |

## Architecture

![RAG Architecture](../assets/rag-architecture.jpg)

Document flow: inbox → Docling parser → semantic chunking → Ollama embeddings → Qdrant → search results.

➡️ **[Document Memory Concepts](concepts.md)** - Learn how RAG works

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

## Next Steps

- **[Document Memory Concepts](concepts.md)** - Understand how RAG works
- **[RAG Configuration](configuration.md)** - Configure Qdrant and Ollama
- **[RAG Troubleshooting](troubleshooting.md)** - Solve common issues
- **[Promotion Workflow](../lkap/promotion-workflow.md)** - Promote facts to knowledge
- **[Knowledge Memory (Graph)](../kg/quickstart.md)** - Durable knowledge storage
