# Changelog

All notable changes to the Madeinoz Knowledge System are documented here.

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
