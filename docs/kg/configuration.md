---
title: "Knowledge Memory Configuration"
description: "Configure Graphiti and Neo4j for Knowledge Memory"
---

<!-- AI-FRIENDLY SUMMARY
System: Knowledge Memory (KG) Configuration
Purpose: Environment variables and settings for Graphiti and Neo4j

Configuration Prefix: MADEINOZ_KNOWLEDGE_*

Key Variables:
- NEO4J_URI: Bolt connection URI
- NEO4J_USER: Database username
- NEO4J_PASSWORD: Database password (REQUIRED)
- MODEL_NAME: LLM for entity extraction
- EMBEDDING_MODEL: Embedding model

Database Options:
- Neo4j (default): Port 7474/7687
- FalkorDB: Port 3000/6379

LLM Options:
- gpt-4o-mini (default): Good balance of cost/quality
- gpt-4o: Better extraction, higher cost

Compatible: gpt-4o, gpt-4o-mini, Claude 3.5 Haiku, Gemini 2.0 Flash
Incompatible: Llama/Mistral variants
-->

# Knowledge Memory Configuration

Configuration options for Knowledge Memory using Graphiti and Neo4j.

## Required Variables

```bash
# Neo4j database password (REQUIRED - no default)
MADEINOZ_KNOWLEDGE_NEO4J_PASSWORD=your-secure-password
```

## Database Settings

### Neo4j (Default)

| Variable | Default | Description |
|----------|---------|-------------|
| `MADEINOZ_KNOWLEDGE_NEO4J_URI` | `bolt://localhost:7687` | Bolt connection URI |
| `MADEINOZ_KNOWLEDGE_NEO4J_USER` | `neo4j` | Database username |
| `MADEINOZ_KNOWLEDGE_NEO4J_PASSWORD` | *(required)* | Database password |

### FalkorDB (Alternative)

| Variable | Default | Description |
|----------|---------|-------------|
| `MADEINOZ_KNOWLEDGE_GRAPH_BACKEND` | `neo4j` | Set to `falkordb` to use FalkorDB |
| `MADEINOZ_KNOWLEDGE_FALKORDB_HOST` | `localhost` | FalkorDB host |
| `MADEINOZ_KNOWLEDGE_FALKORDB_PORT` | `6379` | Redis port |

## LLM Settings

### Model Selection

| Variable | Default | Description |
|----------|---------|-------------|
| `MADEINOZ_KNOWLEDGE_MODEL_NAME` | `gpt-4o-mini` | LLM for entity extraction |
| `MADEINOZ_KNOWLEDGE_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |

### Model Compatibility

**Working Models:**
- `gpt-4o-mini` (recommended) - Good balance of cost and quality
- `gpt-4o` - Better extraction for complex knowledge
- `claude-3-5-haiku` via OpenRouter
- `gemini-2.0-flash` via OpenRouter

**Incompatible Models:**
- All Llama variants (Pydantic validation errors)
- All Mistral variants (Pydantic validation errors)

### LLM Provider Configuration

The system supports multiple LLM providers:

```bash
# OpenAI (default)
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...

# Anthropic via OpenRouter
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...
MADEINOZ_KNOWLEDGE_MODEL_NAME=anthropic/claude-3.5-haiku

# Google via OpenRouter
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openrouter
MADEINOZ_KNOWLEDGE_MODEL_NAME=google/gemini-2.0-flash
```

## Memory Decay Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MADEINOZ_KNOWLEDGE_DECAY_ENABLED` | `true` | Enable memory decay |
| `MADEINOZ_KNOWLEDGE_DECAY_HALF_LIFE` | `180` | Decay half-life (days) |

See [Memory Decay & Lifecycle](../usage/memory-decay.md) for details.

## Search Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MADEINOZ_KNOWLEDGE_SEARCH_LIMIT` | `10` | Default search results |
| `MADEINOZ_KNOWLEDGE_SEMAPHORE_LIMIT` | `10` | Concurrent LLM calls |

## Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `MADEINOZ_KNOWLEDGE_LOG_LEVEL` | `INFO` | Log level |

## Example Configuration

### Development

```bash
# .env.dev
MADEINOZ_KNOWLEDGE_NEO4J_URI=bolt://localhost:7687
MADEINOZ_KNOWLEDGE_NEO4J_USER=neo4j
MADEINOZ_KNOWLEDGE_NEO4J_PASSWORD=dev-password
MADEINOZ_KNOWLEDGE_MODEL_NAME=gpt-4o-mini
MADEINOZ_KNOWLEDGE_LOG_LEVEL=DEBUG
```

### Production

```bash
# .env
MADEINOZ_KNOWLEDGE_NEO4J_URI=bolt://neo4j.example.com:7687
MADEINOZ_KNOWLEDGE_NEO4J_USER=neo4j
MADEINOZ_KNOWLEDGE_NEO4J_PASSWORD=secure-production-password
MADEINOZ_KNOWLEDGE_MODEL_NAME=gpt-4o
MADEINOZ_KNOWLEDGE_DECAY_ENABLED=true
MADEINOZ_KNOWLEDGE_LOG_LEVEL=WARNING
```

## Docker Configuration

### Neo4j Container

```yaml
# src/skills/server/docker-compose-neo4j.yml
services:
  neo4j:
    image: neo4j:5.26-community
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    environment:
      - NEO4J_AUTH=neo4j/${MADEINOZ_KNOWLEDGE_NEO4J_PASSWORD}
      - NEO4J_server_memory_pagecache_size=256M
      - NEO4J_server_memory_heap_initial__size=512M
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs

volumes:
  neo4j_data:
  neo4j_logs:
```

## Cost Estimates

| Operation | Model | Cost |
|-----------|-------|------|
| Capture (entity extraction) | gpt-4o-mini | ~$0.01 per episode |
| Capture (entity extraction) | gpt-4o | ~$0.03 per episode |
| Embedding generation | text-embedding-3-small | ~$0.0001 |
| Search query embedding | text-embedding-3-small | ~$0.0001 |

**Monthly estimates:**
- Light use: ~$0.50-1.00
- Moderate use: ~$2.00-5.00
- Heavy use: ~$5.00-15.00

## Related Topics

- **[Knowledge Memory Quickstart](quickstart.md)** - Get started with KG
- **[Knowledge Memory Troubleshooting](troubleshooting.md)** - Solve common issues
- **[Knowledge Memory Concepts](concepts.md)** - Understand knowledge graphs
- **[Configuration Reference](../reference/configuration.md)** - Full configuration guide
