# Implementation Plan: Memory Access Patterns Dashboard

**Branch**: `014-memory-access-dashboard` | **Date**: 2026-01-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/014-memory-access-dashboard/spec.md`

## Summary

Create a Grafana dashboard to visualize memory access patterns across importance levels, lifecycle states, and time periods. The dashboard enables validation of decay scoring effectiveness by correlating access frequency with decay scores. Implementation follows the existing memory-decay-dashboard.json pattern as a single JSON configuration file.

## Technical Context

**Language/Version**: JSON (Grafana dashboard configuration)
**Primary Dependencies**: Grafana (provisioned), Prometheus (data source), existing metrics from PR #34
**Storage**: N/A (dashboard configuration only)
**Testing**: Manual dashboard verification in Grafana UI
**Target Platform**: Grafana 10.x (existing infrastructure)
**Project Type**: Single file (JSON dashboard configuration)
**Performance Goals**: Panel load time < 5 seconds per SC-004
**Constraints**: Must use existing metrics only, no new instrumentation required
**Scale/Scope**: 8-10 panels covering 6 user stories

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Container-First Architecture | ✅ PASS | Uses existing Grafana container |
| II. Graph-Centric Design | ✅ PASS | Visualizes graph access patterns |
| III. Zero-Friction Knowledge Capture | N/A | Not a capture feature |
| IV. Query Resilience | ✅ PASS | Prometheus handles query escaping |
| V. Graceful Degradation | ✅ PASS | Grafana shows "No data" for missing metrics |
| VI. Codanna-First Development | ✅ PASS | Used Codanna to find existing dashboard pattern |
| VII. Language Separation | ✅ PASS | JSON config, not code |
| VIII. Dual-Audience Documentation | ✅ PASS | Dashboard IS visual documentation for metrics |
| **IX. Observability & Metrics** | ✅ PASS | **Primary principle - dashboard covers new metrics** |

**Gate Status**: PASSED - All applicable principles satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/014-memory-access-dashboard/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0: metrics verification
├── data-model.md        # Phase 1: panel structure
├── quickstart.md        # Phase 1: usage guide
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```text
config/monitoring/grafana/dashboards/
└── memory-access-dashboard.json    # NEW: Dashboard configuration
```

**Structure Decision**: Single JSON file following existing dashboard pattern (`memory-decay-dashboard.json`). No code changes required - dashboard consumes existing metrics from `docker/patches/metrics_exporter.py`.

## Complexity Tracking

> No violations - straightforward dashboard configuration following established patterns.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Implementation Approach

### Metrics Available (Verified from metrics_exporter.py)

| Metric | Type | Labels | Use |
|--------|------|--------|-----|
| `knowledge_access_by_importance_total` | Counter | `level` (CRITICAL, HIGH, MEDIUM, LOW) | FR-001: Importance distribution |
| `knowledge_access_by_state_total` | Counter | `state` (ACTIVE, STABLE, DORMANT, ARCHIVED) | FR-002: State distribution |
| `knowledge_memory_access_total` | Counter | - | FR-003: Access rate over time |
| `knowledge_days_since_last_access` | Histogram | buckets [1, 7, 30, 90, 180, 365, 730, 1095] | FR-004: Age distribution |
| `knowledge_reactivations_total` | Counter | `from_state` (DORMANT, ARCHIVED) | FR-005, FR-006: Reactivations |

### Panel Design

| Panel | Type | Metric | Position | User Story |
|-------|------|--------|----------|------------|
| Access by Importance | Pie Chart | `knowledge_access_by_importance_total` | Row 1 | US-1 |
| Access by State | Pie Chart | `knowledge_access_by_state_total` | Row 1 | US-2 |
| Access Rate | Time Series | `rate(knowledge_memory_access_total[5m])` | Row 2 | US-3 |
| Age Distribution | Heatmap | `knowledge_days_since_last_access` | Row 2 | US-4 |
| Reactivations (Dormant) | Stat | `increase(knowledge_reactivations_total{from_state="DORMANT"}[1h])` | Row 3 | US-5 |
| Reactivations (Archived) | Stat | `increase(knowledge_reactivations_total{from_state="ARCHIVED"}[1h])` | Row 3 | US-6 |
| Total Access Count | Stat | `sum(knowledge_memory_access_total)` | Row 3 | Overview |
| Access vs Decay Correlation | Time Series | Multi-query comparison | Row 4 | US-6 |

### Query Patterns (Constitution IX Compliance)

Per Principle IX, cumulative counters must use time-over-time functions:

```promql
# Access counts - use max_over_time for restart resilience
max_over_time(knowledge_access_by_importance_total[1h])

# Rates - wrap with max_over_time
max_over_time(rate(knowledge_memory_access_total[5m])[1h:])

# Reactivations - use increase for period totals
increase(knowledge_reactivations_total{from_state="DORMANT"}[$__range])
```

## Next Steps

After `/speckit.plan` completes:
1. Run `/speckit.tasks` to generate implementation tasks
2. Implement dashboard JSON following panel design
3. Test dashboard in Grafana
4. Update `docs/reference/observability.md` with new dashboard reference
