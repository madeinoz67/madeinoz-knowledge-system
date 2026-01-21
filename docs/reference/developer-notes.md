# Developer Notes

## Custom Docker Image

### Why We Use a Custom Image

This project currently uses a custom Docker image (`madeinoz-knowledge-system:fixed`) instead of the official upstream images. This is a **temporary workaround** while waiting for upstream fixes to be merged.

**Upstream images we're NOT using:**
- `falkordb/graphiti-knowledge-graph-mcp:latest` (FalkorDB backend)
- `zepai/knowledge-graph-mcp:standalone` (Neo4j backend)

### Patches Applied

The custom image includes three critical patches that fix upstream issues:

#### 1. Async Iteration Bug Fix
**File:** `src/server/patches/graphiti_mcp_server.patch`
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
**File:** `src/server/patches/factories.py`
**Issue:** [Upstream GitHub Issue #1116](https://github.com/getzep/graphiti/issues/1116)
**Fix:** Added explicit Ollama embedder client and OpenAI-compatible API support

This enables:
- Ollama embeddings with custom models
- OpenRouter and other OpenAI-compatible LLM providers
- Custom embedding dimensions

#### 3. Search All Groups Functionality
**File:** `src/server/patches/graphiti_mcp_server.patch`
**Issue:** Default behavior only searches specified group_ids, making cross-group discovery impossible
**Fix:** When no `group_ids` are specified, search queries ALL groups in the knowledge graph

This is essential for PAI pack usage where knowledge may be stored across multiple groups (e.g., `osint-profiles`, `main`, `research`).

### Configuration Selection
**File:** `src/server/entrypoint.sh`
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

The Dockerfile:
1. Copies patches from `src/server/patches/`
2. Copies both config files
3. Copies `entrypoint.sh` for runtime config selection
4. Applies all patches during image build

### Migration Path to Official Images

**When upstream merges these fixes**, we will:

1. Update `src/server/lib/container.ts` to use official images:
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

2. Remove custom image build from documentation
3. Archive patches to `src/server/patches/archived/` for reference
4. Update this document with migration completion date

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
2. **Docker Compose** passes these to the container via `env_file`
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

## Password Typo Bug (Fixed)

**Issue:** `docker-compose-neo4j.yml` had inconsistent Neo4j password
**Impact:** Authentication failures with "madeinojknowledge" vs "madeinozknowledge"
**Fixed in:** Commit [insert hash] - standardized to `madeinozknowledge`

**Affected lines:**
- Line 62: `NEO4J_AUTH=neo4j/madeinozknowledge`
- Line 88: `NEO4J_PASSWORD=madeinozknowledge`

---

## Network Alias Fix (Fixed)

**Issue:** Podman requires explicit `--network-alias` for DNS service discovery
**Impact:** MCP container couldn't resolve `bolt://neo4j:7687` or `redis://falkordb:6379`
**Fixed in:** `src/server/run.ts`

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
**Fixed in:** `src/server/run.ts` lines 290-291

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
