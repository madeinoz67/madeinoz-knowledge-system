---
title: "Configuration Reference"
description: "Complete configuration guide for the Madeinoz Knowledge System"
---

# Configuration Reference

## Overview

All Madeinoz Knowledge System configuration is managed through your PAI environment file. This document describes every available configuration option.

## Configuration Location

**Primary:** `~/.claude/.env` (or `$PAI_DIR/.env`)

This is the single source of truth for all Madeinoz Knowledge System settings. The `config/.env.example` file in the pack is a reference template only.

## Configuration File Format

The configuration file uses standard shell environment variable syntax:

```bash
# Comments start with #
VARIABLE_NAME=value
MULTI_LINE_VALUE="can span lines with quotes"
NUMERIC_VALUE=123
BOOLEAN_VALUE=true
```

## LLM Provider Configuration

### Provider Selection

```bash
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openai
```

**Valid values:**
- `openai` - OpenAI API or OpenAI-compatible providers (OpenRouter, Together, etc.)
- `anthropic` - Anthropic Claude API
- `gemini` - Google Gemini API
- `groq` - Groq API
- `ollama` - Local Ollama server

### Model Selection

```bash
MADEINOZ_KNOWLEDGE_MODEL_NAME=gpt-4o-mini
```

**Recommended models:**
- `gpt-4o-mini` (OpenAI) - Best balance of cost and quality
- `google/gemini-2.0-flash-001` (OpenRouter) - Cheapest working model
- `openai/gpt-4o` (OpenRouter) - Fastest extraction
- `meta-llama/llama-3.1-8b-instruct` (OpenRouter) - Lowest cost (may have validation issues)

### API Keys

```bash
MADEINOZ_KNOWLEDGE_OPENAI_API_KEY=sk-your-openai-key-here
MADEINOZ_KNOWLEDGE_ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
MADEINOZ_KNOWLEDGE_GOOGLE_API_KEY=your-google-api-key
MADEINOZ_KNOWLEDGE_GROQ_API_KEY=gsk-your-groq-key
```

**Important:** Only include the API key for your chosen provider.

### Custom Base URL (OpenAI-Compatible Providers)

```bash
MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

**Common values:**
- `https://openrouter.ai/api/v1` - OpenRouter
- `https://api.together.xyz/v1` - Together AI
- `https://api.fireworks.ai/inference/v1` - Fireworks AI
- `https://api.deepinfra.com/v1/openai` - DeepInfra
- `http://localhost:11434/v1` - Local Ollama

**For Ollama, use:**
```bash
MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL=http://host.docker.internal:11434/v1
# On Linux, replace host.docker.internal with your Ollama server IP
```

## Embedder Configuration

### Embedder Provider

```bash
MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER=openai
```

**Valid values:**
- `openai` - OpenAI API or OpenAI-compatible providers
- `anthropic` - Anthropic (limited embedding support)
- `ollama` - Local Ollama embeddings (recommended for cost)

### Embedding Model

```bash
MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL=mxbai-embed-large
```

**Recommended models:**
- `mxbai-embed-large` (Ollama) - FREE, 87ms, 73.9% quality
- `text-embedding-3-small` (OpenAI) - $0.02/1M, 78.2% quality
- `BAAI/bge-large-en-v1.5` (Together AI) - Fast, high quality

### Embedding Dimensions

```bash
MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS=1024
```

**Important:** Must match the embedding model's output dimensions:
- `mxbai-embed-large` → `1024`
- `text-embedding-3-small` → `1536`
- `text-embedding-3-large` → `3072`
- `nomic-embed-text` → `768`

**⚠️ CRITICAL:** Changing embedding models breaks existing data. All vectors must have identical dimensions for Neo4j vector search to work. If you change embedding models, you must clear the graph and re-add all knowledge.

### Embedder Base URL

```bash
MADEINOZ_KNOWLEDGE_EMBEDDER_BASE_URL=http://host.docker.internal:11434/v1
```

Set only if using Ollama or another OpenAI-compatible embedder provider.

## Database Backend Configuration

### Database Type

```bash
MADEINOZ_KNOWLEDGE_DATABASE_TYPE=neo4j
```

**Valid values:**
- `neo4j` (default) - Native graph database, better special character handling
- `falkordb` - Redis-based, simpler setup, lower resources

### Neo4j Configuration

```bash
MADEINOZ_KNOWLEDGE_NEO4J_URI=bolt://madeinoz-knowledge-neo4j:7687
MADEINOZ_KNOWLEDGE_NEO4J_USER=neo4j
MADEINOZ_KNOWLEDGE_NEO4J_PASSWORD=madeinozknowledge
MADEINOZ_KNOWLEDGE_NEO4J_DATABASE=neo4j
```

**Default values work with docker-compose setup.**

**For external Neo4j:**
```bash
MADEINOZ_KNOWLEDGE_NEO4J_URI=bolt://your-neo4j-server:7687
MADEINOZ_KNOWLEDGE_NEO4J_USER=your-username
MADEINOZ_KNOWLEDGE_NEO4J_PASSWORD=your-password
```

### FalkorDB Configuration

```bash
MADEINOZ_KNOWLEDGE_FALKORDB_HOST=madeinoz-knowledge-falkordb
MADEINOZ_KNOWLEDGE_FALKORDB_PORT=6379
```

**For external FalkorDB:**
```bash
MADEINOZ_KNOWLEDGE_FALKORDB_HOST=your-redis-server
MADEINOZ_KNOWLEDGE_FALKORDB_PORT=6379
```

## Knowledge Graph Configuration

### Group ID

```bash
MADEINOZ_KNOWLEDGE_GROUP_ID=main
```

Organizes knowledge into logical groups. Enables multiple isolated knowledge graphs:

```bash
# Create separate groups for different domains
MADEINOZ_KNOWLEDGE_GROUP_ID=main          # Default personal knowledge
MADEINOZ_KNOWLEDGE_GROUP_ID=research      # Research findings
MADEINOZ_KNOWLEDGE_GROUP_ID=osint-intel   # OSINT/CTI data
```

Multiple groups can be searched together using the search workflows.

## Performance Configuration

### Concurrency/Semaphore Limit

```bash
MADEINOZ_KNOWLEDGE_SEMAPHORE_LIMIT=10
```

Controls concurrent API requests to LLM provider. Tune based on API rate limits:

| Tier | Rate Limit | Recommended | Cost |
|------|-----------|-------------|------|
| Free | 0 RPM | 1-2 | $0/month |
| Tier 1 | 10 RPM | 3-5 | $5/month |
| Tier 2 | 60 RPM | 8-10 | $20/month |
| Tier 3 | 500 RPM | 10-15 | $100/month |
| Tier 4 | 5000+ RPM | 20-50 | $250/month |

**If experiencing rate limit errors:**
1. Lower this value (e.g., 5)
2. Upgrade your API tier
3. Check `MADEINOZ_KNOWLEDGE_OPENAI_API_KEY` has credits/quota

## Neo4j-Specific Features

### Search All Groups (Neo4j only)

```bash
MADEINOZ_KNOWLEDGE_SEARCH_ALL_GROUPS=true
```

When enabled, searches automatically query all available group_ids without explicitly specifying them. This ensures knowledge stored in different groups is discoverable:

```bash
# With SEARCH_ALL_GROUPS=true:
# Finds knowledge in: main, research, osint-intel, etc.

# With SEARCH_ALL_GROUPS=false:
# Only searches specified group_ids (original behavior)
```

**Default:** `true` (enabled)

**Cache duration:** 30 seconds (balance between performance and freshness)

## Telemetry Configuration

### Telemetry Enabled

```bash
MADEINOZ_KNOWLEDGE_GRAPHITI_TELEMETRY_ENABLED=false
```

Controls whether Graphiti sends anonymous telemetry. Default is `false` (disabled).

## Query Sanitization (FalkorDB Only)

For FalkorDB backend, special characters in group_ids and search queries are automatically sanitized to prevent Lucene query syntax errors.

**Escaped characters:** `+ - && || ! ( ) { } [ ] ^ " ~ * ? : \ /`

Example:
```
Input:  group_id:madeinoz-threat-intel
Output: group_id:"madeinoz-threat-intel"
```

This is automatic and transparent.

## Legacy Configuration (Deprecated)

These variables are deprecated in favor of `MADEINOZ_KNOWLEDGE_*` prefixed versions:

```bash
# Old style (still supported as fallback)
OPENAI_API_KEY=sk-your-key
ANTHROPIC_API_KEY=sk-ant-your-key

# New style (preferred)
MADEINOZ_KNOWLEDGE_OPENAI_API_KEY=sk-your-key
MADEINOZ_KNOWLEDGE_ANTHROPIC_API_KEY=sk-ant-your-key
```

**Benefits of migration:**
- Isolated configuration per pack
- No conflicts with other tools
- Better organization in .env file

## Configuration Examples

### Minimal Setup (Ollama LLM + Local Embeddings)

```bash
# LLM - must use cloud provider due to Graphiti limitations
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openai
MADEINOZ_KNOWLEDGE_MODEL_NAME=openai/gpt-4o-mini
MADEINOZ_KNOWLEDGE_OPENAI_API_KEY=sk-or-v1-your-key
MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL=https://openrouter.ai/api/v1

# Embeddings - free local Ollama
MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER=openai
MADEINOZ_KNOWLEDGE_EMBEDDER_BASE_URL=http://host.docker.internal:11434/v1
MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL=mxbai-embed-large
MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS=1024

# Database
MADEINOZ_KNOWLEDGE_DATABASE_TYPE=neo4j

# Group
MADEINOZ_KNOWLEDGE_GROUP_ID=main
```

### Premium Setup (All Cloud)

```bash
# LLM
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openai
MADEINOZ_KNOWLEDGE_MODEL_NAME=gpt-4o
MADEINOZ_KNOWLEDGE_OPENAI_API_KEY=sk-your-openai-key

# Embeddings
MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER=openai
MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL=text-embedding-3-small

# Database
MADEINOZ_KNOWLEDGE_DATABASE_TYPE=neo4j

# Performance
MADEINOZ_KNOWLEDGE_SEMAPHORE_LIMIT=20
```

### Multi-Group CTI Setup

```bash
# LLM with special character support (Neo4j)
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openai
MADEINOZ_KNOWLEDGE_MODEL_NAME=gpt-4o
MADEINOZ_KNOWLEDGE_OPENAI_API_KEY=sk-your-key

# Embeddings
MADEINOZ_KNOWLEDGE_EMBEDDER_BASE_URL=http://host.docker.internal:11434/v1
MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL=mxbai-embed-large

# Database - Neo4j for hyphenated identifiers
MADEINOZ_KNOWLEDGE_DATABASE_TYPE=neo4j
MADEINOZ_KNOWLEDGE_NEO4J_URI=bolt://madeinoz-knowledge-neo4j:7687

# Multiple groups for CTI domains
MADEINOZ_KNOWLEDGE_GROUP_ID=main
# Create additional groups by using different group_id in workflows

# Search all groups automatically
MADEINOZ_KNOWLEDGE_SEARCH_ALL_GROUPS=true
```

## Verification

To verify your configuration is correct:

```bash
# Check configuration is loaded
grep MADEINOZ_KNOWLEDGE ~/.claude/.env

# Verify API key is set (don't expose the value)
grep -c MADEINOZ_KNOWLEDGE_OPENAI_API_KEY ~/.claude/.env

# Test connectivity
curl http://localhost:8000/health
```

## Changing Configuration

To update configuration after installation:

1. **Edit PAI .env file:**
   ```bash
   nano ~/.claude/.env
   # or: vim ~/.claude/.env
   ```

2. **Restart the server:**
   ```bash
   bun run src/skills/tools/stop.ts
   bun run src/skills/tools/start.ts
   ```

3. **Verify changes:**
   ```bash
   curl http://localhost:8000/health
   ```

## Troubleshooting

### "Invalid API key"

- Verify key is correctly copied (no spaces, correct prefix)
- Check key has available credits/quota
- Confirm key is for the right provider

### "Unknown model"

- Verify model name matches provider's catalog
- Check provider base URL is correct
- Confirm API key can access the model

### "Connection refused"

- Verify `MADEINOZ_KNOWLEDGE_*_BASE_URL` is correct
- Check firewall allows connection to provider
- Ensure Ollama server is running (if using local embeddings)

### "Rate limit exceeded"

- Lower `MADEINOZ_KNOWLEDGE_SEMAPHORE_LIMIT`
- Upgrade API tier
- Wait for rate limit window to reset

### "Vector dimension mismatch"

- Verify `MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS` matches your embedding model
- Cannot change embedding models without clearing the graph
- See "Database Backend Configuration" section for model-to-dimension mapping

## Environment Variable Precedence

Configuration is loaded in this order (later values override earlier):

1. `.env.example` in pack (reference only)
2. PAI .env file (`~/.claude/.env` or `$PAI_DIR/.env`)
3. Shell environment variables (if set directly)

Recommended: Keep all configuration in PAI .env file for consistency.
