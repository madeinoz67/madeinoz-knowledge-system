# Implementation Plan: Memory Decay Scoring and Importance Classification

**Branch**: `009-memory-decay-scoring` | **Date**: 2026-01-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/009-memory-decay-scoring/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement memory decay scoring, importance classification, lifecycle management, and observability metrics for the Knowledge system. Uses Graphiti's existing `attributes` dictionary for custom fields, exponential half-life decay formula with stability-adjusted rates, and Prometheus-compatible metrics for monitoring. All Python modules live in `docker/patches/` per Constitution Principle VII.

## Technical Context

**Language/Version**: Python 3.11 (MCP server), TypeScript (CLI tools with Bun)
**Primary Dependencies**: graphiti-core, neo4j, pydantic, prometheus_client
**Storage**: Neo4j (default) or FalkorDB backend
**Testing**: pytest (Python), bun test (TypeScript)
**Target Platform**: Linux/macOS containers via Podman/Docker
**Project Type**: Single project with language separation (docker/ for Python, src/ for TypeScript)
**Performance Goals**: Maintenance completes within 10 minutes, search latency unchanged
**Constraints**: LLM classification fallback to defaults on failure, batch processing
**Scale/Scope**: 10k+ memories, scheduled maintenance runs

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Container-First Architecture | ✅ PASS | All code runs in Docker/Podman containers |
| II. Graph-Centric Design | ✅ PASS | Extends Graphiti EntityNode attributes |
| III. Zero-Friction Knowledge Capture | ✅ PASS | Classification is automatic at ingestion |
| IV. Query Resilience | ✅ PASS | Lifecycle state filters prevent returning soft-deleted |
| V. Graceful Degradation | ✅ PASS | LLM fallback to defaults, stale decay scores OK |
| VI. Codanna-First Development | ✅ PASS | Used Codanna for codebase exploration |
| VII. Language Separation | ✅ PASS | Python in docker/patches/, TypeScript in src/ |
| VIII. Dual-Audience Documentation | ✅ PASS | Metrics tables in spec for AI parsing |

## Project Structure

### Documentation (this feature)

```text
specs/009-memory-decay-scoring/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output - COMPLETE
├── data-model.md        # Phase 1 output - COMPLETE (updated for metrics)
├── quickstart.md        # Phase 1 output - COMPLETE
├── contracts/           # Phase 1 output
│   └── decay-api.yaml   # MCP tool definitions - COMPLETE (updated for metrics)
└── tasks.md             # Phase 2 output - COMPLETE
```

### Source Code (repository root)

```text
docker/                      # Python ecosystem (Constitution VII)
├── patches/                 # Python implementation code
│   ├── graphiti_mcp_server.py    # Extended with decay MCP tools
│   ├── decay_types.py           # Enums and dataclasses
│   ├── decay_config.py          # YAML config loader
│   ├── decay_migration.py       # Neo4j index/backfill
│   ├── importance_classifier.py  # LLM classification
│   ├── memory_decay.py          # Decay calculator + weighted scoring
│   ├── lifecycle_manager.py      # State transitions
│   ├── maintenance_service.py    # Batch processing
│   └── metrics_exporter.py       # NEW: Prometheus metrics ← Observability
└── tests/                   # Python tests
    ├── unit/               # Unit tests for decay modules
    └── integration/        # Integration tests

src/                         # TypeScript ecosystem (Constitution VII)
└── skills/                 # PAI skill definitions
    └── workflows/
        └── health-report.md # Health report workflow

config/
├── decay-config.yaml       # Decay configuration
└── monitoring/
    └── prometheus/
        └── prometheus.yml  # Prometheus scrape config ← Observability
```

**Structure Decision**: Following Constitution Principle VII - Python code (decay modules, metrics) in `docker/patches/`, TypeScript tools in `src/`.

## Complexity Tracking

> **No violations - all changes align with Constitution principles**

| Addition | Justification |
|----------|---------------|
| metrics_exporter.py | Required for observability per spec FR-010, follows existing Prometheus pattern |
| prometheus.yml updates | Extends existing monitoring infrastructure |

## Observability Metrics Addition

### Phase 0 Research: Prometheus Integration

**Decision**: Use `prometheus_client` Python library with push gateway or embedded HTTP endpoint.

**Rationale**:
- Project already has `config/monitoring/prometheus/prometheus.yml` infrastructure
- `prometheus_client` is the standard Python library for Prometheus metrics
- Matches observability patterns from Feature 006 (Gemini Prompt Caching)

**Alternatives Considered**:

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| prometheus_client | Standard, well-documented | Adds dependency | **Chosen** |
| StatsD | Push-based | Extra infrastructure | Rejected |
| OpenTelemetry | Standard observability | Heavier weight | Future option |
| Manual /metrics endpoint | No dependencies | Reinventing wheel | Rejected |

### Phase 1 Design: Metrics Module

**New File**: `docker/patches/metrics_exporter.py`

```python
from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry

# Counter metrics
MAINTENANCE_RUNS = Counter(
    'knowledge_decay_maintenance_runs_total',
    'Total maintenance runs',
    ['status']
)
DECAY_SCORES_UPDATED = Counter(
    'knowledge_decay_scores_updated_total',
    'Cumulative decay scores recalculated'
)
LIFECYCLE_TRANSITIONS = Counter(
    'knowledge_lifecycle_transitions_total',
    'State transition counts',
    ['from_state', 'to_state']
)
MEMORIES_PURGED = Counter(
    'knowledge_memories_purged_total',
    'Soft-deleted memories permanently removed'
)
CLASSIFICATION_REQUESTS = Counter(
    'knowledge_classification_requests_total',
    'LLM classification attempts',
    ['status']
)

# Gauge metrics
MEMORIES_BY_STATE = Gauge(
    'knowledge_memories_by_state',
    'Current count per lifecycle state',
    ['state']
)
DECAY_SCORE_AVG = Gauge(
    'knowledge_decay_score_avg',
    'Average decay score across non-permanent memories'
)
IMPORTANCE_AVG = Gauge(
    'knowledge_importance_avg',
    'Average importance score'
)
STABILITY_AVG = Gauge(
    'knowledge_stability_avg',
    'Average stability score'
)
MEMORIES_TOTAL = Gauge(
    'knowledge_memories_total',
    'Total memory count excluding soft-deleted'
)

# Histogram metrics
MAINTENANCE_DURATION = Histogram(
    'knowledge_maintenance_duration_seconds',
    'Maintenance run duration',
    buckets=[1, 5, 30, 60, 120, 300, 600]
)
CLASSIFICATION_LATENCY = Histogram(
    'knowledge_classification_latency_seconds',
    'LLM classification response time',
    buckets=[0.1, 0.5, 1, 2, 5]
)
SEARCH_WEIGHTED_LATENCY = Histogram(
    'knowledge_search_weighted_latency_seconds',
    'Weighted search scoring overhead',
    buckets=[0.01, 0.05, 0.1, 0.5, 1]
)
```

### Tasks for Observability

New tasks to add to tasks.md Phase 8:

- [ ] T059 [P] Create `docker/patches/metrics_exporter.py` with Prometheus metrics definitions
- [ ] T060 [P] Instrument `maintenance_service.py` with duration histogram and counters
- [ ] T061 [P] Instrument `importance_classifier.py` with latency histogram and status counter
- [ ] T062 [P] Instrument `lifecycle_manager.py` with transition counters
- [ ] T063 [P] Add `/metrics` HTTP endpoint to graphiti_mcp_server.py
- [ ] T064 [P] Update `config/monitoring/prometheus/prometheus.yml` with knowledge scrape target
- [ ] T065 [P] Create unit test `docker/tests/unit/test_metrics_exporter.py`

## Implementation Status

### Completed Phases

- [x] Phase 1: Setup (T001-T004)
- [x] Phase 2: Foundational (T005-T008)
- [x] Phase 3: US2 - Classification (T009-T011 implementation, T012-T015 pending tests)
- [x] Phase 4: US1 - Weighted Search (T016-T022 implementation, T023-T024 pending tests)
- [x] Phase 5: US3 - Decay (T025-T029 implementation, T030-T031 pending tests)
- [x] Phase 6: US4 - Lifecycle (T032-T038 implementation, T039-T041 pending tests)
- [x] Phase 7: US5 - Maintenance (T042-T050 implementation, T051-T052 pending tests)
- [ ] Phase 8: Polish & Observability (T053-T058 + NEW T059-T065)

### Remaining Work

1. **Integration**: T012-T013 (add_memory classification via QueueService)
2. **Unit Tests**: T014-T015, T023-T024, T030-T031, T039-T041, T051-T052
3. **Integration Tests**: T052
4. **Observability**: T059-T065 (NEW)
5. **Documentation**: T053-T058
