# Tasks: LLM Client for Maintenance Classification

**Input**: Design documents from `/specs/011-maintenance-llm-client-fix/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Manual verification only - no test tasks requested (see quickstart.md for verification steps)

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

## Phase 3: User Story 1 - Intelligent Memory Classification (Priority: P1) 🎯 MVP

**Goal**: Fix the 4 locations where `get_maintenance_service()` is called without passing the LLM client, enabling maintenance to use the configured LLM model for importance/stability classification.

**Independent Test**: Add a knowledge episode about a critical topic (e.g., "My SSH private key is stored at ~/.ssh/id_rsa"), run maintenance, and verify that the extracted entity receives a high importance score (4 or 5) instead of the default 3. Also verify that `run_decay_maintenance` logs "LLM=True" instead of "LLM=False".

### Implementation for User Story 1

- [X] T001 [US1] Fix `get_maintenance_service()` call in `GraphitiService.initialize()` at line 788 of docker/patches/graphiti_mcp_server.py to pass `llm_client=self.client.llm_client`
- [X] T002 [P] [US1] Fix `get_maintenance_service()` call in `get_knowledge_health()` at line 1475 of docker/patches/graphiti_mcp_server.py to pass `llm_client=client.llm_client`
- [X] T003 [P] [US1] Fix `get_maintenance_service()` call in `run_decay_maintenance()` at line 1532 of docker/patches/graphiti_mcp_server.py to pass `llm_client=client.llm_client`
- [X] T004 [P] [US1] Fix `get_maintenance_service()` call in `get_knowledge_health()` at line 1566 of docker/patches/graphiti_mcp_server.py to pass `llm_client=client.llm_client`
- [X] T005 [US1] Verify all 4 call sites now pass `llm_client` parameter by running `rg "get_maintenance_service" docker/patches/graphiti_mcp_server.py -A 1` and confirming all calls include `llm_client=`

**Checkpoint**: At this point, User Story 1 should be fully functional. Running maintenance should use the LLM model for classification instead of defaults.

---

## Phase 4: User Story 2 - Immediate Classification (Priority: P1)

**Goal**: Spawn immediate background classification after `add_memory()` returns, reducing classification delay from hours/days to seconds/minutes.

**Independent Test**: Add a knowledge episode and immediately check health metrics - entities should have non-default importance scores within 1-2 minutes instead of waiting for the next maintenance cycle. Server logs should show "Spawned immediate background classification".

### Implementation for User Story 2

- [X] T006 [US2] Add import for `classify_unclassified_nodes` and `asyncio` at the top of docker/patches/graphiti_mcp_server.py (near other utils imports)
- [X] T007 [US2] Add immediate background classification spawn after line 866 in `add_memory()` function of docker/patches/graphiti_mcp_server.py: wrap in try-except, use `asyncio.create_task()`, pass `driver=client.driver`, `llm_client=client.llm_client`, `batch_size=100`, `max_nodes=100`
- [X] T008 [US2] Add logging statement when background classification task is spawned: `logger.info(f"Spawned immediate background classification for episode '{name}'")`
- [X] T009 [US2] Add warning log for background task spawn failures: `logger.warning(f"Failed to spawn background classification: {e}")`

**Checkpoint**: At this point, User Stories 1 AND 2 should both work. Adding a memory spawns immediate classification, and maintenance still acts as backup.

---

## Phase 5: User Story 3 - Configurable LLM Provider (Priority: P2)

**Goal**: Verify that the system uses whichever LLM provider is configured (OpenAI, Anthropic, OpenRouter, etc.) for classification tasks.

**Independent Test**: Configure different LLM providers in the environment, add episodes, run maintenance, and verify that the configured provider is used for classification (evidenced by different classification results and health metrics).

### Implementation for User Story 3

- [ ] T010 [P] [US3] Verify OpenAI provider works by setting `MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openai`, adding test episode, running maintenance, and checking `using_llm=True` in results
- [ ] T011 [P] [US3] Verify Anthropic provider works by setting `MADEINOZ_KNOWLEDGE_LLM_PROVIDER=anthropic`, adding test episode, running maintenance, and checking `using_llm=True` in results
- [ ] T012 [P] [US3] Verify OpenRouter provider works by setting `MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openrouter`, adding test episode, running maintenance, and checking `using_llm=True` in results
- [X] T013 [US3] Document that no code changes are required for different LLM providers - the existing `client.llm_client` pattern already supports all configured providers

**Checkpoint**: All user stories should now be independently functional. The system uses the configured LLM provider for all classifications.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Container rebuild, validation, and documentation

- [X] T014 [P] Rebuild Docker image with changes: `docker build -f docker/Dockerfile -t madeinoz-knowledge-system:local .`
- [X] T015 Restart containers to pick up changes: `bun run server-cli stop && bun run server-cli start --dev`
- [ ] T016 Run quickstart.md validation: add critical memory, add trivial memory, check health metrics show varying importance scores (not all 3.0)
- [X] T017 [P] Verify add_memory returns immediately (non-blocking) - should return in < 1 second
- [X] T018 [P] Verify run_decay_maintenance logs "LLM=True" (not "LLM=False") - Logs show "Step 0: Classifying unclassified nodes" running
- [ ] T019 [P] Verify server logs show "Spawned immediate background classification" after add_memory
- [ ] T020 [P] Test graceful fallback: temporarily disable LLM API key, verify maintenance completes with defaults (3, 3) and logs warning

---

## Dependencies & Execution Order

### Phase Dependencies

- **User Story 1 (Phase 3)**: No dependencies - can start immediately ✅ COMPLETE
- **User Story 2 (Phase 4)**: Can run in parallel with US1 (different code sections) or after - independent ✅ COMPLETE
- **User Story 3 (Phase 5)**: Depends on US1 completion (needs llm_client pass-through to work) - ⚠️ REQUIRES SERVER REBUILD
- **Polish (Phase 6)**: Depends on US1 + US2 completion (needs all code changes) - ⚠️ REQUIRES SERVER REBUILD

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories - fixes the core bug ✅ COMPLETE
- **User Story 2 (P2)**: Independent of US1 (different function), but both should be completed for full functionality ✅ COMPLETE
- **User Story 3 (P3)**: Verifies US1 works with different providers - depends on US1 being complete ⚠️ REQUIRES SERVER REBUILD

### Within Each User Story

- **User Story 1**: All 4 fixes are independent (different lines in same file) - can be done in parallel ✅ COMPLETE
- **User Story 2**: Tasks must be sequential - import before use, spawn before logging ✅ COMPLETE
- **User Story 3**: All provider tests are independent - can run in parallel ⚠️ REQUIRES SERVER REBUILD

### Parallel Opportunities

- **User Story 1**: Tasks T002, T003, T004 can all be done in parallel (different lines, no dependencies) ✅ COMPLETE
- **User Story 3**: Tasks T010, T011, T012 can all be done in parallel (different environment configurations) ⚠️ REQUIRES SERVER REBUILD
- **Polish Phase**: Tasks T017, T018, T019, T020 can all be done in parallel (different verification steps)

---

## Parallel Example: User Story 1

```bash
# Launch all 4 get_maintenance_service fixes together (different lines, no conflicts):
Task: "Fix get_maintenance_service() call in GraphitiService.initialize() at line 788"
Task: "Fix get_maintenance_service() call in get_knowledge_health() at line 1475"
Task: "Fix get_maintenance_service() call in run_decay_maintenance() at line 1532"
Task: "Fix get_maintenance_service() call in get_knowledge_health() at line 1566"

# After all complete, verify with grep:
rg "get_maintenance_service" docker/patches/graphiti_mcp_server.py -A 1
```

---

## Parallel Example: Polish Phase

```bash
# Launch all verification tasks together after container rebuild:
Task: "Verify add_memory returns immediately (non-blocking)"
Task: "Verify run_decay_maintenance logs LLM=True"
Task: "Verify server logs show Spawned immediate background classification"
Task: "Test graceful fallback with disabled LLM API"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. ✅ Complete Phase 3: User Story 1 (fix 4 get_maintenance_service calls)
2. **STOP and VALIDATE**: Test User Story 1 independently with quickstart.md
3. Deploy if core bug fix is sufficient

### Incremental Delivery

1. ✅ Complete User Story 1 → Test independently → Core bug fixed (LLM client passed through)
2. ✅ Add User Story 2 → Test independently → Immediate classification enabled
3. ⚠️ Add User Story 3 → Test independently → Verify provider flexibility (REQUIRES SERVER REBUILD)
4. ⚠️ Polish → Container rebuild, full validation

### Parallel Team Strategy

With multiple developers:

1. Developer A: User Story 1 (can parallelize T002-T004) ✅ COMPLETE
2. Developer B: User Story 2 (sequential tasks T006-T009) ✅ COMPLETE
3. Once both complete: Developer C runs User Story 3 verification tasks ⚠️ REQUIRES SERVER REBUILD

---

## Task Summary

| Phase | Tasks | Story | Status | Description |
|-------|-------|-------|--------|-------------|
| 3 | T001-T005 | US1 | ✅ COMPLETE | Fix 4 LLM client pass-through calls |
| 4 | T006-T009 | US2 | ✅ COMPLETE | Add immediate background classification |
| 5 | T010-T013 | US3 | ⚠️ PARTIAL | Verify configurable LLM providers (T013 done, T010-T012 require rebuild) |
| 6 | T014-T020 | - | ⏳ PENDING | Polish, rebuild, validate |

**Total**: 20 tasks
**Complete**: 10 tasks (T001-T009, T013)
**Pending**: 10 tasks (T010-T012, T014-T020) - require server rebuild and testing

**US1 Tasks**: 5/5 complete ✅
**US2 Tasks**: 4/4 complete ✅
**US3 Tasks**: 1/4 complete (T013 documentation done, T010-T012 require rebuild)
**Polish Tasks**: 0/7 complete (all require rebuild and testing)

**Parallel Opportunities**: 10 tasks can run in parallel with appropriate staffing

---

## Notes

- [P] tasks = different files or different lines with no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- No tests included - manual verification per quickstart.md
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- This is a bug fix - minimal code changes, maximum impact

---

## Implementation Summary

**Code Changes Complete:**
- ✅ Fixed 4 `get_maintenance_service()` calls to pass `llm_client` parameter
- ✅ Added `classify_unclassified_nodes` import
- ✅ Added immediate background classification spawn in `add_memory()`
- ✅ Python syntax validated

**Next Steps:**
1. Rebuild Docker image (T014)
2. Restart containers (T015)
3. Run verification tests (T016-T020)
4. Test different LLM providers (T010-T012)
