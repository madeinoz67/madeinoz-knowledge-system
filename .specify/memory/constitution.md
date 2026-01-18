<!--
SYNC IMPACT REPORT
==================
Version Change: 0.0.0 → 1.0.0 (MAJOR - Initial constitution ratification)

Modified Principles:
- [NEW] I. Container-First Architecture
- [NEW] II. Graph-Centric Design
- [NEW] III. Zero-Friction Knowledge Capture
- [NEW] IV. Query Resilience
- [NEW] V. Graceful Degradation

Added Sections:
- Core Principles (5 principles)
- Technical Constraints
- Development Workflow
- Governance

Removed Sections:
- None (initial version)

Templates Requiring Updates:
- .specify/templates/plan-template.md ✅ (no changes needed - Constitution Check section is generic)
- .specify/templates/spec-template.md ✅ (no changes needed - requirements structure compatible)
- .specify/templates/tasks-template.md ✅ (no changes needed - phase structure aligns)
- .specify/templates/checklist-template.md ✅ (no changes needed - generic structure)
- .specify/templates/agent-file-template.md ✅ (no changes needed - generic structure)

Follow-up TODOs:
- None - all placeholders resolved
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
- Unit tests via `bun test`
- Integration tests require running containers
- All tests MUST pass before merge to master

## Development Workflow

**Code Changes:**
1. Create feature branch from master
2. Implement changes following Constitution principles
3. Run `bun run typecheck` - MUST pass with no errors
4. Run `bun test` - all tests MUST pass
5. Update documentation if user-facing behavior changes
6. Create PR with clear description of changes

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

**Version**: 1.0.0 | **Ratified**: 2026-01-18 | **Last Amended**: 2026-01-18
