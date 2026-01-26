---
title: "CLI Reference"
description: "Command-line interface reference for the Madeinoz Knowledge System"
---

# CLI Reference

## Overview

The Madeinoz Knowledge System provides command-line tools for managing the knowledge graph server and performing knowledge operations.

## Server Management Commands

### Start Server

```bash
bun run server-cli start
```

Launches the Graphiti MCP server with the configured database backend (Neo4j or FalkorDB).

**Options:**

- Detects container runtime (Podman or Docker) automatically
- Loads configuration from PAI .env file
- Waits for server initialization before returning

**Expected Output:**

```
✓ Server is running and healthy!
```

### Start Services

```bash
bun run server-cli start
```

Starts the containerized MCP server and database backend.

### Stop Services

```bash
bun run server-cli stop
```

Stops and removes the running containers.

### Check Status

```bash
bun run server-cli status
```

Displays current container status and server health.

**Output includes:**

- Container status (running/stopped)
- MCP server health
- Database backend status
- Port availability

### View Logs

```bash
bun run server-cli logs
```

Streams logs from the running MCP server container.

**Usage:**

```bash
# Follow logs in real-time
bun run server-cli logs

# View last N lines
bun run server-cli logs --lines 100
```

## Knowledge Operations

### Add Knowledge (Capture)

Via Claude Code skill:

```
Remember that [your knowledge here]
```

This triggers the CaptureEpisode workflow which:

1. Sends content to MCP server
2. Extracts entities and relationships
3. Creates vector embeddings
4. Stores in graph database with timestamp

### Search Knowledge

Via Claude Code skill:

```
What do I know about [topic]?
```

This triggers the SearchKnowledge workflow which:

1. Converts query to vector embedding
2. Searches graph for semantically similar entities
3. Returns entities with summaries and facts

### Find Relationships

Via Claude Code skill:

```
How are [entity A] and [entity B] related?
```

This triggers the SearchFacts workflow which:

1. Traverses edges between entities in graph
2. Returns direct relationships
3. Shows temporal context of relationships

### View Recent Knowledge

Via Claude Code skill:

```
What did I learn recently?
```

This triggers the GetRecent workflow which:

1. Queries graph for recent episodes
2. Returns chronological list
3. Shows timestamps and summaries

### Check System Status

Via Claude Code skill:

```
Show the knowledge graph status
```

This triggers the GetStatus workflow which:

1. Connects to MCP server
2. Returns entity count, episode count, last update
3. Shows database health

### Clear Knowledge

Via Claude Code skill:

```
Clear my knowledge graph
```

This triggers the ClearGraph workflow which:

1. Confirms destructive action
2. Deletes all entities and relationships
3. Rebuilds indices

## Knowledge CLI (Token-Efficient Wrapper)

The `knowledge` CLI provides a token-efficient wrapper around MCP operations with compact output formatting and metrics tracking. Achieves 25-35% token savings through intelligent formatting.

### Syntax

**Run from the project directory:**

```bash
bun run tools/knowledge-cli.ts <command> [args...] [options]
```

**Note:** All CLI commands should be run from the installed skill directory (`~/.claude/skills/Knowledge/`) where tools are available at `tools/knowledge-cli.ts`.

### Commands

#### add_episode

Add knowledge to the graph:

```bash
bun run tools/knowledge-cli.ts add_episode "Episode title" "Episode body content"
```

With optional source description:

```bash
bun run tools/knowledge-cli.ts add_episode "CTI Research" "Analysis of threat actor" "osint-recon"
```

**Arguments:**

- `<title>` (required): Episode title
- `<body>` (required): Episode content
- `[source_description]` (optional): Source identifier (e.g., 'user-input', 'api-import', 'osint-recon')

#### search_nodes

Search for entities in the knowledge graph:

```bash
bun run tools/knowledge-cli.ts search_nodes "container orchestration"
```

Limit results:

```bash
bun run tools/knowledge-cli.ts search_nodes "container orchestration" 10
```

**Arguments:**

- `<query>` (required): Search query
- `[limit]` (optional): Max results (default: 5)

**Output format:**

- Compact format showing entity name, type, and summary
- ~30% token savings vs raw MCP output

#### search_facts

Find relationships between entities:

```bash
bun run tools/knowledge-cli.ts search_facts "Podman"
```

Limit facts returned:

```bash
bun run tools/knowledge-cli.ts search_facts "Podman" 10
```

**Arguments:**

- `<query>` (required): Entity name or search query
- `[limit]` (optional): Max facts (default: 5)

**Output format:**

- Shows relationship text and type
- ~30% token savings vs raw MCP output

#### get_episodes

Retrieve recent episodes from the knowledge graph:

```bash
bun run tools/knowledge-cli.ts get_episodes
```

Limit number of episodes:

```bash
bun run tools/knowledge-cli.ts get_episodes 10
```

**Arguments:**

- `[limit]` (optional): Max episodes to retrieve (default: 5)

**Output format:**

- Shows episode content and timestamp
- ~30% token savings vs raw MCP output

#### get_status

Get knowledge graph status and health:

```bash
bun run tools/knowledge-cli.ts get_status
```

**Output includes:**

- Entity count
- Episode count
- Last update timestamp
- Database health status

#### clear_graph

Delete all knowledge from the graph (destructive operation):

```bash
bun run tools/knowledge-cli.ts clear_graph --force
```

**Safety:**

- Requires `--force` flag to confirm
- Deletes ALL entities, relationships, and episodes
- Cannot be undone

#### health

Check MCP server health:

```bash
bun run tools/knowledge-cli.ts health
```

**Output:**

- Server status
- Connection state
- Response time

### Options

All commands support the following flags:

```bash
--raw              # Output raw JSON instead of compact format
--metrics          # Display token metrics after operation
--metrics-file <p> # Write metrics to JSONL file
--since <date>     # Filter results created after this date
--until <date>     # Filter results created before this date
-h, --help         # Show help message
```

**Temporal Filter Options:**

The `--since` and `--until` flags enable date-based filtering for `search_nodes` and `search_facts` commands.

**Supported date formats:**

| Format | Example | Description |
|--------|---------|-------------|
| `today` | `--since today` | Start of current day (UTC) |
| `yesterday` | `--since yesterday` | Start of previous day (UTC) |
| `Nd` | `--since 7d` | N days ago |
| `Nw` | `--since 2w` | N weeks ago |
| `Nm` | `--since 1m` | N months ago (30 days per month) |
| ISO 8601 | `--since 2026-01-15` | Specific date |
| ISO 8601 | `--since 2026-01-15T14:30:00Z` | Specific datetime |

### Examples

**Add knowledge with metrics:**

```bash
bun run tools/knowledge-cli.ts add_episode \
  "Test Episode" \
  "This is a test episode" \
  --metrics
```

**Search with raw JSON output:**

```bash
bun run tools/knowledge-cli.ts search_nodes "PAI" --raw
```

**Search with metrics logging:**

```bash
bun run tools/knowledge-cli.ts search_nodes "PAI" 10 \
  --metrics-file ~/.madeinoz-knowledge/metrics.jsonl
```

**Get status and track metrics:**

```bash
bun run tools/knowledge-cli.ts get_status --metrics
```

### Temporal Search Examples

**Search for today's knowledge:**

```bash
bun run tools/knowledge-cli.ts search_nodes "PAI" --since today
```

**Search from the last 7 days:**

```bash
bun run tools/knowledge-cli.ts search_facts "decisions" --since 7d
```

**Search within a specific date range:**

```bash
bun run tools/knowledge-cli.ts search_nodes "project" --since 2026-01-01 --until 2026-01-15
```

**Search yesterday's knowledge:**

```bash
bun run tools/knowledge-cli.ts search_nodes "learning" --since yesterday --until today
```

**Search from last month:**

```bash
bun run tools/knowledge-cli.ts search_facts "architecture" --since 1m
```

**Combine temporal filters with other options:**

```bash
bun run tools/knowledge-cli.ts search_nodes "AI" 20 --since 7d --metrics
```

### Environment Variables

The Knowledge CLI respects the following environment variables for customization:

```bash
# Disable compact output (use raw JSON by default)
export MADEINOZ_WRAPPER_COMPACT=false

# Enable metrics collection by default
export MADEINOZ_WRAPPER_METRICS=true

# Default metrics file path
export MADEINOZ_WRAPPER_METRICS_FILE=~/.madeinoz-knowledge/metrics.jsonl

# Error log path for transformation issues
export MADEINOZ_WRAPPER_LOG_FILE=~/.madeinoz-knowledge/errors.log

# Slow processing threshold in milliseconds (default: 50)
export MADEINOZ_WRAPPER_SLOW_THRESHOLD=50

# Processing timeout in milliseconds (default: 100)
export MADEINOZ_WRAPPER_TIMEOUT=100
```

### Metrics Tracking

When `--metrics` flag is enabled or `MADEINOZ_WRAPPER_METRICS=true`, the CLI displays token usage statistics:

```bash
bun run tools/knowledge-cli.ts search_nodes "AI models" --metrics
```

**Metrics output includes:**

- Operation name
- Raw size (bytes and estimated tokens)
- Compact size (bytes and estimated tokens)
- Savings percentage
- Tokens saved
- Processing time (milliseconds)

**Example output:**

```
--- Token Metrics ---
Operation: search_nodes
Raw size: 12,345 bytes (3,086 est. tokens)
Compact size: 8,234 bytes (2,059 est. tokens)
Savings: 33.3% (1,027 tokens saved)
Processing time: 42ms
```

### Metrics File Format

When using `--metrics-file`, metrics are written as JSONL (one JSON object per line):

```jsonl
{"operation":"search_nodes","timestamp":"2025-01-19T12:34:56.789Z","rawBytes":12345,"compactBytes":8234,"savingsPercent":33.3,"estimatedTokensBefore":3086,"estimatedTokensAfter":2059,"processingTimeMs":42}
{"operation":"get_status","timestamp":"2025-01-19T12:35:12.345Z","rawBytes":567,"compactBytes":234,"savingsPercent":58.7,"estimatedTokensBefore":142,"estimatedTokensAfter":59,"processingTimeMs":15}
```

This format is ideal for:

- Time-series analysis
- Performance monitoring
- Cost tracking
- Optimization validation

## Interactive Installation

```bash
cd ~/.claude/skills/Knowledge
bun run tools/install.ts
```

Guides through:

1. System analysis and conflict detection
2. LLM provider selection
3. API key configuration
4. Database backend selection
5. Service startup

**Options:**

- `--yes` / `-y`: Non-interactive mode with defaults
- `--update` / `-u`: Update existing installation

## Utilities

### Health Check

```bash
curl http://localhost:8000/health
```

Returns server health status as JSON:

```json
{
  "status": "healthy",
  "service": "graphiti-mcp",
  "patch": "madeinoz-all-groups-enabled"
}
```

### MCP Endpoint

```bash
curl http://localhost:8000/mcp
```

SSE endpoint for MCP protocol communication.

## Environment Variables

All CLI commands read from PAI configuration:

```bash
# Set PAI directory (defaults to ~/.claude)
export PAI_DIR=/path/to/pai

# Set database type
export MADEINOZ_KNOWLEDGE_DATABASE_TYPE=neo4j

# Set logging level
export LOG_LEVEL=debug
```

## Troubleshooting

### "Port already in use"

```bash
# Find process using port 8000
lsof -i :8000

# Kill process if needed
kill -9 [PID]

# Or use different port by modifying the Docker Compose files
```

### "Container not found"

```bash
# List all containers
podman ps -a
# or: docker ps -a

# Start services
bun run server-cli start
```

### "Health check failed"

```bash
# Check logs
bun run server-cli logs

# Verify server is responding
curl --max-time 5 http://localhost:8000/health
```

### "Connection refused"

```bash
# Verify MCP server endpoint
curl http://localhost:8000/health

# If unavailable, start server
bun run server-cli start
```

## Configuration Files

### PAI Environment File

Location: `~/.claude/.env` (or `$PAI_DIR/.env`)

Contains all Madeinoz Knowledge System configuration:

- API keys
- LLM provider settings
- Database backend configuration
- Performance tuning options

### Docker Compose Files

- `docker/docker-compose-falkordb.yml` - FalkorDB backend (Docker)
- `docker/docker-compose-neo4j.yml` - Neo4j backend (Docker)
- `docker/podman-compose-falkordb.yml` - FalkorDB backend (Podman)
- `docker/podman-compose-neo4j.yml` - Neo4j backend (Podman)

### Configuration Template

Reference file: `config/.env.example`

Complete example of all available configuration options.

## Related Commands

```bash
# View all available skills (from installed location)
ls -la ~/.claude/skills/Knowledge/workflows/

# Test LLM connectivity
bun run tools/install.ts

# Export knowledge data
# (Via MCP: get_episodes with limit=999999)

# Monitor memory sync
bun run ~/.claude/hooks/sync-memory-to-knowledge.ts --verbose
```
