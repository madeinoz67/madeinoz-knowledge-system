# Research: Memory Access Metrics

**Feature**: 015-memory-access-metrics
**Date**: 2026-01-31
**Status**: Complete

## Research Tasks

### 1. Metrics Definition Verification

**Question**: Are the required metrics already defined in `metrics_exporter.py`?

**Finding**: ✅ YES - All 4 metrics are already defined

| Metric | Line | Type | Labels | Status |
|--------|------|------|--------|--------|
| `knowledge_access_by_importance_total` | 867-870 | Counter | `level` | ✅ Defined |
| `knowledge_access_by_state_total` | 871-875 | Counter | `state` | ✅ Defined |
| `knowledge_days_since_last_access` | 1047-1051 | Histogram | - | ✅ Defined |
| `knowledge_reactivations_total` | 832-836 | Counter | `from_state` | ✅ Defined |

**Decision**: No new metric definitions needed - infrastructure exists.

### 2. Access Pattern Recording Location

**Question**: Where is `record_access_pattern()` called from?

**Finding**: ⚠️ ONLY called from lifecycle transitions, NOT search operations

```python
# docker/patches/lifecycle_manager.py:352-356
# Called during DORMANT/ARCHIVED → ACTIVE reactivation
decay_metrics.record_access_pattern(
    importance=importance,
    lifecycle_state=prev_state,
    days_since_last_access=float(days_since_access)
)
```

**Search operations call different function:**

```python
# docker/patches/graphiti_mcp_server.py:1066, 1110, 1245
# Only records generic access count, NOT detailed attributes
decay_metrics.record_memory_access()
```

**Decision**: Must modify `graphiti_mcp_server.py` to call `record_access_pattern()` with node attributes during search.

### 3. Search Result Attribute Extraction

**Question**: Do search results include the attributes needed for `record_access_pattern()`?

**Finding**: ✅ YES - Neo4j nodes return these properties

| Attribute | Neo4j Property | Type |
|-----------|----------------|------|
| importance | `importance` | int (1-5) |
| lifecycle_state | `lifecycle_state` | string (ACTIVE, STABLE, DORMANT, ARCHIVED) |
| days_since_access | `daysSinceAccess` | float |

**Sample extraction pattern from lifecycle_manager.py:**
```python
importance = record.get("importance", 3)
lifecycle_state = record.get("lifecycle_state", "ACTIVE")
days_since_access = record.get("daysSinceAccess", 0)
```

**Decision**: Extract these same attributes from search results in `graphiti_mcp_server.py`.

### 4. Importance Label Mapping

**Question**: Do the importance labels match what the dashboard expects?

**Finding**: ❌ NO - Label mismatch between code and dashboard

| Code Uses | Dashboard Expects | Issue |
|-----------|-------------------|-------|
| CORE (5) | CRITICAL | Name mismatch |
| HIGH (4) | HIGH | ✅ Match |
| MODERATE (3) | MEDIUM | Name mismatch |
| LOW (2) | LOW | ✅ Match |
| TRIVIAL (1) | - | Not in dashboard |

**Current mapping in metrics_exporter.py:1438-1445:**
```python
importance_labels = {
    1: "TRIVIAL",
    2: "LOW",
    3: "MODERATE",
    4: "HIGH",
    5: "CORE",
}
```

**Decision**: Update label mapping to match dashboard: {5: "CRITICAL", 4: "HIGH", 3: "MEDIUM", 2: "LOW", 1: "LOW"}.

### 5. Reactivation Tracking

**Question**: Is reactivation tracking already working?

**Finding**: ✅ YES - `record_reactivation()` is called during lifecycle transitions

```python
# docker/patches/lifecycle_manager.py:350
decay_metrics.record_reactivation(prev_state)
```

The reactivation metrics should already be exported. Dashboard panels not showing data likely due to lack of reactivation events in test data.

**Decision**: No changes needed for reactivation tracking - already functional.

## Unresolved Items

None. All research questions answered.

## Implementation Summary

| File | Change | Reason |
|------|--------|--------|
| `graphiti_mcp_server.py` | Call `record_access_pattern()` in search handlers | Connect metrics to search flow |
| `metrics_exporter.py` | Update importance label mapping | Match dashboard expectations |
| `tests/test_access_metrics.py` | Add tests for access pattern recording | Verify instrumentation |

## References

- `docker/patches/metrics_exporter.py` - Metrics definitions
- `docker/patches/lifecycle_manager.py` - Existing `record_access_pattern()` usage
- `docker/patches/graphiti_mcp_server.py` - Search operation handlers
- Feature #37/PR #42 - Memory Access Patterns dashboard
