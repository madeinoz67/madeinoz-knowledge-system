# Quick Start: Qdrant RAG Migration

**Feature**: 023-qdrant-rag
**Date**: 2026-02-13

<!--
AI-FRIENDLY SUMMARY
System: LKAP (Local Knowledge Augmentation Platform) with Qdrant
Purpose: Lightweight RAG system for document ingestion and semantic search
Key Components: Qdrant (vector DB), Ollama (embeddings), Docling (parsing)

Key Tools/Commands:
- rag.search: Semantic search across documents
- rag.getChunk: Retrieve specific chunk by ID
- rag.ingest: Ingest document into vector DB
- rag.health: Check system health

Configuration Prefix: MADEINOZ_KNOWLEDGE_QDRANT_*
Default Ports: 6333 (Qdrant), 11434 (Ollama)

Limits:
- Chunk size: 512-768 tokens
- Confidence threshold: 0.70
- Search latency: <500ms
- Memory: <200MB
-->

## Overview

This guide walks you through using the Qdrant-based RAG system for document ingestion and semantic search.

## Prerequisites

- Docker or Podman installed
- Ollama running with `bge-large-en-v1.5` model
- At least 500MB free disk space

## Quick Reference

| Task | Command |
|------|---------|
| Start Qdrant | `docker compose -f docker/docker-compose-qdrant.yml up -d` |
| Ingest document | `bun run rag-cli.ts ingest knowledge/inbox/doc.pdf` |
| Search documents | `bun run rag-cli.ts search "your query"` |
| Get chunk by ID | `bun run rag-cli.ts get-chunk <chunk-id>` |
| Check health | `bun run rag-cli.ts health` |

## Step 1: Start Services

```bash
# Start Qdrant vector database
docker compose -f docker/docker-compose-qdrant.yml up -d

# Verify Qdrant is running
curl http://localhost:6333/health

# Ensure Ollama is running with embedding model
ollama pull bge-large-en-v1.5
ollama serve
```

## Step 2: Ingest Documents

```bash
# Place documents in inbox
cp ~/Documents/datasheet.pdf knowledge/inbox/

# Ingest via CLI
bun run src/skills/server/lib/rag-cli.ts ingest knowledge/inbox/datasheet.pdf \
  --metadata domain=embedded \
  --metadata project=stm32h7 \
  --metadata type=datasheet

# Or ingest via MCP tool (from Claude)
# Call rag.ingest with file_path and metadata
```

**Expected Output**:
```
Ingesting: knowledge/inbox/datasheet.pdf
Parsing document... Done (2.3s)
Chunking into segments... 45 chunks created
Generating embeddings... Done (5.1s)
Storing in Qdrant... Done
Moving to processed/knowledge/processed/datasheet.pdf

Result:
  Document ID: 550e8400-e29b-41d4-a716-446655440000
  Status: success
  Chunks: 45
  Duration: 7.4s
```

## Step 3: Search Documents

```bash
# Search via CLI
bun run src/skills/server/lib/rag-cli.ts search "GPIO configuration maximum speed"

# Search with filters
bun run src/skills/server/lib/rag-cli.ts search "clock settings" \
  --filter domain=embedded \
  --filter project=stm32h7

# Or search via MCP tool (from Claude)
# Call rag.search with query and filters
```

**Expected Output**:
```
Results (3):

1. [0.92] stm32h7-reference.pdf - Section 5.1
   "GPIO maximum speed is 120MHz on STM32H7..."
   Page: 23 | Headings: [GPIO, Speed Configuration]

2. [0.87] stm32h7-reference.pdf - Section 5.2
   "The GPIO peripheral can be configured for..."
   Page: 24 | Headings: [GPIO, Alternate Functions]

3. [0.81] stm32h7-errata.pdf - Section 2.1
   "Known issue with GPIO speed settings..."
   Page: 5 | Headings: [Errata, GPIO]
```

## Step 4: Retrieve Specific Chunk

```bash
# Get full chunk details by ID
bun run src/skills/server/lib/rag-cli.ts get-chunk 550e8400-e29b-41d4-a716-446655440001

# Or via MCP tool (from Claude)
# Call rag.getChunk with chunk_id
```

## Step 5: Check System Health

```bash
# Check all components
bun run src/skills/server/lib/rag-cli.ts health

# Or via MCP tool
# Call rag.health
```

**Expected Output**:
```
System Health: HEALTHY

Qdrant:
  Connected: ✓
  Collection: lkap_documents
  Vectors: 1,523
  Latency: 5ms

Ollama:
  Connected: ✓
  Model: bge-large-en-v1.5
  Latency: 12ms
```

## MCP Tool Usage (for AI Assistants)

When working with Claude or other AI assistants, use these MCP tools:

### Search Documents
```
Call: rag.search
Arguments:
  query: "your search query"
  filters: { domain: "embedded", project: "stm32h7" }
  top_k: 10
```

### Retrieve Chunk
```
Call: rag.getChunk
Arguments:
  chunk_id: "uuid-from-search-result"
```

### Ingest Document
```
Call: rag.ingest
Arguments:
  file_path: "knowledge/inbox/document.pdf"
  metadata: { domain: "embedded", type: "datasheet" }
```

### Check Health
```
Call: rag.health
Arguments: {}
```

## Troubleshooting

### Qdrant Connection Failed
```bash
# Check if container is running
docker ps | grep qdrant

# Check logs
docker logs qdrant

# Restart container
docker compose -f docker/docker-compose-qdrant.yml restart
```

### Ollama Connection Failed
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Pull embedding model
ollama pull bge-large-en-v1.5

# Start Ollama server
ollama serve
```

### No Search Results
- Verify documents are ingested: `rag.health` should show vector_count > 0
- Check confidence threshold (default 0.70) - try lowering if needed
- Verify filters match document metadata

### Ingestion Errors
- Check file format (PDF, Markdown, Text only)
- Verify file exists at specified path
- Check Ollama is running for embeddings
- Review logs: `docker logs knowledge-system`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MADEINOZ_KNOWLEDGE_QDRANT_URL` | `http://localhost:6333` | Qdrant server URL |
| `MADEINOZ_KNOWLEDGE_QDRANT_COLLECTION` | `lkap_documents` | Collection name |
| `MADEINOZ_KNOWLEDGE_OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `MADEINOZ_KNOWLEDGE_OLLAMA_MODEL` | `bge-large-en-v1.5` | Embedding model |
| `MADEINOZ_KNOWLEDGE_QDRANT_CONFIDENCE_THRESHOLD` | `0.70` | Minimum confidence |
