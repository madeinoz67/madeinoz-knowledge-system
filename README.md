---
# name: (24 words max) Human-readable pack name
name: Madeinoz Knowledge System

# pack-id: (format) {author}-{pack-name}-{variant}-v{version}
pack-id: madeinoz67-madeinoz-knowledge-system-core-v1.9.0

# version: (format) SemVer major.minor.patch
version: 1.9.0

# author: (1 word) GitHub username or organization
author: madeinoz67

# description: (128 words max) One-line description
description: Two-tier memory system with RAG document search (Qdrant) and knowledge graph (Neo4j) - automatic entity extraction, semantic search, and evidence-to-fact promotion for AI conversations and documents

# type: (single) concept | skill | hook | plugin | agent | mcp | workflow | template | other
type: skill

# purpose-type: (multi) security | productivity | research | development | automation | integration | creativity | analysis | other
purpose-type: [productivity, automation, development]

# platform: (single) agnostic | claude-code | opencode | cursor | custom
platform: claude-code

# dependencies: (list) Required pack-ids, empty [] if none
dependencies: []

# keywords: (24 tags max) Searchable tags for discovery
keywords: [knowledge, graph, memory, semantic search, entity extraction, relationships, graphiti, neo4j, qdrant, rag, lkap, docling, ollama, mcp, persistent, ai, storage, retrieval, documentation]
---

<p align="center"><img src="./icons/knowledge-system-architecture.png" alt="Madeinoz Knowledge System Architecture"></p>

# Knowledge

> Persistent personal knowledge management system powered by Graphiti knowledge graph - automatically extracts entities, relationships, and temporal context from conversations and documents.

[![CI](https://github.com/madeinoz67/madeinoz-knowledge-system/actions/workflows/ci.yml/badge.svg)](https://github.com/madeinoz67/madeinoz-knowledge-system/actions/workflows/ci.yml)
[![CodeQL](https://github.com/madeinoz67/madeinoz-knowledge-system/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/madeinoz67/madeinoz-knowledge-system/security/code-scanning)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/madeinoz67/madeinoz-knowledge-system)](https://github.com/madeinoz67/madeinoz-knowledge-system/releases/latest)
[![GitHub Container Registry](https://img.shields.io/badge/ghcr.io-madeinoz--knowledge--system-blue?logo=docker)](https://ghcr.io/madeinoz67/madeinoz-knowledge-system)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for full version history.

## Documentation

**[View Full Documentation](https://madeinoz67.github.io/madeinoz-knowledge-system/)** - Complete guides, architecture, and reference.

| Topic | Description |
|-------|-------------|
| [Getting Started](https://madeinoz67.github.io/madeinoz-knowledge-system/getting-started/) | Installation and quick start guide |
| [LKAP Overview](https://madeinoz67.github.io/madeinoz-knowledge-system/lkap/) | Two-tier memory model |
| [RAG Quickstart](https://madeinoz67.github.io/madeinoz-knowledge-system/rag/quickstart/) | Document search setup |
| [Configuration](https://madeinoz67.github.io/madeinoz-knowledge-system/reference/configuration/) | Environment variables and settings |
| [Architecture](https://madeinoz67.github.io/madeinoz-knowledge-system/concepts/architecture/) | System design and components |
| [Troubleshooting](https://madeinoz67.github.io/madeinoz-knowledge-system/troubleshooting/) | Common issues and solutions |

## Installation

See [INSTALL.md](INSTALL.md) for complete installation instructions, performance benchmarks, and [VERIFY.md](VERIFY.md) for verification checklist.

## Features

### Two-Tier Memory (LKAP)

- **Document Memory (RAG)** - Fast semantic search across PDFs, markdown, and text using Qdrant
- **Knowledge Memory (Graph)** - Durable facts with provenance tracking in Neo4j
- **Promotion Workflow** - Promote evidence from documents to verified facts

### Knowledge Graph

- **Automatic Entity Extraction** - LLM-powered extraction of people, organizations, concepts, and more
- **Relationship Mapping** - Automatically discovers connections between entities
- **Semantic Search** - Find knowledge using natural language, not just keywords
- **Investigative Search** - Find entity with all connected relationships in a single query (configurable depth 1-3 hops)
- **Memory Decay Scoring** - Automatic memory prioritization with importance/stability classification
- **Weighted Search** - Results ranked by semantic relevance, recency, and importance
- **Lifecycle Management** - Automated memory transitions (ACTIVE → DORMANT → ARCHIVED → EXPIRED)
- **Temporal Tracking** - Know when knowledge was captured and how it evolves
- **OSINT/CTI Ontology** - Custom entity types for threat intelligence with STIX 2.1 import support

### Observability

- **Prometheus Metrics** - Token usage, API costs, cache statistics, and memory health metrics
- **Automated Maintenance** - Scheduled cleanup of expired memories
- **Grafana Dashboards** - Visualize knowledge, token usage, graph stats and memory health
- **Memory Sync** - Auto-syncs learnings from PAI Memory System

## Usage

The skill triggers automatically based on natural language:

| Say This | Action |
|----------|--------|
| "remember that X" | Capture knowledge with entity extraction |
| "what do I know about X" | Semantic search for related entities |
| "how are X and Y related" | Find relationships between concepts |
| "what did I learn today" | **Temporal search** - filter by date |
| "recent learnings" | Retrieve recent knowledge additions |
| "knowledge status" | Check system health |
| "search documents for X" | **RAG search** across ingested documents |

### Document Search (RAG)

Drop documents in `knowledge/inbox/` for automatic ingestion, then search:

```bash
# Semantic search across documents
bun run rag-cli.ts search "GPIO configuration"

# Ingest new documents
bun run rag-cli.ts ingest knowledge/inbox/
```

See [RAG Quickstart](https://madeinoz67.github.io/madeinoz-knowledge-system/rag/quickstart/) for full documentation.

### Temporal Search

Filter search results by date with `--since` and `--until`:

```bash
# Today's knowledge
bun run tools/knowledge-cli.ts search_nodes "topic" --since today

# Last 7 days
bun run tools/knowledge-cli.ts search_facts "decisions" --since 7d

# Date range
bun run tools/knowledge-cli.ts search_nodes "project" --since 2026-01-01 --until 2026-01-15
```

**Date formats:** `today`, `yesterday`, `7d`, `1w`, `1m`, or ISO dates (`2026-01-26`)

### Weighted Search (Low-Cost)

Rank results by **semantic relevance (60%) + recency (25%) + importance (15%)** using the `--weighted` flag:

```bash
# Weighted search - prioritizes important, recent, relevant knowledge
bun run tools/knowledge-cli.ts search_nodes "topic" --weighted
```

**Cost benefit:** Weighted scoring uses already-computed embeddings and metadata — **no additional LLM calls**. Works with any embedding model including free/local options like Ollama, Trinity, or gpt-4o-mini.

**Output includes:**

- 📊 Overall score (0-1)
- S: Semantic similarity
- R: Recency score
- I: Importance score
- Lifecycle state (ACTIVE/DORMANT/ARCHIVED)
- Importance/Stability ratings (1-5)

## What's Included

| Component | Purpose |
|-----------|---------|
| `SKILL.md` | PAI skill with intent-based routing |
| `src/skills/workflows/` | 8 workflows (Capture, Search, SearchByDate, Facts, Recent, Status, Clear, BulkImport) |
| `src/skills/tools/` | Server management scripts (start, stop, status, logs) |
| `src/hooks/` | Memory sync hook for automatic knowledge capture |
| `docker/` | Docker/Podman compose files for Neo4j and Qdrant |

## Database Backends

| Backend | Port | Purpose |
|---------|------|---------|
| **Neo4j** (default) | 7474/7687 | Knowledge graph storage |
| **Qdrant** | 6333 | Document memory (RAG) vector storage |
| **Ollama** | 11434 | Local embeddings (optional) |

## For AI Agents

This is a **PAI Pack** - a complete, self-contained module for Personal AI Infrastructure:

1. Read the entire README to understand what you're installing
2. Follow [INSTALL.md](INSTALL.md) step-by-step
3. Complete ALL verification checks in [VERIFY.md](VERIFY.md)
4. If any step fails, STOP and troubleshoot before continuing

## Credits

- **Knowledge graph engine**: [Graphiti](https://github.com/getzep/graphiti) by Zep AI
- **Graph database**: [Neo4j](https://neo4j.com/)
- **Vector database**: [Qdrant](https://qdrant.tech/)
- **Document parsing**: [Docling](https://github.com/DS4SD/docling)
- **Built for**: [Personal AI Infrastructure (PAI)](https://github.com/danielmiessler/PAI)

See full [Acknowledgments](https://madeinoz67.github.io/madeinoz-knowledge-system/acknowledgments) for credits to the community and research that inspired this system.

## Related

- [PAI Memory System](https://github.com/danielmiessler/PAI) - Auto-syncs learnings to knowledge graph
- [PAI Research Skill](https://github.com/danielmiessler/PAI) - Capture research findings

---

*For detailed documentation, visit the [full docs](https://madeinoz67.github.io/madeinoz-knowledge-system/).*
