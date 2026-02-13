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
- **Memory decay** - Lifecycle states, maintenance operations, classification performance (Feature 009)

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

!!! success "Prompt Caching via OpenRouter"
    **Prompt caching is available for Gemini models via OpenRouter.** The system uses explicit `cache_control` markers (similar to Anthropic's approach) with a minimum of 1,024 tokens. To enable caching, set `MADEINOZ_KNOWLEDGE_PROMPT_CACHE_ENABLED=true`. See [Prompt Caching](#prompt-caching-gemini-via-openrouter) for details.

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

## Memory Decay Metrics (Feature 009)

The memory decay system tracks lifecycle state transitions, maintenance operations, and classification performance. These metrics use the `knowledge_` prefix.

### Health Endpoint

A dedicated health endpoint provides decay system status:

```bash
curl http://localhost:9090/health/decay
```

Returns:

```json
{
  "status": "healthy",
  "decay_enabled": true,
  "last_maintenance": "2026-01-28T12:00:00Z",
  "metrics_endpoint": "/metrics"
}
```

### Maintenance Metrics

Track scheduled maintenance operations that recalculate decay scores and transition lifecycle states.

| Metric | Labels | Description |
|--------|--------|-------------|
| `knowledge_decay_maintenance_runs_total` | `status` | Maintenance runs by status (success/failure) |
| `knowledge_decay_scores_updated_total` | - | Decay scores recalculated |
| `knowledge_maintenance_duration_seconds` | - | Maintenance run duration (histogram) |
| `knowledge_memories_purged_total` | - | Soft-deleted memories permanently removed |

**Duration bucket boundaries (seconds):**

```
1, 5, 30, 60, 120, 300, 600
```

Performance target: Complete within 10 minutes (600 seconds).

### Lifecycle Metrics

Track state transitions as memories age or are accessed.

| Metric | Labels | Description |
|--------|--------|-------------|
| `knowledge_lifecycle_transitions_total` | `from_state`, `to_state` | State transitions by type |
| `knowledge_memories_by_state` | `state` | Current count per lifecycle state |
| `knowledge_memories_total` | - | Total memory count (excluding soft-deleted) |

**Lifecycle states:**

| State | Description |
|-------|-------------|
| `ACTIVE` | Recently accessed, full relevance |
| `DORMANT` | Not accessed for 30+ days |
| `ARCHIVED` | Not accessed for 90+ days |
| `EXPIRED` | Marked for deletion |
| `SOFT_DELETED` | Deleted but recoverable for 90 days |
| `PERMANENT` | High importance + stability, never decays |

### Classification Metrics

Track LLM-based importance/stability classification.

| Metric | Labels | Description |
|--------|--------|-------------|
| `knowledge_classification_requests_total` | `status` | Classification attempts (success/failure/fallback) |
| `knowledge_classification_latency_seconds` | - | LLM response time (histogram) |

**Latency bucket boundaries (seconds):**

```
0.1, 0.5, 1, 2, 5
```

**Classification statuses:**

| Status | Description |
|--------|-------------|
| `success` | LLM classified successfully |
| `failure` | LLM call failed, used defaults |
| `fallback` | LLM unavailable, used defaults |

### Aggregate Metrics

Track average scores across the knowledge graph.

| Metric | Description |
|--------|-------------|
| `knowledge_decay_score_avg` | Average decay score (0.0-1.0) |
| `knowledge_importance_avg` | Average importance (1-5) |
| `knowledge_stability_avg` | Average stability (1-5) |

### Search Metrics

Track weighted search operations that boost by relevance.

| Metric | Labels | Description |
|--------|--------|-------------|
| `knowledge_weighted_searches_total` | - | Weighted search operations |
| `knowledge_search_weighted_latency_seconds` | - | Scoring overhead (histogram) |

### Memory Access Pattern Metrics (Feature 015)

Track memory access patterns during search operations to validate decay scoring effectiveness.

| Metric | Labels | Description |
|--------|--------|-------------|
| `knowledge_access_by_importance_total` | `level` | Cumulative accesses by importance level (LOW/MEDIUM/HIGH/CRITICAL) |
| `knowledge_access_by_state_total` | `state` | Cumulative accesses by lifecycle state (ACTIVE/DORMANT/ARCHIVED/PERMANENT) |
| `knowledge_days_since_last_access` | - | Histogram of days since memory was last accessed |
| `knowledge_reactivations_total` | `from_state` | Memories reactivated from DORMANT/ARCHIVED to ACTIVE |

**Importance level mapping:**

| Score | Label | Description |
|-------|-------|-------------|
| 1-2 | LOW | Lower priority memories |
| 3 | MEDIUM | Standard importance (default) |
| 4 | HIGH | Important memories |
| 5 | CRITICAL | Core/foundational memories |

**Days histogram bucket boundaries:**

```
1, 7, 30, 90, 180, 365, 730, 1095
```

| Bucket | Description |
|--------|-------------|
| 1 | 1 day ago |
| 7 | 1 week ago |
| 30 | 1 month ago |
| 90 | 3 months ago |
| 180 | 6 months (half-life threshold) |
| 365 | 1 year ago |
| 730 | 2 years ago |
| 1095 | 3+ years ago |

!!! note "Metric Recording Behavior"
    Access pattern metrics are recorded during `search_memory_nodes` and `search_memory_facts` operations. The histogram only records when nodes have a `last_accessed_at` attribute set.

**Access Pattern PromQL Queries:**

```promql
# Access rate by importance (per second)
sum(rate(knowledge_access_by_importance_total[5m])) by (level)

# Access distribution by state (current values)
knowledge_access_by_state_total

# Reactivation rate (last hour)
increase(knowledge_reactivations_total[1h])

# Age distribution heatmap
sum(rate(knowledge_days_since_last_access_bucket[5m])) by (le)

# Access vs decay correlation (dual-axis)
# Left axis: rate(knowledge_access_by_importance_total[5m])
# Right axis: knowledge_decay_score_avg
```

### Example PromQL Queries

**Maintenance success rate (last 24 hours):**

```promql
sum(increase(knowledge_decay_maintenance_runs_total{status="success"}[24h]))
/
sum(increase(knowledge_decay_maintenance_runs_total[24h]))
```

**State distribution:**

```promql
knowledge_memories_by_state
```

**Classification fallback rate:**

```promql
sum(rate(knowledge_classification_requests_total{status="fallback"}[5m]))
/
sum(rate(knowledge_classification_requests_total[5m]))
```

**Lifecycle transitions per hour:**

```promql
sum by (from_state, to_state) (increase(knowledge_lifecycle_transitions_total[1h]))
```

**P95 classification latency:**

```promql
histogram_quantile(0.95, rate(knowledge_classification_latency_seconds_bucket[5m]))
```

### Alert Rules

Alert rules are defined in `config/monitoring/prometheus/alerts/knowledge.yml`:

| Alert | Condition | Severity |
|-------|-----------|----------|
| `MaintenanceTimeout` | Duration > 10 minutes | warning |
| `MaintenanceFailed` | Any failure in last hour | critical |
| `ClassificationDegraded` | Fallback rate > 20% | warning |
| `ExcessiveExpiration` | > 100 expired/hour | warning |
| `SoftDeleteBacklog` | > 1000 awaiting purge | warning |

## Prometheus Integration

### Metrics Naming Conventions

The system follows **OpenTelemetry Semantic Conventions** for metric naming:

| Convention | Implementation |
|------------|----------------|
| **Units in metadata** | Units specified via `unit` field in Grafana, not in metric names |
| **No unit suffixes** | Metrics use `_total` for counters, not `_cost_total_usd` or `_tokens_total_count` |
| **Descriptive base** | Metric names describe what is measured (e.g., `api_cost`, `total_tokens`) |
| **Counter suffix** | All cumulative counters use `_total` suffix per OpenTelemetry convention |

**Examples of correct naming:**

| Metric | Correct | Incorrect |
|--------|---------|-----------|
| API cost | `graphiti_api_cost_total` | `graphiti_api_cost_USD_total` |
| Cache hit rate | `graphiti_cache_hit_rate` | `graphiti_cache_hit_rate_percent` |
| Tokens saved | `graphiti_cache_tokens_saved_total` | `graphiti_cache_tokens_saved_count` |

**Dashboard unit configuration:**

Instead of embedding units in metric names, Grafana dashboards use the `unit` field to display appropriate units:

- `currencyUSD` - Cost metrics display in USD
- `short` - Count metrics display as plain numbers
- `percent` - Rate metrics display as percentages
- `seconds` - Duration metrics display in seconds
- `locale` - Token count display with locale formatting

### Handling Service Restarts

Counter metrics reset to zero when the service restarts, which causes `rate()` calculations to show brief gaps or spikes in visualizations. This is expected Prometheus behavior for counter resets.

**Current dashboard behavior:**

- `rate()` queries will briefly show gaps during counter resets
- Grafana automatically interpolates across short gaps
- For longer gaps, consider increasing the scrape interval

**Note:** Time-over-time functions like `max_over_time()` cannot wrap `rate()` results in PromQL. They must wrap range vector selectors directly (e.g., `max_over_time(metric[1h])`). For rate-based metrics, accepting brief gaps during restarts is the standard approach.

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

### Available Dashboards

The system includes multiple pre-configured Grafana dashboards:

| Dashboard | UID | Purpose |
|-----------|-----|---------|
| **Graph Health** | `graph-health-dashboard` | Entity states, episodes, operation rates, error tracking |
| **Memory Decay** | `memory-decay-dashboard` | Lifecycle transitions, maintenance operations, classification metrics |
| **Memory Access Patterns** | `memory-access-dashboard` | Access distribution by importance/state, reactivation tracking, decay correlation |
| **Knowledge System** | `madeinoz-knowledge` | Token usage, cost tracking, request duration, cache performance |
| **Prompt Cache Effectiveness** | `prompt-cache-effectiveness` | Cache ROI, hit/miss patterns, write overhead, per-model comparison |
| **Queue Processing Metrics** | `queue-metrics` | Queue depth, latency, consumer health, throughput, errors |

### Prompt Cache Effectiveness Dashboard

**Purpose**: Dedicated monitoring for Gemini prompt caching performance and ROI

**Access**: `http://localhost:3002/d/prompt-cache-effectiveness` (dev)

**Panels**:

| Panel | Metric | Description |
|-------|--------|-------------|
| **Total Cost Savings** | `graphiti_cache_cost_saved_all_models_total` | USD saved from caching (uses time-over-time for restart resilience) |
| **Hit Rate** | `graphiti_cache_hit_rate` | Current cache hit percentage (gauge: >50% green, 20-50% yellow, <20% red) |
| **Tokens Saved** | `graphiti_cache_tokens_saved_all_models_total` | Total tokens saved from caching |
| **Tokens Written** | `graphiti_cache_write_tokens_all_models_total` | Tokens consumed to create cache entries (overhead) |
| **Savings Rate** | `rate(...[1h]) * 3600` | Cost savings per hour trend |
| **Hit Rate Trend** | `graphiti_cache_hit_rate` | Hit rate over time for anomaly detection |
| **Hits vs Misses** | Dual time series | Comparison of cache hits vs misses rate |
| **Tokens Saved Distribution** | `graphiti_cache_tokens_saved_per_request_bucket` | Heatmap showing cache hit size distribution |
| **Per-Model Performance** | Table | Side-by-side comparison of caching by LLM model |

**Key Features**:

- Time-over-time queries (`max_over_time()[1h]`) handle service restarts without data gaps
- Color-coded thresholds for quick health assessment
- 30-second auto-refresh (user-configurable)
- Single 1080p screen layout (no scrolling required)

**Troubleshooting Dashboard**:

1. **No data showing**: Verify cache is enabled (`curl http://localhost:9091/metrics | grep cache_enabled`)
2. **Gaps in charts**: Check for service restarts - time-over-time functions should smooth gaps
3. **Zero hit rate**: Normal for new deployments; requires repeated similar prompts to build cache

### Memory Access Patterns Dashboard

**Purpose**: Validate decay scoring effectiveness by visualizing memory access patterns across importance levels, lifecycle states, and time periods

**Access**: `http://localhost:3002/d/memory-access-dashboard` (dev)

**Panels**:

| Panel | Metric | Description |
|-------|--------|-------------|
| **Total Access Count** | `knowledge_memory_access_total` | Cumulative memory accesses (uses max_over_time for restart resilience) |
| **Access Rate** | `rate(...[5m])` | Current memory accesses per second |
| **Reactivations (Dormant)** | `knowledge_reactivations_total{from_state="DORMANT"}` | Memories revived from dormant state (thresholds: green=0, yellow=5, red=20) |
| **Reactivations (Archived)** | `knowledge_reactivations_total{from_state="ARCHIVED"}` | Memories revived from archived state (thresholds: green=0, yellow=3, red=10) |
| **Access by Importance** | `knowledge_access_by_importance_total` | Pie chart showing access distribution by CRITICAL/HIGH/MEDIUM/LOW |
| **Access by State** | `knowledge_access_by_state_total` | Pie chart showing access distribution by ACTIVE/STABLE/DORMANT/ARCHIVED |
| **Access Rate Over Time** | `rate(knowledge_memory_access_total[5m])` | Time series trend of access velocity |
| **Age Distribution** | `knowledge_days_since_last_access_bucket` | Heatmap showing when memories were last accessed |
| **Access vs Decay Correlation** | Dual-axis | Compares access rate (left) with average decay score (right) |

**Key Features**:

- Time-over-time queries (`max_over_time()[1h]`) handle service restarts without data gaps
- Dual-axis correlation panel for validating decay effectiveness
- Color-coded reactivation thresholds for quick anomaly detection
- 30-second auto-refresh with 24-hour default time range

**Common Tasks**:

1. **Validate Decay Scoring**: Check if CRITICAL/HIGH importance memories have proportionally more accesses
2. **Tune Decay Parameters**: Use age distribution heatmap to identify if 180-day half-life is appropriate
3. **Investigate Reactivations**: High reactivation counts suggest decay is too aggressive

### Customizing Dashboards

Dashboard configurations are stored at:

```
config/monitoring/grafana/dashboards/
├── graph-health-dashboard.json
├── memory-access-dashboard.json
├── memory-decay-dashboard.json
├── madeinoz-knowledge.json
└── prompt-cache-effectiveness.json
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
2. **Cost Rate ($/hour)** - `rate(graphiti_api_cost_all_models_total[5m]) * 3600`
3. **Request Cost Distribution** - Histogram panel with `graphiti_api_cost_per_request_bucket`
4. **Token Usage by Model** - `sum by (model) (rate(graphiti_total_tokens_total[5m]))`

**Performance:**

1. **Request Duration P95** - `histogram_quantile(0.95, rate(graphiti_llm_request_duration_seconds_bucket[5m]))`
2. **Request Duration Heatmap** - Heatmap panel with `graphiti_llm_request_duration_seconds_bucket`
3. **Error Rate** - `sum(rate(graphiti_llm_errors_total[5m]))`

**Caching (when enabled):**

1. **Cache Hit Rate** - `graphiti_cache_hit_rate` (gauge metric)
2. **Cost Savings Rate** - `rate(graphiti_cache_cost_saved_all_models_total[5m]) * 3600`
3. **Tokens Saved** - `increase(graphiti_cache_tokens_saved_all_models_total[1h])`

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

## Prompt Caching (Gemini via OpenRouter)

Prompt caching reduces API costs by up to 15-20% by reusing previously processed prompt content. The system adds explicit `cache_control` markers to requests when enabled, allowing OpenRouter to serve cached content at reduced cost (0.25x normal price).

**Note:** Prompt caching is **disabled by default** and must be explicitly enabled via configuration.

!!! info "Developer Documentation"
    For implementation details including architecture diagrams, code flow, and metrics internals, see the [Cache Implementation Guide](cache-implementation.md).

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

### How Caching Works via OpenRouter

The Madeinoz Knowledge System implements **explicit prompt caching** via OpenRouter using `cache_control` markers (similar to Anthropic's approach):

| Aspect | Description |
|--------|-------------|
| **Implementation** | Explicit `cache_control` markers added to last message part |
| **Format** | Multipart messages with content parts array |
| **Cache lifecycle** | Managed by OpenRouter automatically |
| **Minimum tokens** | 1,024 tokens for caching to be applied |
| **Default state** | **Disabled** - must be explicitly enabled |

**Recommended Model:** `google/gemini-2.0-flash-001` via OpenRouter

This implementation uses the **CachingLLMClient** wrapper which:

1. Checks if caching is enabled (environment variable)
2. Verifies the model is Gemini via OpenRouter
3. Converts messages to multipart format
4. Adds `cache_control` marker to the last content part
5. Extracts cache metrics from responses (cache_read_tokens, cache_write_tokens)

### Configuration

```bash
# Enable prompt caching (disabled by default)
MADEINOZ_KNOWLEDGE_PROMPT_CACHE_ENABLED=true

# Enable metrics collection for cache statistics (recommended)
MADEINOZ_KNOWLEDGE_PROMPT_CACHE_METRICS_ENABLED=true

# Enable verbose caching logs for debugging (optional)
MADEINOZ_KNOWLEDGE_PROMPT_CACHE_LOG_REQUESTS=true

# Recommended model for caching
MADEINOZ_KNOWLEDGE_MODEL_NAME=google/gemini-2.0-flash-001
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

## Queue Metrics (Feature 017)

The queue processing metrics provide observability for message queue operations, tracking throughput, latency, consumer health, and failure patterns. These metrics use the `messaging_` prefix.

### Overview

Queue metrics monitor the full lifecycle of message processing:

- **Enqueue** - Messages added to queue
- **Wait** - Time spent in queue before processing
- **Processing** - Time to process each message
- **Completion** - Success or failure with error categorization
- **Consumer Health** - Lag, saturation, active consumer count

### Available Metrics

#### Throughput Counters

Track cumulative message counts.

| Metric | Labels | Description |
|--------|--------|-------------|
| `messaging_messages_processed_total` | `queue_name`, `status` | Total messages processed (success/failure) |
| `messaging_messages_failed_total` | `queue_name`, `error_type` | Total failures by error category |
| `messaging_retries_total` | `queue_name` | Total retry attempts |

**Error categories** (coarse-grained to prevent high cardinality):

| Category | Example Errors |
|----------|----------------|
| `ConnectionError` | `ConnectionError`, `ConnectionRefusedError`, `OperationalError` |
| `ValidationError` | `ValidationError`, `ValueError`, `PydanticException` |
| `TimeoutError` | `TimeoutError`, `AsyncTimeoutError` |
| `RateLimitError` | `RateLimitError`, `RateLimitExceededError` |
| `UnknownError` | Any uncategorized error |

#### Queue Depth Gauge

Track current queue size (messages waiting).

| Metric | Labels | Description |
|--------|--------|-------------|
| `messaging_queue_depth` | `queue_name`, `priority` | Current number of messages waiting |

#### Consumer Health Gauges

Track consumer pool state and utilization.

| Metric | Labels | Description |
|--------|--------|-------------|
| `messaging_active_consumers` | `queue_name` | Number of active consumers |
| `messaging_consumer_saturation` | `queue_name` | Consumer utilization (0-1, 1=fully saturated) |
| `messaging_consumer_lag_seconds` | `queue_name` | Time to catch up (seconds) |

#### Latency Histograms

Track processing time distributions for percentile analysis.

| Metric | Bucket Range | Description |
|--------|--------------|-------------|
| `messaging_processing_duration_seconds` | 5ms - 10s | Time to process a message |
| `messaging_wait_time_seconds` | 5ms - 10s | Time spent in queue before processing |
| `messaging_end_to_end_latency_seconds` | 5ms - 10s | Total time from enqueue to completion |

**Duration bucket boundaries (seconds):**

```
0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10
```

| Range | Processing Type |
|-------|-----------------|
| 5-50ms | Fast processing (simple operations) |
| 50-250ms | Normal processing |
| 250ms-1s | Slow processing |
| 1-10s | Very slow processing (possible issues) |

### Example PromQL Queries

**Queue depth trend:**

```promql
messaging_queue_depth
```

**Processing throughput (messages/second):**

```promql
sum(rate(messaging_messages_processed_total{status="success"}[5m]))
```

**Error rate (percentage):**

```promql
sum(rate(messaging_messages_failed_total[5m]))
/
sum(rate(messaging_messages_processed_total[5m])) * 100
```

**P95 processing latency:**

```promql
histogram_quantile(0.95, sum(rate(messaging_processing_duration_seconds_bucket[5m])) by (le))
```

**P95 wait time (queue delay):**

```promql
histogram_quantile(0.95, sum(rate(messaging_wait_time_seconds_bucket[5m])) by (le))
```

**P95 end-to-end latency:**

```promql
histogram_quantile(0.95, sum(rate(messaging_end_to_end_latency_seconds_bucket[5m])) by (le))
```

**Consumer saturation check:**

```promql
messaging_consumer_saturation
# Alert if > 0.85 (85% utilization)
```

**Time to drain queue (at current rate):**

```promql
messaging_queue_depth / sum(rate(messaging_messages_processed_total{status="success"}[5m]))
```

**Retry rate (retries per message):**

```promql
sum(rate(messaging_retries_total[5m])) / sum(rate(messaging_messages_processed_total[5m]))
```

### Queue Metrics Dashboard

**Access**: `http://localhost:3002/d/queue-metrics` (dev)

A 12-panel Grafana dashboard provides comprehensive queue monitoring:

**Overview Row (4 panels):**

| Panel | Metric | Thresholds |
|-------|--------|------------|
| Queue Depth | `messaging_queue_depth` | green=0, yellow=10, red=50 |
| Consumer Saturation | `messaging_consumer_saturation` | green=0, yellow=0.5, red=0.85 |
| Consumer Lag | `messaging_consumer_lag_seconds` | green=0, yellow=30s, red=300s |
| Active Consumers | `messaging_active_consumers` | green=1+, yellow=1, red=0 |

**Time Series Rows:**

- Queue Depth Over Time - Trend analysis
- Processing Latency (P50/P95/P99) - Percentile analysis
- Wait Time (P50/P95) - Queue delay analysis
- End-to-End Latency (P50/P95) - Full journey latency
- Throughput (Success/Failure Rate) - Ops/second
- Error Rate (%) - Gauge panel
- Failures by Error Type - Pie chart
- Retry Rate - Retries/second trend

### Troubleshooting Queue Issues

#### Growing Queue Backlog

**Symptoms:**

- `messaging_queue_depth` increasing over time
- `messaging_consumer_lag_seconds` increasing
- `messaging_consumer_saturation` near 1.0

**Diagnosis:**

```promql
# Check if production rate exceeds consumption rate
sum(rate(messaging_messages_processed_total[5m])) < sum(rate(messages_enqueued[5m]))

# Check processing latency trend
histogram_quantile(0.95, sum(rate(messaging_processing_duration_seconds_bucket[5m])) by (le))
```

**Solutions:**

1. Scale consumers (increase `messaging_active_consumers`)
2. Optimize processing (reduce latency)
3. Implement priority queueing
4. Add rate limiting at enqueue

#### High Consumer Lag

**Symptoms:**

- `messaging_consumer_lag_seconds` > 300 (5 minutes)
- Queue depth stable but lag increasing

**Diagnosis:**

```promql
# Time to catch up at current rate
messaging_queue_depth / sum(rate(messaging_messages_processed_total{status="success"}[5m]))
```

**Solutions:**

1. Increase consumer count
2. Reduce processing time per message
3. Implement batch processing
4. Scale horizontally (multiple queue instances)

#### Consumer Saturation

**Symptoms:**

- `messaging_consumer_saturation` > 0.85
- Wait times increasing

**Diagnosis:**

```promql
# Check wait time trend
histogram_quantile(0.95, sum(rate(messaging_wait_time_seconds_bucket[5m])) by (le))
```

**Solutions:**

1. Add more consumers
2. Increase consumer parallelism
3. Implement async processing

#### High Error Rate

**Symptoms:**

- `messaging_messages_failed_total` increasing
- Error rate gauge > 5%

**Diagnosis:**

```promql
# Error breakdown by type
sum by (error_type) (messaging_messages_failed_total)
```

**Solutions:**

1. Check error types in failures panel
2. Fix common error patterns
3. Implement circuit breaker for failing services
4. Add retry with exponential backoff

#### High Retry Rate

**Symptoms:**

- `messaging_retries_total` increasing rapidly
- Retry rate > 0.1 retries/message

**Diagnosis:**

```promql
# Retries per successful message
sum(rate(messaging_retries_total[5m])) / sum(rate(messaging_messages_processed_total{status="success"}[5m]))
```

**Solutions:**

1. Identify root cause of failures
2. Implement dead letter queue
3. Add backoff strategy
4. Limit max retry attempts

### Implementation

The queue metrics are implemented in `docker/patches/metrics_exporter.py`:

```python
class QueueMetricsExporter:
    """Manages queue processing metrics."""

    def record_enqueue(queue_name, priority)
    def record_dequeue(queue_name)
    def record_processing_complete(queue_name, duration, success, error_type)
    def record_retry(queue_name)
    def update_queue_depth(queue_name, depth, priority)
    def update_consumer_metrics(queue_name, active, saturation, lag_seconds)
```

**Thread safety**: All state modifications use locks.

**Graceful degradation**: Methods do nothing if metrics are disabled.

## LKAP Logging (Feature 022)

### Overview

The Local Knowledge Augmentation Platform (LKAP) provides structured logging for observability of document ingestion, classification, and knowledge promotion operations. Logs track ingestion status, classification confidence, and performance metrics.

### Configuration

Logging behavior is controlled via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MADEINOZ_KNOWLEDGE_RAGFLOW_LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `RAGFLOW_LOG_PATH` | `/ragflow/logs/ragflow.log` | Log file path |

### Log Locations

Logs are written to two destinations:

1. **Console** (stdout): Full output with timestamps for development
2. **File**: Rotating file handler (10MB max, 5 backups)

File log format:
```
YYYY-MM-DD HH:MM:SS - logger_name - LEVEL - function_name:line_number - message
```

Console format:
```
YYYY-MM-DD HH:MM:SS - logger_name - LEVEL - message
```

### Component Loggers

| Logger Name | Component | Description |
|-------------|-----------|-------------|
| `lkap.ingestion` | Document Ingestion | File parsing, chunking, storage operations |
| `lkap.classification` | Progressive Classification | Domain classification, confidence scoring |
| `lkap.promotion` | Evidence-to-KG Promotion | Knowledge graph fact promotion |
| `lkap.ragflow` | RAGFlow Client | Vector database operations |
| `lkap.embeddings` | Embedding Service | Embedding generation |
| `lkap.chunking` | Chunking Service | Document chunking operations |

### Key Log Messages

#### Ingestion Status

**Successful ingestion:**
```
Ingestion complete for {doc_id}: 42/42 chunks in 12.3s
Document moved to processed: /path/to/processed/{doc_id}/v1/filename.pdf
```

**Skipped (duplicate):**
```
Document already ingested (hash match): filename.pdf
```

**Failed ingestion:**
```
Ingestion failed for {file_path}: {error_message}
```

#### Classification Events

**Domain classified:**
```
User override for domain: {path} -> {domain}
Saved user override: {source_key} domain: {original} -> {new}
```

**Low confidence warning:**
```
Could not classify domain for {filename}, defaulting to software
```

#### Batch Processing

**Batch completion:**
```
Batch ingestion complete: 95/100 successful, 3 skipped, 2 failed in 285.1s
Found 150 documents for batch ingestion
```

**Performance warnings:**
```
Batch ingestion performance: 3.45s per document (target: 3s for 100 docs in 5 min)
```

### Ingestion Metrics

Logged after each document ingestion:

| Metric | Description |
|--------|-------------|
| `doc_id` | Unique document identifier |
| `duration_seconds` | Total ingestion time |
| `chunks_processed` | Number of chunks successfully processed |
| `chunks_total` | Total chunks in document |
| `errors` | List of error messages (if any) |
| `success` | Boolean indicating success/failure |

### Confidence Bands

Classification results include confidence band for quality monitoring:

| Band | Confidence Range | Action |
|------|------------------|--------|
| HIGH | >= 0.85 | Auto-accept |
| MEDIUM | 0.70 - 0.84 | Optional review |
| LOW | < 0.70 | Required review |

### Performance Targets

| Operation | Target | Logged By |
|-----------|--------|-----------|
| Document ingestion | < 3.0 seconds per document | `lkap.ingestion` |
| Batch ingestion (100 docs) | < 5 minutes total | `lkap.ingestion` |
| Classification | < 500ms | `lkap.classification` |
| Chunking | < 1 second per document | `lkap.chunking` |

### Monitoring Recommendations

**Key indicators to monitor:**

1. **Ingestion success rate**: Track "Ingestion complete" vs "Ingestion failed"
2. **Duplicate detection**: Monitor "Document already ingested" frequency
3. **Classification confidence**: Watch for low confidence warnings
4. **Performance degradation**: Alert on per-document time > 3.0s
5. **Batch processing**: Monitor success/skipped/failed ratios

**Example log monitoring queries:**

```bash
# Count ingestion failures
grep "Ingestion failed" /ragflow/logs/ragflow.log | wc -l

# Find slow ingestions (>3s)
grep "Ingestion complete" /ragflow/logs/ragflow.log | \
  awk '{split($0,a,"in "); split(a[2],b,"s"); if(b[1]>3.0) print}'

# Low confidence classifications
grep "defaulting to software" /ragflow/logs/ragflow.log
```

### Troubleshooting

#### High Ingestion Failure Rate

**Symptoms:** Many "Ingestion failed" messages

**Check:**
1. File permissions on inbox directory
2. RAGFlow service availability
3. Disk space on processed path

#### Low Classification Confidence

**Symptoms:** Frequent "defaulting to software" warnings

**Check:**
1. Document path structure (add domain-specific folders)
2. Content quality (are documents technical enough?)
3. Consider user overrides for recurring sources

#### Performance Degradation

**Symptoms:** Per-document time > 3.0s

**Check:**
1. Embedding service responsiveness
2. RAGFlow API latency
3. Network connectivity to services

### Implementation

The logging system is implemented in `docker/patches/lkap_logging.py`:

```python
def setup_lkap_logging()
    # Configures console and rotating file handlers

def get_logger(name: str) -> logging.Logger
    # Returns configured logger for component

class IngestionMetrics
    # Tracks ingestion metrics and produces summaries
```

**Usage example:**

```python
from lkap_logging import get_logger, IngestionMetrics

logger = get_logger("lkap.ingestion")
metrics = IngestionMetrics(doc_id)

# Track progress
metrics.increment_chunks()
metrics.set_chunks_total(42)

# Log summary
metrics.log_summary(logger)
```

## Related Documentation

- [Configuration Reference](configuration.md) - All environment variables
- [Developer Notes](developer-notes.md) - Internal architecture details
- [Troubleshooting](../troubleshooting/common-issues.md) - Common issues
