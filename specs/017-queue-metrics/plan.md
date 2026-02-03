# Implementation Plan: Queue Processing Metrics

**Branch**: `017-queue-metrics` | **Date**: 2026-02-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/017-queue-metrics/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Add queue processing metrics observability to the knowledge system following the RED (Rate, Errors, Duration) + USE (Utilization, Saturation, Errors) methodology. The feature implements a `QueueMetricsExporter` class patterned after existing `CacheMetricsExporter` and `DecayMetricsExporter`, exposing counters, gauges, and histograms via Prometheus on port 9090. Instrumentation wraps QueueService operations without modifying the external Graphiti library.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- OpenTelemetry SDK (metrics, PrometheusMetricReader)
- prometheus_client (HTTP server)
- Graphiti library (QueueService - external, not modified)
**Storage**: Neo4j or FalkorDB (existing, unchanged)
**Testing**: pytest (existing test infrastructure)
**Target Platform**: Linux containers (Docker/Podman)
**Project Type**: Python MCP server with containerized deployment
**Performance Goals**:
- Metrics collection overhead < 1ms per message
- Prometheus scrape completes in < 100ms
- No degradation to existing queue processing throughput
**Constraints**:
- Must not modify external Graphiti QueueService
- Must share OpenTelemetry meter with existing metrics exporters
- Must gracefully degrade when OpenTelemetry unavailable
**Scale/Scope**:
- Single exporter class in `docker/patches/metrics_exporter.py`
- Instrumentation in `docker/patches/graphiti_mcp_server.py`
- Optional Grafana dashboard (P3 priority)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

[No constitution file exists for this project - skipping]

## Project Structure

### Documentation (this feature)

```text
specs/017-queue-metrics/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (queue service analysis, OpenTelemetry patterns)
├── data-model.md        # Phase 1 output (metric types, labels, data structures)
├── quickstart.md        # Phase 1 output (setup, verification, dashboard import)
├── contracts/           # Phase 1 output (metric contract definitions)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created yet)
```

### Source Code (repository root)

```text
docker/
├── patches/
│   ├── metrics_exporter.py       # Add QueueMetricsExporter class (new)
│   └── graphiti_mcp_server.py    # Add instrumentation calls (modify)
```

**Structure Decision**: Single project structure with Python backend. The `docker/patches/` directory contains all modifications to the Graphiti MCP server, following the established pattern from features 006 (cache metrics) and 009 (decay metrics).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | No violations | This feature follows established patterns from existing metrics exporters |

## Phase 0: Research

**Goal**: Validate assumptions, identify risks, confirm feasibility.

### Research Questions

| Question | Impact | Answers Needed |
|----------|--------|----------------|
| How does QueueService expose queue state? | High | Need to determine if queue depth is observable without modification |
| What instrumentation points exist? | High | Identify where enqueue/dequeue/processing can be measured |
| Does OpenTelemetry support required metric types? | Medium | Confirm histogram buckets, gauge labels work as expected |
| What are the performance implications? | Medium | Validate metrics collection doesn't degrade processing |

### Research Tasks

1. **Analyze QueueService interface** (`services.queue_service` from Graphiti)
   - Determine if queue depth is accessible via public API
   - Identify consumer lifecycle hooks
   - Document any limitations

2. **Study existing metrics patterns**
   - Review `CacheMetricsExporter` initialization
   - Review `DecayMetricsExporter` metric recording patterns
   - Document shared meter usage

3. **Validate OpenTelemetry capabilities**
   - Confirm histogram bucket configuration
   - Verify gauge label cardinality handling
   - Test Prometheus endpoint integration

### Research Output

See [research.md](research.md) for detailed findings.

**Key Findings**:
- QueueService is external library with no hooks for instrumentation (from spec #011)
- Must wrap calls to `queue_service.add_episode()` rather than modifying QueueService
- Existing `CacheMetricsExporter` and `DecayMetricsExporter` provide proven pattern
- OpenTelemetry meter can be shared across exporters

## Phase 1: Design

**Goal**: Define data structures, API contracts, and integration points.

### Data Model

See [data-model.md](data-model.md) for complete data structures.

**Key Entities**:

| Entity | Attributes | Notes |
|--------|-----------|-------|
| QueueMessage | priority, enqueue_time, dequeue_time, status, error_type | Wrapped for instrumentation |
| Queue | name, depth, active_consumer_count | Gauge metrics source |
| Consumer | group_id, saturation (0-1), lag_seconds | Calculated from depth and rate |
| ProcessingAttempt | attempt_number, duration, result, error_type | Histogram data points |
| Metric | name, type, labels, value | OpenTelemetry instrument |

### Metric Types

| Type | Metric Name | Labels | Description |
|------|-------------|--------|-------------|
| Counter | `messaging_messages_processed_total` | queue_name, status | Total messages processed |
| Counter | `messaging_messages_failed_total` | queue_name, error_type | Total failures |
| Counter | `messaging_retries_total` | queue_name | Retry attempts |
| Gauge | `messaging_queue_depth` | queue_name, priority | Current queue size |
| Gauge | `messaging_consumer_lag_seconds` | queue_name, consumer_group | Time to catch up |
| Gauge | `messaging_consumer_saturation` | queue_name, consumer_group | Utilization ratio |
| Gauge | `messaging_active_consumers` | queue_name | Consumer count |
| Histogram | `messaging_processing_duration_seconds` | - | Processing time |
| Histogram | `messaging_wait_time_seconds` | - | Queue wait time |
| Histogram | `messaging_end_to_end_latency_seconds` | - | Total latency |

### API Contracts

See [contracts/](contracts/) for detailed contract definitions.

**QueueMetricsExporter Public Interface**:

```python
class QueueMetricsExporter:
    def __init__(self, meter: Optional[Any] = None)
    def record_enqueue(self, queue_name: str, priority: str) -> None
    def record_dequeue(self, queue_name: str) -> None
    def record_processing_start(self, queue_name: str) -> ContextManager
    def record_processing_complete(self, queue_name: str, duration: float, success: bool, error_type: Optional[str] = None) -> None
    def record_retry(self, queue_name: str) -> None
    def update_queue_depth(self, queue_name: str, depth: int, priority: str) -> None
    def update_consumer_metrics(self, queue_name: str, consumer_group: str, active: int, saturation: float, lag_seconds: float) -> None
```

### Integration Points

| Location | Change | Purpose |
|----------|--------|---------|
| `docker/patches/metrics_exporter.py` | Add `QueueMetricsExporter` class | Metrics collection |
| `docker/patches/metrics_exporter.py` | Add queue Views to meter provider | Histogram buckets |
| `docker/patches/graphiti_mcp_server.py` | Import and initialize `QueueMetricsExporter` | Bootstrap |
| `docker/patches/graphiti_mcp_server.py` | Wrap `queue_service.add_episode()` calls | Instrumentation |

### Quickstart Guide

See [quickstart.md](quickstart.md) for setup and verification steps.

**Summary**:
1. Add `QueueMetricsExporter` to `metrics_exporter.py`
2. Import and initialize in `graphiti_mcp_server.py` main()
3. Wrap queue operations with metric recording calls
4. Verify metrics at `http://localhost:9090/metrics`
5. (Optional) Import Grafana dashboard from `specs/017-queue-metrics/dashboard.json`

## Phase 2: Decomposition

**Goal**: Break down into implementable tasks. Output: `tasks.md` (created by `/speckit.tasks`)

**Task Categories** (to be expanded in tasks.md):

1. **Core Metrics Implementation**
   - Create `QueueMetricsExporter` class
   - Add queue Views to meter provider
   - Implement counter metrics
   - Implement gauge metrics
   - Implement histogram metrics

2. **Instrumentation**
   - Import and initialize in main()
   - Wrap enqueue operations
   - Wrap dequeue operations
   - Add processing duration tracking
   - Add failure and retry tracking

3. **Testing**
   - Unit tests for `QueueMetricsExporter`
   - Integration tests for instrumentation
   - Verify Prometheus endpoint
   - Performance tests (overhead < 1ms)

4. **Dashboard (P3)**
   - Design Grafana dashboard JSON
   - Test panel queries
   - Document import process

## Open Questions

| Question | Priority | Status |
|----------|----------|--------|
| How to measure actual queue depth from external QueueService? | High | Open - may need approximation |
| How to calculate consumer saturation without internal metrics? | Medium | Open - may need heuristics |
| Should dashboard be included in P1 or deferred to P3? | Low | Resolved - P3 per spec |

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| QueueService doesn't expose depth | High | Use enqueue/dequeue counters as proxy |
| Metrics collection degrades performance | Medium | Benchmark and optimize hot paths |
| High label cardinality on error_type | Low | Use coarse-grained error categories |

## Dependencies

| Dependency | Type | Required For |
|------------|------|--------------|
| OpenTelemetry SDK | External | Metrics export |
| prometheus_client | External | HTTP endpoint |
| Graphiti QueueService | External | Queue operations (instrumentation only) |

## Success Criteria

From [spec.md](spec.md):

- Operators can identify growing backlog within 5 minutes (SC-001)
- Consumer lag expressed as time-to-catch-up (SC-002)
- Processing latency regressions detected within 1 minute (SC-003)
- Capacity planning enabled via metrics correlation (SC-004)
- Failed processing debuggable via error type labels (SC-005)
- All metrics queryable via existing Prometheus endpoint (SC-006)
- Dashboard assesses queue health in under 30 seconds (SC-007, P3)
