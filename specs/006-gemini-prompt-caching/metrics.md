# Feature 006: Prometheus Metrics Reference

**Feature**: 006-gemini-prompt-caching
**Status**: Metrics Active (Caching Blocked)
**Endpoint**: `http://localhost:9091/metrics` (dev) / `http://localhost:9090/metrics` (prod)

## Overview

The metrics system provides comprehensive observability for LLM API usage, including token consumption, costs, and cache statistics. Metrics are exported in Prometheus format via OpenTelemetry.

## Metrics Summary

| Type | Count | Purpose |
|------|-------|---------|
| Counters | 12 | Cumulative totals (tokens, costs) |
| Histograms | 6 | Per-request distributions |
| Gauges | 2 | Current state (cache enabled, hit rate) |

---

## Counter Metrics

### Token Usage (Per-Model)

| Metric | Description |
|--------|-------------|
| `graphiti_prompt_tokens_total{model="..."}` | Total input/prompt tokens |
| `graphiti_completion_tokens_total{model="..."}` | Total output/completion tokens |
| `graphiti_total_tokens_total{model="..."}` | Total tokens (prompt + completion) |

### Token Usage (Aggregate)

| Metric | Description |
|--------|-------------|
| `graphiti_prompt_tokens_all_models_total` | Input tokens across all models |
| `graphiti_completion_tokens_all_models_total` | Output tokens across all models |
| `graphiti_total_tokens_all_models_total` | Total tokens across all models |

### API Costs (Per-Model)

| Metric | Unit | Description |
|--------|------|-------------|
| `graphiti_api_cost_total{model="..."}` | USD | Total API cost |
| `graphiti_api_input_cost_total{model="..."}` | USD | Input/prompt cost |
| `graphiti_api_output_cost_total{model="..."}` | USD | Output/completion cost |

### API Costs (Aggregate)

| Metric | Unit | Description |
|--------|------|-------------|
| `graphiti_api_cost_all_models_total` | USD | Total cost across all models |
| `graphiti_api_input_cost_all_models_total` | USD | Input cost across all models |
| `graphiti_api_output_cost_all_models_total` | USD | Output cost across all models |

### Cache Statistics

| Metric | Description |
|--------|-------------|
| `graphiti_cache_hits_total{model="..."}` | Cache hits (per model) |
| `graphiti_cache_misses_total{model="..."}` | Cache misses (per model) |
| `graphiti_cache_tokens_saved_total{model="..."}` | Tokens saved via caching |
| `graphiti_cache_cost_saved_total{model="..."}` | Cost savings from caching (USD) |
| `graphiti_cache_requests_total{model="..."}` | Total requests with cache metrics |

---

## Histogram Metrics

Histograms track per-request distributions, enabling percentile calculations (p50, p95, p99).

### Token Histograms

| Metric | Bucket Range | Description |
|--------|--------------|-------------|
| `graphiti_prompt_tokens_per_request` | 10 - 200,000 | Input tokens per request |
| `graphiti_completion_tokens_per_request` | 10 - 200,000 | Output tokens per request |
| `graphiti_total_tokens_per_request` | 10 - 200,000 | Total tokens per request |

**Token Bucket Boundaries:**
```
10, 25, 50, 100, 250, 500, 1000, 2000, 3000, 5000, 10000, 25000, 50000, 100000, 200000
```

### Cost Histograms

| Metric | Bucket Range | Description |
|--------|--------------|-------------|
| `graphiti_api_cost_per_request` | $0.000005 - $5.00 | Total cost per request |
| `graphiti_api_input_cost_per_request` | $0.000005 - $5.00 | Input cost per request |
| `graphiti_api_output_cost_per_request` | $0.000005 - $5.00 | Output cost per request |

**Cost Bucket Boundaries:**
```
$0.000005, $0.00001, $0.000025, $0.00005, $0.0001, $0.00025, $0.0005, $0.001,
$0.0025, $0.005, $0.01, $0.025, $0.05, $0.1, $0.25, $0.5, $1.0, $2.5, $5.0
```

**Cost Bucket Coverage:**

| Range | Models |
|-------|--------|
| $0.000005 - $0.01 | Cheap: Gemini Flash, GPT-4o-mini |
| $0.01 - $0.10 | Mid-range: GPT-4o, Claude Sonnet |
| $0.10 - $1.00 | Expensive: GPT-4, Claude Opus |
| $1.00 - $5.00 | Large context on expensive models |

---

## Gauge Metrics

| Metric | Values | Description |
|--------|--------|-------------|
| `graphiti_cache_enabled` | 0 or 1 | Whether prompt caching is enabled |
| `graphiti_cache_hit_rate` | 0-100 | Current session cache hit rate (%) |

---

## Example PromQL Queries

### Token Usage

```promql
# Total tokens in last hour
increase(graphiti_total_tokens_all_models_total[1h])

# Tokens per model
sum by (model) (increase(graphiti_total_tokens_total[1h]))
```

### Cost Tracking

```promql
# Total cost in last 24h
increase(graphiti_api_cost_all_models_total[24h])

# Cost per model
sum by (model) (increase(graphiti_api_cost_total[24h]))
```

### Percentiles

```promql
# p95 cost per request
histogram_quantile(0.95, rate(graphiti_api_cost_per_request_bucket[5m]))

# p99 tokens per request
histogram_quantile(0.99, rate(graphiti_total_tokens_per_request_bucket[5m]))

# Median (p50) cost per request
histogram_quantile(0.50, rate(graphiti_api_cost_per_request_bucket[5m]))
```

### Cache Effectiveness

```promql
# Cache hit rate
graphiti_cache_hit_rate

# Cache enabled status
graphiti_cache_enabled
```

---

## Understanding Histogram Buckets

Prometheus histograms are **cumulative**. Each bucket shows the count of observations **less than or equal to** that boundary.

Example output:
```
graphiti_api_cost_per_request_USD_bucket{le="0.0001"} 2.0
graphiti_api_cost_per_request_USD_bucket{le="0.00025"} 5.0
graphiti_api_cost_per_request_USD_bucket{le="0.0005"} 5.0
```

Interpretation:
- 2 requests cost ≤ $0.0001
- 3 more requests cost between $0.0001 and $0.00025
- 0 requests cost more than $0.00025 (count stays at 5)

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MADEINOZ_KNOWLEDGE_PROMPT_CACHE_ENABLED` | `false` | Enable/disable caching |
| `MADEINOZ_KNOWLEDGE_PROMPT_CACHE_METRICS_ENABLED` | `true` | Enable/disable metrics collection |
| `MADEINOZ_KNOWLEDGE_PROMPT_CACHE_LOG_REQUESTS` | `false` | Enable verbose request logging |

### Enabling Debug Logging

Set log level to DEBUG to see per-request metrics in logs:
```
LOG_LEVEL=DEBUG
```

This enables the `📊 Metrics: prompt=X, completion=Y, cost=$Z` log lines.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     OpenRouter API                               │
│  (returns: usage, cost, cost_details, prompt_tokens_details)    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   caching_wrapper.py                             │
│  - Wraps responses.parse() and chat.completions.create()        │
│  - Extracts metrics from response                                │
│  - Calls metrics_exporter.record_request_metrics()              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   metrics_exporter.py                            │
│  - OpenTelemetry MeterProvider with custom Views                │
│  - Prometheus exporter on port 9090/9091                        │
│  - Counters, Histograms, Gauges                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Prometheus / Grafana                                │
│  - Scrape /metrics endpoint                                      │
│  - Visualize with dashboards                                     │
│  - Alert on thresholds                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Known Limitations

1. **Caching Disabled**: Prompt caching is blocked due to OpenRouter `/responses` endpoint not supporting multipart format required for `cache_control` markers. See `resolution-research.md`.

2. **Cache metrics always show miss**: Until caching is enabled, `graphiti_cache_hits_total` will remain 0.

3. **OpenRouter field names**: The actual API response uses `upstream_inference_input_cost` / `upstream_inference_output_cost`, not the documented `upstream_inference_prompt_cost` / `upstream_inference_completions_cost`.

---

## Files

| File | Purpose |
|------|---------|
| `docker/patches/metrics_exporter.py` | OpenTelemetry/Prometheus metrics exporter |
| `docker/patches/caching_wrapper.py` | Response wrapper that extracts metrics |
| `docker/patches/cache_metrics.py` | Cache metrics data structures |
| `docker/patches/message_formatter.py` | Message formatting for cache markers |
