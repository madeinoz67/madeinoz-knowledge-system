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

## Releases (CRITICAL)

**⚠️ NEVER use `gh release create` directly** - it creates the tag via GitHub API without triggering the CI workflow. The release job will never run, leaving you with a broken release (no Docker image pushed, no docs deployed).

**Release checklist - follow these steps exactly:**

```bash
# === PRE-RELEASE CHECKS ===
# 1. Check you're on main branch
git branch --show-current  # Should output: main

# 2. Pull latest changes
git pull origin main

# 3. Verify working tree is clean (no uncommitted changes)
git status  # Should show: "nothing to commit, working tree clean"

# 4. Verify latest CI passed
gh run list --limit 1  # Check status is "completed success"

# === CREATE RELEASE ===
# 5. Create annotated tag with release description
git tag -a v1.x.x -m "Release v1.x.x" -m "Description of what's in this release"
# Or for multi-line descriptions, omit -m to open your editor:
git tag -a v1.x.x
# Then write your description in the editor (same format as commit messages)

# 6. Push tag to trigger CI workflow
git push origin v1.x.x

# === VERIFY RELEASE ===
# 7. Watch workflow run
gh run watch

# 8. Confirm release created
gh release view v1.x.x
```

**What the CI workflow does automatically:**
- Generates changelog from git-cliff using conventional commits
- Updates CHANGELOG.md on main branch
- Builds and pushes multi-arch Docker image to GHCR
- Creates GitHub Release with formatted release notes
- Deploys documentation to GitHub Pages

**Recovering from a bad release:**

```bash
# If you accidentally used gh release create or created via web UI:
gh release delete v1.x.x --yes
git tag -d v1.x.x
git push origin :refs/tags/v1.x.x
# Then follow the correct process above
```

**Why this matters:** The release job (`.github/workflows/ci.yml:195`) only triggers on `push` events for tags matching `v*`. Tags created via GitHub web UI or `gh release create` generate a `ReleaseEvent`, not a `push` event, so the workflow never runs.

## Active Technologies
- JSON (Grafana dashboard configuration) + Grafana (provisioned), Prometheus (data source), existing metrics from PR #34 (013-prompt-cache-dashboard)
- N/A (dashboard configuration only) (013-prompt-cache-dashboard)
- Python 3.11+ + OpenTelemetry Prometheus exporter, Graphiti MCP server (015-memory-access-metrics)
- Neo4j / FalkorDB (existing graph database) (015-memory-access-metrics)
- PromQL (Prometheus Query Language), JSON (Grafana dashboard format) + Grafana 10.x, Prometheus (scraping OpenTelemetry metrics) (016-prometheus-dashboard-fixes)
- N/A (dashboard configuration files only) (016-prometheus-dashboard-fixes)

## Recent Changes
- 013-prompt-cache-dashboard: Added JSON (Grafana dashboard configuration) + Grafana (provisioned), Prometheus (data source), existing metrics from PR #34
