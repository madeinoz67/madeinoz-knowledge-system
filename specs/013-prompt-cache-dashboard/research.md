# Research: Prompt Cache Effectiveness Dashboard

## Overview

This feature creates a Grafana dashboard to visualize prompt caching metrics. The metrics already exist (emitted by PR #34), so research focuses on Grafana dashboard patterns and time-over-time query functions for restart gap handling.

## Research Tasks

### Task 1: Identify Existing Metrics

**Question**: Which metrics from PR #34 need dashboard panels?

**Research Source**: `docker/patches/metrics_exporter.py`

**Findings**:

| Metric | Type | Labels | Dashboard Purpose |
|--------|------|--------|-------------------|
| `graphiti_cache_tokens_saved_all_models_total` | Counter | - | Total tokens saved from caching |
| `graphiti_cache_cost_saved_all_models_total` | Counter | - | USD savings from caching |
| `graphiti_cache_hits_all_models_total` | Counter | - | Total cache hits |
| `graphiti_cache_misses_all_models_total` | Counter | - | Total cache misses |
| `graphiti_cache_hit_rate` | Gauge | - | Current hit rate percentage |
| `graphiti_cache_write_tokens_all_models_total` | Counter | - | Tokens written to create cache |
| `graphiti_cache_tokens_saved_per_request_bucket` | Histogram | model | Distribution of tokens saved per hit |
| `graphiti_cache_cost_saved_per_request_bucket` | Histogram | model | Distribution of cost saved per hit |
| `graphiti_cache_hits_total` | Counter | model | Per-model hits |
| `graphiti_cache_misses_total` | Counter | model | Per-model misses |
| `graphiti_cache_cost_saved_total` | Counter | model | Per-model savings |

**Decision**: All 10 metrics will have dashboard panels. Per-model metrics will use variable substitution for model labels.

---

### Task 2: Grafana Dashboard Patterns

**Question**: What Grafana panel types and query patterns should be used?

**Research Source**: Existing dashboards in `config/monitoring/grafana/dashboards/`

**Findings**:

| Panel Type | Use Case | PromQL Pattern |
|-----------|----------|---------------|
| **Stat** | Single value display | `metric` or `max_over_time(metric[1h])` |
| **Time Series** | Trend over time | `rate(metric[5m])` or `max_over_time(metric[1h])` |
| **Heatmap** | Histogram distribution | `sum(increase(metric_bucket[$__rate_interval])) by (le)` |
| **Gauge** | Percentage display | Direct gauge metric |
| **Table** | Per-model comparison | `metric{model="*"}` |

**Decision**: Use Stat for cumulative values, Time Series for trends, Heatmap for distributions, Table for per-model comparison.

---

### Task 3: Time-Over-Time Functions for Restart Gaps

**Question**: How to handle service restart gaps in cumulative metrics?

**Research Source**: Issue #39, PromQL documentation, Grafana community best practices

**Findings**:

| Metric Type | Problem | Solution |
|-------------|----------|----------|
| Counter (cumulative) | Resets to 0 on restart | `max_over_time(metric[1h])` preserves last value |
| Rate calculation | `rate()` produces gaps during restart | `max_over_time(rate(metric[5m])[1h])` |
| Gauge | May have gaps during restart | `min_over_time(metric[5m-15m])` shows minimum |

**Decision**: Wrap all cumulative counter queries with `max_over_time()[1h]` to maintain continuity during restarts. Use 1-hour window as default (balances responsiveness and gap coverage).

---

### Task 4: Dashboard Layout for 1080p Single Screen

**Question**: How many panels fit on a single screen?

**Research Source**: Grafana dashboard layout best practices

**Findings**:

- Standard 1080p screen: ~1920x1080 pixels
- Grafana headers/footers consume ~100px vertical
- Usable height: ~900-950px
- Recommended panel height: 6-8 rows (Row panel in Grafana)
- Panels per row: 1-3 depending on width

**Decision**: 3 rows, 3-4 panels per row = 10 panels total:
- Row 1: Stat panels (Cost savings, Hit rate, Tokens saved, Tokens written)
- Row 2: Time series (Savings rate, Hit rate trend, Hits vs Misses)
- Row 3: Heatmap (Tokens saved distribution) + Table (Per-model comparison)

---

## Decisions Summary

| Decision | Rationale |
|----------|-----------|
| Use existing PR #34 metrics | Metrics already deployed and documented |
| `max_over_time()[1h]` for cumulative metrics | Handles restart gaps per Principle IX |
| 3-row layout × 3-4 panels | Fits 1080p screen without scrolling |
| Heatmap for histogram buckets | Standard Grafana pattern for distributions |
| Variable substitution for per-model panels | Single panel serves all models |
