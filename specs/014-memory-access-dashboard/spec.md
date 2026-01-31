# Feature Specification: Memory Access Patterns Dashboard

**Feature Branch**: `014-memory-access-dashboard`
**Created**: 2026-01-31
**Status**: Draft
**GitHub Issue**: [#37](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/37)

## Overview

Create a monitoring dashboard to visualize knowledge graph memory access patterns and validate the effectiveness of the decay scoring system. This dashboard enables administrators to understand how memories are accessed across importance levels, lifecycle states, and time periods, while providing data scientists with correlation analysis between access patterns and decay scores.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Access Distribution by Importance (Priority: P1)

As a knowledge system administrator, I want to see how memory accesses are distributed across importance levels so that I can validate that critical memories are being accessed appropriately.

**Why this priority**: Understanding access distribution by importance is the primary validation for decay scoring - if high-importance memories aren't being accessed more, the scoring system may need adjustment.

**Independent Test**: Can be fully tested by viewing a single panel showing access counts per importance level and verifying it displays real-time data.

**Acceptance Scenarios**:

1. **Given** the dashboard is loaded, **When** I view the importance distribution panel, **Then** I see access counts broken down by importance level (CRITICAL, HIGH, MEDIUM, LOW).
2. **Given** new memory accesses occur, **When** the dashboard refreshes, **Then** the importance distribution reflects the updated access patterns.
3. **Given** I select a time range, **When** the filter applies, **Then** the importance distribution shows data only for that period.

---

### User Story 2 - View Access Distribution by Lifecycle State (Priority: P1)

As a knowledge system administrator, I want to see how memory accesses are distributed across lifecycle states so that I can understand memory lifecycle progression and identify anomalies.

**Why this priority**: Lifecycle state distribution reveals whether memories are progressing through states as expected and if dormant/archived memories are being unnecessarily accessed.

**Independent Test**: Can be fully tested by viewing a single panel showing access counts per lifecycle state.

**Acceptance Scenarios**:

1. **Given** the dashboard is loaded, **When** I view the lifecycle state distribution panel, **Then** I see access counts broken down by state (ACTIVE, STABLE, DORMANT, ARCHIVED).
2. **Given** memories transition between states, **When** the dashboard refreshes, **Then** the distribution reflects current state assignments.

---

### User Story 3 - Monitor Access Rate Over Time (Priority: P2)

As a knowledge system administrator, I want to see memory access rates over time so that I can identify usage trends and peak access periods.

**Why this priority**: Time-series access data is essential for capacity planning and understanding system usage patterns.

**Independent Test**: Can be fully tested by viewing a time-series chart showing access counts over configurable time ranges.

**Acceptance Scenarios**:

1. **Given** the dashboard is loaded, **When** I view the access rate panel, **Then** I see a time-series visualization of memory access counts.
2. **Given** I adjust the time range, **When** the filter applies, **Then** the access rate chart updates to show data for the selected period.
3. **Given** access activity varies throughout the day, **When** I view hourly data, **Then** I can identify peak and low-activity periods.

---

### User Story 4 - Analyze Memory Age Distribution (Priority: P2)

As a data scientist, I want to see the distribution of time since last access across memories so that I can understand decay scoring inputs and identify memories at risk of becoming stale.

**Why this priority**: Age distribution is a key input to decay scoring and helps validate that the 180-day half-life setting is appropriate.

**Independent Test**: Can be fully tested by viewing a distribution chart showing memory counts by days since last access.

**Acceptance Scenarios**:

1. **Given** the dashboard is loaded, **When** I view the age distribution panel, **Then** I see memories grouped by time buckets since last access.
2. **Given** different decay configurations, **When** I analyze the distribution, **Then** I can identify memories approaching decay thresholds.

---

### User Story 5 - Track Memory Reactivations (Priority: P2)

As a knowledge system administrator, I want to see when dormant or archived memories are reactivated so that I can validate that the decay system correctly preserves valuable memories.

**Why this priority**: Reactivations indicate memories that were accessed after becoming dormant/archived, validating that the system correctly handles memory revival.

**Independent Test**: Can be fully tested by viewing reactivation counts and verifying they correspond to actual state transitions.

**Acceptance Scenarios**:

1. **Given** the dashboard is loaded, **When** I view the reactivations panel, **Then** I see counts of memories reactivated from DORMANT and ARCHIVED states.
2. **Given** a memory is accessed after becoming dormant, **When** it transitions back to active, **Then** the reactivation counter increments.
3. **Given** I select a time range, **When** the filter applies, **Then** I see reactivation events only for that period.

---

### User Story 6 - Correlate Access Patterns with Decay Scores (Priority: P3)

As a data scientist, I want to compare access patterns against decay score effectiveness so that I can tune the decay algorithm parameters for optimal memory management.

**Why this priority**: Correlation analysis is valuable for algorithm tuning but depends on other panels being available first.

**Independent Test**: Can be fully tested by viewing comparative visualizations that show relationships between access frequency and decay scores.

**Acceptance Scenarios**:

1. **Given** the dashboard is loaded, **When** I view the correlation panel, **Then** I see a visualization comparing access frequency with decay score distributions.
2. **Given** decay parameters are adjusted, **When** I compare before/after periods, **Then** I can assess the impact on access patterns.

---

### Edge Cases

- What happens when no access data exists for a time range? → Display "No data" message with clear indication of the empty period.
- How does system handle metrics with zero values? → Display zero values explicitly rather than omitting the data point.
- What happens when metric collection is temporarily unavailable? → Display last known data with a "data stale" indicator.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Dashboard MUST display access counts grouped by importance level (CRITICAL, HIGH, MEDIUM, LOW).
- **FR-002**: Dashboard MUST display access counts grouped by lifecycle state (ACTIVE, STABLE, DORMANT, ARCHIVED).
- **FR-003**: Dashboard MUST display memory access rate as a time-series visualization.
- **FR-004**: Dashboard MUST display distribution of days since last access across memory population.
- **FR-005**: Dashboard MUST display count of memories reactivated from DORMANT state.
- **FR-006**: Dashboard MUST display count of memories reactivated from ARCHIVED state.
- **FR-007**: Dashboard MUST provide time range selection to filter all panels.
- **FR-008**: Dashboard MUST auto-refresh at configurable intervals.
- **FR-009**: Dashboard MUST provide correlation visualization between access patterns and decay effectiveness.

### Key Entities

- **Memory Access Event**: A record of when a memory was accessed, including timestamp, memory ID, importance level, and lifecycle state at time of access.
- **Reactivation Event**: A record of when a memory transitioned from DORMANT or ARCHIVED back to ACTIVE state due to access.
- **Decay Score**: A calculated value representing memory decay based on time since last access and the configured half-life.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Administrators can identify the most-accessed importance level within 10 seconds of viewing the dashboard.
- **SC-002**: Administrators can determine if reactivations are occurring and at what rate within 30 seconds.
- **SC-003**: Data scientists can identify the median days-since-access for the memory population within 30 seconds.
- **SC-004**: All dashboard panels load and display data within 5 seconds on a standard network connection.
- **SC-005**: Time range filters apply to all panels simultaneously without requiring individual panel configuration.
- **SC-006**: Dashboard provides visual correlation between access frequency and decay score distribution.

## Assumptions

- Metrics `knowledge_access_by_importance_total`, `knowledge_access_by_state_total`, `knowledge_days_since_last_access_bucket`, `knowledge_memory_access_total`, and `knowledge_reactivations_total` are already being collected (per PR #34).
- Dashboard follows the same provisioning pattern as the existing Prompt Cache Effectiveness dashboard (PR #40).
- Default time range is 24 hours with options for 1h, 6h, 12h, 24h, 7d, 30d.
- Auto-refresh default is 30 seconds.

## Dependencies

- PR #34: Access pattern metrics must be collected and available.
- Existing Grafana/Prometheus infrastructure from the knowledge system.
