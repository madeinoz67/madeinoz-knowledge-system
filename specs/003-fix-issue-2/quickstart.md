# Quickstart: Fix Sync Hook Protocol Mismatch

**Feature**: 003-fix-issue-2
**Date**: 2026-01-20

## Overview

This quickstart guide helps you test the sync hook fix locally before deploying to production.

## Prerequisites

1. **Bun runtime** installed: `brew install bun`
2. **Podman or Docker** installed and running
3. **Neo4j or FalkorDB** containers started: `bun run server-cli start`
4. **PAI Memory System** with test files in `~/.claude/MEMORY/`

## Environment Setup

### 1. Start MCP Server

```bash
cd /path/to/madeinoz-knowledge-system
bun run server-cli start
```

Verify server is running:
```bash
bun run server-cli status
```

Expected output:
```
Container STATUS: running
Health check: OK
```

### 2. Configure Database Type

Set the database type (default is neo4j):

```bash
# For Neo4j (default)
export MADEINOZ_KNOWLEDGE_DB=neo4j

# For FalkorDB
export MADEINOZ_KNOWLEDGE_DB=falkorodb
```

### 3. Configure MCP URL (if non-default)

```bash
export MADEINOZ_KNOWLEDGE_MCP_URL=http://localhost:8000
```

## Manual Testing

### Test 1: Health Check

Verify the MCP client can connect to the server:

```bash
bun run src/hooks/sync-memory-to-knowledge.ts --verbose
```

Expected output:
```
[Sync] Running in CLI mode
[Sync] Options: {"dryRun":false,"syncAll":false,"maxFiles":50,"verbose":true}
[Sync] Memory directory: /Users/you/.claude/MEMORY
[Sync] MCP server available after 1 attempts
[Sync] Found X files to sync
```

### Test 2: Dry Run Sync

Preview sync without making changes:

```bash
bun run src/hooks/sync-memory-to-knowledge.ts --dry-run --verbose
```

Expected output:
```
[DryRun] Would sync: LEARNING: Test Episode Title
[DryRun] Would sync: RESEARCH: Another Test Episode
```

### Test 3: Actual Sync

Sync memory files to knowledge graph:

```bash
bun run src/hooks/sync-memory-to-knowledge.ts --verbose
```

Expected output:
```
[Sync] Running in CLI mode
[Sync] MCP server available after 1 attempts
[Sync] Found 5 files to sync
[Sync] Processing: LEARNING: Test Episode Title
[Sync] ✓ Synced: LEARNING: Test Episode Title
[Sync] Processing: RESEARCH: Another Test Episode
[Sync] ✓ Synced: RESEARCH: Another Test Episode
[Sync] Complete: 5 synced, 0 failed, 0 skipped
```

### Test 4: Verify Knowledge Graph

Query the knowledge graph to verify episodes were added:

```bash
# Using the Knowledge CLI (if available)
knowledge search "test episode"

# Or directly via MCP
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "search_nodes",
      "arguments": {"query": "test episode", "max_nodes": 5}
    }
  }'
```

### Test 5: Incremental Sync

Run sync again to verify deduplication works:

```bash
bun run src/hooks/sync-memory-to-knowledge.ts --verbose
```

Expected output:
```
[Sync] Found 0 files to sync
[Sync] No new files to sync
```

### Test 6: Database Type Switching

Test that query sanitization switches correctly:

```bash
# Test with Neo4j
export MADEINOZ_KNOWLEDGE_DB=neo4j
bun run src/hooks/sync-memory-to-knowledge.ts --all --verbose

# Test with FalkorDB
export MADEINOZ_KNOWLEDGE_DB=falkorodb
bun run src/hooks/sync-memory-to-knowledge.ts --all --verbose
```

Both should complete without query syntax errors.

### Test 7: Special Character Handling

Create a test file with hyphenated identifier (CTI use case):

```bash
cat > ~/.claude/MEMORY/LEARNING/ALGORITHM/test-apt-28.md << 'EOF'
---
capture_type: LEARNING
---

# APT-28 Threat Actor

APT-28 is a sophisticated threat actor known for cyber espionage.
EOF

bun run src/hooks/sync-memory-to-knowledge.ts --verbose
```

Expected: Sync succeeds without Lucene syntax errors.

### Test 8: Graceful Degradation

Test that sync fails gracefully when MCP server is offline:

```bash
# Stop the server
bun run server-cli stop

# Run sync (should not crash)
bun run src/hooks/sync-memory-to-knowledge.ts --verbose
```

Expected output:
```
[Sync] MCP server offline, retrying in 1000ms (attempt 1/3)
[Sync] MCP server offline after retries - skipping sync
```

Restart server:
```bash
bun run server-cli start
```

## Verification Checklist

- [ ] Health check passes when server is running
- [ ] Health check fails gracefully when server is stopped
- [ ] Dry run lists files without making API calls
- [ ] Actual sync adds episodes to knowledge graph
- [ ] Incremental sync skips already-synced files
- [ ] Special characters (hyphens, slashes) work in queries
- [ ] Database type switching works (neo4j vs falkorodb)
- [ ] Sync completes within 15 seconds for 20 files
- [ ] Sync hook does not block when server is unavailable

## Troubleshooting

### "Failed to establish MCP session"

**Cause**: MCP server not running or wrong URL

**Fix**:
```bash
bun run server-cli status
# If stopped:
bun run server-cli start
# Check URL:
echo $MADEINOZ_KNOWLEDGE_MCP_URL
```

### "Lucene syntax error"

**Cause**: Database type is falkorodb but special characters not escaped

**Fix**: Verify `MADEINOZ_KNOWLEDGE_DB` is set correctly:
```bash
echo $MADEINOZ_KNOWLEDGE_DB
# Should be 'neo4j' or 'falkorodb'
```

### "Sync completes but 0 files synced"

**Cause**: All files already synced or no files found

**Fix**: Run with `--all` flag to force re-sync:
```bash
bun run src/hooks/sync-memory-to-knowledge.ts --all --verbose
```

### "Request timeout after Xms"

**Cause**: MCP server unresponsive or network latency

**Fix**: Increase timeout:
```bash
export MADEINOZ_KNOWLEDGE_TIMEOUT=30000
```

## Next Steps

After manual testing passes:
1. Run unit tests: `bun test tests/unit`
2. Run integration tests: `bun test tests/integration`
3. Create pull request with implementation
4. Update documentation if needed
