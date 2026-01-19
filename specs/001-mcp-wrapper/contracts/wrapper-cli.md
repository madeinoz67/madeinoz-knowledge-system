# Wrapper CLI Contract

**Feature Branch**: `001-mcp-wrapper`
**Date**: 2026-01-18
**Status**: Complete

## Overview

The MCP wrapper CLI provides a token-efficient interface to the Graphiti MCP server. All commands output compact, human-readable text by default.

---

## CLI Interface

### Base Command

```bash
bun run src/server/mcp-wrapper.ts <command> [args...] [options]
```

### Global Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--raw` | flag | false | Output raw JSON instead of compact format |
| `--metrics` | flag | false | Collect and display token metrics |
| `--metrics-file <path>` | string | - | Write metrics to JSONL file |
| `--timeout <ms>` | number | 100 | Transformation timeout in milliseconds |
| `-h, --help` | flag | - | Show help message |

---

## Commands

### search_nodes

Search for entities in the knowledge graph.

**Syntax**:
```bash
mcp-wrapper.ts search_nodes <query> [limit] [--entity <type>]
```

**Arguments**:
- `query` (required): Natural language search query
- `limit` (optional): Maximum results (default: 10)

**Options**:
- `--entity <type>`: Filter by entity type (Preference, Procedure, Learning, Research, Decision, etc.)

**Example**:
```bash
$ bun run src/server/mcp-wrapper.ts search_nodes "Graphiti" 5

Found 3 entities for "Graphiti":
1. Graphiti [Framework] - Knowledge graph framework with temporal context support
2. FalkorDB [Database] - Graph database backend used by Graphiti MCP server
3. MCP Server [Service] - Model Context Protocol server for knowledge operations
```

**Example (with --raw)**:
```bash
$ bun run src/server/mcp-wrapper.ts search_nodes "Graphiti" 5 --raw

{
  "nodes": [
    {
      "uuid": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Graphiti",
      "entity_type": "Framework",
      ...
    }
  ]
}
```

---

### search_facts

Search for relationships between entities.

**Syntax**:
```bash
mcp-wrapper.ts search_facts <query> [limit]
```

**Arguments**:
- `query` (required): Natural language search query
- `limit` (optional): Maximum results (default: 10)

**Example**:
```bash
$ bun run src/server/mcp-wrapper.ts search_facts "Graphiti database" 5

Found 2 relationships for "Graphiti database":
1. Graphiti --uses--> FalkorDB (confidence: 0.95)
2. FalkorDB --stores--> Knowledge Graph (confidence: 0.88)
```

---

### get_episodes

Retrieve recent episodes from the knowledge graph.

**Syntax**:
```bash
mcp-wrapper.ts get_episodes [limit]
```

**Arguments**:
- `limit` (optional): Maximum episodes (default: 5)

**Example**:
```bash
$ bun run src/server/mcp-wrapper.ts get_episodes 3

Recent episodes (3):
- [2h ago] Podman Volume Syntax - volume mounting best practices learned during containerization
- [1d ago] Architecture Decision - selected Graphiti for temporal knowledge graph
- [3d ago] VS Code Preferences - tab size 2, auto-save on focus change
```

---

### add_episode

Add knowledge to the graph.

**Syntax**:
```bash
mcp-wrapper.ts add_episode <title> <body> [source_description]
```

**Arguments**:
- `title` (required): Episode title
- `body` (required): Episode content
- `source_description` (optional): Where this knowledge came from

**Example**:
```bash
$ bun run src/server/mcp-wrapper.ts add_episode "Docker Networking" "Use bridge networks for container-to-container communication" "Technical learning"

✓ Episode added: "Docker Networking" (id: ...a1b2c3d4)
  Extracted: 2 entities, 1 fact
```

---

### get_status

Check knowledge graph status.

**Syntax**:
```bash
mcp-wrapper.ts get_status
```

**Example**:
```bash
$ bun run src/server/mcp-wrapper.ts get_status

Knowledge Graph Status: HEALTHY
Entities: 142 | Episodes: 47 | Last update: 5m ago
```

---

### clear_graph

Delete all knowledge (requires confirmation).

**Syntax**:
```bash
mcp-wrapper.ts clear_graph --force
```

**Arguments**:
- `--force` (required): Confirm destructive operation

**Example**:
```bash
$ bun run src/server/mcp-wrapper.ts clear_graph --force

✓ Knowledge graph cleared
  Removed: 142 entities, 47 episodes
```

---

### health

Check server health.

**Syntax**:
```bash
mcp-wrapper.ts health
```

**Example**:
```bash
$ bun run src/server/mcp-wrapper.ts health

MCP Server: HEALTHY (http://localhost:8000)
```

---

## Metrics Output

When `--metrics` is enabled:

```bash
$ bun run src/server/mcp-wrapper.ts search_nodes "Graphiti" --metrics

Found 3 entities for "Graphiti":
1. Graphiti [Framework] - Knowledge graph framework with temporal context support
2. FalkorDB [Database] - Graph database backend used by Graphiti MCP server
3. MCP Server [Service] - Model Context Protocol server for knowledge operations

--- Token Metrics ---
Operation: search_nodes
Raw size: 1,247 bytes (312 est. tokens)
Compact size: 298 bytes (75 est. tokens)
Savings: 76.1% (237 tokens saved)
Processing time: 8ms
```

When `--metrics-file` is specified, metrics are appended as JSONL:

```json
{"operation":"search_nodes","timestamp":"2026-01-18T12:00:00Z","rawBytes":1247,"compactBytes":298,"savingsPercent":76.1,"estimatedTokensBefore":312,"estimatedTokensAfter":75,"processingTimeMs":8}
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Command error (invalid args, operation failed) |
| 2 | Server connection error |
| 3 | Transformation timeout (exceeded --timeout) |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MADEINOZ_WRAPPER_COMPACT` | `true` | Enable compact output by default |
| `MADEINOZ_WRAPPER_METRICS_FILE` | - | Default metrics file path |
| `MADEINOZ_WRAPPER_LOG_FILE` | `~/.madeinoz-knowledge/wrapper.log` | Transformation log path |
