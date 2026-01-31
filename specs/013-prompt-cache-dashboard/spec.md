# Feature Specification: Prompt Cache Effectiveness Dashboard

**Feature Branch**: `013-prompt-cache-dashboard`
**Created**: 2026-01-31
**Status**: Draft
**Input**: Issues #36, #39 - Create a new dashboard to visualize Gemini prompt caching performance and ROI with restart gap handling

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Monitor Caching ROI (Priority: P1)

As a **cost optimizer**, I need to see the total cost savings from prompt caching so I can justify the caching investment and identify optimization opportunities.

**Why this priority**: Direct financial impact - this is the primary business case for using prompt caching. Without visibility into savings, caching effectiveness cannot be measured or optimized.

**Independent Test**: Dashboard displays cumulative cost savings metric that can be compared against API costs to calculate net savings.

**Acceptance Scenarios**:

1. **Given** the dashboard is loaded, **When** I view the cost savings panel, **Then** I see total USD saved since system start with current value prominently displayed
2. **Given** caching has been running for at least 24 hours, **When** I view the cost savings rate panel, **Then** I see savings per hour trend over time
3. **Given** multiple LLM models are in use, **When** I view cost savings by model, **Then** I can compare which models provide the highest caching ROI

---

### User Story 2 - Analyze Cache Hit/Miss Patterns (Priority: P1)

As a **system administrator**, I need to see cache hit and miss rates so I can identify whether caching is working effectively and detect any anomalies.

**Why this priority**: Hit rate is the primary indicator of caching health. A sudden drop in hit rate indicates cache configuration issues or changing access patterns that need attention.

**Independent Test**: Dashboard displays hit rate percentage and hit/miss count comparison that can be monitored for anomalies.

**Acceptance Scenarios**:

1. **Given** the dashboard is loaded, **When** I view the hit rate panel, **Then** I see current hit rate as a percentage with trend over time
2. **Given** normal operation, **When** I view the hit vs miss comparison, **Then** I see both metrics displayed side-by-side with proportional representation
3. **Given** a sudden drop in hit rate occurs, **When** I view the hit rate trend, **Then** I can identify the approximate time of the drop from the time-series graph

---

### User Story 3 - Understand Cache Write Overhead (Priority: P2)

As a **system administrator**, I need to see how many tokens are being written to cache so I can understand the storage and performance overhead of maintaining the cache.

**Why this priority**: Cache writes consume resources. Understanding write volume helps assess whether caching overhead is justified by the savings.

**Independent Test**: Dashboard displays cache write token count that can be compared against tokens saved to calculate overhead ratio.

**Acceptance Scenarios**:

1. **Given** the dashboard is loaded, **When** I view the cache writes panel, **Then** I see total tokens written to cache since system start
2. **Given** the dashboard shows writes and savings, **When** I compare the values, **Then** I can calculate the write-to-saved ratio to assess cache efficiency

---

### User Story 4 - Analyze Cache Hit Distribution (Priority: P2)

As a **cost optimizer**, I need to see the distribution of cache hit sizes so I can understand whether most hits are small (low value) or large (high value).

**Why this priority**: A small number of large hits may be more valuable than many small hits. Distribution analysis helps focus optimization efforts.

**Independent Test**: Dashboard displays histogram showing tokens saved per request bucket distribution.

**Acceptance Scenarios**:

1. **Given** the dashboard is loaded, **When** I view the tokens saved distribution, **Then** I see a heatmap showing the frequency of different hit sizes
2. **Given** the heatmap is displayed, **When** I examine the distribution, **Then** I can identify whether hits are concentrated in small, medium, or large token ranges

---

### User Story 5 - Compare Model-Specific Caching Performance (Priority: P3)

As a **system administrator**, I need to compare caching effectiveness across different LLM models so I can identify which models benefit most from caching and which may need configuration adjustments.

**Why this priority**: Different models may have different access patterns. Model-specific comparison helps optimize caching strategy per model.

**Independent Test**: Dashboard displays per-model breakdown of key cache metrics (hits, misses, savings) allowing side-by-side comparison.

**Acceptance Scenarios**:

1. **Given** multiple models are in use, **When** I view the per-model comparison panel, **Then** I see each model's hit rate, tokens saved, and cost savings displayed side-by-side
2. **Given** I want to identify underperforming models, **When** I sort by any metric, **Then** I can see models ranked by that metric

---

### Edge Cases

- Service restart: Counters reset to zero, but time-over-time queries should preserve the last known value during the gap
- No cache activity yet (no hits or misses): Dashboard should display "0" or "No data" without errors
- Missing or incomplete metric data: Dashboard should handle gracefully without breaking visualizations
- Model added or removed from service: Dashboard should adapt without requiring manual reconfiguration
- Time ranges with no activity: Dashboard should show continuous time series with no gaps (handled by time-over-time functions)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Dashboard MUST display total cost savings in USD since system start
- **FR-002**: Dashboard MUST display cache hit rate as a percentage with trend over time
- **FR-003**: Dashboard MUST display cache hits vs misses comparison
- **FR-004**: Dashboard MUST display tokens saved per request distribution as a heatmap
- **FR-005**: Dashboard MUST display total tokens written to cache (write overhead)
- **FR-006**: Dashboard MUST display per-model cache performance comparison
- **FR-007**: Dashboard MUST support time range selection (1h, 6h, 24h, 7d, 30d)
- **FR-008**: Dashboard MUST handle zero-value gracefully (show "No data" or "0" instead of errors)
- **FR-009**: Dashboard MUST refresh data automatically at configurable intervals
- **FR-010**: Dashboard MUST display all panels on a single screen (no scrolling required for overview)
- **FR-011**: Dashboard MUST use time-over-time query functions (e.g., `max_over_time()`, `min_over_time()`) to handle service restart gaps in cumulative metrics

### Key Entities

- **Cache Savings Metric**: Cumulative USD saved from prompt caching since system start
- **Hit Rate Metric**: Percentage of cache reads that returned cached results vs. misses
- **Tokens Saved Distribution**: Histogram bucket showing frequency of different token save amounts per request
- **Cache Writes Metric**: Cumulative tokens written to cache for creating new cached entries
- **Model Performance**: Per-model breakdown of hits, misses, tokens saved, and cost savings

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can identify total cache cost savings within 5 seconds of loading the dashboard
- **SC-002**: Users can detect a cache hit rate anomaly (drop >20%) within 5 minutes of occurrence
- **SC-003**: Dashboard displays all data on a single screen without scrolling on standard 1080p display
- **SC-004**: Dashboard handles service restarts gracefully without displaying errors or broken visualizations
- **SC-005**: Users can compare caching performance across at least 3 different LLM models simultaneously

## Assumptions

1. Prometheus metrics are already being emitted (PR #34 added the required metrics)
2. Grafana is already provisioned and accessible
3. Dashboard will be provisioned via Grafana's dashboard provisioning system (JSON files)
4. Standard Grafana visualization panels (time series, heatmap, stat, gauge) will be used
5. Dashboard refresh interval defaults to 30 seconds but is user-configurable
6. Time range selection uses Grafana's standard time range controls

## Out of Scope

- Historical data migration or backfill (dashboard shows data from when metrics were added)
- Alerting or notification rules (these are separate Prometheus alerts)
- Caching configuration management (this is a monitoring dashboard, not a control interface)
- Cost attribution per user or per group (this is system-level caching visibility)

## Dependencies

- PR #34 metrics must be deployed and emitting data
- Grafana instance must be provisioned and accessible
- Prometheus data source must be configured in Grafana
- Issue #39 restart gap handling pattern should be applied for consistency across all dashboards
