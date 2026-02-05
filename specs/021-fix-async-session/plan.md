# Implementation Plan: Fix AsyncSession Compatibility in Graph Traversal

**Branch**: `021-fix-async-session` | **Date**: 2026-02-05 | **Spec**: [spec.md](./spec.md)
**Related Issue**: https://github.com/madeinoz67/madeinoz-knowledge-system/issues/66

## Summary

The `investigate_entity` MCP tool (Feature 020) fails because `GraphTraversal._traverse_neo4j()` uses synchronous Neo4j session syntax (`with session:`) while the MCP server passes it an async driver. This fix converts the graph traversal methods to async/await patterns compatible with Neo4j's AsyncSession.

**Technical Approach**:
- Refactor `GraphTraversal` class methods to support async Neo4j sessions
- Use `async with driver.session() as session:` syntax for Neo4j
- Maintain backward compatibility with FalkorDB synchronous implementation
- Add async wrapper for MCP server integration

## Technical Context

**Language/Version**: Python 3.11+ (async/await required)
**Primary Dependencies**: neo4j (async driver), Graphiti MCP server, pytest
**Storage**: Neo4j (default) or FalkorDB (Redis)
**Testing**: pytest (Python integration tests)
**Target Platform**: Linux containers (Docker/Podman)
**Project Type**: Single (Python patches in docker/ directory)
**Performance Goals**: <5 seconds for depth=2 queries on 1000-entity graphs
**Constraints**: Must maintain existing GraphTraversal class API for backward compatibility
**Scale/Scope**: Supports up to 500 connections per traversal with cycle detection

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Container-First Architecture
✅ **PASS** - Changes are within Python container (docker/patches/). No new containers required.

### Principle II: Graph-Centric Design
✅ **PASS** - Maintains graph traversal through Graphiti API. Preserves entity/relationship structure.

### Principle III: Zero-Friction Knowledge Capture
✅ **PASS** - Fix is transparent to users. No changes to capture workflows.

### Principle IV: Query Resilience
✅ **PASS** - Existing special character handling preserved. Hyphenated identifiers continue to work.

### Principle V: Graceful Degradation
✅ **PASS** - Error handling maintained for unavailable drivers, missing entities, connection failures.

### Principle VI: Codanna-First Development
✅ **PASS** - Will use Codanna CLI to explore existing async patterns in codebase before implementing.

### Principle VII: Language Separation
✅ **PASS** - Changes only in docker/patches/ (Python). No TypeScript changes required.

### Principle VIII: Dual-Audience Documentation
✅ **PASS** - Will update docs/reference/observability.md if new metrics added (none expected for bug fix).

### Principle IX: Observability & Metrics
✅ **PASS** - No new metrics being added. Fix restores existing functionality only.

**Constitution Gate Result**: ✅ **ALL PASSED** - Proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/021-fix-async-session/
├── plan.md              # This file
├── research.md          # Phase 0 output (async Neo4j patterns)
├── data-model.md        # Phase 1 output (entity/connection structures)
├── quickstart.md        # Phase 1 output (testing guide)
├── contracts/           # Phase 1 output (MCP tool contract)
│   └── investigate-entity.yaml
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
docker/patches/
├── utils/
│   └── graph_traversal.py    # Modified: async methods for Neo4j
└── graphiti_mcp_server.py     # Modified: async integration

docker/tests/integration/
└── test_investigate.py        # Existing: validates fix
```

**Structure Decision**: Single project (Python only). Changes isolated to docker/patches/ following Principle VII (Language Separation).

## Complexity Tracking

> **No violations requiring justification**

This fix:
- Maintains existing class structure (GraphTraversal)
- Preserves public API (traverse() method signature)
- Only changes internal implementation from sync to async
- No new dependencies or architectural patterns

---

## Phase 0: Research & Decisions

### Research Tasks

1. **Neo4j AsyncSession Patterns**
   - **Question**: What is the correct async syntax for Neo4j Python driver?
   - **Sources**: Neo4j Python driver docs, existing MCP server async patterns
   - **Decision Needed**: `async with driver.session() as session:` vs alternatives

2. **Graphiti Async Architecture**
   - **Question**: How does Graphiti's async client work with Neo4j driver?
   - **Sources**: docker/patches/graphiti_mcp_server.py (line 1647), existing async methods
   - **Decision Needed**: Copy patterns from get_status() or investigate_entity()

3. **Backward Compatibility Strategy**
   - **Question**: Should we support both sync and async, or async-only?
   - **Sources**: FalkorDB implementation (sync), MCP server usage (async)
   - **Decision Needed**: Dual implementation or wrapper approach

### Dependencies to Analyze

1. **Neo4j Python Driver Version**
   - Need to confirm async support in base image (zepai/knowledge-graph-mcp:standalone)
   - Check if `AsyncSession` context manager is available in current driver version

2. **FalkorDB Async Support**
   - Currently uses synchronous redis client
   - May need async wrapper for future (deferred per spec "Out of Scope")

### Integration Points

1. **MCP Server → GraphTraversal**
   - `graphiti_mcp_server.py:1750-1754` creates GraphTraversal instance
   - Passes `client.driver` (async) to GraphTraversal constructor
   - Need to update instantiation if API changes

2. **GraphTraversal.traverse() → Results**
   - Returns TraversalResult dataclass
   - Need to ensure async version returns same structure
   - MCP server expects synchronous return from traverse()

---

*Research findings will be consolidated in `research.md` following Phase 0 completion.*
