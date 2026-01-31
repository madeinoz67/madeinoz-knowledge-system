# Quickstart: Memory Access Patterns Dashboard

**Feature**: 014-memory-access-dashboard
**Audience**: Knowledge system administrators and data scientists

## Prerequisites

- Knowledge system containers running (`bun run server-cli start`)
- Grafana accessible at http://localhost:3000
- Prometheus collecting metrics from MCP server

## Accessing the Dashboard

1. Open Grafana: http://localhost:3000
2. Navigate to Dashboards → Browse
3. Select "Memory Access Patterns" from the list

Or direct URL: http://localhost:3000/d/memory-access-dashboard

## Dashboard Sections

### Header Row (Stats)

Quick overview of access patterns:

| Panel | What It Shows | Use For |
|-------|---------------|---------|
| Total Access Count | Cumulative memory accesses | Gauge overall activity |
| Access Rate | Current accesses per second | Monitor real-time load |
| Reactivations (Dormant) | Memories revived from dormant | Validate decay thresholds |
| Reactivations (Archived) | Memories revived from archived | Identify valuable old memories |

### Distribution Row

Understand access distribution:

- **Access by Importance**: Pie chart showing which importance levels are accessed most
  - Expect: CRITICAL and HIGH should have proportionally more accesses
  - Concern: If LOW has most accesses, review importance classification

- **Access by State**: Pie chart showing accesses by lifecycle state
  - Expect: ACTIVE memories should dominate
  - Concern: High DORMANT/ARCHIVED access suggests decay is too aggressive

### Time Series Row

Track patterns over time:

- **Access Rate Over Time**: Shows access velocity trends
  - Use: Identify peak usage periods
  - Use: Spot anomalies or system issues

- **Age Distribution Heatmap**: Shows when memories were last accessed
  - Buckets: 1d, 1w, 1m, 3m, 6m, 1y, 2y, 3y+
  - Use: Validate 180-day half-life setting
  - Concern: Cluster at 180d+ suggests slower decay needed

### Correlation Row

Validate decay effectiveness:

- **Access vs Decay Correlation**: Dual-axis time series
  - Left axis: Access rate
  - Right axis: Average decay score
  - Look for: Inverse correlation (high access → low decay)

## Time Range Selection

Use Grafana's time picker (top right) to adjust the view:

| Range | Use Case |
|-------|----------|
| Last 1h | Real-time monitoring |
| Last 6h | Recent activity review |
| Last 24h | Daily patterns (default) |
| Last 7d | Weekly trends |
| Last 30d | Long-term analysis |

## Common Tasks

### Task: Validate Decay Scoring

1. View "Access by Importance" pie chart
2. Compare with "Access by State" pie chart
3. Check "Reactivations" stats - should be low if decay is working
4. Review "Age Distribution" - memories should cluster below 180 days

**Healthy indicators**:
- CRITICAL/HIGH importance dominate access
- ACTIVE/STABLE states dominate access
- Few reactivations (< 5% of total accesses)
- Age distribution peaks before 90 days

### Task: Tune Decay Parameters

1. View "Age Distribution Heatmap"
2. Identify the bucket with most memories
3. If peak is far from 180d half-life, consider adjustment

| Observation | Action |
|-------------|--------|
| Peak at 30-60d | Decay may be too slow, consider shorter half-life |
| Peak at 180d+ | Decay may be too aggressive, consider longer half-life |
| Even distribution | System is well-tuned |

### Task: Investigate Reactivations

1. Check "Reactivations" stat panels
2. If unexpectedly high, click panel for detailed view
3. Cross-reference with "Access by State" - are DORMANT accesses increasing?
4. Review which memories are being reactivated

## Troubleshooting

### No Data Shown

1. Verify containers are running: `bun run server-cli status`
2. Check Prometheus is scraping: http://localhost:9090/targets
3. Verify metrics exist: http://localhost:9090/graph → query `knowledge_memory_access_total`

### Panels Show Gaps

Normal after MCP server restart. Dashboard uses `max_over_time()` to minimize gaps.
Wait 5-10 minutes for fresh data.

### Stale Data Indicator

If panels show "data stale", the MCP server may be down or not exporting metrics.
Check: `bun run server-cli logs`

## Related Dashboards

- **Memory Decay**: Lifecycle state transitions and decay scores
- **Graph Health**: Overall knowledge graph health metrics
