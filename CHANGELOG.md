# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- LKAP (Large Knowledge Access Platform) two-tier memory model with RAGFlow document ingestion and Knowledge Graph integration
- RAGFlow semantic search with chunk retrieval and relevance scoring
- Knowledge promotion from RAG evidence chunks and direct query results
- Conflict resolution system for contradictory knowledge
- Knowledge provenance tracking for audit trails
- 6 new MCP tools: `rag.search`, `rag.getChunk`, `kg.promoteFromEvidence`, `kg.promoteFromQuery`, `kg.reviewConflicts`, `kg.getProvenance`
- New CLI: `rag-cli.ts` for RAG operations and document management
- New containers: RAGFlow document processing, Ollama (optional local embedding)

## [1.9.1] - 2026-02-05


### Fixed


- Resolve AsyncSession context manager error in investigate_entity ([#67](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/67))

## [1.9.0] - 2026-02-04


### Added


- Add weighted search support to Knowledge CLI ([#59](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/59))
- Add queue processing metrics for input monitoring ([#62](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/62))
- Add OSINT/CTI ontology support with custom entities and CLI commands ([#64](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/64))
- Investigative search with connected entities (Feature 020) ([#65](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/65))


### Fixed


- Extract docs artifact properly for GitHub Pages deployment
- Correct artifact upload/download for docs deployment
- Downgrade artifact actions to v3 for proper extraction
- Use v4 artifact actions with directory-preserving path
- Upgrade peaceiris/actions-gh-pages to v4
- Use peaceiris/actions-gh-pages@v4 built-in artifact download
- Rebuild docs in Release job instead of artifact download

## [1.8.4] - 2026-02-02


### Fixed


- Clean Python bytecode cache in Docker build ([#55](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/55))
- Update Grafana dashboards to query OpenTelemetry metric names with unit infixes ([#57](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/57))

## [1.8.3] - 2026-02-02


### Fixed


- Fix Docker cache issue and add build info metric (issues #45, #51) ([#52](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/52))
- Metrics_exporter indentation bug ([#51](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/51))

## [1.8.0] - 2026-02-01


### Added


- Add Grafana prompt cache effectiveness dashboard ([#40](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/40))
- Add Memory Access Patterns dashboard ([#42](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/42))
- Add memory access pattern instrumentation ([#41](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/41)) ([#43](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/43))


### Fixed


- Prometheus dashboard queries and observability improvements ([#44](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/44))

## [1.7.2] - 2026-01-31


### Added


- Add access pattern metrics and resolve gaps ([#34](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/34))


### Fixed


- Fix AsyncResult consumption in decay score histogram recording ([#25](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/25))
- Fix changelog generation: breaking changes, issue linking, race conditions ([#33](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/33))
- Include GitHub PR merges in changelog
- Make commit parsers case-insensitive for GitHub PR titles
- Strip commit body from changelog entries
- Strip everything after first newline from commit messages

## [1.7.1] - 2026-01-30


### Fixed


- Pass LLM client to maintenance service and improve classification ([#23](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/23))

## [1.7.0] - 2026-01-30


### Added


- Add remote MCP access to knowledge-cli (client-only) ([#20](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/20))

## [1.6.0] - 2026-01-29


### Added


- Memory Decay Scoring & Lifecycle Management ([#15](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/15))

## [1.5.0] - 2026-01-28


### Added


- Fix metric names and add heatmap visualizations
- Configurable memory sync with external config (v1.5.0) ([#13](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/13))


### Fixed


- Correct icon path in README
- Discard local CHANGELOG.md changes before branch switch

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


