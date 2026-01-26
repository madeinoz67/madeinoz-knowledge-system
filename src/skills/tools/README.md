# Madeinoz Knowledge System - Skill Tools

Container management tools for the installed Madeinoz Knowledge System skill.

These tools are installed with the skill to `~/.claude/skills/Knowledge/tools/`.

## Workflows

### Install.md

Installation workflow invoked by the skill system.

**Triggers:** "install knowledge", "setup knowledge system", "configure knowledge graph"

**What it does:**
- Guides through MCP server setup
- Installs skill to Claude skills directory
- Configures MCP in `~/.claude.json`
- Verifies installation

## Container Management

These tools manage the Podman/Docker containers for the knowledge system.

### start.ts

Start the MCP server and FalkorDB containers.

```bash
bun run tools/start.ts
```

### stop.ts

Stop all knowledge system containers.

```bash
bun run tools/stop.ts
```

### status.ts

Show status of containers and test health endpoints.

```bash
bun run tools/status.ts
```

### logs.ts

View container logs with optional follow mode.

```bash
bun run tools/logs.ts           # Show recent logs
bun run tools/logs.ts --follow  # Follow logs in real-time
bun run tools/logs.ts --mcp     # Show MCP server logs only
bun run tools/logs.ts --db      # Show FalkorDB logs only
```

## Shared Library

The `lib/` directory contains shared utilities used by skill tools:

- `cli.ts` - Console output formatting and colors
- `container.ts` - Podman/Docker container management

## Pack-Level Tools

The following tools are in `src/skills/` (not installed with skill):

- `server/install.ts` - Full installation wizard
- `server/diagnose.ts` - Diagnostic and troubleshooting tool
- `server/server-cli.ts` - Unified server CLI (start, stop, restart, status, logs)
- `tools/knowledge-cli.ts` - Knowledge CLI wrapper (token-efficient MCP operations)

Run these from the pack directory:

```bash
bun run src/skills/server/install.ts   # Interactive installation
bun run src/skills/server/diagnose.ts  # Run diagnostics
bun run server-cli start               # Start the server
bun run server-cli stop                # Stop the server
bun run server-cli status              # Check status
bun run server-cli logs                # View logs
bun run src/skills/tools/knowledge-cli.ts search_nodes "query"  # Knowledge CLI
```

## Tool Development

When adding new skill tools:

1. **Use TypeScript** - Write tools as `.ts` files run with `bun`
2. **Import from lib** - Use shared utilities: `import { cli } from "../lib/cli.js"`
3. **Minimal dependencies** - Only use cli.ts and container.ts
4. **Self-documenting** - Include `--help` flag support
5. **Exit codes** - Return 0 for success, non-zero for errors

Example structure:

```typescript
#!/usr/bin/env bun

import { cli } from "../lib/cli.js";
import { createContainerManager } from "../lib/container.js";

const args = process.argv.slice(2);

if (args.includes('--help')) {
  cli.info('Usage: bun run tools/mytool.ts [options]');
  process.exit(0);
}

// Tool logic here
```

## Related

- `SKILL.md` - Skill definition with workflow routing
- `STANDARDS.md` - Usage standards for knowledge capture
- `../../server/` - Pack-level infrastructure files
