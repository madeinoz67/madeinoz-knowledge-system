# Quickstart: MCP Wrapper for Token Savings

**Feature Branch**: `001-mcp-wrapper`
**Date**: 2026-01-18

## Prerequisites

- Bun runtime installed
- Madeinoz Knowledge System repository cloned
- MCP server running (`bun run server-cli start`)

## Quick Test

```bash
# Verify wrapper is working
bun run src/skills/tools/knowledge-cli.ts health

# Expected output:
# MCP Server: HEALTHY (http://localhost:8000)
```

## Basic Usage

### Search Knowledge (Token-Efficient)

```bash
# Compact output (default)
bun run src/skills/tools/knowledge-cli.ts search_nodes "Graphiti"

# Output:
# Found 3 entities for "Graphiti":
# 1. Graphiti [Framework] - Knowledge graph framework with temporal context
# 2. FalkorDB [Database] - Graph database backend for Graphiti
# 3. MCP Server [Service] - Model Context Protocol server

# Raw JSON output (for debugging)
bun run src/skills/tools/knowledge-cli.ts search_nodes "Graphiti" --raw
```

### Add Knowledge

```bash
bun run src/skills/tools/knowledge-cli.ts add_episode "Docker Tips" "Use --rm flag for temporary containers"

# Output:
# ✓ Episode added: "Docker Tips" (id: ...a1b2c3d4)
#   Extracted: 2 entities, 1 fact
```

### View Recent Episodes

```bash
bun run src/skills/tools/knowledge-cli.ts get_episodes 5

# Output:
# Recent episodes (5):
# - [2h ago] Docker Tips - Use --rm flag for temporary containers
# - [1d ago] Graphiti Setup - Configuration for knowledge graph
# ...
```

### Check Token Savings

```bash
# Enable metrics display
bun run src/skills/tools/knowledge-cli.ts search_nodes "knowledge" --metrics

# Output includes metrics:
# --- Token Metrics ---
# Operation: search_nodes
# Raw size: 1,247 bytes (312 est. tokens)
# Compact size: 298 bytes (75 est. tokens)
# Savings: 76.1% (237 tokens saved)
# Processing time: 8ms
```

## Running Benchmarks

```bash
# Run benchmark suite (requires running MCP server)
bun test tests/integration/wrapper-benchmark.test.ts

# Expected output:
# ✓ search_nodes achieves >30% savings
# ✓ search_facts achieves >30% savings
# ✓ add_memory achieves >25% savings
# ✓ get_episodes achieves >25% savings
```

## Development Setup

```bash
# Build TypeScript
bun run build

# Run type checking
bun run typecheck

# Run all tests
bun test
```

## Common Issues

### Wrapper returns raw JSON unexpectedly

The wrapper falls back to raw JSON when:
- Response structure doesn't match expected schema
- Transformation timeout (>100ms)

Check logs at `~/.madeinoz-knowledge/wrapper.log` for details.

### No savings shown for certain operations

Some operations (like `health`) have minimal response data. Token savings are most significant for:
- `search_nodes` (typical: 50-70% savings)
- `search_facts` (typical: 60-75% savings)
- `get_episodes` (typical: 40-55% savings)
