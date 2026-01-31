# Research: Prometheus Dashboard Fixes

**Feature**: 016-prometheus-dashboard-fixes
**Date**: 2026-01-31
**Phase**: 0 - Research & Analysis

## Overview

This document consolidates research findings for fixing Prometheus dashboard metric naming inconsistencies and adding time-over-time functions for service restart gap handling.

## Decision: Metric Name Correction Strategy

**Decision**: Update dashboard queries to match code-defined metric names. Do NOT modify metric names in Python code.

**Rationale**:
1. Metrics are already being emitted with correct names via OpenTelemetry in `docker/patches/metrics_exporter.py`
2. Changing metric names in code would be a breaking change for any external consumers
3. Dashboard queries are configuration files - easier to update than production code
4. The metric definitions follow OpenTelemetry naming conventions (unit as attribute, not name)

**Alternatives Considered**:
1. **Change metric names in code to match dashboards** - REJECTED because code follows correct OpenTelemetry conventions
2. **Add Prometheus metric relabeling** - REJECTED as unnecessary complexity; fixing source queries is cleaner
3. **Dashboard query aliases** - REJECTED; PromQL doesn't support aliasing in queries

## OpenTelemetry Naming Conventions

**Standard**: [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/general/naming/)

**Key Rules**:
1. Metric names MUST use lowercase letters, numbers, underscores, and dots (namespace separators only)
2. Metric names MUST start with a letter
3. **Units are specified via the `unit` parameter when creating instruments, NOT as part of the metric name**
4. The OpenTelemetry Prometheus Exporter preserves metric names as-is (no automatic unit suffixing)

**Our Implementation** (Correct):
```python
# From docker/patches/metrics_exporter.py
"api_cost_total": self._meter.create_counter(
    name="graphiti_api_cost_total",  # ✅ Unit NOT in name
    description="Total API cost in USD since server start (per model)",
    unit="USD"  # ✅ Unit as metadata attribute
)
```

**Dashboard Incorrect Usage**:
```promql
# ❌ WRONG - Unit in metric name
graphiti_api_cost_USD_total

# ✅ CORRECT - Matches code-defined name
graphiti_api_cost_total
```

**Why This Matters**:
- OpenTelemetry specifies units as metadata to enable automatic unit conversion in backends
- Hardcoding units in metric names creates brittleness (what if we switch currencies?)
- The Prometheus exposition format from OpenTelemetry exposes units via HELP text, not metric names

**Verification**:
From `docker/tests/integration/test_metrics_endpoint.py`:
```python
# Test confirms actual exposed metric name has no unit suffix
assert "graphiti_cache_hits_total" in text, \
    "graphiti_cache_hits_total counter should be present"
```

## Decision: Time-Over-Time Window Size

**Decision**: Use 1-hour (`[1h]`) window for `max_over_time()` wrappers.

**Rationale**:
1. Service restarts typically take seconds to minutes
2. 1-hour window provides sufficient buffer for restart scenarios
3. Longer windows (>24h) would hide legitimate data changes
4. Shorter windows (<5m) wouldn't bridge typical restart gaps
5. Industry standard for "service restart" gap handling is 1-4 hours

**Alternatives Considered**:
1. **5-minute window** - REJECTED; may not bridge longer restarts
2. **24-hour window** - REJECTED; would hide day-to-day variations
3. **Dynamic window based on scrape interval** - REJECTED; unnecessary complexity

## Decision: max_over_time vs avg_over_time vs min_over_time

**Decision**: Use `max_over_time()` for counter metrics and `rate()` expressions.

**Rationale**:
1. For counters that reset to zero on restart, `max_over_time()` preserves the last known value
2. `avg_over_time()` would produce incorrect values (averaging zero with non-zero creates dip)
3. `min_over_time()` would return zero (the reset value), which is not useful
4. For gauges that might legitimately drop to zero, `min_over_time()` could be appropriate but isn't needed for current metrics

**Alternatives Considered**:
1. **avg_over_time()** - REJECTED; creates artificial dips during restart gaps
2. **min_over_time()** - REJECTED; returns zero (the reset value)
3. **or operator with defaults** - REJECTED; PromQL doesn't support conditional logic

## Metric Name Reference

### Code-Defined Metric Names (from `docker/patches/metrics_exporter.py`)

| Metric Name | Type | Unit | Description |
|-------------|------|------|-------------|
| `graphiti_cache_hits_total` | Counter | - | Total cache hits |
| `graphiti_cache_misses_total` | Counter | - | Total cache misses |
| `graphiti_cache_hit_rate` | Gauge | % | Cache hit rate percentage |
| `graphiti_api_cost_total` | Counter | USD | Total API cost |
| `graphiti_api_cost_per_request` | Histogram | USD | API cost per request |
| `graphiti_cache_cost_saved_total` | Counter | USD | Cost saved via caching |
| `graphiti_prompt_tokens_total` | Counter | - | Prompt tokens used |
| `graphiti_completion_tokens_total` | Counter | - | Completion tokens used |
| `graphiti_total_tokens_total` | Counter | - | Total tokens used |
| `graphiti_llm_request_duration_seconds` | Histogram | s | LLM request duration |
| `graphiti_cache_hits_all_models_total` | Counter | - | Total hits (all models) |
| `graphiti_cache_misses_all_models_total` | Counter | - | Total misses (all models) |
| `graphiti_cache_tokens_saved_total` | Counter | - | Tokens saved (all models) |
| `graphiti_cache_cost_saved_all_models_total` | Counter | USD | Cost saved (all models) |

### Dashboard Metric Name Corrections

| Incorrect Name | Correct Name | Files Using |
|----------------|--------------|-------------|
| `graphiti_cache_hit_rate_percent` | `graphiti_cache_hit_rate` | madeinoz-knowledge.json, prompt-cache-effectiveness.json |
| `graphiti_api_cost_USD_total` | `graphiti_api_cost_total` | madeinoz-knowledge.json |
| `graphiti_api_cost_all_models_USD_total` | `graphiti_api_cost_all_models_total` | madeinoz-knowledge.json |
| `graphiti_cache_cost_saved_USD_total` | `graphiti_cache_cost_saved_total` | madeinoz-knowledge.json |
| `graphiti_cache_cost_saved_all_models_USD_total` | `graphiti_cache_cost_saved_all_models_total` | madeinoz-knowledge.json |
| `graphiti_api_cost_per_request_USD_bucket` | `graphiti_api_cost_per_request` | madeinoz-knowledge.json |

## Dashboard File Inventory

| File | Location | Panel Count | Changes Needed |
|------|----------|-------------|----------------|
| madeinoz-knowledge.json | dashboards/ | 32 | 9 name fixes + ~15 wrappers |
| graph-health-dashboard.json | dashboards/ | 11 | ~8 wrappers |
| memory-decay-dashboard.json | dashboards/ | 19 | ~5 wrappers |
| memory-access-dashboard.json | dashboards/ | 18 | ~2 wrappers |
| prompt-cache-effectiveness.json | dashboards/ | 8 | 6 name fixes + ~2 wrappers |
| madeinoz-knowledge.json | provisioning/dashboards/ | 32 | 9 name fixes + ~15 wrappers (copy of above) |

## Query Pattern Catalog

### Counter Rate Queries

**Pattern**: `rate(counter[5m])` → `max_over_time(rate(counter[5m]))[1h]`

**Examples**:
```promql
# Token throughput
rate(graphiti_total_tokens_all_models_total[5m])
→ max_over_time(rate(graphiti_total_tokens_all_models_total[5m]))[1h]

# Cache hit/miss rates
rate(graphiti_cache_hits_all_models_total[5m])
→ max_over_time(rate(graphiti_cache_hits_all_models_total[5m]))[1h]

# Error rates
rate(graphiti_llm_errors_all_models_total[5m])
→ max_over_time(rate(graphiti_llm_errors_all_models_total[5m]))[1h]
```

### Counter Increase Queries

**Pattern**: `increase(counter[5m])` → `max_over_time(increase(counter[5m]))[1h]`

**Examples**:
```promql
# State transitions over time range
increase(knowledge_lifecycle_transitions_total{from_state="ACTIVE",to_state="DORMANT"}[1h])
→ max_over_time(increase(knowledge_lifecycle_transitions_total{from_state="ACTIVE",to_state="DORMANT"}[1h]))[1h]
```

### Counter Total Queries

**Pattern**: `counter_total` → `max_over_time(counter_total[1h])`

**Examples**:
```promql
# Total cache hits
graphiti_cache_hits_all_models_total
→ max_over_time(graphiti_cache_hits_all_models_total[1h])

# Total errors
sum(graphiti_llm_errors_all_models_total)
→ sum(max_over_time(graphiti_llm_errors_all_models_total[1h]))
```

### Histogram Quantile Queries

**Pattern**: `histogram_quantile(N, rate(bucket[5m]))` → `histogram_quantile(N, max_over_time(rate(bucket[5m]))[1h])`

**Examples**:
```promql
# Request duration percentiles
histogram_quantile(0.95, rate(graphiti_llm_request_duration_seconds_bucket[5m]))
→ histogram_quantile(0.95, max_over_time(rate(graphiti_llm_request_duration_seconds_bucket[5m]))[1h])

# Maintenance duration
histogram_quantile(0.95, sum(rate(knowledge_maintenance_duration_seconds_bucket[5m])) by (le))
→ histogram_quantile(0.95, sum(max_over_time(rate(knowledge_maintenance_duration_seconds_bucket[5m]))[1h]) by (le))
```

### Gauge Queries (No Time-Over-Time Needed)

Gauges represent current values and don't reset on restart in the same way counters do.

```promql
# Cache hit rate (gauge) - no wrapper needed
graphiti_cache_hit_rate

# Entity counts - no wrapper needed
sum(knowledge_memories_by_state{state="ACTIVE"})
```

## References

- [OpenTelemetry Naming Specification](https://opentelemetry.io/docs/specs/semconv/general/naming/) - Metric naming conventions
- [OpenTelemetry Metrics Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/general/metrics/) - Units and instrumentation guidelines
- [Prometheus Query Functions](https://prometheus.io/docs/prometheus/latest/querying/functions/) - Time-over-time functions
- [Grafana Dashboard JSON Reference](https://grafana.com/docs/grafana/latest/dashboards/share-dashboard/) - Dashboard configuration format
