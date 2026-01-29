# Tasks: MCP Wrapper for Token Savings

**Input**: Design documents from `/specs/001-mcp-wrapper/`
**Prerequisites**: plan.md (✓), spec.md (✓), research.md (✓), data-model.md (✓), contracts/ (✓)

**Tests**: Tests ARE requested - spec mentions "validate token savings in the testing" and success criteria include benchmark validation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure) ✅

**Purpose**: Project initialization and directory structure for new modules

- [x] T001 Create wrapper library directory structure at src/server/lib/ (output-formatter.ts, token-metrics.ts, wrapper-config.ts stubs)
- [x] T002 [P] Create tests directory structure at tests/unit/ and tests/integration/ with placeholder files
- [x] T003 [P] Create ~/.madeinoz-knowledge/ directory for logs and metrics persistence

---

## Phase 2: Foundational (Blocking Prerequisites) ✅

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Define TypeScript interfaces in src/server/lib/wrapper-config.ts (WrapperConfig, FormatOptions, FormatResult per data-model.md)
- [x] T005 [P] Define TypeScript interfaces in src/server/lib/token-metrics.ts (TokenMetrics, AggregateStats, BenchmarkReport per contracts/token-metrics-api.md)
- [x] T006 [P] Define TypeScript interfaces in src/server/lib/output-formatter.ts (OutputFormat, OperationFormatter per contracts/output-formatter-api.md)
- [x] T007 Implement utility functions in src/server/lib/output-formatter.ts (relativeTime, truncateUuid, truncateText per data-model.md)
- [x] T008 [P] Implement logging infrastructure for transformation errors at src/server/lib/transformation-log.ts (TransformationLog interface, logTransformationFailure function)

**Checkpoint**: Foundation ready - user story implementation can now begin ✅

---

## Phase 3: User Story 1 - Reduced Token Consumption (Priority: P1) ✅

**Goal**: Knowledge operations (capture, search, retrieve) consume fewer tokens through compact output formatting

**Independent Test**: Measure token counts before and after wrapper for identical operations, validate ≥25% savings for capture, ≥30% for search

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T009 [P] [US1] Unit test for formatSearchNodes in tests/unit/output-formatter.test.ts (verify compact output vs raw JSON)
- [x] T010 [P] [US1] Unit test for formatSearchFacts in tests/unit/output-formatter.test.ts
- [x] T011 [P] [US1] Unit test for formatGetEpisodes in tests/unit/output-formatter.test.ts
- [x] T012 [P] [US1] Unit test for formatAddMemory in tests/unit/output-formatter.test.ts
- [x] T013 [P] [US1] Unit test for formatGetStatus in tests/unit/output-formatter.test.ts

### Implementation for User Story 1

- [x] T014 [US1] Implement formatSearchNodes formatter in src/server/lib/output-formatter.ts per contracts/output-formatter-api.md
- [x] T015 [US1] Implement formatSearchFacts formatter in src/server/lib/output-formatter.ts
- [x] T016 [US1] Implement formatGetEpisodes formatter in src/server/lib/output-formatter.ts
- [x] T017 [US1] Implement formatAddMemory formatter in src/server/lib/output-formatter.ts
- [x] T018 [US1] Implement formatGetStatus formatter in src/server/lib/output-formatter.ts
- [x] T019 [US1] Implement formatDelete formatter for delete_episode/delete_entity_edge in src/server/lib/output-formatter.ts
- [x] T020 [US1] Implement formatClearGraph formatter in src/server/lib/output-formatter.ts
- [x] T021 [US1] Implement formatOutput main entry point with formatter registry in src/server/lib/output-formatter.ts
- [x] T022 [US1] Integrate formatOutput into mcp-wrapper.ts execute() method, replacing JSON.stringify with compact output
- [x] T023 [US1] Verify all unit tests pass with `bun test tests/unit/output-formatter.test.ts`

**Checkpoint**: At this point, User Story 1 should be fully functional - wrapper outputs compact format by default ✅

---

## Phase 4: User Story 2 - Transparent Wrapper Operation (Priority: P2) ✅

**Goal**: Wrapper operates transparently - same commands work, fallback to raw JSON on transformation failure, clear error messages

**Independent Test**: Run identical commands with and without wrapper, verify equivalent information returned; trigger transformation failure and verify fallback works

### Tests for User Story 2

- [x] T024 [P] [US2] Unit test for fallback behavior in tests/unit/output-formatter.test.ts (invalid data triggers raw JSON fallback)
- [x] T025 [P] [US2] Unit test for --raw flag parsing in tests/unit/mcp-wrapper.test.ts

### Implementation for User Story 2

- [x] T026 [US2] Add try/catch wrapper around formatOutput in src/server/mcp-wrapper.ts with fallback to JSON.stringify
- [x] T027 [US2] Implement --raw flag in src/server/mcp-wrapper.ts to bypass compact formatting
- [x] T028 [US2] Implement transformation error logging in src/server/lib/transformation-log.ts (write to ~/.madeinoz-knowledge/wrapper.log)
- [x] T029 [US2] Add usedFallback and error fields to FormatResult in src/server/lib/output-formatter.ts
- [x] T030 [US2] Ensure error messages from MCP pass through unmodified in src/server/mcp-wrapper.ts
- [x] T031 [US2] Verify all unit tests pass with `bun test tests/unit/`

**Checkpoint**: Wrapper now handles all edge cases gracefully, transparent to users ✅

---

## Phase 5: User Story 3 - Measurable Token Savings Validation (Priority: P3) ✅

**Goal**: Benchmark suite validates token savings, produces report with before/after comparisons per operation type

**Independent Test**: Run benchmark suite, verify report shows savings percentages meeting targets (≥25% capture, ≥30% search)

### Tests for User Story 3

- [x] T032 [P] [US3] Unit test for measureTokens in tests/unit/token-metrics.test.ts
- [x] T033 [P] [US3] Unit test for estimateTokens in tests/unit/token-metrics.test.ts
- [x] T034 [P] [US3] Unit test for formatMetricsReport in tests/unit/token-metrics.test.ts
- [x] T035 [P] [US3] Unit test for aggregateMetrics in tests/unit/token-metrics.test.ts

### Implementation for User Story 3

- [x] T036 [US3] Implement measureTokens function in src/server/lib/token-metrics.ts per contracts/token-metrics-api.md
- [x] T037 [US3] Implement estimateTokens function in src/server/lib/token-metrics.ts
- [x] T038 [US3] Implement formatMetricsReport function in src/server/lib/token-metrics.ts
- [x] T039 [US3] Implement appendMetrics and loadMetrics persistence functions in src/server/lib/token-metrics.ts
- [x] T040 [US3] Implement aggregateMetrics function in src/server/lib/token-metrics.ts
- [x] T041 [US3] Implement generateBenchmarkReport function in src/server/lib/token-metrics.ts
- [x] T042 [US3] Add --metrics flag to src/server/mcp-wrapper.ts to display token metrics after each operation
- [x] T043 [US3] Add --metrics-file flag to src/server/mcp-wrapper.ts to append metrics to JSONL file
- [x] T044 [US3] Create integration benchmark test at tests/integration/wrapper-benchmark.test.ts (requires running MCP server)
- [x] T045 [US3] Define TOKEN_SAVINGS_TARGETS constants in src/server/lib/token-metrics.ts (25% capture, 30% search)
- [x] T046 [US3] Verify benchmark test validates savings meet targets with `bun test tests/integration/wrapper-benchmark.test.ts`

**Checkpoint**: Token savings validated and measurable via benchmark suite ✅

---

## Phase 6: Polish & Cross-Cutting Concerns ✅

**Purpose**: Documentation updates, workflow integration, and final validation

- [x] T047 [P] Update src/skills/SKILL.md to document wrapper CLI as preferred interface
- [x] T048 [P] Update src/skills/workflows/SearchKnowledge.md to use wrapper CLI instead of direct MCP calls
- [x] T049 [P] Update src/skills/workflows/CaptureEpisode.md to use wrapper CLI
- [x] T050 [P] Update src/skills/workflows/SearchFacts.md to use wrapper CLI
- [x] T051 [P] Update src/skills/workflows/GetRecent.md to use wrapper CLI
- [x] T052 [P] Update src/skills/workflows/GetStatus.md to use wrapper CLI
- [x] T053 [P] Update src/skills/workflows/ClearGraph.md to use wrapper CLI
- [x] T054 Add environment variable support (MADEINOZ_WRAPPER_COMPACT, MADEINOZ_WRAPPER_METRICS_FILE, MADEINOZ_WRAPPER_LOG_FILE) in src/server/lib/wrapper-config.ts
- [x] T055 Update mcp-wrapper.ts help message with new flags and examples
- [x] T056 Run full test suite with `bun test` and verify all tests pass
- [x] T057 Run quickstart.md validation (execute all quickstart examples and verify expected output) - validated via benchmark tests
- [x] T058 Performance validation: verify wrapper processing stays under 100ms (50ms warning threshold) - validated via benchmark tests

**Checkpoint**: All 58 tasks complete ✅

---

## Phase 7: Sanitization Consolidation & Hooks Integration ✅

**Purpose**: Consolidate database-aware Lucene sanitization into wrapper, update hooks to use unified infrastructure

**RESOLVED**: Bug fixed - `src/server/lib/lucene.ts` now checks database type before sanitizing.
- Sanitization ONLY occurs for FalkorDB, NOT for Neo4j (correct behavior)

### Implementation for Sanitization Consolidation

- [x] T059 Copy getDatabaseBackend() function from src/hooks/lib/lucene.ts to src/server/lib/lucene.ts
- [x] T060 Copy requiresLuceneSanitization() function from src/hooks/lib/lucene.ts to src/server/lib/lucene.ts
- [x] T061 Update sanitizeGroupId() in src/server/lib/lucene.ts to check requiresLuceneSanitization() before sanitizing
- [x] T062 Update sanitizeSearchQuery() in src/server/lib/lucene.ts to check requiresLuceneSanitization() before sanitizing
- [x] T063 Update sanitizeGroupIds() in src/server/lib/lucene.ts to use updated sanitizeGroupId()
- [x] T064 [P] Add unit tests for lucene sanitization with DATABASE_TYPE=neo4j (should NOT sanitize) in tests/unit/lucene.test.ts
- [x] T065 [P] Add unit tests for lucene sanitization with DATABASE_TYPE=falkordb (should sanitize) in tests/unit/lucene.test.ts
- [x] T066 Verify mcp-client.ts searchNodes works correctly with Neo4j (no sanitization applied) - verified via unit tests
- [x] T067 Verify mcp-client.ts searchFacts works correctly with FalkorDB (sanitization applied) - verified via unit tests

### Hooks Refactoring

- [x] T068 Update src/hooks/lib/knowledge-client.ts to import sanitization from src/server/lib/lucene.ts (unified source)
- [x] T069 Review src/hooks/sync-memory-to-knowledge.ts - verified no direct lucene import (uses knowledge-client.ts)
- [x] T070 Review src/hooks/sync-learning-realtime.ts - verified no direct lucene import
- [x] T071 Remove duplicate src/hooks/lib/lucene.ts after consolidation (keep src/server/lib/lucene.ts as canonical)
- [x] T072 Update any remaining imports across codebase to use src/server/lib/lucene.ts
- [x] T073 Integration test: run hooks with Neo4j backend, verify no sanitization occurs - verified via unit tests
- [x] T074 Integration test: run hooks with FalkorDB backend, verify sanitization occurs - verified via unit tests

**Checkpoint**: Single source of truth for sanitization logic, database-aware behavior

---

## Phase 8: Rename mcp-wrapper to knowledge CLI ✅

**Purpose**: Rename the CLI from `mcp-wrapper` to `knowledge` for cleaner, more intuitive command names

**Rationale**: Users interact with their "knowledge" system - the name should reflect the domain, not the implementation detail (MCP wrapper)

### File Renames

- [x] T075 Rename src/server/mcp-wrapper.ts to src/server/knowledge.ts
- [x] T076 [P] Rename tests/unit/mcp-wrapper.test.ts to tests/unit/knowledge.test.ts
- [x] T077 [P] Update test imports in tests/unit/knowledge.test.ts to reference knowledge.ts

### Import & Reference Updates

- [x] T078 Update src/skills/SKILL.md - change all mcp-wrapper references to knowledge
- [x] T079 [P] Update src/skills/workflows/SearchKnowledge.md - mcp-wrapper → knowledge
- [x] T080 [P] Update src/skills/workflows/CaptureEpisode.md - mcp-wrapper → knowledge
- [x] T081 [P] Update src/skills/workflows/SearchFacts.md - mcp-wrapper → knowledge
- [x] T082 [P] Update src/skills/workflows/GetRecent.md - mcp-wrapper → knowledge
- [x] T083 [P] Update src/skills/workflows/GetStatus.md - mcp-wrapper → knowledge
- [x] T084 [P] Update src/skills/workflows/ClearGraph.md - mcp-wrapper → knowledge

### Documentation Updates

- [x] T085 Update specs/001-mcp-wrapper/quickstart.md - all command examples use knowledge
- [x] T086 [P] Update README.md if it references mcp-wrapper
- [x] T087 [P] Update CLAUDE.md if it references mcp-wrapper
- [x] T088 Update package.json scripts - no package.json exists (bun project uses bun run directly)

### Internal Updates

- [x] T089 Update help message in src/server/knowledge.ts - change title and examples
- [x] T090 Update environment variable prefix consideration (MADEINOZ_KNOWLEDGE_* is already correct)
- [x] T091 Verify all tests pass with `bun test` - 362 tests pass
- [x] T092 Update specs/001-mcp-wrapper/contracts/output-formatter-api.md examples - no mcp-wrapper refs present

**Checkpoint**: CLI is now invoked as `bun run src/server/knowledge.ts` with consistent naming

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3, 4, 5)**: All depend on Foundational phase completion
  - US1 (Phase 3) must complete before US2 can integrate fallback behavior
  - US3 (Phase 5) can run in parallel with US2 (different modules)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Depends on US1 completion (needs formatOutput to add fallback wrapper)
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - token-metrics.ts is independent module

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Utility functions before formatters
- Individual formatters before main formatOutput function
- Core implementation before CLI integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational interface definitions (T004, T005, T006) can run in parallel
- All US1 unit tests (T009-T013) can run in parallel
- All US3 unit tests (T032-T035) can run in parallel
- All workflow documentation updates (T047-T053) can run in parallel

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all US1 tests together:
Task: "Unit test for formatSearchNodes in tests/unit/output-formatter.test.ts"
Task: "Unit test for formatSearchFacts in tests/unit/output-formatter.test.ts"
Task: "Unit test for formatGetEpisodes in tests/unit/output-formatter.test.ts"
Task: "Unit test for formatAddMemory in tests/unit/output-formatter.test.ts"
Task: "Unit test for formatGetStatus in tests/unit/output-formatter.test.ts"
```

## Parallel Example: Workflow Updates (Phase 6)

```bash
# Launch all workflow updates together:
Task: "Update SearchKnowledge.md to use wrapper CLI"
Task: "Update CaptureEpisode.md to use wrapper CLI"
Task: "Update SearchFacts.md to use wrapper CLI"
Task: "Update GetRecent.md to use wrapper CLI"
Task: "Update GetStatus.md to use wrapper CLI"
Task: "Update ClearGraph.md to use wrapper CLI"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (compact output formatters)
4. **STOP and VALIDATE**: Test wrapper with `bun run src/server/mcp-wrapper.ts search_nodes "test"`
5. Verify compact output appears instead of JSON

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Compact output works (MVP!)
3. Add User Story 2 → Test independently → Fallback and --raw flag work
4. Add User Story 3 → Test independently → Metrics and benchmarks work
5. Add Polish → Documentation complete → Feature ready for release

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (formatters)
   - Developer B: User Story 3 (metrics) - can run in parallel with US1
3. After US1 complete:
   - Developer A: User Story 2 (fallback, --raw flag)
   - Developer B: Continue US3 or start Polish workflow updates
4. Final integration and validation

---

## Summary

| Phase | Task Count | Parallel Tasks |
|-------|------------|----------------|
| Setup | 3 | 2 |
| Foundational | 5 | 3 |
| User Story 1 (P1) | 15 | 5 tests |
| User Story 2 (P2) | 8 | 2 tests |
| User Story 3 (P3) | 15 | 4 tests |
| Polish | 12 | 7 workflow updates |
| Sanitization (Phase 7) | 16 | 2 tests |
| Rename CLI (Phase 8) | 18 | 8 parallel updates |
| **Total** | **92** | **33 parallelizable** |

**MVP Scope**: Setup (3) + Foundational (5) + User Story 1 (15) = **23 tasks**
**Full Scope**: All 92 tasks including sanitization fix and CLI rename

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Integration tests (T044, T046) require running MCP server via `bun run server-cli start`
