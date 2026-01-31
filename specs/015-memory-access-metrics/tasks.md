# Tasks: Memory Access Metrics

**Input**: Design documents from `/specs/015-memory-access-metrics/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Manual verification in Grafana dashboard (no automated tests - metrics instrumentation)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, etc.)
- Include exact file paths in descriptions

## Path Conventions

**For this feature:**
- **Python implementation**: `docker/patches/` for code changes
- **Python tests**: `docker/tests/` for test files
- **Documentation**: `docs/reference/observability.md`

---

## Phase 1: Setup

**Purpose**: Read and understand existing code structure

- [x] T001 Read docker/patches/metrics_exporter.py to understand record_access_pattern() function
- [x] T002 Read docker/patches/graphiti_mcp_server.py to locate search_memory_nodes and search_memory_facts handlers
- [x] T003 Read docker/patches/lifecycle_manager.py to understand existing record_access_pattern() usage pattern

**Checkpoint**: Understanding of current implementation achieved

---

## Phase 2: Foundational (Label Mapping Fix)

**Purpose**: Fix importance label mapping to match dashboard expectations

**⚠️ CRITICAL**: This must be done BEFORE user stories so labels are correct

- [x] T004 Update importance label mapping in docker/patches/metrics_exporter.py to map 5→"CRITICAL", 4→"HIGH", 3→"MEDIUM", 2→"LOW", 1→"LOW"

**Checkpoint**: Label mapping matches dashboard expectations

---

## Phase 3: User Story 1 - View Access Distribution by Importance (Priority: P1) 🎯 MVP

**Goal**: Enable "Access by Importance" pie chart to show data when searches return results

**Independent Test**: Perform searches returning memories of different importance levels, verify dashboard pie chart shows proportional distribution

### Implementation for User Story 1

- [x] T005 [US1] Modify search_memory_nodes handler in docker/patches/graphiti_mcp_server.py to extract importance attribute from node results
- [x] T006 [US1] Call decay_metrics.record_access_pattern() with importance, lifecycle_state, and days_since_last_access in search_memory_nodes handler
- [x] T007 [US1] Add error handling for missing node attributes in search_memory_nodes handler (use defaults: importance=3, state="ACTIVE", days=0)

**Checkpoint**: US1 complete - importance distribution metrics recorded during node searches

---

## Phase 4: User Story 2 - View Access Distribution by Lifecycle State (Priority: P1)

**Goal**: Enable "Access by State" pie chart to show data when searches return results

**Independent Test**: Perform searches returning memories in different lifecycle states, verify dashboard pie chart shows state distribution

### Implementation for User Story 2

- [x] T008 [US2] Verify search_memory_nodes handler from T006 records lifecycle_state correctly (already handled by T006)
- [x] T009 [US2] Verify search_memory_facts handler in docker/patches/graphiti_mcp_server.py also calls record_access_pattern() (shares implementation with US1)

**Checkpoint**: US2 complete - state distribution metrics recorded during searches (already handled by US1 implementation)

---

## Phase 5: User Story 3 - Monitor Memory Age Distribution (Priority: P2)

**Goal**: Enable "Age Distribution" heatmap to show data when searches return results

**Independent Test**: Perform searches, verify dashboard heatmap shows memories in time buckets

### Implementation for User Story 3

- [x] T010 [US3] Verify search_memory_nodes handler from T006 records days_since_last_access correctly (already handled by T006)
- [x] T011 [US3] Verify histogram bucket boundaries match dashboard: [1, 7, 30, 90, 180, 365, 730, 1095] days

**Checkpoint**: US3 complete - age distribution histogram recorded during searches (already handled by US1 implementation)

---

## Phase 6: User Story 4 - Track Memory Reactivations (Priority: P2)

**Goal**: Verify "Reactivations" stat panels show counts when memories are reactivated

**Independent Test**: Access DORMANT/ARCHIVED memories, verify reactivation stat panels increment

### Implementation for User Story 4

- [x] T012 [US4] Verify record_reactivation() function exists in docker/patches/metrics_exporter.py and is called from lifecycle_manager.py
- [x] T013 [US4] Verify reactivation metrics use from_state label (DORMANT, ARCHIVED) correctly

**Checkpoint**: US4 complete - reactivation tracking already functional (no code changes needed)

---

## Phase 7: User Story 5 - Validate Decay Scoring Effectiveness (Priority: P3)

**Goal**: Verify "Access vs Decay Correlation" panel shows both metrics

**Independent Test**: View dashboard correlation panel, verify access rate and decay score both display

### Implementation for User Story 5

- [x] T014 [US5] Verify knowledge_decay_score_avg gauge metric exists and is exported (already implemented in feature #009)
- [x] T015 [US5] Verify dashboard correlation panel queries both metrics (already configured in feature #37)

**Checkpoint**: US5 complete - correlation validation already functional (no code changes needed)

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Finalize implementation and verify all metrics work

- [x] T016 Rebuild Docker container with code changes: docker build -f docker/Dockerfile -t madeinoz-knowledge-system:local .
- [x] T017 Restart containers: bun run server-cli stop && bun run server-cli start --dev
- [x] T018 Verify all four metrics appear in metrics endpoint: curl -s http://localhost:9091/metrics | grep "knowledge_access_by"
- [x] T019 Generate test data by performing searches: bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts --profile development search_nodes "test"
- [x] T020 Verify dashboard panels show data at http://localhost:3002/d/memory-access-dashboard
- [x] T021 Update docs/reference/observability.md with new metrics documentation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion
- **User Stories (Phases 3-7)**: All depend on Foundational (label fix) completion
- **Polish (Phase 8)**: Depends on all implementation phases

### User Story Dependencies

| Story | Priority | Dependencies | Notes |
|-------|----------|--------------|-------|
| US1 | P1 | Phase 2 only | Implements core instrumentation |
| US2 | P1 | Phase 2, US1 | Uses US1 implementation |
| US3 | P2 | Phase 2, US1 | Uses US1 implementation |
| US4 | P2 | Phase 2 only | Verification only - already works |
| US5 | P3 | Phase 2 only | Verification only - already works |

### Within Each Phase

Since most work is in `graphiti_mcp_server.py`, tasks must be sequential within each file.

---

## Parallel Opportunities

**Limited parallelism** due to single-file implementation:

- Phase 1 tasks (T001-T003): Sequential (same file read-only)
- Phase 2 tasks (T004): Single task
- Phases 3-7: Implementation is mostly verification (US2-US5 reuse US1 work)
- Phase 8: Sequential (container rebuild must complete before restart)

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational label fix (T004)
3. Complete Phase 3: User Story 1 (T005-T007)
4. **STOP and VALIDATE**: Verify importance distribution metrics appear in dashboard
5. Dashboard "Access by Importance" panel shows data

### Incremental Delivery

1. Setup + Foundational → Label mapping fixed
2. Add US1 implementation → Core instrumentation done
3. US2-US5 → Verification phases (mostly no new code)
4. Polish → Rebuild, verify, document

---

## Summary

| Metric | Value |
|--------|-------|
| **Total Tasks** | 21 |
| **Setup Tasks** | 3 |
| **Foundational Tasks** | 1 |
| **US1 Tasks** | 3 |
| **US2 Tasks** | 2 |
| **US3 Tasks** | 2 |
| **US4 Tasks** | 2 |
| **US5 Tasks** | 2 |
| **Polish Tasks** | 6 |
| **MVP Scope** | Phase 1-3 (T001-T007) |
| **New Code Required** | T004-T007 (4 tasks) |
| **Verification Tasks** | 8 tasks (T008-T015) |

---

## Notes

- All implementation tasks modify `docker/patches/graphiti_mcp_server.py` or `docker/patches/metrics_exporter.py`
- Reactivation tracking (US4) and decay correlation (US5) already work - just need verification
- After code changes, container must be rebuilt and restarted
- Dashboard at http://localhost:3002/d/memory-access-dashboard (dev) or http://localhost:3000 (prod)
