<!--
SYNC IMPACT REPORT
==================
Version Change: 1.1.1 → 1.2.0 (MINOR - New principle added)

Modified Principles:
- [UNCHANGED] I. Container-First Architecture
- [UNCHANGED] II. Graph-Centric Design
- [UNCHANGED] III. Zero-Friction Knowledge Capture
- [UNCHANGED] IV. Query Resilience
- [UNCHANGED] V. Graceful Degradation
- [UNCHANGED] VI. Codanna-First Development

Added Sections:
- [NEW] VII. Language Separation - Establishes strict directory boundaries between Python (docker/) and TypeScript (src/) code

Removed Sections:
- None

Templates Requiring Updates:
- .specify/templates/plan-template.md ✅ (no changes needed - Constitution Check is generic)
- .specify/templates/spec-template.md ✅ (no changes needed - requirements structure compatible)
- .specify/templates/tasks-template.md ⚠ (UPDATED - Path Conventions section amended to reference project-specific language separation)
- .specify/templates/checklist-template.md ✅ (no changes needed - generic structure)
- .specify/templates/agent-file-template.md ✅ (no changes needed - generic structure)

Follow-up TODOs:
- None - new principle codifies existing practice from feature 006 integration test placement
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
6. Update documentation if user-facing behavior changes
7. Create PR with clear description of changes

**Container Changes:**
1. Test locally with `bun run start` / `bun run stop`
2. Verify health checks pass via `bun run status`
3. Check logs for errors via `bun run logs`
4. Document any new environment variables required

**Documentation Updates:**
- README.md: User-facing features and installation
- INSTALL.md: Step-by-step installation guide
- VERIFY.md: Post-installation verification steps
- docs/: Detailed usage and troubleshooting
- Use `codanna mcp search_documents` to find related documentation before making changes

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

**Version**: 1.2.0 | **Ratified**: 2026-01-18 | **Last Amended**: 2026-01-27
