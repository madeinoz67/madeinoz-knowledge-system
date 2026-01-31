<!--
SYNC IMPACT REPORT
==================
Version Change: 1.3.0 → 1.4.0 (MINOR - New principle added)

Modified Principles:
- [UNCHANGED] I. Container-First Architecture
- [UNCHANGED] II. Graph-Centric Design
- [UNCHANGED] III. Zero-Friction Knowledge Capture
- [UNCHANGED] IV. Query Resilience
- [UNCHANGED] V. Graceful Degradation
- [UNCHANGED] VI. Codanna-First Development
- [UNCHANGED] VII. Language Separation
- [UNCHANGED] VIII. Dual-Audience Documentation

Added Sections:
- [NEW] IX. Observability & Metrics - Establishes requirements for metrics documentation, dashboard coverage, and restart gap handling using time-over-time functions

Removed Sections:
- None

Templates Requiring Updates:
- .specify/templates/plan-template.md ⚠ (add metrics/dashboard check to Constitution Check)
- .specify/templates/spec-template.md ⚠ (add metrics/dashboard requirements for features exposing new metrics)
- .specify/templates/tasks-template.md ✅ (observability task category exists)
- .specify/templates/checklist-template.md ✅ (generic structure)
- .specify/templates/agent-file-template.md ✅ (generic structure)

Follow-up TODOs:
- Update plan-template.md Constitution Check to include metrics/dashboard coverage validation
- Update spec-template.md to require metrics documentation for features exposing new data
-->

# Madeinoz Knowledge System Constitution

## Core Principles

### I. Container-First Architecture

All services MUST run in containers (Podman or Docker) for isolation, reproducibility, and portability. The knowledge system consists of:

- **MCP Server Container**: Graphiti-based knowledge graph server
- **Database Container**: Neo4j (default) or FalkorDB backend

**Non-Negotiable Rules:**
- Container orchestration via docker-compose or podman-compose
- Network isolation via dedicated bridge network (`madeinoz-knowledge-net`)
- Health checks MUST be implemented for all containers
- Persistent volumes MUST be used for database storage to prevent data loss

**Rationale:** Container isolation prevents dependency conflicts, enables consistent deployment across environments, and simplifies installation for end users.

### II. Graph-Centric Design

Knowledge MUST be stored as a graph of entities and relationships, not as flat documents or key-value pairs.

**Non-Negotiable Rules:**
- All knowledge operations MUST go through the Graphiti knowledge graph API
- Entities MUST have typed relationships (causal, dependency, temporal, semantic)
- Vector embeddings MUST be maintained for semantic search capability
- Temporal metadata MUST be preserved for all episodes

**Rationale:** Graph structure enables relationship discovery, semantic search, and temporal tracking that flat storage cannot provide.

### III. Zero-Friction Knowledge Capture

Knowledge capture MUST be conversational and automatic, requiring no manual organization from users.

**Non-Negotiable Rules:**
- Entity extraction MUST be performed automatically by the LLM
- Users MUST NOT be required to tag, categorize, or link knowledge manually
- Natural language triggers ("remember this", "store this") MUST activate capture
- Failed captures MUST provide clear troubleshooting guidance

**Rationale:** Manual organization creates friction that prevents consistent knowledge capture. Automation ensures the knowledge graph grows naturally with usage.

### IV. Query Resilience

All query operations MUST handle edge cases gracefully, including special characters in identifiers.

**Non-Negotiable Rules:**
- FalkorDB queries MUST sanitize Lucene special characters: `+ - && || ! ( ) { } [ ] ^ " ~ * ? : \ /`
- Hyphenated identifiers (e.g., `apt-28`, `madeinoz-threat-intel`) MUST work without manual escaping
- Neo4j queries use native Cypher and do not require sanitization
- Query failures MUST return actionable error messages, not raw database errors

**Rationale:** CTI/OSINT data commonly uses hyphenated identifiers. Query failures due to special characters break user trust and data retrieval.

### V. Graceful Degradation

The system MUST fail gracefully when external dependencies are unavailable.

**Non-Negotiable Rules:**
- MCP server unavailability MUST NOT crash Claude Code sessions
- Memory sync hooks MUST exit gracefully when knowledge server is offline
- API rate limits MUST trigger automatic retry with exponential backoff
- Missing configuration MUST provide clear setup instructions, not cryptic errors

**Rationale:** External dependencies (LLM APIs, container runtime, databases) can fail. Users should continue working with degraded functionality rather than complete failure.

### VI. Codanna-First Development

All codebase exploration and documentation searches MUST use the Codanna CLI (invoked via Bash) before falling back to manual methods (grep, find, direct file reads).

**Non-Negotiable Rules:**
- Codanna CLI MUST be invoked via Bash tool, NOT via native MCP tools (`mcp__codanna__*`)
- Text output MUST be the default; JSON output only when programmatic parsing is required
- Semantic search MUST be the starting point for code exploration
- Line ranges from Codanna results MUST be used to read only relevant code sections
- Symbol IDs MUST be used to chain related queries efficiently

**CLI Command Reference:**

```bash
# Semantic search (start here)
codanna mcp semantic_search_with_context query:"your search" limit:5

# Document search (for README, docs, guides)
codanna mcp search_documents query:"installation guide" limit:5

# Symbol lookup
codanna mcp find_symbol <name>
codanna mcp search_symbols query:<term> limit:10

# Relationship analysis
codanna retrieve callers symbol_id:<ID>
codanna retrieve calls symbol_id:<ID>
codanna retrieve describe symbol_id:<ID>

# Impact analysis before modifying shared code
codanna mcp analyze_impact symbol_name:<name>
```

**Workflow Requirements:**
1. Start with `codanna mcp semantic_search_with_context` to map the landscape
2. Use symbol IDs from results to chain related queries
3. Read only the line ranges provided (saves tokens)
4. Follow relationships with `codanna retrieve callers/calls`
5. Refine searches based on findings

**Rationale:** The Codanna CLI provides concise text output that conserves context window tokens (3-5x more efficient than JSON). Native MCP tools return verbose JSON by default, consuming excessive context. Using CLI-first via Bash ensures consistent, token-efficient code intelligence operations.

### VII. Language Separation

Python and TypeScript code MUST be kept in separate directory trees and MUST NOT be mixed.

**Non-Negotiable Rules:**
- Python code (server, patches, utilities) MUST live in `docker/` directory
- TypeScript code (CLI, tools, client libraries) MUST live in `src/` directory
- Python tests MUST live in `docker/tests/` (unit and integration subdirectories)
- TypeScript tests MUST live in `tests/` at repository root
- NEVER create Python files in `src/` or TypeScript files in `docker/patches/`
- Build artifacts MUST respect language boundaries (Python: `docker/.venv`, `docker/__pycache__`; TypeScript: `dist/`, `node_modules/`)

**Directory Structure:**

```text
docker/                      # Python ecosystem
├── patches/                 # Python implementation code
│   ├── graphiti_mcp_server.py
│   ├── factories.py
│   ├── cache_metrics.py
│   └── ...
├── tests/                   # Python tests
│   ├── unit/               # Python unit tests
│   └── integration/        # Python integration tests
└── Dockerfile              # Python container definition

src/                         # TypeScript ecosystem
├── server/                 # TypeScript server code
│   ├── server-cli.ts
│   ├── install.ts
│   └── lib/
├── skills/                 # PAI skill definitions
└── hooks/                  # Session lifecycle hooks

tests/                       # TypeScript tests (if needed)
└── ...
```

**Rationale:** Mixing languages in the same directory tree creates confusion about runtime requirements, complicates build processes, and makes dependency management ambiguous. Clear separation enables language-specific tooling (Python virtual environments, TypeScript path aliases, linters) to operate independently without conflicts. This principle emerged from feature 006 where integration tests were initially placed in root `tests/` before being correctly relocated to `docker/tests/integration/`.

### VIII. Dual-Audience Documentation

All user-facing documentation MUST be optimized for both human readers and AI consumers (LLMs, agents, automated systems).

**Non-Negotiable Rules:**
- Documentation MUST include hidden AI-friendly summaries in HTML comments at the top of key pages
- Tables MUST be used for structured data (ports, metrics, configuration, limits) to enable machine parsing
- Quick reference sections MUST consolidate actionable information for rapid AI context loading
- Code blocks MUST include language identifiers for syntax highlighting and semantic parsing
- Section headings MUST be descriptive and hierarchical for navigation by both humans and AI

**AI-Friendly Summary Format:**

```markdown
<!-- AI-FRIENDLY SUMMARY
System: [System name]
Purpose: [One-line description]
Key Components: [Comma-separated list]

Key Tools/Commands:
- [tool_name]: [brief description]
- [tool_name]: [brief description]

Configuration Prefix: [PREFIX_*]
Default Ports: [port] ([service]), [port] ([service])

Limits:
- [Limit name]: [value] ([notes])
-->
```

**Quick Reference Card Requirements:**
- MUST appear near the end of main documentation pages
- MUST use tables for all structured data
- MUST include: tools/commands, environment variables, ports, metrics, limits
- MUST be scannable in under 30 seconds by both humans and AI

**Table Formatting Standards:**

| Element | Human Benefit | AI Benefit |
|---------|---------------|------------|
| Tables | Visual scanning | Structured extraction |
| Code blocks | Syntax highlighting | Language detection |
| Hidden comments | None (invisible) | Context loading |
| Headings | Navigation | Section parsing |
| Lists | Readability | Enumeration |

**Documentation Structure:**

```text
docs/
├── index.md                 # MUST include AI-friendly summary + Quick Reference Card
├── getting-started/
│   ├── overview.md          # Human-friendly introduction
│   └── quick-reference.md   # Command/trigger reference tables
├── reference/
│   ├── configuration.md     # MUST include System Limits Summary table
│   └── observability.md     # MUST include metrics tables
└── [topic]/
    └── *.md                 # Follow dual-audience patterns
```

**Rationale:** Modern AI assistants consume documentation to help users. Documentation that only serves human readers forces AI to guess, hallucinate, or ask clarifying questions. Hidden metadata enables AI to quickly load context without cluttering the human reading experience. Structured tables enable both humans to scan and AI to parse accurately. This principle emerged from feature 006 documentation updates where AI-friendly summaries and limits tables significantly improved assistant comprehension.

### IX. Observability & Metrics

All metrics MUST be documented and visualized in dashboards. Dashboard queries MUST handle service restart gaps to prevent data discontinuity.

**Non-Negotiable Rules:**
- ALL new metrics MUST be documented in `docs/reference/observability.md`
- ALL new metrics MUST have a corresponding dashboard panel or visualization
- Cumulative counter metrics MUST use time-over-time functions (`max_over_time()`, `min_over_time()`) to survive service restarts
- Dashboard queries MUST NOT break when counters reset to zero after restart
- Metrics MUST follow naming conventions: `<domain>_<metric>_<unit>_total` for counters, `<domain>_<metric>` for gauges

**Metric Documentation Requirements:**
When adding a new metric, update `docs/reference/observability.md` with:
| Field | Description |
|-------|-------------|
| Metric Name | Full metric name as exposed to Prometheus |
| Type | Counter, Gauge, Histogram |
| Labels | Label names and possible values |
| Description | What the metric measures and why it matters |
| Dashboard | Which dashboard panel visualizes this metric |

**Dashboard Query Requirements:**
For cumulative metrics that reset on restart, wrap with time-over-time functions:

```promql
# WRONG - shows gap on restart
graphiti_cache_hits_all_models_total

# CORRECT - shows last value during restart gap
max_over_time(graphiti_cache_hits_all_models_total[1h])
```

**Time-over-Time Function Selection:**
| Use Case | Function | Window |
|----------|--------|--------|
| Cumulative counters (preserve last value) | `max_over_time()` | 1h-24h |
| Rate calculations (survive restart) | `max_over_time(rate()[5m])[1h])` | 1h |
| Gauges (show minimum during gap) | `min_over_time()` | 5m-15m |
| Availability (any data in window) | `present_over_time()` | 5m |

**Dashboard Coverage Requirements:**
When adding new metrics, verify:
- [ ] Metric documented in `docs/reference/observability.md`
- [ ] Dashboard panel created or updated
- [ ] Query uses time-over-time functions if metric is cumulative
- [ ] Panel handles zero-values gracefully (displays "0" or "No data", not errors)
- [ ] Panel title and description explain what the metric means

**Rationale:** Metrics without documentation or dashboards are "dark matter" - they exist but provide no value. Service restarts cause cumulative counters to reset, creating visual "cliffs" in dashboards. Time-over-time functions preserve the last known value during restart gaps, maintaining data continuity for observability. This principle emerged from issue #39 and the RedTeam analysis that identified 43% of collected metrics had no dashboard coverage.

## Technical Constraints

**Runtime Environment:**
- Bun as TypeScript runtime (ES modules, strict mode)
- Podman or Docker for container orchestration
- Neo4j (default) or FalkorDB as graph database

**API Dependencies:**
- OpenAI API (or compatible: Anthropic, Google, Groq via OpenRouter)
- Graphiti MCP protocol over SSE transport

**Configuration:**
- Environment variables prefixed with `MADEINOZ_KNOWLEDGE_*`
- PAI config location: `$PAI_DIR/.env` or `~/.claude/.env`
- Per-installation config via `.env` files (never committed)

**Testing Requirements:**
- Unit tests via `bun test` (TypeScript) or `pytest` (Python)
- Integration tests require running containers
- All tests MUST pass before merge to master

## Development Workflow

**Code Changes:**
1. Create feature branch from master
2. Use Codanna CLI to explore existing codebase and understand context (Principle VI)
3. Implement changes following Constitution principles, respecting language separation (Principle VII)
4. Run `bun run typecheck` - MUST pass with no errors
5. Run `bun test` (TypeScript) and/or `pytest docker/tests` (Python) - all tests MUST pass
6. Update documentation if user-facing behavior changes (following Principle VIII)
7. If adding metrics, update observability docs and dashboards (following Principle IX)
8. Create PR with clear description of changes

**Container Changes:**
1. Test locally with `bun run server-cli start` / `bun run server-cli stop`
2. Verify health checks pass via `bun run server-cli status`
3. Check logs for errors via `bun run server-cli logs`
4. Document any new environment variables required

**Documentation Updates:**
- README.md: User-facing features and installation
- INSTALL.md: Step-by-step installation guide
- VERIFY.md: Post-installation verification steps
- docs/: Detailed usage and troubleshooting
- docs/reference/observability.md: Metrics documentation when adding new metrics
- Use `codanna mcp search_documents` to find related documentation before making changes
- Follow Principle VIII: Include AI-friendly summaries, use tables for structured data, add quick reference sections

## Governance

This Constitution supersedes all other practices in the Madeinoz Knowledge System repository.

**Amendment Process:**
1. Propose change via GitHub Issue with rationale
2. Document impact on existing functionality
3. Update Constitution version following SemVer:
   - MAJOR: Principle removal or incompatible redefinition
   - MINOR: New principle or material expansion
   - PATCH: Clarifications or typo fixes
4. Update dependent templates if Constitution Check criteria change
5. Merge only after review and approval

**Compliance Review:**
- All PRs MUST verify compliance with Constitution principles
- Constitution Check in plan-template.md MUST be evaluated for each feature
- Complexity additions MUST be justified in Complexity Tracking table
- Metrics additions MUST verify observability docs and dashboard coverage (Principle IX)

**Version**: 1.4.0 | **Ratified**: 2026-01-18 | **Last Amended**: 2026-01-31
