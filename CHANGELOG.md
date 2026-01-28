# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]


### Added


- Configurable memory sync with environment variable controls [007]
  - Enable/disable sync per source (LEARNING_ALGORITHM, LEARNING_SYSTEM, RESEARCH)
  - Custom exclude patterns via MADEINOZ_KNOWLEDGE_SYNC_EXCLUDE_PATTERNS
  - Max files per sync and verbose logging options
  - External path configuration via config/sync-sources.json
- Anti-loop detection to prevent knowledge query results from being re-synced [007]
  - 16 built-in patterns for MCP tools, query phrases, and formatted output
  - Prevents knowledge graph pollution from recursive syncing
- Sync status CLI command (`--status`) showing configuration and recent activity [007]
- Production Docker Compose for remote Neo4j deployment [007]
  - Native service names (neo4j, knowledge-mcp)
  - Self-contained deployment without PAI infrastructure
- Remote deployment documentation at docs/installation/remote-deployment.md [007]


### Changed


- Consolidated memory sync into single SessionStart hook (deprecated realtime sync) [007]


### Removed


- Deprecated sync-learning-realtime.ts hook (functionality moved to main sync hook) [007]


### Fixed


- Fix metric names and add heatmap visualizations

## [1.4.1] - 2026-01-27


### Fixed


- Use PROMPT_CACHE_ENABLED env var for cache metrics
- Standardize env var names in all patches (no prefix)

## [1.4.0] - 2026-01-27


### Added


- Gemini prompt caching with monitoring stack [006] ([#12](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/12))


### Fixed


- Release workflow checkout main before pushing CHANGELOG

## [1.3.0] - 2026-01-26


### Added


- Add temporal search with date filtering (v1.3.0) ([#9](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/9))


### Fixed


- Implement dual MCP protocol support for Neo4j and FalkorDB sync hooks

## [1.2.5] - 2026-01-19


### Added


- Madeinoz-knowledge-system v1.2.5


### Fixed


- Rename INDEX.md to index.md for case-sensitive filesystems


