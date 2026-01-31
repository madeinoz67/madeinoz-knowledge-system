# Research: Memory Access Patterns Dashboard

**Feature**: 014-memory-access-dashboard
**Date**: 2026-01-31
**Status**: Complete

## Research Tasks

### 1. Metrics Availability Verification

**Question**: Are all required metrics from the spec available in the codebase?

**Finding**: ✅ All metrics exist in `docker/patches/metrics_exporter.py`

| Metric | Line | Type | Confirmed |
|--------|------|------|-----------|
| `knowledge_access_by_importance_total` | 867 | Counter | ✅ |
| `knowledge_access_by_state_total` | 872 | Counter | ✅ |
| `knowledge_memory_access_total` | 851 | Counter | ✅ |
| `knowledge_days_since_last_access` | 1048 | Histogram | ✅ |
| `knowledge_reactivations_total` | 833 | Counter | ✅ |

**Decision**: No new metrics required. Implementation can proceed with existing instrumentation.

### 2. Existing Dashboard Pattern

**Question**: What pattern should the new dashboard follow?

**Finding**: Two existing dashboards provide patterns:
- `config/monitoring/grafana/dashboards/memory-decay-dashboard.json` - Comprehensive, 18 panels
- `config/monitoring/grafana/dashboards/graph-health-dashboard.json` - Health-focused

**Decision**: Follow `memory-decay-dashboard.json` pattern:
- Same JSON structure
- Same panel types (stat, piechart, timeseries, heatmap)
- Same refresh interval (30s)
- Same Prometheus datasource configuration

**Rationale**: Consistency with existing dashboards reduces maintenance burden and provides familiar UX.

### 3. Time-Over-Time Query Pattern

**Question**: How should cumulative counter queries handle service restarts (per Constitution IX)?

**Finding**: Constitution IX requires `max_over_time()` wrapper for cumulative counters:

```promql
# Standard counter - shows gap on restart
knowledge_access_by_importance_total

# Restart-resilient - shows last value during gap
max_over_time(knowledge_access_by_importance_total[1h])
```

**Decision**: All cumulative counter panels will use `max_over_time()` with 1h window.

**Rationale**: Prevents visual "cliffs" in dashboard when MCP server restarts.

### 4. Histogram Visualization

**Question**: How to visualize `knowledge_days_since_last_access` histogram effectively?

**Finding**: Existing dashboards use heatmap visualization for histograms:
- `knowledge_decay_score_bucket` → heatmap in memory-decay-dashboard
- Uses `sum(rate(...[5m])) by (le)` pattern

**Decision**: Use heatmap with Oranges color scheme for age distribution.

**Alternatives Considered**:
- Bar chart: Less effective for bucket visualization
- Stat panels per bucket: Too many panels, cluttered

### 5. Correlation Visualization

**Question**: How to show access patterns vs decay score correlation (US-6)?

**Finding**: No direct precedent in existing dashboards. Options:

| Option | Pros | Cons |
|--------|------|------|
| Dual-axis time series | Shows trend correlation | Scales may differ |
| Side-by-side time series | Clear comparison | Takes more space |
| Scatter plot | Shows direct correlation | Requires join, complex |

**Decision**: Dual-axis time series with access rate on left axis, decay score on right axis.

**Rationale**: Enables visual correlation without complex query joins. Users can compare trends over same time period.

## Unresolved Items

None. All research questions answered.

## References

- `docker/patches/metrics_exporter.py` - Metrics definitions
- `config/monitoring/grafana/dashboards/memory-decay-dashboard.json` - Dashboard pattern
- `.specify/memory/constitution.md` - Principle IX requirements
