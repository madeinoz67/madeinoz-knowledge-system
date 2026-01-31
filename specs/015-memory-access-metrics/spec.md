# Feature Specification: Memory Access Metrics

**Feature Branch**: `015-memory-access-metrics`
**Created**: 2026-01-31
**Status**: Draft
**Input**: [GitHub Issue #41](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/41)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Access Distribution by Importance (Priority: P1)

As a knowledge system administrator, I want to see which importance levels (CRITICAL, HIGH, MEDIUM, LOW) are being accessed most frequently, so I can validate that the importance classification aligns with actual usage patterns.

**Why this priority**: Enables validation of the core decay scoring assumption - that important memories are accessed more often. This is the primary value proposition of the memory decay system.

**Independent Test**: Access memories of different importance levels via search, then verify the "Access by Importance" pie chart in the Grafana dashboard shows proportional distribution.

**Acceptance Scenarios**:

1. **Given** a knowledge graph with memories classified as CRITICAL, HIGH, MEDIUM, and LOW importance, **When** I perform searches that return results across all levels, **Then** the dashboard displays access counts for each importance level
2. **Given** the dashboard is showing access by importance, **When** I access only HIGH importance memories repeatedly, **Then** the HIGH segment of the pie chart increases proportionally

---

### User Story 2 - View Access Distribution by Lifecycle State (Priority: P1)

As a knowledge system administrator, I want to see which lifecycle states (ACTIVE, STABLE, DORMANT, ARCHIVED) are being accessed, so I can determine if the decay thresholds are configured appropriately.

**Why this priority**: Invalid decay thresholds cause memories to transition to DORMANT/ARCHIVED too quickly (losing useful content) or too slowly (wasting resources). This is essential for system tuning.

**Independent Test**: Allow memories to age into different states, then access them and verify the "Access by State" pie chart reflects the access patterns.

**Acceptance Scenarios**:

1. **Given** memories in ACTIVE, STABLE, DORMANT, and ARCHIVED states, **When** I perform searches that return results from multiple states, **Then** the dashboard displays access counts for each state
2. **Given** memories have transitioned to DORMANT state, **When** I access one of those memories, **Then** the dashboard shows the reactivation and updates the state distribution

---

### User Story 3 - Monitor Memory Age Distribution (Priority: P2)

As a data scientist analyzing the knowledge system, I want to see a heatmap of when memories were last accessed (time buckets), so I can validate the 180-day half-life setting is appropriate.

**Why this priority**: Provides visibility into whether the decay configuration matches actual usage patterns. Lower priority than the P1 stories which show current state.

**Independent Test**: Generate memory access activity over time, then verify the "Age Distribution" heatmap shows memories clustered in appropriate time buckets.

**Acceptance Scenarios**:

1. **Given** memories with varying last-access timestamps, **When** I view the Age Distribution heatmap, **Then** memories are displayed in time buckets (1d, 1w, 1m, 3m, 6m, 1y, 2y, 3y+)
2. **Given** newly added memories, **When** I access them immediately, **Then** they appear in the 1d bucket of the heatmap

---

### User Story 4 - Track Memory Reactivations (Priority: P2)

As a knowledge system administrator, I want to see how many memories are being reactivated from DORMANT and ARCHIVED states, so I can detect if decay is too aggressive (high reactivations indicate premature state transitions).

**Why this priority**: Reactivation tracking is a leading indicator of decay misconfiguration. High reactivations suggest tuning is needed.

**Independent Test**: Allow memories to transition to DORMANT/ARCHIVED, then access them to trigger reactivation. Verify the reactivation stat panels show the counts.

**Acceptance Scenarios**:

1. **Given** memories in DORMANT state, **When** I access a dormant memory, **Then** the "Reactivations (Dormant)" panel increments by 1
2. **Given** memories in ARCHIVED state, **When** I access an archived memory, **Then** the "Reactivations (Archived)" panel increments by 1
3. **Given** the reactivation threshold is set to yellow=5, **When** 5 dormant memories are reactivated, **Then** the "Reactivations (Dormant)" panel changes from green to yellow background

---

### User Story 5 - Validate Decay Scoring Effectiveness (Priority: P3)

As a knowledge system maintainer, I want to correlate access patterns with decay scores, so I can confirm that high-decay memories are accessed less frequently (validating the scoring model).

**Why this priority**: Provides scientific validation of the decay system but is not essential for day-to-day operations.

**Independent Test**: View the "Access vs Decay Correlation" panel and verify that periods of high access correlate with low average decay scores.

**Acceptance Scenarios**:

1. **Given** a knowledge graph with varying decay scores, **When** I view the correlation panel, **Then** both access rate (left axis) and average decay score (right axis) are displayed
2. **Given** memories with high decay scores, **When** they are accessed, **Then** the correlation panel shows the access spike and corresponding decay score

---

### Edge Cases

- What happens when a memory has never been accessed? (days_since_last_access should be 0 or not exported)
- What happens when a memory transitions from DORMANT to ARCHIVED without being accessed? (no reactivation metric increment)
- What happens when the system restarts with counter metrics? (counters reset to 0, which is expected Prometheus behavior)
- What happens when a memory is accessed but has no importance label? (metric not incremented or labeled as "UNKNOWN")
- What happens when histogram bucket boundaries are exceeded? (value goes into +Inf bucket)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST export `knowledge_access_by_importance_total` counter metric with `level` label (CRITICAL, HIGH, MEDIUM, LOW)
- **FR-002**: System MUST export `knowledge_access_by_state_total` counter metric with `state` label (ACTIVE, STABLE, DORMANT, ARCHIVED)
- **FR-003**: System MUST export `knowledge_days_since_last_access_bucket` histogram metric with bucket boundaries [1, 7, 30, 90, 180, 365, 730, 1095] days
- **FR-004**: System MUST export `knowledge_reactivations_total` counter metric with `from_state` label (DORMANT, ARCHIVED)
- **FR-005**: System MUST increment access-by-importance counter when a memory is returned in search results
- **FR-006**: System MUST increment access-by-state counter when a memory is returned in search results
- **FR-007**: System MUST record days-since-last-access when a memory is returned in search results
- **FR-008**: System MUST increment reactivation counter when a memory transitions from DORMANT/ARCHIVED to ACTIVE
- **FR-009**: Metrics MUST be visible at the `/metrics` endpoint on port 9091 (dev) or 9090 (production)
- **FR-010**: Dashboard panels MUST display data when metrics are populated

### Key Entities

- **Memory Access Event**: A single access of a memory (via search), characterized by the memory's importance level, lifecycle state, and days since last access
- **Reactivation Event**: A transition from DORMANT or ARCHIVED state back to ACTIVE, indicating the decay system may have been too aggressive
- **Metric Labels**:
  - `level`: CRITICAL, HIGH, MEDIUM, LOW (importance classification)
  - `state`: ACTIVE, STABLE, DORMANT, ARCHIVED (lifecycle state)
  - `from_state`: DORMANT, ARCHIVED (previous state before reactivation)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All four new metrics appear in the Prometheus metrics endpoint with correct labels and types
- **SC-002**: Dashboard "Access by Importance" panel shows data after performing searches that return results
- **SC-003**: Dashboard "Access by State" panel shows data after performing searches that return results
- **SC-004**: Dashboard "Age Distribution" heatmap shows data after memories are accessed
- **SC-005**: Dashboard "Reactivations" stat panels increment when memories are reactivated from DORMANT/ARCHIVED states
- **SC-006**: Reactivation panels show color thresholds (green/yellow/red) at configured values

## Assumptions

- The Memory Access Patterns dashboard (feature #37 / PR #42) is already deployed and waiting for these metrics
- The existing `knowledge_memory_access_total` metric provides the base access counter pattern to follow
- OpenTelemetry meter API is used for metrics export (consistent with existing code)
- Search operations are the primary method of memory access (direct memory retrieval is not counted)
- Importance and state labels are already assigned to memories by existing classification/decay systems

## Dependencies

- **Feature #37 (Memory Access Patterns Dashboard)**: Requires these metrics to display data
- **Feature #009 (Memory Decay Scoring)**: Provides importance classification and lifecycle state transitions
- **Feature #006 (Gemini Prompt Caching)**: N/A - independent feature
- **Metrics Exporter**: `docker/patches/metrics_exporter.py` - where new metrics will be defined

## Out of Scope

- Modifying the dashboard configuration (already complete in feature #37)
- Changing importance or state classification logic (feature #009)
- Adding new lifecycle states or importance levels
- Persisting historical metrics data (Prometheus handles this)
- Alerting on metric values (can be added later as separate feature)
