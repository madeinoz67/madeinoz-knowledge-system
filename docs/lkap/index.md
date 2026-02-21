---
title: "LKAP Overview"
description: "Local Knowledge Augmentation Platform - Two-tier memory combining documents and knowledge"
---

<!-- AI-FRIENDLY SUMMARY
System: Local Knowledge Augmentation Platform (LKAP)
Purpose: Two-tier memory combining transient documents with durable knowledge
Feature: 022-self-hosted-rag, 023-qdrant-rag

Architecture:
- Document Memory (Qdrant): High-volume, transient, citation-centric RAG
- Knowledge Memory (Graphiti): Low-volume, durable, typed, provenance-backed graph

Key Principle: Documents are evidence. Knowledge is curated truth.
- Users validate, not data-enter
- Promotion workflow bridges RAG → Knowledge Graph
- Provenance traces facts back to source documents

Related Sections:
- [Two-Tier Memory Model](two-tier-model.md) - Tier comparison and decision matrix
- [Promotion Workflow](promotion-workflow.md) - Fact promotion and provenance
- [Document Memory (RAG)](../rag/quickstart.md) - RAG quickstart guide
- [Knowledge Memory (Graph)](../kg/quickstart.md) - Knowledge Graph quickstart
-->

# LKAP Overview

**Local Knowledge Augmentation Platform** combines transient document search with durable knowledge storage.

![LKAP Two-Tier Memory Model](../assets/lkap-two-tier.jpg)

## Two-Tier Memory Model

| Tier | Technology | Purpose | Volume |
|------|------------|---------|--------|
| **Document Memory** | Qdrant (RAG) | Semantic search across documents | High-volume, transient |
| **Knowledge Memory** | Graphiti/Neo4j | Durable, typed facts with provenance | Low-volume, curated |

**Core principle**: Documents are evidence. Knowledge is curated truth.

## When to Use Each Tier

| Question | Use Tier | Why |
|----------|----------|-----|
| "What does the datasheet say about GPIO?" | **Document Memory** | Exploring new information |
| "Find evidence for this decision" | **Document Memory** | Finding citations |
| "What's the max clock frequency?" | **Knowledge Memory** | Verified constraint |
| "What workarounds exist for this bug?" | **Knowledge Memory** | Curated solutions |

➡️ **[Two-Tier Memory Model](two-tier-model.md)** - Full comparison and decision guidance

## Quick Start

### Document Memory (RAG)

```bash
# Start Qdrant
docker compose -f docker/docker-compose-qdrant.yml up -d

# Drop documents
cp report.pdf knowledge/inbox/

# Search
bun run src/skills/server/lib/rag-cli.ts search "GPIO configuration"
```

➡️ **[Document Memory (RAG) Quickstart](../rag/quickstart.md)**

### Knowledge Memory (KG)

```bash
# Start Neo4j (included with knowledge system)
bun run server-cli start

# Promote facts from evidence
kg.promoteFromQuery("max clock frequency")
```

➡️ **[Knowledge Memory (Graph) Quickstart](../kg/quickstart.md)**

## Promotion Workflow

The key LKAP workflow is **promoting** high-value facts from documents to durable knowledge:

```
Document → Search → Evidence → Promote → Knowledge
                    (chunk)            (fact)
```

➡️ **[Promotion Workflow](promotion-workflow.md)** - Full promotion guide

## MCP Tools Summary

### Document Memory (RAG)

| Tool | Purpose |
|------|---------|
| `rag.search(query, filters, topK)` | Semantic search |
| `rag.getChunk(chunkId)` | Get specific chunk |
| `rag.ingest(filePath, ingestAll)` | Ingest documents |
| `rag.health()` | Check Qdrant |

### Knowledge Memory (KG)

| Tool | Purpose |
|------|---------|
| `kg.promoteFromEvidence(evidenceId)` | Promote fact |
| `kg.promoteFromQuery(query)` | Search & promote |
| `kg.getProvenance(factId)` | Trace sources |

## Next Steps

- **[Two-Tier Memory Model](two-tier-model.md)** - Understand when to use each tier
- **[Promotion Workflow](promotion-workflow.md)** - Learn fact promotion
- **[Document Memory (RAG)](../rag/quickstart.md)** - Get started with RAG
- **[Knowledge Memory (Graph)](../kg/quickstart.md)** - Get started with knowledge graph
