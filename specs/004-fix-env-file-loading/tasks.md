# Implementation Tasks: Fix Environment File Loading

**Feature**: 004-fix-env-file-loading
**Branch**: `004-fix-env-file-loading`
**Date**: 2026-01-20

## Overview

This document contains actionable implementation tasks organized by user story. Each user story represents an independently testable increment that delivers value. Tasks are numbered sequentially and follow the checklist format for execution tracking.

**Task Count**: 32 tasks across 6 phases
**MVP Scope**: Phase 1-4 (User Story 1 - fix env_file loading bug)
**Parallel Opportunities**: 9 tasks marked with [P] can run in parallel

---

## Phase 1: Setup

**Goal**: Create missing compose file and prepare for renaming

### Tasks

- [X] T001 Create podman-compose-neo4j.yml in src/server/ based on docker-compose-neo4j.yml structure with Neo4j services
- [X] T002 [P] Update env_file path in docker-compose-neo4j.yml from `${PAI_DIR:-~/.claude}/.env` to `${PAI_DIR:-$HOME/.claude}/.env` (fix tilde expansion)
- [X] T003 [P] Update env_file path in docker-compose.yml from `${PAI_DIR:-~/.claude}/.env` to `${PAI_DIR:-$HOME/.claude}/.env` (fix tilde expansion)
- [X] T004 [P] Update env_file path in podman-compose.yml from `${PAI_DIR}/.env` to `${PAI_DIR:-$HOME/.claude}/.env` (fix tilde expansion, add fallback)
- [X] T005 [P] Update env_file path in newly created podman-compose-neo4j.yml to use `${PAI_DIR:-$HOME/.claude}/.env` (correct syntax from start)
- [X] T006 [P] Rename docker-compose.yml to docker-compose-falkordb.yml using git mv to preserve history
- [X] T007 [P] Rename podman-compose.yml to podman-compose-falkordb.yml using git mv to preserve history

---

## Phase 2: Foundational

**Goal**: Update all file references in codebase after compose file renaming

### Tasks

- [X] T008 Update references to docker-compose.yml in src/server/test-model-combinations.ts to docker-compose-falkordb.yml (NO CHANGES - test files reference docker-compose-neo4j.yml, not docker-compose.yml)
- [X] T009 Update references to docker-compose.yml in src/server/test-grok-llms-mcp.ts to docker-compose-falkordb.yml (NO CHANGES - test files reference docker-compose-neo4j.yml, not docker-compose.yml)
- [X] T010 Update references to docker-compose.yml in src/server/test-all-llms-mcp.ts to docker-compose-falkordb.yml (NO CHANGES - test files reference docker-compose-neo4j.yml, not docker-compose.yml)
- [X] T011 Update compose file table in README.md with new filenames (docker-compose-falkordb.yml, podman-compose-falkordb.yml, podman-compose-neo4j.yml)
- [X] T012 Update compose file references in docs/installation/index.md to use new filenames
- [X] T013 Update compose file references in docs/reference/cli.md to use new filenames
- [X] T014 Update compose file references in VERIFY.md to use new filenames
- [X] T015 Update compose file references in INSTALL.md to use new filenames
- [X] T016 Update .claude/CLAUDE.md compose file paths with new filenames

---

## Phase 3: User Story 1 - Docker Compose Loads Environment Variables (P1)

**Story Goal**: Fix the env_file loading bug so Docker Compose automatically loads API keys from PAI .env file

**Independent Test**: Configure ~/.claude/.env with API keys, run docker compose -f src/server/docker-compose-neo4j.yml up -d, check container logs to confirm no "variable not set" warnings, verify MCP server logs show configured LLM/embedder clients

**Acceptance Criteria**:
- All 4 compose files use `${PAI_DIR:-$HOME/.claude}/.env` path ✅ VERIFIED
- No "variable not set" warnings appear in container logs (MANUAL TEST REQUIRED)
- Environment variables are accessible inside containers (MANUAL TEST REQUIRED)
- PAI_DIR environment variable works correctly when set (MANUAL TEST REQUIRED)
- Services start with defaults when .env is missing (MANUAL TEST REQUIRED)

### Tasks

- [ ] T017 [US1] Test docker-compose-neo4j.yml: start containers, verify no warnings, check env vars in container
- [ ] T018 [US1] Test docker-compose-falkordb.yml: start containers, verify no warnings, check env vars in container
- [ ] T019 [US1] Test podman-compose-falkordb.yml with Podman: start containers, verify no warnings, check env vars
- [ ] T020 [US1] Test podman-compose-neo4j.yml with Podman: start containers, verify no warnings, check env vars
- [ ] T021 [US1] Test PAI_DIR variable: export PAI_DIR, start containers, verify correct .env is loaded
- [ ] T022 [US1] Test graceful degradation: remove .env, start containers, verify defaults are used, no crash

---

## Phase 4: User Story 2 - Clear Documentation of Environment Configuration (P2)

**Story Goal**: Provide clear documentation explaining how environment variables are loaded from .env files

**Independent Test**: Review documentation for clarity and completeness, follow documentation instructions to configure environment, verify documented behavior matches actual system behavior

**Acceptance Criteria**:
- Documentation explains where to place .env file and what variables to configure
- Troubleshooting documentation has clear steps for "variable not set" warnings
- Documentation explains how variable expansion (${PAI_DIR:-$HOME/.claude}) works
- Documentation explains which compose file to use for each runtime/backend combination

### Tasks

- [ ] T023 [P] [US2] Create docs/getting-started/environment-configuration.md with detailed .env file setup guide
- [ ] T024 [P] [US2] Create docs/getting-started/troubleshooting/env-file-issues.md with troubleshooting steps
- [ ] T025 [P] [US2] Create docs/concepts/container-configuration.md explaining all 4 compose files and when to use each
- [ ] T026 [US2] Update README.md with breaking change notice about compose file renaming
- [ ] T027 [US2] Add compose file selection guide to README.md (Docker vs Podman, Neo4j vs FalkorDB decision matrix)

---

## Phase 5: User Story 3 - Validation and Error Messaging (P3)

**Story Goal**: Provide clear error messages when environment configuration is invalid or missing

**Independent Test**: Intentionally misconfigure .env file (invalid format), start Docker Compose services, verify helpful error messages appear in logs

**Acceptance Criteria**:
- Malformed .env syntax shows clear warning message
- Missing API keys show helpful error message with configuration instructions
- Incorrect .env file path shows expected file location

### Tasks

- [ ] T028 [US3] Test malformed .env: create file with quotes around values, start containers, verify error message
- [ ] T029 [US3] Test missing API keys: create .env without required keys, start containers, verify helpful error
- [ ] T030 [US3] Test incorrect .env path: set PAI_DIR to non-existent directory, verify error shows expected location
- [ ] T031 [US3] Document error messages in docs/getting-started/troubleshooting/env-file-issues.md

---

## Phase 6: Polish & Cross-Cutting Concerns

**Goal**: Final validation, edge case handling, and documentation verification

### Tasks

- [ ] T032 [P] Verify all 4 compose files exist and have correct env_file path: grep env_file src/server/*compose*.yml
- [ ] T033 [P] Verify no remaining references to old filenames: grep -r "docker-compose\.yml\|podman-compose\.yml" src/ docs/
- [ ] T034 [P] Run typecheck: bun run typecheck and verify no errors
- [ ] T035 [P] Test with Windows-style line endings: create .env with CRLF, verify it loads correctly
- [ ] T036 [P] Test with Unicode values: create .env with multi-byte characters, verify it loads correctly
- [ ] T037 Test with very long environment variable values (>4096 chars): create .env with long value, verify it loads
- [ ] T038 Verify all success criteria from spec.md are met
- [ ] T039 Update CHANGELOG.md with entry for this fix (v1.2.6)

---

## Dependencies

### User Story Completion Order

```
Phase 1 (Setup - rename and create files)
    ↓
Phase 2 (Foundational - update all references)
    ↓
Phase 3 (US1 - Fix env_file loading bug) ← MVP SCOPE
    ↓
Phase 4 (US2 - Documentation)
    ↓
Phase 5 (US3 - Error messaging)
    ↓
Phase 6 (Polish)
```

**Critical Path**: T001-T007 (file creation and renaming) must complete before T008-T016 (reference updates).

**Story Dependencies**:
- US2 and US3 depend on US1 (env_file fix must work before documenting/error handling)
- US2 and US3 are independent of each other (can run in parallel)

---

## Parallel Execution Examples

### Within Phase 1 (Setup)

Tasks T002-T005 can run in parallel (env_file fixes in different files):
```bash
# Parallel execution
Task T002: Fix docker-compose-neo4j.yml
Task T003: Fix docker-compose.yml
Task T004: Fix podman-compose.yml
Task T005: Fix podman-compose-neo4j.yml
```

Tasks T006-T007 can run in parallel (file renames):
```bash
# Parallel execution
Task T006: Rename docker-compose.yml → docker-compose-falkordb.yml
Task T007: Rename podman-compose.yml → podman-compose-falkordb.yml
```

### Within Phase 4 (US2 - Documentation)

Tasks T023-T025 can run in parallel (creating separate documentation files):
```bash
# Parallel execution
Task T023: Create environment-configuration.md
Task T024: Create env-file-issues.md
Task T025: Create container-configuration.md
```

### Within Phase 6 (Polish)

All documentation and validation tasks can run in parallel:
```bash
# Parallel execution
Task T032: Verify compose files exist
Task T033: Verify no old filename references
Task T034: Run typecheck
Task T035: Test CRLF line endings
Task T036: Test Unicode values
```

---

## Implementation Strategy

### MVP First (Recommended)

**MVP Scope**: Phase 1-3 (Tasks T001-T022)
- Delivers the core bug fix (tilde expansion)
- Creates missing podman-compose-neo4j.yml
- Renames compose files for clarity
- 22 tasks, estimated 2-3 hours

**Post-MVP**: Phase 4-6 (Tasks T023-T039)
- Clear documentation (P2)
- Error messaging (P3)
- Edge case handling and validation
- 17 tasks, estimated 1-2 hours

### Incremental Delivery

Each phase can be independently tested and validated:
1. **After Phase 1**: All compose files exist with correct env_file syntax
2. **After Phase 2**: All file references updated, breaking change complete
3. **After Phase 3**: Core bug fixed, MVP complete, users can configure automatically
4. **After Phase 4**: Documentation complete, users can self-service troubleshoot
5. **After Phase 5**: Error messaging enhanced, better debugging experience
6. **After Phase 6**: All edge cases handled, production ready

---

## Testing Strategy

### Manual Testing Required

This feature requires manual testing with live containers:
- No automated tests can verify Docker Compose env_file behavior
- Integration tests require running Docker/Podman
- See quickstart.md for detailed test scenarios

### Test Scenarios

1. **Basic env_file loading** (US1): Create .env with API keys, start containers, verify vars loaded
2. **Tilde fix verification** (US1): Verify $HOME expands, ~ does not expand
3. **All 4 compose files** (US1): Test docker-compose-falkordb.yml, docker-compose-neo4j.yml, podman-compose-falkordb.yml, podman-compose-neo4j.yml
4. **PAI_DIR override** (US1): Set PAI_DIR, verify it takes precedence
5. **Graceful degradation** (US1): Remove .env, verify defaults used
6. **Documentation clarity** (US2): Follow docs, verify they work
7. **Error messages** (US3): Test malformed .env, missing keys, bad path
8. **Edge cases** (Polish): CRLF line endings, Unicode, long values

---

## Format Validation

✅ **All tasks follow the checklist format**:
- Checkbox: `- [ ]` prefix
- Task ID: Sequential numbering (T001-T039)
- Parallel marker: `[P]` for parallelizable tasks
- Story label: `[US1]`, `[US2]`, `[US3]` for user story phases
- Description: Clear action with file path

✅ **File paths specified** for all implementation tasks
✅ **Independent test criteria** defined for each user story
✅ **Dependencies documented** in completion order diagram
