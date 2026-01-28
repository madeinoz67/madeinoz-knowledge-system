# madeinoz-knowledge-system Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-18

## Active Technologies
- Python 3.x (MkDocs), YAML (configuration), Markdown (content) + MkDocs 1.6+, mkdocs-material 9.5+, GitHub Actions (002-mkdocs-documentation)
- Static markdown files in `docs/` directory (002-mkdocs-documentation)
- TypeScript (ES modules, strict mode), Bun runtime + @modelcontextprotocol/sdk (existing), existing mcp-client.ts library (003-fix-issue-2)
- Neo4j (default) or FalkorDB backend via Docker/Podman containers (003-fix-issue-2)
- YAML (Docker/Podman Compose v2.x) + Docker Compose v2.x or Podman Compose (004-fix-env-file-loading)
- N/A (configuration files only) (004-fix-env-file-loading)
- Markdown (documentation), YAML (Docker/Podman Compose v2.x) + Docker Compose v2.x or Podman Compose (001-docs-compose-updates)
- N/A (documentation and configuration files only) (001-docs-compose-updates)
- TypeScript (ES modules, strict mode) with Bun runtime + @modelcontextprotocol/sdk, node:fs, node:crypto (001-configurable-memory-sync)
- Neo4j graph database via Graphiti MCP server (001-configurable-memory-sync)

- TypeScript (ES modules, strict mode), Bun runtime + @modelcontextprotocol/sdk (existing), mcp-client.ts library (existing) (001-mcp-wrapper)

## Project Structure

```text
src/
tests/
```

## Commands

npm test && npm run lint

## Code Style

TypeScript (ES modules, strict mode), Bun runtime: Follow standard conventions

## Recent Changes
- 001-configurable-memory-sync: Added TypeScript (ES modules, strict mode) with Bun runtime + @modelcontextprotocol/sdk, node:fs, node:crypto
- 001-docs-compose-updates: Added Markdown (documentation), YAML (Docker/Podman Compose v2.x) + Docker Compose v2.x or Podman Compose
- 004-fix-env-file-loading: Added YAML (Docker/Podman Compose v2.x) + Docker Compose v2.x or Podman Compose


<!-- MANUAL ADDITIONS START -->

## Memory-to-Knowledge Sync Configuration

The system syncs LEARNING and RESEARCH files from `~/.claude/MEMORY/` to the knowledge graph.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MADEINOZ_KNOWLEDGE_SYNC_LEARNING_ALGORITHM` | `true` | Enable sync for LEARNING/ALGORITHM files |
| `MADEINOZ_KNOWLEDGE_SYNC_LEARNING_SYSTEM` | `true` | Enable sync for LEARNING/SYSTEM files |
| `MADEINOZ_KNOWLEDGE_SYNC_RESEARCH` | `true` | Enable sync for RESEARCH files |
| `MADEINOZ_KNOWLEDGE_SYNC_EXCLUDE_PATTERNS` | - | Comma-separated custom exclude patterns (overrides config file) |
| `MADEINOZ_KNOWLEDGE_SYNC_MAX_FILES` | `50` | Max files per sync run (1-1000) |
| `MADEINOZ_KNOWLEDGE_SYNC_VERBOSE` | `false` | Enable verbose logging |

### CLI Usage

```bash
# Run sync manually
bun run src/hooks/sync-memory-to-knowledge.ts

# Show sync status
bun run src/hooks/sync-memory-to-knowledge.ts --status

# Sync all files (not just recent)
bun run src/hooks/sync-memory-to-knowledge.ts --all

# Dry run with verbose output
bun run src/hooks/sync-memory-to-knowledge.ts --dry-run --verbose
```

### External Configuration

Sync configuration can be customized via `config/sync-sources.json`:

```json
{
  "version": "1.0",
  "sources": [
    {
      "id": "LEARNING_ALGORITHM",
      "path": "LEARNING/ALGORITHM",
      "type": "LEARNING",
      "description": "Task execution learnings",
      "defaultEnabled": true
    }
  ],
  "customExcludePatterns": [
    "meeting notes",
    "/^draft-/i"
  ]
}
```

**Pattern types:**
- Substring match: `"meeting notes"` (case-insensitive)
- Regex: `"/^draft-/i"` (surrounded by `/`, optional flags)

### Anti-Loop Detection

The system automatically excludes knowledge-derived content from being re-synced to prevent feedback loops. Built-in patterns detect:
- MCP tool invocations (`mcp__madeinoz-knowledge__`)
- Query phrases ("what do I know about")
- Formatted search output ("Knowledge Found:", "Key Entities:")

## Codanna Code Intelligence

### CLI Syntax

Codanna supports both MCP tools and CLI commands with Unix-friendly syntax:

**Simple Commands (positional arguments):**
```bash
# Text output (DEFAULT - prefer this to save context)
codanna mcp find_symbol main
codanna mcp get_calls process_file
codanna mcp find_callers init

# JSON output (only when structured data needed)
codanna mcp find_symbol main --json
```

**Complex Commands (key:value pairs):**
```bash
# Text output (DEFAULT - prefer this)
codanna mcp search_symbols query:parse limit:10
codanna mcp semantic_search_docs query:"error handling"

# JSON output (only for parsing/piping)
codanna mcp search_symbols query:parse --json | jq '.data[].name'
```

**Important:** Prefer TEXT output - JSON fills context window quickly (3-5x more tokens).

### Search Workflow

1. **Semantic Search** (start here):
   ```bash
   codanna mcp semantic_search_with_context query:"your search" limit:5
   ```

2. **Read Code** using line ranges from search results:
   - Formula: `limit = end_line - start_line + 1`
   - Use Read tool with `offset` and `limit` parameters

3. **Explore Details**:
   ```bash
   codanna retrieve describe symbol_id:896
   ```

4. **Follow Relationships**:
   ```bash
   codanna retrieve callers symbol_id:896
   codanna retrieve calls symbol_id:896
   ```

### Document Search

```bash
codanna mcp search_documents query:"installation guide" limit:5
```

### Tips

- Read only line ranges provided (saves tokens)
- Use symbol_id to chain commands
- Add `lang:rust` to filter by language
- Use `rg` (ripgrep) for pattern matching: `rg "pattern" src/`

<!-- MANUAL ADDITIONS END -->
