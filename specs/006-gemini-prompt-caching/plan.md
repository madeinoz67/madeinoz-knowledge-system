# Implementation Plan: Gemini Prompt Caching with Cost Reporting

**Branch**: `006-gemini-prompt-caching` | **Date**: 2026-01-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-gemini-prompt-caching/spec.md`

**Status**: REVISED for OpenRouter Proxy Architecture

---

## Summary

Implement request format modification and cache metrics extraction for Gemini models accessed via OpenRouter proxy. The system will convert simple messages to multipart format with `cache_control` markers, then extract cache metrics from OpenRouter responses (`cached_tokens`, `cache_discount`) and embed cost savings information in MCP tool responses. This is **simpler than direct Gemini SDK but NOT trivial** - it requires request format transformation.

**Key Change from Original Plan (CORRECTED 2026-01-27)**: No Gemini SDK required. OpenRouter caching requires **explicit `cache_control` markers** in requests (similar to Anthropic), but manages cache lifecycle automatically. Implementation requires a message format wrapper to convert simple string messages to multipart content with caching markers.

---

## Technical Context

**Language/Version**: Python 3.10+ (existing graphiti_mcp image)
**Primary Dependencies**:
- Existing: OpenAI-compatible client via OpenRouter
- New: opentelemetry-api, opentelemetry-sdk, opentelemetry-exporter-prometheus, prometheus-client
**Storage**: In-memory session metrics (simple counters, not LRU cache)
**Testing**: pytest (existing), integration tests against OpenRouter responses
**Target Platform**: Docker/Podman container (existing graphiti_mcp image)
**Project Type**: Single container with patches
**Performance Goals**: <10ms overhead for request format modification + metrics extraction per request
**Constraints**: No external dependencies, graceful degradation if metrics unavailable
**Scale/Scope**: Single-instance deployment, session-level metrics

**CORRECTED 2026-01-27**: Implementation is **moderate complexity** (not low). Requires:
- Request format wrapper (convert simple strings to multipart with `cache_control`)
- Message restructuring for system prompts
- Metrics extraction from responses (unchanged)

---

## Constitution Check

**GATE**: Verified - implementation is simpler than original plan.

| Gate | Status | Notes |
|------|--------|-------|
| No new external dependencies | PASS | Uses existing OpenAI client |
| Minimal code changes | PASS | Metrics extraction + response enhancement only |
| No breaking changes | PASS | cache_metrics field is additive |
| Graceful degradation | PASS | Missing metrics = omit field |

---

## Project Structure

### Documentation (this feature)

```text
specs/006-gemini-prompt-caching/
├── plan.md              # This file (REVISED)
├── research.md          # Phase 0 output (REVISED for OpenRouter + metrics)
├── data-model.md        # Phase 1 output (still valid)
├── contracts/           # Phase 1 output (REVISED)
│   ├── cache-response.md   # Response metadata format
│   └── metrics.md          # NEW: Prometheus metrics format (replaces health-endpoint.md)
├── impact-analysis.md   # Documents changes from original design
└── tasks.md             # Phase 2 output (NEEDS REVISION)
```

### Source Code (repository root)

```text
docker/patches/
├── cache_metrics.py         # NEW: CacheMetrics dataclass + extraction logic
├── pricing_calculator.py    # NEW: Cost calculation for OpenRouter Gemini models
├── session_metrics.py       # NEW: Session-level aggregation counters
├── message_formatter.py     # NEW: Convert simple messages to multipart with cache_control
├── metrics_exporter.py      # NEW: OpenTelemetry/Prometheus metrics instrumentation
└── factories.py             # MODIFY: Add request preprocessing + response post-processing

# NOT NEEDED (removed from original plan):
# ├── requirements-cache.txt  # REMOVED - minimal new dependencies only
# ├── gemini_caching_client.py  # REMOVED - no explicit cache management
# └── prompt_cache.py           # REMOVED - no LRU cache needed
```

**Structure Decision (CORRECTED)**: Five new Python files. The key additions are `message_formatter.py` for request format transformation and `metrics_exporter.py` for OpenTelemetry/Prometheus instrumentation. Moderate modification to factories.py for request preprocessing AND response post-processing. Dockerfile needs minor update for OpenTelemetry dependencies.

---

## Comparison: Original vs Revised Approach (CORRECTED 2026-01-27)

| Aspect | Original Plan | Revised Plan (CORRECTED) |
|--------|---------------|--------------------------|
| SDK Dependency | google-generativeai>=0.8.0 | None (existing) |
| Dockerfile Changes | Install new requirements | None |
| Cache Enablement | SDK: `caches.create()` | Request: `cache_control` markers |
| Cache Lifecycle | Manual (create, TTL, delete) | Automatic (OpenRouter) |
| Request Format | N/A (SDK handles) | Multipart messages with markers |
| Code Complexity | High (wrapper client, LRU cache) | **Moderate** (message formatter + metrics) |
| New Files | 6 | 4 |
| Modified Files | 2 | 1 |
| Risk Level | Medium | **Low-Medium** |
| Implementation Time | 2-3 days | **0.5-1.5 days** |

**Note**: Previous "Revised Plan" claimed "Low complexity" and "0.5-1 day" - this was INCORRECT. The need for request format modification adds moderate complexity.

---

## Implementation Phases (CORRECTED 2026-01-27)

### Phase 1: Request Format Modification (NEW - CRITICAL)

**Purpose**: Convert simple messages to multipart format with `cache_control` markers

**Files to Create**:
1. `docker/patches/message_formatter.py`:
   - `convert_to_multipart()` function - convert simple string messages to multipart content
   - `add_cache_control()` function - add `{"type": "ephemeral"}` markers
   - `should_enable_caching()` function - check if Gemini model via OpenRouter
   - Support for system prompt caching (primary use case)

**Example Transformation**:
```python
# INPUT: Simple message format
{"role": "system", "content": "System prompt text..."}

# OUTPUT: Multipart format with cache_control
{"role": "system", "content": [
    {"type": "text", "text": "System prompt text...", "cache_control": {"type": "ephemeral"}}
]}
```

**Checkpoint**: Can transform requests to include cache_control markers

### Phase 2: Metrics Extraction (Core)

**Purpose**: Extract cache metrics from OpenRouter responses

**Files to Create**:
1. `docker/patches/cache_metrics.py`:
   - CacheMetrics dataclass (10 fields per data-model.md)
   - `extract_from_openrouter_response()` function
   - `CacheMetrics.to_dict()` method

2. `docker/patches/pricing_calculator.py`:
   - OpenRouter Gemini pricing constants
   - `calculate_request_cost()` function
   - Support for `cache_discount` field from response

3. `docker/patches/session_metrics.py`:
   - SessionMetrics dataclass
   - `record_request()` method
   - `cache_hit_rate` property

**Checkpoint**: Can extract metrics from OpenRouter response JSON

### Phase 3: Request/Response Integration

**Purpose**: Wire up request preprocessing AND response post-processing

**Files to Modify**:
1. `docker/patches/factories.py` (or appropriate handler):
   - **REQUEST preprocessing**: Call `convert_to_multipart()` before LLM call
   - **RESPONSE post-processing**: Call `extract_from_openrouter_response()` after LLM call
   - Check if Gemini model via OpenRouter
   - Embed cache_metrics in MCP response

**Checkpoint**: MCP responses include cache_metrics field for Gemini models with caching enabled

### Phase 4: Prometheus Metrics Instrumentation

**Purpose**: Expose cache metrics via OpenTelemetry/Prometheus endpoint

**Files to Create**:
1. `docker/patches/metrics_exporter.py`:
   - Initialize OpenTelemetry with Prometheus exporter
   - Define cache metrics (counters and gauges)
   - `record_cache_hit()` and `record_cache_miss()` functions
   - Start metrics HTTP server on port 9090

**Metrics Defined**:
- `graphiti_cache_hits_total` (counter)
- `graphiti_cache_misses_total` (counter)
- `graphiti_cache_tokens_saved_total` (counter)
- `graphiti_cache_cost_saved_total` (counter)
- `graphiti_cache_hit_rate` (gauge)
- `graphiti_cache_entries` (gauge)
- `graphiti_cache_size_bytes` (gauge)

**Dependencies to Add**:
```
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-exporter-prometheus>=0.41b0
prometheus-client>=0.17.0
```

**Checkpoint**: `/metrics` endpoint exposes Prometheus-format cache statistics

### Phase 5: Testing & Documentation

**Purpose**: Verify implementation and document for users

**Implementation**:
1. Unit tests for message formatter (multipart conversion)
2. Unit tests for CacheMetrics extraction
3. Unit tests for pricing calculations
4. Integration test with mock OpenRouter responses
5. Update README with cache metrics documentation
6. Add CHANGELOG entry

**Checkpoint**: All tests pass, documentation complete

---

## Environment Variables (SIMPLIFIED)

```bash
# Enable/disable cache metrics in responses (default: true)
MADEINOZ_KNOWLEDGE_PROMPT_CACHE_METRICS_ENABLED=true

# Log cache metrics for each request (default: false, for debugging)
MADEINOZ_KNOWLEDGE_PROMPT_CACHE_LOG_REQUESTS=false
```

**Note**: No TTL, cache size, or min tokens variables needed - OpenRouter handles all cache configuration automatically.

---

## What Still Works from Original Design

The following artifacts remain valid:

| Artifact | Status | Notes |
|----------|--------|-------|
| data-model.md | VALID | CacheMetrics fields same as OpenRouter provides |
| contracts/cache-response.md | VALID | Response schema unchanged |
| contracts/health-endpoint.md | VALID | Health schema unchanged |
| spec.md | VALID | User stories still apply |
| FR-001 to FR-015 | MOSTLY VALID | Some FRs simplified (no TTL control) |

---

## What Changes from Original Design

| Original Requirement | Changed To |
|----------------------|------------|
| FR-007: Respect Gemini TTL limits | N/A - OpenRouter controls TTL |
| FR-011: Configurable cache TTL | N/A - OpenRouter automatic |
| FR-012: Cache size limits | N/A - OpenRouter manages |
| FR-013: LRU eviction | N/A - OpenRouter manages |
| FR-014: Docker image dependencies | Removed - no new deps |
| FR-015: Validate Gemini API caching | Changed to: Check OpenRouter model |

---

## Complexity Tracking (CORRECTED 2026-01-27)

> **Moderate complexity** - simpler than original but NOT trivial.

| Original Complexity | Simplified To (CORRECTED) |
|---------------------|---------------------------|
| 6 new Python files | 4 new Python files |
| 2 Dockerfile changes | 0 Dockerfile changes |
| LRU cache with TTL | Simple counters |
| Gemini SDK wrapper | **Message format wrapper** |
| Explicit cache lifecycle | Automatic (OpenRouter) |
| No request changes | **Request format modification** |

**Previous incorrect claim**: "3 new Python files" and "Response extraction only"
**Corrected**: 4 new files including message_formatter.py for request transformation

---

## Risk Assessment (CORRECTED 2026-01-27)

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| OpenRouter removes cached_tokens field | Very Low | Medium | Graceful degradation |
| Pricing estimates inaccurate | Low | Low | Use cache_discount when available |
| Metrics extraction breaks on API change | Low | Low | Unit tests + version check |
| **Multipart format breaks other providers** | **Medium** | **Medium** | **Conditional formatting based on model** |
| **cache_control marker changes** | **Low** | **Medium** | **Abstract behind function, easy to update** |
| **Minimum token threshold not met** | **Medium** | **Low** | **Log when caching unavailable, no error** |

**NEW RISK CATEGORY**: Request format modification introduces potential compatibility issues with non-Gemini models. The `should_enable_caching()` check is critical to prevent breaking other providers.

---

## Next Steps (CORRECTED 2026-01-27)

1. **IMMEDIATE**: Regenerate tasks.md with corrected task list (~40 tasks)
2. **Phase 1**: Implement message formatter (1 new file - CRITICAL)
3. **Phase 2**: Implement metrics extraction (3 files)
4. **Phase 3**: Wire up request preprocessing AND response post-processing (1 file modification)
5. **Phase 4**: Enhance health endpoint
6. **Phase 5**: Tests and documentation

**Estimated Total Effort**: 6-12 hours (down from 16-24 hours original, but NOT as low as previously claimed 4-8 hours)

**Previous incorrect estimate**: "4-8 hours" assumed passive metrics extraction only.
**Corrected**: Request format modification adds ~2-4 hours of implementation and testing.
