# Data Model: Fix Decay Calculation Bugs

**Feature**: 012-fix-decay-bugs
**Date**: 2026-01-31

## Overview

This feature is a bug fix to existing code - no new data models are introduced. The changes ensure that the existing decay calculation uses the correct configuration values and reports accurate metrics.

## Existing Data Model (No Changes)

### Entity Node Attributes

| Attribute | Type | Description | Affected By |
|-----------|------|-------------|-------------|
| `decay_score` | Float | Calculated decay (0.0-1.0) | Bug #1: Was using 30-day half-life instead of 180-day |
| `importance` | Integer (1-5) | Memory importance score | Used in decay calculation |
| `stability` | Integer (1-5) | Memory stability score | Used in decay calculation |
| `lifecycle_state` | String | ACTIVE, DORMANT, ARCHIVED, etc. | Unchanged |
| `last_accessed_at` | DateTime | Last access timestamp | Bug #3: NULL handling improved |
| `created_at` | DateTime | Entity creation timestamp | Bug #3: Fallback when last_accessed_at is NULL |
| `access_count` | Integer | Number of accesses | Unchanged |

### Decay Configuration (decay-config.yaml)

```yaml
decay:
  base_half_life_days: 180    # Was not being loaded (Bug #1)

  thresholds:
    dormant:
      days: 30
      decay_score: 0.3
    archived:
      days: 90
      decay_score: 0.5
    expired:
      days: 180
      decay_score: 0.7
      max_importance: 2
```

## Decay Calculation Formula

```
half_life = base_half_life_days × (stability / 3.0)
lambda = ln(2) / half_life
adjusted_rate = lambda × (6 - importance) / 5.0
decay_score = 1 - exp(-adjusted_rate × days_since_access)
```

### Expected Values (With 180-day Config)

| Days | Importance | Stability | Expected Decay |
|------|------------|-----------|----------------|
| 2 | 3 | 3 | 0.46% |
| 30 | 3 | 3 | 6.9% |
| 90 | 3 | 3 | 19.5% |
| 180 | 3 | 3 | 36.0% |

### Actual Values (With 30-day Default Bug)

| Days | Importance | Stability | Actual Decay (Bug) |
|------|------------|-----------|-------------------|
| 2 | 3 | 3 | 2.7% |
| 30 | 3 | 3 | 31.1% |
| 90 | 3 | 3 | 67.3% |
| 180 | 3 | 3 | 89.3% |

## Prometheus Metrics (Bug #2)

| Metric | Type | Description | Bug |
|--------|------|-------------|-----|
| `knowledge_decay_score_avg` | Gauge | Average decay score | Was stale after maintenance |
| `knowledge_memories_by_state` | Gauge | Count per lifecycle state | Was stale after maintenance |
| `knowledge_importance_avg` | Gauge | Average importance | Was stale after maintenance |
| `knowledge_stability_avg` | Gauge | Average stability | Was stale after maintenance |

## NULL Timestamp Handling (Bug #3)

### Before (Unsafe)

```cypher
datetime(coalesce(n.`attributes.last_accessed_at`, toString(n.created_at)))
-- If both NULL: datetime(NULL) = undefined behavior
```

### After (Safe)

```cypher
CASE
  WHEN n.`attributes.last_accessed_at` IS NOT NULL
    THEN duration.between(datetime(n.`attributes.last_accessed_at`), datetime()).days
  WHEN n.created_at IS NOT NULL
    THEN duration.between(n.created_at, datetime()).days
  ELSE 0
END AS daysSinceAccess
```

## No Schema Changes Required

This feature does not introduce any new node types, relationships, or attributes. It fixes bugs where existing attributes were being calculated or reported incorrectly.

## Indexes

Existing indexes are sufficient:
- `lifecycle_state` index (created in feature 009)
- `uuid` unique constraint (Graphiti default)
- Vector embeddings (Graphiti default)
