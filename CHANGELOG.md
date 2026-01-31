# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]


### Added


- Add access pattern metrics and resolve gaps ([#34](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/34))


### Fixed


- Fix AsyncResult consumption in decay score histogram recording ([#25](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/25))

* Initial plan

* Fix: Replace AsyncResult.list() with async list comprehension in memory_decay.py

Co-authored-by: madeinoz67 <4160293+madeinoz67@users.noreply.github.com>

---------

Co-authored-by: copilot-swe-agent[bot] <198982749+Copilot@users.noreply.github.com>
Co-authored-by: madeinoz67 <4160293+madeinoz67@users.noreply.github.com>
- Fix changelog generation: breaking changes, issue linking, race conditions ([#33](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/33))

* Initial plan

* fix(ci): Add breaking changes protection, GitHub keywords, and concurrency control to changelog

- P0: Set protect_breaking_commits = true in cliff.toml
- P0: Add breaking change parsers for !: suffix and BREAKING CHANGE: footer
- P1: Add GitHub keywords regex (Closes/Fixes/Resolves [#123](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/123)) to commit_preprocessors
- P1: Add concurrency control to release and update-unreleased jobs
- P2: Enable [remote.github] integration for PR metadata

Co-authored-by: madeinoz67 <4160293+madeinoz67@users.noreply.github.com>

* test: Add validation scripts and documentation for changelog fixes

- Add tests/validate-cliff-config.py to verify cliff.toml configuration
- Add tests/validate-ci-workflow.py to verify CI concurrency settings
- Add .github/CHANGELOG_FIXES.md with detailed before/after examples
- All validation tests pass

Co-authored-by: madeinoz67 <4160293+madeinoz67@users.noreply.github.com>

* docs: Add dependency documentation to CI validation script

Co-authored-by: madeinoz67 <4160293+madeinoz67@users.noreply.github.com>

---------

Co-authored-by: copilot-swe-agent[bot] <198982749+Copilot@users.noreply.github.com>
Co-authored-by: madeinoz67 <4160293+madeinoz67@users.noreply.github.com>
- Include GitHub PR merges in changelog
- Make commit parsers case-insensitive for GitHub PR titles

## [1.7.1] - 2026-01-30


### Fixed


- Pass LLM client to maintenance service and improve classification ([#23](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/23))

## [1.7.0] - 2026-01-30


### Added


- Add remote MCP access to knowledge-cli (client-only) ([#20](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/20))


### Security


- Bump version to 1.7.0 for remote MCP access feature

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


### Security


- Add SECURITY.md with vulnerability reporting policy

## [1.2.5] - 2026-01-19


### Added


- Madeinoz-knowledge-system v1.2.5


### Fixed


- Rename INDEX.md to index.md for case-sensitive filesystems


