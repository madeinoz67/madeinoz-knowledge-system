---
title: "Configuration Reference"
description: "Complete configuration guide for the Madeinoz Knowledge System"
---

# Configuration Reference

## Overview

All Knowledge System configuration is managed through your PAI environment file. This document describes every available configuration option.

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
- `ollama` - Local Ollama server or Ollama-compatible provider (apikey required)

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
MADEINOZ_KNOWLEDGE_NEO4J_URI=bolt://neo4j:7687
MADEINOZ_KNOWLEDGE_NEO4J_USER=neo4j
MADEINOZ_KNOWLEDGE_NEO4J_PASSWORD=madeinozknowledge
MADEINOZ_KNOWLEDGE_NEO4J_DATABASE=neo4j
```

**Default values work with docker-compose setup.**

**For external Neo4j:**

```bash
MADEINOZ_KNOWLEDGE_NEO4J_URI=bolt://neo4j:7687
MADEINOZ_KNOWLEDGE_NEO4J_USER=neo4j
MADEINOZ_KNOWLEDGE_NEO4J_PASSWORD=madeinozknowledge
```

### Changing Neo4j Password

#### Why This Process Is Required

Neo4j's security architecture stores credentials **inside the persistent data volume**, not in environment variables. Understanding this is critical:

1. **First Startup Behavior**: The `NEO4J_AUTH` environment variable is only read on **first startup** when no user data exists. Neo4j uses it to create the initial `neo4j` user with the specified password.

2. **Password Persistence**: After initialization, the password is stored encrypted in the `/data` volume as part of the `system` database. The `NEO4J_AUTH` environment variable is **ignored on subsequent startups**.

3. **Why Environment Variables Don't Work**: Many users expect changing `NEO4J_AUTH` to update the password—this is a common misconception. Since the password lives in the data volume, changing environment variables has no effect on existing databases.

4. **The Correct Approach**: You must use Cypher commands (`ALTER CURRENT USER` or `ALTER USER`) to modify passwords in a running database. This ensures the change is written to the `system` database where credentials are actually stored.

This design ensures that your credentials remain consistent with your data, and that accidentally changing an environment variable cannot lock you out of your database.

**Reference**: [Neo4j Operations Manual - Manage Users](https://neo4j.com/docs/operations-manual/current/authentication-authorization/manage-users/)

#### Method 1: Using Neo4j Browser (Recommended)

The Neo4j Browser provides a web interface for database administration.

1. **Open Neo4j Browser:**

   ```
   http://localhost:7474
   ```

2. **Login with current credentials:**
   - Username: `neo4j`
   - Password: (your current password, default: `madeinozknowledge`)

3. **Run the official password change command:**

   ```cypher
   ALTER CURRENT USER SET PASSWORD FROM 'current-password' TO 'new-password'
   ```

   This command requires you to know your current password and changes it atomically in the `system` database.

4. **Update your `.env` file to match:**

   ```bash
   # Edit ~/.claude/.env
   MADEINOZ_KNOWLEDGE_NEO4J_PASSWORD=new-password
   ```

   **Important:** The `.env` file must match the database password for the MCP server to connect.

5. **Restart the MCP server to apply the new password:**

   ```bash
   bun run server-cli stop
   bun run server-cli start
   ```

#### Method 2: Using Cypher Shell (Command Line)

For users who prefer command-line administration.

1. **Connect to the Neo4j container:**

   ```bash
   docker exec -it madeinoz-knowledge-neo4j cypher-shell -u neo4j -p 'current-password'
   ```

2. **Run the official password change command:**

   ```cypher
   ALTER CURRENT USER SET PASSWORD FROM 'current-password' TO 'new-password';
   ```

   Then exit the shell:

   ```
   :exit
   ```

3. **Update `.env` and restart** (same as Method 1, steps 4-5)

#### Method 3: Admin Changing Another User's Password (Enterprise)

If you have admin privileges, you can change any user's password:

```cypher
ALTER USER username SET PASSWORD 'new-password'
```

Optionally force a password change on next login:

```cypher
ALTER USER username SET PASSWORD 'new-password' CHANGE REQUIRED
```

#### Password Requirements

- Minimum 8 characters (Neo4j default)
- Avoid special characters that may cause shell escaping issues
- Store securely - this password protects your knowledge graph

#### ⚠️ CRITICAL: Never Delete Data Volumes

**NEVER use `docker compose down -v` or `podman compose down -v` to "reset" a forgotten password.** The `-v` flag deletes all data volumes, permanently destroying your knowledge graph. This data is irreplaceable.

If you've forgotten your password:

1. Try the default password: `madeinozknowledge`
2. Check your `~/.claude/.env` for `MADEINOZ_KNOWLEDGE_NEO4J_PASSWORD`
3. Use Method 1 or Method 2 above with a password you remember having set
4. If all else fails, contact the community for recovery assistance before considering any destructive action

#### Troubleshooting Password Issues

**"AuthenticationRateLimit" error:**
Neo4j blocks connections after too many failed attempts. Wait 30 seconds or restart the Neo4j container:

```bash
docker restart madeinoz-knowledge-neo4j
```

**"Authentication failed" after password change:**
The MCP server is using the old password. Ensure:

1. `.env` file has the new password
2. MCP server was restarted after the change
3. No shell environment variable is overriding the `.env` value

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
GRAPHITI_SEARCH_ALL_GROUPS=true
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

## Metrics & Observability Configuration

### Metrics Collection

```bash
MADEINOZ_KNOWLEDGE_PROMPT_CACHE_METRICS_ENABLED=true
```

Controls whether Prometheus metrics are collected and exported. Default is `true` (enabled).

**Metrics endpoint:** `http://localhost:9091/metrics` (dev) or `http://localhost:9090/metrics` (prod)

### Debug Logging

```bash
MADEINOZ_KNOWLEDGE_PROMPT_CACHE_LOG_REQUESTS=false
```

Enables detailed per-request metrics logging. When `true` and `LOG_LEVEL=DEBUG`, logs show:

```
📊 Metrics: prompt=1234, completion=567, cost=$0.000089
```

Default is `false` (disabled).

### Prompt Caching (Experimental)

```bash
MADEINOZ_KNOWLEDGE_PROMPT_CACHE_ENABLED=false
```

Controls prompt caching for Gemini models via OpenRouter. Default is `false` (disabled).

!!! warning "Currently Blocked"
    Prompt caching is blocked due to an OpenRouter API limitation. The `/responses` endpoint does not support the multipart format required for cache control markers. Metrics collection works regardless of this setting.

For detailed metrics documentation, see the [Observability & Metrics](observability.md) reference.

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
MADEINOZ_KNOWLEDGE_NEO4J_URI=bolt://neo4j:7687

# Multiple groups for CTI domains
MADEINOZ_KNOWLEDGE_GROUP_ID=main
# Create additional groups by using different group_id in workflows

# Search all groups automatically
GRAPHITI_SEARCH_ALL_GROUPS=true
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
   bun run server-cli stop
   bun run server-cli start
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
