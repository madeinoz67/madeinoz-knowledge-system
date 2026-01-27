---
title: Madeinoz Knowledge System
description: Persistent personal knowledge management system powered by Graphiti knowledge graph with FalkorDB or Neo4j backend
---

# Madeinoz Knowledge System

<p align="center"><img src="assets/logo.png" alt="Madeinoz Knowledge System" width="200"></p>

> Persistent personal knowledge management system powered by Graphiti knowledge graph - automatically extracts entities, relationships, and temporal context from conversations, documents, and ideas.

<!-- AI-FRIENDLY SUMMARY
System: Madeinoz Knowledge System (PAI Pack)
Purpose: Personal knowledge management with automatic entity extraction
Backend: Neo4j (default) or FalkorDB graph database
LLM: Requires cloud LLM (Gemini, GPT-4o recommended) for entity extraction
Embeddings: Local Ollama (mxbai-embed-large) or cloud embeddings
Caching: Gemini 2.5 Flash supports prompt caching (75% cost reduction)
Metrics: Prometheus endpoint on port 9090/9091

Key MCP Tools:
- add_memory: Store knowledge with automatic entity extraction
- search_memory_nodes: Find entities by semantic search (max_nodes default: 10)
- search_memory_facts: Find relationships between entities (max_facts default: 10)
- get_episodes: Retrieve by time range (max_episodes default: 10)
- get_status: System health check

Configuration Prefix: MADEINOZ_KNOWLEDGE_*
Default Ports: 8000 (MCP), 7474 (Neo4j), 9090 (Metrics)

Limits:
- Rate: 60 requests/60 seconds per IP (configurable)
- Concurrency: 10 parallel LLM requests (SEMAPHORE_LIMIT)
- Search results: 10 nodes/facts/episodes (adjustable per-request)
- Cache minimum: 1024 tokens (smaller requests skip caching)
- Episode body: No hard limit (bounded by LLM context window)
-->

## What It Does

The Madeinoz Knowledge System transforms your AI conversations into a permanent, searchable knowledge base:

- **Automatically Learns**: Extracts entities and relationships as you work
- **Connects Concepts**: Maps how ideas relate over time
- **Semantic Search**: Finds relevant knowledge using natural language
- **Builds Context**: Compounds knowledge across sessions
- **Never Forgets**: Persistent storage with temporal tracking

**Core principle**: Work normally, knowledge handles itself.

## Quick Start

New to the system? Follow this path:

1. **[Overview](getting-started/overview.md)** - What the system does and your first steps (5 min)
2. **[Installation Guide](installation/index.md)** - Step-by-step setup instructions (15 min)
3. **[Basic Usage](usage/basic-usage.md)** - How to capture and search knowledge (10 min)
4. **[Quick Reference](getting-started/quick-reference.md)** - Commands at a glance

**Total time to get started: 30 minutes**

## Documentation Sections

### Getting Started

Start here if you're new:

- **[Overview](getting-started/overview.md)** - What the system does and quick start
- **[Quick Reference](getting-started/quick-reference.md)** - Commands and natural language triggers

### Installation

Set up the system:

- **[Installation Guide](installation/index.md)** - Complete setup instructions
- **[Requirements](installation/requirements.md)** - Prerequisites and dependencies
- **[Verification](installation/verification.md)** - Confirm everything works

### Usage

Learn how to use the system:

- **[Basic Usage](usage/basic-usage.md)** - Capturing and searching knowledge
- **[Advanced Usage](usage/advanced.md)** - Bulk import, backup, multiple graphs

### Concepts

Understand how it works:

- **[Architecture](concepts/architecture.md)** - System design and components
- **[Knowledge Graph](concepts/knowledge-graph.md)** - Episodes, entities, facts explained

### Troubleshooting

Fix common issues:

- **[Common Issues](troubleshooting/common-issues.md)** - Solutions to frequent problems

### Reference

Detailed specifications:

- **[CLI Reference](reference/cli.md)** - Command-line interface
- **[Configuration](reference/configuration.md)** - Environment variables and settings
- **[Observability & Metrics](reference/observability.md)** - Prometheus metrics, monitoring, caching
- **[Model Guide](reference/model-guide.md)** - Ollama and LLM configuration
- **[Benchmarks](reference/benchmarks.md)** - Model performance comparisons

## Natural Language Commands

The system responds to natural conversation:

| Say This | System Does |
|----------|-------------|
| "Remember that..." | Captures knowledge with entity extraction |
| "What do I know about X?" | Searches knowledge base semantically |
| "How are X and Y related?" | Finds relationships between concepts |
| "What did I learn today?" | **Temporal search** - filter by date |
| "What did I learn recently?" | Shows recent knowledge additions |
| "Knowledge status" | Displays system health and statistics |

## Database Backends

Two graph database options:

| Backend | Best For | Web UI |
|---------|----------|--------|
| **Neo4j** (default) | CTI/OSINT data, rich queries | [localhost:7474](http://localhost:7474) |
| **FalkorDB** | Simple setup, lower resources | [localhost:3000](http://localhost:3000) |

## Key Features

### Prompt Caching (Gemini)

Reduce LLM costs by up to 75% with Gemini prompt caching:

```bash
# Enable in ~/.claude/.env
MADEINOZ_KNOWLEDGE_PROMPT_CACHE_ENABLED=true
MADEINOZ_KNOWLEDGE_MODEL_NAME=google/gemini-2.5-flash
```

Gemini 2.5 Flash uses **implicit caching** - automatic with no configuration needed beyond enabling it. See [Observability & Metrics](reference/observability.md#prompt-caching-gemini) for details.

### Observability & Metrics

Monitor API usage, costs, and performance via Prometheus:

```bash
# View metrics
curl http://localhost:9091/metrics | grep graphiti_

# Key metrics available:
# - graphiti_api_cost_total (USD spent)
# - graphiti_llm_request_duration_seconds (latency)
# - graphiti_cache_hit_rate (caching effectiveness)
```

See [Observability & Metrics](reference/observability.md) for full documentation.

## Common Commands

### Server Management

```bash
# Check status
bun run status

# Start server
bun run start

# Stop server
bun run stop

# View logs
bun run logs
```

### Memory Sync

```bash
# Manual sync (from installed location)
bun run ~/.claude/hooks/sync-memory-to-knowledge.ts

# Dry run (see what would sync)
bun run ~/.claude/hooks/sync-memory-to-knowledge.ts --dry-run
```

## Need Help?

1. Check the [Troubleshooting Guide](troubleshooting/common-issues.md)
2. Review [Key Concepts](concepts/knowledge-graph.md)
3. Look for examples in the [Usage Guide](usage/basic-usage.md)

## Quick Reference Card

<!-- This section is designed for quick scanning by both humans and AI -->

### MCP Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `add_memory` | Store knowledge | `{"name": "Note", "episode_body": "...", "group_id": "main"}` |
| `search_memory_nodes` | Find entities | `{"query": "Python frameworks", "limit": 10}` |
| `search_memory_facts` | Find relationships | `{"query": "how X relates to Y"}` |
| `get_episodes` | Temporal retrieval | `{"group_id": "main", "last_n": 10}` |
| `get_status` | Health check | `{}` |

### Environment Variables (Essential)

```bash
# LLM (required)
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openai
MADEINOZ_KNOWLEDGE_MODEL_NAME=google/gemini-2.5-flash
MADEINOZ_KNOWLEDGE_OPENAI_API_KEY=sk-or-v1-...
MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL=https://openrouter.ai/api/v1

# Embeddings (required)
MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER=ollama
MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL=mxbai-embed-large
MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS=1024
MADEINOZ_KNOWLEDGE_EMBEDDER_BASE_URL=http://host.docker.internal:11434/v1

# Caching (optional, recommended)
MADEINOZ_KNOWLEDGE_PROMPT_CACHE_ENABLED=true
MADEINOZ_KNOWLEDGE_PROMPT_CACHE_METRICS_ENABLED=true
```

### Ports

| Port | Service | Environment |
|------|---------|-------------|
| 8000 | MCP Server | Production |
| 8001 | MCP Server | Development |
| 7474 | Neo4j Browser | Production |
| 7475 | Neo4j Browser | Development |
| 9090 | Prometheus Metrics | Production |
| 9091 | Prometheus Metrics | Development |

### Key Metrics

| Metric | What It Measures |
|--------|------------------|
| `graphiti_api_cost_total` | Total USD spent on LLM API |
| `graphiti_total_tokens_total` | Total tokens consumed |
| `graphiti_cache_hit_rate` | Cache effectiveness (%) |
| `graphiti_llm_request_duration_seconds` | Request latency |
| `graphiti_llm_errors_total` | API error count |

### Limits & Constraints

| Limit | Default | Configurable | Notes |
|-------|---------|--------------|-------|
| **Rate limit** | 60 req/60s per IP | Yes | `RATE_LIMIT_MAX_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS` |
| **Concurrent LLM requests** | 10 | Yes | `SEMAPHORE_LIMIT` |
| **Search results (nodes)** | 10 | Yes | `max_nodes` parameter |
| **Search results (facts)** | 10 | Yes | `max_facts` parameter |
| **Search results (episodes)** | 10 | Yes | `max_episodes` parameter |
| **Cache minimum tokens** | 1024 | No | Requests < 1024 tokens skip caching |
| **Episode body size** | No limit | N/A | Limited only by LLM context window |

**Note:** Episode body size is not explicitly limited. Very large episodes (>100KB) may cause slow processing or LLM context overflow. For bulk imports, consider chunking large documents.

## Credits

- **Knowledge graph engine**: [Graphiti](https://github.com/getzep/graphiti) by Zep AI
- **Graph databases**: [Neo4j](https://neo4j.com/) and [FalkorDB](https://www.falkordb.com/)
- **Part of**: [Personal AI Infrastructure (PAI)](https://github.com/danielmiessler/PAI)
