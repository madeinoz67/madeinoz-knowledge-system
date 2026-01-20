# Implementation Tasks: Fix Sync Hook Protocol Mismatch

**Feature**: 003-fix-issue-2
**Branch**: `003-fix-issue-2`
**Date**: 2026-01-20

## Overview

This document contains actionable implementation tasks organized by user story. Each user story represents an independently testable increment that delivers value. Tasks are numbered sequentially and follow the checklist format for execution tracking.

**Task Count**: 24 tasks across 5 phases
**MVP Scope**: Phase 1-3 (User Story 1 - automatic sync)
**Parallel Opportunities**: 5 tasks marked with [P] can run in parallel

---

## Phase 1: Setup

**Goal**: Prepare development environment and verify prerequisites

### Tasks

- [X] T001 Verify MCP server is running at http://localhost:8000 using bun run status
- [X] T002 Verify database backend (Neo4j or FalkorDB) is accessible via containers
- [X] T003 Set MADEINOZ_KNOWLEDGE_DB environment variable to 'neo4j' or 'falkorodb'

---

## Phase 2: Foundational

**Goal**: Implement core MCP client protocol that all user stories depend on

### Tasks

- [X] T004 Rewrite src/hooks/lib/knowledge-client.ts to use HTTP POST protocol instead of SSE GET
- [X] T005 Implement session initialization in src/hooks/lib/knowledge-client.ts with Mcp-Session-Id header extraction
- [X] T006 Implement SSE response body parsing in src/hooks/lib/knowledge-client.ts to extract data: lines
- [X] T007 Add database type detection in src/hooks/lib/knowledge-client.ts reading MADEINOZ_KNOWLEDGE_DB env var
- [X] T008 Integrate lucene.ts sanitization utilities in src/hooks/lib/knowledge-client.ts for conditional escaping
- [X] T009 Implement exponential backoff retry logic in src/hooks/lib/knowledge-client.ts for transient failures
- [X] T010 Update src/hooks/sync-memory-to-knowledge.ts health check to use HTTP POST instead of SSE GET

---

## Phase 3: User Story 1 - Sync Memory Files to Knowledge Graph (P1)

**Story Goal**: Automatically sync memory files to knowledge graph on SessionStart

**Independent Test**: Start MCP server, place test file in ~/.claude/MEMORY/LEARNING/ALGORITHM/, run sync hook, verify content appears in knowledge graph search

**Acceptance Criteria**:
- New memory files are successfully added to knowledge graph
- Previously synced files are skipped (not duplicated)
- MCP server unavailability triggers retry with graceful degradation
- YAML frontmatter metadata is preserved in episodes

### Tasks

- [X] T011 [P] [US1] Implement addEpisode() function in src/hooks/lib/knowledge-client.ts with JSON-RPC tools/call request
- [X] T012 [P] [US1] Add episode body truncation to 5000 characters in src/hooks/lib/knowledge-client.ts
- [X] T013 [P] [US1] Add episode name truncation to 200 characters in src/hooks/lib/knowledge-client.ts
- [X] T014 [P] [US1] Implement group_id sanitization using lucene.ts utilities in src/hooks/lib/knowledge-client.ts
- [X] T015 [US1] Update waitForMcpServer() in src/hooks/sync-memory-to-knowledge.ts to use new health check
- [ ] T016 [US1] Test sync with MCP server running: create test file, run sync, verify episode added
- [ ] T017 [US1] Test incremental sync: run sync twice, verify second run skips already-synced file
- [ ] T018 [US1] Test graceful degradation: stop MCP server, run sync, verify non-blocking failure

---

## Phase 4: User Story 2 - Manual Sync Operations (P2)

**Story Goal**: Enable manual sync with --all, --dry-run, and --verbose flags

**Independent Test**: Run CLI with various flags, verify output messages match expected behavior, check --dry-run makes no API calls

**Acceptance Criteria**:
- --dry-run lists files without making API calls
- --all re-syncs all files regardless of sync state
- --verbose shows detailed progress including retries and health status
- Default behavior syncs only new/modified files

### Tasks

- [X] T019 [P] [US2] Verify --dry-run flag bypasses addEpisode() calls in src/hooks/sync-memory-to-knowledge.ts
- [X] T020 [P] [US2] Verify --all flag clears syncedPaths check in src/hooks/sync-memory-to-knowledge.ts
- [X] T021 [US2] Add sync statistics logging (synced, failed, skipped) to src/hooks/sync-memory-to-knowledge.ts
- [X] T022 [US2] Add detailed error/warning logging in src/hooks/sync-memory-to-knowledge.ts when --verbose flag set
- [ ] T023 [US2] Test --dry-run: run with flag, verify no API calls made, files listed only
- [ ] T024 [US2] Test --all: run with flag, verify all files re-synced regardless of sync state
- [ ] T025 [US2] Test --verbose: run with flag, verify detailed progress messages shown

---

## Phase 5: User Story 3 - Health Check and Monitoring (P3)

**Story Goal**: Verify MCP server health before sync operations with clear feedback

**Independent Test**: Start sync hook with server offline, observe retry behavior, confirm appropriate error message displayed

**Acceptance Criteria**:
- Server offline triggers connection retries with exponential backoff
- Running server results in successful connection and sync operations
- Server becoming available during retries allows sync to proceed

### Tasks

- [ ] T026 [US3] Test health check with server offline: run sync, verify retry messages
- [ ] T027 [US3] Test health check recovery: start server during retries, verify sync proceeds
- [ ] T028 [US3] Verify health check timeout is 5 seconds when server is running

---

## Phase 6: Polish & Cross-Cutting Concerns

**Goal**: Final validation, edge case handling, and documentation

### Tasks

- [ ] T029 [P] Test special character handling: create file with hyphenated identifier (e.g., "apt-28"), verify sync succeeds
- [ ] T030 [P] Test database type switching: sync with neo4j, then sync with falkorodb, verify both work
- [ ] T031 [P] Test invalid MADEINOZ_KNOWLEDGE_DB: set invalid value, verify validation error thrown
- [ ] T032 [P] Test concurrent sync: run multiple sync operations simultaneously, verify no race conditions
- [ ] T033 [P] Test large file handling: create file over 5000 characters, verify truncation works
- [ ] T034 [P] Test malformed YAML: create file with invalid frontmatter, verify graceful handling
- [X] T035 Run typecheck: bun build src/hooks/lib/knowledge-client.ts --verify no compilation errors
- [X] T036 Run build: bun build src/hooks/sync-memory-to-knowledge.ts --verify successful compilation

---

## Dependencies

### User Story Completion Order

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational - MCP Client Protocol)
    ↓
Phase 3 (US1 - Automatic Sync) ← MVP SCOPE
    ↓
Phase 4 (US2 - Manual Sync Operations)
    ↓
Phase 5 (US3 - Health Check & Monitoring)
    ↓
Phase 6 (Polish)
```

**Critical Path**: T001-T010 must complete before any user story tasks can begin.

**Story Dependencies**:
- US2 and US3 depend on US1 (all use the same MCP client)
- US2 and US3 are independent of each other (can run in parallel)

---

## Parallel Execution Examples

### Within Phase 3 (US1)

Tasks T011-T014 can run in parallel (they modify different parts of the same function):
```bash
# Parallel execution
Task T011: Implement addEpisode() core logic
Task T012: Add body truncation
Task T013: Add name truncation
Task T014: Add group_id sanitization
```

### Within Phase 6 (Polish)

All test tasks (T029-T036) can run in parallel:
```bash
# Parallel execution
Task T029: Test special characters
Task T030: Test database switching
Task T031: Test invalid env var
Task T032: Test concurrent sync
Task T033: Test large files
Task T034: Test malformed YAML
Task T035: Run typecheck
Task T036: Run build
```

---

## Implementation Strategy

### MVP First (Recommended)

**MVP Scope**: Phase 1-3 (Tasks T001-T018)
- Delivers automatic sync functionality (P1 user story)
- Fixes critical bug blocking Knowledge sync
- 18 tasks, estimated 2-3 hours

**Post-MVP**: Phase 4-6 (Tasks T019-T036)
- Manual sync operations with flags (P2)
- Enhanced health monitoring (P3)
- Edge case handling and validation
- 18 tasks, estimated 1-2 hours

### Incremental Delivery

Each phase can be independently tested and validated:
1. **After Phase 2**: MCP client protocol works, can make successful API calls
2. **After Phase 3**: Automatic sync fully functional, MVP complete
3. **After Phase 4**: Manual sync controls available
4. **After Phase 5**: Health monitoring enhanced
5. **After Phase 6**: All edge cases handled, production ready

---

## Testing Strategy

### Manual Testing Required

This feature requires manual testing with live MCP server:
- Unit tests cannot verify HTTP POST protocol correctness
- Integration tests require running containers
- See `quickstart.md` for detailed test scenarios

### Test Scenarios

1. **Basic Sync** (US1): Create test file, run sync, verify in knowledge graph
2. **Incremental Sync** (US1): Run sync twice, verify no duplicates
3. **Graceful Degradation** (US1): Stop server, run sync, verify non-blocking
4. **Dry Run** (US2): Run with --dry-run, verify no API calls
5. **Force Sync** (US2): Run with --all, verify all files re-synced
6. **Verbose Logging** (US2): Run with --verbose, verify detailed output
7. **Health Check** (US3): Run with server offline, verify retries
8. **Special Characters** (Polish): Test with hyphenated CTI identifiers
9. **Database Switching** (Polish): Test with both neo4j and falkorodb

---

## Format Validation

✅ **All tasks follow the checklist format**:
- Checkbox: `- [ ]` prefix
- Task ID: Sequential numbering (T001-T036)
- Parallel marker: `[P]` for parallelizable tasks
- Story label: `[US1]`, `[US2]`, `[US3]` for user story phases
- Description: Clear action with file path

✅ **File paths specified** for all implementation tasks
✅ **Independent test criteria** defined for each user story
✅ **Dependencies documented** in completion order diagram
