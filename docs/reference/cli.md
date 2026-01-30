---
title: "CLI Reference"
description: "Command-line interface reference for the Madeinoz Knowledge System"
---

<!-- AI-FRIENDLY SUMMARY
System: Madeinoz Knowledge System - CLI Tools
Purpose: Command-line interface for knowledge graph management, server operations, and remote access
Key Components: server-cli (container management), knowledge-cli (knowledge operations with remote access support)

Key Tools/Commands:
- server-cli: start/stop/restart/status/logs for MCP server containers
- knowledge-cli: add_episode, search_nodes, search_facts, get_episodes, get_status, clear_graph, health, status, list_profiles

Configuration Prefix: MADEINOZ_KNOWLEDGE_
Default Ports: 8001 (MCP HTTP), 8000 (MCP Server), 7474 (Neo4j Browser), 7687 (Neo4j Bolt)

Remote Access (Feature 010):
- Connection profiles via YAML config: $PAI_DIR/config/knowledge-profiles.yaml
- CLI flags: --profile, --host, --port, --protocol
- Environment variable overrides: MADEINOZ_KNOWLEDGE_HOST, MADEINOZ_KNOWLEDGE_PORT, etc.
- TLS/SSL support for HTTPS connections
-->

# CLI Reference

## Overview

The Madeinoz Knowledge System provides command-line tools for managing the knowledge graph server and performing knowledge operations.

### Quick Reference

| Command | Purpose | Example |
|---------|---------|---------|
| `bun run server-cli start` | Start MCP server containers | `bun run server-cli start --dev` |
| `bun run knowledge-cli.ts status` | Show connection status | `bun run knowledge-cli.ts status --profile production` |
| `bun run knowledge-cli.ts list_profiles` | List available profiles | `bun run knowledge-cli.ts list_profiles` |
| `bun run knowledge-cli.ts search_nodes` | Search knowledge graph | `bun run knowledge-cli.ts search_nodes "query" --profile remote` |

## Server Management Commands

### Start Server

```bash
# Production mode
bun run server-cli start

# Development mode
bun run server-cli start --dev
```

Launches the Graphiti MCP server with the configured database backend (Neo4j or FalkorDB).

**Options:**

- `--dev` or `-d`: Enable development mode (uses different ports and env files)
- Detects container runtime (Podman or Docker) automatically
- Loads configuration from PAI .env file
- Generates container environment files
- Waits for server initialization before returning

**Development Mode Differences:**

| Feature | Production | Development |
|---------|-----------|-------------|
| Neo4j Browser | http://localhost:7474 | http://localhost:7475 |
| MCP Server | http://localhost:8000/mcp/ | http://localhost:8001/mcp/ |
| Env Files | `/tmp/madeinoz-knowledge-*.env` | `/tmp/madeinoz-knowledge-*-dev.env` |
| Use Case | Production usage | Code development/testing |

**Expected Output:**

```
✓ Server is running and healthy!
```

### Restart Server

```bash
# Production mode
bun run server-cli restart

# Development mode
bun run server-cli restart --dev
```

Restarts the server containers while preserving data. Regenerates environment files before restarting to ensure configuration changes take effect.

**When to use:**
- After configuration changes
- After code updates (development mode)
- To refresh the server environment

### Stop Server

```bash
bun run server-cli stop
```

Stops and removes the running containers.

**Note:** Database data is persisted in Docker/Podman volumes and will be available when you restart.

### Check Status

```bash
bun run server-cli status
```

Displays current container status and server health.

**Output includes:**

- Container runtime type (Podman/Docker)
- Database backend (Neo4j/FalkorDB)
- Container status (running/stopped)
- MCP server health check result
- Port availability and access URLs

### View Logs

```bash
bun run server-cli logs
```

Streams logs from the running MCP server container.

**Options:**

- `--mcp`: Show only MCP server logs (not database)
- `--db`: Show only database logs (not MCP server)
- `--tail N`: Number of lines to show (default: 100)
- `--no-follow`: Don't follow log output (show current logs and exit)

**Usage:**

```bash
# Follow all logs in real-time
bun run server-cli logs

# Show only MCP server logs
bun run server-cli logs --mcp

# Show last 50 lines and exit
bun run server-cli logs --tail 50 --no-follow

# Show only database logs
bun run server-cli logs --db
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

## Remote Access CLI Options

The Knowledge CLI supports remote MCP access via connection profiles and CLI flags. See [Remote Access Documentation](../remote-access.md) for complete details.

### Connection Profiles

Use predefined connection profiles for different environments:

```bash
# List all available profiles
bun run knowledge-cli.ts list_profiles

# Use specific profile
bun run knowledge-cli.ts search_nodes "query" --profile production

# Show current connection status
bun run knowledge-cli.ts status
```

**Profile Configuration Priority:**

1. CLI flags (`--host`, `--port`, `--protocol`)
2. Individual environment variables (`MADEINOZ_KNOWLEDGE_HOST`)
3. Selected profile (`--profile` or `MADEINOZ_KNOWLEDGE_PROFILE`)
4. Default profile in YAML file
5. Code defaults (localhost:8001, http)

### CLI Flags

All commands support these remote access flags:

| Flag | Description | Example |
|------|-------------|---------|
| `--profile <name>` | Use specific connection profile | `--profile production` |
| `--host <hostname>` | Override profile host | `--host knowledge.example.com` |
| `--port <port>` | Override profile port | `--port 443` |
| `--protocol <proto>` | Override protocol (http/https) | `--protocol https` |

### Environment Variable Overrides

Override any profile setting via environment variables:

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `MADEINOZ_KNOWLEDGE_PROFILE` | Profile name to use | `default` | `production` |
| `MADEINOZ_KNOWLEDGE_HOST` | Server hostname or IP | `localhost` | `knowledge.example.com` |
| `MADEINOZ_KNOWLEDGE_PORT` | Server port | `8001` | `443` |
| `MADEINOZ_KNOWLEDGE_PROTOCOL` | Connection protocol | `http` | `https` |
| `MADEINOZ_KNOWLEDGE_TLS_VERIFY` | Verify TLS certificates | `true` | `false` |
| `MADEINOZ_KNOWLEDGE_TLS_CA` | CA certificate path | - | `/etc/ssl/certs/ca.pem` |
| `MADEINOZ_KNOWLEDGE_TIMEOUT` | Connection timeout (ms) | `30000` | `60000` |

**Example usage:**

```bash
# Use environment variables for remote connection
export MADEINOZ_KNOWLEDGE_HOST=192.168.1.100
export MADEINOZ_KNOWLEDGE_PORT=8001
bun run knowledge-cli.ts search_nodes "my query"

# Combine profile with host override
bun run knowledge-cli.ts get_status --profile production --host backup.example.com
```

### Profile Configuration File

Connection profiles are stored in:

```bash
# Priority location
$PAI_DIR/config/knowledge-profiles.yaml

# Fallback location
~/.claude/config/knowledge-profiles.yaml
```

**Example profile configuration:**

```yaml
version: "1.0"
default_profile: default

profiles:
  default:
    host: localhost
    port: 8001
    protocol: http

  production:
    host: knowledge.example.com
    port: 443
    protocol: https
    tls:
      verify: true
      minVersion: TLSv1.3

  development:
    host: 192.168.1.100
    port: 8001
    protocol: http
```

### New Commands (Feature 010)

#### status

Show connection status and active profile:

```bash
bun run knowledge-cli.ts status
```

**Output includes:**

- Active profile name
- Connection status (connected/disconnected/error)
- Connected host and port
- Protocol (http/https)
- Server version (if available)
- Last connection time

```bash
$ bun run knowledge-cli.ts status --profile production

Knowledge CLI Connection Status
================================
Profile: production
Status: connected
Host: knowledge.example.com
Port: 443
Protocol: https
Server Version: 1.7.0
Last Connected: 2026-01-30T12:34:56Z
```

#### list_profiles

List all available connection profiles:

```bash
bun run knowledge-cli.ts list_profiles
```

**Output includes:**

- All profile names from configuration
- Default profile indicator
- Configuration file path

```bash
$ bun run knowledge-cli.ts list_profiles

Available Profiles
==================
Configuration: ~/.claude/config/knowledge-profiles.yaml
Default Profile: default

Profiles:
  - default (localhost:8001, http)
  - production (knowledge.example.com:443, https)
  - development (192.168.1.100:8001, http)
```

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
