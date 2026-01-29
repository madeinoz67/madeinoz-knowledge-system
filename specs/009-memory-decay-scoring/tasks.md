# Tasks: Memory Decay Scoring and Importance Classification

**Input**: Design documents from `/specs/009-memory-decay-scoring/`
**Prerequisites**: plan.md (complete), spec.md (complete), research.md (complete), data-model.md (complete), contracts/decay-api.yaml (complete)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

**For this project (Madeinoz Knowledge System):**
- **Python code**: `docker/patches/` for implementation, `docker/tests/` for tests
- **TypeScript code**: `src/` for implementation, `tests/` for tests (if needed)
- See Constitution Principle VII (Language Separation) for strict directory boundaries

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 [P] Create `config/decay-config.yaml` with base half-life, thresholds, and weights per data-model.md
- [X] T002 [P] Create `docker/patches/decay_types.py` with enumerations (ImportanceLevel, StabilityLevel, LifecycleState) and MemoryDecayAttributes dataclass per data-model.md
- [X] T003 [P] Create `docker/tests/unit/` directory structure for decay module tests
- [X] T004 [P] Create `docker/tests/integration/` directory structure for end-to-end tests

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Create Neo4j index for `attributes.lifecycle_state` per data-model.md in `docker/patches/graphiti_mcp_server.py` startup
- [X] T006 Create backfill migration query for existing nodes without decay attributes per data-model.md
- [X] T007 [P] Add `DecayConfig` Pydantic model in `docker/patches/decay_types.py` for loading YAML config
- [X] T008 [P] Create config loader function in `docker/patches/decay_config.py` to read `config/decay-config.yaml`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 2 - Importance and Stability Scoring at Ingestion (Priority: P1)

**Goal**: Automatically classify each memory's importance (1-5) and stability (1-5) at ingestion time using LLM

**Why US2 Before US1**: Weighted search (US1) requires importance scores to exist on memories. Classification must be implemented first.

**Independent Test**: Add a memory and verify importance and stability scores are stored in the knowledge graph.

### Implementation for User Story 2

- [X] T009 [US2] Create `docker/patches/importance_classifier.py` with CLASSIFICATION_PROMPT and `classify_memory()` async function per quickstart.md
- [X] T010 [US2] Implement LLM fallback returning defaults (3, 3) when classification fails in `importance_classifier.py`
- [X] T011 [US2] Implement `is_permanent(importance, stability)` helper function in `importance_classifier.py`
- [X] T012 [US2] Implement `classify_unclassified_nodes()` in `importance_classifier.py` to classify nodes missing importance (post-processing approach since Graphiti's queue_service is upstream)
- [X] T013 [US2] Integrate classification into maintenance cycle Step 0 in `maintenance_service.py` - sets lifecycle_state='ACTIVE', decay_score=0.0, last_accessed_at, access_count=0
- [X] T014 [P] [US2] Create unit test `docker/tests/unit/test_importance_classifier.py` for classification logic
- [X] T015 [P] [US2] Create unit test for is_permanent() edge cases (boundary values 4, 4)

**Checkpoint**: At this point, new memories receive importance/stability scores automatically

---

## Phase 4: User Story 1 - Relevance-Weighted Search Results (Priority: P1) 🎯 MVP

**Goal**: Search results ranked by weighted score combining semantic relevance (60%), recency (25%), and importance (15%)

**Independent Test**: Search for a topic and verify results ordered by weighted score, not just semantic similarity.

### Implementation for User Story 1

- [X] T016 [US1] Create `docker/patches/memory_decay.py` with `DecayCalculator` class per quickstart.md
- [X] T017 [US1] Implement `calculate_decay()` method with exponential half-life formula per research.md
- [X] T018 [US1] Implement `calculate_weighted_score()` function for combining semantic/recency/importance per research.md (60/25/15 weights)
- [X] T019 [US1] Extend `search_memory_nodes` MCP tool in `docker/patches/graphiti_mcp_server.py` to post-process results with weighted scoring
- [X] T020 [US1] Update node's last_accessed_at and access_count when returned in search results (atomic update per research.md RQ4)
- [X] T021 [US1] Add lifecycle_state filter to search (only return ACTIVE, DORMANT memories by default)
- [X] T022 [US1] Add WeightedSearchResult response schema fields (weighted_score, score_breakdown) per contracts/decay-api.yaml
- [X] T023 [P] [US1] Create unit test `docker/tests/unit/test_memory_decay.py` for DecayCalculator
- [X] T024 [P] [US1] Create unit test for weighted_score calculation edge cases

**Checkpoint**: At this point, User Story 1 (weighted search) and User Story 2 (classification) should both be fully functional

---

## Phase 5: User Story 3 - Memory Decay Over Time (Priority: P2)

**Goal**: Memories accumulate decay scores over time based on importance, stability, and access patterns

**Independent Test**: Add memories, run decay calculation, verify decay scores increase for unused low-importance memories.

### Implementation for User Story 3

- [X] T025 [US3] Implement stability-adjusted half-life calculation in `DecayCalculator` per research.md (half_life = base * stability/3.0)
- [X] T026 [US3] Implement importance-adjusted decay rate in `DecayCalculator` per research.md (adjusted_rate = lambda * (6-importance)/5)
- [X] T027 [US3] Add permanent memory bypass in decay calculation (importance >= 4 AND stability >= 4 → decay_score = 0.0)
- [X] T028 [US3] Implement batch decay score update Cypher query in `docker/patches/memory_decay.py`
- [X] T029 [US3] Implement decay score reset on access (set decay_score = 0.0 when last_accessed_at updated)
- [X] T030 [P] [US3] Create unit test for stability-adjusted half-life (volatile=7d, low=14d, moderate=30d, high=90d)
- [X] T031 [P] [US3] Create unit test for permanent memory exemption

**Checkpoint**: At this point, User Story 3 (decay over time) should be fully functional

---

## Phase 6: User Story 4 - Memory Lifecycle State Management (Priority: P2)

**Goal**: Memories transition through ACTIVE → DORMANT → ARCHIVED → EXPIRED → SOFT_DELETED based on usage and decay

**Independent Test**: Verify memories transition through states based on access patterns and decay thresholds.

### Implementation for User Story 4

- [X] T032 [US4] Create `docker/patches/lifecycle_manager.py` with `LifecycleManager` class
- [X] T033 [US4] Implement `calculate_next_state()` method with threshold logic per data-model.md state diagram
- [X] T034 [US4] Implement batch state transition Cypher query per research.md RQ4
- [X] T035 [US4] Implement re-activation logic: DORMANT/ARCHIVED → ACTIVE on access
- [X] T036 [US4] Implement soft-delete transition: EXPIRED → SOFT_DELETED with soft_deleted_at timestamp
- [X] T037 [US4] Implement permanent delete after 90-day retention window
- [X] T038 [US4] Implement `recover_soft_deleted` MCP tool per contracts/decay-api.yaml (restore to ARCHIVED state)
- [X] T039 [P] [US4] Create unit test `docker/tests/unit/test_lifecycle_manager.py` for state transitions
- [X] T040 [P] [US4] Create unit test for re-activation edge cases
- [X] T041 [P] [US4] Create unit test for soft-delete recovery within/outside 90-day window

**Checkpoint**: At this point, User Story 4 (lifecycle management) should be fully functional

---

## Phase 7: User Story 5 - Maintenance and Health Reporting (Priority: P3)

**Goal**: Automated maintenance that recalculates decay scores and generates health reports

**Independent Test**: Run maintenance process and verify decay scores updated and health metrics generated.

### Implementation for User Story 5

- [X] T042 [US5] Create `docker/patches/maintenance_service.py` with `MaintenanceService` class
- [X] T043 [US5] Implement batch processing with configurable batch_size (default 500) per data-model.md
- [X] T044 [US5] Implement maintenance orchestration: decay recalculation → state transitions → soft-delete cleanup
- [X] T045 [US5] Implement 10-minute timeout with graceful completion per spec.md SC-005
- [X] T046 [US5] Implement `run_decay_maintenance` MCP tool per contracts/decay-api.yaml
- [X] T047 [US5] Implement MaintenanceResponse with processed counts and state_transitions per contracts/decay-api.yaml
- [X] T048 [US5] Implement `get_knowledge_health` MCP tool per contracts/decay-api.yaml
- [X] T049 [US5] Implement KnowledgeHealthMetrics aggregation queries per data-model.md (states, aggregates, age_distribution)
- [X] T050 [US5] Implement `classify_memory` MCP tool for re-classification per contracts/decay-api.yaml
- [ ] T051 [P] [US5] Create unit test `docker/tests/unit/test_maintenance_service.py` for batch processing
- [ ] T052 [P] [US5] Create integration test `docker/tests/integration/test_decay_integration.py` for full maintenance cycle

**Checkpoint**: At this point, User Story 5 (maintenance) should be fully functional - ALL USER STORIES COMPLETE

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

### Documentation & Skills

- [ ] T053 [P] Update `src/skills/SKILL.md` with decay-related intents (health check, maintenance trigger)
- [ ] T054 [P] Create `src/skills/workflows/health-report.md` health report workflow
- [ ] T055 [P] Update `CLAUDE.md` with memory decay configuration documentation
- [ ] T056 Run backfill migration on existing knowledge graph
- [ ] T057 Run quickstart.md validation checklist
- [ ] T058 [P] Add health metrics to container status output in `src/skills/tools/status.ts`

### Observability (NEW - from spec Observability Metrics section)

- [X] T059 [P] Create `docker/patches/metrics_exporter.py` with Prometheus metrics definitions (Counter, Gauge, Histogram)
- [X] T060 [P] Instrument `maintenance_service.py` with duration histogram and maintenance run counters
- [X] T061 [P] Instrument `importance_classifier.py` with latency histogram and classification status counter
- [X] T062 [P] Instrument `lifecycle_manager.py` with state transition counters (from_state, to_state labels)
- [X] T063 [P] Add `/metrics` HTTP endpoint to graphiti_mcp_server.py using prometheus_client start_http_server
- [X] T064 [P] Add `/health/decay` endpoint returning DecayHealthCheck per contracts/decay-api.yaml
- [X] T065 [P] Update `config/monitoring/prometheus/prometheus.yml` with knowledge scrape target (port 9090)
- [X] T066 [P] Create `config/monitoring/prometheus/alerts/knowledge.yml` with alert rules
- [X] T067 [P] Create unit test `docker/tests/unit/test_metrics_exporter.py` for metrics registration
- [X] T068 [P] Update `docs/reference/observability.md` with decay metrics documentation (following Principle VIII)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 2 (Phase 3)**: Depends on Foundational - MUST complete before US1 (weighted search needs scores)
- **User Story 1 (Phase 4)**: Depends on US2 - Core MVP value
- **User Stories 3-5 (Phases 5-7)**: Can start after US1 complete, can run in parallel
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

```
Phase 1: Setup ─────────────────────────────────────────────────┐
                                                                 │
Phase 2: Foundational ──────────────────────────────────────────┤
                                                                 │
Phase 3: US2 (Classification) ──────────────────────────────────┤ BLOCKING
                                                                 │
Phase 4: US1 (Weighted Search) ─────────────────────────────────┤ MVP
                                                                 │
         ┌──────────────────────────────────────────────────────┤
         │                                                       │
Phase 5: US3 (Decay)  ─────────────┐                            │
                                    ├── CAN RUN IN PARALLEL ────┤
Phase 6: US4 (Lifecycle) ─────────┤                            │
                                    │                            │
Phase 7: US5 (Maintenance) ────────┘                            │
                                                                 │
Phase 8: Polish ────────────────────────────────────────────────┘
```

### Within Each User Story

- Models/types before implementation
- Core implementation before MCP tool integration
- MCP tools before tests
- Tests verify story completeness

### Parallel Opportunities

**Phase 1 (4 parallel tasks):**
- T001, T002, T003, T004 - all independent file creation

**Phase 2 (2 parallel pairs):**
- T007, T008 - config model and loader (independent)

**Phase 3 (2 parallel tests):**
- T014, T015 - unit tests after T009-T013 complete

**Phase 4 (2 parallel tests):**
- T023, T024 - unit tests after T016-T022 complete

**Phase 5 (2 parallel tests):**
- T030, T031 - unit tests after T025-T029 complete

**Phase 6 (3 parallel tests):**
- T039, T040, T041 - unit tests after T032-T038 complete

**Phase 7 (2 parallel tests):**
- T051, T052 - tests after T042-T050 complete

**Phase 8 (14 parallel tasks):**
- T053, T054, T055, T058 - documentation/skill updates
- T059-T068 - observability tasks (all independent)

---

## Implementation Strategy

### MVP First (US2 + US1)

1. Complete Phase 1: Setup (4 tasks)
2. Complete Phase 2: Foundational (4 tasks)
3. Complete Phase 3: User Story 2 - Classification (7 tasks)
4. Complete Phase 4: User Story 1 - Weighted Search (9 tasks)
5. **STOP and VALIDATE**: Test weighted search with importance scoring
6. Deploy/demo MVP

### Full Feature Delivery

1. MVP complete → Foundation ready
2. Add User Story 3 (Decay) → Test independently
3. Add User Story 4 (Lifecycle) → Test independently
4. Add User Story 5 (Maintenance) → Test independently
5. Complete Polish phase
6. Full feature deployed

---

## Task Count Summary

| Phase | Tasks | Parallel Opportunities |
|-------|-------|------------------------|
| Phase 1: Setup | 4 | 4 (100%) |
| Phase 2: Foundational | 4 | 2 (50%) |
| Phase 3: US2 (P1) | 7 | 2 (29%) |
| Phase 4: US1 (P1) 🎯 | 9 | 2 (22%) |
| Phase 5: US3 (P2) | 7 | 2 (29%) |
| Phase 6: US4 (P2) | 10 | 3 (30%) |
| Phase 7: US5 (P3) | 11 | 2 (18%) |
| Phase 8: Polish | 6 | 4 (67%) |
| Phase 8: Observability | 10 | 10 (100%) |
| **Total** | **68** | **31 (46%)** |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- MVP = Phase 1-4 (24 tasks) delivers core weighted search value
