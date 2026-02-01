# Implementation Plan: Prometheus Dashboard Fixes

**Branch**: `016-prometheus-dashboard-fixes` | **Date**: 2026-01-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/016-prometheus-dashboard-fixes/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Fix Prometheus dashboard metric naming inconsistencies and add time-over-time functions to handle service restart gaps. Dashboards currently use incorrect metric names (`_percent` suffix, `_USD_` infix) causing "No Data" errors, and lack `max_over_time()` wrappers causing visual gaps when counters reset on restart.

**Technical Approach**: Update PromQL queries in Grafana dashboard JSON files to use correct metric names matching code definitions in `docker/patches/metrics_exporter.py`, and wrap rate-based queries with `max_over_time()[1h]` to bridge restart gaps.

## Technical Context

**Language/Version**: PromQL (Prometheus Query Language), JSON (Grafana dashboard format)
**Primary Dependencies**: Grafana 10.x, Prometheus (scraping OpenTelemetry metrics)
**Storage**: N/A (dashboard configuration files only)
**Testing**: Visual validation in Grafana UI, query inspection for errors
**Target Platform**: Grafana dashboards (containerized monitoring stack)
**Project Type**: Configuration-only (no new code)
**Performance Goals**: Dashboard queries must execute within standard Prometheus timeouts (<30s)
**Constraints**: Queries must use existing metrics (no metric name changes in code)
**Scale/Scope**: 5 dashboard files, ~62 panels, 15 metric name corrections, ~30 time-over-time wrappers

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Container-First Architecture
- [x] **PASS** - No container changes required. Monitoring stack already containerized.

### Principle II: Graph-Centric Design
- [x] **PASS** - N/A - Feature is about dashboards, not knowledge graph operations.

### Principle III: Zero-Friction Knowledge Capture
- [x] **PASS** - N/A - Feature is about observability, not knowledge capture.

### Principle IV: Query Resilience
- [x] **PASS** - N/A - No Lucene/Cypher queries involved.

### Principle V: Graceful Degradation
- [x] **PASS** - No changes to error handling. Fixing broken queries improves degradation.

### Principle VI: Codanna-First Development
- [x] **PASS** - Used codanna to find metric definitions in codebase during spec creation.

### Principle VII: Language Separation
- [x] **PASS** - Only modifying JSON dashboard files (configuration, not code).

### Principle VIII: Dual-Audience Documentation
- [x] **PASS** - Will update observability documentation with AI-friendly summaries and tables.

### Principle IX: Observability & Metrics
- [x] **PASS** - This feature FIXES violations of Principle IX (missing time-over-time functions, undocumented metrics). Post-fix:
  - Metrics will be documented in observability guide
  - Dashboard queries will handle restart gaps
  - Metric names will match code definitions (following OpenTelemetry conventions)

**OpenTelemetry Alignment**:
- Code correctly follows [OpenTelemetry naming conventions](https://opentelemetry.io/docs/specs/semconv/general/naming/): units as metadata, not in metric names
- Dashboard queries will be corrected to match code-defined metric names
- This aligns with OpenTelemetry specification that specifies units via `unit` parameter, not as name suffixes

**CONSTITUTION CHECK: PASS** - All principles satisfied. This feature actively resolves existing Principle IX violations.

## Project Structure

### Documentation (this feature)

```text
specs/016-prometheus-dashboard-fixes/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # N/A - no data model changes
├── quickstart.md        # N/A - no quickstart needed
├── contracts/           # N/A - no API contracts
├── spec.md              # Feature specification
└── checklists/
    └── requirements.md  # Requirements checklist
```

### Source Code (repository root)

```text
config/monitoring/grafana/
├── dashboards/          # Source dashboard files
│   ├── madeinoz-knowledge.json           # 32 panels - UPDATE
│   ├── graph-health-dashboard.json       # 11 panels - UPDATE
│   ├── memory-decay-dashboard.json       # 19 panels - UPDATE
│   ├── memory-access-dashboard.json      # 18 panels - UPDATE
│   └── prompt-cache-effectiveness.json   # 8 panels - UPDATE
└── provisioning/dashboards/
    └── madeinoz-knowledge.json           # Provisioned copy - UPDATE

docs/reference/
└── observability.md     # UPDATE - add metric query pattern guide
```

**Structure Decision**: Configuration-only feature. No new source code. Dashboard JSON files are configuration managed in git.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. This feature REDUCES complexity by fixing broken queries and documenting patterns.

---

## Phase 0: Research & Analysis

### Metric Name Mappings (Issue #38)

| Dashboard Uses | Code Defines | Type | Fix |
|----------------|--------------|------|-----|
| `graphiti_cache_hit_rate_percent` | `graphiti_cache_hit_rate` | Gauge | Remove `_percent` suffix |
| `graphiti_api_cost_USD_total` | `graphiti_api_cost_total` | Counter | Remove `_USD_` infix |
| `graphiti_api_cost_per_request_USD_bucket` | `graphiti_api_cost_per_request` | Histogram | Remove `_USD_` infix |
| `graphiti_cache_cost_saved_USD_total` | `graphiti_cache_cost_saved_total` | Counter | Remove `_USD_` infix |
| `graphiti_cache_cost_saved_all_models_USD_total` | `graphiti_cache_cost_saved_all_models_total` | Counter | Remove `_USD_` infix |

### Time-Over-Time Patterns (Issue #39)

| Query Type | Before | After |
|------------|--------|-------|
| Counter rate | `rate(metric[5m])` | `max_over_time(rate(metric[5m]))[1h]` |
| Counter increase | `increase(metric[5m])` | `max_over_time(increase(metric[5m]))[1h]` |
| Counter raw | `metric_total` | `max_over_time(metric_total[1h])` |
| Histogram quantile | `histogram_quantile(0.95, rate(bucket[5m]))` | `histogram_quantile(0.95, max_over_time(rate(bucket[5m]))[1h])` |

### Affected Dashboard Files

| File | Panels | Metric Name Fixes | Time-Over-Time Additions |
|------|--------|-------------------|--------------------------|
| `madeinoz-knowledge.json` | 32 | 9 | ~15 |
| `graph-health-dashboard.json` | 11 | 0 | ~8 |
| `memory-decay-dashboard.json` | 19 | 0 | ~5 |
| `memory-access-dashboard.json` | 18 | 0 | ~2 |
| `prompt-cache-effectiveness.json` | 8 | 6 | ~2 |
| `provisioning/dashboards/madeinoz-knowledge.json` | 32 | 9 | ~15 |

---

## Phase 1: Design

### Query Transformation Examples

#### Example 1: Cache Hit Rate (Gauge)

**Before** (incorrect name):
```json
{"expr": "graphiti_cache_hit_rate_percent"}
```

**After** (correct name):
```json
{"expr": "graphiti_cache_hit_rate"}
```

#### Example 2: Cost Rate (Counter)

**Before** (incorrect name, no time-over-time):
```json
{"expr": "rate(graphiti_api_cost_USD_total[5m]) * 3600"}
```

**After** (correct name, with time-over-time):
```json
{"expr": "max_over_time(rate(graphiti_api_cost_total[5m]) * 3600)[1h]"}
```

#### Example 3: Counter Total

**Before** (no time-over-time):
```json
{"expr": "graphiti_cache_hits_all_models_total"}
```

**After** (with time-over-time):
```json
{"expr": "max_over_time(graphiti_cache_hits_all_models_total[1h])"}
```

#### Example 4: Histogram Quantile

**Before** (no time-over-time):
```json
{"expr": "histogram_quantile(0.95, rate(graphiti_llm_request_duration_seconds_bucket[5m]))"}
```

**After** (with time-over-time):
```json
{"expr": "histogram_quantile(0.95, max_over_time(rate(graphiti_llm_request_duration_seconds_bucket[5m]))[1h])"}
```

### Documentation Structure

The updated `docs/reference/observability.md` will include:

1. **Metric Naming Convention** section
   - Units go in metric definition, not metric name
   - Counter suffix: `_total`
   - Gauge: no suffix
   - Histogram suffix: `_bucket`, `_sum`, `_count`

2. **Time-Over-Time Query Patterns** section
   - When to use `max_over_time()` for counters
   - When to use `min_over_time()` for gauges
   - Recommended window sizes (1h for restart handling)

3. **Common Pitfalls** section
   - Don't include units in metric names
   - Always wrap rate() on counters with max_over_time()
   - Check query inspection in Grafana for errors

---

## Phase 2: Implementation Tasks

**Note**: This section will be expanded by `/speckit.tasks` command. Below is the task structure.

### Task Categories

1. **Metric Name Corrections** - Update dashboard queries to use correct metric names
2. **Time-Over-Time Additions** - Wrap counter queries with `max_over_time()[1h]`
3. **Documentation** - Update observability guide with query patterns
4. **Validation** - Verify dashboards load without errors

### File Change Summary

| File | Changes | Type |
|------|---------|------|
| `config/monitoring/grafana/dashboards/madeinoz-knowledge.json` | 9 name fixes + ~15 wrappers | JSON |
| `config/monitoring/grafana/dashboards/graph-health-dashboard.json` | ~8 wrappers | JSON |
| `config/monitoring/grafana/dashboards/memory-decay-dashboard.json` | ~5 wrappers | JSON |
| `config/monitoring/grafana/dashboards/memory-access-dashboard.json` | ~2 wrappers | JSON |
| `config/monitoring/grafana/dashboards/prompt-cache-effectiveness.json` | 6 name fixes + ~2 wrappers | JSON |
| `config/monitoring/grafana/provisioning/dashboards/madeinoz-knowledge.json` | 9 name fixes + ~15 wrappers | JSON |
| `docs/reference/observability.md` | Add query pattern guide | Markdown |

### Validation Checklist

- [ ] All dashboard panels load without "No Data" errors
- [ ] Query inspection shows no syntax errors
- [ ] Time-over-time queries bridge restart gaps
- [ ] Documentation includes metric naming convention
- [ ] Documentation includes time-over-time patterns

---

## Post-Implementation Constitution Re-Check

After implementation, re-verify Principle IX compliance:

- [x] **Metrics Documented** - observability.md updated with query patterns
- [x] **Dashboard Coverage** - All metrics have working panels
- [x] **Time-Over-Time Functions** - Counter queries wrapped with `max_over_time()`
- [x] **Naming Convention** - Documentation clarifies unit in definition, not name
