# Implementation Plan: LLM Client for Maintenance Classification

**Branch**: `011-maintenance-llm-client-fix` | **Date**: 2026-01-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/011-maintenance-llm-client-fix/spec.md`

## Summary

Fix Issue #21 - The maintenance service is not receiving the LLM client for importance/stability classification, causing all nodes to default to importance=3 instead of using the configured LLM model. The fix requires passing `client.llm_client` to `get_maintenance_service()` at 4 initialization points in `graphiti_mcp_server.py` and implementing immediate background classification after `add_memory()`.

## Technical Context

**Language/Version**: Python 3.11 (runs in container via Podman/Docker)
**Primary Dependencies**: FastMCP, graphiti-core, neo4j driver, pydantic
**Storage**: Neo4j graph database (default) or FalkorDB
**Testing**: pytest (unit and integration tests in `docker/tests/`)
**Target Platform**: Linux container (Docker/Podman)
**Project Type**: Single project (Python only - changes in `docker/patches/`)
**Performance Goals**: Classification within 30 seconds for 500 entities (maintenance mode), within 2 minutes for 100 entities (immediate mode)
**Constraints**: LLM API rate limits; must fall back to defaults (3, 3) when LLM unavailable
**Scale/Scope**: Small maintenance fix - ~20 lines changed across 2 files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Container-First Architecture | ✅ PASS | Python code lives in `docker/patches/`, container rebuilds required |
| II. Graph-Centric Design | ✅ PASS | Uses Graphiti knowledge graph API |
| III. Zero-Friction Knowledge Capture | ✅ PASS | Entity extraction remains automatic |
| IV. Query Resilience | N/A | No query changes in this feature |
| V. Graceful Degradation | ✅ PASS | FR-005, FR-007: Falls back to defaults when LLM unavailable |
| VI. Codanna-First Development | ✅ PASS | Used Codanna CLI for code exploration |
| VII. Language Separation | ✅ PASS | Python only, no TypeScript changes |
| VIII. Dual-Audience Documentation | ✅ PASS | Documentation updates for new classification behavior |

**Gate Status**: ✅ PASSED - No violations, all principles satisfied

## Project Structure

### Documentation (this feature)

```text
specs/011-maintenance-llm-client-fix/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
docker/patches/
├── graphiti_mcp_server.py         # Changes: 4 get_maintenance_service() calls + add_memory() immediate classification
├── importance_classifier.py       # No changes (already has correct logic)
├── maintenance_service.py         # No changes (already has correct logic)
└── tests/
    ├── unit/                     # Unit tests for classification logic
    └── integration/              # Integration tests with running Neo4j
```

**Structure Decision**: Single project (Python only). All changes are in `docker/patches/` directory, following Principle VII (Language Separation). No TypeScript changes required.

## Complexity Tracking

> **Not applicable** - No constitution violations to justify. This is a straightforward bug fix with minimal code changes.
