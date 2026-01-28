# Data Model: Configurable Memory Sync

**Feature**: 007-configurable-memory-sync
**Date**: 2026-01-28

## Overview

This document defines the data structures for the Configurable Memory Sync feature. These entities support configurable source filtering, anti-loop detection, and sync decision tracking.

## Entities

### SyncConfiguration

Settings controlling which memory sources are synced to the knowledge graph.

```typescript
interface SyncConfiguration {
  /** Enable sync for LEARNING/ALGORITHM directory */
  syncLearningAlgorithm: boolean;

  /** Enable sync for LEARNING/SYSTEM directory */
  syncLearningSystem: boolean;

  /** Enable sync for RESEARCH directory */
  syncResearch: boolean;

  /** Custom patterns to always exclude (in addition to built-in anti-loop) */
  customExcludePatterns?: string[];

  /** Maximum files to process per sync run */
  maxFilesPerSync: number;

  /** Enable verbose logging */
  verbose: boolean;
}
```

**Default Values**:
| Field | Default | Source |
|-------|---------|--------|
| `syncLearningAlgorithm` | `true` | `MADEINOZ_KNOWLEDGE_SYNC_LEARNING_ALGORITHM` |
| `syncLearningSystem` | `true` | `MADEINOZ_KNOWLEDGE_SYNC_LEARNING_SYSTEM` |
| `syncResearch` | `true` | `MADEINOZ_KNOWLEDGE_SYNC_RESEARCH` |
| `customExcludePatterns` | `[]` | `MADEINOZ_KNOWLEDGE_SYNC_EXCLUDE_PATTERNS` |
| `maxFilesPerSync` | `50` | `MADEINOZ_KNOWLEDGE_SYNC_MAX_FILES` |
| `verbose` | `false` | `MADEINOZ_KNOWLEDGE_SYNC_VERBOSE` |

**Validation Rules**:
- Boolean fields accept: `true`, `false`, `1`, `0`, `yes`, `no`
- Invalid values fall back to defaults with warning log
- `maxFilesPerSync` must be 1-1000, defaults to 50 if invalid

---

### SyncSource

A category of memory content eligible for sync.

```typescript
interface SyncSource {
  /** Relative path from MEMORY directory (e.g., 'LEARNING/ALGORITHM') */
  path: string;

  /** Default capture type for content from this source */
  type: 'LEARNING' | 'RESEARCH';

  /** Human-readable description */
  description: string;

  /** Whether this source is enabled for sync */
  enabled: boolean;
}
```

**Predefined Sources**:
| Path | Type | Description | Config Variable |
|------|------|-------------|-----------------|
| `LEARNING/ALGORITHM` | LEARNING | Task execution learnings | `SYNC_LEARNING_ALGORITHM` |
| `LEARNING/SYSTEM` | LEARNING | PAI/tooling learnings | `SYNC_LEARNING_SYSTEM` |
| `RESEARCH` | RESEARCH | Agent research outputs | `SYNC_RESEARCH` |

**Excluded Directories** (never synced, not configurable):
| Path | Reason |
|------|--------|
| `LEARNING/SIGNALS` | JSONL format, not markdown |
| `LEARNING/SYNTHESIS` | Aggregated reports, different sync if needed |
| `WORK` | Work tracking, different structure |
| `SECURITY` | Security events, JSONL format |
| `STATE` | Runtime state, not knowledge |

---

### AntiLoopPattern

A pattern used to detect knowledge-derived content that should not be re-synced.

```typescript
interface AntiLoopPattern {
  /** The pattern string to match */
  pattern: string;

  /** Human-readable description of what this catches */
  description: string;

  /** Match type: 'contains' (substring) or 'regex' (full regex) */
  matchType: 'contains' | 'regex';

  /** Where to apply the check */
  scope: 'body' | 'title' | 'both';
}
```

**Built-in Patterns**:
| Pattern | Type | Scope | Description |
|---------|------|-------|-------------|
| `mcp__madeinoz-knowledge__` | contains | both | MCP tool invocations |
| `search_memory` | contains | both | Memory search operations |
| `add_memory` | contains | both | Memory add operations |
| `get_episodes` | contains | both | Episode retrieval |
| `knowledge graph` | contains | both | Knowledge graph references |
| `what do i know` | contains | both | Common query phrase |
| `what do you know` | contains | both | Common query phrase |
| `search_memory_nodes` | contains | both | Node search operation |
| `search_memory_facts` | contains | both | Facts search operation |
| `LEARNING: Search` | contains | title | Search result learnings |
| `Knowledge Found:` | contains | body | Formatted search output |
| `Key Entities:` | contains | body | Knowledge query output |

**Expansion from Original**: Original `sync-learning-realtime.ts` had 7 patterns. This model adds 5 more to catch formatted output and title patterns.

---

### SyncDecision

A record of whether a file was synced, skipped, or failed.

```typescript
interface SyncDecision {
  /** Absolute path to the memory file */
  filepath: string;

  /** Decision outcome */
  decision: 'synced' | 'skipped' | 'failed';

  /** Reason for the decision */
  reason: string;

  /** Timestamp of the decision */
  timestamp: string;

  /** Content hash (if computed) */
  contentHash?: string;

  /** Episode UUID (if synced successfully) */
  episodeUuid?: string;
}
```

**Reason Categories**:
| Decision | Reason Examples |
|----------|-----------------|
| `synced` | `Successfully added to knowledge graph` |
| `skipped` | `Already synced (path match)` |
| `skipped` | `Already synced (content hash match)` |
| `skipped` | `Contains knowledge operations (anti-loop)` |
| `skipped` | `Source disabled in configuration` |
| `failed` | `MCP server offline after retries` |
| `failed` | `API error: [error message]` |

---

### ProductionDeployment

Configuration for standalone Docker Compose deployment (not a runtime entity, but a configuration schema).

```yaml
# docker-compose-production.yml schema
name: knowledge-graph  # Clean naming, no pack prefix

services:
  neo4j:
    image: neo4j:latest
    container_name: neo4j
    restart: unless-stopped
    ports:
      - "7474:7474"   # Browser
      - "7687:7687"   # Bolt
    volumes:
      - neo4j-data:/data
      - neo4j-logs:/logs
    environment:
      # Native Neo4j variables (no MADEINOZ_ prefix)
      - NEO4J_AUTH=${NEO4J_USER:-neo4j}/${NEO4J_PASSWORD:-changeme}
      - NEO4J_server_memory_heap_initial__size=512m
      - NEO4J_server_memory_heap_max__size=1G
    healthcheck:
      test: ["CMD", "wget", "-O", "/dev/null", "http://localhost:7474"]
      interval: 10s
      timeout: 5s
      retries: 5

  graphiti-mcp:
    image: zepai/knowledge-graph-mcp:standalone
    container_name: knowledge-mcp
    restart: unless-stopped
    ports:
      - "8000:8000"   # MCP HTTP
    environment:
      # Native variable names
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=${NEO4J_PASSWORD:-changeme}
      - MODEL_NAME=${MODEL_NAME:-gpt-4o-mini}
      - LLM_PROVIDER=${LLM_PROVIDER:-openai}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      neo4j:
        condition: service_healthy

volumes:
  neo4j-data:
  neo4j-logs:

networks:
  default:
    driver: bridge
```

**Key Differences from Local Compose**:
| Aspect | Local | Production |
|--------|-------|------------|
| Project name | `madeinoz-knowledge-system` | `knowledge-graph` |
| Container names | `madeinoz-knowledge-*` | `neo4j`, `knowledge-mcp` |
| Env var prefix | `MADEINOZ_KNOWLEDGE_*` | Native names |
| Network name | `madeinoz-knowledge-net` | `default` |
| Patches | Mounted from `docker/patches/` | None (user adds if needed) |

## State Transitions

### Sync Decision Flow

```
File Found
    ↓
[Check if source enabled] → NO → Decision: skipped (source disabled)
    ↓ YES
[Check if path already synced] → YES → Decision: skipped (path match)
    ↓ NO
[Compute content hash]
    ↓
[Check if hash already synced] → YES → Decision: skipped (hash match)
    ↓ NO
[Check anti-loop patterns] → MATCH → Decision: skipped (anti-loop)
    ↓ NO MATCH
[Call knowledge API]
    ↓
[API Success?] → NO → Decision: failed (error message)
    ↓ YES
Decision: synced (UUID recorded)
```

## Relationships

```
SyncConfiguration
    │
    ├── 1:N → SyncSource (enabled/disabled per source)
    │
    └── 1:N → AntiLoopPattern (built-in + custom)

SyncSource
    │
    └── 1:N → SyncDecision (decisions per file from source)

SyncDecision
    │
    └── 1:1 → Episode (in knowledge graph, via episodeUuid)
```
