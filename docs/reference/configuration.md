---
title: "Configuration Reference"
description: "Complete configuration guide for the Madeinoz Knowledge System"
---

<!-- AI-FRIENDLY SUMMARY
System: Madeinoz Knowledge System Configuration
Purpose: Complete reference for all configuration options and environment variables
Configuration File: ~/.claude/.env (or $PAI_DIR/.env) - single source of truth
Reference Template: config/.env.example in the pack (NOT used directly)

Environment Prefix: MADEINOZ_KNOWLEDGE_*

Key Configuration Sections:
- LLM Provider: PROVIDER, MODEL_NAME, API_KEY, BASE_URL
- Database: BACKEND (neo4j/falkordb), NEO4J_URI, FALKORDB_URI
- Memory Decay (Feature 009): DECAY_CONFIG_FILE, MAINTENANCE_SCHEDULE, SEARCH_WEIGHTS
- Cache: CACHE_ENABLED, CACHE_MAX_SIZE, CACHE_TTL_SECONDS
- Memory Sync: SYNC_LEARNING_ALGORITHM, SYNC_LEARNING_SYSTEM, SYNC_RESEARCH

LLM Providers: openai, anthropic, gemini, groq, ollama
Database Backends: neo4j (default, ports 7474/7687), falkordb (ports 3000/6379)

Feature 009 Configuration: config/decay-config.yaml (copied into container at build time)
Requires rebuild: Yes, after modifying docker/patches/ or config/decay-config.yaml

Default Ports:
- MCP Server: 8000
- Neo4j Browser: 7474, Bolt: 7687
- FalkorDB UI: 3000, Redis: 6379
- Metrics: 9090 (prod) / 9091 (dev)
- Grafana: 3001 (prod) / 3002 (dev)
-->

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

- `arcee-ai/trinity-large-preview:free` (OpenRouter) - **FREE model that passes all tests**
- `arcee-ai/trinity-mini:free` (OpenRouter) - **FREE alternative that passes all tests**
- `gpt-4o-mini` (OpenAI) - Best balance of cost and quality
- `google/gemini-2.0-flash-001` (OpenRouter) - Fast, reliable, NOT being retired
- `openai/gpt-4o` (OpenRouter) - Fastest extraction
- `meta-llama/llama-3.1-8b-instruct` (OpenRouter) - Lowest cost (may have validation issues)

!!! warning "Gemini Retirement Notice"
    `google/gemini-2.0-flash-001` **will be retired in March 2026**. Switch to either Trinity model as free alternatives:
    - `arcee-ai/trinity-large-preview:free` (recommended)
    - `arcee-ai/trinity-mini:free` (faster)

!!! success "Free Trinity Models"
    Both Trinity models are **free** via OpenRouter and successfully pass all Graphiti entity extraction tests:
    - `arcee-ai/trinity-large-preview:free` - Larger model, more detailed extraction
    - `arcee-ai/trinity-mini:free` - Smaller model, faster processing (~16s)

    These are excellent options for cost-conscious users, especially with Gemini retiring in March 2026.

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

### Rate Limiting

```bash
RATE_LIMIT_MAX_REQUESTS=60
RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_ENABLED=true
```

Controls request rate limiting per IP address. Protects against abuse and DoS attacks.

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_MAX_REQUESTS` | 60 | Maximum requests per time window per IP |
| `RATE_LIMIT_WINDOW_SECONDS` | 60 | Time window in seconds |
| `RATE_LIMIT_ENABLED` | true | Set to `false` to disable (not recommended for production) |

**Note:** Rate limiting only applies to HTTP transport mode. SSE/stdio modes do not use rate limiting.

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

### Prompt Caching

```bash
# Prompt caching is DISABLED by default - set to true to enable
MADEINOZ_KNOWLEDGE_PROMPT_CACHE_ENABLED=true
```

**Default:** `false` (disabled)

Controls prompt caching for Gemini models via OpenRouter. When enabled, the system uses explicit `cache_control` markers in requests (similar to Anthropic's approach), not implicit caching. The `/chat/completions` endpoint supports multipart format with cache control markers.

!!! success "Now Available for Gemini"
    Prompt caching is now functional for Gemini models on OpenRouter. The system routes Gemini models through the `/chat/completions` endpoint which supports multipart format with cache control markers. Set to `true` to enable caching and reduce costs on repeated prompts.

For detailed metrics documentation, see the [Observability & Metrics](observability.md) reference.

## LKAP Configuration (Feature 022/023)

!!! info "Feature 022/023: Local Knowledge Augmentation Platform"
    LKAP adds RAG capabilities with automatic document ingestion, semantic search, and evidence-based knowledge promotion. Uses Qdrant (69MB Docker image) as the vector database. See [LKAP Quickstart](../usage/lkap-quickstart.md) for complete user guide.

### Qdrant Configuration

Qdrant provides lightweight vector database storage with 69MB Docker image and 626 QPS performance.

```bash
# Qdrant API endpoint
MADEINOZ_KNOWLEDGE_QDRANT_URL=http://localhost:6333

# Optional Qdrant API key for authentication (cloud deployments)
MADEINOZ_KNOWLEDGE_QDRANT_API_KEY=your-qdrant-api-key

# Collection name for document chunks
MADEINOZ_KNOWLEDGE_QDRANT_COLLECTION=lkap_documents
```

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_URL` | `http://localhost:6333` | Qdrant API endpoint |
| `QDRANT_API_KEY` | (none) | Optional authentication key (cloud only) |
| `QDRANT_COLLECTION` | `lkap_documents` | Collection name for chunks |

### Embedding Configuration

LKAP requires embeddings with 1024+ dimensions for high-quality semantic search. Uses Ollama with bge-large-en-v1.5 by default.

```bash
# Embedding dimension (1024 for bge-large-en-v1.5)
MADEINOZ_KNOWLEDGE_QDRANT_EMBEDDING_DIMENSION=1024

# Embedding model selection (ollama for local operation)
MADEINOZ_KNOWLEDGE_OLLAMA_EMBEDDING_MODEL=bge-large-en-v1.5
```

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_EMBEDDING_DIMENSION` | `1024` | Embedding vector dimension |
| `OLLAMA_EMBEDDING_MODEL` | `bge-large-en-v1.5` | Ollama embedding model |

**Embedding Model Options:**

| Model | Dimensions | Provider | Notes |
|-------|------------|----------|-------|
| `bge-large-en-v1.5` | 1024 | Ollama | Default, free, high quality |
| `mxbai-embed-large` | 1024 | Ollama | Alternative option |
| `nomic-embed-text` | 768 | Ollama | Smaller dimension |

### Chunking Configuration

Documents are split into chunks for semantic search using tiktoken with heading-aware boundaries.

```bash
# Chunking configuration (semantic, heading-aware)
MADEINOZ_KNOWLEDGE_QDRANT_CHUNK_SIZE_MIN=512
MADEINOZ_KNOWLEDGE_QDRANT_CHUNK_SIZE_MAX=768
MADEINOZ_KNOWLEDGE_QDRANT_CHUNK_OVERLAP=100
```

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_CHUNK_SIZE_MIN` | `512` | Minimum chunk size (tokens) |
| `QDRANT_CHUNK_SIZE_MAX` | `768` | Maximum chunk size (tokens) |
| `QDRANT_CHUNK_OVERLAP` | `100` | Overlap between chunks (tokens) |

### Search Configuration

Control search result quality and logging behavior.

```bash
# Search confidence threshold (chunks below 0.70 are not returned)
MADEINOZ_KNOWLEDGE_QDRANT_CONFIDENCE_THRESHOLD=0.70

# Logging level
MADEINOZ_KNOWLEDGE_QDRANT_LOG_LEVEL=INFO
```

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_CONFIDENCE_THRESHOLD` | `0.70` | Minimum confidence for results (0.0-1.0) |
| `QDRANT_LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

### Ollama Configuration

For fully local operation without external API calls.

```bash
# Ollama API endpoint
MADEINOZ_KNOWLEDGE_OLLAMA_BASE_URL=http://ollama:11434

# Ollama embedding model (BGE-large: 1024 dimensions, minimum requirement)
MADEINOZ_KNOWLEDGE_OLLAMA_EMBEDDING_MODEL=bge-large-en-v1.5

# Comma-separated list of models to pull on startup
# bge-large-en-v1.5 provides 1024 dimension embeddings
MADEINOZ_KNOWLEDGE_OLLAMA_MODELS=bge-large-en-v1.5

# Resource limits for Ollama (adjust based on host hardware)
# 0 = CPU only, 1+ = number of GPU layers to offload
MADEINOZ_KNOWLEDGE_OLLAMA_NUM_GPU=0
MADEINOZ_KNOWLEDGE_OLLAMA_NUM_THREAD=4
```

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama API endpoint |
| `OLLAMA_EMBEDDING_MODEL` | `bge-large-en-v1.5` | Ollama embedding model |
| `OLLAMA_MODELS` | `bge-large-en-v1.5` | Models to pull on startup |
| `OLLAMA_NUM_GPU` | `0` | GPU layers (0 = CPU only) |
| `OLLAMA_NUM_THREAD` | `4` | CPU threads for inference |

### Docker Commands

```bash
# Start RAGFlow vector database
docker compose -f docker/docker-compose-ragflow.yml up -d

# Start Ollama (optional - for fully local embeddings)
docker compose -f docker/docker-compose-ollama.yml up -d

# Full LKAP stack (Neo4j + RAGFlow + Ollama)
docker compose -f src/skills/server/docker-compose-neo4j.yml up -d
docker compose -f docker/docker-compose-ragflow.yml up -d
docker compose -f docker/docker-compose-ollama.yml up -d
```

### Document Storage

```bash
knowledge/
├── inbox/          # Drop PDFs, markdown, text files here for ingestion
└── processed/      # Canonical storage after successful ingestion
```

## Memory Decay Configuration (Feature 009)

!!! info "Feature 009: Memory Decay Scoring"
    The memory decay system automatically prioritizes important memories, allows stale information to fade, and maintains sustainable graph growth. See [Memory Decay & Lifecycle Management](../usage/memory-decay.md) for complete user guide.

### Configuration File

**Location:** `config/decay-config.yaml`

This YAML file controls all memory decay behavior. It is copied into the Docker container at build time.

**To modify configuration:**

1. Edit `config/decay-config.yaml`
2. Rebuild the Docker image: `docker build -f docker/Dockerfile -t madeinoz-knowledge-system:local .`
3. Restart containers: `bun run server-cli stop && bun run server-cli start --dev`

### Decay Thresholds

Control when memories transition between lifecycle states:

```yaml
decay:
  thresholds:
    dormant:
      days: 30           # Days inactive before ACTIVE → DORMANT
      decay_score: 0.3   # Decay score threshold for transition
    archived:
      days: 90           # Days inactive before DORMANT → ARCHIVED
      decay_score: 0.6   # Decay score threshold for transition
    expired:
      days: 180          # Days inactive before ARCHIVED → EXPIRED
      decay_score: 0.9   # Decay score threshold for transition
      max_importance: 3  # Only expire if importance ≤ 3
```

**Lifecycle states:**

- **ACTIVE** - Recently accessed, full relevance
- **DORMANT** - Not accessed 30+ days, lower search priority
- **ARCHIVED** - Not accessed 90+ days, much lower priority
- **EXPIRED** - Marked for deletion (soft-delete)
- **SOFT_DELETED** - Deleted but recoverable for 90 days

See [Memory Decay Guide](../usage/memory-decay.md#lifecycle-states) for details.

### Maintenance Schedule

Configure automatic maintenance operations:

```yaml
decay:
  maintenance:
    batch_size: 500             # Memories to process per batch
    max_duration_minutes: 10    # Maximum maintenance run time
    schedule_interval_hours: 24 # Hours between automatic runs (0 = disabled)
```

**What maintenance does:**

- Recalculates decay scores for all memories
- Transitions memories between lifecycle states
- Soft-deletes expired memories (90-day retention)
- Generates health metrics for Grafana

**To disable automatic maintenance:** Set `schedule_interval_hours: 0`

### Search Weights

Configure how search results are ranked:

```yaml
decay:
  weights:
    semantic: 0.60    # Vector similarity weight (0.0-1.0)
    recency: 0.25     # Temporal freshness weight (0.0-1.0)
    importance: 0.15  # Importance score weight (0.0-1.0)
```

**Must sum to 1.0**

**Formula:** `weighted_score = (semantic × 0.60) + (recency × 0.25) + (importance × 0.15)`

**Tuning guidelines:**

- Want recent stuff more? Increase `recency`
- Only care about accuracy? Increase `semantic`
- Always show important stuff? Increase `importance`

See [Weighted Search Results](../usage/memory-decay.md#weighted-search-results) for examples.

### Classification Defaults

Configure fallback values when LLM is unavailable:

```yaml
classification:
  default_importance: 3  # MODERATE (1-5)
  default_stability: 3   # MODERATE (1-5)
```

**Importance levels:** 1=TRIVIAL, 2=LOW, 3=MODERATE, 4=HIGH, 5=CORE
**Stability levels:** 1=VOLATILE, 2=LOW, 3=MODERATE, 4=HIGH, 5=PERMANENT

### Permanent Memory Thresholds

Configure which memories are exempt from decay:

```yaml
permanent:
  importance_threshold: 4  # Minimum importance for permanent
  stability_threshold: 4   # Minimum stability for permanent
```

Memories with **importance ≥4 AND stability ≥4** are classified as **PERMANENT**:

- Never accumulate decay
- Never transition lifecycle states
- Exempt from archival and deletion
- Always prioritized in search

### Half-Life Configuration

Base decay rate (adjusted by stability factor):

```yaml
decay:
  base_half_life_days: 180  # Base half-life in days (1-365)
```

**How it works:**

- Stability 1 (VOLATILE): 0.33× half-life (60 days)
- Stability 3 (MODERATE): 1.0× half-life (180 days)
- Stability 5 (PERMANENT): ∞ half-life (never decays)

Higher values = slower decay. See [Decay Score](../usage/memory-decay.md#decay-score-00-10) for details.

### Retention Policy

Configure soft-delete retention period:

```yaml
decay:
  retention:
    soft_delete_days: 90  # Days to retain soft-deleted memories
```

Soft-deleted memories are permanently purged after this period. Recovery only possible within the retention window.

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

## System Limits Summary

All configurable limits in one place:

| Limit | Default | Variable | Notes |
|-------|---------|----------|-------|
| **Rate limit** | 60 req/60s per IP | `RATE_LIMIT_MAX_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS` | HTTP mode only |
| **Concurrent LLM requests** | 10 | `SEMAPHORE_LIMIT` | Tune based on API tier |
| **Search results (nodes)** | 10 | MCP `max_nodes` param | Per-request |
| **Search results (facts)** | 10 | MCP `max_facts` param | Per-request |
| **Search results (episodes)** | 10 | MCP `max_episodes` param | Per-request |
| **Cache minimum tokens** | 1024 | N/A | Requests < 1024 tokens skip caching |
| **Episode body size** | No limit | N/A | Bounded by LLM context window |

### Content Size Guidelines

While there's no hard limit on episode body size, consider these guidelines:

| Content Size | Behavior |
|--------------|----------|
| < 10 KB | Optimal - fast processing, reliable extraction |
| 10-50 KB | Good - may take longer to process |
| 50-100 KB | Acceptable - consider chunking for bulk import |
| > 100 KB | Not recommended - may hit LLM context limits or timeout |

**For large documents:** Use the bulk import workflow which automatically handles chunking. See [Advanced Usage](../usage/advanced.md).

## Environment Variable Precedence

Configuration is loaded in this order (later values override earlier):

1. `.env.example` in pack (reference only)
2. PAI .env file (`~/.claude/.env` or `$PAI_DIR/.env`)
3. Shell environment variables (if set directly)

Recommended: Keep all configuration in PAI .env file for consistency.

## Ontology Configuration (Feature 018)

The Knowledge System supports custom entity and relationship types through ontology configuration. This enables domain-specific knowledge modeling for Cyber Threat Intelligence (CTI), Open Source Intelligence (OSINT), and other specialized domains.

### Configuration File

**Location:** `config/ontology-types.yaml`

This file is copied into the Docker container at build time. Rebuild after changes:

```bash
# 1. Edit configuration
nano config/ontology-types.yaml

# 2. Rebuild Docker image
docker build -f docker/Dockerfile -t madeinoz-knowledge-system:local .

# 3. Restart containers
bun run server-cli stop
bun run server-cli start --dev
```

### Entity Type Configuration

Entity types define domain-specific entities (ThreatActor, Malware, Vulnerability, etc.):

```yaml
entity_types:
  - name: "ThreatActor"
    description: "Actor responsible for cyber threats"
    permanent: false
    decay_config:
      half_life_days: 180  # Longer half-life for slow-changing CTI data
      importance_floor: 0.5
      stability_multiplier: 1.2
    attributes:
      - name: "aliases"
        type: "list"
        required: false
        description: "Alternative names for the threat actor"
      - name: "country"
        type: "string"
        required: false
```

**Entity Type Properties:**

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | string | Yes | Unique identifier for the entity type |
| `description` | string | Yes | Human-readable description |
| `permanent` | boolean | No | If true, entities exempt from decay (default: false) |
| `decay_config` | object | No | Custom decay settings (half_life_days, importance_floor, stability_multiplier) |
| `attributes` | list | No | Custom attributes for this entity type |

### Configuration Scope: What You CAN vs CANNOT Change

**IMPORTANT:** The ontology configuration file allows customization of **existing** entity and relationship types. Creating entirely **new** entity types requires Python code changes.

#### What You CAN Configure in YAML

✅ **Customize Existing Entity Types:**

- Modify `decay_config` - Adjust half-life, importance floor, stability
- Add/remove `attributes` - Custom fields within existing types
- Change `permanent` flag - Mark types as exempt from decay
- Update `description`, `icon` - Display properties

✅ **Customize Existing Relationship Types:**

- Modify `description`, `forward_name`, `reverse_name`
- Change `permanent` flag
- Adjust `decay_config` for relationship types

#### What Requires CODE Changes

❌ **Creating New Entity Types (Requires Python):**

- New entity types (like `ThreatActor`, `Malware`) must be defined in code
- Modify `docker/patches/ontology_config.py` to add new `EntityTypeConfig` classes
- Update Pydantic models and validation logic
- Rebuild Docker container after code changes

❌ **Creating New Relationship Types (Requires Python):**

- New relationship types must be defined in code
- Update relationship type definitions in the ontology module

#### Example: Customizing an Existing Type

```yaml
# You CAN customize existing ThreatActor type
entity_types:
  - name: "ThreatActor"
    decay_config:
      half_life_days: 365  # Changed from default 180
    attributes:
      - name: "aliases"
        type: "list"
      # Adding custom attributes is OK
      - name: "last_seen"
        type: "datetime"
        description: "Most recent activity"
```

#### Example: What Requires Code

```yaml
# You CANNOT add entirely new entity types via YAML
entity_types:
  - name: "MyCustomType"  # ❌ This won't work!
    description: "Requires code changes"
```

To add `MyCustomType`, you would need to:

1. Edit `docker/patches/ontology_config.py`
2. Define the new entity type class
3. Add validation logic
4. Rebuild the Docker image

### Relationship Type Configuration

Relationship types define connections between entities:

```yaml
relationship_types:
  - name: "uses"
    description: "Source uses target (e.g., ThreatActor uses Malware)"
    source_entity_types: ["ThreatActor", "Campaign"]
    target_entity_types: ["Malware", "Infrastructure", "TTP"]
    bidirectional: false
    inverse_name: null
```

**Relationship Type Properties:**

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | string | Yes | Relationship name (e.g., uses, targets) |
| `description` | string | Yes | Human-readable description |
| `source_entity_types` | list | Yes | Valid source entity types |
| `target_entity_types` | list | Yes | Valid target entity types |
| `bidirectional` | boolean | No | Works in both directions (default: false) |
| `inverse_name` | string | No | Name of inverse relationship |
| `attributes` | list | No | Custom attributes |

### Decay Configuration

Custom entity types can have type-specific decay settings:

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `half_life_days` | float | 180 | Days for 50% decay (higher = slower decay) |
| `importance_floor` | float | null | Minimum importance (0-5), slows decay |
| `stability_multiplier` | float | null | Multiplier for stability (0.1-3.0) |

**Example decay configurations:**

```yaml
# Slow-changing CTI data (180-day half-life)
ThreatActor:
  half_life_days: 180
  importance_floor: 0.5
  stability_multiplier: 1.2

# Fast-changing indicators (90-day half-life)
Indicator:
  half_life_days: 90
  importance_floor: 0.3
  stability_multiplier: 0.8

# Infrastructure changes quickly (60-day half-life)
Infrastructure:
  half_life_days: 60
  importance_floor: 0.3
  stability_multiplier: 0.7
```

### Reserved Attributes

The following attribute names are reserved and cannot be used in custom entity or relationship types:

- `uuid` - Unique identifier
- `name` - Entity/relationship name
- `labels` - Neo4j node labels
- `created_at` - Creation timestamp
- `summary` - Entity summary text
- `attributes` - Attributes dictionary
- `name_embedding` - Vector embedding

### Built-in Entity Types

These entity types are always available and don't need to be defined:

- `Person` - Individuals
- `Organization` - Companies, groups
- `Location` - Places, geographic areas
- `Event` - Time-bounded occurrences
- `Object` - Physical or virtual objects
- `Document` - Documents, files
- `Topic` - Subjects, themes
- `Preference` - User preferences
- `Requirement` - Requirements, specifications
- `Procedure` - Processes, methods

### Pre-built CTI/OSINT Ontology

The system includes a pre-built ontology for CTI/OSINT work with these entity types:

**CTI Entity Types:**

- `ThreatActor` - APT groups, threat actors (180-day half-life)
- `Malware` - Malicious software families (90-day half-life)
- `Vulnerability` - CVE entries, security flaws (180-day half-life)
- `Campaign` - Coordinated attack campaigns (120-day half-life)
- `Indicator` - IOCs, hashes, IPs, domains (90-day half-life)
- `Infrastructure` - C2 servers, attack infrastructure (60-day half-life)
- `TTP` - Tactics, techniques, procedures (365-day half-life)

**OSINT Entity Types:**

- `Account` - User accounts, social media profiles
- `Domain` - Domain names
- `Email` - Email addresses
- `Phone` - Phone numbers
- `Image` - Images, media files
- `Investigation` - OSINT investigations

**Relationship Types:**

- `uses` - ThreatActor uses Malware
- `targets` - Campaign targets Organization
- `exploits` - Malware exploits Vulnerability
- `variant_of` - Malware is variant of another
- `attributed_to` - Campaign attributed to ThreatActor
- `located_at` - Infrastructure located at Location
- `owns` - Person owns Account
- `communicates_with` - ThreatActor communicates with ThreatActor

For a complete example, see `config/ontology-types.yaml` in the repository.
