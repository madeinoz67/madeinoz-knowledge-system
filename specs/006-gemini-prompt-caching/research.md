# Research & Technical Decisions: Gemini Prompt Caching

**Feature**: 006-gemini-prompt-caching
**Date**: 2026-01-27
**Status**: Phase 0 Complete (REVISED for OpenRouter Architecture)
**Author**: Algorithm Agent (Vera Sterling)

---

## Executive Summary

This document captures research findings and technical decisions for implementing Gemini prompt caching with cost reporting in the Madeinoz Knowledge System.

**CRITICAL ARCHITECTURAL UPDATE (2026-01-27, CORRECTED)**: The system uses Gemini through OpenRouter proxy, NOT direct Gemini API. OpenRouter caching requires **explicit `cache_control` markers** in requests (similar to Anthropic), but manages cache lifecycle automatically (unlike direct Gemini SDK). This requires request format modification from simple strings to multipart messages with cache_control breakpoints.

**Previous incorrect assumption**: "OpenRouter provides automatic implicit caching" - this was WRONG. Caching must be explicitly enabled via request markers.

---

## Research Questions & Decisions

### 1. Gemini SDK Caching API Implementation Details

**Decision**: ~~Use Gemini's **Explicit Caching** via `google.genai.caches` module~~ **REVISED (CORRECTED 2026-01-27)**: Use **OpenRouter's Explicit Marker Caching** with automatic lifecycle management - no Gemini SDK required, but request format modification needed.

**Rationale (CORRECTED)**:
- The system uses Gemini via OpenRouter proxy (`OPENAI_BASE_URL=https://openrouter.ai/api/v1`)
- OpenRouter caching requires **explicit `cache_control` markers** in request messages (NOT automatic)
- Requests must use **multipart message content format** (not simple strings)
- OpenRouter manages cache lifecycle automatically (no create/delete API)
- Cache metrics are returned in response via `usage.cached_tokens` and `cache_discount` fields

**Current Configuration**:
```bash
MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL=https://openrouter.ai/api/v1
MADEINOZ_KNOWLEDGE_MODEL_NAME=google/gemini-2.0-flash-001
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openai  # OpenAI-compatible API
```

**Alternatives Considered**:
| Alternative | Why Rejected |
|-------------|--------------|
| Direct Gemini SDK with explicit caching | Would require switching from OpenRouter proxy, losing multi-provider flexibility |
| Client-side prompt caching | Doesn't reduce API costs, only local compute |
| ~~OpenRouter proxy caching~~ | **SELECTED** - This IS our architecture |

**Implementation Implications (CORRECTED)**:
- No `google.genai` SDK needed - use existing OpenAI-compatible client
- **Request format modification required** - convert to multipart messages with `cache_control`
- No cache lifecycle management code (OpenRouter handles TTL/eviction)
- Extract metrics from OpenRouter response fields
- **Moderate complexity** - requires message format wrapper, not simple passive extraction

**OpenRouter Response Format**:
```json
{
  "choices": [...],
  "usage": {
    "prompt_tokens": 2500,
    "completion_tokens": 150,
    "cached_tokens": 1800
  },
  "cache_discount": 0.45
}
```

**Sources**:
- [OpenRouter Prompt Caching Best Practices](https://openrouter.ai/docs/guides/best-practices/prompt-caching)
- [OpenRouter API Response Format](https://openrouter.ai/docs/responses)

---

### 7. OpenRouter Proxy Architecture (CORRECTED 2026-01-27)

**Decision**: Modify request format to add `cache_control` markers, then extract cache metrics from OpenRouter responses.

**CRITICAL CORRECTION**: OpenRouter caching is **NOT fully automatic**. It requires **explicit `cache_control` breakpoints** in the request, similar to Anthropic's caching API. However, unlike direct Gemini SDK or Anthropic, OpenRouter manages the cache lifecycle automatically (no create/delete operations).

**Rationale**:
- OpenRouter is our configured LLM gateway
- Gemini 2.5 Pro/Flash support caching on OpenRouter, but **require explicit markers**
- No storage costs for cached content (included in service)
- Cached reads billed at discounted rate automatically
- OpenRouter manages cache lifecycle (no manual TTL/delete operations)

**Request Format Requirement**:

OpenRouter requires `cache_control` breakpoints in **multipart message content** (not simple string messages):

```json
{
  "model": "google/gemini-2.0-flash-001",
  "messages": [
    {
      "role": "system",
      "content": [
        {
          "type": "text",
          "text": "Long system prompt here that will be cached...",
          "cache_control": {"type": "ephemeral"}
        }
      ]
    },
    {
      "role": "user",
      "content": "User message here"
    }
  ]
}
```

**Key Implementation Details**:
1. **Multipart format required**: Simple string messages (`"content": "text"`) do NOT enable caching
2. **`cache_control` marker**: Add `{"type": "ephemeral"}` to text blocks that should be cached
3. **Only last breakpoint used**: If multiple `cache_control` markers exist, only the last one is active
4. **Minimum token thresholds**: Model-specific (typically 1024+ tokens for Gemini)
5. **Lifecycle is automatic**: OpenRouter manages cache TTL and eviction (no create/delete API)

**OpenRouter Caching Behavior**:

| Model | Caching Type | TTL | Write Cost | Read Discount | Min Tokens |
|-------|--------------|-----|------------|---------------|------------|
| gemini-2.5-flash | Explicit marker | OpenRouter-managed | Free | ~50% | ~1024 |
| gemini-2.5-pro | Explicit marker | OpenRouter-managed | Free | ~50% | ~1024 |
| gemini-2.0-flash | Explicit marker | OpenRouter-managed | Free | ~50% | ~1024 |

**Response Format (Metrics Extraction)**:
```json
{
  "choices": [...],
  "usage": {
    "prompt_tokens": 2500,
    "completion_tokens": 150,
    "cached_tokens": 1800
  },
  "cache_discount": 0.45
}
```

**Metrics Extraction Code**:
```python
# From OpenRouter response (OpenAI-compatible format)
def extract_cache_metrics(response):
    usage = response.get("usage", {})
    return {
        "cached_tokens": usage.get("cached_tokens", 0),
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "cache_discount": response.get("cache_discount", 0.0),
    }
```

**Three-Tier Comparison (CORRECTED)**:

| Aspect | Direct Gemini SDK | OpenRouter (Correct) | Fully Automatic (WRONG) |
|--------|-------------------|----------------------|-------------------------|
| Enable caching | SDK: `cache.create()` | Request: `cache_control` marker | N/A - would be automatic |
| Lifecycle mgmt | Manual (create/delete/TTL) | Automatic (OpenRouter) | N/A |
| Request format | `GenerateContentConfig` | Multipart messages with markers | Simple strings |
| SDK dependency | `google-generativeai>=0.8.0` | None (existing OpenAI SDK) | None |
| Cache naming | Developer-provided names | Opaque (internal) | N/A |
| Storage costs | Per-hour billing | Included | N/A |
| Metrics location | `usage_metadata.cached_tokens` | `usage.cached_tokens` | N/A |
| Complexity | **High** | **Moderate** | Low (doesn't exist) |

**What We MUST Implement**:
1. **Request format wrapper**: Convert simple messages to multipart format with `cache_control`
2. **System prompt caching**: Add `cache_control` marker to system prompts
3. **Metrics extraction**: Extract `cached_tokens` and `cache_discount` from responses
4. **Cost calculation**: Calculate savings from cached token counts

**What We DO NOT Need to Implement**:
1. Cache creation API calls (OpenRouter handles lifecycle)
2. Cache deletion/invalidation
3. TTL management
4. Cache naming or sharing

**Sources**:
- [OpenRouter Prompt Caching Best Practices](https://openrouter.ai/docs/guides/best-practices/prompt-caching)
- [OpenRouter Activity Dashboard](https://openrouter.ai/activity) - view cache analytics

---

### 2. Cache Metrics Calculation Methodology

**Decision**: Extract metrics from OpenRouter response `usage` object and calculate derived metrics (savings, rates) in the MCP server layer.

**Rationale**:
- OpenRouter returns `cached_tokens` count and `cache_discount` in every response
- Cost calculations require combining token counts with current pricing data
- Derived metrics (cost_saved, hit_rate) should be computed server-side for consistency
- Session-level aggregation requires state management in the MCP server

**Alternatives Considered**:
| Alternative | Why Rejected |
|-------------|--------------|
| External metrics service | Adds complexity and latency; overkill for single-instance deployment |
| Client-side calculation | Inconsistent results; requires pricing data distribution to all clients |
| Log-only metrics | Doesn't fulfill FR-006 requirement for response metadata |

**Implementation Implications**:
- Create `CacheMetrics` data class matching FR-006 fields
- Store session-level counters for aggregate statistics
- Pricing constants must be configurable for future rate changes

**Metrics Calculation Formulas**:
```python
# Per-request metrics (from OpenRouter response)
cached_tokens = usage.get("cached_tokens", 0)
cache_discount = response.get("cache_discount", 0.0)

# Derived calculations
cache_hit = cached_tokens > 0
tokens_saved = cached_tokens

# Cost calculations
uncached_tokens = prompt_tokens - cached_tokens
cost_without_cache = (prompt_tokens * standard_input_price + completion_tokens * output_price) / 1_000_000
actual_cost = (uncached_tokens * standard_input_price + cached_tokens * cached_input_price + completion_tokens * output_price) / 1_000_000
cost_saved = cost_without_cache - actual_cost
savings_percent = (cost_saved / cost_without_cache * 100) if cost_without_cache > 0 else 0

# Session-level metrics
cache_hit_rate = total_cache_hits / total_requests * 100
cumulative_savings = sum(cost_saved for each request)
```

**Current Pricing Constants** (January 2026 - via OpenRouter):
| Model | Input ($/1M) | Cached Input ($/1M) | Output ($/1M) | Cache Discount |
|-------|-------------|---------------------|---------------|----------------|
| Gemini 2.5 Flash | $0.30 | ~$0.15 | $2.50 | ~50% |
| Gemini 2.5 Pro | $1.25 | ~$0.625 | $10.00 | ~50% |
| Gemini 2.0 Flash | $0.10 | ~$0.05 | $0.40 | ~50% |

**Note**: OpenRouter applies discounts automatically; `cache_discount` field in response gives exact percentage.

**Sources**:
- [OpenRouter Pricing](https://openrouter.ai/models)
- [OpenRouter Activity Analytics](https://openrouter.ai/activity)

---

### 3. LRU Eviction Implementation Patterns

**Decision**: **SIMPLIFIED** - No local LRU cache required for cache management. OpenRouter handles caching automatically.

**Rationale (REVISED)**:
- OpenRouter manages all cache lifecycle automatically
- No local cache entries need to be tracked for cache management
- Session metrics can use simple counters instead of LRU structure

**What We Still Need**:
- Session-level aggregation counters (not LRU, just accumulators)
- In-memory tracking of request/response metrics for health endpoint

**Simplified Implementation**:
```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class SessionMetrics:
    """Aggregated cache statistics for current session."""
    total_requests: int = 0
    cache_hits: int = 0
    total_cached_tokens: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cost_saved: float = 0.0
    session_start: datetime = field(default_factory=datetime.now)

    def record_request(self, cache_metrics: "CacheMetrics"):
        self.total_requests += 1
        if cache_metrics.cache_hit:
            self.cache_hits += 1
        self.total_cached_tokens += cache_metrics.cached_tokens
        self.total_prompt_tokens += cache_metrics.prompt_tokens
        self.total_completion_tokens += cache_metrics.completion_tokens
        self.total_cost_saved += cache_metrics.cost_saved

    @property
    def cache_hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.cache_hits / self.total_requests) * 100
```

---

### 4. Docker Image Dependency Management

**Decision**: **NO NEW DEPENDENCIES REQUIRED**.

**Rationale (REVISED)**:
- OpenRouter caching uses the existing OpenAI-compatible API client
- No `google-generativeai` SDK needed
- Graphiti already has OpenAI client support
- Caching is handled server-side by OpenRouter

**What Changes**:
- Add metrics extraction logic to existing response handling
- No Dockerfile modifications required
- No new pip dependencies

**Original Plan (DEPRECATED)**:
```dockerfile
# NO LONGER NEEDED
# COPY docker/patches/requirements-cache.txt /tmp/requirements-cache.txt
# RUN pip install -r /tmp/requirements-cache.txt
```

---

### 5. Cost Calculation Formulas for Gemini Pricing

**Decision**: Implement a `PricingCalculator` class with model-specific pricing tiers, using OpenRouter's `cache_discount` field when available.

**Rationale**:
- OpenRouter may return `cache_discount` directly in response
- When available, use `cache_discount` for actual savings calculation
- Fall back to estimated cached token pricing when `cache_discount` not present

**Implementation**:
```python
OPENROUTER_GEMINI_PRICING = {
    "google/gemini-2.5-flash": {
        "input_per_million": 0.30,
        "estimated_cached_discount": 0.50,  # ~50% discount
        "output_per_million": 2.50,
    },
    "google/gemini-2.5-pro": {
        "input_per_million": 1.25,
        "estimated_cached_discount": 0.50,
        "output_per_million": 10.00,
    },
    "google/gemini-2.0-flash-001": {
        "input_per_million": 0.10,
        "estimated_cached_discount": 0.50,
        "output_per_million": 0.40,
    },
}

def calculate_request_cost(
    model: str,
    prompt_tokens: int,
    cached_tokens: int,
    completion_tokens: int,
    cache_discount: float | None = None  # From OpenRouter response
) -> dict:
    pricing = OPENROUTER_GEMINI_PRICING.get(model, OPENROUTER_GEMINI_PRICING["google/gemini-2.0-flash-001"])

    # Use actual cache_discount if provided, otherwise estimate
    discount = cache_discount if cache_discount is not None else pricing["estimated_cached_discount"]
    cached_rate = pricing["input_per_million"] * (1 - discount)

    uncached_tokens = prompt_tokens - cached_tokens

    cost_without_cache = (prompt_tokens * pricing["input_per_million"] + completion_tokens * pricing["output_per_million"]) / 1_000_000
    actual_cost = (uncached_tokens * pricing["input_per_million"] + cached_tokens * cached_rate + completion_tokens * pricing["output_per_million"]) / 1_000_000
    cost_saved = cost_without_cache - actual_cost

    return {
        "prompt_tokens": prompt_tokens,
        "cached_tokens": cached_tokens,
        "completion_tokens": completion_tokens,
        "cost_without_cache": cost_without_cache,
        "actual_cost": actual_cost,
        "cost_saved": cost_saved,
        "savings_percent": (cost_saved / cost_without_cache * 100) if cost_without_cache > 0 else 0,
        "cache_discount_applied": discount,
    }
```

---

### 6. Integration with Existing MCP Server Architecture

**Decision**: **SIMPLIFIED** - Add response metadata extraction middleware rather than a full caching client wrapper.

**Rationale (REVISED)**:
- No need to wrap the LLM client for cache management
- Simply intercept responses and extract OpenRouter cache metrics
- Add metrics to MCP response metadata

**Implementation Approach**:
```
                    +----------------------+
                    |    MCP Server       |
                    |  (graphiti_mcp)     |
                    +----------+----------+
                               |
                    +----------v----------+
                    |  LLMClientFactory   |
                    |  (factories.py)     |
                    +----------+----------+
                               |
              +----------------+----------------+
              |                                 |
    +---------v--------+              +---------v--------+
    | OpenAI Client    |              | Other Clients    |
    | (via OpenRouter) |              | (no caching)     |
    +--------+---------+              +------------------+
             |
    +--------v------------------+
    | CacheMetricsExtractor     |
    | (response post-processor) |
    +---------------------------+
             |
    +--------v------------------+
    |    SessionMetrics         |
    | (session-level counters)  |
    +---------------------------+
```

**Response Post-Processing**:
```python
# In response handling, AFTER LLM call completes
def extract_and_embed_cache_metrics(llm_response, mcp_response):
    """Extract cache metrics from OpenRouter response and embed in MCP result."""

    # Check if this is a Gemini model via OpenRouter
    if not is_gemini_via_openrouter():
        return mcp_response

    usage = llm_response.get("usage", {})
    cache_metrics = CacheMetrics(
        cache_hit=usage.get("cached_tokens", 0) > 0,
        cached_tokens=usage.get("cached_tokens", 0),
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        # ... calculate derived fields
    )

    # Record in session metrics
    session_metrics.record_request(cache_metrics)

    # Embed in response
    mcp_response["cache_metrics"] = cache_metrics.to_dict()
    return mcp_response
```

---

## Technology Stack Decisions (REVISED)

### Primary Dependencies

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| SDK | **None new** | - | Uses existing OpenAI-compatible client |
| Metrics | dataclasses | stdlib | Type-safe metrics |
| Config | python-dotenv | existing | Environment variables |

### No New Dependencies Required
- All caching happens on OpenRouter's infrastructure
- Metrics extraction uses standard JSON parsing
- Session aggregation uses Python stdlib

---

## Integration Approach (REVISED)

### Phase 1: Metrics Extraction
1. Create `docker/patches/cache_metrics.py` - CacheMetrics dataclass and extraction logic
2. Create `docker/patches/pricing_calculator.py` - cost calculation with OpenRouter pricing
3. Add response post-processing to extract cache metrics from OpenRouter responses

### Phase 2: Response Enhancement
1. Extend MCP response format to include `cache_metrics` field
2. Implement session-level metrics aggregation
3. Add cache statistics to health endpoint

### Phase 3: Monitoring
1. Add structured logging for cache hit/miss events
2. Expose session metrics via health endpoint
3. Document cache analytics available via OpenRouter dashboard

### Configuration Environment Variables

```bash
# Most caching is automatic - these are for tuning/disabling

# Enable/disable cache metrics reporting (default: true)
MADEINOZ_KNOWLEDGE_PROMPT_CACHE_METRICS_ENABLED=true

# Log cache metrics on each request (default: false)
MADEINOZ_KNOWLEDGE_PROMPT_CACHE_LOG_REQUESTS=false
```

---

## Risk Assessment (REVISED)

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| OpenRouter changes caching behavior | Low | Medium | Feature flag to disable; metrics will just show no cached_tokens |
| OpenRouter removes cache_discount field | Low | Low | Fall back to estimated discount |
| Metrics extraction fails on some responses | Low | Low | Graceful degradation - omit cache_metrics field |
| Memory usage from session metrics | Very Low | Low | Simple counters, not storing individual requests |

---

## Success Verification (REVISED)

After implementation, the following can be verified:

1. **Cache Metrics in Response**: `cache_metrics` field present in MCP responses for Gemini models
2. **Cache Hits**: `cached_tokens > 0` on repeated requests with same prompts
3. **Cost Savings Display**: `cost_saved > 0` when cache hits occur
4. **Health Endpoint**: `/health` returns session-level cache statistics
5. **OpenRouter Dashboard**: https://openrouter.ai/activity shows cache analytics

---

### 8. Metrics Framework Selection (Added 2026-01-27)

**Decision**: Use **OpenTelemetry SDK with Prometheus exporter** for cache metrics exposure.

**Rationale**:
- **Vendor-neutral**: OpenTelemetry is the industry standard, supported by CNCF
- **Future-proof**: Can export to multiple backends (Prometheus, Jaeger, OTLP)
- **Python SDK mature**: `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-prometheus` are stable
- **Minimal dependencies**: ~3-4 packages added
- **Standard scraping**: Prometheus format works with existing monitoring infrastructure
- **Grafana-ready**: Standard PromQL queries work out-of-box

**Alternatives Considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| Direct prometheus-client | Simpler but less flexible for future backends |
| Custom metrics endpoint | Reinventing wheel, non-standard format |
| Health endpoint extension | User explicitly rejected this approach |
| StatsD | Less common in Python ecosystem, requires separate daemon |
| Custom JSON metrics | Non-standard, no time-series support |

**Implementation Approach**:

```python
from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from prometheus_client import start_http_server

# Initialize provider with Prometheus exporter
reader = PrometheusMetricReader()
provider = MeterProvider(metric_readers=[reader])
metrics.set_meter_provider(provider)

# Create meter for cache metrics
meter = metrics.get_meter("graphiti.cache", version="1.0.0")

# Define counters and gauges
cache_hits = meter.create_counter("graphiti_cache_hits_total")
cache_misses = meter.create_counter("graphiti_cache_misses_total")
cache_tokens_saved = meter.create_counter("graphiti_cache_tokens_saved_total")
cache_cost_saved = meter.create_counter("graphiti_cache_cost_saved_total")
cache_hit_rate = meter.create_observable_gauge("graphiti_cache_hit_rate")
cache_size = meter.create_observable_gauge("graphiti_cache_size_bytes")
cache_entries = meter.create_observable_gauge("graphiti_cache_entries")

# Expose /metrics on port 9090
start_http_server(9090)
```

**Metric Naming Conventions** (Prometheus style):
- Counters end with `_total`: `graphiti_cache_hits_total`
- Gauges describe current state: `graphiti_cache_hit_rate`
- Prefix with namespace: `graphiti_`
- Use snake_case: `cache_tokens_saved`

**User Feedback Context**:
The user explicitly stated: "I don't want an API endpoint for cache stats, however OpenTelemetry or Prometheus metrics exposed would be better". This decision directly addresses that requirement.

**Dependencies Added**:
```
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-exporter-prometheus>=0.41b0
prometheus-client>=0.17.0
```

**Sources**:
- [OpenTelemetry Python SDK](https://opentelemetry.io/docs/languages/python/)
- [OpenTelemetry Prometheus Exporter](https://opentelemetry.io/docs/specs/otel/metrics/sdk_exporters/prometheus/)
- [Prometheus Metric Types](https://prometheus.io/docs/concepts/metric_types/)

---

## References

- [OpenRouter Prompt Caching Best Practices](https://openrouter.ai/docs/guides/best-practices/prompt-caching)
- [OpenRouter API Response Format](https://openrouter.ai/docs/responses)
- [OpenRouter Activity Dashboard](https://openrouter.ai/activity)
- [OpenRouter Pricing](https://openrouter.ai/models)
- [Gemini API Context Caching](https://ai.google.dev/gemini-api/docs/caching) (for reference only - not used)
- [OpenTelemetry Python SDK](https://opentelemetry.io/docs/languages/python/)
- [Prometheus Metric Types](https://prometheus.io/docs/concepts/metric_types/)

---

## Appendix: Original Direct Gemini SDK Approach (DEPRECATED)

The following was the original research for direct Gemini SDK integration. This approach is **NOT APPLICABLE** because we use OpenRouter as our LLM proxy.

<details>
<summary>Click to expand deprecated approach</summary>

### Original Decision (DEPRECATED)
Use Gemini's **Explicit Caching** via `google.genai.caches` module with `CachedContent.create()` for predictable cost savings.

### SDK Methods That Would Have Been Required
```python
# DEPRECATED - Not applicable with OpenRouter
cache = client.caches.create(model, config=types.CreateCachedContentConfig(
    contents=[...],
    display_name="graphiti-system-prompt",
    ttl="600s"
))

response = client.generate_content(
    model=model,
    contents=[user_message],
    config=types.GenerateContentConfig(cached_content=cache.name)
)
```

This approach was rejected because:
1. We use OpenRouter proxy, not direct Gemini API
2. OpenRouter provides automatic caching without SDK
3. No additional dependencies required with OpenRouter approach

</details>
