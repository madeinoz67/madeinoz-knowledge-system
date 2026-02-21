---
title: "Document Memory Concepts"
description: "Understanding RAG architecture in LKAP"
---

<!-- AI-FRIENDLY SUMMARY
System: Document Memory (RAG) - Conceptual Overview
Purpose: Explain RAG architecture, components, and flow

Key Components:
1. Docling Parser - PDF/Markdown/Text extraction
2. Semantic Chunking - 512-768 tokens with heading awareness
3. Ollama Embeddings - bge-large-en-v1.5 (1024 dimensions)
4. Qdrant Vector DB - 69MB image, cosine similarity search

Document Flow:
inbox/ → Docling Parser → Semantic Chunking → Ollama Embeddings → Qdrant → Search

Characteristics:
- High-volume storage (thousands of documents)
- Semantic similarity search
- Citation-backed results
- Transient (documents can be replaced)
-->

# Document Memory Concepts

Document Memory provides RAG (Retrieval-Augmented Generation) capabilities for semantic search across PDFs, markdown, and text documents.

## What is Document Memory?

Document Memory is **Tier 1** of the LKAP two-tier model:

- **Purpose**: Explore documents, find evidence, get citations
- **Technology**: Qdrant vector database with semantic search
- **Volume**: High (thousands of documents)
- **Persistence**: Transient (documents can be updated/replaced)

## Architecture

![RAG Architecture](../assets/rag-architecture.jpg)

### Document Flow

```
knowledge/inbox/  →  Docling Parser  →  Semantic Chunking
                                              ↓
Search Results  ←  Qdrant Search   ←  Ollama Embeddings
```

1. **Drop documents** in `knowledge/inbox/`
2. **Docling** extracts text from PDFs, markdown, text files
3. **Semantic chunking** splits into 512-768 token chunks
4. **Ollama** generates 1024-dimensional embeddings
5. **Qdrant** stores vectors for similarity search

## Components

### Docling Parser

Document parsing with structure awareness:

- **PDF**: Text extraction with page/section tracking
- **Markdown**: Heading-aware parsing
- **Text**: Plain text processing

### Semantic Chunking

Intelligent document splitting:

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Min chunk size | 512 tokens | Avoid too-small chunks |
| Max chunk size | 768 tokens | Preserve context |
| Overlap | 100 tokens | Cross-chunk continuity |
| Heading awareness | Enabled | Split at section boundaries |

### Ollama Embeddings

Local embedding generation:

- **Model**: `bge-large-en-v1.5`
- **Dimensions**: 1024
- **Runs locally**: No API calls needed
- **Speed**: ~100ms per chunk

### Qdrant Vector Database

Efficient vector storage and search:

- **Image size**: 69MB Docker container
- **Port**: 6333 (REST API)
- **Similarity**: Cosine similarity
- **Performance**: 626 QPS on benchmark

## Semantic Search

### How It Works

1. **Query embedding** - Convert search query to vector
2. **Similarity search** - Find nearest vectors in Qdrant
3. **Confidence filtering** - Filter by threshold (default 0.70)
4. **Return chunks** - With source document, page, confidence

### Example

```bash
bun run rag-cli.ts search "GPIO configuration"
```

Returns:

```
Chunk: "GPIO pins can be configured as input, output, analog..."
Source: STM32F4_Datasheet.pdf, page 145
Confidence: 0.92
```

## Document Lifecycle

### Ingestion

1. Place document in `knowledge/inbox/`
2. Run `rag.ingest()` or CLI command
3. Document parsed, chunked, embedded
4. Moved to `knowledge/processed/`
5. Hash tracked for idempotency

### Storage

| Directory | Purpose |
|-----------|---------|
| `knowledge/inbox/` | Drop documents here for ingestion |
| `knowledge/processed/` | Canonical storage after ingestion |

### Search

1. Query converted to embedding
2. Qdrant finds similar chunks
3. Results include citation and confidence
4. Can filter by domain, type, component

### Promotion

High-value chunks can be promoted to Knowledge Memory:

```
Document Chunk (RAG) → Promote → Knowledge Fact (Graph)
```

See [Promotion Workflow](../lkap/promotion-workflow.md) for details.

## Supported Formats

| Format | Extension | Parser |
|--------|-----------|--------|
| PDF | `.pdf` | Docling |
| Markdown | `.md`, `.mdx` | Native |
| Text | `.txt` | Native |

## Key Differences from Knowledge Memory

| Aspect | Document Memory (RAG) | Knowledge Memory (Graph) |
|--------|----------------------|-------------------------|
| Query type | Semantic similarity | Graph traversal |
| Output | Text chunks | Structured facts |
| Relationships | None | Entities linked |
| Volume | High (thousands) | Low (hundreds) |
| Persistence | Transient | Durable |
| Citations | Yes | Via provenance |

## When to Use Document Memory

- ✅ Exploring new documents
- ✅ Finding evidence and citations
- ✅ Broad semantic search
- ✅ Working with full document context
- ✅ Processing new information

See [Two-Tier Memory Model](../lkap/two-tier-model.md) for decision guidance.

## Next Steps

- **[RAG Quickstart](quickstart.md)** - Get started with RAG
- **[RAG Configuration](configuration.md)** - Configure Qdrant and Ollama
- **[RAG Troubleshooting](troubleshooting.md)** - Solve common issues
- **[Promotion Workflow](../lkap/promotion-workflow.md)** - Promote facts to knowledge
