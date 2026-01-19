# Tasks: MkDocs Material Documentation Site

**Input**: Design documents from `/specs/002-mkdocs-documentation/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Not requested in specification. Using `mkdocs build --strict` for validation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Config**: `mkdocs.yml` at repository root
- **Docs**: `docs/` directory with hierarchical sections
- **Workflow**: `.github/workflows/docs.yml`
- **Assets**: `docs/assets/` for images and branding

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and directory structure

- [x] T001 Create documentation directory structure per contracts/directory-structure.md
- [x] T002 [P] Create mkdocs.yml configuration file per contracts/mkdocs-config.yml
- [x] T003 [P] Create .github/workflows/docs.yml per contracts/github-workflow.yml
- [x] T004 [P] Add site/ to .gitignore for build output

---

## Phase 2: Foundational (Assets & Core Files)

**Purpose**: Core infrastructure that MUST be complete before content migration

**⚠️ CRITICAL**: No content migration can begin until assets and structure are ready

- [x] T005 [P] Copy/create logo.png to docs/assets/logo.png
- [x] T006 [P] Create favicon.ico in docs/assets/favicon.ico
- [x] T007 [P] Move docs/assets/falkordb_ui.png to docs/assets/images/falkordb_ui.png
- [x] T008 Create docs/index.md homepage by merging README.md overview and docs/INDEX.md

**Checkpoint**: Foundation ready - content migration can now begin

---

## Phase 3: User Story 1 - Browse Documentation Online (Priority: P1) 🎯 MVP

**Goal**: Users can access comprehensive documentation on GitHub Pages with all content migrated and organized

**Independent Test**: Navigate to GitHub Pages URL and verify all 6+ sections are accessible with styled content

### Getting Started Section

- [x] T009 [P] [US1] Move docs/README.md to docs/getting-started/overview.md
- [x] T010 [P] [US1] Move docs/QUICK_REFERENCE.md to docs/getting-started/quick-reference.md

### Installation Section

- [x] T011 [P] [US1] Copy INSTALL.md to docs/installation/index.md (update internal links)
- [x] T012 [P] [US1] Move docs/installation.md to docs/installation/requirements.md
- [x] T013 [P] [US1] Copy VERIFY.md to docs/installation/verification.md

### Usage Section

- [x] T014 [P] [US1] Move docs/usage.md to docs/usage/basic-usage.md
- [x] T015 [P] [US1] Create docs/usage/advanced.md (extract advanced content from usage.md)

### Concepts Section

- [x] T016 [P] [US1] Extract architecture section from README.md to docs/concepts/architecture.md
- [x] T017 [P] [US1] Move docs/concepts.md to docs/concepts/knowledge-graph.md

### Troubleshooting Section

- [x] T018 [US1] Move docs/troubleshooting.md to docs/troubleshooting/common-issues.md

### Reference Section

- [x] T019 [P] [US1] Extract CLI reference from README.md to docs/reference/cli.md
- [x] T020 [P] [US1] Extract configuration from INSTALL.md to docs/reference/configuration.md
- [x] T021 [P] [US1] Move docs/OLLAMA-MODEL-GUIDE.md to docs/reference/model-guide.md
- [x] T022 [P] [US1] Move docs/MODEL-BENCHMARK-RESULTS.md to docs/reference/benchmarks.md

### Content Validation

- [x] T023 [US1] Update all internal links in migrated files to use new paths
- [x] T024 [US1] Update all image references to use docs/assets/images/ paths
- [x] T025 [US1] Add frontmatter (title, description) to all migrated pages
- [x] T026 [US1] Run mkdocs build --strict and fix any broken links

**Checkpoint**: User Story 1 complete - all documentation is migrated and accessible locally

---

## Phase 4: User Story 2 - Automatic Documentation Publishing (Priority: P2)

**Goal**: Documentation deploys automatically to GitHub Pages when changes are pushed to main

**Independent Test**: Push a documentation change to main branch and verify site updates within 5 minutes

- [x] T027 [US2] Verify .github/workflows/docs.yml is correctly configured (from T003)
- [ ] T028 [US2] Enable GitHub Pages in repository settings (Actions source) [MANUAL - GitHub UI]
- [ ] T029 [US2] Test workflow by pushing docs change to main branch [MANUAL - after merge]
- [ ] T030 [US2] Verify deployment completes and site is accessible at GitHub Pages URL [MANUAL - after merge]

**Checkpoint**: User Story 2 complete - automatic deployment pipeline is working

---

## Phase 5: User Story 3 - Find Information Quickly (Priority: P2)

**Goal**: Users can search documentation and find relevant pages by keyword

**Independent Test**: Search for "installation", "troubleshooting", "Neo4j" and verify relevant results appear

- [x] T031 [US3] Verify search plugin is enabled in mkdocs.yml (search plugin)
- [x] T032 [US3] Verify search.suggest and search.highlight features are enabled
- [x] T033 [US3] Test search functionality locally with mkdocs serve
- [x] T034 [US3] Verify search returns relevant results for key terms (installation, troubleshooting, Neo4j, FalkorDB)

**Checkpoint**: User Story 3 complete - search functionality is working and returns relevant results

---

## Phase 6: User Story 4 - Navigate Documentation Hierarchy (Priority: P3)

**Goal**: Users can navigate logically through documentation with clear structure and location awareness

**Independent Test**: Navigate through all 6 sections using only the navigation menu and verify intuitive hierarchy

- [x] T035 [US4] Verify navigation.sections feature shows section groupings
- [x] T036 [US4] Verify navigation.expand feature works for subsections
- [x] T037 [US4] Verify navigation.top provides scroll-to-top functionality
- [x] T038 [US4] Verify navigation.footer shows prev/next page links
- [x] T039 [US4] Test mobile navigation responsiveness
- [x] T040 [US4] Verify table of contents (toc) appears on pages with sections

**Checkpoint**: User Story 4 complete - navigation hierarchy is intuitive and functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final refinements affecting multiple user stories

- [x] T041 [P] Verify dark/light theme toggle works (SC-008)
- [x] T042 [P] Verify code blocks have syntax highlighting (SC-009)
- [x] T043 [P] Verify site loads within 3 seconds (SC-005)
- [x] T044 Clean up old documentation files that were moved (docs/INDEX.md, etc.)
- [x] T045 Update root README.md with link to documentation site
- [x] T046 Run final mkdocs build --strict validation
- [x] T047 Run quickstart.md validation workflow

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion
- **User Story 1 (Phase 3)**: Depends on Foundational - content migration
- **User Story 2 (Phase 4)**: Depends on Setup (workflow exists) - can run parallel to US1
- **User Story 3 (Phase 5)**: Depends on US1 (needs content for search)
- **User Story 4 (Phase 6)**: Depends on US1 (needs navigation structure)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - Core content migration
- **User Story 2 (P2)**: Can start after Setup (Phase 1) - Independent of content
- **User Story 3 (P2)**: Requires US1 complete - needs content to search
- **User Story 4 (P3)**: Requires US1 complete - needs navigation populated

### Within Each Phase

- Tasks marked [P] can run in parallel (different files)
- Tasks without [P] have sequential dependencies
- Validation tasks (T023-T026) must run after content migration

### Parallel Opportunities

**Phase 1 (Setup)**:
```
T002, T003, T004 can all run in parallel after T001
```

**Phase 2 (Foundational)**:
```
T005, T006, T007 can all run in parallel
```

**Phase 3 (US1 Content Migration)**:
```
All section migrations (T009-T022) can run in parallel
Then T023-T026 run sequentially for validation
```

---

## Parallel Example: Phase 3 Content Migration

```bash
# Launch all Getting Started tasks together:
Task: "Move docs/README.md to docs/getting-started/overview.md"
Task: "Move docs/QUICK_REFERENCE.md to docs/getting-started/quick-reference.md"

# Launch all Installation tasks together:
Task: "Copy INSTALL.md to docs/installation/index.md"
Task: "Move docs/installation.md to docs/installation/requirements.md"
Task: "Copy VERIFY.md to docs/installation/verification.md"

# Launch all Reference tasks together:
Task: "Extract CLI reference from README.md to docs/reference/cli.md"
Task: "Extract configuration from INSTALL.md to docs/reference/configuration.md"
Task: "Move docs/OLLAMA-MODEL-GUIDE.md to docs/reference/model-guide.md"
Task: "Move docs/MODEL-BENCHMARK-RESULTS.md to docs/reference/benchmarks.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T008)
3. Complete Phase 3: User Story 1 (T009-T026)
4. **STOP and VALIDATE**: Run `mkdocs serve` locally
5. Verify all documentation is accessible and links work

### Incremental Delivery

1. Setup + Foundational → Infrastructure ready
2. Add User Story 1 → Test locally → All content migrated (MVP!)
3. Add User Story 2 → Test deployment → Auto-publish working
4. Add User Story 3 → Test search → Search functional
5. Add User Story 4 → Test navigation → Full UX complete
6. Polish phase → Final validation → Production ready

### Recommended Order

Since this is a documentation project (not code), the recommended flow is:

1. **Phase 1-2**: Setup infrastructure (T001-T008)
2. **Phase 3**: Migrate all content (T009-T026) - **This is the main work**
3. **Phase 4**: Enable deployment (T027-T030)
4. **Phase 5-6**: Verify features work (T031-T040)
5. **Phase 7**: Final polish (T041-T047)

---

## Summary

| Phase | Tasks | Purpose |
|-------|-------|---------|
| Phase 1 | T001-T004 (4) | Setup infrastructure |
| Phase 2 | T005-T008 (4) | Core assets and homepage |
| Phase 3 | T009-T026 (18) | US1: Content migration 🎯 MVP |
| Phase 4 | T027-T030 (4) | US2: Auto-deploy |
| Phase 5 | T031-T034 (4) | US3: Search |
| Phase 6 | T035-T040 (6) | US4: Navigation |
| Phase 7 | T041-T047 (7) | Polish |
| **Total** | **47 tasks** | |

### Tasks by User Story

| Story | Tasks | Parallel |
|-------|-------|----------|
| Setup | 4 | 3 |
| Foundation | 4 | 3 |
| US1 (P1) | 18 | 14 |
| US2 (P2) | 4 | 0 |
| US3 (P2) | 4 | 0 |
| US4 (P3) | 6 | 0 |
| Polish | 7 | 3 |

### MVP Scope

**MVP = Phase 1 + Phase 2 + Phase 3 (User Story 1)**

- 26 tasks to reach MVP
- All documentation migrated and accessible locally
- Can deploy manually for review before enabling auto-deploy

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- No tests specified - using `mkdocs build --strict` for validation
- Commit after each phase or logical group of tasks
- Stop at any checkpoint to validate progress
