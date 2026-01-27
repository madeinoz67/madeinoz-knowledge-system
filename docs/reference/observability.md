---
title: "Observability & Metrics"
description: "Prometheus metrics, monitoring, and observability for the Madeinoz Knowledge System"
---

# Observability & Metrics

The Madeinoz Knowledge System exports Prometheus metrics for monitoring LLM API usage, token consumption, and costs. This enables integration with existing observability infrastructure.

## Overview

Metrics are exported via OpenTelemetry with a Prometheus exporter. The system tracks:

- **Token usage** - Input, output, and total tokens per model
- **API costs** - Real-time cost tracking in USD
- **Cache statistics** - Hit rates, tokens saved, cost savings (when caching is enabled)

## Quick Start

### Accessing Metrics

The metrics endpoint is exposed at:

| Environment | Endpoint |
|-------------|----------|
| Development | `http://localhost:9091/metrics` |
| Production | `http://localhost:9090/metrics` |

### Basic Query

```bash
# Fetch all metrics
curl http://localhost:9091/metrics

# Filter to graphiti metrics only
curl -s http://localhost:9091/metrics | grep "^graphiti_"
```

## Configuration

### Environment Variables

Add these to your `~/.claude/.env` file:

```bash
# Enable/disable metrics collection (default: true)
MADEINOZ_KNOWLEDGE_PROMPT_CACHE_METRICS_ENABLED=true

# Enable detailed per-request logging (default: false)
# Set LOG_LEVEL=DEBUG to see metrics in logs
MADEINOZ_KNOWLEDGE_PROMPT_CACHE_LOG_REQUESTS=false

# Enable/disable prompt caching (default: false)
# Note: Currently blocked due to OpenRouter API limitation
MADEINOZ_KNOWLEDGE_PROMPT_CACHE_ENABLED=false
```

### Restart After Configuration

```bash
bun run server-cli stop
bun run server-cli start
```

## Available Metrics

### Token Counters

Track cumulative token usage across all requests.

| Metric | Labels | Description |
|--------|--------|-------------|
| `graphiti_prompt_tokens_total` | `model` | Total input/prompt tokens |
| `graphiti_completion_tokens_total` | `model` | Total output/completion tokens |
| `graphiti_total_tokens_total` | `model` | Total tokens (prompt + completion) |
| `graphiti_prompt_tokens_all_models_total` | - | Input tokens across all models |
| `graphiti_completion_tokens_all_models_total` | - | Output tokens across all models |
| `graphiti_total_tokens_all_models_total` | - | Total tokens across all models |

### Cost Counters

Track cumulative API costs in USD.

| Metric | Labels | Description |
|--------|--------|-------------|
| `graphiti_api_cost_total` | `model` | Total API cost per model |
| `graphiti_api_input_cost_total` | `model` | Input/prompt cost per model |
| `graphiti_api_output_cost_total` | `model` | Output/completion cost per model |
| `graphiti_api_cost_all_models_total` | - | Total cost across all models |
| `graphiti_api_input_cost_all_models_total` | - | Input cost across all models |
| `graphiti_api_output_cost_all_models_total` | - | Output cost across all models |

### Token Histograms

Track per-request token distributions for percentile analysis.

| Metric | Bucket Range | Description |
|--------|--------------|-------------|
| `graphiti_prompt_tokens_per_request` | 10 - 200,000 | Input tokens per request |
| `graphiti_completion_tokens_per_request` | 10 - 200,000 | Output tokens per request |
| `graphiti_total_tokens_per_request` | 10 - 200,000 | Total tokens per request |

**Token bucket boundaries:**

```
10, 25, 50, 100, 250, 500, 1000, 2000, 3000, 5000, 10000, 25000, 50000, 100000, 200000
```

### Cost Histograms

Track per-request cost distributions for percentile analysis.

| Metric | Bucket Range | Description |
|--------|--------------|-------------|
| `graphiti_api_cost_per_request` | $0.000005 - $5.00 | Total cost per request |
| `graphiti_api_input_cost_per_request` | $0.000005 - $5.00 | Input cost per request |
| `graphiti_api_output_cost_per_request` | $0.000005 - $5.00 | Output cost per request |

**Cost bucket boundaries:**

```
$0.000005, $0.00001, $0.000025, $0.00005, $0.0001, $0.00025, $0.0005, $0.001,
$0.0025, $0.005, $0.01, $0.025, $0.05, $0.1, $0.25, $0.5, $1.0, $2.5, $5.0
```

**Bucket coverage by model tier:**

| Range | Model Examples |
|-------|----------------|
| $0.000005 - $0.01 | Gemini Flash, GPT-4o-mini |
| $0.01 - $0.10 | GPT-4o, Claude Sonnet |
| $0.10 - $1.00 | GPT-4, Claude Opus |
| $1.00 - $5.00 | Large context on expensive models |

### Gauge Metrics

Track current state values.

| Metric | Values | Description |
|--------|--------|-------------|
| `graphiti_cache_enabled` | 0 or 1 | Whether prompt caching is enabled |
| `graphiti_cache_hit_rate` | 0-100 | Current session cache hit rate (%) |

### Cache Metrics (When Enabled)

These metrics populate when `MADEINOZ_KNOWLEDGE_PROMPT_CACHE_ENABLED=true`:

| Metric | Labels | Description |
|--------|--------|-------------|
| `graphiti_cache_hits_total` | `model` | Cache hits per model |
| `graphiti_cache_misses_total` | `model` | Cache misses per model |
| `graphiti_cache_tokens_saved_total` | `model` | Tokens saved via caching |
| `graphiti_cache_cost_saved_total` | `model` | Cost savings from caching (USD) |

!!! success "Caching Now Available for Gemini"
    **Prompt caching is now functional for Gemini models on OpenRouter.** The system routes Gemini models through the `/chat/completions` endpoint which supports multipart format with cache control markers. To enable caching, set `MADEINOZ_KNOWLEDGE_PROMPT_CACHE_ENABLED=true`. Other models continue using the `/responses` endpoint where caching is not yet supported.

## Prometheus Integration

### Scrape Configuration

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'madeinoz-knowledge'
    static_configs:
      - targets: ['localhost:9091']  # dev port
    scrape_interval: 15s
```

### Example PromQL Queries

**Token usage in last hour:**

```promql
increase(graphiti_total_tokens_all_models_total[1h])
```

**Tokens per model:**

```promql
sum by (model) (increase(graphiti_total_tokens_total[1h]))
```

**Total cost in last 24 hours:**

```promql
increase(graphiti_api_cost_all_models_total[24h])
```

**Cost per model:**

```promql
sum by (model) (increase(graphiti_api_cost_total[24h]))
```

**P95 cost per request:**

```promql
histogram_quantile(0.95, rate(graphiti_api_cost_per_request_bucket[5m]))
```

**P99 tokens per request:**

```promql
histogram_quantile(0.99, rate(graphiti_total_tokens_per_request_bucket[5m]))
```

**Median (P50) cost per request:**

```promql
histogram_quantile(0.50, rate(graphiti_api_cost_per_request_bucket[5m]))
```

## Understanding Histogram Buckets

Prometheus histograms are **cumulative**. Each bucket shows the count of observations **less than or equal to** that boundary.

**Example output:**

```
graphiti_api_cost_per_request_USD_bucket{le="0.0001"} 2.0
graphiti_api_cost_per_request_USD_bucket{le="0.00025"} 5.0
graphiti_api_cost_per_request_USD_bucket{le="0.0005"} 5.0
```

**Interpretation:**

- 2 requests cost ≤ $0.0001
- 3 more requests cost between $0.0001 and $0.00025
- 0 requests cost more than $0.00025 (count stays at 5)

## Grafana Dashboard

A basic Grafana dashboard can be created with these panels:

1. **Token Usage Rate** - `rate(graphiti_total_tokens_all_models_total[5m])`
2. **Cost Rate ($/hour)** - `rate(graphiti_api_cost_all_models_total[1h]) * 3600`
3. **Request Cost Distribution** - Histogram panel with `graphiti_api_cost_per_request_bucket`
4. **Token Usage by Model** - `sum by (model) (rate(graphiti_total_tokens_total[5m]))`

## Troubleshooting

### Metrics Not Appearing

1. **Check metrics are enabled:**
   ```bash
   grep MADEINOZ_KNOWLEDGE_PROMPT_CACHE_METRICS_ENABLED ~/.claude/.env
   ```

2. **Verify endpoint is accessible:**
   ```bash
   curl http://localhost:9091/metrics
   ```

3. **Check container logs:**
   ```bash
   docker logs madeinoz-knowledge-graph-mcp-dev 2>&1 | grep -i metric
   ```

### Counters Not Incrementing

Counter and histogram metrics only appear after LLM API calls are made. Metrics populate when:

- `add_memory` tool is used (triggers entity extraction)
- Any operation requiring LLM inference

Search operations (`search_memory_facts`, `search_memory_nodes`) use embeddings only and do not increment LLM metrics.

### Debug Logging

Enable detailed per-request logging:

```bash
# In ~/.claude/.env
MADEINOZ_KNOWLEDGE_PROMPT_CACHE_LOG_REQUESTS=true
LOG_LEVEL=DEBUG
```

This shows per-request metrics in container logs:

```
📊 Metrics: prompt=1234, completion=567, cost=$0.000089, input_cost=$0.000062, output_cost=$0.000027
```

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

## Related Documentation

- [Configuration Reference](configuration.md) - All environment variables
- [Developer Notes](developer-notes.md) - Internal architecture details
- [Troubleshooting](../troubleshooting/common-issues.md) - Common issues
