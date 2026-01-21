# madeinoz-knowledge-system Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-18

## Active Technologies
- Python 3.x (MkDocs), YAML (configuration), Markdown (content) + MkDocs 1.6+, mkdocs-material 9.5+, GitHub Actions (002-mkdocs-documentation)
- Static markdown files in `docs/` directory (002-mkdocs-documentation)
- TypeScript (ES modules, strict mode), Bun runtime + @modelcontextprotocol/sdk (existing), existing mcp-client.ts library (003-fix-issue-2)
- Neo4j (default) or FalkorDB backend via Docker/Podman containers (003-fix-issue-2)
- YAML (Docker/Podman Compose v2.x) + Docker Compose v2.x or Podman Compose (004-fix-env-file-loading)
- N/A (configuration files only) (004-fix-env-file-loading)

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
- 004-fix-env-file-loading: Added YAML (Docker/Podman Compose v2.x) + Docker Compose v2.x or Podman Compose
- 003-fix-issue-2: Added TypeScript (ES modules, strict mode), Bun runtime + @modelcontextprotocol/sdk (existing), existing mcp-client.ts library
- 002-mkdocs-documentation: Added Python 3.x (MkDocs), YAML (configuration), Markdown (content) + MkDocs 1.6+, mkdocs-material 9.5+, GitHub Actions


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
