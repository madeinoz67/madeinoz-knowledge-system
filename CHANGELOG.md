# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.8.2] - 2026-02-02


### Fixed


- Fix Docker cache issue and add build info metric (issues #45, #51) ([#52](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/52))

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


