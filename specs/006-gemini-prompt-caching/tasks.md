# Tasks: Gemini Prompt Caching with Cost Reporting (CORRECTED)

**Input**: Design documents from `/specs/006-gemini-prompt-caching/`
**Prerequisites**: plan.md (complete), spec.md (complete), research.md (REVISED), data-model.md (complete), contracts/ (complete)

**Tests**: Included per spec.md acceptance scenarios requiring test coverage.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## CRITICAL ARCHITECTURE NOTES

**This task list reflects the CORRECTED architecture from research.md (2026-01-27):**

1. **OpenRouter Cache Control Approach** (NOT automatic, NOT direct SDK):
   - Caching requires explicit `cache_control` markers in requests
   - Multipart message format required (not simple strings)
   - OpenRouter manages cache lifecycle automatically (no create/delete API)
   - **NO `google-generativeai` SDK dependency**

2. **Prometheus Metrics** (NOT health endpoint):
   - `/metrics` endpoint with Prometheus format on port 9090
   - OpenTelemetry SDK instrumentation
   - 7 metrics defined (5 counters, 4 gauges)
   - **No health endpoint modification**

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- File paths use `docker/patches/` per plan.md project structure

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependencies (OpenTelemetry, NOT google-generativeai), and configuration

- [x] T001 Create docker/patches/requirements-cache.txt with OpenTelemetry dependencies (`opentelemetry-api>=1.20.0`, `opentelemetry-sdk>=1.20.0`, `opentelemetry-exporter-prometheus>=0.41b0`, `prometheus-client>=0.17.0`)
- [x] T002 [P] Update docker/Dockerfile to install cache requirements file
- [x] T003 [P] Add `MADEINOZ_KNOWLEDGE_PROMPT_CACHE_ENABLED` to config/.env.example (default: true)
- [x] T004 [P] Add `MADEINOZ_KNOWLEDGE_PROMPT_CACHE_METRICS_ENABLED` to config/.env.example (default: true)
- [x] T005 [P] Add `MADEINOZ_KNOWLEDGE_METRICS_PORT` to config/.env.example (default: 9090)
- [x] T006 [P] Add `MADEINOZ_KNOWLEDGE_PROMPT_CACHE_LOG_REQUESTS` to config/.env.example (default: false)

**Checkpoint**: Dependencies installed, configuration variables defined

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T007 [P] Implement CacheMetrics dataclass in docker/patches/cache_metrics.py (cache_hit, cached_tokens, prompt_tokens, completion_tokens, tokens_saved, cost_without_cache, actual_cost, cost_saved, savings_percent, model)
- [x] T008 [P] Implement PricingTier dictionary with OpenRouter Gemini pricing in docker/patches/cache_metrics.py (google/gemini-2.5-flash, google/gemini-2.5-pro, google/gemini-2.0-flash-001 with ~50% cache discount)
- [x] T009 [P] Implement SessionMetrics dataclass in docker/patches/session_metrics.py (total_requests, cache_hits, total_cached_tokens, total_prompt_tokens, total_completion_tokens, total_cost_saved, session_start)
- [x] T010 [P] Implement OpenTelemetry meter provider initialization in docker/patches/metrics_exporter.py (create meter for graphiti.cache namespace)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Automatic Prompt Caching (Priority: P1) MVP

**Goal**: Enable automatic caching via OpenRouter cache_control markers - users running Graphiti with Gemini models benefit from prompt caching

**Independent Test**: Repeated queries with same system prompt show 40%+ token cost reduction on cache hits (SC-001)

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T011 [P] [US1] Unit test for multipart message format in tests/unit/test_message_formatter.py
- [ ] T012 [P] [US1] Unit test for cache_control marker injection in tests/unit/test_message_formatter.py
- [ ] T013 [P] [US1] Unit test for simple string to multipart conversion in tests/unit/test_message_formatter.py
- [ ] T014 [P] [US1] Unit test for cached_tokens extraction from OpenRouter response in tests/unit/test_cache_metrics.py

### Implementation for User Story 1

- [x] T015 [US1] Implement format_message_for_caching() in docker/patches/message_formatter.py (convert simple content to multipart with cache_control)
- [x] T016 [US1] Implement add_cache_control_marker() in docker/patches/message_formatter.py (adds {"type": "ephemeral"} to system prompts)
- [x] T017 [US1] Implement is_cacheable_request() check in docker/patches/message_formatter.py (verify minimum token threshold ~1024)
- [x] T018 [US1] Implement extract_cache_metrics() in docker/patches/cache_metrics.py (parse usage.cached_tokens and cache_discount from OpenRouter response)
- [x] T019 [US1] Modify docker/patches/factories.py to wrap message construction with format_message_for_caching() for Gemini models
- [x] T020 [US1] Implement calculate_cost_savings() in docker/patches/cache_metrics.py (use PricingTier and cache_discount from response)
- [x] T021 [P] [US1] Integration test for cache hit on repeated request in docker/tests/integration/test_caching_e2e.py
- [x] T022 [P] [US1] Integration test for cache miss on first request in docker/tests/integration/test_caching_e2e.py
- [x] T023 [P] [US1] Integration test for multipart format sent to OpenRouter in docker/tests/integration/test_caching_e2e.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently - repeated queries show cost reduction

---

## Phase 4: User Story 2 - Cost and Cache Metrics Reporting (Priority: P2)

**Goal**: Show cache metrics in every API response - users receive detailed caching metrics showing cache hit rates, tokens saved, and cost reductions

**Independent Test**: Response metadata includes complete caching metrics (10 fields) in 100% of Gemini API responses (SC-003)

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T024 [P] [US2] Unit test for CacheMetrics dataclass validation in tests/unit/test_cache_metrics.py
- [ ] T025 [P] [US2] Unit test for cost_saved calculation formula in tests/unit/test_cache_metrics.py
- [ ] T026 [P] [US2] Unit test for savings_percent calculation in tests/unit/test_cache_metrics.py
- [ ] T027 [P] [US2] Unit test for SessionMetrics accumulation in tests/unit/test_session_metrics.py

### Implementation for User Story 2

- [ ] T028 [US2] Implement CacheMetrics.to_dict() method in docker/patches/cache_metrics.py for JSON serialization
- [ ] T029 [US2] Implement CacheMetrics.from_openrouter_response() factory in docker/patches/cache_metrics.py (extract from OpenRouter format)
- [ ] T030 [US2] Implement SessionMetrics.record_request() method in docker/patches/session_metrics.py (accumulate per-request metrics)
- [ ] T031 [US2] Add response metadata enhancement in factories.py to embed cache_metrics in MCP response
- [ ] T032 [US2] Implement SessionMetrics.get_summary() method for session-level statistics
- [ ] T033 [P] [US2] Integration test for cache_metrics present in response on cache hit in tests/integration/test_caching_e2e.py
- [ ] T034 [P] [US2] Integration test for all 10 cache_metrics fields present in tests/integration/test_caching_e2e.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - responses include cost transparency

---

## Phase 5: User Story 3 - Prometheus Metrics Monitoring (Priority: P3)

**Goal**: Prometheus /metrics endpoint exposes cache statistics - system administrators can monitor cache effectiveness through standard observability tools

**Independent Test**: Prometheus /metrics endpoint exposes cache statistics in standard format (SC-006)

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T035 [P] [US3] Integration test for /metrics endpoint returns Prometheus format in tests/integration/test_metrics_endpoint.py
- [ ] T036 [P] [US3] Integration test for graphiti_cache_hits_total counter in tests/integration/test_metrics_endpoint.py
- [ ] T037 [P] [US3] Integration test for graphiti_cache_hit_rate gauge in tests/integration/test_metrics_endpoint.py

### Implementation for User Story 3

- [ ] T038 [US3] Implement create_cache_counters() in docker/patches/metrics_exporter.py (graphiti_cache_hits_total, graphiti_cache_misses_total, graphiti_cache_tokens_saved_total, graphiti_cache_cost_saved_total, graphiti_cache_requests_total)
- [ ] T039 [US3] Implement create_cache_gauges() in docker/patches/metrics_exporter.py (graphiti_cache_hit_rate, graphiti_cache_size_bytes, graphiti_cache_entries, graphiti_cache_enabled)
- [ ] T040 [US3] Implement record_cache_hit() in docker/patches/metrics_exporter.py (increment counters with model label)
- [ ] T041 [US3] Implement record_cache_miss() in docker/patches/metrics_exporter.py (increment miss counter)
- [ ] T042 [US3] Implement start_metrics_server() in docker/patches/metrics_exporter.py (start prometheus_client HTTP server on port 9090)
- [ ] T043 [US3] Integrate metrics recording calls into factories.py response processing
- [ ] T044 [P] [US3] Integration test for metrics server responds on port 9090 in tests/integration/test_metrics_endpoint.py
- [ ] T045 [P] [US3] Integration test for Prometheus scrape format compliance in tests/integration/test_metrics_endpoint.py

**Checkpoint**: All user stories should now be independently functional - Prometheus monitoring enabled

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, final validation, and release preparation

- [ ] T046 [P] Create docs/prompt-caching.md with user-facing feature documentation (OpenRouter approach)
- [ ] T047 [P] Update README.md with link to prompt caching documentation
- [ ] T048 [P] Add comprehensive cache configuration examples to config/.env.example comments
- [ ] T049 [P] Create CHANGELOG entry for v1.4.0 with prompt caching feature
- [ ] T050 Run full test suite (unit + integration) and verify all tests pass
- [ ] T051 Verify SC-001: 40%+ token cost reduction on cache hits
- [ ] T052 Verify SC-003: Complete caching metrics (10 fields) in 100% of Gemini responses
- [ ] T053 Verify SC-006: Prometheus /metrics endpoint exposes cache stats

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ────────────────────────────────────────────────────────────┐
    |                                                                       |
    v                                                                       |
Phase 2: Foundational ─────────────────────────────────────────────────────┤
    |                                                                       |
    +─────────────────────+─────────────────────+───────────────────────────┤
    v                     v                     v                           |
Phase 3: US1 (P1)    Phase 4: US2 (P2)    Phase 5: US3 (P3)                |
    |                     |                     |                           |
    +─────────────────────+─────────────────────+──────────────┐            |
                                                               v            |
                                                        Phase 6: Polish ────┘
```

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3, 4, 5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 -> P2 -> P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Uses CacheMetrics from Foundational, can run parallel to US1
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Uses metrics_exporter from Foundational, can run parallel to US1/US2

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD)
- Dataclasses before methods using them
- Core logic before integration points
- Unit tests before integration tests
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1 (5 parallel):**
```
T002, T003, T004, T005, T006 can run in parallel after T001
```

**Phase 2 (4 parallel):**
```
T007, T008, T009, T010 can all run in parallel (different files/classes)
```

**Phase 3 - US1 (mixed):**
```
Tests (parallel):     T011, T012, T013, T014
Implementation:       T015 -> T016 -> T017 -> T018 -> T019 -> T020 (sequential)
Integration tests:    T021, T022, T023 (parallel, after implementation)
```

**Phase 4 - US2 (mixed):**
```
Tests (parallel):     T024, T025, T026, T027
Implementation:       T028 -> T029 -> T030 -> T031 -> T032 (mostly sequential)
Integration tests:    T033, T034 (parallel, after implementation)
```

**Phase 5 - US3 (mixed):**
```
Tests (parallel):     T035, T036, T037
Implementation:       T038 -> T039 -> T040 -> T041 -> T042 -> T043 (sequential)
Integration tests:    T044, T045 (parallel, after implementation)
```

**Phase 6 (4 parallel + 3 sequential):**
```
Docs (parallel):      T046, T047, T048, T049
Validation:           T050 first, then T051-T053 (sequential verification)
```

---

## Critical Files Reference

| File | Purpose | Phase |
|------|---------|-------|
| docker/patches/message_formatter.py | **NEW** - Multipart format + cache_control markers | US1 |
| docker/patches/cache_metrics.py | CacheMetrics dataclass + PricingTier + extraction | Foundational + US1 + US2 |
| docker/patches/session_metrics.py | SessionMetrics tracking | Foundational + US2 |
| docker/patches/metrics_exporter.py | **NEW** - Prometheus/OpenTelemetry metrics | Foundational + US3 |
| docker/patches/factories.py | **MODIFIED** - Integrate message formatter + metrics | US1 + US2 + US3 |
| tests/unit/test_message_formatter.py | Unit tests for message formatting | US1 |
| tests/unit/test_cache_metrics.py | Unit tests for metrics extraction | Foundational + US1 + US2 |
| tests/unit/test_session_metrics.py | Unit tests for session tracking | US2 |
| tests/integration/test_caching_e2e.py | E2E caching tests | US1 + US2 |
| tests/integration/test_metrics_endpoint.py | Prometheus endpoint tests | US3 |

---

## What Is NOT Included (Corrected Architecture)

The following tasks from the previous (incorrect) task list have been REMOVED:

| Removed Task | Reason |
|--------------|--------|
| google-generativeai SDK dependency | OpenRouter handles caching, no SDK needed |
| CacheEntry entity | OpenRouter manages cache entries internally |
| PromptCache LRU class | OpenRouter manages cache lifecycle |
| Cache creation via google.genai.caches.create() | Not applicable to OpenRouter approach |
| Cache TTL management | OpenRouter manages TTL automatically |
| Health endpoint modification | Using Prometheus /metrics instead |
| GeminiCachingClient wrapper | Using message formatter + existing client |

---

## Entity to Task Mapping (Corrected)

| Entity (data-model.md) | Tasks | User Story |
|------------------------|-------|------------|
| CacheMetrics | T007, T014, T018, T020, T024-T029 | Foundational, US1, US2 |
| PricingTier | T008, T020 | Foundational, US1 |
| SessionMetrics | T009, T027, T030, T032 | Foundational, US2 |
| OpenTelemetry Meter | T010, T038-T043 | Foundational, US3 |

## Contract to Task Mapping

| Contract (contracts/) | Tasks | User Story |
|----------------------|-------|------------|
| cache-response.md (CacheMetrics schema) | T007, T028-T034 | Foundational, US2 |
| metrics.md (Prometheus endpoint) | T010, T035-T045 | Foundational, US3 |

---

## Summary

| Metric | Count |
|--------|-------|
| **Total Tasks** | 53 |
| **Phase 1 (Setup)** | 6 tasks |
| **Phase 2 (Foundational)** | 4 tasks |
| **Phase 3 (US1 - P1)** | 13 tasks |
| **Phase 4 (US2 - P2)** | 11 tasks |
| **Phase 5 (US3 - P3)** | 11 tasks |
| **Phase 6 (Polish)** | 8 tasks |
| **Parallel Opportunities** | 31 tasks (58%) |
| **MVP Scope** | 23 tasks (Setup + Foundational + US1) |

---

## Notes

- [P] tasks = different files, no dependencies
- [US#] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- File paths use docker/patches/ per plan.md project structure
- **OpenRouter manages cache lifecycle** - no cache create/delete operations needed
- **Prometheus metrics** - not health endpoint modification
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
