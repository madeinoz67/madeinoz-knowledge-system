# Implementation Plan: Memory Access Metrics

**Branch**: `015-memory-access-metrics` | **Date**: 2026-01-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/015-memory-access-metrics/spec.md`

## Summary

Add memory access pattern metrics to the knowledge system to enable the Memory Access Patterns dashboard (feature #37/PR #42). The metrics are already defined in `docker/patches/metrics_exporter.py` but are not being incremented during search operations. This feature requires hooking into search result processing to extract memory attributes (importance, state, days_since_access) and recording them via `record_access_pattern()`.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: OpenTelemetry Prometheus exporter, Graphiti MCP server
**Storage**: Neo4j / FalkorDB (existing graph database)
**Testing**: pytest with mock metrics (Python tests)
**Target Platform**: Linux containers (Podman/Docker)
**Project Type**: Python patch in `docker/patches/`
**Performance Goals**: <1ms overhead per search result
**Constraints**: Must not break existing search operations; must handle missing attribute values gracefully
**Scale/Scope**: ~4 function modifications, 1 test file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Container-First Architecture | ✅ PASS | Modifies existing containerized Python code |
| II. Graph-Centric Design | ✅ PASS | Reads graph node attributes during search |
| III. Zero-Friction Knowledge Capture | N/A | Not a capture feature |
| IV. Query Resilience | ✅ PASS | No query modifications needed |
| V. Graceful Degradation | ✅ PASS | Metrics failures don't break search |
| VI. Codanna-First Development | ✅ PASS | Used Codanna to locate code |
| VII. Language Separation | ✅ PASS | Python code in `docker/patches/` |
| VIII. Dual-Audience Documentation | ✅ PASS | Metrics will be documented |
| **IX. Observability & Metrics** | ✅ PASS | **Primary purpose - adds dashboard metrics** |

**Gate Status**: PASSED - All applicable principles satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/015-memory-access-metrics/
├── plan.md              # This file
├── research.md          # Phase 0: metrics gap analysis
├── data-model.md        # Phase 1: metric definitions
├── quickstart.md        # Phase 1: usage guide
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```text
docker/patches/
├── graphiti_mcp_server.py    # MODIFIED: Call record_access_pattern() during search
├── metrics_exporter.py        # MODIFIED: Fix importance label mapping
└── tests/
    └── test_access_metrics.py # NEW: Tests for access pattern recording
```

**Structure Decision**: Single Python module modification pattern. The metrics infrastructure already exists; we're connecting it to the search flow.

## Complexity Tracking

> No violations - straightforward metrics instrumentation.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Implementation Approach

### Current State (from Research)

The metrics ARE defined in `metrics_exporter.py`:
- `knowledge_access_by_importance_total` - Counter with `level` label
- `knowledge_access_by_state_total` - Counter with `state` label
- `knowledge_days_since_last_access` - Histogram with buckets [1, 7, 30, 90, 180, 365, 730, 1095]
- `knowledge_reactivations_total` - Counter with `from_state` label

The `record_access_pattern()` function EXISTS and works, but:
1. **Only called during lifecycle transitions** (in `lifecycle_manager.py`)
2. **NOT called during search operations** (where most accesses happen)
3. **Label mismatch**: Dashboard expects CRITICAL/HIGH/MEDIUM/LOW; code uses CORE/HIGH/MODERATE/LOW/TRIVIAL

### Required Changes

1. **graphiti_mcp_server.py** (3 locations):
   - `search_memory_nodes()` - Extract node attributes, call `record_access_pattern()`
   - `search_memory_facts()` - Extract fact node attributes, call `record_access_pattern()`
   - Pattern: For each result, get `importance`, `lifecycle_state`, `daysSinceAccess`

2. **metrics_exporter.py**:
   - Update importance label mapping to match dashboard: {5: "CRITICAL", 4: "HIGH", 3: "MEDIUM", 2: "LOW", 1: "LOW"}

3. **tests/test_access_metrics.py** (NEW):
   - Mock search results and verify `record_access_pattern()` is called
   - Verify correct labels are used
   - Verify histogram recording

### Metrics to be Instrumented

| Metric | Type | Labels | When to Record |
|--------|------|--------|----------------|
| `knowledge_access_by_importance_total` | Counter | `level` (CRITICAL, HIGH, MEDIUM, LOW) | On each search result |
| `knowledge_access_by_state_total` | Counter | `state` (ACTIVE, STABLE, DORMANT, ARCHIVED) | On each search result |
| `knowledge_days_since_last_access_bucket` | Histogram | - | On each search result |
| `knowledge_reactivations_total` | Counter | `from_state` (DORMANT, ARCHIVED) | On lifecycle transition (already works) |

## Next Steps

After `/speckit.plan` completes:
1. Run `/speckit.tasks` to generate implementation tasks
2. Implement search result instrumentation
3. Fix importance label mapping
4. Add tests
5. Verify dashboard populates with data
