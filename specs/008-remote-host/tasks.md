# Tasks: Knowledge CLI Remote Host Support

**Input**: Design documents from `/specs/008-remote-host/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/cli-options.md

**Tests**: Not requested - implementation tasks only.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

**For this project (Madeinoz Knowledge System):**
- **TypeScript code**: `src/` for implementation
- See Constitution Principle VII (Language Separation)

---

## Phase 1: Setup

**Purpose**: No setup needed - extending existing project

*No tasks - existing project structure is sufficient*

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T001 Add ConnectionConfig interface to src/skills/tools/knowledge-cli.ts
- [ ] T002 Add getConnectionConfig() function skeleton to src/skills/tools/knowledge-cli.ts
- [ ] T003 Add validatePort() helper function to src/skills/tools/knowledge-cli.ts
- [ ] T004 Add detectProtocol() and stripProtocol() helpers to src/skills/tools/knowledge-cli.ts
- [ ] T005 Add buildMcpUrl() helper function to src/skills/tools/knowledge-cli.ts

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Connect to Remote Knowledge Server (Priority: P1) MVP

**Goal**: Enable users to connect to remote Knowledge MCP servers via --host and --port CLI flags

**Independent Test**: Run `knowledge-cli.ts --host <remote-host> --port <port> get_status` and verify it connects to the remote server instead of localhost

### Implementation for User Story 1

- [ ] T006 [US1] Extend CLIFlags interface with host and port properties in src/skills/tools/knowledge-cli.ts
- [ ] T007 [US1] Add --host flag parsing to parseFlags() in src/skills/tools/knowledge-cli.ts
- [ ] T008 [US1] Add --port flag parsing to parseFlags() in src/skills/tools/knowledge-cli.ts
- [ ] T009 [US1] Implement port validation (1-65535) with clear error message in src/skills/tools/knowledge-cli.ts
- [ ] T010 [US1] Implement protocol detection from host prefix (http://, https://) in src/skills/tools/knowledge-cli.ts
- [ ] T011 [US1] Implement URL construction in getConnectionConfig() in src/skills/tools/knowledge-cli.ts
- [ ] T012 [US1] Update all createMCPClient() calls to pass configured baseURL in src/skills/tools/knowledge-cli.ts
- [ ] T013 [US1] Verify default behavior unchanged (localhost:8000) when no flags in src/skills/tools/knowledge-cli.ts

**Checkpoint**: User Story 1 complete - users can connect to remote servers via CLI flags

---

## Phase 4: User Story 2 - Environment Variable Configuration (Priority: P2)

**Goal**: Enable users to configure remote host settings via environment variables for script-friendly configuration

**Independent Test**: Set `MADEINOZ_KNOWLEDGE_HOST` and `MADEINOZ_KNOWLEDGE_PORT` environment variables and run commands without flags, verifying the configured values are used

### Implementation for User Story 2

- [ ] T014 [US2] Add MADEINOZ_KNOWLEDGE_HOST env var reading to getConnectionConfig() in src/skills/tools/knowledge-cli.ts
- [ ] T015 [US2] Add MADEINOZ_KNOWLEDGE_PORT env var reading to getConnectionConfig() in src/skills/tools/knowledge-cli.ts
- [ ] T016 [US2] Implement priority logic: CLI flags > env vars > defaults in src/skills/tools/knowledge-cli.ts
- [ ] T017 [US2] Verify env var port is validated same as CLI flag in src/skills/tools/knowledge-cli.ts

**Checkpoint**: User Story 2 complete - users can configure via env vars, flags take precedence

---

## Phase 5: User Story 3 - Connection Verification and Diagnostics (Priority: P3)

**Goal**: Provide clear connection verification and diagnostic information for troubleshooting

**Independent Test**: Run `health` command with various valid and invalid host configurations and verify appropriate success/error messages

### Implementation for User Story 3

- [ ] T018 [US3] Extend CLIFlags interface with insecure and verbose properties in src/skills/tools/knowledge-cli.ts
- [ ] T019 [US3] Add --insecure flag parsing to parseFlags() in src/skills/tools/knowledge-cli.ts
- [ ] T020 [US3] Add --verbose flag parsing to parseFlags() in src/skills/tools/knowledge-cli.ts
- [ ] T021 [US3] Implement TLS validation skip when --insecure flag set in src/skills/tools/knowledge-cli.ts
- [ ] T022 [US3] Update cmdHealth() to show connected host:port in output in src/skills/tools/knowledge-cli.ts
- [ ] T023 [US3] Update cmdHealth() to show protocol (HTTP/HTTPS) in src/skills/tools/knowledge-cli.ts
- [ ] T024 [US3] Update cmdHealth() to show TLS validation status in src/skills/tools/knowledge-cli.ts
- [ ] T025 [US3] Wrap client calls with try/catch for connection error handling in src/skills/tools/knowledge-cli.ts
- [ ] T026 [US3] Format connection errors to include hostname and port in src/skills/tools/knowledge-cli.ts
- [ ] T027 [US3] Add verbose output for DNS resolution and timing when --verbose set in src/skills/tools/knowledge-cli.ts
- [ ] T028 [US3] Display warning when --insecure flag is used in src/skills/tools/knowledge-cli.ts

**Checkpoint**: User Story 3 complete - users get clear diagnostics and connection verification

---

## Phase 6: Polish & Documentation (FR-017)

**Purpose**: Update documentation per Constitution Principle VIII (Dual-Audience Documentation)

- [ ] T029 [P] Update printHelp() with Connection Options section in src/skills/tools/knowledge-cli.ts
- [ ] T030 [P] Update printHelp() with new Environment Variables section in src/skills/tools/knowledge-cli.ts
- [ ] T031 [P] Update printHelp() with remote connection examples in src/skills/tools/knowledge-cli.ts
- [ ] T032 [P] Add AI-friendly summary comment to docs/index.md
- [ ] T033 [P] Update Quick Reference Card in docs/index.md with new CLI options
- [ ] T034 [P] Add remote connection examples to docs/getting-started/overview.md
- [ ] T035 [P] Add environment variables table to docs/reference/configuration.md
- [ ] T036 Run manual verification using quickstart.md scenarios

**Checkpoint**: All documentation updated per Constitution Principle VIII

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No tasks - existing project
- **Foundational (Phase 2)**: T001-T005 must complete before user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2 - implements core remote connection
- **User Story 2 (Phase 4)**: Depends on Phase 2 - can run parallel to US1
- **User Story 3 (Phase 5)**: Depends on Phase 2 - can run parallel to US1/US2
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Foundational only - no dependencies on other stories
- **User Story 2 (P2)**: Depends on Foundational only - independent of US1
- **User Story 3 (P3)**: Depends on Foundational only - independent of US1/US2

### Within Each User Story

- Flag parsing before configuration logic
- Configuration logic before client calls
- Core implementation before polish

### Parallel Opportunities

- **Foundational (Phase 2)**: T001-T005 are sequential (same file, building on each other)
- **User Stories**: US1, US2, US3 can theoretically run in parallel after Phase 2
  - However, all modify same file (knowledge-cli.ts) so sequential is safer
- **Polish (Phase 6)**: T029-T035 marked [P] can run in parallel (different files)

---

## Parallel Example: Phase 6 Documentation

```bash
# Launch all documentation tasks in parallel (different files):
Task: "Update printHelp() with Connection Options section in src/skills/tools/knowledge-cli.ts"
Task: "Add AI-friendly summary comment to docs/index.md"
Task: "Add remote connection examples to docs/getting-started/overview.md"
Task: "Add environment variables table to docs/reference/configuration.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 2: Foundational (T001-T005)
2. Complete Phase 3: User Story 1 (T006-T013)
3. **STOP and VALIDATE**: Test with `--host example.com --port 9000 get_status`
4. Deploy/demo if ready - users can now connect to remote servers

### Incremental Delivery

1. Complete Foundational → Foundation ready
2. Add User Story 1 → Test independently → Users can use --host/--port (MVP!)
3. Add User Story 2 → Test independently → Users can use env vars
4. Add User Story 3 → Test independently → Users get diagnostics
5. Complete Polish → Full documentation

### Recommended Execution Order

Since all user stories modify the same file (knowledge-cli.ts), recommended order:

1. **T001-T005**: Foundational helpers
2. **T006-T013**: User Story 1 (--host, --port flags)
3. **T014-T017**: User Story 2 (env vars)
4. **T018-T028**: User Story 3 (diagnostics)
5. **T029-T036**: Polish (help text, docs)

---

## Summary

| Metric | Count |
|--------|-------|
| **Total Tasks** | 36 |
| **Phase 2 (Foundational)** | 5 |
| **User Story 1 (P1)** | 8 |
| **User Story 2 (P2)** | 4 |
| **User Story 3 (P3)** | 11 |
| **Polish** | 8 |
| **Parallel Opportunities** | 7 (Phase 6 documentation) |

| User Story | Independent Test |
|------------|------------------|
| US1 (P1) | `--host example.com --port 9000 get_status` |
| US2 (P2) | `export MADEINOZ_KNOWLEDGE_HOST=example.com && get_status` |
| US3 (P3) | `health` command with valid/invalid hosts |

**MVP Scope**: Complete Phase 2 + Phase 3 (User Story 1) = 13 tasks

---

## Notes

- All user stories modify `src/skills/tools/knowledge-cli.ts` - execute sequentially to avoid conflicts
- [P] tasks in Phase 6 can truly run in parallel (different files)
- Each user story has clear independent test criteria
- Stop at any checkpoint to validate story independently
- Commit after each task or logical group
