# Implementation Plan: Fix Decay Calculation Bugs

**Branch**: `012-fix-decay-bugs` | **Date**: 2026-01-31 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/012-fix-decay-bugs/spec.md`
**Related Issue**: [GitHub Issue #26](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/26)

## Summary

Fix three bugs in the memory decay scoring system:
1. **Config Path Mismatch (P1)**: Entrypoint script doesn't copy decay config to expected location, causing 30-day default instead of 180-day configured half-life
2. **Stale Prometheus Metrics (P2)**: Gauge metrics not refreshed after maintenance runs, showing stale values
3. **Timestamp NULL Handling (P3)**: Decay calculation may fail silently with NULL timestamps

## Technical Context

**Language/Version**: Python 3.11 (MCP server), Shell (entrypoint)
**Primary Dependencies**: FastMCP, graphiti-core, neo4j driver, pydantic, prometheus-client
**Storage**: Neo4j graph database (Entity nodes with decay attributes)
**Testing**: pytest (Python), manual integration testing via container restart
**Target Platform**: Linux containers (Docker/Podman)
**Project Type**: Container-based MCP server patches
**Performance Goals**: Gauge refresh must add <1s to maintenance cycle
**Constraints**: Must not fail maintenance if gauge refresh errors; graceful degradation required
**Scale/Scope**: Affects all Entity nodes in knowledge graph (~100-10000 nodes typical)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Container-First Architecture | ✅ PASS | Changes are in container entrypoint and Python patches |
| II. Graph-Centric Design | ✅ PASS | No changes to graph structure, only decay calculation |
| III. Zero-Friction Knowledge Capture | ✅ N/A | Not applicable to this bug fix |
| IV. Query Resilience | ✅ PASS | Improving NULL handling makes queries more resilient |
| V. Graceful Degradation | ✅ PASS | FR-007 requires gauge refresh errors not to fail maintenance |
| VI. Codanna-First Development | ✅ PASS | Used codanna for initial bug analysis |
| VII. Language Separation | ✅ PASS | Python changes in docker/patches/, shell in src/skills/server/ |
| VIII. Dual-Audience Documentation | ✅ N/A | Bug fix, no documentation changes needed |

**Gate Result**: PASS - All applicable principles satisfied

## Project Structure

### Documentation (this feature)

```text
specs/012-fix-decay-bugs/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (existing model, no changes)
├── quickstart.md        # Phase 1 output
├── checklists/          # Quality checklists
│   └── requirements.md  # Spec quality checklist (complete)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
# Files to modify:
src/skills/server/
└── entrypoint.sh        # Fix #1: Add decay config copy

docker/patches/
├── maintenance_service.py   # Fix #2: Add gauge refresh after maintenance
└── memory_decay.py          # Fix #3: Safe NULL timestamp handling in Cypher query

# Files for reference (no changes):
config/
└── decay-config.yaml    # Contains correct 180-day half-life

docker/
└── Dockerfile           # Already copies config to /tmp/

docker/patches/
├── decay_config.py      # Config loader (no changes needed)
├── decay_types.py       # Type definitions (contains 30-day default)
└── metrics_exporter.py  # Metrics exporter (no changes needed)
```

**Structure Decision**: Existing repository structure maintained. Changes affect 3 files across shell and Python layers per Constitution Principle VII (Language Separation).

## Complexity Tracking

> No violations to justify - all changes follow Constitution principles.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |

## Implementation Phases

### Phase 0: Research (Complete)

Research was completed during red team analysis. Key findings documented in [research.md](research.md).

### Phase 1: Design

**Fix #1 - Config Path (entrypoint.sh)**
- Location: `src/skills/server/entrypoint.sh` after line 30
- Add: `cp /tmp/decay-config.yaml /app/mcp/config/decay-config.yaml || true`
- Graceful: Use `|| true` to not fail if source missing

**Fix #2 - Gauge Refresh (maintenance_service.py)**
- Location: `docker/patches/maintenance_service.py` in `run_maintenance()` after line 372
- Add: Call to `get_health_metrics()` which internally calls `_update_gauge_metrics()`
- Wrap in try/except for graceful degradation per FR-007

**Fix #3 - NULL Handling (memory_decay.py)**
- Location: `docker/patches/memory_decay.py` line 357 (`BATCH_DECAY_UPDATE_QUERY`)
- Replace: Cypher coalesce with explicit CASE statement
- Handle: NULL `last_accessed_at`, NULL `created_at`, or both

### Phase 2: Tasks

Tasks will be generated by `/speckit.tasks` command.

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Config copy fails on some containers | Low | Low | Use `|| true` for graceful fallback to defaults |
| Gauge refresh adds latency | Low | Low | Health metrics query is lightweight |
| NULL handling breaks edge cases | Low | Medium | Test with NULL values before merge |
| Existing decay scores need recalculation | Medium | Low | Maintenance will recalculate on next run |

## Verification Plan

1. **Unit Tests**: Add pytest cases for NULL timestamp handling
2. **Integration Test**: Start container, add episodes, run maintenance, check:
   - Logs show "Loaded decay config from /app/mcp/config/decay-config.yaml"
   - 2-day-old entities show ~0.46% decay (not 2.7%)
   - Prometheus `knowledge_decay_score_avg` matches database average
3. **Regression Test**: Existing decay tests must continue passing
