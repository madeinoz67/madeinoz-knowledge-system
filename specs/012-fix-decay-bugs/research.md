# Research: Fix Decay Calculation Bugs

**Feature**: 012-fix-decay-bugs
**Date**: 2026-01-31
**Status**: Complete

## Research Summary

Research completed via Red Team parallel analysis of decay calculation code. Three bugs identified with root cause analysis.

## Bug #1: Config Path Mismatch

### Decision
Add `cp /tmp/decay-config.yaml /app/mcp/config/decay-config.yaml || true` to `entrypoint.sh`

### Rationale
- Dockerfile copies `config/decay-config.yaml` to `/tmp/decay-config.yaml` (line 52)
- Python code expects config at `/app/mcp/config/decay-config.yaml` (decay_config.py line 22)
- Entrypoint.sh copies database configs but NOT decay config
- Result: Config not found, code default of 30 days used instead of 180 days

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Change Dockerfile COPY destination | Would require changing code expectations |
| Set DECAY_CONFIG_PATH env var | Adds configuration complexity |
| Change Python default path | Would need to handle both paths |
| **Copy in entrypoint (CHOSEN)** | Simple, follows existing pattern for database configs |

### Evidence

```python
# decay_config.py line 22
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "decay-config.yaml"
# Resolves to: /app/mcp/config/decay-config.yaml

# decay_types.py line 212
base_half_life_days: float = Field(default=30.0, ...)
# This is the fallback when config not found
```

```dockerfile
# Dockerfile line 52
COPY config/decay-config.yaml /tmp/decay-config.yaml
# Copied to wrong location
```

## Bug #2: Prometheus Metrics Not Refreshed

### Decision
Call `get_health_metrics()` at end of `run_maintenance()` with try/except wrapper

### Rationale
- `run_maintenance()` updates decay scores in database
- `_record_metrics()` only records counters (maintenance runs, transitions)
- `_update_gauge_metrics()` only called from `get_health_metrics()`
- Result: Prometheus gauges show stale values until explicit health check

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Add `_update_gauge_metrics()` call to `_record_metrics()` | Requires passing HealthMetrics object |
| Create dedicated refresh method | Redundant with existing `get_health_metrics()` |
| **Call get_health_metrics() (CHOSEN)** | Reuses existing code, already updates gauges |

### Evidence

```python
# maintenance_service.py line 372
self._record_metrics(result)  # Only records counters

# maintenance_service.py line 528-553
def _record_metrics(self, result):
    # Records: maintenance_run, lifecycle_transitions, purged
    # Does NOT call _update_gauge_metrics()

# maintenance_service.py line 478
self._update_gauge_metrics(metrics)  # Only called from get_health_metrics()
```

### Implementation Pattern

```python
# After line 372 in run_maintenance():
# Refresh gauge metrics with current averages
try:
    await self.get_health_metrics()  # Internally calls _update_gauge_metrics
    logger.debug("Gauge metrics refreshed after maintenance")
except Exception as e:
    logger.warning(f"Failed to refresh gauge metrics: {e}")
    # Don't fail maintenance - graceful degradation per FR-007
```

## Bug #3: Timestamp NULL Handling

### Decision
Replace Cypher coalesce with explicit CASE statement handling all NULL scenarios

### Rationale
- Current query: `datetime(coalesce(n.last_accessed_at, toString(n.created_at)))`
- If both are NULL: `datetime(NULL)` behavior undefined
- Diagnostic data shows timestamps ARE parsing correctly, so this is defensive hardening

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Keep coalesce, add NULL check in WHERE | Skips nodes instead of calculating |
| Default to epoch timestamp | Would give massive (wrong) decay scores |
| **CASE with 0 default (CHOSEN)** | Handles all cases, 0 days = no decay |

### Evidence

```cypher
-- Current (memory_decay.py line 357)
datetime(coalesce(n.`attributes.last_accessed_at`, toString(n.created_at)))

-- Proposed
CASE
  WHEN n.`attributes.last_accessed_at` IS NOT NULL
    THEN duration.between(datetime(n.`attributes.last_accessed_at`), datetime()).days
  WHEN n.created_at IS NOT NULL
    THEN duration.between(n.created_at, datetime()).days
  ELSE 0
END AS daysSinceAccess
```

### Diagnostic Data

From `records.json` analysis:
- 2-day-old entities: `calculated_days: 2`, `decay_score: 0.027` (matches 30-day half-life)
- 0-day-old entities: `calculated_days: 0`, `decay_score: 0.0`
- Timestamps ARE parsing correctly for existing data

## Mathematical Verification

### Expected Decay Scores

| Half-Life | Days | Importance | Stability | Expected Decay |
|-----------|------|------------|-----------|----------------|
| 180 (config) | 2 | 3 | 3 | **0.46%** |
| 30 (default) | 2 | 3 | 3 | **2.7%** |

### Formula Verification

```
half_life = base_half_life × (stability / 3.0)
lambda = ln(2) / half_life
adjusted_rate = lambda × (6 - importance) / 5.0
decay = 1 - exp(-adjusted_rate × days)

For base=30, stability=3, importance=3, days=2:
half_life = 30 × 1.0 = 30
lambda = 0.693 / 30 = 0.0231
adjusted_rate = 0.0231 × 0.6 = 0.0139
decay = 1 - exp(-0.0139 × 2) = 1 - 0.973 = 0.027 (2.7%) ✓
```

## Files Analyzed

| File | Purpose | Key Lines |
|------|---------|-----------|
| `docker/Dockerfile` | Container build | 52 (COPY decay config) |
| `src/skills/server/entrypoint.sh` | Container startup | 24-30 (database config copy) |
| `docker/patches/decay_config.py` | Config loader | 22 (expected path) |
| `docker/patches/decay_types.py` | Type definitions | 212 (30-day default) |
| `docker/patches/memory_decay.py` | Decay calculation | 357 (timestamp query) |
| `docker/patches/maintenance_service.py` | Maintenance service | 372, 478, 528 (metrics) |
| `docker/patches/metrics_exporter.py` | Prometheus exporter | 850, 1096 (gauges) |
| `config/decay-config.yaml` | Config file | 9 (180-day half-life) |

## Open Questions

None - all research questions resolved.
