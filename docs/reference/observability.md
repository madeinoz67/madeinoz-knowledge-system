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
# Access rate by importance (per second, restart-resilient)
sum(max_over_time(rate(knowledge_access_by_importance_total[5m]))[1h]) by (level)

# Access distribution by state (1-hour window)
max_over_time(knowledge_access_by_state_total[1h])

# Reactivation rate (last hour)
increase(knowledge_reactivations_total[1h])

# Age distribution heatmap
sum(rate(knowledge_days_since_last_access_bucket[5m])) by (le)

# Access vs decay correlation (dual-axis)
# Left axis: max_over_time(rate(knowledge_access_by_importance_total[5m]))[1h]
# Right axis: knowledge_decay_score_avg
```

### Example PromQL Queries (with Time-Over-Time Wrappers)

**Note:** These queries use `max_over_time()[1h]` wrappers to maintain continuity across service restarts.

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
histogram_quantile(0.95, max_over_time(rate(knowledge_classification_latency_seconds_bucket[5m]))[1h])
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

Counter metrics reset to zero when the service restarts, causing visible gaps in time series graphs. To maintain continuous visualization during restarts, dashboards use **time-over-time functions**:

**Pattern for counter queries:**

```promql
# Basic rate query (shows gaps after restart)
rate(graphiti_total_tokens_total[5m])

# Time-over-time wrapped (continuous across restarts)
max_over_time(rate(graphiti_total_tokens_total[5m]))[1h]
```

**Why this works:**

1. `rate(graphiti_total_tokens_total[5m])` - Calculates per-second rate over 5-minute window
2. `max_over_time(...)[1h]` - Takes maximum value seen over the past hour
3. When counter resets, the rate briefly spikes, then the max_over_time smooths the transition

**Histogram quantile pattern:**

```promql
# Basic histogram quantile (shows gaps)
histogram_quantile(0.95, rate(graphiti_llm_request_duration_seconds_bucket[5m]))

# Time-over-time wrapped (continuous)
histogram_quantile(0.95, max_over_time(rate(graphiti_llm_request_duration_seconds_bucket[5m]))[1h])
```

**Queries that don't need wrapping:**

- Gauge metrics (e.g., `graphiti_cache_enabled`, `graphiti_cache_hit_rate`)
- `increase()` with `$__range` (uses dashboard's selected time range)
- Absolute counter values (not rate calculations)

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

If building a custom dashboard, use these PromQL queries with time-over-time wrappers for restart resilience:

**Usage & Cost:**

1. **Token Usage Rate** - `max_over_time(rate(graphiti_total_tokens_all_models_total[5m]))[1h]`
2. **Cost Rate ($/hour)** - `max_over_time(rate(graphiti_api_cost_all_models_total[5m]) * 3600)[1h]`
3. **Request Cost Distribution** - Histogram panel with `graphiti_api_cost_per_request_bucket`
4. **Token Usage by Model** - `sum by (model) (max_over_time(rate(graphiti_total_tokens_total[5m]))[1h])`

**Performance:**

5. **Request Duration P95** - `histogram_quantile(0.95, max_over_time(rate(graphiti_llm_request_duration_seconds_bucket[5m]))[1h])`
6. **Request Duration Heatmap** - Heatmap panel with `graphiti_llm_request_duration_seconds_bucket`
7. **Error Rate** - `sum(max_over_time(rate(graphiti_llm_errors_total[5m]))[1h])`

**Caching (when enabled):**

8. **Cache Hit Rate** - `graphiti_cache_hit_rate` (gauge, no wrapper needed)
9. **Cost Savings Rate** - `max_over_time(rate(graphiti_cache_cost_saved_all_models_total[5m]) * 3600)[1h]`
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

## Related Documentation

- [Configuration Reference](configuration.md) - All environment variables
- [Developer Notes](developer-notes.md) - Internal architecture details
- [Troubleshooting](../troubleshooting/common-issues.md) - Common issues
