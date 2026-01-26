# Implementation Plan: Documentation and Docker Compose Updates

**Branch**: `001-docs-compose-updates` | **Date**: 2026-01-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-docs-compose-updates/spec.md`

## Summary

Remove obsolete Lucene-specific documentation content, improve benchmark documentation organization with LLM model recommendations, and update all Docker/Podman Compose files to reference ghcr.io/madeinoz67/madeinoz-knowledge-system:latest container image. This is a documentation and configuration update with no code changes to core functionality.

## Technical Context

**Language/Version**: Markdown (documentation), YAML (Docker/Podman Compose v2.x)
**Primary Dependencies**: Docker Compose v2.x or Podman Compose
**Storage**: N/A (documentation and configuration files only)
**Testing**: Manual verification via documentation review and container deployment tests
**Target Platform**: Linux/macOS/Windows with Docker or Podman
**Project Type**: Documentation and configuration updates (no source code changes)
**Performance Goals**: N/A (documentation updates only)
**Constraints**: No functional code changes; maintain accuracy while simplifying content
**Scale/Scope**: ~10-15 documentation files, 4 compose files, multiple scripts

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Container-First Architecture
**Status**: ✅ PASS

**Rationale**: This feature UPDATES container orchestration files to use correct image references from GitHub Container Registry. No changes to container orchestration architecture, health checks, or volume management. Complies with container-first principle.

### Principle II: Graph-Centric Design
**Status**: ✅ PASS

**Rationale**: Documentation updates only. No changes to knowledge graph operations, entity storage, or API design. Complies with graph-centric principle.

### Principle III: Zero-Friction Knowledge Capture
**Status**: ✅ PASS

**Rationale**: Documentation updates only. No changes to entity extraction, LLM automation, or natural language triggers. Complies with zero-friction principle.

### Principle IV: Query Resilience
**Status**: ✅ PASS

**Rationale**: While removing Lucene documentation references, the underlying query sanitization implementation in `lucene.ts` remains unchanged. Documentation will be simplified to remove implementation details that confuse users. Query handling functionality is preserved.

**Note**: Removing Lucene documentation is a SIMPLIFICATION, not a functional change. The `lucene.ts` library still handles special character escaping internally - we're just removing confusing documentation about backend-specific internals.

### Principle V: Graceful Degradation
**Status**: ✅ PASS

**Rationale**: Documentation updates only. No changes to error handling, retry logic, or graceful failure modes. Complies with graceful degradation principle.

### Principle VI: Codanna-First Development
**Status**: ✅ PASS

**Rationale**: This principle applies to CODEBASE EXPLORATION and DOCUMENTATION SEARCHES during development. This feature IS a documentation update, not code exploration. We will use `codanna mcp search_documents` to find existing Lucene references before removing them. Complies with Codanna-first principle.

**Constitution Check Result**: ✅ ALL PASS - No violations to justify

## Project Structure

### Documentation (this feature)

```text
specs/001-docs-compose-updates/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # N/A - no data model changes needed
├── quickstart.md        # N/A - no new functionality
├── contracts/           # N/A - no API contracts
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── server/
│   ├── docker-compose-neo4j.yml         # UPDATE: image reference
│   ├── docker-compose-falkordb.yml       # UPDATE: image reference
│   ├── podman-compose-neo4j.yml          # UPDATE: image reference
│   └── podman-compose-falkordb.yml        # UPDATE: image reference
└── (no code changes - lucene.ts implementation unchanged)

docs/                          # UPDATE: remove Lucene references, improve benchmarks
├── (various .md files)        # REVIEW: all files for Lucene content
└── (benchmark sections)       # REORGANIZE: structure + add LLM recommendations

.                              # REVIEW: root-level documentation files
├── README.md                  # UPDATE: remove Lucene, improve benchmarks
├── CLAUDE.md                  # UPDATE: remove Lucene references
├── INSTALL.md                 # REVIEW: for Lucene content
└── (other docs)               # REVIEW: all documentation

scripts/                      # REVIEW: for image references
└── (*.sh scripts)            # UPDATE: ghcr.io references if found
```

**Structure Decision**: Single project structure (repository root). This is a documentation and configuration update affecting files across the repository structure. No new directories or modules added.

## Complexity Tracking

> **No Constitution violations - this section intentionally left blank**

All updates are straightforward:
- Documentation text removal (Lucene references)
- Documentation reorganization (benchmark sections)
- String replacements (image references)

No new complexity introduced. Simplification of documentation reduces cognitive load for users.

