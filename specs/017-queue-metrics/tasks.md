# Tasks: Queue Processing Metrics

**Input**: Design documents from `/specs/017-queue-metrics/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/metrics.md
**Tests**: NOT included - tests not explicitly requested in feature specification

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

**For this project (Madeinoz Knowledge System):**
- **Python code**: `docker/patches/` for implementation
- **Metrics**: `docker/patches/metrics_exporter.py` (existing file to extend)
- **Instrumentation**: `docker/patches/graphiti_mcp_server.py` (existing file to modify)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No setup needed - leveraging existing metrics infrastructure

**Note**: This feature extends existing metrics infrastructure (CacheMetricsExporter, DecayMetricsExporter). No new project initialization required.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core QueueMetricsExporter class that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T001 Add queue histogram Views to meter provider in docker/patches/metrics_exporter.py (in CacheMetricsExporter._initialize_metrics() after line 212)
- [x] T002 [P] Create QueueMetricsExporter class structure in docker/patches/metrics_exporter.py (after DecayMetricsExporter class)
- [x] T003 [P] Implement QueueMetricsExporter.__init__() method with meter initialization in docker/patches/metrics_exporter.py
- [x] T004 [P] Implement QueueMetricsExporter._create_counters() method for message_processed, messages_failed, retries_total counters in docker/patches/metrics_exporter.py
- [x] T005 [P] Implement QueueMetricsExporter._create_gauges() method for queue_depth, consumer_lag_seconds, consumer_saturation, active_consumers gauges in docker/patches/metrics_exporter.py
- [x] T006 [P] Implement QueueMetricsExporter._create_histograms() method for processing_duration_seconds, wait_time_seconds, end_to_end_latency_seconds histograms in docker/patches/metrics_exporter.py
- [x] T007 Implement internal state tracking (_enqueued_total, _processed_total, _failed_total, _enqueue_times, _processing_start_time, _last_processed_count) in QueueMetricsExporter.__init__() in docker/patches/metrics_exporter.py
- [x] T008 Add initialize_queue_metrics_exporter() module-level function in docker/patches/metrics_exporter.py
- [x] T009 Add get_queue_metrics_exporter() module-level function in docker/patches/metrics_exporter.py

**Checkpoint**: Foundation ready - QueueMetricsExporter class exists with all metric types defined

---

## Phase 3: User Story 1 - Monitor Queue Backlog Growth (Priority: P1) 🎯 MVP

**Goal**: Track queue depth and backlog growth via counter and gauge metrics

**Independent Test**: Send messages to queue, query `http://localhost:9090/metrics` for `messaging_queue_depth`, verify depth increments/decrements correctly

### Implementation for User Story 1

- [x] T010 [P] [US1] Implement record_enqueue() method in QueueMetricsExporter class in docker/patches/metrics_exporter.py (increments enqueued_total, updates queue_depth gauge, records enqueue timestamp)
- [x] T011 [P] [US1] Implement record_dequeue() method in QueueMetricsExporter class in docker/patches/metrics_exporter.py (decrements queue_depth gauge)
- [x] T012 [US1] Implement update_queue_depth() method in QueueMetricsExporter class in docker/patches/metrics_exporter.py (sets gauge to exact value for external synchronization)
- [x] T013 [US1] Add module-level import for queue metrics in docker/patches/graphiti_mcp_server.py (line ~56 after decay metrics import)
- [x] T014 [US1] Add global queue_metrics_exporter variable in docker/patches/graphiti_mcp_server.py (near other global variables around line 591)
- [x] T015 [US1] Initialize queue metrics exporter in main() function in docker/patches/graphiti_mcp_server.py (after line 1982, after decay metrics initialization)
- [x] T016 [US1] Wrap queue_service.add_episode() call with record_enqueue() in docker/patches/graphiti_mcp_server.py (around line 862, before await queue_service.add_episode())
- [x] T017 [US1] Wrap queue_service.add_episode() call with record_dequeue() in docker/patches/graphiti_mcp_server.py (around line 862, after await queue_service.add_episode() returns)

**Checkpoint**: At this point, User Story 1 should be fully functional - queue depth metrics are exposed via Prometheus endpoint

---

## Phase 4: User Story 2 - Detect Processing Latency Issues (Priority: P1)

**Goal**: Measure message processing latency via duration histograms

**Independent Test**: Send test messages with known timestamps, query `messaging_processing_duration_seconds` histogram from Prometheus, verify P50/P95/P99 percentiles are within expected ranges

### Implementation for User Story 2

- [x] T018 [P] [US2] Implement record_processing_start() context manager method in QueueMetricsExporter class in docker/patches/metrics_exporter.py (returns Iterator[None], records start timestamp)
- [x] T019 [P] [US2] Implement record_processing_complete() method in QueueMetricsExporter class in docker/patches/metrics_exporter.py (records processing duration to histogram, updates processed_total, decrements queue_depth, handles success/failure)
- [x] T020 [US2] Calculate wait_time from enqueue timestamp in record_processing_complete() method in docker/patches/metrics_exporter.py (wait_time = processing_start_time - enqueue_time)
- [x] T021 [US2] Calculate e2e_latency in record_processing_complete() method in docker/patches/metrics_exporter.py (e2e_latency = processing_duration + wait_time)
- [x] T022 [US2] Update queue_service.add_episode() instrumentation to use record_processing_complete() with duration tracking in docker/patches/graphiti_mcp_server.py (capture start/end time around the await call, pass duration to record_processing_complete())
- [x] T023 [US2] Add error handling wrapper around queue_service.add_episode() to pass success/error_type to record_processing_complete() in docker/patches/graphiti_mcp_server.py (try/except to capture failures)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - queue depth and processing latency metrics are exposed

---

## Phase 5: User Story 3 - Monitor Consumer Health and Saturation (Priority: P2)

**Goal**: Track consumer utilization, lag, and saturation via gauge metrics

**Independent Test**: Check `messaging_consumer_lag_seconds` and `messaging_consumer_saturation` gauges from Prometheus, verify lag is expressed in time (not message count) and saturation reflects consumer utilization

### Implementation for User Story 3

- [x] T024 [P] [US3] Calculate processing_rate from processed_total and uptime in QueueMetricsExporter class in docker/patches/metrics_exporter.py (rate = processed_total / (now() - _processing_start_time))
- [x] T025 [P] [US3] Calculate lag_seconds from queue_depth and processing_rate in QueueMetricsExporter class in docker/patches/metrics_exporter.py (lag = depth / rate with div-by-zero guard)
- [x] T026 [P] [US3] Implement update_consumer_metrics() method in QueueMetricsExporter class in docker/patches/metrics_exporter.py (sets consumer_lag_seconds, consumer_saturation, active_consumers gauges)
- [x] T027 [US3] Add thread safety for internal counter dictionaries using threading.Lock in QueueMetricsExporter class in docker/patches/metrics_exporter.py (protect _enqueued_total, _processed_total, _failed_total access)
- [x] T028 [US3] Create background task to periodically update consumer metrics in docker/patches/graphiti_mcp_server.py (asyncio task that calls update_consumer_metrics every 30 seconds with calculated saturation and lag)

**Checkpoint**: At this point, User Stories 1, 2, AND 3 should all work - consumer health metrics are exposed

---

## Phase 6: User Story 4 - Track Processing Failures and Retries (Priority: P2)

**Goal**: Track failure rates and retry attempts via counter metrics with error type labels

**Independent Test**: Send messages that will fail processing, verify `messaging_messages_failed_total` counter increments with correct error_type label, verify `messaging_retries_total` increments

### Implementation for User Story 4

- [x] T029 [P] [US4] Add error_type categorization to record_processing_complete() method in QueueMetricsExporter class in docker/patches/metrics_exporter.py (map exceptions to coarse categories: ConnectionError, ValidationError, TimeoutError, RateLimitError, UnknownError)
- [x] T030 [P] [US4] Implement record_retry() method in QueueMetricsExporter class in docker/patches/metrics_exporter.py (increments messaging_retries_total counter)
- [x] T031 [US4] Update instrumentation to record retry attempts in docker/patches/graphiti_mcp_server.py (call record_retry() on retry logic) - Note: record_retry() method available for use when retry logic is implemented
- [x] T032 [US4] Verify error_type labels are applied to messages_failed_total counter in QueueMetricsExporter.record_processing_complete() method in docker/patches/metrics_exporter.py (ensure high-cardinality labels are avoided)

**Checkpoint**: At this point, all P1 and P2 user stories should be functional - queue depth, latency, consumer health, and failure tracking metrics are exposed

---

## Phase 7: User Story 5 - Visualize Metrics in Dashboard (Priority: P3)

**Goal**: Provide pre-built Grafana dashboard for quick health assessment

**Independent Test**: Import dashboard JSON into Grafana, verify all panels display data correctly, adjust time range to confirm historical context works

### Implementation for User Story 5

- [x] T033 [P] [US5] Design Grafana dashboard JSON with panels for queue depth, latency, consumer health, and throughput in specs/017-queue-metrics/dashboard.json
- [x] T034 [P] [US5] Add panel for Queue Depth Over Time in specs/017-queue-metrics/dashboard.json (query: messaging_queue_depth)
- [x] T035 [P] [US5] Add panel for Processing Latency (P50/P95/P99) in specs/017-queue-metrics/dashboard.json (query: histogram_quantile(0.95, sum(rate(messaging_processing_duration_seconds_bucket[5m])) by (le)))
- [x] T036 [P] [US5] Add panel for Consumer Lag (Time to Catch Up) in specs/017-queue-metrics/dashboard.json (query: messaging_consumer_lag_seconds)
- [x] T037 [P] [US5] Add panel for Throughput (Messages/Second) in specs/017-queue-metrics/dashboard.json (query: sum(rate(messaging_messages_processed_total{status="success"}[5m])))
- [x] T038 [P] [US5] Add panel for Error Rate in specs/017-queue-metrics/dashboard.json (query: sum(rate(messaging_messages_failed_total[5m])) / sum(rate(messaging_messages_processed_total[5m])) * 100)
- [x] T039 [US5] Document dashboard import process in specs/017-queue-metrics/quickstart.md (Step 7: Grafana Dashboard Import section)

**Checkpoint**: All user stories complete - full observability for queue processing with dashboard visualization

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T040 [P] Add comprehensive docstrings to all QueueMetricsExporter public methods in docker/patches/metrics_exporter.py
- [x] T041 [P] Add inline comments explaining gauge calculation logic (depth, lag, saturation) in docker/patches/metrics_exporter.py
- [x] T042 Add graceful degradation for when OpenTelemetry is unavailable in QueueMetricsExporter methods in docker/patches/metrics_exporter.py (log warnings and return silently)
- [x] T043 [P] Add logging for queue metrics initialization in docker/patches/graphiti_mcp_server.py main() function
- [x] T044 [P] Update CLAUDE.md with queue metrics feature documentation in /Users/seaton/Documents/src/madeinoz-knowledge-system/CLAUDE.md
- [x] T045 Rebuild containers with local changes per quickstart.md Step 5 (docker build -f docker/Dockerfile -t madeinoz-knowledge-system:local .)
- [x] T046 Verify metrics at Prometheus endpoint per quickstart.md Step 6 (curl http://localhost:9090/metrics | grep messaging_)
- [x] T047 Run validation: send test message and verify metrics increment per quickstart.md Step 6

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Skipped - using existing infrastructure
- **Foundational (Phase 2)**: No dependencies - can start immediately, BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1) - Queue Backlog**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1) - Processing Latency**: Can start after Foundational (Phase 2) - Extends US1 instrumentation but independently testable
- **User Story 3 (P2) - Consumer Health**: Can start after Foundational (Phase 2) - Uses metrics from US1/US2 but independently testable
- **User Story 4 (P2) - Failure Tracking**: Can start after Foundational (Phase 2) - Extends US2 error handling but independently testable
- **User Story 5 (P3) - Dashboard**: Can start after all P1/P2 stories complete - Requires metrics to exist first

### Within Each User Story

- Core implementation before integration
- Models before services (applies to foundational phase)
- Core implementation before instrumentation
- Story complete before moving to next priority

### Parallel Opportunities

- All Foundational tasks marked [P] can run in parallel (T002-T006 create different metric types)
- Once Foundational phase completes, US1 and US2 can start in parallel (both P1 priority)
- US3 and US4 can start in parallel after P1 stories complete (both P2 priority)
- US5 must wait for all metric-producing stories (US1-US4)
- Within US1: T010-T011 (enqueue/dequeue methods) can run in parallel
- Within US2: T018-T019 (processing methods) can run in parallel
- Within US3: T024-T026 (calculation methods) can run in parallel
- Within US4: T029-T030 (failure/retry methods) can run in parallel
- Within US5: T034-T038 (dashboard panels) can run in parallel

---

## Parallel Example: Foundational Phase

```bash
# Launch all metric type creators in parallel:
Task: "T004 [P] Implement QueueMetricsExporter._create_counters()"
Task: "T005 [P] Implement QueueMetricsExporter._create_gauges()"
Task: "T006 [P] Implement QueueMetricsExporter._create_histograms()"
```

---

## Parallel Example: User Story 1

```bash
# Launch enqueue/dequeue methods in parallel:
Task: "T010 [P] [US1] Implement record_enqueue() method"
Task: "T011 [P] [US1] Implement record_dequeue() method"
```

---

## Parallel Example: User Story 5 (Dashboard)

```bash
# Launch all dashboard panel creators in parallel:
Task: "T034 [P] [US5] Add panel for Queue Depth Over Time"
Task: "T035 [P] [US5] Add panel for Processing Latency"
Task: "T036 [P] [US5] Add panel for Consumer Lag"
Task: "T037 [P] [US5] Add panel for Throughput"
Task: "T038 [P] [US5] Add panel for Error Rate"
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2 Only - Both P1)

1. Skip Phase 1 (no setup needed)
2. Complete Phase 2: Foundational (T001-T009) - **CRITICAL**
3. Complete Phase 3: User Story 1 (T010-T017) - Queue backlog monitoring
4. Complete Phase 4: User Story 2 (T018-T023) - Processing latency tracking
5. **STOP and VALIDATE**: Test US1 and US2 independently
6. Deploy/demo if ready

**MVP Scope**: Queue backlog growth detection + processing latency regression detection

### Full Feature (All User Stories)

1. Complete MVP (Phases 2-4) as above
2. Add Phase 5: User Story 3 (T024-T028) - Consumer health monitoring
3. Add Phase 6: User Story 4 (T029-T032) - Failure and retry tracking
4. Add Phase 7: User Story 5 (T033-T039) - Grafana dashboard
5. Add Phase 8: Polish (T040-T047)
6. **FINAL VALIDATION**: Test all stories per quickstart.md

### Parallel Team Strategy

With multiple developers:

1. Team completes Foundational phase (T001-T009) together
2. Once Foundational is done:
   - Developer A: User Story 1 (T010-T017)
   - Developer B: User Story 2 (T018-T023)
3. After P1 stories merge:
   - Developer A: User Story 3 (T024-T028)
   - Developer B: User Story 4 (T029-T032)
4. After P2 stories merge:
   - Developer C: User Story 5 (T033-T039) - Dashboard
5. Team: Polish phase (T040-T047)

---

## Summary

- **Total Tasks**: 47
- **Tasks per User Story**:
  - Foundational: 9 tasks
  - US1 (Queue Backlog): 8 tasks
  - US2 (Latency): 6 tasks
  - US3 (Consumer Health): 5 tasks
  - US4 (Failure Tracking): 4 tasks
  - US5 (Dashboard): 7 tasks
  - Polish: 8 tasks
- **Parallel Opportunities**: 20 tasks marked [P]
- **Independent Test Criteria**: Defined for each user story phase
- **Suggested MVP Scope**: Phases 2-4 (Foundational + US1 + US2) = 23 tasks

---

## Notes

- [P] tasks = different files or methods, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Verify metrics at http://localhost:9090/metrics after implementation
- Rebuild containers after code changes: `docker build -f docker/Dockerfile -t madeinoz-knowledge-system:local .`
