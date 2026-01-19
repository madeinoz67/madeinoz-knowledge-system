# Changelog

All notable changes to the Madeinoz Knowledge System are documented here.

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
