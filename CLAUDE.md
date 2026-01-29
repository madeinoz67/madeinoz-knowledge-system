# madeinoz-knowledge-system Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-18

## Active Technologies
- Python 3.x (MkDocs), YAML (configuration), Markdown (content) + MkDocs 1.6+, mkdocs-material 9.5+, GitHub Actions (002-mkdocs-documentation)
- Static markdown files in `docs/` directory (002-mkdocs-documentation)
- TypeScript (ES modules, strict mode), Bun runtime + @modelcontextprotocol/sdk (existing), existing mcp-client.ts library (003-fix-issue-2)
- Neo4j (default) or FalkorDB backend via Docker/Podman containers (003-fix-issue-2)
- YAML (Docker/Podman Compose v2.x) + Docker Compose v2.x or Podman Compose (004-fix-env-file-loading)
- N/A (configuration files only) (004-fix-env-file-loading)
- Markdown (documentation), YAML (Docker/Podman Compose v2.x) + Docker Compose v2.x or Podman Compose (001-docs-compose-updates)
- N/A (documentation and configuration files only) (001-docs-compose-updates)
- TypeScript (ES modules, strict mode) with Bun runtime + @modelcontextprotocol/sdk, node:fs, node:crypto (001-configurable-memory-sync)
- Neo4j graph database via Graphiti MCP server (001-configurable-memory-sync)
- Python 3.11+ (server/patches), TypeScript/Bun (CLI/tools) + graphiti_core, Neo4j driver, FastMCP, pydantic (009-memory-decay-scoring)
- Neo4j graph database (or FalkorDB) via Graphiti (009-memory-decay-scoring)
- Python 3.11 (MCP server), TypeScript (CLI tools with Bun) + graphiti-core, neo4j, pydantic, prometheus_clien (009-memory-decay-scoring)

- TypeScript (ES modules, strict mode), Bun runtime + @modelcontextprotocol/sdk (existing), mcp-client.ts library (existing) (001-mcp-wrapper)

## Project Structure

```text
src/
tests/
```

## Commands

npm test && npm run lint

## Code Style

TypeScript (ES modules, strict mode), Bun runtime: Follow standard conventions

## Recent Changes
- 009-memory-decay-scoring: Added Python 3.11 (MCP server), TypeScript (CLI tools with Bun) + graphiti-core, neo4j, pydantic, prometheus_clien
- 009-memory-decay-scoring: Added Python 3.11+ (server/patches), TypeScript/Bun (CLI/tools) + graphiti_core, Neo4j driver, FastMCP, pydantic
- 001-configurable-memory-sync: Added TypeScript (ES modules, strict mode) with Bun runtime + @modelcontextprotocol/sdk, node:fs, node:crypto


<!-- MANUAL ADDITIONS START -->

## Memory-to-Knowledge Sync Configuration

The system syncs LEARNING and RESEARCH files from `~/.claude/MEMORY/` to the knowledge graph.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MADEINOZ_KNOWLEDGE_SYNC_LEARNING_ALGORITHM` | `true` | Enable sync for LEARNING/ALGORITHM files |
| `MADEINOZ_KNOWLEDGE_SYNC_LEARNING_SYSTEM` | `true` | Enable sync for LEARNING/SYSTEM files |
| `MADEINOZ_KNOWLEDGE_SYNC_RESEARCH` | `true` | Enable sync for RESEARCH files |
| `MADEINOZ_KNOWLEDGE_SYNC_EXCLUDE_PATTERNS` | - | Comma-separated custom exclude patterns (overrides config file) |
| `MADEINOZ_KNOWLEDGE_SYNC_MAX_FILES` | `50` | Max files per sync run (1-1000) |
| `MADEINOZ_KNOWLEDGE_SYNC_VERBOSE` | `false` | Enable verbose logging |

### CLI Usage

```bash
# Run sync manually
bun run src/hooks/sync-memory-to-knowledge.ts

# Show sync status
bun run src/hooks/sync-memory-to-knowledge.ts --status

# Sync all files (not just recent)
bun run src/hooks/sync-memory-to-knowledge.ts --all

# Dry run with verbose output
bun run src/hooks/sync-memory-to-knowledge.ts --dry-run --verbose
```

### External Configuration

Sync configuration can be customized via `config/sync-sources.json`:

```json
{
  "version": "1.0",
  "sources": [
    {
      "id": "LEARNING_ALGORITHM",
      "path": "LEARNING/ALGORITHM",
      "type": "LEARNING",
      "description": "Task execution learnings",
      "defaultEnabled": true
    }
  ],
  "customExcludePatterns": [
    "meeting notes",
    "/^draft-/i"
  ]
}
```

**Pattern types:**
- Substring match: `"meeting notes"` (case-insensitive)
- Regex: `"/^draft-/i"` (surrounded by `/`, optional flags)

### Anti-Loop Detection

The system automatically excludes knowledge-derived content from being re-synced to prevent feedback loops. Built-in patterns detect:
- MCP tool invocations (`mcp__madeinoz-knowledge__`)
- Query phrases ("what do I know about")
- Formatted search output ("Knowledge Found:", "Key Entities:")

## Codanna Code Intelligence

### CLI Syntax

Codanna supports both MCP tools and CLI commands with Unix-friendly syntax:

**Simple Commands (positional arguments):**
```bash
# Text output (DEFAULT - prefer this to save context)
codanna mcp find_symbol main
codanna mcp get_calls process_file
codanna mcp find_callers init

# JSON output (only when structured data needed)
codanna mcp find_symbol main --json
```

**Complex Commands (key:value pairs):**
```bash
# Text output (DEFAULT - prefer this)
codanna mcp search_symbols query:parse limit:10
codanna mcp semantic_search_docs query:"error handling"

# JSON output (only for parsing/piping)
codanna mcp search_symbols query:parse --json | jq '.data[].name'
```

**Important:** Prefer TEXT output - JSON fills context window quickly (3-5x more tokens).

### Search Workflow

1. **Semantic Search** (start here):
   ```bash
   codanna mcp semantic_search_with_context query:"your search" limit:5
   ```

2. **Read Code** using line ranges from search results:
   - Formula: `limit = end_line - start_line + 1`
   - Use Read tool with `offset` and `limit` parameters

3. **Explore Details**:
   ```bash
   codanna retrieve describe symbol_id:896
   ```

4. **Follow Relationships**:
   ```bash
   codanna retrieve callers symbol_id:896
   codanna retrieve calls symbol_id:896
   ```

### Document Search

```bash
codanna mcp search_documents query:"installation guide" limit:5
```

### Tips

- Read only line ranges provided (saves tokens)
- Use symbol_id to chain commands
- Add `lang:rust` to filter by language
- Use `rg` (ripgrep) for pattern matching: `rg "pattern" src/`

## Memory Decay Scoring Configuration

The knowledge system implements automatic memory decay scoring, importance classification, and lifecycle management to prioritize relevant memories and maintain sustainable graph growth.

### Decay Configuration

**Configuration File:** `config/decay-config.yaml`

```yaml
decay:
  # Base half-life for decay calculation (days)
  base_half_life_days: 30

  # Soft-delete retention window (days)
  retention:
    soft_delete_days: 90

  # Lifecycle state transition thresholds
  thresholds:
    dormant:
      days: 30
      decay_score: 0.3
    archived:
      days: 90
      decay_score: 0.5
    expired:
      days: 180
      decay_score: 0.7
      max_importance: 2

  # Weighted search weights (must sum to 1.0)
  weights:
    semantic: 0.60
    recency: 0.25
    importance: 0.15

  # Classification defaults
  classification:
    default_importance: 3
    default_stability: 3
    permanent_thresholds:
      importance: 4
      stability: 4

  # Maintenance settings
  maintenance:
    batch_size: 500
    max_duration_seconds: 600  # 10 minutes
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DECAY_BASE_HALF_LIFE_DAYS` | `30` | Base half-life for decay calculation |
| `DECAY_DORMANT_THRESHOLD_DAYS` | `30` | Days before ACTIVE → DORMANT |
| `DECAY_ARCHIVED_THRESHOLD_DAYS` | `90` | Days before DORMANT → ARCHIVED |
| `DECAY_SOFT_DELETE_RETENTION_DAYS` | `90` | Retention window for soft-deleted memories |
| `DECAY_WEIGHT_SEMANTIC` | `0.60` | Weight for semantic similarity |
| `DECAY_WEIGHT_RECENCY` | `0.25` | Weight for recency score |
| `DECAY_WEIGHT_IMPORTANCE` | `0.15` | Weight for importance score |
| `DECAY_MAINTENANCE_BATCH_SIZE` | `500` | Batch size for maintenance processing |

### Importance & Stability Scoring

**Importance Levels (1-5):**
- **1** = Trivial (can forget immediately)
- **2** = Low (useful but replaceable)
- **3** = Moderate (general knowledge)
- **4** = High (important to work/identity)
- **5** = Core (fundamental, never forget)

**Stability Levels (1-5):**
- **1** = Volatile (changes in hours/days)
- **2** = Low (changes in days/weeks)
- **3** = Moderate (changes in weeks/months)
- **4** = High (changes in months/years)
- **5** = Permanent (never changes)

**Permanent Classification:**
Memories with `importance >= 4` AND `stability >= 4` are classified as PERMANENT and exempt from decay.

### Lifecycle States

| State | Description | Transition Trigger |
|-------|-------------|-------------------|
| **ACTIVE** | Recently accessed, full relevance | Initial state, or on access to DORMANT/ARCHIVED |
| **DORMANT** | Not accessed 30+ days | 30+ days inactive, decay ≥ 0.3 |
| **ARCHIVED** | Not accessed 90+ days | 90+ days inactive, decay ≥ 0.5 |
| **EXPIRED** | Marked for deletion | 180+ days inactive, decay ≥ 0.7, importance < 3 |
| **SOFT_DELETED** | Deleted but recoverable | Maintenance run on EXPIRED |
| **PERMANENT** | Exempt from decay | importance ≥ 4 AND stability ≥ 4 |

### Running Maintenance

**Via CLI (from skill directory):**
```bash
cd ~/.claude/skills/Knowledge

# Run maintenance cycle
bun run tools/knowledge-cli.ts run_maintenance

# Get health report
bun run tools/knowledge-cli.ts health_report
```

**Via MCP Tools:**
```typescript
// Run maintenance
run_decay_maintenance({})

// Get health metrics
get_knowledge_health({})

// Classify a specific memory
classify_memory({
  content: "Memory content to classify"
})

// Recover soft-deleted memory
recover_soft_deleted({
  memory_uuid: "uuid-here"
})
```

### Backfill Migration

For existing knowledge graphs created before decay scoring was implemented, run the backfill migration to initialize decay attributes on all nodes:

```bash
# From repository root
cd /Users/seaton/Documents/src/madeinoz-knowledge-system

# Start containers if not running
bun run server-cli --start

# Run backfill migration (Python)
cd docker/patches
python -c "
from decay_migration import run_backfill_migration
import asyncio

async def backfill():
    driver = None  # Your Neo4j driver
    await run_backfill_migration(driver)

asyncio.run(backfill())
"
```

**Backfill performs:**
1. Creates lifecycle_state index if not exists
2. Sets default attributes on nodes without decay data:
   - `importance = 3`, `stability = 3`
   - `lifecycle_state = 'ACTIVE'`
   - `decay_score = 0.0`
   - `last_accessed_at = created_at`
   - `access_count = 0`

### Observability Metrics

**Prometheus Metrics (exposed on port 9090):**

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `knowledge_decay_maintenance_runs_total` | Counter | `status` | Total maintenance runs |
| `knowledge_lifecycle_transitions_total` | Counter | `from_state`, `to_state` | State transition counts |
| `knowledge_memories_by_state` | Gauge | `state` | Current count per lifecycle state |
| `knowledge_decay_score_avg` | Gauge | - | Average decay score |
| `knowledge_maintenance_duration_seconds` | Histogram | - | Maintenance run duration |

**Health Check Endpoints:**
- `/health/decay` - Decay system status
- `/metrics` - Prometheus metrics endpoint

### Testing Decay Features

**Run integration tests:**
```bash
# Python integration tests (requires running Neo4j)
cd docker/patches
pytest tests/integration/test_decay_integration.py -v

# Unit tests
pytest tests/unit/test_memory_decay.py -v
pytest tests/unit/test_lifecycle_manager.py -v
pytest tests/unit/test_importance_classifier.py -v
pytest tests/unit/test_maintenance_service.py -v
```

**Test decay calculation:**
```python
from memory_decay import DecayCalculator

calc = DecayCalculator(base_half_life=30.0)

# Calculate decay for moderate memory after 30 days
decay = calc.calculate_decay(
    days_since_access=30,
    importance=3,
    stability=3
)
# Returns: 0.341 (approximately)

# Permanent memories never decay
decay_permanent = calc.calculate_decay(
    days_since_access=1000,
    importance=5,
    stability=5
)
# Returns: 0.0
```

**Weighted search scoring:**
```python
from memory_decay import calculate_weighted_score

# Combine semantic (0.75), recency (moderate), importance (high)
weighted = calculate_weighted_score(
    semantic_score=0.75,
    days_since_access=15,
    importance=4
)
# Returns: ~0.71 (60% semantic + 25% recency + 15% importance)
```

### Quickstart Checklist

After implementing or updating decay features:

- [ ] Decay configuration file exists at `config/decay-config.yaml`
- [ ] Neo4j index for `lifecycle_state` created
- [ ] Backfill migration run on existing nodes
- [ ] Unit tests pass: `pytest docker/tests/unit/`
- [ ] Integration tests pass: `pytest docker/tests/integration/`
- [ ] Health report returns accurate metrics
- [ ] Maintenance completes within 10 minutes
- [ ] Permanent memories never transition from ACTIVE
- [ ] Soft-deleted memories purged after 90 days

<!-- MANUAL ADDITIONS END -->
