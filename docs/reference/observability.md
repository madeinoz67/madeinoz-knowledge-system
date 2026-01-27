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
| `graphiti_cache_write_tokens_total` | `model` | Tokens written to cache (cache creation) |

**Cache Savings Histograms:**

| Metric | Labels | Description |
|--------|--------|-------------|
| `graphiti_cache_tokens_saved_per_request` | `model` | Distribution of tokens saved per cache hit |
| `graphiti_cache_cost_saved_per_request` | `model` | Distribution of cost saved per cache hit (USD) |

!!! success "Caching Now Available for Gemini 2.5"
    **Prompt caching is functional for Gemini 2.5 models on OpenRouter.** Gemini 2.5 Flash uses **implicit caching** (automatic, no markers needed) with a minimum of 1,028 tokens. The system routes Gemini models through the `/chat/completions` endpoint. To enable caching, set `MADEINOZ_KNOWLEDGE_PROMPT_CACHE_ENABLED=true`. See [Prompt Caching](#prompt-caching-gemini) for details.

### Duration Metrics

Track LLM request latency for performance monitoring.

| Metric | Labels | Description |
|--------|--------|-------------|
| `graphiti_llm_request_duration_seconds` | `model` | Distribution of LLM request latency |

**Duration bucket boundaries (seconds):**

```
0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 15.0, 30.0, 60.0, 120.0, 300.0
```

**Bucket coverage:**

| Range | Request Type |
|-------|--------------|
| 0.05s - 1s | Cached/simple requests |
| 1s - 10s | Typical LLM calls |
| 10s - 60s | Complex reasoning, large context |
| 60s - 300s | Timeout territory |

### Error Metrics

Track LLM API errors for reliability monitoring.

| Metric | Labels | Description |
|--------|--------|-------------|
| `graphiti_llm_errors_total` | `model`, `error_type` | Error count by model and type |
| `graphiti_llm_errors_all_models_total` | - | Total errors across all models |

**Error types:**

- `rate_limit` - API rate limit exceeded
- `timeout` - Request timeout
- `BadRequestError`, `APIError`, etc. - Exception class names

!!! note "Error Metrics Visibility"
    Error counters only appear in Prometheus after at least one error has been recorded. If you don't see these metrics, it means no LLM errors have occurred.

### Throughput Metrics

Track episode processing volume.

| Metric | Labels | Description |
|--------|--------|-------------|
| `graphiti_episodes_processed_total` | `group_id` | Episodes processed per group |
| `graphiti_episodes_processed_all_groups_total` | - | Total episodes across all groups |

!!! note "Throughput Metrics Integration"
    Episode metrics require integration into the MCP tool handler and may not be active in all deployments.

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

**P95 request duration:**

```promql
histogram_quantile(0.95, rate(graphiti_llm_request_duration_seconds_bucket[5m]))
```

**Average request duration:**

```promql
rate(graphiti_llm_request_duration_seconds_sum[5m]) / rate(graphiti_llm_request_duration_seconds_count[5m])
```

**Error rate by model:**

```promql
sum by (model) (rate(graphiti_llm_errors_total[5m]))
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

The system includes a pre-configured Grafana dashboard with comprehensive monitoring panels.

### Quick Start (Development)

The development environment includes Prometheus and Grafana by default:

```bash
# Start dev environment with monitoring
docker compose -f src/skills/server/docker-compose-neo4j-dev.yml up -d

# Access points:
# - Grafana: http://localhost:3002 (login: admin/admin)
# - Prometheus UI: http://localhost:9092
```

### Production Setup (Optional)

Production monitoring uses Docker Compose profiles and is disabled by default:

```bash
# Start with monitoring enabled
docker compose -f src/skills/server/docker-compose-neo4j.yml --profile monitoring up -d

# Start without monitoring (default)
docker compose -f src/skills/server/docker-compose-neo4j.yml up -d

# Access points (when enabled):
# - Grafana: http://localhost:3001 (login: admin/admin or custom password)
# - Prometheus UI: http://localhost:9092
```

!!! tip "Custom Grafana Password"
    Set `GRAFANA_ADMIN_PASSWORD` environment variable for a secure password:
    ```bash
    export GRAFANA_ADMIN_PASSWORD=your-secure-password
    docker compose -f src/skills/server/docker-compose-neo4j.yml --profile monitoring up -d
    ```

### Dashboard Panels

The pre-configured dashboard includes these sections:

**Overview Row:**

- Total API Cost (USD)
- Total Tokens Used
- Cache Status (Enabled/Disabled)
- Cache Hit Rate (%)
- Total Errors

**Token Usage Row:**

- Token Usage Rate (by Model) - Time series
- Prompt vs Completion Tokens - Stacked area

**Cost Tracking Row:**

- Cost Rate ($/hour by Model) - Time series
- Cost by Model - Pie chart
- Input vs Output Cost - Donut chart

**Request Duration Row:**

- Request Duration Percentiles (P50, P95, P99) - Time series
- Average Request Duration (by Model) - Bar chart

**Cache Performance Row:**

- Cache Hit Rate Over Time - Time series
- Cache Cost Savings Rate - Time series
- Cache Hits vs Misses - Stacked area

**Errors Row:**

- Error Rate (by Model & Type) - Stacked bars
- Errors by Type - Pie chart

### Port Assignments

| Environment | Service | Port | Notes |
|-------------|---------|------|-------|
| Development | Grafana | 3002 | Neo4j backend |
| Development | Grafana | 3003 | FalkorDB backend (avoids UI conflict) |
| Development | Prometheus UI | 9092 | Query interface |
| Production | Grafana | 3001 | Neo4j backend |
| Production | Grafana | 3002 | FalkorDB backend |
| Production | Prometheus UI | 9092 | Query interface |

### Customizing the Dashboard

The dashboard configuration is stored at:

```
config/monitoring/grafana/provisioning/dashboards/madeinoz-knowledge.json
```

To customize:

1. Open Grafana and make changes via the UI
2. Export the dashboard JSON (Share > Export > Save to file)
3. Replace the provisioned dashboard file
4. Restart Grafana to apply changes

### Manual Panel Examples

If building a custom dashboard, use these PromQL queries:

**Usage & Cost:**

1. **Token Usage Rate** - `rate(graphiti_total_tokens_all_models_total[5m])`
2. **Cost Rate ($/hour)** - `rate(graphiti_api_cost_all_models_total[1h]) * 3600`
3. **Request Cost Distribution** - Histogram panel with `graphiti_api_cost_per_request_bucket`
4. **Token Usage by Model** - `sum by (model) (rate(graphiti_total_tokens_total[5m]))`

**Performance:**

5. **Request Duration P95** - `histogram_quantile(0.95, rate(graphiti_llm_request_duration_seconds_bucket[5m]))`
6. **Request Duration Heatmap** - Heatmap panel with `graphiti_llm_request_duration_seconds_bucket`
7. **Error Rate** - `sum(rate(graphiti_llm_errors_total[5m]))`

**Caching (when enabled):**

8. **Cache Hit Rate** - `graphiti_cache_hit_rate`
9. **Cost Savings Rate** - `rate(graphiti_cache_cost_saved_all_models_total[1h]) * 3600`
10. **Tokens Saved** - `increase(graphiti_cache_tokens_saved_all_models_total[1h])`

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

## Prompt Caching (Gemini)

Prompt caching reduces API costs by reusing previously processed prompt content. The system automatically caches system prompts and repeated content, serving subsequent requests from cache at reduced cost.

!!! info "Developer Documentation"
    For implementation details including architecture, code flow, and metrics internals, see the [Cache Implementation Guide](cache-implementation.md).

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                    First Request (Cache Miss)                    │
├─────────────────────────────────────────────────────────────────┤
│  System Prompt (800 tokens) ──► LLM processes ──► Cache stored  │
│  User Message (200 tokens)  ──► LLM processes ──► Response      │
│                                                                  │
│  Cost: Full price for 1000 tokens                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Second Request (Cache Hit)                     │
├─────────────────────────────────────────────────────────────────┤
│  System Prompt (800 tokens) ──► Retrieved from cache (0.25x)    │
│  User Message (200 tokens)  ──► LLM processes ──► Response      │
│                                                                  │
│  Cost: 0.25x for cached 800 + full for 200 = 75% savings        │
└─────────────────────────────────────────────────────────────────┘
```

### Gemini Caching Modes

| Model Family | Caching Mode | Minimum Tokens | How It Works |
|--------------|--------------|----------------|--------------|
| Gemini 2.5 | **Implicit** | 1,028 | Automatic - no markers needed |
| Gemini 2.0 | **Explicit** | 4,096 | Requires `cache_control` markers |

**Recommendation:** Use **Gemini 2.5 Flash** (`google/gemini-2.5-flash`) for best caching results. It has a lower token threshold (1,028 vs 4,096) and caching is automatic.

### Implicit vs Explicit Caching

**Implicit Caching (Gemini 2.5):**

- Automatic - Gemini decides what to cache
- No special formatting required
- Works with standard message format
- Cache keys based on content hash

**Explicit Caching (Gemini 2.0):**

- Requires `cache_control: {"type": "ephemeral"}` markers
- Messages must use multipart format
- Minimum 4,096 tokens required
- Most Graphiti prompts (~800 tokens) are below this threshold

### Configuration

```bash
# Enable prompt caching (required)
MADEINOZ_KNOWLEDGE_PROMPT_CACHE_ENABLED=true

# Enable metrics collection for cache statistics (recommended)
MADEINOZ_KNOWLEDGE_PROMPT_CACHE_METRICS_ENABLED=true

# Enable verbose caching logs for debugging (optional)
MADEINOZ_KNOWLEDGE_PROMPT_CACHE_LOG_REQUESTS=true

# Recommended model for caching
MADEINOZ_KNOWLEDGE_MODEL_NAME=google/gemini-2.5-flash
```

### Cache Pricing

Cached tokens are billed at **0.25x** the normal input token price:

| Model | Input Price | Cached Price | Savings |
|-------|-------------|--------------|---------|
| Gemini 2.5 Flash | $0.15/1M | $0.0375/1M | 75% |
| Gemini 2.5 Pro | $1.25/1M | $0.3125/1M | 75% |
| Gemini 2.0 Flash | $0.10/1M | $0.025/1M | 75% |

### Cache Metrics to Monitor

| Metric | Purpose |
|--------|---------|
| `graphiti_cache_hit_rate` | Current session hit rate (%) |
| `graphiti_cache_tokens_saved_total` | Cumulative tokens served from cache |
| `graphiti_cache_cost_saved_total` | Cumulative USD saved |
| `graphiti_cache_hits_total` / `graphiti_cache_misses_total` | Hit/miss ratio |

### Example PromQL Queries

**Cache hit rate over time:**

```promql
graphiti_cache_hit_rate
```

**Cost savings rate ($/hour):**

```promql
rate(graphiti_cache_cost_saved_all_models_total[1h]) * 3600
```

**Tokens saved in last hour:**

```promql
increase(graphiti_cache_tokens_saved_all_models_total[1h])
```

**Cache effectiveness by model:**

```promql
sum by (model) (graphiti_cache_hits_total) / sum by (model) (graphiti_cache_requests_total) * 100
```

### Troubleshooting Caching

#### Cache Hits Are Zero

**Possible causes:**

1. **Model doesn't support caching** - Only Gemini models support caching
2. **Token count below threshold** - Gemini 2.0 requires 4,096+ tokens (use Gemini 2.5 instead)
3. **Caching not enabled** - Set `MADEINOZ_KNOWLEDGE_PROMPT_CACHE_ENABLED=true`
4. **Different prompts** - Cache keys are content-based; slight variations = cache miss

**Debug steps:**

```bash
# Check caching is enabled
curl -s http://localhost:9091/metrics | grep graphiti_cache_enabled

# Check for any cache activity
curl -s http://localhost:9091/metrics | grep graphiti_cache

# Enable verbose logging
MADEINOZ_KNOWLEDGE_PROMPT_CACHE_LOG_REQUESTS=true
```

#### Low Cache Hit Rate

**Expected behavior:**

- First request for any unique prompt = cache miss
- Subsequent identical prompts = cache hit
- Entity extraction uses similar system prompts = good cache reuse

**Typical hit rates:**

| Scenario | Expected Hit Rate |
|----------|-------------------|
| Single `add_memory` call | 0% (first request) |
| Bulk import (10+ episodes) | 30-50% |
| Steady-state operation | 40-60% |

### Implementation Details

The caching system consists of three components:

1. **`caching_wrapper.py`** - Wraps OpenAI client methods
   - Adds timing for duration metrics
   - Catches errors for error metrics
   - Extracts cache statistics from responses

2. **`message_formatter.py`** - Formats messages for caching
   - Adds `cache_control` markers for explicit caching
   - Detects Gemini model families

3. **`metrics_exporter.py`** - Exports to Prometheus
   - Counters for totals
   - Histograms for distributions
   - Gauges for current state

**Files modified (in `docker/patches/`):**

```
docker/patches/
├── caching_wrapper.py      # Client wrapper with timing/error tracking
├── caching_llm_client.py   # LLM client routing
├── message_formatter.py    # Cache marker formatting
├── cache_metrics.py        # Metrics calculation
├── session_metrics.py      # Session-level aggregation
└── metrics_exporter.py     # Prometheus export
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     OpenRouter API                               │
│  (returns: usage, cost, cost_details, prompt_tokens_details)    │
│  (Gemini: cached_tokens in prompt_tokens_details)               │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │
┌─────────────────────────────────────────────────────────────────┐
│                   caching_wrapper.py                             │
│  - Wraps responses.parse() and chat.completions.create()        │
│  - Adds timing (record_request_duration)                         │
│  - Catches errors (record_error)                                 │
│  - Extracts cache metrics from response                          │
│  - Records cache hits/misses and savings                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   metrics_exporter.py                            │
│  - OpenTelemetry MeterProvider with custom Views                │
│  - Prometheus exporter on port 9090/9091                        │
│  - Counters: tokens, cost, cache hits/misses, errors            │
│  - Histograms: tokens/request, cost/request, duration           │
│  - Gauges: cache_enabled, cache_hit_rate                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Prometheus / Grafana                                │
│  - Scrape /metrics endpoint                                      │
│  - Visualize with dashboards                                     │
│  - Alert on thresholds (cost, errors, latency)                  │
└─────────────────────────────────────────────────────────────────┘
```

## Related Documentation

- [Configuration Reference](configuration.md) - All environment variables
- [Developer Notes](developer-notes.md) - Internal architecture details
- [Troubleshooting](../troubleshooting/common-issues.md) - Common issues
