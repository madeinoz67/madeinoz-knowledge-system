# Impact Analysis: OpenRouter Proxy Architecture Correction

**Feature**: 006-gemini-prompt-caching
**Date**: 2026-01-27 (SECOND CORRECTION)
**Author**: Algorithm Agent (Vera Sterling)
**Type**: Architectural Correction (Iteration 2)

---

## Executive Summary

**SECOND CORRECTION APPLIED**: The previous revision incorrectly stated that OpenRouter provides "automatic implicit caching" with no configuration needed. This was WRONG.

**Correct Understanding**:
- OpenRouter caching requires **explicit `cache_control` markers** in requests
- Requests must use **multipart message content format** (not simple strings)
- OpenRouter manages cache **lifecycle** automatically (no create/delete API)
- This is a **middle ground** between direct Gemini SDK (full manual) and "fully automatic" (doesn't exist)

This document analyzes the impact on all planning artifacts and tasks, reflecting the CORRECTED understanding.

---

## What Was Wrong in Previous Update

| Previous Claim | Reality |
|----------------|---------|
| "OpenRouter provides automatic implicit caching" | Caching requires explicit `cache_control` markers |
| "No configuration needed" | Must convert to multipart message format |
| "Simply extract metrics from responses" | Must also modify request format |
| "Low complexity" | Moderate complexity (request transformation needed) |
| "3 new Python files" | 4 new Python files (add message_formatter.py) |
| "4-8 hours effort" | 6-12 hours effort |
| "~35 tasks" | ~40 tasks |

---

## Root Cause

**Configuration Reality** (from `config/.env.example`):
```bash
MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL=https://openrouter.ai/api/v1
MADEINOZ_KNOWLEDGE_MODEL_NAME=google/gemini-2.0-flash-001
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openai  # OpenAI-compatible API!
```

The system uses the **OpenAI-compatible API** to access Gemini models through OpenRouter, NOT the native Gemini SDK. This means:

1. **No direct access** to `google.genai.caches` API
2. **Must add `cache_control` markers** in multipart message format
3. **OpenRouter manages lifecycle** (TTL, eviction) automatically
4. **Metrics available** via `usage.cached_tokens` and `cache_discount` fields
5. **No SDK dependencies** required (still true)

---

## Artifact Impact Assessment

### research.md

| Section | Status | Action Required |
|---------|--------|-----------------|
| Section 1: SDK Implementation | INVALID | Rewritten for OpenRouter |
| Section 2: Metrics Calculation | VALID | Updated data source |
| Section 3: LRU Eviction | INVALID | Simplified to counters |
| Section 4: Docker Dependencies | INVALID | Removed (no new deps) |
| Section 5: Cost Calculation | VALID | Updated pricing source |
| Section 6: Integration | INVALID | Simplified architecture |
| Section 7: OpenRouter | NEW | Added OpenRouter documentation |

**Action**: COMPLETED - research.md has been fully rewritten.

---

### plan.md

| Section | Status | Action Required |
|---------|--------|-----------------|
| Summary | INVALID | Rewritten |
| Technical Context | INVALID | Updated dependencies |
| Project Structure | INVALID | Fewer files needed |
| Implementation Phases | INVALID | Simplified phases |
| Environment Variables | INVALID | Fewer variables |

**Action**: COMPLETED - plan.md has been fully rewritten.

---

### data-model.md

| Entity | Status | Notes |
|--------|--------|-------|
| CacheMetrics | VALID | Same fields, different source (OpenRouter) |
| CacheConfiguration | PARTIALLY VALID | TTL/size not configurable via OpenRouter |
| CacheEntry | INVALID | No local cache entries with OpenRouter |
| SessionMetrics | VALID | Still needed for aggregation |
| PricingTier | VALID | Updated for OpenRouter pricing |

**Action**: Minor updates recommended but not blocking.

---

### contracts/cache-response.md

| Schema | Status | Notes |
|--------|--------|-------|
| CacheMetrics | VALID | Response format unchanged |
| Example responses | VALID | Same structure |
| Validation invariants | VALID | Same rules apply |

**Action**: NO CHANGES NEEDED - contract remains valid.

---

### contracts/health-endpoint.md

| Schema | Status | Notes |
|--------|--------|-------|
| CacheHealth | VALID | Same structure |
| CacheStats | PARTIALLY VALID | Some stats not available (no local cache) |
| SessionMetrics | VALID | Same structure |

**Action**: Minor updates - remove local cache stats that don't apply.

---

### tasks.md - DETAILED TASK ANALYSIS

#### Phase 1: Setup - MOSTLY INVALID

| Task ID | Description | Status | Reason |
|---------|-------------|--------|--------|
| T001 | Create requirements-cache.txt | INVALID | No SDK needed |
| T002 | Update Dockerfile | INVALID | No changes needed |
| T003 | Add PROMPT_CACHE_ENABLED env var | VALID | Can keep for metrics toggle |
| T004 | Add PROMPT_CACHE_TTL env var | INVALID | OpenRouter controls TTL |
| T005 | Add PROMPT_CACHE_SIZE_MB env var | INVALID | OpenRouter controls size |
| T006 | Add PROMPT_CACHE_MIN_TOKENS env var | INVALID | OpenRouter controls threshold |

**Summary**: 5/6 tasks INVALID

#### Phase 2: Foundational - MOSTLY INVALID

| Task ID | Description | Status | Reason |
|---------|-------------|--------|--------|
| T007 | Implement CacheEntry dataclass | INVALID | No local cache entries |
| T008 | Implement PromptCache class (LRU) | INVALID | No local cache management |
| T009 | Implement PricingTier dictionary | VALID | Still needed for cost calculation |
| T010 | Implement CacheConfiguration | PARTIALLY VALID | Simplified (fewer fields) |

**Summary**: 2/4 tasks INVALID, 1 partially valid

#### Phase 3: US1 - Automatic Caching - MAJOR CHANGES

| Task ID | Description | Status | Reason |
|---------|-------------|--------|--------|
| T011-T014 | Unit tests for CacheEntry/PromptCache | INVALID | No local cache |
| T015 | GeminiCachingClient wrapper | INVALID | No wrapper needed |
| T016 | Cache creation via google.genai | INVALID | Not applicable |
| T017 | Prompt hash calculation | INVALID | Not needed (OpenRouter handles) |
| T018 | Cache lookup/hit detection | CHANGED | Just read cached_tokens from response |
| T019 | TTL management | INVALID | OpenRouter controls |
| T020 | Minimum token threshold | INVALID | OpenRouter controls |
| T021 | Modify factories.py for caching client | CHANGED | Add response extraction only |
| T022-T024 | Integration tests | VALID | Test against OpenRouter responses |

**Summary**: 10/14 tasks INVALID or CHANGED

#### Phase 4: US2 - Metrics Reporting - MOSTLY VALID

| Task ID | Description | Status | Reason |
|---------|-------------|--------|--------|
| T025-T028 | Unit tests for CacheMetrics | VALID | Same tests, different source |
| T029 | Implement CacheMetrics dataclass | VALID | Same fields |
| T030 | Implement calculate_request_cost | VALID | Same calculation |
| T031 | CacheMetrics.from_usage_metadata() | CHANGED | from_openrouter_response() |
| T032 | Response metadata enhancement | VALID | Same embedding |
| T033 | SessionMetrics dataclass | VALID | Same structure |
| T034 | Session metrics accumulation | VALID | Same logic |
| T035-T036 | Integration tests | VALID | Same tests |

**Summary**: 1/12 tasks CHANGED, rest VALID

#### Phase 5: US3 - Monitoring - PARTIALLY VALID

| Task ID | Description | Status | Reason |
|---------|-------------|--------|--------|
| T037-T039 | Health endpoint tests | VALID | Same tests |
| T040 | CacheHealth dataclass | VALID | Same structure |
| T041 | CacheStats dataclass | CHANGED | Fewer fields (no local cache stats) |
| T042 | get_cache_health() method | CHANGED | Simpler (session metrics only) |
| T043 | Extend health endpoint | VALID | Same enhancement |
| T044-T046 | Logging and headers | VALID | Same implementation |

**Summary**: 2/10 tasks CHANGED, rest VALID

#### Phase 6: Polish - MOSTLY VALID

| Task ID | Description | Status | Reason |
|---------|-------------|--------|--------|
| T047-T050 | Documentation | VALID | Still needed |
| T051 | Full test suite | VALID | Run all tests |
| T052-T059 | Success criteria verification | MOSTLY VALID | Some criteria changed |

**Summary**: Minor adjustments only

---

## Summary of Invalid Tasks

| Phase | Total Tasks | Invalid/Changed | Valid |
|-------|-------------|-----------------|-------|
| Phase 1: Setup | 6 | 5 | 1 |
| Phase 2: Foundational | 4 | 3 | 1 |
| Phase 3: US1 | 14 | 12 | 2 |
| Phase 4: US2 | 12 | 1 | 11 |
| Phase 5: US3 | 10 | 2 | 8 |
| Phase 6: Polish | 13 | 2 | 11 |
| **TOTAL** | **59** | **25 (42%)** | **34 (58%)** |

---

## Tasks That Must Be REMOVED

The following tasks should be completely removed from the revised tasks.md:

```
T001, T002, T004, T005, T006  (Phase 1 - no SDK/Dockerfile changes)
T007, T008                      (Phase 2 - no local cache)
T011, T012, T013, T014         (Phase 3 - no CacheEntry/PromptCache tests)
T015, T016, T017, T019, T020   (Phase 3 - no caching client/management)
```

**Total removed**: 15 tasks

---

## Tasks That Must Be CHANGED

The following tasks need modification:

| Task | Original | Revised |
|------|----------|---------|
| T010 | CacheConfiguration (full) | CacheConfiguration (simplified: enabled, log_requests only) |
| T018 | Cache lookup in wrapper | Extract cached_tokens from OpenRouter response |
| T021 | Wire up caching client | Add response post-processing |
| T031 | from_usage_metadata() | from_openrouter_response() |
| T041 | CacheStats (local cache) | CacheStats (session only) |
| T042 | get_cache_health() (complex) | get_cache_health() (simple counters) |

**Total changed**: 6 tasks

---

## NEW Tasks Required (CORRECTED 2026-01-27)

The following new tasks should be added:

| New ID | Description | Phase |
|--------|-------------|-------|
| NEW-01 | Create `convert_to_multipart()` function | Phase 1 (NEW) |
| NEW-02 | Create `add_cache_control()` function | Phase 1 (NEW) |
| NEW-03 | Create `should_enable_caching()` check function | Phase 1 (NEW) |
| NEW-04 | Unit tests for message_formatter.py | Phase 1 (NEW) |
| NEW-05 | Create extract_from_openrouter_response() utility | Phase 2 |
| NEW-06 | Add request preprocessing to factories.py | Phase 3 |
| NEW-07 | Document OpenRouter explicit caching (not automatic) in README | Phase 5 |
| NEW-08 | Link to OpenRouter activity dashboard for analytics | Phase 5 |

**Tasks NOT needed** (OpenRouter handles automatically):
- Cache creation API calls
- Cache deletion/invalidation
- TTL management
- Cache naming or sharing

---

## Effort Comparison (CORRECTED 2026-01-27)

| Metric | Original | Previous "Revised" (WRONG) | Corrected |
|--------|----------|---------------------------|-----------|
| Total Tasks | 59 | ~35 | **~40** |
| New Files | 6 | 3 | **4** |
| Modified Files | 2 | 1 | 1 |
| Test Files | 4 | 2 | **3** |
| Estimated Hours | 16-24 | 4-8 | **6-12** |

**Explanation of Correction**:
- +1 new file: `message_formatter.py` for request transformation
- +1 test file: Unit tests for message formatter
- +5 tasks: Message format conversion, multipart handling, cache_control insertion
- +2-4 hours: Request preprocessing implementation and testing

---

## Recommendation (CORRECTED 2026-01-27)

**IMMEDIATE ACTION**: Regenerate tasks.md with the corrected task list based on this analysis.

The corrected implementation is **moderately simpler** than original (not "significantly simpler"):

**Still True**:
1. No Gemini SDK dependency
2. No Docker/container changes
3. No LRU cache management
4. Still delivers all user-facing features (cost transparency, health monitoring)

**New Requirements** (previously missed):
5. **Request format modification** - convert simple messages to multipart
6. **cache_control marker insertion** - add `{"type": "ephemeral"}` to cacheable content
7. **Conditional formatting** - only apply to Gemini models via OpenRouter

**Implementation Priority**:
1. **Phase 1 FIRST**: message_formatter.py is the critical new component
2. Phase 2: metrics extraction (unchanged)
3. Phase 3: wire up request preprocessing AND response post-processing

---

## Requirement Clarification: Metrics Approach (2026-01-27)

**User Feedback**: "I don't want an API endpoint for cache stats, however OpenTelemetry or Prometheus metrics exposed would be better"

### What Changed

| Aspect | Original (Health Endpoint) | Revised (Prometheus Metrics) |
|--------|---------------------------|------------------------------|
| Format | JSON response on /health | Prometheus text format on /metrics |
| Contract | contracts/health-endpoint.md | contracts/metrics.md |
| Implementation | Extend existing health endpoint | New OpenTelemetry instrumentation |
| Dependencies | None | opentelemetry-*, prometheus-client |
| Port | Same as MCP server | Separate port (9090) |
| Scraping | Manual/custom | Standard Prometheus scrape |

### Documents Updated

| Document | Change |
|----------|--------|
| spec.md | User Story 3 acceptance criteria updated |
| spec.md | FR-008 changed to Prometheus endpoint |
| spec.md | SC-006 changed to Prometheus scraping |
| spec.md | Dependencies updated with OpenTelemetry |
| research.md | Section 8 added for metrics framework decision |
| plan.md | Phase 4 renamed to Prometheus Metrics Instrumentation |
| plan.md | Project structure includes metrics_exporter.py |
| plan.md | Dependencies updated |
| data-model.md | Prometheus metrics schema added |
| data-model.md | Backward compatibility updated |
| contracts/health-endpoint.md | DELETED |
| contracts/metrics.md | CREATED |

### Task Impact

| Original Tasks | Status |
|----------------|--------|
| Health endpoint extension tasks | REMOVED |
| CacheHealth dataclass | REMOVED |
| X-Cache-Status header | OPTIONAL (can keep if useful) |

| New Tasks | Added |
|-----------|-------|
| Create metrics_exporter.py | ADDED |
| Add OpenTelemetry dependencies | ADDED |
| Unit tests for metrics | ADDED |
| Document metrics endpoint | ADDED |

### Estimated Impact

- **Removed tasks**: ~3-4 (health endpoint specific)
- **Added tasks**: ~4-5 (metrics instrumentation)
- **Net change**: Similar task count, different focus
- **Complexity**: Similar overall (metrics instrumentation vs endpoint extension)

---

## Files Updated

| File | Status | Date |
|------|--------|------|
| spec.md | UPDATED (US3, FR-008, SC-006, dependencies) | 2026-01-27 |
| research.md | UPDATED (Section 8 added) | 2026-01-27 |
| plan.md | UPDATED (Phase 4, dependencies, structure) | 2026-01-27 |
| data-model.md | UPDATED (metrics schema, compatibility) | 2026-01-27 |
| contracts/cache-response.md | NO CHANGE | - |
| contracts/health-endpoint.md | DELETED | 2026-01-27 |
| contracts/metrics.md | CREATED | 2026-01-27 |
| impact-analysis.md | UPDATED (this section) | 2026-01-27 |
| tasks.md | NEEDS REGENERATION | - |

---

## Three-Tier Comparison (Definitive Reference)

| Aspect | Direct Gemini SDK | OpenRouter (CORRECT) | "Fully Automatic" (WRONG) |
|--------|-------------------|----------------------|---------------------------|
| Enable caching | SDK: `cache.create()` | Request: `cache_control` marker | N/A - would be automatic |
| Lifecycle mgmt | Manual (create/delete/TTL) | Automatic (OpenRouter) | N/A |
| Request format | `GenerateContentConfig` | Multipart messages with markers | Simple strings |
| SDK dependency | `google-generativeai>=0.8.0` | None (existing OpenAI SDK) | None |
| Storage costs | Per-hour billing | Included | N/A |
| Complexity | **High** | **Moderate** | Low (doesn't exist) |

**Key Insight**: OpenRouter is the **correct middle ground** - explicit request markers (like Anthropic), automatic lifecycle (unlike Anthropic), no SDK (unlike direct Gemini).
