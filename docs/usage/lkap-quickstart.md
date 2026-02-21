---
title: "LKAP Overview"
description: "Two-tier memory model combining RAG and Knowledge Graph"
---

<!-- AI-FRIENDLY SUMMARY
System: Local Knowledge Augmentation Platform (LKAP)
Purpose: Two-tier memory combining transient documents with durable knowledge
Feature: 023-qdrant-rag

Two-Tier Memory Model:
1. Document Memory (Qdrant) - High-volume, transient, citation-centric
2. Knowledge Memory (Graphiti) - Low-volume, durable, typed, provenance-backed

Key Concept: Documents are evidence. Knowledge is curated truth.
- Users validate, not data-enter
- Promotion workflow bridges RAG → Knowledge Graph
- Provenance traces facts back to source documents

Related Docs:
- [RAG Quickstart](rag-quickstart.md) - Document Memory details
- [Knowledge Graph Quickstart](../concepts/knowledge-graph.md) - Knowledge Memory details
-->

# LKAP Overview

**Local Knowledge Augmentation Platform** combines transient document search with durable knowledge storage.

## Two-Tier Memory Model

![LKAP Two-Tier Memory Model](../assets/lkap-two-tier.jpg)

**Tier 1: Document Memory (RAG)** - Qdrant-based semantic search for transient document exploration.

**Tier 2: Knowledge Memory (KG)** - Graphiti/Neo4j for durable, typed facts with provenance.

**Promotion workflow** bridges the two: evidence from documents → curated knowledge.

## When to Use Each Tier

| Question | Use Tier | Why |
|----------|----------|-----|
| "What does the datasheet say about GPIO?" | **Document Memory** | Exploring new information |
| "Find evidence for this decision" | **Document Memory** | Finding citations |
| "What's the max clock frequency?" | **Knowledge Memory** | Verified constraint |
| "What workarounds exist for this bug?" | **Knowledge Memory** | Curated solutions |

## Quick Start

### 1. Document Memory (RAG)

```bash
# Start Qdrant
docker compose -f docker/docker-compose-qdrant.yml up -d

# Drop documents
cp report.pdf knowledge/inbox/

# Search
bun run src/skills/server/lib/rag-cli.ts search "GPIO configuration"
```

➡️ **[Full RAG Guide](rag-quickstart.md)**

### 2. Knowledge Memory (KG)

```bash
# Start Neo4j (included with knowledge system)
bun run server-cli start

# Promote facts from evidence
kg.promoteFromQuery("max clock frequency")
```

➡️ **[Full Knowledge Graph Guide](../concepts/knowledge-graph.md)**

## Promotion Workflow

The key LKAP workflow is **promoting** high-value facts from documents to durable knowledge:

```
Document → Search → Evidence → Promote → Knowledge
                    (chunk)            (fact)
```

### Promote from Evidence

```python
# Search and find relevant evidence
results = rag.search("SPI clock frequency limit")

# Promote the evidence to knowledge
kg.promoteFromEvidence(
    evidence_id="chunk-abc123",
    fact_type="Constraint",
    value="SPI max frequency is 80MHz"
)
```

### Promote from Query

```python
# Search and promote in one operation
kg.promoteFromQuery(
    query="maximum clock frequency",
    fact_type="Constraint"
)
```

### Trace Provenance

```python
# See where a fact came from
kg.getProvenance(fact_id="fact-456")
# Returns: Fact → Evidence chunks → Source documents
```

## Fact Types

When promoting to knowledge, facts are typed:

| Type | Description | Example |
|------|-------------|---------|
| `Constraint` | System limits | "max clock frequency is 120MHz" |
| `Erratum` | Known issues | "SPI FIFO corrupts above 80MHz" |
| `API` | Function signatures | `gpio_init(port, pin, mode)` |
| `Workaround` | Solutions | "Use DMA instead of FIFO" |
| `BuildFlag` | Compiler options | `-DUSE_SPI_FIFO=0` |
| `ProtocolRule` | Protocol limits | "I2C max frequency is 400kHz" |
| `Detection` | Security rules | "suspicious GPIO toggling" |
| `Indicator` | IOC data | "IP 192.168.1.100" |

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

- **[RAG Quickstart](rag-quickstart.md)** - Document ingestion and search
- **[Knowledge Graph Quickstart](../concepts/knowledge-graph.md)** - Entities, relationships, facts
- **[Configuration Reference](../reference/configuration.md)** - Environment variables
