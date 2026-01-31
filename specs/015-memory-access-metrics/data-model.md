# Data Model: Memory Access Metrics

**Feature**: 015-memory-access-metrics
**Date**: 2026-01-31

## Overview

This feature adds instrumentation to existing code - no new data entities are created. The data model describes the metrics being recorded and their attributes.

## Metric Definitions

### knowledge_access_by_importance_total

**Type**: Counter
**Description**: Total memory accesses by importance level
**Labels**: `level` (CRITICAL, HIGH, MEDIUM, LOW)

| Value | Label | Description |
|-------|-------|-------------|
| 5 | CRITICAL | Core/foundational memories |
| 4 | HIGH | Important memories |
| 3 | MEDIUM | Standard importance |
| 2 | LOW | Lower priority |
| 1 | LOW | Trivial (mapped to LOW) |

**PromQL Example**:
```promql
sum(rate(knowledge_access_by_importance_total[5m])) by (level)
```

### knowledge_access_by_state_total

**Type**: Counter
**Description**: Total memory accesses by lifecycle state at access time
**Labels**: `state` (ACTIVE, STABLE, DORMANT, ARCHIVED)

| State | Description |
|-------|-------------|
| ACTIVE | Recently accessed (last 30 days) |
| STABLE | Accessed 30-90 days ago |
| DORMANT | Not accessed 90+ days |
| ARCHIVED | Not accessed 180+ days |
| PERMANENT | High importance + stability (never decays) |

**PromQL Example**:
```promql
max_over_time(knowledge_access_by_state_total[1h])
```

### knowledge_days_since_last_access

**Type**: Histogram
**Description**: Days since memory was last accessed
**Unit**: days
**Buckets**: [1, 7, 30, 90, 180, 365, 730, 1095]

| Bucket | Description |
|--------|-------------|
| 1 | 1 day |
| 7 | 1 week |
| 30 | 1 month |
| 90 | 3 months |
| 180 | 6 months (half-life threshold) |
| 365 | 1 year |
| 730 | 2 years |
| 1095 | 3+ years |

**PromQL Example**:
```promql
sum(rate(knowledge_days_since_last_access_bucket[5m])) by (le)
```

### knowledge_reactivations_total

**Type**: Counter
**Description**: Memories reactivated from DORMANT/ARCHIVED to ACTIVE
**Labels**: `from_state` (DORMANT, ARCHIVED)

| From State | Description |
|------------|-------------|
| DORMANT | Memory was in DORMANT state before access |
| ARCHIVED | Memory was in ARCHIVED state before access |

**PromQL Example**:
```promql
increase(knowledge_reactivations_total{from_state="DORMANT"}[$__range])
```

## Recording Flow

```
┌─────────────────┐
│ Search Operation │
│ (nodes/facts)   │
└────────┬─────────┘
         │
         ▼
┌─────────────────────────────┐
│ Extract Node Attributes:    │
│ - importance (int 1-5)      │
│ - lifecycle_state (string)  │
│ - daysSinceAccess (float)   │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ record_access_pattern(              │
│   importance,                       │
│   lifecycle_state,                  │
│   days_since_last_access            │
│ )                                   │
└────────┬────────────────────────────┘
         │
         ├──► access_by_importance.add(1, {level})
         ├──► access_by_state.add(1, {state})
         └──► days_since_last_access.record(days)
```

## Attribute Sources

| Attribute | Neo4j Property | Type | Default |
|-----------|----------------|------|---------|
| importance | `importance` | int | 3 |
| lifecycle_state | `lifecycle_state` | string | "ACTIVE" |
| days_since_access | `daysSinceAccess` | float | 0.0 |

## Validation Rules

1. **Missing attributes**: Use defaults (importance=3, state="ACTIVE", days=0)
2. **Unknown importance values**: Map to "LOW" label
3. **Unknown lifecycle states**: Use actual string value (pass through)
4. **Negative days**: Treat as 0 (never accessed)

## Dependencies

- Neo4j node properties must include `importance`, `lifecycle_state`, `daysSinceAccess`
- These properties are set by the memory decay system (feature #009)
