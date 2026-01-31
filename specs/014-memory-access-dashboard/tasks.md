# Tasks: Memory Access Patterns Dashboard

**Input**: Design documents from `/specs/014-memory-access-dashboard/`
**Prerequisites**: plan.md, spec.md, data-model.md, research.md, quickstart.md

**Tests**: Manual verification in Grafana UI (no automated tests - per plan.md)

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, etc.)
- Include exact file paths in descriptions

## Path Conventions

**For this feature:**
- **Dashboard**: `config/monitoring/grafana/dashboards/memory-access-dashboard.json`
- **Documentation**: `docs/reference/observability.md`

---

## Phase 1: Setup

**Purpose**: Create dashboard skeleton with metadata and shared configuration

- [x] T001 Create dashboard JSON skeleton with metadata in config/monitoring/grafana/dashboards/memory-access-dashboard.json
- [x] T002 Add dashboard annotations and links configuration in config/monitoring/grafana/dashboards/memory-access-dashboard.json
- [x] T003 Configure time range picker (default 24h) and auto-refresh (30s) in config/monitoring/grafana/dashboards/memory-access-dashboard.json

**Checkpoint**: Dashboard accessible in Grafana but with no panels

---

## Phase 2: Foundational (Header Stats)

**Purpose**: Add overview stat panels that provide context for all user stories

**⚠️ CRITICAL**: These panels appear at the top and provide quick overview metrics

- [x] T004 Add Panel 1: Total Access Count stat (x=0, y=0, w=6, h=4) in config/monitoring/grafana/dashboards/memory-access-dashboard.json
- [x] T005 Add Panel 2: Access Rate stat (x=6, y=0, w=6, h=4) in config/monitoring/grafana/dashboards/memory-access-dashboard.json

**Checkpoint**: Header row shows total access count and current rate

---

## Phase 3: User Story 1 - View Access Distribution by Importance (Priority: P1) 🎯 MVP

**Goal**: Display pie chart showing access counts by importance level (CRITICAL, HIGH, MEDIUM, LOW)

**Independent Test**: Load dashboard → View "Access by Importance" panel → Verify pie chart shows 4 segments with labels and percentages

### Implementation for User Story 1

- [x] T006 [US1] Add Panel 5: Access by Importance pie chart (x=0, y=4, w=12, h=8) in config/monitoring/grafana/dashboards/memory-access-dashboard.json
- [x] T007 [US1] Configure query with max_over_time() wrapper for restart resilience in config/monitoring/grafana/dashboards/memory-access-dashboard.json
- [x] T008 [US1] Configure legend with table format, right placement, values and percent in config/monitoring/grafana/dashboards/memory-access-dashboard.json

**Checkpoint**: US1 complete - importance distribution visible and responsive to time range

---

## Phase 4: User Story 2 - View Access Distribution by Lifecycle State (Priority: P1)

**Goal**: Display pie chart showing access counts by lifecycle state (ACTIVE, STABLE, DORMANT, ARCHIVED)

**Independent Test**: Load dashboard → View "Access by State" panel → Verify pie chart shows 4 segments with labels and percentages

### Implementation for User Story 2

- [x] T009 [US2] Add Panel 6: Access by State pie chart (x=12, y=4, w=12, h=8) in config/monitoring/grafana/dashboards/memory-access-dashboard.json
- [x] T010 [US2] Configure query with max_over_time() wrapper for restart resilience in config/monitoring/grafana/dashboards/memory-access-dashboard.json
- [x] T011 [US2] Configure legend with table format, right placement, values and percent in config/monitoring/grafana/dashboards/memory-access-dashboard.json

**Checkpoint**: US2 complete - state distribution visible and responsive to time range

---

## Phase 5: User Story 3 - Monitor Access Rate Over Time (Priority: P2)

**Goal**: Display time-series chart showing memory access rates over time

**Independent Test**: Load dashboard → View "Access Rate Over Time" panel → Verify line chart shows rate data with time range responsiveness

### Implementation for User Story 3

- [x] T012 [US3] Add Panel 7: Access Rate Over Time timeseries (x=0, y=12, w=12, h=8) in config/monitoring/grafana/dashboards/memory-access-dashboard.json
- [x] T013 [US3] Configure rate() query with 5m interval in config/monitoring/grafana/dashboards/memory-access-dashboard.json
- [x] T014 [US3] Configure smooth line with fill opacity 20, legend with last/mean in config/monitoring/grafana/dashboards/memory-access-dashboard.json

**Checkpoint**: US3 complete - access rate trends visible over time

---

## Phase 6: User Story 4 - Analyze Memory Age Distribution (Priority: P2)

**Goal**: Display heatmap showing distribution of days since last access

**Independent Test**: Load dashboard → View "Age Distribution" panel → Verify heatmap shows memory counts in time buckets (1d, 1w, 1m, 3m, 6m, 1y+)

### Implementation for User Story 4

- [x] T015 [US4] Add Panel 8: Age Distribution heatmap (x=12, y=12, w=12, h=8) in config/monitoring/grafana/dashboards/memory-access-dashboard.json
- [x] T016 [US4] Configure histogram bucket query for days_since_last_access in config/monitoring/grafana/dashboards/memory-access-dashboard.json
- [x] T017 [US4] Configure Oranges color scheme and heatmap format in config/monitoring/grafana/dashboards/memory-access-dashboard.json

**Checkpoint**: US4 complete - age distribution visible as heatmap

---

## Phase 7: User Story 5 - Track Memory Reactivations (Priority: P2)

**Goal**: Display stat panels showing reactivation counts from DORMANT and ARCHIVED states

**Independent Test**: Load dashboard → View reactivation panels → Verify counts with color thresholds (green/yellow/red)

### Implementation for User Story 5

- [x] T018 [US5] Add Panel 3: Reactivations (Dormant) stat (x=12, y=0, w=6, h=4) in config/monitoring/grafana/dashboards/memory-access-dashboard.json
- [x] T019 [US5] Configure increase() query with from_state="DORMANT" filter in config/monitoring/grafana/dashboards/memory-access-dashboard.json
- [x] T020 [US5] Configure thresholds: green=0, yellow=5, red=20 in config/monitoring/grafana/dashboards/memory-access-dashboard.json
- [x] T021 [US5] Add Panel 4: Reactivations (Archived) stat (x=18, y=0, w=6, h=4) in config/monitoring/grafana/dashboards/memory-access-dashboard.json
- [x] T022 [US5] Configure increase() query with from_state="ARCHIVED" filter in config/monitoring/grafana/dashboards/memory-access-dashboard.json
- [x] T023 [US5] Configure thresholds: green=0, yellow=3, red=10 in config/monitoring/grafana/dashboards/memory-access-dashboard.json

**Checkpoint**: US5 complete - reactivation tracking visible with alert thresholds

---

## Phase 8: User Story 6 - Correlate Access Patterns with Decay Scores (Priority: P3)

**Goal**: Display dual-axis time series comparing access rate with decay score

**Independent Test**: Load dashboard → View correlation panel → Verify both access rate (left axis) and decay score (right axis) displayed

### Implementation for User Story 6

- [x] T024 [US6] Add Panel 9: Access vs Decay Correlation timeseries (x=0, y=20, w=24, h=8) in config/monitoring/grafana/dashboards/memory-access-dashboard.json
- [x] T025 [US6] Configure Query A: rate(knowledge_memory_access_total[5m]) on left axis in config/monitoring/grafana/dashboards/memory-access-dashboard.json
- [x] T026 [US6] Configure Query B: knowledge_decay_score_avg on right axis in config/monitoring/grafana/dashboards/memory-access-dashboard.json
- [x] T027 [US6] Configure dual-axis display and legend with last/mean values in config/monitoring/grafana/dashboards/memory-access-dashboard.json

**Checkpoint**: US6 complete - correlation analysis available

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Finalize dashboard and update documentation

- [x] T028 Validate all panel IDs are unique (1-9) in config/monitoring/grafana/dashboards/memory-access-dashboard.json
- [x] T029 Validate grid positions don't overlap in config/monitoring/grafana/dashboards/memory-access-dashboard.json
- [x] T030 Add dashboard to observability documentation in docs/reference/observability.md
- [x] T031 Run quickstart.md validation - verify all described functionality works
- [x] T032 Verify dashboard loads in Grafana with all panels rendering correctly

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup (dashboard skeleton must exist)
- **User Stories (Phases 3-8)**: All depend on Setup (Phase 1) completion
  - US1 and US2 (P1) should complete first
  - US3, US4, US5 (P2) can proceed after P1 stories
  - US6 (P3) should be last (depends on access rate panel concept from US3)
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

| Story | Priority | Dependencies | Notes |
|-------|----------|--------------|-------|
| US1 | P1 | Phase 1 only | Can start immediately after setup |
| US2 | P1 | Phase 1 only | Can start immediately after setup |
| US3 | P2 | Phase 1 only | Can start after P1 stories |
| US4 | P2 | Phase 1 only | Can start after P1 stories |
| US5 | P2 | Phase 1 only | Can start after P1 stories |
| US6 | P3 | Phase 1 only | Depends conceptually on US3 (similar query pattern) |

### Within Each User Story

Since all tasks modify the same JSON file, they must be executed sequentially within each story.

---

## Parallel Opportunities

**Limited parallelism** due to single-file implementation:

- Phase 1 tasks (T001-T003): Sequential (same file)
- Phase 2 tasks (T004-T005): Sequential (same file)
- **User Stories can be developed on separate branches** and merged:
  - Branch A: US1 + US2 (P1 stories together)
  - Branch B: US3 + US4 (P2 time series stories)
  - Branch C: US5 (P2 reactivation stats)
  - Branch D: US6 (P3 correlation)
- Polish tasks (T028-T032): Sequential

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational header stats (T004-T005)
3. Complete Phase 3: User Story 1 (T006-T008)
4. **STOP and VALIDATE**: Verify importance distribution works
5. Dashboard is usable with single panel

### Incremental Delivery

1. Setup + Foundational → Dashboard skeleton with header stats
2. Add US1 (P1) → Importance distribution ✓
3. Add US2 (P1) → State distribution ✓ (both P1 complete)
4. Add US3-US5 (P2) → Time series, heatmap, reactivations ✓
5. Add US6 (P3) → Correlation analysis ✓
6. Polish → Documentation, validation ✓

---

## Summary

| Metric | Value |
|--------|-------|
| **Total Tasks** | 32 |
| **Setup Tasks** | 3 |
| **Foundational Tasks** | 2 |
| **US1 Tasks** | 3 |
| **US2 Tasks** | 3 |
| **US3 Tasks** | 3 |
| **US4 Tasks** | 3 |
| **US5 Tasks** | 6 |
| **US6 Tasks** | 4 |
| **Polish Tasks** | 5 |
| **MVP Scope** | Phase 1-3 (T001-T008) |
| **Parallel Opportunities** | Branch-based for user stories |

---

## Notes

- All tasks modify `config/monitoring/grafana/dashboards/memory-access-dashboard.json`
- Manual testing per plan.md - no automated test tasks
- Use Constitution IX compliant queries (max_over_time, rate, increase)
- Commit after each phase or logical group
- Stop at any checkpoint to validate story independently
