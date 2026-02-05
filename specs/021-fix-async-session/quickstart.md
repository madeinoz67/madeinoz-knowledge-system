# Quickstart: AsyncSession Fix Testing Guide

**Feature**: 021-fix-async-session
**Date**: 2026-02-05

## Overview

This guide provides step-by-step instructions for testing the AsyncSession compatibility fix after implementation.

## Prerequisites

- Dev containers running with latest code (includes Feature 020)
- Knowledge graph populated with test data
- CLI access: `bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts`

## Quick Test (5 minutes)

### 1. Verify Fix is Applied

```bash
# Check server is running
bun run server-cli status

# Should show: MCP Server: http://localhost:8001/mcp/ (dev mode)
```

### 2. Test Basic Investigation

```bash
# Investigate Apollo 11 with depth 2
cd ~/.claude/skills/Knowledge
bun run tools/knowledge-cli.ts --profile development investigate "Apollo 11" --depth 2
```

**Expected Result**:
- Returns connected entities (Neil Armstrong, Buzz Aldrin, Michael Collins)
- Shows relationship types (FOLLOWED, FIRST_TO_STEP_ON, REMAINED_IN_ORBIT)
- No AsyncSession errors

**❌ If Error**: Check MCP server logs:
```bash
bun run server-cli logs --mcp
```

### 3. Test Relationship Filtering

```bash
# Filter by specific relationship types
bun run tools/knowledge-cli.ts --profile development investigate "Apollo 11" --relationship-type "FOLLOWED" --depth 2
```

**Expected Result**:
- Returns only FOLLOWED relationships
- Buzz Aldrin should appear (followed Neil Armstrong)
- Others filtered out

### 4. Test Entity Not Found

```bash
# Search for non-existent entity
bun run tools/knowledge-cli.ts --profile development investigate "NonExistentEntity123"
```

**Expected Result**:
- Error message: "Entity not found: NonExistentEntity123"
- Suggestion to use search_nodes first

## Acceptance Tests

### Test 1: Depth Validation

```bash
# Try invalid depth (should fail)
bun run tools/knowledge-cli.ts --profile development investigate "Apollo 11" --depth 5
```

**Expected**: Error about depth must be between 1 and 3

### Test 2: Cycle Detection

```bash
# Investigate entity with cyclical relationships
bun run tools/knowledge-cli.ts --profile development investigate "Graphiti" --depth 3
```

**Expected**:
- Cycles detected and reported in metadata
- No infinite loops
- Cycles pruned from results

### Test 3: Performance

```bash
# Time the investigation
time bun run tools/knowledge-cli.ts --profile development investigate "Apollo 11" --depth 2
```

**Expected**: Completes in <5 seconds on graphs with 1000 entities

## Troubleshooting

### Error: "Unknown tool: investigate_entity"

**Cause**: MCP server doesn't have investigate_entity tool
**Fix**: Rebuild containers with latest code
```bash
bun run server-cli stop
docker build -f docker/Dockerfile -t madeinoz-knowledge-system:local .
bun run server-cli start --dev
```

### Error: "AsyncSession does not support context manager protocol"

**Cause**: Code still uses sync `with session:` instead of `async with session:`
**Fix**: Verify async changes applied to `docker/patches/utils/graph_traversal.py`

### Error: "Entity not found" for valid entity

**Cause**: Entity name doesn't match exactly (semantic search)
**Fix**: Use search_nodes first to find exact name:
```bash
bun run tools/knowledge-cli.ts --profile development search_nodes "Apollo" 10
```

## Integration Test Location

Full integration test suite: `docker/tests/integration/test_investigate.py`

Run with:
```bash
cd docker
pytest tests/integration/test_investigate.py -v
```

## Success Criteria

✅ All quick tests pass without AsyncSession errors
✅ investigate command returns connected entities
✅ Relationship filtering works correctly
✅ Entity not found returns clear error
✅ Performance <5 seconds for depth=2 queries
