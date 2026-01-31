# Data Model: Prompt Cache Effectiveness Dashboard

## Overview

This feature does not introduce new data entities. It creates a Grafana dashboard JSON file that queries existing Prometheus metrics. The "data model" here represents the Prometheus metric schema and Grafana dashboard structure.

## Prometheus Metrics Schema

### Counters (Cumulative, Reset on Restart)

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `graphiti_cache_tokens_saved_all_models_total` | Counter | - | Total tokens saved from prompt caching |
| `graphiti_cache_cost_saved_all_models_total` | Counter | - | Total USD saved from caching |
| `graphiti_cache_hits_all_models_total` | Counter | - | Total cache hits |
| `graphiti_cache_misses_all_models_total` | Counter | - | Total cache misses |
| `graphiti_cache_write_tokens_all_models_total` | Counter | - | Total tokens written to cache |
| `graphiti_cache_hits_total` | Counter | `model` | Cache hits per LLM model |
| `graphiti_cache_misses_total` | Counter | `model` | Cache misses per LLM model |
| `graphiti_cache_cost_saved_total` | Counter | `model` | Cost savings per LLM model |

### Histograms

| Metric Name | Type | Labels | Buckets |
|-------------|------|--------|--------|
| `graphiti_cache_tokens_saved_per_request_bucket` | Histogram | `model` | Prometheus default (exponential) |
| `graphiti_cache_cost_saved_per_request_bucket` | Histogram | `model` | Prometheus default (exponential) |

### Gauges

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `graphiti_cache_hit_rate` | Gauge | - | Current cache hit rate as percentage (0-100) |

## Grafana Dashboard Structure

### Dashboard JSON Schema

```json
{
  "dashboard": {
    "title": "Prompt Cache Effectiveness",
    "tags": ["cache", "monitoring", "cost", "gemini"],
    "timezone": "",
    "schemaVersion": 16,
    "version": 0,
    "refresh": "30s",
    "panels": [
      {
        "type": "stat",
        "title": "Total Cost Savings",
        "targets": [
          {
            "expr": "max_over_time(graphiti_cache_cost_saved_all_models_total[1h])"
          }
        ]
      },
      // ... 9 more panels
    ]
  }
}
```

### Panel Types and Queries

#### Row 1: Overview (Stat Panels)

| Panel | Metric | Query | Color Thresholds |
|-------|--------|-------|----------------|
| Cost Savings | `graphiti_cache_cost_saved_all_models_total` | `max_over_time(...[1h])` | Green (good), Yellow (low) |
| Hit Rate | `graphiti_cache_hit_rate` | Direct | Green (>50%), Yellow (20-50%), Red (<20%) |
| Tokens Saved | `graphiti_cache_tokens_saved_all_models_total` | `max_over_time(...[1h])` | Blue |
| Tokens Written | `graphiti_cache_write_tokens_all_models_total` | `max_over_time(...[1h])` | Orange |

#### Row 2: Trends (Time Series)

| Panel | Metric | Query |
|-------|--------|-------|
| Savings Rate | `graphiti_cache_cost_saved_all_models_total` | `rate(max_over_time(...[1h])[5m])` |
| Hit Rate Trend | `graphiti_cache_hit_rate` | Direct |
| Hits vs Misses | Combined | `rate(max_over_time(hits[1h])[5m])` vs `rate(max_over_time(misses[1h])[5m])` |

#### Row 3: Distribution & Comparison

| Panel | Type | Metric | Query |
|-------|------|--------|-------|
| Tokens Saved Distribution | Heatmap | `graphiti_cache_tokens_saved_per_request_bucket` | `sum(increase(...[$__rate_interval])) by (le)` |
| Per-Model Comparison | Table | Multiple | `rate(max_over_time(...[1h])[5m])` by (model) |

## Relationships

```
graphiti_cache_tokens_saved_total
        │
        ├── (aggregates to dashboard)
        └── (used for cost savings calculation)

graphiti_cache_cost_saved_total
        │
        └── (compared with API costs for ROI)

graphiti_cache_hit_rate
        │
        ├── (monitors cache health)
        └── (triggers alerts when low)
```

## Validation Rules

### Metric Availability

- [ ] All PR #34 metrics are being emitted by the metrics exporter
- [ ] Prometheus data source is configured in Grafana
- [ ] Metrics are accessible via `/metrics` endpoint on port 9090 (production) or 9091 (development)

### Dashboard Constraints

- [ ] Dashboard JSON is valid Grafana schema version 16
- [ ] All queries use time-over-time functions for cumulative metrics
- [ ] Zero-value scenarios handled with "No data" or "0"
- [ ] Dashboard fits on 1080p display without scrolling
- [ ] Refresh interval is 30 seconds (user-configurable)
