# madeinoz-knowledge-system Development Guidelines

Personal knowledge management system using Graphiti knowledge graph with Neo4j/FalkorDB.

## Quick Reference

| Resource | Location |
|----------|----------|
| Full docs | `docs/` or https://madeinoz67.github.io/madeinoz-knowledge-system/ |
| Memory Decay | `docs/usage/memory-decay.md` |
| Configuration | `docs/reference/configuration.md` |
| CLI Reference | `docs/reference/cli.md` |
| Observability | `docs/reference/observability.md` |

## Commands

```bash
bun run build              # Build TypeScript
bun run typecheck          # Type check only
bun test                   # Run tests
bun run server-cli start   # Start containers
bun run server-cli stop    # Stop containers
bun run server-cli status  # Check status
```

## Architecture

```
src/
├── server/           # MCP server orchestration, container management
├── skills/           # PAI Skill definition and workflows
├── hooks/            # Session lifecycle hooks (memory sync)
└── config/           # Environment configuration

docker/
├── patches/          # Python MCP server code (graphiti patches)
└── Dockerfile        # Container build

config/
├── decay-config.yaml # Memory decay settings (180-day half-life)
└── sync-sources.json # Memory sync configuration
```

## Technical Details

- **Runtime**: Bun (ES modules, target: bun)
- **TypeScript**: Strict mode, path aliases (`@server/*`, `@lib/*`)
- **Database**: Neo4j (default, port 7474/7687) or FalkorDB (port 3000/6379)
- **Python**: 3.11+ in container for MCP server patches

**LLM Compatibility**:
- Working: gpt-4o-mini, gpt-4o, Claude 3.5 Haiku, Gemini 2.0 Flash
- Failing: All Llama/Mistral variants (Pydantic validation errors)

## Container Development (CRITICAL)

After modifying `docker/patches/*.py`, you MUST rebuild:

```bash
docker build -f docker/Dockerfile -t madeinoz-knowledge-system:local .
bun run server-cli stop
bun run server-cli start --dev
```

**If changes don't appear**: Docker caching issue. Stop containers fully before restart.

## CLI Profile Usage (CRITICAL)

**MUST use `--profile development` when testing against dev containers.**

```bash
# CORRECT - testing against dev containers
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts --profile development health
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts --profile development run_maintenance

# WRONG - omitting profile hits PRODUCTION data
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts health
```

| Profile | Container | Use Case |
|---------|-----------|----------|
| `production` (default) | Production | Live data |
| `development` | `--dev` containers | Testing |

**Rules**: Never reconfigure profiles. Always pass `--profile development` for dev work.
