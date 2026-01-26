# Tasks: Documentation and Docker Compose Updates

**Input**: Design documents from `/specs/001-docs-compose-updates/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md (available)
**Tests**: No code tests requested - manual verification only

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

**Note**: This is a documentation and configuration update feature. No source code changes, no automated tests. All verification is manual review and container deployment testing.

---

## Phase 1: Setup (Preparation)

**Purpose**: Create feature branch and prepare for documentation updates

- [X] T001 Create and checkout feature branch 001-docs-compose-updates from main
- [X] T002 Verify branch matches specs/001-docs-compose-updates directory

---

## Phase 2: User Story 1 - Documentation Cleanup (Priority: P1) 🎯 MVP

**Goal**: Remove ALL Lucene references from documentation so users see clear, backend-agnostic information.

**Independent Test**: Review all documentation files for Lucene references using `codanna mcp search_documents query:"lucene"` or `rg -i "lucene" docs/ *.md` and verify zero results.

### Audit for Lucene References

- [X] T003 [P] [US1] Search all .md files for Lucene references using `rg -i "lucene" --type md` in repository root
- [X] T004 [P] [US1] Search compose files for Lucene comments in src/skills/server/*.yml
- [X] T005 [US1] Document all Lucene references found in checklist notes

### Documentation Content Removal

- [X] T006 [P] [US1] Remove "Lucene Query Errors with Hyphenated Groups" section from INSTALL.md
- [X] T007 [P] [US1] Remove "Test 4: Verify Lucene sanitization" from INSTALL.md verification steps
- [X] T008 [P] [US1] Remove lucene.ts references from required files check in INSTALL.md
- [X] T009 [P] [US1] Remove inline code references to lucene.ts from INSTALL.md

### Compose File Header Cleanup

- [X] T010 [P] [US1] Remove "no RediSearch/Lucene escaping needed" comments from src/skills/server/docker-compose-neo4j.yml header
- [X] T011 [P] [US1] Remove "no RediSearch/Lucene escaping needed" comments from src/skills/server/docker-compose-falkordb.yml header
- [X] T012 [P] [US1] Simplify patch descriptions referencing Lucene in src/skills/server/podman-compose-neo4j.yml header
- [X] T013 [P] [US1] Simplify patch descriptions referencing Lucene in src/skills/server/podman-compose-falkordb.yml header

### Additional Compose Files Review

- [X] T014 [P] [US1] Review and clean src/skills/server/docker-compose.yml for Lucene references
- [X] T015 [P] [US1] Review and clean src/skills/server/docker-compose-test.yml for Lucene references
- [X] T016 [P] [US1] Review and clean src/skills/server/podman-compose.yml for Lucene references
- [X] T017 [P] [US1] Review and clean docker/docker-compose-*.yml files for Lucene references

**Checkpoint**: All Lucene references removed from documentation and compose files. Verify with `rg -i "lucene" --type md` and `rg -i "lucene" src/skills/server/*.yml`

---

## Phase 3: User Story 2 - Improved Benchmark Documentation (Priority: P2)

**Goal**: Reorganize benchmark sections with real performance data at top, testing results at bottom, and add explicit LLM model recommendations.

**Independent Test**: Review INSTALL.md benchmark section to verify: (1) Real benchmarks prominently at top, (2) LLM model recommendations present with "best for price/performance" and "models to avoid" sections, (3) Testing methodology at bottom.

### Benchmark Reorganization

- [X] T018 [US2] Create new "Performance Benchmarks" section near top of INSTALL.md (before provider selection)
- [X] T019 [US2] Move existing LLM Provider Comparison table to new Performance Benchmarks section
- [X] T020 [US2] Move existing Embedding Options table to new Performance Benchmarks section

### LLM Model Recommendations

- [X] T021 [P] [US2] Add "Recommended LLM Models" subsection in Performance Benchmarks with clear guidance
- [X] T022 [P] [US2] Add "Best for Price/Performance" models list with reasoning (OpenRouter GPT-4o Mini)
- [X] T023 [P] [US2] Add "Models to Avoid" section with explicit warnings and reasoning (Llama/Mistral variants)
- [X] T024 [US2] Reorganize testing methodology and results to bottom of benchmark section

### Cross-Reference Updates

- [X] T025 [P] [US2] Update README.md to reference new Performance Benchmarks section
- [X] T026 [P] [US2] Update CLAUDE.md to reference new Performance Benchmarks section if applicable (N/A - no applicable references)

**Checkpoint**: Benchmark sections reorganized with real performance data at top, LLM recommendations clear, testing methodology at bottom.

---

## Phase 4: User Story 3 - Docker Compose Image Updates (Priority: P1)

**Goal**: Update all Docker/Podman Compose files to reference ghcr.io/madeinoz67/madeinoz-knowledge-system:latest

**Independent Test**: Run `docker compose -f <file> config` for each compose file and verify image references in output show `ghcr.io/madeinoz67/madeinoz-knowledge-system:latest`.

### Primary Compose Files (High Priority)

- [X] T027 [P] [US3] Update graphiti-mcp service image in src/skills/server/docker-compose-neo4j.yml to ghcr.io/madeinoz67/madeinoz-knowledge-system:latest
- [X] T028 [P] [US3] Update graphiti-mcp service image in src/skills/server/docker-compose-falkordb.yml to ghcr.io/madeinoz67/madeinoz-knowledge-system:latest
- [X] T029 [P] [US3] Update graphiti-mcp service image in src/skills/server/podman-compose-neo4j.yml to ghcr.io/madeinoz67/madeinoz-knowledge-system:latest
- [X] T030 [P] [US3] Update graphiti-mcp service image in src/skills/server/podman-compose-falkordb.yml to ghcr.io/madeinoz67/madeinoz-knowledge-system:latest

### Additional Compose Files Review

- [X] T031 [P] [US3] Review and update image references in src/skills/server/docker-compose.yml if needed
- [X] T032 [P] [US3] Review and update image references in src/skills/server/docker-compose-test.yml if needed
- [X] T033 [P] [US3] Review and update image references in src/skills/server/podman-compose.yml if needed
- [X] T034 [P] [US3] Review and update image references in docker/docker-compose-*.yml files if needed

### Scripts and Documentation Review

- [X] T035 [P] [US3] Search all .sh scripts for image references using `rg "image:" scripts/` (if scripts directory exists)
- [X] T036 [P] [US3] Review and update any image references in src/skills/server/entrypoint.sh comments
- [X] T037 [US3] Verify documentation correctly references ghcr.io/madeinoz67/madeinoz-knowledge-system:latest

### Compose File Validation

- [X] T038 [P] [US3] Validate docker-compose-neo4j.yml syntax with `docker compose -f src/skills/server/docker-compose-neo4j.yml config`
- [X] T039 [P] [US3] Validate docker-compose-falkordb.yml syntax with `docker compose -f src/skills/server/docker-compose-falkordb.yml config`
- [X] T040 [P] [US3] Validate podman-compose-neo4j.yml syntax with `podman-compose -f src/skills/server/podman-compose-neo4j.yml config`
- [X] T041 [P] [US3] Validate podman-compose-falkordb.yml syntax with `podman-compose -f src/skills/server/podman-compose-falkordb.yml config`

**Checkpoint**: All compose files validated with correct GHCR image references.

---

## Phase 5: Polish & Verification

**Purpose**: Final review and validation of all changes

- [X] T042 [P] Verify all Lucene references removed with `rg -i "lucene" --type md && rg -i "lucene" src/skills/server/*.yml`
- [X] T043 [P] Verify benchmark section organization in INSTALL.md (performance top, methodology bottom)
- [X] T044 [P] Verify LLM model recommendations present (best for price/performance, models to avoid)
- [X] T045 [P] Verify all compose files reference ghcr.io/madeinoz67/madeinoz-knowledge-system:latest with `rg "image:" src/skills/server/*.yml`
-[X] T046 Test container deployment with `docker compose -f src/skills/server/docker-compose-neo4j.yml up --dry-run` or manual validation
- [X] T047 [P] Review CLAUDE.md for any remaining technical inaccuracies after changes
- [X] T048 [P] Review README.md for any remaining technical inaccuracies after changes

### Additional Podman Compose Updates

- [X] T049 [P] [US3] Update all podman-compose files with ghcr.io/madeinoz67/madeinoz-knowledge-system:latest image reference

**Files updated by T049:**
- `src/skills/server/podman-compose-neo4j.yml`
- `src/skills/server/podman-compose-falkordb.yml`
- `src/skills/server/podman-compose.yml`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **User Story 1 (Phase 2)**: Depends on branch creation - can start immediately after Phase 1
- **User Story 2 (Phase 3)**: Depends on US1 completion (benchmark reorganization in INSTALL.md)
- **User Story 3 (Phase 4)**: No dependencies on other stories - can run in parallel with US1/US2
- **Polish (Phase 5)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Independent - no dependencies on other stories
- **User Story 2 (P2)**: Partially depends on US1 (both modify INSTALL.md) - should coordinate or sequence US1 → US2
- **User Story 3 (P1)**: Independent - no dependencies on other stories

### Parallel Opportunities

- **US1 Documentation Tasks (T006-T009)**: Can run in parallel (different sections of INSTALL.md)
- **US1 Compose Headers (T010-T013)**: Can run in parallel (different files)
- **US1 Additional Compose Review (T014-T017)**: Can run in parallel (different files)
- **US2 LLM Recommendations (T021-T023)**: Can run in parallel (different subsections)
- **US2 Cross-References (T025-T026)**: Can run in parallel (different files)
- **US3 Primary Compose Updates (T027-T030)**: Can run in parallel (different files)
- **US3 Additional Compose Review (T031-T034)**: Can run in parallel (different files)
- **US3 Validation (T038-T041)**: Can run in parallel (different files)
- **US1 + US3**: Can run in parallel (US1 is documentation, US3 is compose files - minimal overlap)

### Recommended Execution Strategy

#### MVP Scope (P1 User Stories Only)
1. Complete Phase 1: Setup
2. Complete Phase 2: User Story 1 (Documentation Cleanup)
3. Complete Phase 4: User Story 3 (Docker Compose Updates)
4. Skip Phase 3: User Story 2 (P2 - can add later)
5. Complete Phase 5: Polish & Verification

#### Full Implementation (Priority Order)
1. Phase 1: Setup → Foundation ready
2. Phase 2: US1 (Documentation Cleanup) → Test independently
3. Phase 4: US3 (Docker Compose Updates) → Test independently (can parallelize with US1 after initial audit)
4. Phase 3: US2 (Benchmark Improvements) → Test independently (modifies INSTALL.md, coordinate after US1)
5. Phase 5: Polish & Verification → Final validation

#### Parallel Team Strategy
With multiple developers:
1. Complete Setup together
2. Split immediately:
   - Developer A: User Story 1 (Documentation Cleanup)
   - Developer B: User Story 3 (Docker Compose Updates)
3. After US1 completes:
   - Developer A: User Story 2 (Benchmark Improvements)
4. Join for Phase 5: Verification

---

## Parallel Example: User Story 1

```bash
# Launch all compose file header cleanup tasks together:
Task T010: docker-compose-neo4j.yml
Task T011: docker-compose-falkordb.yml
Task T012: podman-compose-neo4j.yml
Task T013: podman-compose-falkordb.yml
```

---

## Parallel Example: User Story 3

```bash
# Launch all primary compose file image updates together:
Task T027: docker-compose-neo4j.yml
Task T028: docker-compose-falkordb.yml
Task T029: podman-compose-neo4j.yml
Task030: podman-compose-falkordb.yml

# Launch all validation tasks together:
Task T038: docker-compose-neo4j.yml config
Task T039: docker-compose-falkordb.yml config
Task T040: podman-compose-neo4j.yml config
Task T041: podman-compose-falkordb.yml config
```

---

## Implementation Strategy

### MVP First (P1 User Stories Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: User Story 1 (T003-T017)
3. Complete Phase 4: User Story 3 (T027-T041)
4. **STOP and VALIDATE**:
   - Verify no Lucene references: `rg -i "lucene" --type md && rg -i "lucene" src/skills/server/*.yml`
   - Verify all compose files use GHCR: `rg "image:" src/skills/server/*.yml`
   - Test container deployment: `docker compose -f src/skills/server/docker-compose-neo4j.yml config`
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + US1 (Documentation Cleanup) → Documentation improved, commit and push
2. Add US3 (Docker Compose Updates) → Deployable, commit and push (MVP!)
3. Add US2 (Benchmark Improvements) → Enhanced documentation, commit and push
4. Polish & Verification → Final validation, ready to merge

### Notes

- [P] tasks = different files or sections, no dependencies
- [Story] label maps task to specific user story for traceability
- US1 and US3 can run in parallel (minimal file overlap)
- US2 should wait for US1 completion (both modify INSTALL.md)
- Commit after each task or logical group
- Manual verification only (no automated tests for this feature)
