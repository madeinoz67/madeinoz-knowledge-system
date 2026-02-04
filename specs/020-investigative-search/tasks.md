# Tasks: Investigative Search with Connected Entities

**Input**: Design documents from `/specs/020-investigative-search/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/investigate-entity.yaml

**Tests**: Tests are REQUIRED - explicitly requested in feature specification (FR-012: "comprehensive tests for investigative search functionality")

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

**For this project (Madeinoz Knowledge System):**
- **Python code**: `docker/patches/` for implementation, `docker/tests/` for tests
- **TypeScript code**: `src/skills/Knowledge/` for implementation, `tests/` for tests
- See Constitution Principle VII (Language Separation) for strict directory boundaries

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create response types and prepare structure for implementation

- [x] T001 [P] Add InvestigateResult response type to docker/patches/models/response_types.py
- [x] T002 [P] Add Connection response type to docker/patches/models/response_types.py
- [x] T003 [P] Add InvestigationMetadata response type to docker/patches/models/response_types.py
- [x] T004 [P] Add InvestigateEntityError error response type to docker/patches/models/response_types.py

**Checkpoint**: ✅ Response types ready for MCP tool implementation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core graph traversal infrastructure that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Create docker/patches/utils/graph_traversal.py module with GraphTraversal class
- [x] T006 Implement cycle detection with visited entity tracking in docker/patches/utils/graph_traversal.py
- [x] T007 [P] Implement Neo4j Cypher variable-length path traversal in docker/patches/utils/graph_traversal.py
- [x] T008 [P] Implement FalkorDB breadth-first traversal in docker/patches/utils/graph_traversal.py
- [x] T009 Implement depth validation (1-3 hops) in docker/patches/utils/graph_traversal.py
- [x] T010 [P] Implement relationship type filtering in docker/patches/utils/graph_traversal.py
- [x] T011 [P] Implement connection count warning threshold (500) in docker/patches/utils/graph_traversal.py
- [x] T012 Add entity name resolution to traversal results in docker/patches/utils/graph_traversal.py

**Checkpoint**: ✅ Graph traversal infrastructure ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Investigative Search Returns Connected Entities (Priority: P1) 🎯 MVP

**Goal**: Return entity with all direct connections (names, types, UUIDs) in a single query

**Independent Test**: Search for an entity with known connections, verify all related entities returned with names and relationship types

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T013 [P] [US1] Create integration test for investigate with 1-hop connections in docker/tests/integration/test_investigate.py
- [x] T014 [P] [US1] Create integration test for investigate with no connections in docker/tests/integration/test_investigate.py
- [x] T015 [P] [US1] Create integration test for investigate entity not found in docker/tests/integration/test_investigate.py
- [x] T016 [P] [US1] Create unit test for graph traversal cycle detection in docker/tests/unit/test_graph_traversal.py
- [x] T017 [P] [US1] Create unit test for connection count warning threshold in docker/tests/unit/test_graph_traversal.py

### Implementation for User Story 1

- [x] T018 [US1] Add investigate_entity MCP tool to docker/patches/graphiti_mcp_server.py
- [x] T019 [US1] Implement entity lookup by name in investigate_entity tool
- [x] T020 [US1] Implement 1-hop traversal using graph_traversal.py in investigate_entity tool
- [x] T021 [US1] Build InvestigateResult response with entity and connections in investigate_entity tool
- [x] T022 [US1] Add depth parameter handling (default=1) in investigate_entity tool
- [x] T023 [US1] Add query duration tracking to InvestigationMetadata in investigate_entity tool
- [x] T024 [US1] Add error handling for entity not found in investigate_entity tool

**Checkpoint**: ✅ At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Configurable Connection Depth (Priority: P1)

**Goal**: Control traversal depth (1-3 hops) for comprehensive analysis

**Independent Test**: Search with different depth values, verify correct number of hops returned

### Tests for User Story 2

- [x] T025 [P] [US2] Create integration test for depth=1 traversal in docker/tests/integration/test_investigate.py
- [x] T026 [P] [US2] Create integration test for depth=2 traversal in docker/tests/integration/test_investigate.py
- [x] T027 [P] [US2] Create integration test for depth=3 traversal in docker/tests/integration/test_investigate.py
- [x] T028 [P] [US2] Create integration test for depth>3 rejection in docker/tests/integration/test_investigate.py
- [x] T029 [P] [US2] Create unit test for multi-hop traversal in docker/tests/unit/test_graph_traversal.py

### Implementation for User Story 2

- [x] T030 [US2] Implement variable-depth traversal (2-3 hops) in docker/patches/utils/graph_traversal.py
- [x] T031 [US2] Update investigate_entity tool to use depth parameter from graph_traversal.py
- [x] T032 [US2] Add hop_distance to Connection response type in models/response_types.py
- [x] T033 [US2] Include hop_distance in InvestigateResult metadata in investigate_entity tool

**Checkpoint**: ✅ At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Filterable by Relationship Type (Priority: P2)

**Goal**: Filter connections by specific relationship types to reduce noise

**Independent Test**: Search with relationship filters, verify only matching relationships returned

### Tests for User Story 3

- [ ] T034 [P] [US3] Create integration test for single relationship type filter in docker/tests/integration/test_investigate.py
- [ ] T035 [P] [US3] Create integration test for multiple relationship type filters in docker/tests/integration/test_investigate.py
- [ ] T036 [P] [US3] Create integration test for non-existent relationship type in docker/tests/integration/test_investigate.py
- [ ] T037 [P] [US3] Create unit test for relationship type filtering in docker/tests/unit/test_graph_traversal.py

### Implementation for User Story 3

- [x] T038 [US3] Add relationship_types parameter to investigate_entity tool in docker/patches/graphiti_mcp_server.py
- [x] T039 [US3] Implement relationship type filtering in graph_traversal.py before traversal
- [x] T040 [US3] Add relationship_types_filtered to InvestigationMetadata in investigate_entity tool
- [x] T041 [US3] Update InvestigateResult to include filtered relationship metadata in investigate_entity tool

**Checkpoint**: ✅ User Stories 1, 2, AND 3 should all work independently

---

## Phase 6: User Story 4 - Works with Custom Entity Types (Priority: P1)

**Goal**: Support all custom entity types (Phone, Account, ThreatActor, Malware, etc.)

**Independent Test**: Create custom entity types, verify investigate returns their connections correctly

### Tests for User Story 4

- [ ] T042 [P] [US4] Create integration test for ThreatActor entity type in docker/tests/integration/test_investigate.py
- [ ] T043 [P] [US4] Create integration test for Malware entity type in docker/tests/integration/test_investigate.py
- [ ] T044 [P] [US4] Create integration test for Indicator entity type in docker/tests/integration/test_investigate.py
- [ ] T045 [P] [US4] Create integration test for custom relationship types (USES, EXPLOITS) in docker/tests/integration/test_investigate.py

### Implementation for User Story 4

- [x] T046 [US4] Ensure graph traversal handles all entity labels (standard and custom) in docker/patches/utils/graph_traversal.py
- [x] T047 [US4] Ensure graph traversal handles custom relationship types in docker/patches/utils/graph_traversal.py
- [x] T048 [US4] Add entity labels to InvestigateResult entity in investigate_entity tool
- [x] T049 [US4] Add support for custom_attributes in Entity response type in models/response_types.py

**Checkpoint**: ✅ User Stories 1, 2, 3, AND 4 should all work independently

---

## Phase 7: User Story 5 - AI-Friendly JSON Structure (Priority: P1)

**Goal**: Return entity names alongside UUIDs for AI consumption without additional lookups

**Independent Test**: Programmatically call investigate, verify entity names present without additional queries

### Tests for User Story 5

- [ ] T050 [P] [US5] Create integration test verifying names in all entity responses in docker/tests/integration/test_investigate.py
- [ ] T051 [P] [US5] Create integration test verifying UUIDs in all entity responses in docker/tests/integration/test_investigate.py
- [ ] T052 [P] [US5] Create integration test verifying no additional queries needed in docker/tests/integration/test_investigate.py

### Implementation for User Story 5

- [x] T053 [US5] Ensure full entity objects (name, type, UUID) returned in connections in investigate_entity tool
- [x] T054 [US5] Verify InvestigateResult structure includes all required entity fields in investigate_entity tool
- [ ] T055 [US5] Add format validation test for AI-friendly JSON in docker/tests/integration/test_investigate.py

**Checkpoint**: ✅ User Stories 1-5 should all work independently with AI-friendly responses

---

## Phase 8: User Story 6 - Cycle Detection and Handling (Priority: P2)

**Goal**: Detect and handle circular relationships without infinite loops

**Independent Test**: Create circular relationships, verify query completes with cycle reporting

### Tests for User Story 6

- [ ] T056 [P] [US6] Create integration test for circular relationship (A→B→C→A) in docker/tests/integration/test_investigate.py
- [ ] T057 [P] [US6] Create integration test for self-referential relationship (A→A) in docker/tests/integration/test_investigate.py
- [ ] T058 [P] [US6] Create integration test for cycle metadata reporting in docker/tests/integration/test_investigate.py
- [ ] T059 [P] [US6] Create unit test for visited entity tracking in docker/tests/unit/test_graph_traversal.py

### Implementation for User Story 6

- [x] T060 [US6] Implement cycle detection in graph_traversal.py (already in T006, verify working)
- [x] T061 [US6] Add cycles_detected to InvestigationMetadata in investigate_entity tool
- [x] T062 [US6] Add cycles_pruned (UUID list) to InvestigationMetadata in investigate_entity tool
- [x] T063 [US6] Ensure no duplicate entities returned in connections in investigate_entity tool
- [x] T064 [US6] Ensure self-referential relationships included once in investigate_entity tool

**Checkpoint**: ✅ User Stories 1-6 should all work independently with cycle handling

---

## Phase 9: User Story 7 - CLI and MCP Tool Parity (Priority: P1)

**Goal**: Access investigative search from both CLI and MCP tools

**Independent Test**: Run same query via CLI and MCP, verify identical results

### Tests for User Story 7

- [ ] T065 [P] [US7] Create unit test for knowledge-cli investigate command in tests/unit/skills/Knowledge/tools/knowledge-cli.test.ts
- [ ] T066 [P] [US7] Create unit test for mcp-client investigateEntity method in tests/unit/skills/Knowledge/lib/mcp-client.test.ts
- [ ] T067 [P] [US7] Create unit test for formatInvestigateEntity formatter in tests/unit/skills/Knowledge/lib/output-formatter.test.ts
- [ ] T068 [P] [US7] Create integration test for CLI-MCP parity in docker/tests/integration/test_investigate.py

### Implementation for User Story 7

- [x] T069 [US7] Add investigate command handler to docker/patches/graphiti_mcp_server.py (already in T018, verify MCP tool complete)
- [x] T070 [P] [US7] Add investigateEntity() method to src/skills/lib/mcp-client.ts
- [x] T071 [P] [US7] Add cmdInvestigate() handler to src/skills/tools/knowledge-cli.ts
- [x] T072 [P] [US7] Add formatInvestigateEntity() formatter to src/skills/lib/output-formatter.ts
- [x] T073 [US7] Register investigate command in knowledge-cli.ts registerCommands() method
- [x] T074 [US7] Add --depth flag parsing for investigate command in knowledge-cli.ts
- [x] T075 [US7] Add --relationship-type flag parsing for investigate command in knowledge-cli.ts
- [ ] T076 [P] [US7] Update src/skills/Knowledge/SKILL.md workflow routing for investigate command
- [x] T077 [US7] Verify consistent JSON structure between CLI and MCP in both implementations

**Checkpoint**: ✅ User Stories 1-7 should all work independently with CLI and MCP access

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Tests, documentation, metrics, and validation

- [ ] T078 [P] Add investigate metrics to docker/patches/utils/metrics_exporter.py (investigate_latency, investigate_depth, investigate_cycles)
- [ ] T079 [P] Add investigate metrics documentation to docs/reference/observability.md
- [ ] T080 [P] Create Grafana dashboard panel for investigate metrics
- [ ] T081 [P] Update docs/reference/cli.md with investigate command documentation
- [ ] T082 [P] Add OSINT/CTI workflow examples to docs/guides/osint-workflows.md
- [ ] T083 [P] Update README.md with investigate feature description
- [ ] T084 Run performance validation (SC-001: < 2s for 100 connections)
- [ ] T085 Run test coverage validation (SC-004: 100% coverage)
- [ ] T086 Validate documentation examples (SC-005: 3 workflow examples)
- [ ] T087 Validate CLI-MCP parity (SC-006: identical results)
- [ ] T088 Validate cycle handling (SC-007: no hanging on cycles)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-9)**: All depend on Foundational phase completion
  - US1, US2, US4, US5, US7 (P1) should be completed in priority order
  - US3, US6 (P2) can be completed after P1 stories or in parallel if staffed
- **Polish (Phase 10)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Depends on US1 (extends depth parameter)
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Independent filter feature
- **User Story 4 (P1)**: Can start after Foundational (Phase 2) - Tests with custom types from Feature 019
- **User Story 5 (P1)**: Can start after Foundational (Phase 2) - Validation of response format
- **User Story 6 (P2)**: Can start after Foundational (Phase 2) - Independent cycle handling
- **User Story 7 (P1)**: Depends on US1 (MCP tool must exist first)

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD approach per FR-012)
- Response types before tools (Phase 1 before Phase 3+)
- Graph traversal before MCP tool (Phase 2 before Phase 3+)
- MCP tool before CLI (US1 before US7)
- Core implementation before integration

### Parallel Opportunities

- All Setup tasks (T001-T004) can run in parallel
- All Foundational tasks (T005-T012) can run in parallel EXCEPT T012 depends on T005-T011
- All tests within a story marked [P] can run in parallel
- US3 and US6 can run in parallel with US2/US4/US5/US7 (different stories, no blocking dependencies)
- Documentation tasks (T078-T083) can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task T013: "Create integration test for investigate with 1-hop connections"
Task T014: "Create integration test for investigate with no connections"
Task T015: "Create integration test for investigate entity not found"
Task T016: "Create unit test for graph traversal cycle detection"
Task T017: "Create unit test for connection count warning threshold"

# Launch all response type setup tasks together:
Task T001: "Add InvestigateResult response type"
Task T002: "Add Connection response type"
Task T003: "Add InvestigationMetadata response type"
Task T004: "Add InvestigateEntityError error response type"
```

---

## Implementation Strategy

### MVP First (User Stories 1, 2, 4, 5, 7 - P1 stories)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T012)
3. Complete Phase 3: User Story 1 (T013-T024)
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Complete Phase 4: User Story 2 (T025-T033)
6. Complete Phase 6: User Story 4 (T042-T049)
7. Complete Phase 7: User Story 5 (T050-T055)
8. Complete Phase 9: User Story 7 (T065-T077)
9. **STOP and VALIDATE**: Test all P1 stories together
10. Deploy/demo P1 features

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Core investigate works
3. Add User Story 2 → Test independently → Depth control works
4. Add User Story 4 → Test independently → Custom types work
5. Add User Story 5 → Test independently → AI-friendly JSON works
6. Add User Story 7 → Test independently → CLI + MCP parity works
7. Add User Story 3 → Test independently → Relationship filtering works
8. Add User Story 6 → Test independently → Cycle detection works
9. Polish → Metrics, docs, performance validation
10. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T012)
2. Once Foundational is done:
   - Developer A: User Story 1 (T013-T024) → MVP!
   - Developer B: User Story 2 (T025-T033)
   - Developer C: User Story 4 (T042-T049)
3. After US1 complete:
   - Developer D: User Story 7 (T065-T077) - CLI integration
4. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Tests are REQUIRED per FR-012 (100% coverage goal)
- Performance target: < 2 seconds for 100 connections (SC-001)
