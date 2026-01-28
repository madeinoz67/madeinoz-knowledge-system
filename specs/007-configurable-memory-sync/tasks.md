# Tasks: Configurable Memory Sync

**Input**: Design documents from `/specs/007-configurable-memory-sync/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/sync-config.ts, quickstart.md

**Tests**: Not explicitly requested - tasks focus on implementation only.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, etc.)
- Exact file paths included in descriptions

## Path Conventions

Per Constitution Principle VII (Language Separation):
- **TypeScript code**: `src/` for implementation
- **Docker files**: `src/server/` for compose files
- **Documentation**: `docs/` for user-facing docs

---

## Phase 1: Setup

**Purpose**: No setup needed - project structure exists, dependencies installed.

*This phase is empty - proceed directly to Foundational phase.*

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T001 [P] Create sync configuration loader in `src/hooks/lib/sync-config.ts` implementing LoadSyncConfig function from contracts
- [x] T002 [P] Create anti-loop pattern module in `src/hooks/lib/anti-loop-patterns.ts` implementing CheckAntiLoop function with BUILTIN_ANTI_LOOP_PATTERNS

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Configure Memory Sync Sources (Priority: P1) 🎯 MVP

**Goal**: Users can enable/disable sync for LEARNING/ALGORITHM, LEARNING/SYSTEM, and RESEARCH directories via environment variables.

**Independent Test**: Modify `MADEINOZ_KNOWLEDGE_SYNC_LEARNING_ALGORITHM=false`, run sync, verify LEARNING/ALGORITHM files are not synced.

### Implementation for User Story 1

- [x] T003 [US1] Add configuration loading to `src/hooks/sync-memory-to-knowledge.ts` - import and call loadSyncConfig() at hook start
- [x] T004 [US1] Replace hardcoded SYNC_SOURCES constant in `src/hooks/sync-memory-to-knowledge.ts` with getEnabledSources(config) function call
- [x] T005 [US1] Add configuration validation and warning logs for invalid environment values in `src/hooks/lib/sync-config.ts`
- [x] T006 [US1] Add verbose logging option controlled by MADEINOZ_KNOWLEDGE_SYNC_VERBOSE in `src/hooks/sync-memory-to-knowledge.ts`

**Checkpoint**: User Story 1 complete - sync sources are now configurable

---

## Phase 4: User Story 2 - Prevent Knowledge Feedback Loops (Priority: P1)

**Goal**: System detects and excludes knowledge-derived content (query results, MCP tool output) from being re-synced.

**Independent Test**: Create a learning file containing "what do I know about", run sync, verify file is skipped with anti-loop reason.

### Implementation for User Story 2

- [x] T007 [US2] Import checkAntiLoop function into `src/hooks/sync-memory-to-knowledge.ts`
- [x] T008 [US2] Add anti-loop check before sync in syncFile() function in `src/hooks/sync-memory-to-knowledge.ts` - skip files that match patterns
- [x] T009 [US2] Add SyncDecision logging with reasonCode for skipped files in `src/hooks/sync-memory-to-knowledge.ts`
- [x] T010 [US2] Add custom exclude patterns support from MADEINOZ_KNOWLEDGE_SYNC_EXCLUDE_PATTERNS in `src/hooks/lib/anti-loop-patterns.ts`

**Checkpoint**: User Story 2 complete - knowledge loops are prevented

---

## Phase 4b: External Path Configuration (FR-020 to FR-022)

**Purpose**: Make sync source paths configurable via external JSON file instead of hardcoded values.

**Goal**: Users can customize which directories are synced without modifying code.

### Implementation

- [x] T010a [P] Create default sync sources configuration file at `config/sync-sources.json`
- [x] T010b Add loadSyncSources function to `src/hooks/lib/sync-config.ts` that loads from config file with fallback
- [x] T010c Update getEnabledSources to use loaded sources instead of hardcoded ALL_SYNC_SOURCES
- [x] T010d Add validation and warning logs for invalid sync-sources.json entries

**Checkpoint**: External path configuration complete - users can customize sync paths

---

## Phase 5: User Story 3 - Deprecate Realtime Sync Hook (Priority: P2)

**Goal**: Remove the realtime sync hook entirely, consolidating all sync into the main SessionStart hook.

**Independent Test**: Verify `src/hooks/sync-learning-realtime.ts` is deleted and system runs without errors.

### Implementation for User Story 3

- [x] T011 [US3] Delete the realtime sync hook file `src/hooks/sync-learning-realtime.ts`
- [x] T012 [US3] Remove any references to sync-learning-realtime from hook registration in `src/hooks/` if present
- [x] T013 [US3] Verify main sync hook in `src/hooks/sync-memory-to-knowledge.ts` handles all content that realtime hook previously processed

**Checkpoint**: User Story 3 complete - single consolidated sync hook

---

## Phase 6: User Story 5 - Production Docker Compose for Remote Systems (Priority: P2)

**Goal**: Standalone Docker Compose for deploying Neo4j + Graphiti MCP on remote servers without PAI infrastructure.

**Independent Test**: Deploy `docker-compose-production.yml` on a fresh server, verify services start and accept connections.

### Implementation for User Story 5

- [x] T014 [P] [US5] Create production Docker Compose file at `src/skills/server/docker-compose-production.yml` using native service names (neo4j, knowledge-mcp)
- [x] T015 [P] [US5] Create remote deployment documentation at `docs/installation/remote-deployment.md` with quickstart guide
- [x] T016 [US5] Add health checks and restart policies to `src/skills/server/docker-compose-production.yml`
- [x] T017 [US5] Add AI-friendly summary comment to `docs/installation/remote-deployment.md` per constitution Principle VIII

**Checkpoint**: User Story 5 complete - production deployment ready

---

## Phase 7: User Story 4 - View Sync Status and Configuration (Priority: P3)

**Goal**: Users can view current sync configuration and recent sync activity.

**Independent Test**: Run status command, verify it displays enabled sources and recent sync counts.

### Implementation for User Story 4

- [x] T018 [US4] Create sync status function in `src/hooks/lib/sync-status.ts` that reads config and sync state
- [x] T019 [US4] Add getSyncStatus export to `src/hooks/sync-memory-to-knowledge.ts` or create status CLI command
- [x] T020 [US4] Add recent sync activity tracking (count by decision type) to `src/hooks/lib/sync-state.ts` (already existed via getSyncStats)
- [x] T021 [US4] Format status output showing enabled sources, recent synced/skipped counts, and last sync timestamp

**Checkpoint**: User Story 4 complete - sync status visible

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, cleanup, and validation

- [x] T022 [P] Update CLAUDE.md with new environment variables and configuration options
- [x] T023 [P] Add inline documentation to `src/hooks/lib/sync-config.ts` explaining each configuration option (already included in file header)
- [ ] T024 Verify quickstart.md scenarios work end-to-end with production compose (deferred - requires live testing)
- [x] T025 Run `bun run typecheck` and `bun test` to verify no regressions
- [x] T026 Update CHANGELOG.md with feature summary

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Empty - proceed to Foundational
- **Foundational (Phase 2)**: No dependencies - can start immediately
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US1 (P1) and US2 (P1) can proceed in parallel after Foundational
  - US3 (P2) can start after US1 & US2 complete (needs consolidated hook)
  - US5 (P2) can start immediately after Foundational (independent of hook changes)
  - US4 (P3) depends on US1 (needs configuration to report)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

```
Foundational (T001-T002)
    │
    ├──→ US1 (T003-T006) ───┐
    │                       ├──→ US3 (T011-T013) ──→ US4 (T018-T021)
    ├──→ US2 (T007-T010) ───┘
    │
    └──→ US5 (T014-T017) [Independent]
```

- **User Story 1 (P1)**: Depends on Foundational only
- **User Story 2 (P1)**: Depends on Foundational only - can run parallel with US1
- **User Story 3 (P2)**: Depends on US1 & US2 (needs both features in main hook before deleting realtime hook)
- **User Story 4 (P3)**: Depends on US1 (needs config to report status)
- **User Story 5 (P2)**: Depends on Foundational only - fully independent of hook changes

### Parallel Opportunities

**Within Foundational Phase:**
```bash
# T001 and T002 can run in parallel (different files)
Task: "Create sync configuration loader in src/hooks/lib/sync-config.ts"
Task: "Create anti-loop pattern module in src/hooks/lib/anti-loop-patterns.ts"
```

**Within User Story 5:**
```bash
# T014 and T015 can run in parallel (different files)
Task: "Create production Docker Compose file at src/server/docker-compose-production.yml"
Task: "Create remote deployment documentation at docs/remote-deployment.md"
```

**Cross-Story Parallelism:**
```bash
# After Foundational, these can run in parallel:
Task: US1 implementation (T003-T006)
Task: US5 implementation (T014-T017)
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2 Only)

1. Complete Phase 2: Foundational (T001-T002)
2. Complete Phase 3: User Story 1 (T003-T006)
3. Complete Phase 4: User Story 2 (T007-T010)
4. **STOP and VALIDATE**: Test configuration and anti-loop detection independently
5. Merge/deploy if ready - system now has configurable, loop-safe sync

### Incremental Delivery

1. **MVP**: Foundational + US1 + US2 → Configurable, safe sync
2. **Cleanup**: + US3 → Single consolidated hook
3. **Remote**: + US5 → Production deployment capability
4. **Visibility**: + US4 → Status reporting
5. **Polish**: Final documentation and testing

### Recommended Execution Order

| Order | Phase | Tasks | Parallelizable With |
|-------|-------|-------|---------------------|
| 1 | Foundational | T001-T002 | T001 ∥ T002 |
| 2 | US1 | T003-T006 | US5 (T014-T017) |
| 3 | US2 | T007-T010 | US5 (T014-T017) |
| 4 | US3 | T011-T013 | - |
| 5 | US5 | T014-T017 | Can start at step 2 |
| 6 | US4 | T018-T021 | - |
| 7 | Polish | T022-T026 | T022 ∥ T023 |

---

## Notes

- [P] tasks = different files, no dependencies - safe to run in parallel
- [Story] label maps task to specific user story for traceability
- US1 and US2 both modify `sync-memory-to-knowledge.ts` but touch different sections
- US5 is fully independent - can be done in parallel with hook work
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
