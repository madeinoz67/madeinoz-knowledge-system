# Tasks: Prometheus Dashboard Fixes

**Input**: Design documents from `/specs/016-prometheus-dashboard-fixes/`
**Prerequisites**: plan.md, spec.md, research.md

**Tests**: This feature includes visual validation tasks (opening dashboards in Grafana UI) instead of automated tests.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

**For this project (Madeinoz Knowledge System):**
- **Dashboard configuration**: `config/monitoring/grafana/dashboards/` and `config/monitoring/grafana/provisioning/dashboards/`
- **Documentation**: `docs/reference/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare working environment and gather context

- [ ] T001 Verify feature branch `016-prometheus-dashboard-fixes` is checked out
- [ ] T002 Review research.md for metric name mappings and query transformation patterns
- [ ] T003 Verify metrics server is running (`bun run server-cli status`)

**Checkpoint**: Environment ready, dashboard files identified

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No code infrastructure needed - this is configuration-only

*Note*: This feature requires no foundational code work. All tasks are file edits to existing dashboard JSON configurations.

**Checkpoint**: Ready to proceed with user story implementation

---

## Phase 3: User Story 1 - Fix Broken Dashboard Metrics (Priority: P1) 🎯 MVP

**Goal**: Correct metric names in dashboard queries to match code-defined metric names, eliminating "No Data" errors

**Independent Test**: Open each dashboard in Grafana UI and verify all panels display data without query errors

### Implementation for User Story 1

**Metric Name Corrections (Issue #38)**:

- [ ] T004 [P] [US1] Fix cache hit rate metric name in `config/monitoring/grafana/dashboards/madeinoz-knowledge.json` (replace `graphiti_cache_hit_rate_percent` with `graphiti_cache_hit_rate`)
- [ ] T005 [P] [US1] Fix API cost metric names in `config/monitoring/grafana/dashboards/madeinoz-knowledge.json` (replace `graphiti_api_cost_USD_total` with `graphiti_api_cost_total`, `graphiti_api_cost_all_models_USD_total` with `graphiti_api_cost_all_models_total`)
- [ ] T006 [P] [US1] Fix cost savings metric names in `config/monitoring/grafana/dashboards/madeinoz-knowledge.json` (replace `graphiti_cache_cost_saved_USD_total` with `graphiti_cache_cost_saved_total`, `graphiti_cache_cost_saved_all_models_USD_total` with `graphiti_cache_cost_saved_all_models_total`)
- [ ] T007 [P] [US1] Fix histogram metric name in `config/monitoring/grafana/dashboards/madeinoz-knowledge.json` (replace `graphiti_api_cost_per_request_USD_bucket` with `graphiti_api_cost_per_request`)
- [ ] T008 [P] [US1] Fix cache hit rate metric name in `config/monitoring/grafana/dashboards/prompt-cache-effectiveness.json` (replace `graphiti_cache_hit_rate_percent` with `graphiti_cache_hit_rate`)
- [ ] T009 [P] [US1] Fix cost savings metric names in `config/monitoring/grafana/dashboards/prompt-cache-effectiveness.json` (replace `graphiti_cache_cost_saved_USD_total` with `graphiti_cache_cost_saved_total`, `graphiti_cache_cost_saved_all_models_USD_total` with `graphiti_cache_cost_saved_all_models_total`)
- [ ] T010 [P] [US1] Fix histogram metric name in `config/monitoring/grafana/dashboards/prompt-cache-effectiveness.json` (replace `graphiti_api_cost_per_request_USD_bucket` with `graphiti_api_cost_per_request`)
- [ ] T011 [US1] Sync metric name fixes to `config/monitoring/grafana/provisioning/dashboards/madeinoz-knowledge.json` (copy corrected queries from source dashboard)
- [ ] T012 [US1] Validate dashboards load without query errors (open Grafana UI, check Query Inspection for each panel)

**Checkpoint**: All dashboard panels display data. Metric names match code definitions (FR-001 through FR-005 satisfied)

---

## Phase 4: User Story 2 - Maintain Continuous Metrics During Restarts (Priority: P2)

**Goal**: Add time-over-time wrapper functions to counter queries to bridge service restart gaps

**Independent Test**: Simulate service restart (`bun run server-cli restart`) and verify dashboard graphs show continuous data without gaps

### Implementation for User Story 2

**Time-Over-Time Additions (Issue #39)**:

- [ ] T013 [P] [US2] Add `max_over_time()[1h]` wrappers to counter rate queries in `config/monitoring/grafana/dashboards/madeinoz-knowledge.json` (wrap `rate()` expressions for `graphiti_total_tokens_total`, `graphiti_cache_hits_all_models_total`, `graphiti_cache_misses_all_models_total`)
- [ ] T014 [P] [US2] Add `max_over_time()[1h]` wrappers to counter total queries in `config/monitoring/grafana/dashboards/madeinoz-knowledge.json` (wrap `graphiti_cache_hits_all_models_total`, `graphiti_api_cost_total`)
- [ ] T015 [P] [US2] Add `max_over_time()[1h]` wrappers to histogram quantile queries in `config/monitoring/grafana/dashboards/madeinoz-knowledge.json` (wrap inner `rate()` in `histogram_quantile()` expressions for `graphiti_llm_request_duration_seconds_bucket`)
- [ ] T016 [P] [US2] Add `max_over_time()[1h]` wrappers to counter rate queries in `config/monitoring/grafana/dashboards/graph-health-dashboard.json` (wrap `rate()` expressions for `graphiti_cache_requests_all_models_total`, `graphiti_total_tokens_all_models_total`, `graphiti_episodes_processed_all_groups_total`)
- [ ] T017 [P] [US2] Add `max_over_time()[1h]` wrappers to counter queries in `config/monitoring/grafana/dashboards/memory-decay-dashboard.json` (wrap `increase()` and `rate()` expressions for lifecycle transition counters)
- [ ] T018 [P] [US2] Add `max_over_time()[1h]` wrappers to counter queries in `config/monitoring/grafana/dashboards/memory-access-dashboard.json` (wrap `rate()` expression for `knowledge_access_by_importance_total`)
- [ ] T019 [P] [US2] Add `max_over_time()[1h]` wrappers to counter queries in `config/monitoring/grafana/dashboards/prompt-cache-effectiveness.json` (wrap `rate()` expressions)
- [ ] T020 [US2] Sync time-over-time wrappers to `config/monitoring/grafana/provisioning/dashboards/madeinoz-knowledge.json` (copy wrapped queries from source dashboard)
- [ ] T021 [US2] Validate restart gap handling (restart metrics server, verify graphs show continuous data without visual cliffs)

**Checkpoint**: Dashboard graphs bridge restart gaps smoothly. Counter reset on restart no longer causes visual discontinuities (FR-006 through FR-010 satisfied)

---

## Phase 5: User Story 3 - Document Metric Query Patterns (Priority: P3)

**Goal**: Update observability documentation with metric naming conventions and query patterns

**Independent Test**: Create a new test dashboard panel following the documented patterns and verify it works correctly

### Implementation for User Story 3

**Documentation Updates**:

- [ ] T022 [US3] Add "Metric Naming Convention" section to `docs/reference/observability.md` (explain units as metadata, not in metric names; counter suffix `_total`; gauge no suffix; histogram suffixes)
- [ ] T023 [US3] Add "Time-Over-Time Query Patterns" section to `docs/reference/observability.md` (document `max_over_time()` for counters, 1-hour window recommendation, histogram quantile patterns)
- [ ] T024 [US3] Add "Common Pitfalls" section to `docs/reference/observability.md` (include correct vs incorrect examples, dashboard query troubleshooting)
- [ ] T025 [US3] Add metric reference table to `docs/reference/observability.md` (document all `graphiti_*` metrics with type, unit, description)
- [ ] T026 [US3] Validate documentation completeness (verify all FR-014, FR-015, FR-016 requirements are met)

**Checkpoint**: Documentation enables contributors to write correct dashboard queries without guessing metric names (FR-014 through FR-016 satisfied)

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup

- [ ] T027 [P] Verify JSON syntax is valid for all modified dashboard files (use `jq . < config/monitoring/grafana/dashboards/*.json` to validate)
- [ ] T028 [P] Run final Grafana UI validation (open all dashboards, check Query Inspection, verify no red query errors)
- [ ] T029 Commit changes with descriptive message following conventional commit format (`fix: correct Prometheus metric names in dashboards` and `improvement: add time-over-time functions for restart gap handling`)
- [ ] T030 Update CHANGELOG.md with feature summary

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Skipped - no foundational code needed
- **User Story 1 (Phase 3)**: Can start after Setup - fixes metric name mismatches
- **User Story 2 (Phase 4)**: Can start after Setup - independently adds time-over-time wrappers
- **User Story 3 (Phase 5)**: Can start after Setup - documentation updates
- **Polish (Phase 6)**: Depends on US1, US2, US3 completion

### User Story Dependencies

- **User Story 1 (P1)**: Independent - fixes metric names only
- **User Story 2 (P2)**: Independent - adds time-over-time wrappers (can be done in parallel with US1 on different files)
- **User Story 3 (P3)**: Independent - documentation updates

### Within Each User Story

- US1: Metric name fixes (T004-T010) are parallel across different files, T011 depends on source dashboard being complete, T012 validates all
- US2: Time-over-time wrappers (T013-T019) are parallel across different files, T020 depends on source dashboard being complete, T021 validates all
- US3: Documentation sections (T022-T025) are sequential within the file, T026 validates all

### Parallel Opportunities

- **US1 parallel execution**: Tasks T004-T007 can run in parallel (different panels within same file, but safer to do sequential)
- **US1 cross-file parallel**: T004-T010 can run in parallel across different dashboard files
- **US2 cross-file parallel**: T013-T019 can run in parallel across different dashboard files
- **US1 and US2 parallel**: Can work on metric name fixes (US1) and time-over-time wrappers (US2) in parallel on different files by different contributors

---

## Parallel Example: User Stories 1 and 2 Together

```bash
# Contributor A: Works on metric name fixes in US1
Task: "Fix cache hit rate metric name in config/monitoring/grafana/dashboards/madeinoz-knowledge.json"
Task: "Fix API cost metric names in config/monitoring/grafana/dashboards/madeinoz-knowledge.json"

# Contributor B: Works on time-over-time wrappers in US2 (different file)
Task: "Add max_over_time wrappers to counter rate queries in config/monitoring/grafana/dashboards/graph-health-dashboard.json"
Task: "Add max_over_time wrappers to counter queries in config/monitoring/grafana/dashboards/memory-decay-dashboard.json"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 3: User Story 1 (fix broken metrics)
3. **STOP and VALIDATE**: Open dashboards in Grafana, verify no "No Data" errors
4. Deploy/dashboards work correctly

**MVP delivers**: All dashboard panels show data. Metric naming inconsistencies resolved.

### Incremental Delivery

1. **Increment 1**: Add US2 → Time-over-time functions → Graphs bridge restart gaps
2. **Increment 2**: Add US3 → Documentation → Future contributors follow patterns
3. Each increment adds value without breaking previous work

### Parallel Team Strategy

With multiple contributors:

1. **Setup together**: Review research.md, verify environment
2. **Parallel work on different files**:
   - Contributor A: US1 on `madeinoz-knowledge.json`
   - Contributor B: US1 on `prompt-cache-effectiveness.json`
   - Contributor C: US2 on `graph-health-dashboard.json`
3. **Sync provisioning dashboard**: Copy from source once all changes complete
4. **Final validation together**: All dashboards open in Grafana UI

---

## File Change Summary

| File | US1 Changes | US2 Changes | Total |
|------|-------------|-------------|-------|
| `config/monitoring/grafana/dashboards/madeinoz-knowledge.json` | 9 name fixes | ~15 wrappers | 24 |
| `config/monitoring/grafana/dashboards/graph-health-dashboard.json` | 0 | ~8 wrappers | 8 |
| `config/monitoring/grafana/dashboards/memory-decay-dashboard.json` | 0 | ~5 wrappers | 5 |
| `config/monitoring/grafana/dashboards/memory-access-dashboard.json` | 0 | ~2 wrappers | 2 |
| `config/monitoring/grafana/dashboards/prompt-cache-effectiveness.json` | 6 name fixes | ~2 wrappers | 8 |
| `config/monitoring/grafana/provisioning/dashboards/madeinoz-knowledge.json` | 9 name fixes | ~15 wrappers | 24 |
| `docs/reference/observability.md` | 0 | 0 | 4 sections added |

---

## Notes

- [P] tasks = different files, no dependencies, can run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each logical group of tasks (e.g., per file)
- Stop at any checkpoint to validate story independently
- JSON files must maintain valid syntax after edits (verify with `jq` or similar)
- Dashboard panel IDs must remain stable (don't change `"id"` values)
