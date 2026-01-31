# Tasks: Prompt Cache Effectiveness Dashboard

**Input**: Design documents from `/specs/013-prompt-cache-dashboard/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Visual verification against live Grafana instance - no automated tests required for dashboard configuration.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different panels, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US5)
- Panel IDs correspond to Grafana dashboard panel grid positions

## Path Conventions

**For this feature (Dashboard configuration only):**
- **Dashboard JSON**: `config/monitoring/grafana/dashboards/prompt-cache-effectiveness.json`
- No application code changes required
- Uses existing PR #34 Prometheus metrics
- Dashboard provisioning via Grafana's automatic dashboard loading

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dashboard file structure and Grafana provisioning setup

- [X] T001 Verify Grafana dashboard provisioning directory exists at `config/monitoring/grafana/dashboards/`
- [X] T002 Verify Prometheus data source is configured in Grafana settings
- [X] T003 Verify PR #34 metrics are being emitted by checking `curl http://localhost:9091/metrics | grep cache`

---

## Phase 2: Foundational (Dashboard Structure)

**Purpose**: Core dashboard JSON structure that ALL panels depend on

**⚠️ CRITICAL**: No user story panels can be added until this phase is complete

- [X] T004 Create dashboard JSON skeleton with metadata (title, tags, timezone, schemaVersion, refresh: "30s")
- [X] T005 Configure dashboard layout for 3 rows × 3-4 panels to fit 1080p single screen
- [X] T006 Add Prometheus data source variable to dashboard configuration
- [X] T007 Set time range options (1h, 6h, 24h, 7d, 30d) with default "Last 24 hours"

**Checkpoint**: Dashboard skeleton loads in Grafana with empty panel grid

---

## Phase 3: User Story 1 - Monitor Caching ROI (Priority: P1) 🎯 MVP

**Goal**: Display total cost savings, savings rate trend, and per-model cost comparison

**Independent Test**: Dashboard shows cumulative cost savings metric that can be compared against API costs

### Implementation for User Story 1

- [X] T008 [P] [US1] Create Stat panel "Total Cost Savings" (Row 1, Panel 1) with query: `max_over_time(graphiti_cache_cost_saved_all_models_total[1h])`
- [X] T009 [P] [US1] Configure color thresholds for cost savings panel (green >$1, yellow $0.01-$1, red $0)
- [X] T010 [P] [US1] Add unit formatting "USD" and decimal precision (2 places)
- [X] T011 [US1] Create Time Series panel "Savings Rate" (Row 2, Panel 1) with query: `rate(max_over_time(graphiti_cache_cost_saved_all_models_total[1h])[5m])`
- [X] T012 [US1] Configure savings rate panel legend and y-axis formatting (USD/hour)
- [X] T013 [US1] Add per-model cost savings column to comparison table (Row 3, right panel) with query: `rate(max_over_time(graphiti_cache_cost_saved_total[1h])[5m]) by (model)`

**Checkpoint**: At this point, User Story 1 panels display cost savings with trend

---

## Phase 4: User Story 2 - Analyze Cache Hit/Miss Patterns (Priority: P1) 🎯 MVP

**Goal**: Display hit rate gauge, hit/miss comparison time series

**Independent Test**: Dashboard shows hit rate percentage and hit/miss counts for anomaly detection

### Implementation for User Story 2

- [X] T014 [P] [US2] Create Stat panel "Hit Rate" (Row 1, Panel 2) with direct query: `graphiti_cache_hit_rate`
- [X] T015 [P] [US2] Configure color thresholds for hit rate panel (green >50%, yellow 20-50%, red <20%)
- [X] T016 [P] [US2] Add percentage formatting with gauge visualization (0-100%)
- [X] T017 [US2] Create Time Series panel "Hit Rate Trend" (Row 2, Panel 2) with query: `graphiti_cache_hit_rate`
- [X] T018 [US2] Create Time Series panel "Hits vs Misses" (Row 2, Panel 3) with dual queries:
  - Hits: `rate(max_over_time(graphiti_cache_hits_all_models_total[1h])[5m])`
  - Misses: `rate(max_over_time(graphiti_cache_misses_all_models_total[1h])[5m])`
- [X] T019 [US2] Configure stacked area chart for hits vs misses comparison
- [X] T020 [US2] Add per-model hit rate column to comparison table with query: `graphiti_cache_hits_total / (graphiti_cache_hits_total + graphiti_cache_misses_total) by (model)`

**Checkpoint**: At this point, User Story 2 panels display hit/miss patterns with trend

---

## Phase 5: User Story 3 - Understand Cache Write Overhead (Priority: P2)

**Goal**: Display tokens written to cache for overhead assessment

**Independent Test**: Dashboard shows cache write token count comparable to tokens saved

### Implementation for User Story 3

- [X] T021 [P] [US3] Create Stat panel "Tokens Written" (Row 1, Panel 4) with query: `max_over_time(graphiti_cache_write_tokens_all_models_total[1h])`
- [X] T022 [P] [US3] Configure unit formatting "short" (e.g., "1.2M", "345K") for large token counts
- [X] T023 [US3] Add orange color scheme to distinguish from "Tokens Saved" panel
- [X] T024 [US3] Add description text: "Tokens consumed to create cache entries (compare with tokens saved to assess efficiency)"

**Checkpoint**: At this point, User Story 3 panel displays write overhead

---

## Phase 6: User Story 4 - Analyze Cache Hit Distribution (Priority: P2)

**Goal**: Display histogram heatmap of tokens saved per request

**Independent Test**: Dashboard shows heatmap showing frequency of different hit sizes

### Implementation for User Story 4

- [X] T025 [P] [US4] Create Stat panel "Tokens Saved" (Row 1, Panel 3) with query: `max_over_time(graphiti_cache_tokens_saved_all_models_total[1h])`
- [X] T026 [P] [US4] Configure blue color scheme for positive/savings metric
- [X] T027 [US4] Add unit formatting "short" for large token counts
- [X] T028 [US4] Create Heatmap panel "Tokens Saved Distribution" (Row 3, left panel) with query: `sum(increase(graphiti_cache_tokens_saved_per_request_bucket[$__rate_interval])) by (le)`
- [X] T029 [US4] Configure heatmap color palette (blue → green → yellow for increasing frequency)
- [X] T030 [US4] Add X-axis label "Tokens Saved" and Y-axis label "Frequency"

**Checkpoint**: At this point, User Story 4 panels display distribution and total

---

## Phase 7: User Story 5 - Compare Model-Specific Caching Performance (Priority: P3)

**Goal**: Display per-model comparison table

**Independent Test**: Dashboard shows per-model breakdown allowing side-by-side comparison

### Implementation for User Story 5

- [X] T031 [P] [US5] Create Table panel "Per-Model Comparison" (Row 3, right panel) with columns:
  - Model name
  - Hit rate (%)
  - Tokens saved
  - Cost saved (USD)
  - Hits
  - Misses
- [X] T032 [P] [US5] Configure table queries for each column using `by (model)` aggregation:
  - Hit rate: `rate(max_over_time(graphiti_cache_hits_total[1h])[5m]) / (rate(max_over_time(graphiti_cache_hits_total[1h])[5m]) + rate(max_over_time(graphiti_cache_misses_total[1h])[5m])) by (model)`
  - Tokens saved: `rate(max_over_time(graphiti_cache_tokens_saved_total[1h])[5m]) by (model)`
  - Cost saved: `rate(max_over_time(graphiti_cache_cost_saved_total[1h])[5m]) by (model)`
- [X] T033 [US5] Configure table column sorting (all columns sortable by user click)
- [X] T034 [US5] Add table title "Per-Model Cache Performance" with description "Compare caching effectiveness across LLM models"

**Checkpoint**: All user stories should now be independently functional

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T035 [P] Verify all cumulative metric queries use `max_over_time()[1h]` wrapper (Principle IX compliance)
- [X] T036 [P] Verify dashboard fits on single 1080p screen without scrolling (adjust panel heights if needed)
- [X] T037 [P] Test zero-value scenarios: ensure panels show "No data" or "0" instead of errors
- [X] T038 [P] Add dashboard title "Prompt Cache Effectiveness" with tagline "Gemini caching ROI and performance monitoring"
- [X] T039 [P] Add dashboard tags: "cache", "monitoring", "cost", "gemini", "prompt-caching"
- [X] T040 [P] Set dashboard auto-refresh to 30 seconds (user-configurable)
- [X] T041 [P] Add panel descriptions for quickstart.md reference
- [X] T042 Verify Grafana dashboard JSON schema is valid (version 36)
- [X] T043 Run quickstart.md validation: load dashboard at `http://localhost:3002/d/prompt-cache-effectiveness`
- [X] T044 Test service restart scenario: verify no gaps in cumulative metrics (time-over-time functions working)
- [X] T045 Update `docs/reference/observability.md` with new dashboard documentation (per Principle IX)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - verification tasks can run in parallel
- **Foundational (Phase 2)**: Depends on verification in Setup - BLOCKS all user stories
- **User Stories (Phases 3-7)**: All depend on Foundational phase completion
  - User stories can proceed in parallel after foundation
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational - Shares comparison table with US5 (coordinate on table panel)
- **User Story 3 (P2)**: Can start after Foundational - No dependencies on other stories
- **User Story 4 (P2)**: Can start after Foundational - No dependencies on other stories
- **User Story 5 (P3)**: Can start after Foundational - Completes comparison table started in US1/US2

### Within Each User Story

- Stat panels can be created in parallel (different panel IDs)
- Time series panels can be created in parallel
- Table panel in US5 depends on queries from US1/US2 for per-model data

### Parallel Opportunities

- T001, T002, T003: All verification tasks can run in parallel
- Within each user story, all [P] tasks can run in parallel (different panels)
- After Foundational phase, all 5 user stories can be worked on in parallel
- All Phase 8 polish tasks marked [P] can run in parallel

---

## Implementation Strategy

### MVP First (User Stories 1 & 2 Only - P1 Priority)

1. Complete Phase 1: Setup (verify metrics and Grafana)
2. Complete Phase 2: Foundational (dashboard skeleton)
3. Complete Phase 3: User Story 1 (Cost savings panels)
4. Complete Phase 4: User Story 2 (Hit/miss panels)
5. **STOP and VALIDATE**: Test dashboard shows key ROI and health metrics
6. Deploy/demo if ready (P1 MVP complete!)

### Incremental Delivery

1. Complete Setup + Foundational → Dashboard skeleton ready
2. Add User Story 1 → Test cost savings → Deploy (MVP increment 1)
3. Add User Story 2 → Test hit/miss patterns → Deploy (MVP complete!)
4. Add User Story 3 → Test write overhead → Deploy
5. Add User Story 4 → Test distribution heatmap → Deploy
6. Add User Story 5 → Test per-model table → Deploy
7. Complete Polish → Final release

### Visual Verification Testing

After each user story:
1. Reload Grafana dashboard (`http://localhost:3000/d/prompt-cache-effectiveness`)
2. Verify panels render without errors
3. Check time-over-time queries handle any service restarts
4. Verify zero-value scenarios show "0" or "No data"
5. Confirm panel fits on 1080p screen layout

---

## Notes

- [P] tasks = different panels or files, no dependencies
- [Story] label maps task to specific user story for traceability
- All cumulative metrics MUST use `max_over_time()[1h]` wrapper (Principle IX)
- Dashboard JSON file is the only output - no application code changes
- Visual verification is the primary testing method for dashboards
- Time-over-time functions ensure dashboard survives service restarts without gaps
