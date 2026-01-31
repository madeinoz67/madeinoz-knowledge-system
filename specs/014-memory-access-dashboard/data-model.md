# Data Model: Memory Access Patterns Dashboard

**Feature**: 014-memory-access-dashboard
**Date**: 2026-01-31

## Overview

This feature creates a Grafana dashboard (JSON configuration). There are no database entities or API contracts - only dashboard panel definitions consuming existing Prometheus metrics.

## Dashboard Structure

### Layout Grid

Grafana uses a 24-column grid system. Height is in grid units (1 unit ≈ 30px).

```
Row 0 (y=0, h=4):  Header Stats
├── [w=6] Total Access Count
├── [w=6] Access Rate (/s)
├── [w=6] Reactivations (Dormant)
└── [w=6] Reactivations (Archived)

Row 1 (y=4, h=8):  Distribution Charts
├── [w=12] Access by Importance (Pie)
└── [w=12] Access by State (Pie)

Row 2 (y=12, h=8): Time Series
├── [w=12] Access Rate Over Time
└── [w=12] Age Distribution Heatmap

Row 3 (y=20, h=8): Correlation
└── [w=24] Access vs Decay Correlation
```

## Panel Specifications

### Panel 1: Total Access Count

| Property | Value |
|----------|-------|
| Type | stat |
| Position | x=0, y=0, w=6, h=4 |
| Query | `max_over_time(sum(knowledge_memory_access_total)[1h])` |
| Unit | short |
| Color Mode | value |

### Panel 2: Access Rate

| Property | Value |
|----------|-------|
| Type | stat |
| Position | x=6, y=0, w=6, h=4 |
| Query | `sum(rate(knowledge_memory_access_total[5m]))` |
| Unit | ops |
| Color Mode | value |

### Panel 3: Reactivations (Dormant)

| Property | Value |
|----------|-------|
| Type | stat |
| Position | x=12, y=0, w=6, h=4 |
| Query | `increase(knowledge_reactivations_total{from_state="DORMANT"}[$__range])` |
| Unit | short |
| Thresholds | green=0, yellow=5, red=20 |

### Panel 4: Reactivations (Archived)

| Property | Value |
|----------|-------|
| Type | stat |
| Position | x=18, y=0, w=6, h=4 |
| Query | `increase(knowledge_reactivations_total{from_state="ARCHIVED"}[$__range])` |
| Unit | short |
| Thresholds | green=0, yellow=3, red=10 |

### Panel 5: Access by Importance

| Property | Value |
|----------|-------|
| Type | piechart |
| Position | x=0, y=4, w=12, h=8 |
| Query | `max_over_time(knowledge_access_by_importance_total[1h])` |
| Legend Format | `{{level}}` |
| Legend | table, right, with values and percent |

### Panel 6: Access by State

| Property | Value |
|----------|-------|
| Type | piechart |
| Position | x=12, y=4, w=12, h=8 |
| Query | `max_over_time(knowledge_access_by_state_total[1h])` |
| Legend Format | `{{state}}` |
| Legend | table, right, with values and percent |

### Panel 7: Access Rate Over Time

| Property | Value |
|----------|-------|
| Type | timeseries |
| Position | x=0, y=12, w=12, h=8 |
| Query | `rate(knowledge_memory_access_total[5m])` |
| Legend Format | Access Rate |
| Draw Style | line, smooth, fill opacity 20 |

### Panel 8: Age Distribution Heatmap

| Property | Value |
|----------|-------|
| Type | heatmap |
| Position | x=12, y=12, w=12, h=8 |
| Query | `sum(rate(knowledge_days_since_last_access_bucket[5m])) by (le)` |
| Format | heatmap |
| Color Scheme | Oranges |

### Panel 9: Access vs Decay Correlation

| Property | Value |
|----------|-------|
| Type | timeseries |
| Position | x=0, y=20, w=24, h=8 |
| Query A | `rate(knowledge_memory_access_total[5m])` (left axis) |
| Query B | `knowledge_decay_score_avg` (right axis) |
| Legend | table, bottom, with last/mean |

## Dashboard Metadata

| Property | Value |
|----------|-------|
| uid | memory-access-dashboard |
| title | Memory Access Patterns |
| tags | ["knowledge", "access", "patterns"] |
| refresh | 30s |
| time range | 24h (with picker) |
| editable | true |
| schemaVersion | 36 |

## Validation Rules

1. All panel IDs must be unique (1-9)
2. Grid positions must not overlap
3. Total row width must not exceed 24
4. All queries must reference existing metrics
5. All counter queries must use `max_over_time()` or `rate()`/`increase()` for Constitution IX compliance
