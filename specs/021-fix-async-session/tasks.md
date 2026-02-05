# Implementation Tasks: Fix AsyncSession Compatibility in Graph Traversal

**Feature Branch**: `021-fix-async-session`
**Date**: 2026-02-05
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)

## Overview

This document breaks down the implementation of Feature 021 into actionable tasks organized by user story. Tasks are numbered sequentially (T001, T002, etc.) and organized to enable incremental delivery and independent testing.

## Task Count Summary

- **Total Tasks**: 13
- **Setup Tasks**: 2
- **Foundational Tasks**: 2
- **User Story 1 (P1)**: 6 tasks
- **User Story 2 (P2)**: 1 task
- **User Story 3 (P3)**: 0 tasks (uses US1 implementation)
- **Polish Tasks**: 2

## Parallel Execution Opportunities

- **T003-T004**: Can run in parallel (separate files)
- **T006-T007**: Can run in parallel (separate implementations)
- **T008**: Parallel with T006-T007 (contract validation)
- **T011**: Can run independently (existing test validation)

## MVP Scope

**Recommended MVP**: User Story 1 only (T001-T010)
- Enables core investigate functionality
- Independently testable
- Delivers primary user value

---

## Phase 1: Setup

**Goal**: Prepare development environment and understand current implementation.

### Story Goal
Ensure development environment is ready and current implementation is understood.

### Independent Test Criteria
- Can run existing integration tests successfully
- Understand current sync implementation in graph_traversal.py

### Tasks

- [X] T001 Review research.md decisions in specs/021-fix-async-session/research.md
- [X] T002 Review data-model.md entity definitions in specs/021-fix-async-session/data-model.md

---

## Phase 2: Foundational

**Goal**: Implement async infrastructure that all user stories depend on.

### Story Goal
Create async-compatible graph traversal infrastructure.

### Independent Test Criteria
- GraphTraversal class can be instantiated with async driver
- Async session can be opened and closed successfully

### Tasks

- [X] T003 [P] Add async method signature to GraphTraversal.traverse() in docker/patches/utils/graph_traversal.py
- [X] T004 [P] Create _traverse_neo4j_async() async method in docker/patches/utils/graph_traversal.py

---

## Phase 3: User Story 1 - Investigate Entity Connections (Priority: P1)

**Goal**: Users can find all entities connected to a specific entity, traversing up to 3 hops deep.

### Independent Test Criteria
- Running `investigate "Apollo 11" --depth 2` returns connected entities
- No AsyncSession errors in MCP server logs
- Cycle detection works correctly for depth=3 queries

### Tasks

- [X] T005 [US1] Implement async Neo4j session context in docker/patches/utils/graph_traversal.py:_traverse_neo4j_async()
  - Use `async with self.driver.session() as session:` pattern
  - Implement Cypher query execution with `await session.run(query)`
  - Process results with async record iteration: `[record async for record in results]`

- [X] T006 [P] [US1] Update FalkorDB wrapper to return coroutine in docker/patches/utils/graph_traversal.py
  - Wrap existing _traverse_falkordb_sync() in async def
  - Return TraversalResult directly (no await needed for sync implementation)

- [X] T007 [P] [US1] Update MCP server to await traversal in docker/patches/graphiti_mcp_server.py
  - Change line 1756 from `traversal_result = traversal.traverse(...)` to `traversal_result = await traversal.traverse(...)`
  - Ensure investigate_entity function remains async

- [X] T008 [US1] Validate contract output matches quickstart scenarios in specs/021-fix-async-session/contracts/investigate-entity.yaml
  - Verify TraversalResult structure matches contract
  - Confirm all metadata fields are present

- [X] T009 [US1] Test basic investigation per quickstart.md specs/021-fix-async-session/quickstart.md
  - Run: `bun run knowledge-cli.ts --profile development investigate "Apollo 11" --depth 2`
  - Verify connected entities returned (Neil Armstrong, Buzz Aldrin, Michael Collins)
  - Confirm no AsyncSession errors

- [X] T010 [US1] Test edge cases per quickstart.md specs/021-fix-async-session/quickstart.md
  - Test depth validation: `investigate "Apollo 11" --depth 5` should fail
  - Test entity not found: `investigate "NonExistentEntity123"` should return clear error
  - Test cycle detection: Investigate entity with cyclical relationships

---

## Phase 4: User Story 2 - Filter by Relationship Type (Priority: P2)

**Goal**: Users can filter investigation results by specific relationship types to reduce noise.

### Independent Test Criteria
- `investigate "apt28" --relationship-type "uses"` returns only USES relationships
- Filtered queries return empty results when no matches found

### Tasks

- [X] T011 [P] [US2] Verify relationship filtering works with async implementation
  - Run: `bun run knowledge-cli.ts --profile development investigate "Apollo 11" --relationship-type "FOLLOWED"`
  - Confirm only FOLLOWED relationships returned
  - Test with multiple filters: `--relationship-type "USES" --relationship-type "TARGETS"`

---

## Phase 5: User Story 3 - Investigate Across Multiple Knowledge Groups (Priority: P3)

**Goal**: Users can investigate entities across multiple knowledge groups or specific groups.

### Independent Test Criteria
- Investigation without group filter returns connections from all groups
- Investigation with `--group-ids "main"` returns only main group connections

### Tasks

*No tasks needed* - Multi-group support is already implemented in GraphTraversal class (see data-model.md group_ids parameter). US3 validates existing functionality works with async fix.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Goal**: Ensure code quality, documentation, and observability.

### Independent Test Criteria
- All integration tests pass
- Code follows Python async best practices
- Documentation updated if needed

### Tasks

- [X] T012 [P] Run full integration test suite in docker/tests/integration/test_investigate.py
  - Execute: `pytest docker/tests/integration/test_investigate.py -v`
  - Verify all tests pass
  - Check coverage for async code paths

- [X] T013 [P] Verify performance per success criteria in spec.md
  - Run timed investigation: `time bun run knowledge-cli.ts --profile development investigate "Apollo 11" --depth 2`
  - Confirm completes in <5 seconds
  - Check query duration is reported in metadata

---

## Dependencies

```text
Phase 1 (Setup)
  └── Phase 2 (Foundational)
      ├── Phase 3 (US1 - Investigate Entity Connections)
      │   ├── Phase 4 (US2 - Filter by Relationship Type)
      │   └── Phase 5 (US3 - Multi-Group) [no tasks - uses US1 impl]
      └── Phase 6 (Polish)
```

**Blocking Relationships**:
- Phase 2 MUST complete before Phase 3 (async infrastructure needed)
- Phase 3 (US1) MUST complete before Phase 4 (US2 builds on US1)
- Phase 3 (US1) MUST complete before Phase 5 (US3 validates US1)

---

## Parallel Execution Examples

### Phase 2 (Foundational)

```bash
# Can run T003 and T004 in parallel (different methods, same file)
# T003: Add async signature to traverse()
# T004: Create _traverse_neo4j_async()
```

### Phase 3 (User Story 1)

```bash
# Can run T006, T007, T008 in parallel (T005 must complete first)
# After T005 (async infrastructure ready):
parallel \
  "T006: Update FalkorDB wrapper" \
  "T007: Update MCP server to await" \
  "T008: Validate contract output"
```

### Phase 6 (Polish)

```bash
# Can run T012 and T013 in parallel (independent validation)
parallel \
  "T012: Run integration tests" \
  "T013: Verify performance"
```

---

## Implementation Strategy

### MVP First (Recommended)

1. **MVP Release**: Phase 1 + Phase 2 + Phase 3 (US1)
   - Delivers core investigate functionality
   - Independently testable
   - Addresses primary user pain point (AsyncSession error)

2. **Enhancement Release**: Phase 4 (US2)
   - Adds relationship filtering
   - Builds on working MVP

3. **Full Release**: Phase 5 (US3) + Phase 6 (Polish)
   - Multi-group validation
   - Performance verification
   - Full test coverage

### Incremental Delivery

Each phase is a complete, independently testable increment:
- **After Phase 2**: Async infrastructure ready (no user value yet)
- **After Phase 3**: Core investigate feature works (MVP ✅)
- **After Phase 4**: Filtering capability works
- **After Phase 5**: Multi-group support validated
- **After Phase 6**: Production-ready with tests and performance verification

---

## Notes

- All tasks include exact file paths from plan.md project structure
- Tasks follow checklist format: `- [ ] [TaskID] [P?] [Story?] Description with file path`
- [P] marker indicates parallelizable tasks (different files, no dependencies)
- [Story] labels (US1, US2, US3) map directly to user stories in spec.md
- Integration test location: `docker/tests/integration/test_investigate.py`
- Testing guide: `specs/021-fix-async-session/quickstart.md`
