# API Contract: Prometheus Metrics for Cache Statistics

**Feature**: 006-gemini-prompt-caching
**Date**: 2026-01-27
**Status**: Phase 1 Complete
**Contract Type**: Metrics Endpoint

---

## Overview

This contract defines the Prometheus metrics endpoint that exposes prompt cache statistics. The metrics endpoint provides operational visibility into cache effectiveness, token savings, and cost reductions using standard observability tooling.

**Design Decision**: OpenTelemetry SDK with Prometheus exporter was chosen for vendor-neutral, future-proof instrumentation that integrates with existing monitoring infrastructure.

---

## Endpoint Specification

### Request

```
GET /metrics
```

No request body. No authentication required (metrics endpoints should be accessible for scraping).

### Response Headers

```
Content-Type: text/plain; version=0.0.4; charset=utf-8
```

---

## Metric Definitions

### Counter Metrics

Counters only ever increase and are suitable for tracking cumulative totals.

#### graphiti_cache_hits_total

```prometheus
# HELP graphiti_cache_hits_total Total number of cache hits since server start
# TYPE graphiti_cache_hits_total counter
graphiti_cache_hits_total{model="google/gemini-2.0-flash-001"} 1523
```

**Labels**:
- `model`: The Gemini model identifier (e.g., "google/gemini-2.0-flash-001")

---

#### graphiti_cache_misses_total

```prometheus
# HELP graphiti_cache_misses_total Total number of cache misses since server start
# TYPE graphiti_cache_misses_total counter
graphiti_cache_misses_total{model="google/gemini-2.0-flash-001"} 487
```

**Labels**:
- `model`: The Gemini model identifier

---

#### graphiti_cache_tokens_saved_total

```prometheus
# HELP graphiti_cache_tokens_saved_total Total tokens saved via caching since server start
# TYPE graphiti_cache_tokens_saved_total counter
graphiti_cache_tokens_saved_total{model="google/gemini-2.0-flash-001"} 2847350
```

**Labels**:
- `model`: The Gemini model identifier

---

#### graphiti_cache_cost_saved_total

```prometheus
# HELP graphiti_cache_cost_saved_total Total cost savings in USD from caching since server start
# TYPE graphiti_cache_cost_saved_total counter
graphiti_cache_cost_saved_total{model="google/gemini-2.0-flash-001"} 0.7584
```

**Labels**:
- `model`: The Gemini model identifier

---

#### graphiti_cache_requests_total

```prometheus
# HELP graphiti_cache_requests_total Total API requests with cache metrics since server start
# TYPE graphiti_cache_requests_total counter
graphiti_cache_requests_total{model="google/gemini-2.0-flash-001"} 2010
```

**Labels**:
- `model`: The Gemini model identifier

---

### Gauge Metrics

Gauges represent a value that can go up or down over time.

#### graphiti_cache_hit_rate

```prometheus
# HELP graphiti_cache_hit_rate Current cache hit rate as a percentage (0-100)
# TYPE graphiti_cache_hit_rate gauge
graphiti_cache_hit_rate{model="google/gemini-2.0-flash-001"} 75.77
```

**Labels**:
- `model`: The Gemini model identifier

---

#### graphiti_cache_size_bytes

```prometheus
# HELP graphiti_cache_size_bytes Current estimated cache memory usage in bytes
# TYPE graphiti_cache_size_bytes gauge
graphiti_cache_size_bytes 8808652
```

**Note**: This metric may not have labels as it represents total cache size across all models.

---

#### graphiti_cache_entries

```prometheus
# HELP graphiti_cache_entries Current number of entries in the cache
# TYPE graphiti_cache_entries gauge
graphiti_cache_entries 23
```

---

#### graphiti_cache_enabled

```prometheus
# HELP graphiti_cache_enabled Whether caching is currently enabled (1=enabled, 0=disabled)
# TYPE graphiti_cache_enabled gauge
graphiti_cache_enabled 1
```

---

## Full Example Output

```prometheus
# HELP graphiti_cache_enabled Whether caching is currently enabled (1=enabled, 0=disabled)
# TYPE graphiti_cache_enabled gauge
graphiti_cache_enabled 1

# HELP graphiti_cache_entries Current number of entries in the cache
# TYPE graphiti_cache_entries gauge
graphiti_cache_entries 23

# HELP graphiti_cache_size_bytes Current estimated cache memory usage in bytes
# TYPE graphiti_cache_size_bytes gauge
graphiti_cache_size_bytes 8808652

# HELP graphiti_cache_hits_total Total number of cache hits since server start
# TYPE graphiti_cache_hits_total counter
graphiti_cache_hits_total{model="google/gemini-2.0-flash-001"} 1523
graphiti_cache_hits_total{model="google/gemini-2.5-pro"} 89

# HELP graphiti_cache_misses_total Total number of cache misses since server start
# TYPE graphiti_cache_misses_total counter
graphiti_cache_misses_total{model="google/gemini-2.0-flash-001"} 487
graphiti_cache_misses_total{model="google/gemini-2.5-pro"} 34

# HELP graphiti_cache_requests_total Total API requests with cache metrics since server start
# TYPE graphiti_cache_requests_total counter
graphiti_cache_requests_total{model="google/gemini-2.0-flash-001"} 2010
graphiti_cache_requests_total{model="google/gemini-2.5-pro"} 123

# HELP graphiti_cache_hit_rate Current cache hit rate as a percentage (0-100)
# TYPE graphiti_cache_hit_rate gauge
graphiti_cache_hit_rate{model="google/gemini-2.0-flash-001"} 75.77
graphiti_cache_hit_rate{model="google/gemini-2.5-pro"} 72.36

# HELP graphiti_cache_tokens_saved_total Total tokens saved via caching since server start
# TYPE graphiti_cache_tokens_saved_total counter
graphiti_cache_tokens_saved_total{model="google/gemini-2.0-flash-001"} 2847350
graphiti_cache_tokens_saved_total{model="google/gemini-2.5-pro"} 156230

# HELP graphiti_cache_cost_saved_total Total cost savings in USD from caching since server start
# TYPE graphiti_cache_cost_saved_total counter
graphiti_cache_cost_saved_total{model="google/gemini-2.0-flash-001"} 0.7584
graphiti_cache_cost_saved_total{model="google/gemini-2.5-pro"} 0.3912
```

---

## OpenTelemetry Integration

### SDK Configuration

```python
from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from prometheus_client import start_http_server

# Initialize Prometheus exporter
reader = PrometheusMetricReader()
provider = MeterProvider(metric_readers=[reader])
metrics.set_meter_provider(provider)

# Get meter for cache metrics
meter = metrics.get_meter("graphiti.cache", version="1.0.0")

# Define metrics
cache_hits = meter.create_counter(
    name="graphiti_cache_hits",
    description="Total number of cache hits",
    unit="1"
)

cache_misses = meter.create_counter(
    name="graphiti_cache_misses",
    description="Total number of cache misses",
    unit="1"
)

cache_tokens_saved = meter.create_counter(
    name="graphiti_cache_tokens_saved",
    description="Total tokens saved via caching",
    unit="1"
)

cache_cost_saved = meter.create_counter(
    name="graphiti_cache_cost_saved",
    description="Total cost savings from caching",
    unit="USD"
)

cache_hit_rate = meter.create_observable_gauge(
    name="graphiti_cache_hit_rate",
    description="Current cache hit rate percentage",
    unit="%",
    callbacks=[lambda options: [hit_rate_callback()]]
)

# Start metrics HTTP server on port 9090
start_http_server(9090)
```

### Recording Metrics

```python
# On cache hit
cache_hits.add(1, {"model": model_name})
cache_tokens_saved.add(cached_tokens, {"model": model_name})
cache_cost_saved.add(cost_saved, {"model": model_name})

# On cache miss
cache_misses.add(1, {"model": model_name})
```

---

## Label Conventions

Following Prometheus naming conventions:

| Label | Description | Example Values |
|-------|-------------|----------------|
| `model` | Gemini model identifier | `google/gemini-2.0-flash-001`, `google/gemini-2.5-pro` |

---

## Prometheus Scrape Configuration

Example `prometheus.yml` configuration:

```yaml
scrape_configs:
  - job_name: 'graphiti-mcp'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:9090']
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        replacement: 'graphiti-mcp'
```

---

## Alerting Rules

Recommended alerting thresholds:

```yaml
groups:
  - name: graphiti-cache
    rules:
      - alert: LowCacheHitRate
        expr: graphiti_cache_hit_rate < 50
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Cache hit rate is below 50%"
          description: "Cache hit rate is {{ $value }}% for model {{ $labels.model }}"

      - alert: HighCacheMemory
        expr: graphiti_cache_size_bytes > 100000000
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Cache memory usage exceeds 100MB"
          description: "Cache is using {{ $value | humanize }} of memory"
```

---

## Grafana Dashboard Queries

Useful PromQL queries for dashboards:

```promql
# Cache hit rate over time
graphiti_cache_hit_rate{model="google/gemini-2.0-flash-001"}

# Cache hits per minute
rate(graphiti_cache_hits_total[1m])

# Cost savings per hour
increase(graphiti_cache_cost_saved_total[1h])

# Token savings per minute
rate(graphiti_cache_tokens_saved_total[1m])

# Overall hit rate across all models
sum(graphiti_cache_hits_total) / sum(graphiti_cache_requests_total) * 100
```

---

## Dependencies

```
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-exporter-prometheus>=0.41b0
prometheus-client>=0.17.0
```

---

## Environment Variables

```bash
# Port for Prometheus metrics endpoint (default: 9090)
MADEINOZ_KNOWLEDGE_METRICS_PORT=9090

# Enable/disable metrics endpoint (default: true)
MADEINOZ_KNOWLEDGE_METRICS_ENABLED=true
```

---

## Backward Compatibility

- **Existing clients**: Metrics endpoint is a new addition, no breaking changes
- **Health endpoint**: Remains unchanged for basic health checks (if present)
- **Monitoring systems**: Standard Prometheus format ensures compatibility

---

## Comparison: Health Endpoint vs Prometheus Metrics

| Aspect | Health Endpoint (OLD) | Prometheus Metrics (NEW) |
|--------|----------------------|--------------------------|
| Format | JSON | Prometheus text format |
| Scraping | Manual/custom | Standard Prometheus scraping |
| Time-series | Snapshot only | Full time-series history |
| Alerting | Custom implementation | Native Prometheus alerts |
| Dashboards | Custom implementation | Grafana out-of-box |
| Aggregation | Client-side | PromQL queries |
| Labels | Nested JSON | Flat labels |
| Industry standard | No | Yes |
