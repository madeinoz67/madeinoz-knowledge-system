# Quickstart: Prompt Cache Effectiveness Dashboard

## Overview

The Prompt Cache Effectiveness Dashboard provides visibility into Gemini prompt caching performance, ROI, and operational overhead. It is accessible via Grafana and displays real-time metrics with automatic refresh.

## Access

**Development**: http://localhost:3002/d/prompt-cache-effectiveness
**Production**: Replace `localhost:3002` with your Grafana server hostname

**Prerequisites**:
1. Knowledge system containers must be running (`bun run server-cli start`)
2. Prometheus must be scraping metrics (automatic when containers are up)
3. Dashboard must be provisioned in Grafana

## Dashboard Panels

### Overview Row (Top)

| Panel | Description | Metric |
|-------|-------------|--------|
| **Total Cost Savings** | USD saved since system start | `graphiti_cache_cost_saved_all_models_total` |
| **Hit Rate** | Current cache hit percentage | `graphiti_cache_hit_rate` |
| **Tokens Saved** | Total tokens saved from caching | `graphiti_cache_tokens_saved_all_models_total` |
| **Tokens Written** | Tokens consumed to create cache entries | `graphiti_cache_write_tokens_all_models_total` |

### Trends Row (Middle)

| Panel | Description | Time Range |
|-------|-------------|------------|
| **Savings Rate** | Cost savings per hour over time | Last 24 hours |
| **Hit Rate Trend** | Hit rate percentage over time | Last 24 hours |
| **Hits vs Misses** | Comparison of cache hits vs misses | Last 24 hours |

### Analysis Row (Bottom)

| Panel | Description | Type |
|-------|-------------|------|
| **Tokens Saved Distribution** | Heatmap showing distribution of cache hit sizes | Histogram heatmap |
| **Per-Model Comparison** | Side-by-side comparison of cache metrics by LLM model | Table |

## Key Metrics Explained

### Cost Savings (`graphiti_cache_cost_saved_all_models_total`)

**What it measures**: Cumulative USD saved by using cached responses instead of making new LLM API calls.

**Why it matters**: Direct ROI indicator for prompt caching. Higher values = more cost savings.

**Interpretation**:
- Increasing over time = caching is effective
- Flat line = no new cache hits or cache evictions
- Reset to 0 = service restart (expected, handled by time-over-time query)

### Hit Rate (`graphiti_cache_hit_rate`)

**What it measures**: Percentage of cache reads that return cached results vs. cache misses.

**Why it matters**: Primary indicator of cache health. Low hit rates indicate:
- Insufficient cache warming
- Poor cache key selection
- Changing access patterns

**Interpretation**:
- >50% = good (more reads served from cache)
- 20-50% = fair (room for improvement)
- <20% = poor (caching may not be cost-effective)

### Tokens Written (`graphiti_cache_write_tokens_all_models_total`)

**What it measures**: Total tokens consumed to create new cached entries.

**Why it matters**: Cache writes have overhead. Compare with tokens saved to assess efficiency.

**Interpretation**:
- High write volume + low savings = cache inefficiency
- Low write volume + high savings = cache is "warm" and effective

## Troubleshooting

### Dashboard Shows "No Data"

1. Verify containers are running: `bun run server-cli status`
2. Check metrics are being emitted: `curl http://localhost:9091/metrics | grep cache`
3. Verify Prometheus data source in Grafana settings
4. Check time range - try expanding to "Last 6 hours"

### Dashboard Shows Gaps or Drops

1. Check for service restarts: `docker logs <container-name>`
2. Verify time-over-time functions are used in queries
3. Check Prometheus retention period - if gaps exceed retention, data is lost

### Hit Rate Suddenly Drops

1. Check if cache was cleared or evicted
2. Verify application is using caching (not bypassing)
3. Check for changes in access patterns (new queries may not be cached yet)

## Time-Over-Time Functions

All cumulative counter metrics use `max_over_time()[1h]` to handle service restarts:

```promql
# Without time-over-time (WRONG - shows gaps)
graphiti_cache_hits_all_models_total

# With time-over-time (CORRECT - survives restarts)
max_over_time(graphiti_cache_hits_all_models_total[1h])
```

**Why this matters**: When the service restarts, counters reset to 0. Time-over-time functions preserve the last known value during the restart gap, maintaining visual continuity in dashboards.

## Refresh and Time Range

- **Auto-refresh**: Every 30 seconds (default)
- **Time range options**: 1h, 6h, 24h, 7d, 30d
- **Default view**: Last 24 hours

Use the time range selector in the top-right corner of Grafana to adjust.
