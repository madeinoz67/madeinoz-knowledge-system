# Changelog

All notable changes to the Madeinoz Knowledge System are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **GitHub Actions CI/CD Pipeline** - Automated Docker image builds and releases
  - Multi-platform builds (linux/amd64, linux/arm64)
  - Auto-publish to GitHub Container Registry (`ghcr.io/madeinoz67/madeinoz-knowledge-system`)
  - Optional Docker Hub publishing (with secrets configuration)
  - Semantic version tagging (`latest`, `fixed`, `1.0.1`, `1.0`, `1`, `sha-abc123`)
  - Image testing before publish
  - Triggered by pushes to main, version tags, and manual dispatch

- **Release Automation Workflow** - Manual release workflow for version management
  - Version validation (semantic versioning)
  - Automatic changelog generation from git commits
  - GitHub Release creation with auto-generated notes
  - Dockerfile version label updates
  - Triggers Docker build via tag push

- **Developer Documentation** - Comprehensive technical reference
  - Custom Docker image rationale and patches explanation
  - Migration path to official upstream images (when patches are merged)
  - Environment variable prefix workaround (`MADEINOZ_KNOWLEDGE_*` → unprefixed)
  - Patch details: async bug fix, Ollama support, search-all-groups
  - Network alias fix for Podman DNS resolution

- **Release Process Documentation** - Complete release guide
  - Step-by-step release instructions
  - Semantic versioning guidelines
  - Rollback procedures
  - Troubleshooting section
  - Docker Hub configuration guide

- **Custom Docker Image** - `madeinoz-knowledge-system:fixed` with baked-in patches
  - Applies three critical upstream patches at build time
  - Supports both Neo4j and FalkorDB backends
  - Dynamic config selection via `DATABASE_TYPE` environment variable
  - Environment prefix mapping via `entrypoint.sh`

### Fixed

- **Neo4j Password Typo** - Fixed inconsistent password in `docker-compose-neo4j.yml`
  - Changed `madeinojknowledge` → `madeinozknowledge` (missing 'z')
  - Affected lines 62 and 88 in docker-compose file
  - Resolved authentication failures

- **Volume Mount Conflict** - Removed read-only volume mounts in `run.ts`
  - Custom image has configs and patches baked in
  - Entrypoint now copies correct config based on `DATABASE_TYPE`
  - Fixed crash-loop with "Read-only file system" error

- **Async Iteration Bug** - Added None check in `graphiti_mcp_server.patch`
  - Fixed "async for requires __aiter__ method, got NoneType" error
  - Added defensive `if result:` check before async iteration
  - Prevents crashes when `get_all_group_ids()` returns None

- **Network Alias for Podman** - Added explicit DNS aliases in `run.ts`
  - Added `--network-alias=falkordb` for FalkorDB container
  - Added `--network-alias=neo4j` for Neo4j container
  - Fixed "Error -2 connecting to falkordb:6379" on Podman
  - Docker handles this automatically, Podman requires explicit aliases

- **Container Image References** - Updated `container.ts` to use custom image
  - Changed from upstream images to `madeinoz-knowledge-system:fixed`
  - Both Neo4j and FalkorDB backends now use the patched custom image
  - Ensures all patches are applied consistently

### Changed

- **README Updates** - Added Docker quick start and badges
  - GitHub Actions build status badge
  - Latest release version badge
  - Docker Hub pulls badge
  - GitHub Container Registry badge
  - Quick Start with Docker section
  - Pull commands for both GHCR and Docker Hub

- **Documentation Navigation** - Added new reference sections
  - Developer Notes in docs navigation
  - Release Process in docs navigation
  - Updated mkdocs.yml structure

### Tested

- **Neo4j Backend Verification** - Complete end-to-end testing
  - ✅ Containers start successfully via docker-compose
  - ✅ Authentication with corrected password
  - ✅ Database connectivity via Cypher queries
  - ✅ Episode storage and retrieval
  - ✅ Entity extraction (4 entities from test episode)
  - ✅ Semantic search functionality
  - ✅ All Madeinoz patches active (search-all-groups, Ollama, OpenRouter)
  - ✅ Health endpoint returns proper JSON
  - ✅ Network alias DNS resolution

## [1.2.5] - 2026-01-20

### Fixed

- **Sync Hook Protocol Mismatch** - Fixed critical bug where sync hook only supported SSE GET protocol (FalkorDB) and failed with Neo4j backend. Now implements dual protocol support:
  - **FalkorDB**: SSE GET to `/sse` endpoint (preserved original working code)
  - **Neo4j**: HTTP POST to `/mcp` endpoint with JSON-RPC 2.0 protocol
  - Session management with `Mcp-Session-Id` header for Neo4j
  - Exponential backoff retry logic for transient failures

### Changed

- **Database-specific protocol routing** - `MADEINOZ_KNOWLEDGE_DB` environment variable now determines which MCP client protocol to use
- **Conditional query sanitization** - Lucene special character escaping (for hyphenated CTI identifiers like `apt-28`) now applied only for FalkorDB, not Neo4j

### Technical Details

- Created separate `FalkorDBClient` and `Neo4jClient` classes in `src/hooks/lib/knowledge-client.ts`
- Database type validation: `neo4j` or `falkorodb` (throws error on invalid values)
- SSE response body parsing to extract `data:` lines with JSON-RPC results
- Graceful degradation when MCP server is unavailable

## [1.2.4] - 2026-01-19

### Fixed

- **EdgeDuplicate/ExtractedEntities Pydantic validation errors** - Applied fix from [Graphiti issue #912](https://github.com/getzep/graphiti/issues/912) to use `OpenAIClient` instead of `OpenAIGenericClient` for cloud LLM providers (OpenRouter, Together, etc.). This provides stricter JSON schema enforcement via the parse API, preventing LLMs from returning schema definitions instead of actual values.

### Changed

- **Default LLM changed to Gemini 2.0 Flash** - Now uses `google/gemini-2.0-flash-001` via OpenRouter for better cost-performance balance
- **LLM client selection logic** - Cloud providers now use `OpenAIClient` (parse API), while local endpoints (Ollama) continue to use `OpenAIGenericClient` (json_object mode)

### Tested

Models verified working with the OpenAIClient patch:
- `openai/gpt-4o-mini` via OpenRouter ✅
- `openai/gpt-4o` via OpenRouter ✅
- `google/gemini-2.0-flash-001` via OpenRouter ✅

Note: Intermittent validation errors still occur but are now recoverable via built-in retry logic (2 retries max).

## [1.2.3] - 2026-01-18

### Fixed

- Environment variable naming standardization (`MADEINOZ_KNOWLEDGE_*` prefix)
- Docker compose port mapping for Neo4j backend
- Installation process now replaces ALL pack files on version change

## [1.2.2] - 2026-01-17

### Added

- Neo4j backend support as default (alongside FalkorDB)
- Knowledge CLI for token-efficient operations (30-84% token savings)
- Lucene query sanitization for special characters

### Fixed

- Pydantic validation errors with Ollama models
- Group ID handling with special characters

## [1.2.1] - 2026-01-15

### Added

- Model benchmark results documentation
- Ollama model compatibility guide

## [1.2.0] - 2026-01-12

### Added

- MCP wrapper implementation for efficient knowledge operations
- Session sync hooks for Memory System integration
- Multi-backend support (Neo4j and FalkorDB)

## [1.1.0] - 2026-01-05

### Added

- Initial Graphiti MCP server integration
- Basic entity extraction and relationship mapping
- Semantic search capabilities

## [1.0.0] - 2026-01-01

### Added

- Initial release
- FalkorDB backend
- Core MCP tools (add_memory, search_nodes, search_facts, etc.)
