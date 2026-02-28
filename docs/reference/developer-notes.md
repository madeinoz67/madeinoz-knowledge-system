# Developer Notes

## Custom Docker Image

### Why We Use a Custom Image

This project currently uses a custom Docker image (`ghcr.io/madeinoz67/madeinoz-knowledge-system:latest`) instead of the official upstream images. This is a **temporary workaround** while waiting for upstream fixes to be merged.

**Published Image:**

- **Registry:** [GitHub Container Registry](https://github.com/madeinoz67/madeinoz-knowledge-system/pkgs/container/madeinoz-knowledge-system)
- **Image:** `ghcr.io/madeinoz67/madeinoz-knowledge-system:latest`

**Upstream images we're NOT using:**

- `falkordb/graphiti-knowledge-graph-mcp:latest` (FalkorDB backend)
- `zepai/knowledge-graph-mcp:standalone` (Neo4j backend)

### Patches Applied

The custom Docker image includes four critical patches applied at image build time:

#### 1. Async Iteration Bug Fix

**Issue:** [Upstream GitHub Issue - async iteration on NoneType]

**Fix:** Added None check before async for loop in `get_all_group_ids()`

```python
# Before: Would crash with "async for requires __aiter__ method, got NoneType"
records = [record async for record in result]

# After: Safe None check
if result:
    records = [record async for record in result]
else:
    group_ids = []
```

#### 2. Ollama/Custom Endpoint Support

**Issue:** [Upstream GitHub Issue #1116](https://github.com/getzep/graphiti/issues/1116)

**Fix:** Added explicit Ollama embedder client and OpenAI-compatible API support

This enables:

- Ollama embeddings with custom models
- OpenRouter and other OpenAI-compatible LLM providers
- Custom embedding dimensions

#### 3. Search All Groups Functionality

**Issue:** Default behavior only searches specified group_ids, making cross-group discovery impossible

**Fix:** When no `group_ids` are specified, search queries ALL groups in the knowledge graph

This is essential for PAI pack usage where knowledge may be stored across multiple groups (e.g., `osint-profiles`, `main`, `research`).

#### 4. Temporal Search Feature

**Issue:** Original search functionality lacked time-based filtering capabilities

**Fix:** Added `start_date` and `end_date` parameters to search functions for temporal queries

This enables:

- Time-range filtered searches (e.g., "find entities created in last 7 days")
- Historical knowledge tracking and analysis
- Temporal relationship discovery
- Episode-based timeline reconstruction

The temporal search feature integrates with the existing search API, allowing combined spatial and temporal queries for comprehensive knowledge retrieval.

### Configuration Selection

**File:** `src/skills/server/entrypoint.sh` (development) or baked into image

**Purpose:** Dynamically select the correct config file based on `DATABASE_TYPE` environment variable

```bash
case "$DATABASE_TYPE" in
  falkordb|redis)
    cp /tmp/config-falkordb.yaml /app/mcp/config/config.yaml
    ;;
  neo4j|*)
    cp /tmp/config-neo4j.yaml /app/mcp/config/config.yaml
    ;;
esac
```

Both config files are baked into the image at build time:

- `/tmp/config-neo4j.yaml`
- `/tmp/config-falkordb.yaml`

### Building the Custom Image

```bash
# From pack root directory
docker build -t madeinoz-knowledge-system:fixed .
```

The Dockerfile applies patches during the image build process:

1. Copies patch files from the patches directory
2. Copies both config files
3. Copies `entrypoint.sh` for runtime config selection
4. Applies all patches to the upstream source code during build

### Migration Path to Official Images

**When upstream merges these fixes**, we will:

1. Update `src/skills/server/lib/container.ts` to use official images:

```typescript
static readonly IMAGES = {
  falkordb: {
    database: "falkordb/falkordb:latest",
    mcp: "falkordb/graphiti-knowledge-graph-mcp:latest",  // ← Revert here
  },
  neo4j: {
    database: "neo4j:5.26.0",
    mcp: "zepai/knowledge-graph-mcp:standalone",  // ← Revert here
  },
}
```

1. Remove custom image build from documentation
2. Archive patches to `docker/patches/archived/` for reference
3. Update this document with migration completion date

**Status:** Waiting for upstream to merge fixes. Track progress at:

- Graphiti GitHub Issues
- Zep AI releases

---

## Environment Variable Prefix Workaround

### The Problem

PAI (Personal AI Infrastructure) packs must isolate their configuration to avoid conflicts with other packs. However, the Graphiti MCP server expects **unprefixed** environment variables like:

- `OPENAI_API_KEY`
- `MODEL_NAME`
- `LLM_PROVIDER`
- `NEO4J_URI`
- etc.

If every pack used these generic names, they would collide in the shared PAI `.env` file.

### The Solution: Variable Mapping

We use **prefixed variables** in the PAI `.env` file and map them to unprefixed variables inside the container.

#### In PAI .env File (`~/.claude/.env` or `$PAI_DIR/.env`)

```bash
# Pack-isolated configuration (prefixed)
MADEINOZ_KNOWLEDGE_OPENAI_API_KEY=sk-...
MADEINOZ_KNOWLEDGE_MODEL_NAME=google/gemini-2.0-flash-001
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openrouter
MADEINOZ_KNOWLEDGE_DATABASE_TYPE=neo4j
MADEINOZ_KNOWLEDGE_NEO4J_PASSWORD=madeinozknowledge
```

#### In Container (unprefixed)

The `entrypoint.sh` script automatically maps prefixed → unprefixed:

```bash
# entrypoint.sh mapping logic
test -n "$MADEINOZ_KNOWLEDGE_OPENAI_API_KEY" && export OPENAI_API_KEY="$MADEINOZ_KNOWLEDGE_OPENAI_API_KEY"
test -n "$MADEINOZ_KNOWLEDGE_MODEL_NAME" && export MODEL_NAME="$MADEINOZ_KNOWLEDGE_MODEL_NAME"
test -n "$MADEINOZ_KNOWLEDGE_LLM_PROVIDER" && export LLM_PROVIDER="$MADEINOZ_KNOWLEDGE_LLM_PROVIDER"

# Fallback to unprefixed if no prefix found (for standalone use)
test -n "$OPENAI_API_KEY" && export OPENAI_API_KEY="$OPENAI_API_KEY"
```

### How It Works

1. **PAI .env** contains only prefixed variables (`MADEINOZ_KNOWLEDGE_*`)
2. **Docker Compose** passes these to the container via a targeted `env_file`
3. **entrypoint.sh** runs before the MCP server starts
4. Script checks for prefixed variables and exports unprefixed versions
5. **MCP server** sees standard unprefixed variables it expects

### Benefits

✓ **Pack isolation** - No conflicts with other PAI packs
✓ **Portable** - Works across all PAI installations (`$PAI_DIR` or `~/.claude/`)
✓ **Backward compatible** - Fallback to unprefixed for standalone usage
✓ **Maintainable** - Single `.env` file for entire PAI system

### Fallback Strategy

The entrypoint uses a two-tier approach:

```bash
# Try prefixed first (PAI pack mode)
test -n "$MADEINOZ_KNOWLEDGE_OPENAI_API_KEY" && export OPENAI_API_KEY="$MADEINOZ_KNOWLEDGE_OPENAI_API_KEY"

# Fall back to unprefixed (standalone mode)
test -n "$OPENAI_API_KEY" && export OPENAI_API_KEY="$OPENAI_API_KEY"
```

This ensures the system works both:

- **As a PAI pack** (using prefixed variables)
- **Standalone** (using unprefixed variables)

### Example: Complete Variable Flow

```
┌─────────────────────────────────────┐
│ ~/.claude/.env (PAI central config) │
│                                     │
│ MADEINOZ_KNOWLEDGE_OPENAI_API_KEY= │
│ sk-proj-abc123...                   │
└──────────────┬──────────────────────┘
               │
               │ env_file: ${PAI_DIR:-~/.claude}/.env
               ▼
┌─────────────────────────────────────┐
│ Docker Container Environment        │
│                                     │
│ MADEINOZ_KNOWLEDGE_OPENAI_API_KEY= │
│ sk-proj-abc123...                   │
└──────────────┬──────────────────────┘
               │
               │ entrypoint.sh mapping
               ▼
┌─────────────────────────────────────┐
│ Container Runtime (after mapping)   │
│                                     │
│ OPENAI_API_KEY=sk-proj-abc123...   │
│ (unprefixed - what MCP expects)    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Graphiti MCP Server                 │
│ ✓ Reads standard OPENAI_API_KEY    │
└─────────────────────────────────────┘
```

### Adding New Configuration Variables

When adding a new config variable:

1. **Add to `.env.example`** with `MADEINOZ_KNOWLEDGE_` prefix
2. **Add mapping in `entrypoint.sh`**:

   ```bash
   test -n "$MADEINOZ_KNOWLEDGE_NEW_VAR" && export NEW_VAR="$MADEINOZ_KNOWLEDGE_NEW_VAR"
   ```

3. **Document in `docs/reference/configuration.md`**
4. **Test both prefixed and unprefixed modes**

---

## Network Alias Fix (Fixed)

**Issue:** Podman requires explicit `--network-alias` for DNS service discovery
**Impact:** MCP container couldn't resolve `bolt://neo4j:7687` or `redis://falkordb:6379`
**Fixed in:** `src/skills/server/server-cli.ts`

**Solution:**

```typescript
// FalkorDB
"--network-alias=falkordb",  // DNS alias for service discovery

// Neo4j
"--network-alias=neo4j",  // DNS alias for service discovery
```

Docker handles this automatically, but Podman requires explicit aliases.

---

## Volume Mount Conflict (Fixed)

**Issue:** Read-only volume mounts conflicted with entrypoint.sh config selection
**Impact:** MCP container crash-looped with "Read-only file system" error
**Fixed in:** `src/skills/server/server-cli.ts`

**Before (broken):**

```typescript
args.push(`-v=${configPath}:/app/mcp/config/config.yaml:ro`);
args.push(`-v=${patchesDir}/factories.py:/app/mcp/src/services/factories.py:ro`);
```

**After (fixed):**

```typescript
// Config files and patches are baked into the custom image
// The entrypoint.sh selects the correct config based on DATABASE_TYPE
```

Since the custom image has all configs and patches baked in, external mounts are not needed.

---

## Development Environment Setup

### Quick Start

For development and testing of server code changes, use `--dev` mode which provides isolated ports and environment files:

```bash
# Start in development mode
bun run server-cli start --dev

# Restart in development mode
bun run server-cli restart --dev

# Stop development containers
bun run server-cli stop
```

### Development vs Production Ports

| Service | Production | Development |
|---------|------------|-------------|
| MCP Server | 8000 | 8001 |
| Neo4j Browser | 7474 | 7475 |
| Neo4j Bolt | 7687 | 7688 |
| Prometheus Metrics | 9090 | 9091 |
| Grafana | 3001 | 3002 |

### Creating .env.dev

Development mode uses separate environment files to avoid affecting production data. Create `.env.dev` in the project root:

```bash
# Copy the example file
cp .env.example .env.dev

# Edit with your development settings
nano .env.dev
```

**Minimal .env.dev example:**

```bash
# LLM Configuration (use cheaper models for dev)
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openai
MADEINOZ_KNOWLEDGE_MODEL_NAME=openai/gpt-4o-mini
MADEINOZ_KNOWLEDGE_OPENAI_API_KEY=sk-or-v1-your-key
MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL=https://openrouter.ai/api/v1

# Embeddings (local Ollama)
MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER=ollama
MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL=mxbai-embed-large
MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS=1024
MADEINOZ_KNOWLEDGE_EMBEDDER_BASE_URL=http://host.docker.internal:11434/v1

# Database (dev credentials)
MADEINOZ_KNOWLEDGE_DATABASE_TYPE=neo4j
MADEINOZ_KNOWLEDGE_NEO4J_PASSWORD=devpassword

# RAG Configuration (Qdrant)
MADEINOZ_KNOWLEDGE_QDRANT_URL=http://localhost:6333
MADEINOZ_KNOWLEDGE_QDRANT_COLLECTION=lkap_documents_dev

# Ollama (for RAG embeddings)
MADEINOZ_KNOWLEDGE_OLLAMA_BASE_URL=http://localhost:11434
MADEINOZ_KNOWLEDGE_OLLAMA_EMBEDDING_MODEL=bge-large-en-v1.5
```

### Environment File Location

The server-cli looks for environment files in this order:

1. **Explicit path:** `--env-file /path/to/.env.dev`
2. **Project root:** `.env.dev` (for development mode)
3. **PAI config:** `$PAI_DIR/.env` or `~/.claude/.env` (default)

### Testing Container Changes

After modifying `docker/patches/*.py` or other container code:

```bash
# 1. Rebuild the Docker image
docker build -f docker/Dockerfile -t madeinoz-knowledge-system:local .

# 2. Stop existing containers
bun run server-cli stop

# 3. Start in dev mode with local image
bun run server-cli start --dev

# 4. Verify changes
bun run server-cli logs --mcp --tail 50
```

### Development Mode Flags

The `--dev` flag affects:

- **Ports:** All services use alternate ports (see table above)
- **Env files:** Uses `/tmp/madeinoz-knowledge-*-dev.env` for container config
- **Data isolation:** Dev containers use separate volumes
- **Image:** Can use local builds without affecting production

### Debugging MCP Server

To debug MCP server issues:

```bash
# View MCP server logs
bun run server-cli logs --mcp

# Follow logs in real-time
bun run server-cli logs --mcp --tail 100 -f

# Check container health
docker ps -a | grep knowledge

# Inspect container environment
docker exec -it madeinoz-knowledge-mcp-dev env | grep MADEINOZ
```

---

## Future Improvements

### When Upstream Issues Are Resolved

- [ ] Migrate back to official upstream images
- [ ] Remove custom Dockerfile
- [ ] Archive patches for reference
- [ ] Update documentation
- [ ] Simplify container.ts image references

### Potential Enhancements

- [ ] Add health check retries with exponential backoff
- [ ] Implement multi-stage Docker build for smaller image
- [ ] Add version pinning for reproducible builds
- [ ] Create integration tests for patch functionality
- [ ] Add automated upstream tracking (check for merged PRs)

---

**Last Updated:** 2026-01-21
**Maintainer:** @madeinoz67
**Upstream:** [getzep/graphiti](https://github.com/getzep/graphiti)
