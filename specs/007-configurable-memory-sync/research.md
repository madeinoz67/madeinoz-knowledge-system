# Research: Configurable Memory Sync

**Feature**: 007-configurable-memory-sync
**Date**: 2026-01-28
**Status**: Complete

## Overview

This document captures research findings and decisions made during the specification and clarification phases for the Configurable Memory Sync feature.

## Problem Analysis

### Root Cause of Memory Loop

**Discovery Method**: Codanna semantic search and codebase exploration

**Findings**:
1. **Two independent sync hooks** operate without coordination:
   - `sync-learning-realtime.ts` - runs at SessionEnd (Stop hook)
   - `sync-memory-to-knowledge.ts` - runs at SessionStart

2. **Anti-loop detection gap**: Only `sync-learning-realtime.ts` has `containsKnowledgeOperations()` check (lines 57-60). The main sync hook at `sync-memory-to-knowledge.ts` has **no anti-loop detection**.

3. **Loop flow**:
   ```
   Knowledge query → Learning captured → sync-learning-realtime MAY catch it
                                              ↓
                         sync-memory-to-knowledge syncs it (no check!)
                                              ↓
                         Knowledge graph stores search results
                                              ↓
                         Next search retrieves own previous results → LOOP
   ```

**Source Files**:
- `src/hooks/sync-learning-realtime.ts:38-47` - KNOWLEDGE_TOOL_PATTERNS array
- `src/hooks/sync-learning-realtime.ts:57-60` - containsKnowledgeOperations function
- `src/hooks/sync-learning-realtime.ts:142-148` - Loop prevention check
- `src/hooks/sync-memory-to-knowledge.ts:247-304` - syncFile() has NO loop prevention

## Decisions

### Decision 1: Database Backend

**Decision**: Neo4j only for production deployment

**Rationale**:
- Neo4j is the established default in the codebase
- No Lucene escaping required (simpler than FalkorDB)
- Better documentation and ecosystem support
- Production compose should be simple and reliable

**Alternatives Considered**:
- FalkorDB (lighter resources, but requires Lucene escaping)
- Both backends (complexity, maintenance burden)

### Decision 2: Configuration Storage

**Decision**: Native container environment variables (no MADEINOZ_ prefixes in production)

**Rationale**:
- Production compose targets servers without PAI infrastructure
- Native Neo4j variable names are more intuitive for external users
- Maintains consistency with standard Docker deployment patterns
- Local sync uses existing MADEINOZ_KNOWLEDGE_* pattern for PAI integration

**Implementation**:
- Local hooks: `MADEINOZ_KNOWLEDGE_SYNC_LEARNING_ALGORITHM=true`
- Production compose: `NEO4J_AUTH=neo4j/password` (native naming)

### Decision 3: Security Defaults

**Decision**: Minimal security (Neo4j default authentication)

**Rationale**:
- Remote deployment is user responsibility
- TLS adds complexity that not all users need
- Users who need security can add it themselves
- Matches the "out of scope" boundary for remote operations

**What's Included**:
- Neo4j default authentication (username/password)
- restart: unless-stopped policy
- Volume persistence

**What's Excluded (User Responsibility)**:
- TLS/SSL configuration
- Firewall rules
- Advanced security hardening

### Decision 4: Deduplication Strategy

**Decision**: Dual deduplication (file path AND content hash)

**Rationale**:
- File path catches re-processing of same file
- Content hash catches duplicate content from different files
- Existing `sync-state.ts` already supports both mechanisms
- Defense in depth for data integrity

**Implementation**:
```typescript
// Skip if already synced by path
if (syncedPaths.has(filepath)) continue;

// Skip if content already synced (even from different file)
if (syncedHashes.has(contentHash)) continue;
```

### Decision 5: Sync Timing

**Decision**: SessionStart only

**Rationale**:
- Simplifies architecture (single sync point)
- Eliminates realtime hook entirely
- Content from current session available in next session
- Matches existing main hook behavior

**Implications**:
- No immediate availability of learnings in current session
- Reduces complexity by removing Stop hook sync
- Consistent timing expectations for users

## Technical Research

### Existing Anti-Loop Patterns

From `sync-learning-realtime.ts:38-47`:

```typescript
const KNOWLEDGE_TOOL_PATTERNS = [
  'mcp__madeinoz-knowledge__',
  'search_memory',
  'add_memory',
  'get_episodes',
  'knowledge graph',
  'what do i know',
  'what do you know',
];
```

**Enhancement Needed**: These patterns need expansion to catch:
- Formatted knowledge query output (markdown tables, headers)
- Episode name patterns ("LEARNING: Search Results for...")
- Any MCP tool names containing "knowledge"

### Configuration Environment Variables

New sync configuration variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MADEINOZ_KNOWLEDGE_SYNC_LEARNING_ALGORITHM` | `true` | Sync LEARNING/ALGORITHM directory |
| `MADEINOZ_KNOWLEDGE_SYNC_LEARNING_SYSTEM` | `true` | Sync LEARNING/SYSTEM directory |
| `MADEINOZ_KNOWLEDGE_SYNC_RESEARCH` | `true` | Sync RESEARCH directory |

### Production Compose Structure

Based on existing `docker/docker-compose-neo4j.yml`:

```yaml
# Production differences from local:
name: knowledge-graph  # Native naming (not madeinoz-knowledge-system)
services:
  neo4j:
    container_name: neo4j  # Native naming
    environment:
      - NEO4J_AUTH=${NEO4J_USER:-neo4j}/${NEO4J_PASSWORD:-changeme}
      # No MADEINOZ_ prefixes
  graphiti-mcp:
    container_name: knowledge-mcp  # Native naming
    environment:
      # Native variable names only
      - MODEL_NAME=${MODEL_NAME:-gpt-4o-mini}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
```

## References

- Existing sync code: `src/hooks/sync-memory-to-knowledge.ts`
- Realtime hook (to deprecate): `src/hooks/sync-learning-realtime.ts`
- Sync state management: `src/hooks/lib/sync-state.ts`
- Existing compose: `docker/docker-compose-neo4j.yml`
- Constitution: `.specify/memory/constitution.md`
