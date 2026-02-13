---
title: "LKAP Quickstart"
description: "Quick start guide for the Local Knowledge Augmentation Platform"
---

<!-- AI-FRIENDLY SUMMARY
System: Local Knowledge Augmentation Platform (LKAP)
Purpose: Self-hosted RAG with RAGFlow document management and knowledge promotion
Feature: 022-self-hosted-rag

Two-Tier Memory Model:
1. Document Memory (RAGFlow) - High-volume, versioned, citation-centric, short-lived relevance
2. Knowledge Memory (Graphiti) - Low-volume, high-signal, typed, version-aware, long-lived

Key Concepts:
- Documents are evidence (transient, noisy, versioned) - managed via RAGFlow web UI
- Knowledge is curated truth (durable, typed, conflict-aware)
- Users are validators, not data entry clerks
- System is fast when confident, careful when uncertain, always explicit about provenance

Core Workflows:
1. Access RAGFlow UI at http://localhost:9380 for document management
2. Create datasets and upload documents via drag-and-drop
3. Search with rag.search() for semantic retrieval with citations
4. Promote facts to knowledge graph with kg.promoteFromEvidence()
5. Trace provenance with kg.getProvenance()

MCP Tools:
- rag.search(query, filters, topK) - Semantic search across documents
- rag.getChunk(chunkId) - Retrieve specific chunk by ID
- kg.promoteFromEvidence(evidenceId) - Promote fact from evidence
- kg.promoteFromQuery(query) - Search and promote in one operation
- kg.getProvenance(factId) - Trace fact to source documents

Configuration Prefix: MADEINOZ_KNOWLEDGE_*

RAGFlow Features:
- Web UI at http://localhost:9380 for document upload and management
- 14 built-in chunking templates for different document types
- Visual chunk preview with editing capabilities
- PDF parsing via MinerU/PaddleOCR
- Documents stored in MinIO (object storage)
-->

# LKAP Quickstart Guide

**Local Knowledge Augmentation Platform** - Self-hosted RAG with RAGFlow document management and evidence-based knowledge promotion. Documents are managed via RAGFlow's built-in web interface at http://localhost:9380.

## What is LKAP?

LKAP extends the knowledge graph system with a two-tier memory model:

1. **Document Memory (RAG)** - Fast semantic search across PDFs, markdown, and text documents (managed via RAGFlow UI)
2. **Knowledge Memory (KG)** - Durable, typed facts with provenance links to source documents

**Key Value Proposition**: Documents are evidence (transient, noisy). Knowledge is curated truth (durable, typed). You validate facts, the system tracks provenance.

## Quick Reference Card

| Task | Command/Action |
|------|----------------|
| **Start LKAP** | `docker compose -f docker/docker-compose-ragflow.yml up -d` |
| **Access RAGFlow UI** | Open http://localhost:9380 in browser |
| **Search documents** | `bun run src/skills/server/lib/rag-cli.ts search "<query>"` |
| **Get chunk details** | `bun run src/skills/server/lib/rag-cli.ts get-chunk <id>` |
| **List documents** | `bun run src/skills/server/lib/rag-cli.ts list` |
| **Check health** | `bun run src/skills/server/lib/rag-cli.ts health` |
| **Upload documents** | Use RAGFlow UI at http://localhost:9380 |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        LKAP Two-Tier Memory Model                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Document Memory (RAGFlow Web UI)                           │  │
│  │  - Access at http://localhost:9380                          │  │
│  │  - Drag-and-drop document upload                            │  │
│  │  - Visual chunk preview and editing                         │  │
│  │  - 14 built-in chunking templates                           │  │
│  │  - PDF parsing via MinerU/PaddleOCR                         │  │
│  │  - Documents stored in MinIO                                │  │
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
# Start RAGFlow vector database with web UI
docker compose -f docker/docker-compose-ragflow.yml up -d

# Verify services are healthy
bun run src/skills/server/lib/rag-cli.ts health
```

### 2. Access RAGFlow UI

Open your browser and navigate to:

```
http://localhost:9380
```

The RAGFlow UI provides:
- **Dataset Management** - Create and manage document collections
- **Document Upload** - Drag-and-drop PDFs, markdown, and text files
- **Chunk Preview** - Visual review of parsed chunks with editing
- **Search Testing** - Test retrieval quality before integration

### 3. Create a Dataset

In the RAGFlow UI:

1. Click **"Create Dataset"**
2. Configure embedding model and chunking method:
   - **Embedding Model**: `ollama` (local) or `openai` (external API)
   - **Chunking Method**: Choose from 14 built-in templates
   - **Chunk Size**: 512-768 tokens (recommended)
3. Save the dataset

### 4. Upload Documents

In the RAGFlow UI:

1. Select your dataset
2. Click **"Upload Documents"**
3. Drag and drop files or click to browse:
   - **PDF**: `.pdf` files (parsed via MinerU/PaddleOCR)
   - **Markdown**: `.md`, `.mdx` files
   - **Text**: `.txt` files
   - **Office**: `.docx`, `.xlsx`, `.pptx` files
4. Documents are automatically:
   - Parsed and extracted
   - Split into chunks (respecting heading boundaries)
   - Embedded with your chosen model
   - Stored in MinIO for retrieval

### 5. Review and Edit Chunks (Optional)

In the RAGFlow UI:

1. Navigate to **Documents** → select your document
2. View parsed chunks with page/section references
3. **Add Keywords** - Improve search relevance for specific chunks
4. **Edit Content** - Double-click any chunk to correct parsing errors
5. **Add Questions** - Define test queries for retrieval validation

### 6. Search Documents

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
- Metadata filters (domain, type, component, version)

### 7. Promote to Knowledge

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
- **RAGFlow UI**: http://localhost:9380 (document management)
- **MCP Tools**: `rag.search(query, filters, topK)` for semantic search
- **MCP Tools**: `rag.getChunk(chunkId)` for specific chunk retrieval

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
# RAGFlow API endpoint
MADEINOZ_KNOWLEDGE_RAGFLOW_API_URL=http://ragflow:9380
```

**Note**: Embedding configuration reuses existing Graphiti variables:
- `MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER` (ollama, openai)
- `MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL` (mxbai-embed-large, text-embedding-3-large)
- `MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS` (1024+ required)
- `MADEINOZ_KNOWLEDGE_OPENROUTER_API_KEY` (if using OpenAI embeddings via OpenRouter)

### Optional Variables

```bash
# RAGFlow Configuration
MADEINOZ_KNOWLEDGE_RAGFLOW_API_KEY=
MADEINOZ_KNOWLEDGE_RAGFLOW_CONFIDENCE_THRESHOLD=0.70
MADEINOZ_KNOWLEDGE_RAGFLOW_CHUNK_SIZE_MIN=512
MADEINOZ_KNOWLEDGE_RAGFLOW_CHUNK_SIZE_MAX=768
MADEINOZ_KNOWLEDGE_RAGFLOW_CHUNK_OVERLAP=100
MADEINOZ_KNOWLEDGE_RAGFLOW_LOG_LEVEL=INFO

# Ollama Configuration (for local embeddings)
MADEINOZ_KNOWLEDGE_OLLAMA_BASE_URL=http://ollama:11434
MADEINOZ_KNOWLEDGE_OLLAMA_EMBEDDING_MODEL=bge-large-en-v1.5
MADEINOZ_KNOWLEDGE_OLLAMA_NUM_THREAD=4
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

## RAGFlow UI Features

### Document Upload

- **Drag-and-Drop**: Drop multiple files at once (32 files per batch via UI)
- **File Size**: Default 1GB per upload (configurable)
- **Supported Formats**: PDF, DOC, DOCX, TXT, MD, MDX, CSV, XLSX, XLS, JPEG, JPG, PNG, TIF, GIF, PPT, PPTX

### Chunking Templates

RAGFlow provides 14 built-in chunking templates:
- **General** - Balanced chunking for most documents
- **Legal** - Preserves legal document structure
- **Finance** - Optimized for financial reports
- **Technical** - Handles technical documentation
- **Paper** - For academic papers
- **Manual** - For user manuals
- **Book** - Long-form content
- **Laws** - Legal statutes and regulations
- **Presentation** - Slide decks (PPT, PPTX)
- **QA** - Question-answer pairs
- **Knowledge Graph** - Entity-relationship extraction
- **Resume** - CV parsing
- **Table** - Preserves table structures
- **One** - Single chunk per document

### Chunk Editing

- **Visual Preview**: See how documents were chunked
- **Add Keywords**: Improve search relevance
- **Edit Content**: Fix parsing errors
- **Test Retrieval**: Validate search quality

### Storage

- **MinIO**: Object storage for uploaded files
- **Vector Database**: Embedded chunks for semantic search
- **Persistent**: Survives container restarts

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

### RAGFlow UI not accessible

```bash
# Verify port 9380 is available
curl http://localhost:9380

# Check browser console for errors
# Try accessing from different browser or incognito mode
```

### Documents not parsing

```bash
# Check RAGFlow logs for parsing errors
docker logs madeinoz-knowledge-ragflow

# Verify file format is supported
# File size under limit (default 1GB)
```

### Search returns no results

```bash
# Lower confidence threshold
MADEINOZ_KNOWLEDGE_RAGFLOW_CONFIDENCE_THRESHOLD=0.60

# Check documents are indexed
bun run src/skills/server/lib/rag-cli.ts list

# Verify embedding model is working
docker logs madeinoz-knowledge-ragflow | grep -i embedding
```

### Knowledge promotion fails

```bash
# Check Graphiti connection
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts health

# Verify evidence ID exists
bun run src/skills/server/lib/rag-cli.ts search <chunk-text>
```

## Next Steps

- [Configuration Reference](../reference/configuration.md#lkap-configuration-feature-022) - Complete environment variable reference
- [Memory Decay Guide](memory-decay.md) - Knowledge lifecycle management
- [CLI Reference](../reference/cli.md) - Complete CLI documentation
