# Feature Specification: Prometheus Dashboard Fixes

**Feature Branch**: `016-prometheus-dashboard-fixes`
**Created**: 2026-01-31
**Status**: Draft
**Input**: GitHub issues #38 and #39

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fix Broken Dashboard Metrics (Priority: P1)

As a system operator, I need all dashboard panels to display accurate metrics data so that I can monitor the knowledge system's health and performance.

**Why this priority**: Dashboards currently show "No Data" for some panels due to metric name mismatches. This breaks observability and prevents operators from monitoring system health.

**Independent Test**: Can be fully tested by opening each dashboard and verifying all panels show data instead of "No Data" errors.

**Acceptance Scenarios**:

1. **Given** I have deployed the updated dashboards, **When** I open the main knowledge dashboard, **Then** all panels display data without "No Data" errors
2. **Given** the cache hit rate panel previously showed no data, **When** I view the dashboard, **Then** the hit rate percentage displays correctly
3. **Given** API cost panels previously failed queries, **When** I view cost statistics, **Then** total and per-hour costs display correctly

---

### User Story 2 - Maintain Continuous Metrics During Restarts (Priority: P2)

As a system operator, I need dashboard graphs to show continuous data even when the knowledge system service restarts so that I can analyze long-term trends without visual gaps.

**Why this priority**: Service restarts create visual "cliffs" in graphs, making it difficult to analyze trends over time. However, this is a UX improvement rather than a critical breakage.

**Independent Test**: Can be fully tested by simulating a service restart and verifying dashboard panels continue to show smooth data transitions instead of gaps or spikes.

**Acceptance Scenarios**:

1. **Given** the knowledge system service is running, **When** the service restarts, **Then** dashboard graphs continue to show data without gaps
2. **Given** counter metrics reset to zero on restart, **When** viewing rate-based panels, **Then** the displayed values transition smoothly across the restart boundary
3. **Given** a service restart occurred, **When** viewing historical data spanning the restart, **Then** time-over-time functions bridge the gap showing maximum values in the time window

---

### User Story 3 - Document Metric Query Patterns (Priority: P3)

As a developer or operator, I need documented patterns for writing dashboard queries so that future dashboard additions follow consistent conventions.

**Why this priority**: Documentation prevents future inconsistencies but doesn't affect immediate functionality. This is a "force multiplier" for maintainability.

**Independent Test**: Can be fully tested by referencing the documentation while creating a new panel and verifying the recommended patterns produce working queries.

**Acceptance Scenarios**:

1. **Given** I am adding a new dashboard panel, **When** I reference the query patterns documentation, **Then** I can identify the correct metric name format without checking the Python code
2. **Given** I need to create a rate-based query, **When** following the documented patterns, **Then** my query includes appropriate time-over-time functions
3. **Given** a metric has a unit defined in code, **When** writing dashboard queries, **Then** I understand not to include the unit in the metric name

---

### Edge Cases

- What happens when a metric exists in code but has never been emitted (no data yet)?
- How do dashboards behave when Prometheus scrape interval is longer than query time ranges?
- What if OpenTelemetry metric naming conventions change in future versions?
- How do time-over-time queries behave when the time window extends before service first started?
- What happens if a dashboard references a metric that was removed in a code update?

## Requirements *(mandatory)*

### Functional Requirements

**Metric Name Corrections (Issue #38)**

- **FR-001**: Dashboard queries MUST use `graphiti_cache_hit_rate` (the actual metric name) instead of `graphiti_cache_hit_rate_percent`
- **FR-002**: Dashboard queries for cost metrics MUST use `graphiti_api_cost_total` instead of `graphiti_api_cost_USD_total`
- **FR-003**: Dashboard queries for cost savings MUST use `graphiti_cache_cost_saved_total` and `graphiti_cache_cost_saved_all_models_total` instead of versions with `_USD_` in the metric name
- **FR-004**: Dashboard queries for cost histograms MUST use `graphiti_api_cost_per_request` instead of `graphiti_api_cost_per_request_USD_bucket`
- **FR-005**: All metric names in dashboard queries MUST match the instrument_name values defined in `docker/patches/metrics_exporter.py`

**Time-Over-Time Functions (Issue #39)**

- **FR-006**: Counter-based queries using `rate()` or `increase()` MUST be wrapped with `max_over_time()` to bridge restart gaps
- **FR-007**: Time-over-time windows MUST be set to 1 hour to cover typical restart scenarios
- **FR-008**: Gauge metric queries (like `graphiti_cache_hit_rate`) that use `rate()` MUST also include time-over-time wrapping
- **FR-009**: Histogram quantile queries MUST use time-over-time functions on the inner `rate()` calculation
- **FR-010**: The `max_over_time()` wrapper MUST be applied to the complete rate expression, not just the metric name

**Dashboard Updates**

- **FR-011**: All dashboards in `config/monitoring/grafana/dashboards/` MUST be updated with corrected metric names
- **FR-012**: All dashboards in `config/monitoring/grafana/provisioning/dashboards/` MUST be updated to match the source dashboards
- **FR-013**: After updates, each dashboard panel MUST be validated to show data without query errors

**Documentation**

- **FR-014**: An observability guide document MUST explain the metric naming convention (unit is in the metric definition, not the name)
- **FR-015**: The guide MUST document the time-over-time query pattern for handling restarts
- **FR-016**: The guide MUST include examples of correct vs incorrect metric name usage

### Key Entities

- **Dashboard Panel**: A visualization component in Grafana that displays metrics data using PromQL queries
- **PromQL Query**: The query language used to fetch and transform metrics from Prometheus
- **Counter Metric**: A cumulative metric that only increases (e.g., total requests, total cost) and resets to zero on service restart
- **Gauge Metric**: A metric that represents a current value (e.g., cache hit rate percentage)
- **Time-Over-Time Function**: PromQL functions like `max_over_time()`, `min_over_time()`, `avg_over_time()` that operate on data over a time window
- **Metric Name**: The identifier used to reference a metric in PromQL (distinct from its unit which is defined separately)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All dashboard panels display data without "No Data" errors when the service is running normally
- **SC-002**: Dashboard graphs show continuous data without visual gaps when service restarts occur
- **SC-003**: Time-over-time queries successfully bridge restart gaps, showing the maximum counter value in the time window
- **SC-004**: Zero metric name mismatches exist between dashboard queries and code-defined metric names
- **SC-005**: New contributors can write correct dashboard queries by following the documentation pattern guide
- **SC-006**: Dashboard panel query errors visible in Grafana "Query Inspection" are reduced to zero
