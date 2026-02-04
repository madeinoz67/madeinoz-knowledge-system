# Implementation Plan: Investigative Search with Connected Entities

**Branch**: `020-investigative-search` | **Date**: 2026-02-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/020-investigative-search/spec.md`

## Summary

This feature adds an `investigate` command that returns entities with their connected relationships and related entities in a single query. The implementation requires:
1. A new Python MCP tool (`investigate_entity`) for graph traversal with entity name resolution
2. TypeScript CLI command handler for the `investigate` command
3. MCP client method for server communication
4. Response formatter for AI-friendly JSON output
5. Comprehensive tests and documentation

The key technical challenge is efficient graph traversal with cycle detection, configurable depth (1-3 hops), and relationship type filtering while returning full entity names (not just UUIDs) in the response.

## Technical Context

**Language/Version**: Python 3.11+ (MCP server), TypeScript/Bun (CLI)
**Primary Dependencies**: FastMCP (Python), Graphiti Core (knowledge graph), mcp-client (TypeScript)
**Storage**: Neo4j (default) or FalkorDB with graph traversal support
**Testing**: pytest (Python), bun test (TypeScript)
**Target Platform**: Linux/macOS containers (Podman/Docker)
**Project Type**: Single project with language separation (docker/ for Python, src/ for TypeScript)
**Performance Goals**: Investigative search completes in under 2 seconds for entities with up to 100 direct connections
**Constraints**: Max depth 3 hops to prevent runaway queries, cycle detection required
**Scale/Scope**: Supports all custom entity types (Phone, Account, ThreatActor, Malware, etc.)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Container-First Architecture | ✅ PASS | MCP server runs in containers, existing infrastructure used |
| II. Graph-Centric Design | ✅ PASS | Uses Graphiti knowledge graph, relationships as first-class citizens |
| III. Zero-Friction Knowledge Capture | ✅ PASS | N/A - this is search/query feature, not capture |
| IV. Query Resilience | ✅ PASS | Inherits existing Lucene sanitization for FalkorDB |
| V. Graceful Degradation | ✅ PASS | Handles missing entities, empty connections, cycle detection |
| VI. Codanna-First Development | ✅ PASS | Used Codanna for research (semantic_search_with_context) |
| VII. Language Separation | ✅ PASS | Python code in docker/, TypeScript code in src/ |
| VIII. Dual-Audience Documentation | ✅ PASS | Will include AI-friendly summaries in docs |
| IX. Observability & Metrics | ⚠️ ACTION | Need to add metrics for investigate queries (latency, result count, depth) |

**Action Required**: Add investigate-specific metrics to observability docs and dashboard (Principle IX)

## Project Structure

### Documentation (this feature)

```text
specs/020-investigative-search/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── investigate-entity.yaml  # OpenAPI contract for investigate command
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Python (MCP Server)
docker/patches/
├── graphiti_mcp_server.py     # Add investigate_entity MCP tool
└── utils/
    └── graph_traversal.py      # NEW: Graph traversal utilities with cycle detection

# TypeScript (CLI)
src/skills/Knowledge/
├── tools/
│   └── knowledge-cli.ts        # Add investigate command handler
├── lib/
│   ├── mcp-client.ts           # Add investigateEntity() method
│   └── output-formatter.ts     # Add formatInvestigateEntity() formatter
└── SKILL.md                    # Update workflow routing

# Tests
docker/tests/integration/
└── test_investigate.py         # NEW: Integration tests for investigate tool

tests/unit/
└── skills/Knowledge/lib/
    └── output-formatter.test.ts  # Add tests for investigate formatter

# Documentation
docs/reference/
├── cli.md                       # Add investigate command documentation
└── observability.md             # Add investigate metrics documentation
```

**Structure Decision**: Single project structure with language separation (Constitution Principle VII). Python MCP server code in `docker/patches/`, TypeScript CLI code in `src/skills/Knowledge/`.

## Complexity Tracking

> **No complexity violations** - feature extends existing patterns without introducing new architectural complexity.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Phase 0: Research & Decisions

### Research Tasks

1. **Graph Traversal Patterns** (RESOLVED)
   - **Question**: How to perform efficient multi-hop graph traversal with cycle detection in Neo4j/FalkorDB?
   - **Decision**: Use Cypher variable-length paths for Neo4j, custom breadth-first traversal with visited set for FalkorDB
   - **Rationale**: Native Cypher paths are optimized; FalkorDB requires custom traversal due to limited path query support
   - **Alternatives Considered**: Recursive queries (rejected - depth limits), multiple round-trips (rejected - performance)

2. **Entity Name Resolution** (RESOLVED)
   - **Question**: How to include entity names in relationship responses without N+1 queries?
   - **Decision**: Return full entity objects (with name, type, UUID) inline in connections array
   - **Rationale**: Single query round-trip, matches Codanna's `analyze_impact` pattern
   - **Alternatives Considered**: UUID-only with client-side lookup (rejected - multiple queries), name-only (rejected - loses UUID)

3. **Cycle Detection Strategy** (RESOLVED)
   - **Question**: How to detect and handle cycles during graph traversal?
   - **Decision**: Track visited entities in a set, skip already-visited entities, report cycles in metadata
   - **Rationale**: Prevents infinite loops, provides visibility to users
   - **Alternatives Considered**: Depth-first with recursion limit (rejected - stack overflow), allow duplicates (rejected - messy output)

### Best Practices Research

1. **Graph Query Performance** (RESOLVED)
   - **Finding**: Limit result sets early, use index hints on entity names, apply relationship filters before traversal
   - **Decision**: Implement max_connections warning threshold (500), filter by relationship_type before traversal

2. **API Response Format** (RESOLVED)
   - **Finding**: Follow existing NodeResult/FactSearchResponse patterns from response_types.py
   - **Decision**: Create InvestigateResult response type with inline entity objects

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](./data-model.md) - Defines InvestigationResult, Connection, ConnectionGraph, and CycleMetadata entities.

### API Contracts

See [contracts/investigate-entity.yaml](./contracts/investigate-entity.yaml) - OpenAPI 3.0 specification for the investigate_entity MCP tool.

### Quickstart Guide

See [quickstart.md](./quickstart.md) - User-facing quickstart for investigative search workflows.

### Constitution Check (Re-evaluated)

| Principle | Status | Notes |
|-----------|--------|-------|
| IX. Observability & Metrics | ✅ PASS | Design includes metrics for investigate queries (latency, depth, cycles detected) |

**Result**: All gates passed. Proceed to implementation.

## Implementation Phases

### Phase 2: Implementation (covered by /speckit.tasks)

1. **Python MCP Server**
   - Add `investigate_entity` tool to graphiti_mcp_server.py
   - Create graph_traversal.py utilities with cycle detection
   - Add InvestigateResult response type to models/response_types.py
   - Implement metrics recording for investigate queries

2. **TypeScript CLI**
   - Add `investigate` command handler to knowledge-cli.ts
   - Add `investigateEntity()` method to mcp-client.ts
   - Add `formatInvestigateEntity()` formatter to output-formatter.ts
   - Update SKILL.md workflow routing

3. **Tests**
   - Integration tests for investigate_entity tool
   - Unit tests for graph traversal utilities
   - Unit tests for CLI formatter
   - End-to-end tests for complete workflow

4. **Documentation**
   - Update docs/reference/cli.md with investigate command
   - Add metrics to docs/reference/observability.md
   - Create OSINT/CTI workflow examples

### Phase 3: Verification (covered by /speckit.tasks)

- All tests pass (pytest + bun test)
- Manual testing with real OSINT/CTI data
- Performance validation (< 2s for 100 connections)
- Metrics visible in dashboard

## Dependencies

- Feature 019 (OSINT/CTI Ontology Support) - for custom entity type support
- Existing Graphiti MCP server infrastructure
- Existing knowledge CLI framework
- Existing metrics export infrastructure

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Graph traversal performance on dense graphs | High | Depth limit (3), connection count warning (500), relationship type filters |
| Cycle detection overhead | Medium | Efficient set-based tracking, skip cost acceptable for safety |
| FalkorDB vs Neo4j query differences | Medium | Abstract traversal logic into database driver layer |

## Success Criteria

From spec.md - all must pass:

- SC-001: Investigative search completes for entities with up to 100 direct connections in under 2 seconds
- SC-002: Users can retrieve entity connections without additional lookup queries
- SC-003: All custom entity types (Phone, Account, ThreatActor, etc.) are supported in investigative search
- SC-004: 100% of investigative search functionality is covered by automated tests
- SC-005: Documentation includes at least 3 complete OSINT/CTI workflow examples
- SC-006: CLI and MCP tools return identical results for the same investigate query
- SC-007: Queries with circular relationships complete successfully without hanging
