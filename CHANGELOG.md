# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]


### Added


- Feat(metrics): add access pattern metrics and resolve gaps ([#34](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/34))
- Add explicit Views for importance/stability histograms with correct
  buckets [1,2,3,4,5] instead of default [0,5,10,25...]
- Wire up search_weighted_latency_seconds recording in apply_weighted_scoring()
- Add knowledge_reactivations_total counter with from_state label
- Expand age distribution gauge from 4 to 6 buckets aligned with
  180-day half-life lifecycle thresholds:
  - UNDER_7_DAYS, DAYS_7_TO_30, DAYS_30_TO_90
  - DAYS_90_TO_180 (DORMANT territory)
  - DAYS_180_TO_365 (ARCHIVED territory)
  - OVER_365_DAYS (approaching/at EXPIRED)
- Update data-model.md to reflect correct 180-day half-life
- Document actual transition times (~93d DORMANT, ~238d ARCHIVED, ~598d EXPIRED)
- Update YAML config example with current values
- Counter: knowledge_access_by_importance_total (by level label)
- Counter: knowledge_access_by_state_total (by state label)
- Histogram: knowledge_days_since_last_access (access frequency)
- Add record_access_pattern() method to DecayMetricsExporter
- Update Cypher queries to return importance, state, days_since_access
- Wire up metrics in update_access_on_retrieval()
- Update data-model.md spec with new metrics and label definitions
to new 6-bucket schema aligned with lifecycle thresholds:
- days_90_to_180 (was: over_90_days)
- days_180_to_365 (new)
- over_365_days (new)


### Fixed


- Fix AsyncResult consumption in decay score histogram recording ([#25](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/25))
Co-authored-by: madeinoz67 <4160293+madeinoz67@users.noreply.github.com>
- Fix changelog generation: breaking changes, issue linking, race conditions ([#33](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/33))
- P0: Add breaking change parsers for !: suffix and BREAKING CHANGE: footer
- P1: Add GitHub keywords regex (Closes/Fixes/Resolves [#123](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/123)) to commit_preprocessors
- P1: Add concurrency control to release and update-unreleased jobs
- P2: Enable [remote.github] integration for PR metadata
- Add tests/validate-ci-workflow.py to verify CI concurrency settings
- Add .github/CHANGELOG_FIXES.md with detailed before/after examples
- All validation tests pass
Co-authored-by: madeinoz67 <4160293+madeinoz67@users.noreply.github.com>
- Fix(cliff): include GitHub PR merges in changelog
merges that use "Fix X ([#123](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/123))" format instead of "fix: X".
the changelog. This restores visibility for all user-facing commits.
- Fix(cliff): make commit parsers case-insensitive for GitHub PR titles
were case-sensitive "^fix". Added (?i) flag to all patterns to capture
both GitHub-style and conventional-commit-style messages.
- Fix(cliff): strip commit body from changelog entries
keeping only the commit subject. This prevents verbose PR bodies
from cluttering the changelog.

## [1.7.1] - 2026-01-30


### Fixed


- Fix: pass LLM client to maintenance service and improve classification ([#23](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/23))
for importance/stability classification.
- Fixed llm_client access in classify_memory MCP tool (was accessing
  client.llm_client instead of graphiti_service.llm_client)
- Fixed generate_response call format (now passes Message objects
  instead of plain string)
- Fixed response parsing (handles dict responses from Graphiti)
- Added forced-choice classification prompt to overcome LLM central
  tendency bias
- Added documentation about central tendency bias and mitigation
- SSN → 5/5 PERMANENT (correctly identified as CORE)
- "Wonder about weather" → 1/1 (correctly identified as TRIVIAL)
- "Paris is capital of France" → 2/5 (LOW but permanent)
the module is not available. Made the import optional with
try/except to fall back to string format for backward compatibility
with existing tests.
- test_successful_classification
- test_content_truncation
- test_source_description_included
prompt length. The forced-choice prompt is now longer due to
bias mitigation instructions, but the content should still be
truncated to 2000 chars as expected.
- Added forced-choice prompting to overcome LLM central tendency bias
- Fixed Message import for test compatibility
- Updated documentation with central tendency bias research
- YAML formatting consistency (list format for commands)

## [1.7.0] - 2026-01-30


### Added


- Feat: add remote MCP access to knowledge-cli (client-only) ([#20](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/20))
- Add HTTPS client support with TLS certificate verification
- Add YAML-based connection profile management
- Add CLI flags: --host, --port, --protocol, --profile, --tls-no-verify
- Add --status and --list-profiles commands
- Add docs/remote-access.md with AI-friendly summary
standard Docker port binding (-p 8000:8000). TLS termination
handled by external reverse proxy (nginx, traefik, etc.).
   - Replace failing require() with ES module import for loadProfileWithOverrides
   - Fix spread order in createMCPClient() to prevent undefined envConfig values
     from overriding profile config
   - Now correctly loads remote profile (10.0.0.150:8001) when called without args
   - Add missing notifications/initialized notification after initialize call
   - Required by FastMCP HTTP transport for proper session handshake
   - Applied to both mcp-client.ts and knowledge-client.ts
   - Add 54 comprehensive tests for profile functionality
   - Tests cover profile loading, validation, environment overrides, and CLI integration
   - All 365 tests passing
- src/skills/lib/mcp-client.ts: ES module import, spread order fix, notification
- src/hooks/lib/knowledge-client.ts: Add notifications/initialized notification
- tests/unit/lib/connection-profile.test.ts: 25 unit tests
- tests/unit/lib/mcp-client-profiles.test.ts: 14 unit tests
- tests/integration/knowledge-cli-profiles.test.ts: 15 integration tests
- connection-profile.ts: Removed unused 'dirname' import, prefixed unused error vars with '_'
- knowledge-client.ts: Fixed checkHealth to use effectiveConfig while respecting passed config
enable mock responses in integration tests, preventing network calls
that cause timeouts on CI.
- mcp-client.ts: Add test mode check in testConnection() to return mock response
- knowledge-cli-profiles.test.ts: Use test mode env var for all status command tests
- Add 10-second timeout to runCLI() to prevent hanging processes
requiring a running MCP server.
Removed version from mock response to match interface.
but ConnectionProfileManager looks for tempDir/config/knowledge-profiles.yaml.
Added mkdirSync for config subdirectory in beforeEach.
- Fix broken link to specs/010-remote-mcp-access/quickstart.md
- Fix installation/ link to installation/index.md
- Add key validation to setNestedProperty to prevent prototype pollution
- Sensitive data logging in mcp-client.ts
- Prototype pollution in connection-profile.ts
- AI-friendly summary with system info, tools, ports, configuration
- Quick reference table for common commands
- Remote Access CLI Options section documenting:
  - Connection profiles (--profile, --list-profiles)
  - CLI flags (--host, --port, --protocol)
  - Environment variable overrides
  - Profile configuration file format
  - New commands: status, list_profiles
hidden metadata (AI-friendly summary), and quick reference sections.
could lead to prototype pollution attacks. Previous regex validation
allowed properties like __proto__ since it starts with underscore.
- __proto__, constructor, prototype (direct prototype pollution)
- toString, toLocaleString, valueOf (object coercion methods)
- hasOwnProperty, isPrototypeOf, propertyIsEnumerable (reflection methods)
traverse and mutate plain objects (not arrays, dates, or objects
with modified prototypes).
- Add isPlainObject() helper that verifies:
  1. Value is a non-null object
  2. Object toString() returns '[object Object]' (not Array, Date, etc.)
  3. Prototype chain is Object.prototype or null
- Validate each intermediate object during traversal
- Validate final object before assignment
- Better error messages for debugging
pollution mitigation.

## [1.6.0] - 2026-01-29


### Added


- Feat(009): Memory Decay Scoring & Lifecycle Management ([#15](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/15))
lifecycle management, and observability metrics for the Knowledge system.
- Automatic importance (1-5) and stability (1-5) classification at ingestion
- Exponential decay calculation with stability-adjusted half-life
- Weighted search combining semantic (60%), recency (25%), importance (15%)
- Lifecycle state transitions (ACTIVE → DORMANT → ARCHIVED → EXPIRED → SOFT_DELETED)
- Permanent memory exemption (importance ≥4 AND stability ≥4)
- Automated maintenance with 10-minute timeout constraint
- 90-day soft-delete retention window with recovery capability
- decay_types.py: Enumerations and dataclasses for decay system
- decay_config.py: YAML configuration loader
- decay_migration.py: Neo4j index creation and backfill migration
- importance_classifier.py: LLM-based importance/stability classification
- memory_decay.py: Decay calculator and weighted search scoring
- lifecycle_manager.py: State transition logic and reactivation
- maintenance_service.py: Batch processing and orchestration
- metrics_exporter.py: Prometheus metrics (counters, gauges, histograms)
- test_decay_integration.py: End-to-end integration tests (810 lines, 12 tests)
- test_importance_classifier.py: Classification unit tests
- test_lifecycle_manager.py: State transition unit tests
- test_maintenance_service.py: Maintenance orchestration tests
- test_memory_decay.py: Decay calculation unit tests
- test_metrics_exporter.py: Metrics registration tests
- specs/009-memory-decay-scoring/: Complete feature specification
  - spec.md: User stories, requirements, success criteria
  - plan.md: Implementation plan and architecture
  - research.md: Research on decay algorithms and ML approaches
  - data-model.md: Data model and API contracts
  - quickstart.md: Developer quickstart guide
  - tasks.md: 68 implementation tasks with dependencies
- src/skills/workflows/HealthReport.md: Health report workflow
- src/skills/workflows/RunMaintenance.md: Maintenance execution workflow
- CLAUDE.md: Memory decay configuration documentation
- docs/reference/observability.md: Prometheus metrics and alerting
- config/decay-config.yaml: Decay thresholds, weights, maintenance settings
- config/monitoring/prometheus/alerts/knowledge.yml: Alert rules
- Prometheus metrics on port 9090
- Health check endpoints: /health/decay, /metrics
- Alert rules for maintenance timeout, classification degradation
- health_metrics: Get memory lifecycle health metrics
- run_maintenance: Run decay maintenance cycle
- classify_memory: Classify memory importance and stability
- recover_memory: Recover a soft-deleted memory
to interact with memory decay scoring and lifecycle management
via the command line interface.
- Add 4 new CLI commands to frontmatter tools array (auto-discovery)
- Add Feature 009 keywords to description field (triggers)
- Document 4 new CLI commands in CLI section
- Add 4 new MCP tools to reference table
- Update workflows to use CLI-first approach
- Fix path inconsistency in RunMaintenance.md Step 2
- Clean up troubleshooting section to remove unsupported parameters
features through natural language triggers and tools array.
utils. prefix, allowing Feature 009 modules to load correctly in the MCP server.
- Dockerfile: Add pyyaml>=6.0 dependency, update version to 1.5.0
- All decay patch files: Fix relative imports (decay_config, decay_migration,
  lifecycle_manager, maintenance_service, memory_decay, importance_classifier,
  graphiti_mcp_server)
- mcp-client.ts: Update DEFAULT_BASE_URL to port 8001 for dev environment
imported successfully, and the MCP client connects to the correct dev port.
- health_metrics: ✓ Returns 46 active nodes with full decay metrics
- classify_memory: ✓ Classifies content for importance and stability
- run_maintenance: ✓ Processes decay cycles in 0.42s
- recover_memory: ✓ Handles soft-deleted memory recovery
- Add Graph Health dashboard with errors heatmap
- Restore original Madeinoz Knowledge System dashboard from git
- Fix Prometheus datasource UID references
- Update dev compose Prometheus port from 9092 to 9093
- Histogram views: search_query_latency, days_since_access, search_result_count
- Counters: memory_access, memories_created, zero_result_searches
- Gauge: orphan_entities (disconnected entities from graph)
- Recording methods: record_memory_access(), record_memory_created(),
  record_search_execution(), update_orphan_count()
- search_nodes: record latency, result count, zero results, memory access
- search_memory_facts: record latency, result count, zero results, memory access
- All return paths instrumented (weighted, standard, zero-result)
- ORPHAN_ENTITIES_QUERY: count entities with no relationships
- HealthMetrics.aggregates: include orphan_entities
- get_health_metrics: fetch and record orphan count
- batch_update_decay_scores: record all decay scores to histogram
- Orphan Entities gauge (green/yellow/orange/red thresholds)
- Memory Access Rate (ops/sec)
- Zero Result % (green/yellow/red thresholds)
- Memories Created (1h)
- Search Query Latency (P50/P95 timeseries)
- Search Result Count Distribution (heatmap)
- bun run start → bun run server-cli --start
- bun run stop → bun run server-cli --stop
- bun run restart → bun run server-cli --restart
- bun run status → bun run server-cli --status
- bun run logs → bun run server-cli --logs
- CLAUDE.md
- docs/index.md
- docs/installation/index.md
- docs/usage/backup-restore.md
- src/skills/server/install.ts
- src/skills/tools/Install.md
- bun run server-cli --start → bun run server-cli start
- bun run server-cli --stop → bun run server-cli stop
- bun run server-cli --restart → bun run server-cli restart
- bun run server-cli --status → bun run server-cli status
- bun run server-cli --logs → bun run server-cli logs
- bun run server-cli logs --mcp --tail 50
- bun run server-cli start --dev
generating the required dev env files. Now both start and restart
call generateEnvFiles() to ensure env files exist before running
docker-compose/podman-compose.
- Added generateEnvFiles() call to restart() function
- Dev mode now properly generates env files before restart
- Add "Development Mode" section with usage examples
- Document dev mode differences (ports, env files)
- Explain when to use dev mode
- Add --dev flag documentation to start command
- Add restart command documentation (was missing)
- Add development mode comparison table
- Update logs command with correct --tail flag
- Add all log options (--mcp, --db, --no-follow)
- Add HEALTH_IMPORTANCE_DISTRIBUTION_QUERY to maintenance_service.py for importance aggregation
- Update HealthMetrics to include importance_distribution field
- Reposition "By Importance" pie chart to second row of dashboard (replacing "Maintenance (1h)")
- Fix "Maintenance" status panel to show "Completed" when maintenance has run (vs checking last hour)
- Add schedule_interval_hours configuration to MaintenanceConfig (default: 24 hours)
- Document container rebuild workflow in CLAUDE.md for development
  (central hub, data flows, lifecycle states, quality metrics, observability)
- Replace main README icon with full architecture infographic
- Replace Grafana dashboard screenshot with sidebar-collapsed version
  (2560x1440 resolution, shows full dashboard width)
- Add new System Architecture section to docs/index.md
  - Importance and stability classification (1-5 scales)
  - Decay scoring and lifecycle state management
  - Weighted search formula and configuration
  - Maintenance operations and monitoring
  - AI-friendly summary for rapid context loading
  - Integrate Memory Decay into architecture diagrams
  - Replace ASCII diagrams with Excalidraw-style infographic
  - Generic LLM provider references (removed gpt-4o-mini/gpt-4o)
  - Change "Document Import" to "Document Text Import"
  - Add weighted search to "How It Works" examples
  - Update Design Principles to include memory prioritization
  - architecture-flow-diagram.png (1024x682)
  - memory-decay-importance-stability-matrix.png
  - memory-decay-lifecycle-timeline.png
  - memory-decay-weighted-search-formula.png
  - memory-decay-permanent-protection.png
- Update navigation (mkdocs.yml, index.md) to include memory decay page
Docker images instead of pulling from GitHub Container Registry.
- Uses image: madeinozknowledge-system:local (local build)
- Instead of: ghcr.io/madeinoz67/madeinoz-knowledge-system:1.4.1 (registry)
before publishing to the registry.
- Bun test runner for all TypeScript tests
- ESLint linting check
- TypeScript type checking (non-blocking)
- Uses uv for fast Python package management
- Runs unit tests from docker/tests/unit/
- Runs integration tests from docker/tests/integration/
- Dependencies: pytest, pytest-asyncio, pydantic, pyyaml, prometheus-client
- Push to main, develop, and any branch
- Pull requests to main/develop
- Manual workflow dispatch
packages. GitHub Actions uses system Python, so we need --system.
a utils/ subdirectory structure matching the container layout
(/app/mcp/src/utils/).
the parent patch files, allowing tests to import correctly.
own database sessions:
   - Mock batch_update_decay_scores, batch_transition_states, and
     purge_expired_soft_deletes directly since they create their own
     sessions (not using the mocked session.run)
   - These functions return values directly (int, StateTransitionResult),
     not session results with .single
   - Add missing mock results for ORPHAN_ENTITIES_QUERY and
     HEALTH_IMPORTANCE_DISTRIBUTION_QUERY
   - get_health_metrics makes 5 session.run calls, but test only
     mocked 3, causing side_effect to return None for later calls
via driver.session() rather than reusing the parent's session, so they
can't be mocked via session.run() alone.
- bun run start → bun run server-cli start
- bun run stop → bun run server-cli stop
- bun run restart → bun run server-cli restart
- bun run status → bun run server-cli status
- bun run logs → bun run server-cli logs
- specs/003-fix-issue-2/quickstart.md
- specs/003-fix-issue-2/tasks.md
- specs/009-memory-decay-scoring/quickstart.md
- specs/001-mcp-wrapper/quickstart.md
- specs/001-mcp-wrapper/tasks.md
- docs/concepts/hooks-integration.md
- .specify/memory/constitution.md
now uses correct server-cli command format.
tests into a single CI job with sequential steps:
2. Type check (TypeScript)
3. TypeScript Tests
4. Python Tests
that runs all checks sequentially. This provides:
- Better organization with all CI checks in one place
- Clearer status indication (single CI job status)
- More efficient use of GitHub Actions resources
and Python tests, but within a single job rather than separate parallel jobs.
purpose.
jobs running in parallel, rather than a single sequential CI job.
1. TypeScript Tests - runs Bun test, lint, typecheck
2. Python Tests (Feature 009) - runs pytest with uv
The main CI workflow (ci.yml) already exists and handles TypeScript testing.
differently, not as a separate tests.yml workflow.
- Add 'python-tests' job running in parallel after lint
- Update 'build' job to depend on both test stages
- Build only proceeds if typescript-tests AND python-tests pass
before any build or release operations can occur.
for cleaner CI workflow display.
- METRICS_PORT: Prometheus metrics port (default: 9090)
- PROMPT_CACHE_METRICS_ENABLED: Enable/disable metrics (default: true)
- DECAY_CONFIG_PATH: Optional custom decay config path
This separate workflow file is no longer needed.

## [1.5.0] - 2026-01-28


### Added


- Feat(dashboard): fix metric names and add heatmap visualizations
- Replace non-functional Input/Output Cost panel with Total Cost vs Cache Savings
- Add new Heatmaps row with 3 panels:
  - Request Latency Distribution (Oranges color scheme)
  - Tokens per Request Distribution (Blues color scheme)
  - Cost per Request Distribution (Greens color scheme)
- Update docker-compose image to v1.4.1
- Feat: configurable memory sync with external config (v1.5.0) ([#13](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/13))
- Add custom exclude patterns support in config file
- Implement anti-loop pattern detection (16 built-in patterns)
- Consolidate sync into single SessionStart hook (remove realtime hook)
- Add sync status reporting with getSyncStatus()
- Update install.ts to copy config to ~/.claude/config/
- Add production Docker Compose for remote deployment
- Update INSTALL.md and VERIFY.md with AI-friendly summaries
- Add AI agent issue tracking and RCA instructions
- Align documentation with Constitution Principle VIII
sync-memory-to-knowledge.ts). Users upgrading should remove Stop and
SubagentStop hook registrations from settings.json.
instead of source pack at src/skills/. This ensures verification checks
the actual installation rather than just the pack contents.
- All src/skills/* refs → ~/.claude/skills/Knowledge/*
- All src/hooks/* refs → ~/.claude/hooks/*
- Added PAI_SKILLS variable for consistent path references
- Updated failure actions with correct installed paths
Streamable HTTP transport requiring session management. The
knowledge-cli.ts handles sessions internally.
- Old: Raw curl to /mcp/ endpoint (fails with "Missing session ID")
- New: knowledge-cli.ts commands that handle sessions
- 5.1: add_episode command replaces curl add_memory
- 5.2: search_nodes command replaces curl search_memory_nodes
- 5.3: search_facts command replaces curl search_memory_facts
- 5.4: get_episodes command replaces curl get_episodes
- Added note about Streamable HTTP transport
version matches the installed pack version. Prevents running outdated
MCP server code after pack upgrades.
- Gets installed version from SKILL.md frontmatter
- Gets running image version from container
- Compares versions and FAILs if mismatch
- Provides fix instructions (pull new image, restart)
- spec.md: Feature specification
- plan.md: Implementation plan
- tasks.md: Task breakdown
- research.md: Research notes
- data-model.md: Data model design
- quickstart.md: Quick start guide
- checklists/: Requirements checklist
- contracts/: API contracts
- Add LOG_LEVEL=DEBUG to development compose files
- Fix all workflow files to use absolute path for knowledge-cli.ts
  (~/.claude/skills/Knowledge/tools/knowledge-cli.ts)
- Workflows now work when skill is installed, not just from source
- Prefix unused parseEnvPatterns function with underscore in sync-config.ts


### Fixed


- Correct icon path in README
- Fix(ci): discard local CHANGELOG.md changes before branch switch
Need to discard these before switching to main branch.

## [1.4.1] - 2026-01-27


### Fixed


- Fix: use PROMPT_CACHE_ENABLED env var for cache metrics
but containers receive the prefix-stripped version PROMPT_CACHE_ENABLED.
- Add prompt cache config to KnowledgeConfig interface
- Add MADEINOZ_KNOWLEDGE_PROMPT_CACHE_* to env var mapping
- Pass PROMPT_CACHE_* vars to container env file
- Fix: standardize env var names in all patches (no prefix)
- PROMPT_CACHE_ENABLED (not MADEINOZ_KNOWLEDGE_PROMPT_CACHE_ENABLED)
- PROMPT_CACHE_METRICS_ENABLED
- PROMPT_CACHE_LOG_REQUESTS
- PROMPT_CACHE_TTL
- METRICS_PORT

## [1.4.0] - 2026-01-27


### Added


- Feat: Gemini prompt caching with monitoring stack [006] ([#12](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/12))
- Establishes strict directory boundaries: Python in docker/, TypeScript in src/
- Update tasks-template.md Path Conventions to reference new principle
- Rationale: Codifies practice from feature 006 integration test placement
cache_control markers and cost reporting.
- Add OpenTelemetry/Prometheus dependencies for metrics
- Add 4 environment variables for caching configuration
- Update Dockerfile to install cache requirements
- Add .dockerignore for Python artifacts
- Implement CacheMetrics dataclass with OpenRouter response parsing
- Implement PricingTier for cost calculations (~50% cache discount)
- Implement SessionMetrics for cumulative statistics
- Implement OpenTelemetry meter provider and Prometheus exporter
- Implement message_formatter.py (multipart format + cache_control markers)
- Implement caching_wrapper.py (monkey-patch OpenAI client)
- Integrate wrapper into factories.py for all OpenAI-compatible clients
- Initialize metrics exporter at server startup
- Integration tests for cache hits, misses, multipart format
- Located in docker/tests/integration/ per Constitution Principle VII
- Tests validate 40%+ cost reduction on cache hits (SC-001)
Repeated queries with same system prompt show token cost reduction.
- Add histogram metrics for per-request token and cost distributions
- Custom bucket boundaries for micro-dollar costs ($0.000005-$5.00)
- Custom bucket boundaries for token counts (10-200,000)
- Fix cache_enabled gauge to read actual env var
- Change debug logging to DEBUG level (configurable)
- Document OpenRouter /responses endpoint multipart limitation
- Analyze 3 resolution paths (all non-viable for immediate fix)
- Recommend monitoring OpenRouter quarterly for API updates
- Document native Gemini API migration as long-term option
- Add comprehensive metrics.md reference (all metrics, PromQL examples)
- Add resolution-research.md with full technical analysis
- Update spec.md status to reflect blocked state
Metrics collection works for all LLM requests regardless.
- Update mkdocs.yml nav to include new page
- Add metrics env vars section to configuration.md
- Include PromQL examples, histogram explanations, architecture diagram
/chat/completions endpoint. This endpoint supports both multipart
format (for cache_control markers) AND json_schema response format.
- Add _is_gemini_model() helper to detect Gemini models
- Route Gemini+OpenRouter → OpenAIGenericClient (/chat/completions)
- Keep other cloud providers → OpenAIClient (/responses)
- Fix is_reasoning_model undefined variable bug
- Fix caching default to "false" (matches documentation)
* feat: add metrics enhancements and dual-audience documentation [006]
- Add LLM request duration histogram (graphiti_llm_request_duration_seconds)
- Add error counter with type labels (rate_limit, timeout, exception)
- Add cache write tokens counter for tracking cache creation
- Wire timing and error tracking into caching_wrapper.py
- Add AI-friendly summaries in HTML comments for AI context loading
- Add Limits & Constraints quick reference tables
- Add System Limits Summary section to configuration.md
- Add comprehensive prompt caching documentation to observability.md
- Update metrics documentation with duration, errors, throughput sections
- Add Principle VIII: Dual-Audience Documentation
- Require AI-friendly metadata, structured tables, quick reference cards
- Update Documentation Updates workflow to reference new principle
- Grafana with auto-provisioned datasource and dashboard
- 23-panel dashboard covering tokens, costs, cache, duration, errors
- Dev environments have monitoring enabled by default
- Production uses Docker Compose profiles (--profile monitoring)
- Dev: Grafana 3002 (Neo4j) / 3003 (FalkorDB), Prometheus 9092
- Prod: Grafana 3001 (Neo4j) / 3002 (FalkorDB), Prometheus 9092
- config/monitoring/prometheus/prometheus.yml
- config/monitoring/grafana/provisioning/datasources/prometheus.yml
- config/monitoring/grafana/provisioning/dashboards/dashboards.yml
- config/monitoring/grafana/provisioning/dashboards/madeinoz-knowledge.json
  Principle VIII (Dual-Audience Documentation):
  - AI-friendly summary in HTML comment
  - Tables for ports, credentials, metrics
  - Quick reference section
  - Code blocks with language identifiers
  - grafana-login.png: Login page
  - grafana-dashboard-overview.png: Dashboard with live metrics
  - prometheus-targets.png: Target health verification
- Include AI-friendly summary for LLM context loading
- Document architecture, data models, and Prometheus metrics
- Move screenshots to docs/assets/images/ (MkDocs requirement)
- Add cache implementation page to mkdocs nav
- Link from observability docs to implementation guide
- Bump version to 1.3.2
* chore: sync version 1.3.2 in README.md and SKILL.md
to satisfy CodeQL security scan.
evil-domain.com from matching. The leading dot ensures only actual
subdomains match.


### Fixed


- Fix: release workflow checkout main before pushing CHANGELOG
commit but tried to push to main. Now saves CHANGELOG.md, checks out
main, restores and commits, then returns to tag for build steps.

## [1.3.0] - 2026-01-26


### Added


- Feat: add temporal search with date filtering (v1.3.0) ([#9](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/9))
and versioned releases with comprehensive documentation.
- GitHub Actions workflow for automated Docker builds
  - Multi-platform support (linux/amd64, linux/arm64)
  - Auto-publish to GitHub Container Registry (ghcr.io)
  - Optional Docker Hub publishing (if secrets configured)
  - Image testing before publish
  - Auto-tagging with semver, latest, fixed, and sha
- Release workflow for version management
  - Manual dispatch with version validation
  - Automatic changelog generation from commits
  - GitHub Release creation with notes
  - Triggers Docker build via tag push
- Developer documentation
  - Custom image rationale and migration path
  - Environment prefix workaround explanation
  - Patch details (async bug, Ollama support, search-all-groups)
- Release process documentation
  - Step-by-step release guide
  - Version numbering (SemVer) guidelines
  - Rollback procedures
  - Troubleshooting section
- Fix Neo4j password typo in docker-compose-neo4j.yml (madeinojknowledge → madeinozknowledge)
- Remove volume mount conflict in run.ts (custom image has configs baked in)
- Update container.ts to reference custom image (madeinoz-knowledge-system:fixed)
- Add release badges to README.md
- Add Quick Start with Docker section
- Add Developer Notes to reference docs
- Add Release Process to reference docs
- Update mkdocs.yml navigation
- GitHub Actions CI/CD pipeline for automated builds and releases
- Developer and release process documentation
- Bug fixes (Neo4j password, volume mount, async iteration, network alias)
- Custom Docker image with baked-in patches
- Neo4j backend end-to-end verification
- README updates with badges and quick start
- Add author info (Stephen Eaton / madeinoz67)
- Add JSON schema reference for IDE support
- Establishes tsconfig.json as central version source of truth
- Add bun scripts for build, test, start, stop, status, logs
- Install bun-types and typescript as devDependencies
- Remove version/author from tsconfig.json (keep $schema)
- Update bun.lock for reproducible installs
  - Biome linter with TypeScript strict mode
  - Trivy vulnerability scanner
  - TruffleHog secret detection
  - Auto-update CHANGELOG.md on main branch pushes
  - Version bumping in Dockerfile and package.json
  - git-cliff changelog generation
  - Docker build and push to GHCR (amd64/arm64)
  - MkDocs documentation build and GitHub Pages deploy
  - GitHub Release creation with release notes
  - docs.yml (merged into release.yml)
  - docker-build.yml (merged into release.yml)
  - biome.json: Linter/formatter configuration
  - cliff.toml: Changelog generation rules
  - noExcessiveCognitiveComplexity: off
  - noForEach: off
  - noStaticOnlyClass: off
  - noNonNullAssertion: off
  - noExplicitAny: off
  - Add type annotations for implicit any (knowledge-client.ts)
  - Replace banned {} type with Record<string, never> (mcp-client.ts)
  - Add missing break in switch statement (logs.ts)
  - Remove unused variables and imports across test files
  - Fix noAccumulatingSpread in tests/setup.ts
  - Expect "88%" instead of "0.88" for confidence display
  - Expect "No facts found" instead of "No relationships found"
  - Use proper save/restore pattern for process.env vars
  - Delete MADEINOZ_KNOWLEDGE_DATABASE_TYPE before setting DATABASE_TYPE
  - Ensures FalkorDB mode is correctly detected during tests
server.ts that provides subcommands: start, stop, restart, status, logs.
- Update package.json with npm scripts for all subcommands
- Update SKILL.md documentation with new usage
- Update run.ts management command hints
  start     - Start containers
  stop      - Stop containers
  restart   - Restart containers
  status    - Show status and health
  logs      - View container logs (--mcp, --db, --tail, --no-follow)
- Add generateEnvFiles() function that creates /tmp/madeinoz-knowledge-*.env
  files automatically from PAI config before starting containers
- This makes server-cli.ts fully self-contained, eliminating the need
  for start.sh to be run separately
- Update compose file comments to note 'bun run server start' is preferred
- Update SKILL.md references to use server-cli.ts
are now redundant - server-cli.ts handles env file generation internally.
- Rename npm script from "server" to "server-cli" for consistency
- Fix build/dev scripts that referenced deleted run.ts
- Update 16 documentation files to use bun run server-cli commands
- Update server-cli.ts help message with correct command pattern
- bun run server start → bun run server-cli start
- bun run server stop → bun run server-cli stop
- bun run server status → bun run server-cli status
- bun run server logs → bun run server-cli logs
- bun run server restart → bun run server-cli restart
distinct ports, volumes, and container names. This fixes getComposeFilePath()
which previously ignored databaseType when devMode=true.
- FalkorDB dev: 3001 (UI), 8001 (MCP)
- Neo4j dev: 7475 (Browser), 7688 (Bolt), 8001 (MCP)
- Rename docker-compose-dev.yml to docker-compose-neo4j-dev.yml
- Add docker-compose-falkordb-dev.yml with dev configuration
- Update COMPOSE_FILES with neo4jDev and falkordbDev keys
- Fix getComposeFilePath() to use databaseType for dev files
- Fix server-cli.ts to display correct FalkorDB dev port (3001)
organization as a PAI pack component. This consolidates:
- Container management (compose files, podman support)
- MCP server tooling (diagnose, install, knowledge CLI)
- Configuration and patches
- Test utilities for LLM/embedding providers
- Add env-generation.test.ts for config loader testing
- Remove lucene.test.ts (functionality moved to Python patch)
- Update Dockerfile for new server path
- Expand configuration.md documentation
- Update tsconfig.json paths
- Dockerfile (with updated paths for new structure)
- build-image.ts (builds from project root)
- docker-compose files for Neo4j/FalkorDB
- patches/ with Graphiti monkey-patches
- Add WORK/ to .gitignore (working notes directory)
- Remove VERSION file (version in Dockerfile labels)
- Update imports in server-cli.ts, build-image.ts, and test files
- Remove duplicate src/skills/server/lib/ directory
- Slim README from 1,375 to 179 lines with links to docs
- Fix tsconfig.json invalid options (allowUnusedLocals -> noUnusedLocals)
- Update CI workflow to use ESLint
- Add lenient rules for test files
- Add Docker image build to build job (validation only)
- Add MkDocs documentation build to build job
- Release job: push Docker to GHCR, deploy docs to Pages
- Fix Dockerfile path: ./Dockerfile → ./docker/Dockerfile
- Add DEV_STATUS.md for developer handoff
- Add bun-test.d.ts for Bun test globals (describe, it, expect)
- Fix import paths in diagnose.ts, install.ts, knowledge.ts
- Fix async/await issues: envExists() now async, await file.exists()
- Fix type casts in mcp-client.ts (use as unknown as Record)
- Fix ExecOptions: quiet -> silent
- Update ESLint config for test files (project: null)
- Simplify release job: changelog + build + Docker + GitHub Release
- Remove documentation deployment from release job
- Remove pages/id-token permissions
- Remove release notes append step
1. Generate changelog
2. Update CHANGELOG.md
3. Commit CHANGELOG.md
4. Build (TypeScript)
5. Build and push Docker image
6. Create GitHub Release
- Security runs in parallel (no dependencies)
- Test depends on lint only
- Build depends on lint + security
- Fix embedder provider configuration to be independent from LLM provider
- Previously when LLM_PROVIDER=ollama, EMBEDDER_PROVIDER was forced to 'openai'
- Now respects user's EMBEDDER_PROVIDER setting (ollama, openai, etc.)
- Update config.ts, YAML configs, Python factories, docker-compose, patch files
- Update SKILL.md: add trigger keywords, Bash wrapper tools, model recommendations
- Add variable mapping reference table to .env.example
- Update workflow files with new variable references
- Update Install.md and install.ts
- Update all references in SKILL.md, workflow files, and documentation
- Update help text and usage examples in the CLI
- Update INSTALL.md and developer-notes.md references
Now they correctly replace the original files at build time:
- factories.py → /app/mcp/src/services/factories.py (Ollama support)
- graphiti_mcp_server.py → /app/mcp/src/graphiti_mcp_server.py (search all groups)
- falkordb_lucene.py → /app/mcp/src/utils/falkordb_lucene.py (Lucene sanitization)
all FastMCP versions. Now gracefully degrades with a warning instead
of crashing the server on startup.
for filtering results by creation date. Supports both ISO 8601 dates
(2026-01-26) and relative formats (today, yesterday, 7d, 1w, 1m).
- Python MCP server: add parse_date_input() helper and temporal
  filtering in search_nodes/search_memory_facts functions
- TypeScript MCP client: add since/until params to search interfaces
- Knowledge CLI: add --since/--until flag parsing with help examples
- New SearchByDate.md workflow for temporal queries
- Updated SearchKnowledge.md and SearchFacts.md with temporal examples
- Added SearchByDate to SKILL.md workflow routing table
- Fix all src/ paths to use installed skill paths (tools/, workflows/)
- Add SearchByDate workflow to documentation
- Update CLI reference with date format table and examples
- Fix memory sync hook paths throughout docs
- Update quick-reference with correct directory structure
- Added --since/--until date filtering flags
- New SearchByDate workflow
- Documentation updates with fixed paths


### Fixed


- Fix: implement dual MCP protocol support for Neo4j and FalkorDB sync hooks
  JSON-RPC 2.0, FalkorDB uses SSE GET to /sse endpoint
- Add database type detection via MADEINOZ_KNOWLEDGE_DB environment variable
  (neo4j or falkorodb, defaults to neo4j)
- Add session management for Neo4j with Mcp-Session-Id header extraction
- Implement conditional Lucene query sanitization for FalkorDB only
- Add SSE response body parsing to extract data: lines with JSON
- Implement exponential backoff retry logic for transient failures
- Add comprehensive documentation in specs/003-fix-issue-2/
- Update docs/concepts/hooks-integration.md with protocol details
- Update CHANGELOG.md with v1.2.5 entry

## [1.2.5] - 2026-01-19


### Added


- Madeinoz-knowledge-system v1.2.5


### Fixed


- Fix: rename INDEX.md to index.md for case-sensitive filesystems
references index.md but the file was INDEX.md, causing build failure.


