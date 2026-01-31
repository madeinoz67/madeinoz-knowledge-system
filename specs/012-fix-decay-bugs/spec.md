# Feature Specification: Fix Decay Calculation Bugs

**Feature Branch**: `012-fix-decay-bugs`
**Created**: 2026-01-31
**Status**: Draft
**Input**: User description: "Fix all bugs in https://github.com/madeinoz67/madeinoz-knowledge-system/issues/26"
**Related Issue**: [GitHub Issue #26](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/26)

## Problem Statement

The memory decay scoring system has three bugs causing incorrect decay calculations and misleading monitoring data:

1. **Config Path Mismatch**: The decay configuration file (180-day half-life) is not being loaded, causing the system to use the code default (30-day half-life), resulting in 6x faster decay than intended.

2. **Stale Prometheus Metrics**: After maintenance runs, the `knowledge_decay_score_avg` metric is not refreshed, showing stale values that don't reflect actual database state.

3. **Timestamp NULL Handling**: The decay calculation query may fail silently when Entity nodes have NULL timestamps.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Correct Decay Configuration Loading (Priority: P1)

As a system administrator, I want the decay configuration to be properly loaded so that memories decay at the intended rate (180-day half-life) rather than the faster default rate (30-day half-life).

**Why this priority**: This is the core bug - incorrect decay rate affects all knowledge retention. Without this fix, memories are expiring 6x faster than designed.

**Independent Test**: Can be fully tested by checking decay scores after adding new episodes and verifying they match the 180-day half-life calculation.

**Acceptance Scenarios**:

1. **Given** the system starts with `config/decay-config.yaml` specifying 180-day half-life, **When** decay scores are calculated, **Then** a 2-day-old memory with moderate importance should show approximately 0.46% decay (not 2.7%).

2. **Given** the decay configuration file exists in the container image, **When** the container starts, **Then** the configuration should be copied to the expected location and loaded successfully.

3. **Given** the system logs startup information, **When** the container starts, **Then** logs should indicate "Loaded decay config from [path]" (not "using defaults").

---

### User Story 2 - Accurate Prometheus Metrics (Priority: P2)

As a system operator, I want the monitoring metrics to reflect the current system state so that dashboards show accurate information.

**Why this priority**: Stale metrics lead to false alerts and incorrect operational decisions. This is critical for production monitoring.

**Independent Test**: Can be tested by running maintenance, then querying the metrics endpoint and comparing to direct queries.

**Acceptance Scenarios**:

1. **Given** maintenance has just completed and updated decay scores, **When** the metrics endpoint is queried, **Then** `knowledge_decay_score_avg` should match the actual average.

2. **Given** episodes are added after server startup, **When** maintenance runs, **Then** the metric gauges should update to reflect the new state.

3. **Given** the maintenance service logs completion, **When** checking logs, **Then** there should be an entry indicating gauge metrics were refreshed.

---

### User Story 3 - Robust Timestamp Handling (Priority: P3)

As a developer, I want the decay calculation to handle NULL timestamps gracefully so that edge cases don't cause silent calculation failures.

**Why this priority**: Diagnostic data shows timestamps are currently parsing correctly, so this is defensive hardening rather than an active bug fix.

**Independent Test**: Can be tested by creating Entity nodes with NULL timestamps and verifying decay calculation doesn't fail.

**Acceptance Scenarios**:

1. **Given** an Entity node with NULL `last_accessed_at` and NULL `created_at`, **When** decay score is calculated, **Then** the system should use a default value (0 days) rather than failing.

2. **Given** an Entity node with only `created_at` set (no `last_accessed_at`), **When** decay score is calculated, **Then** the calculation should use `created_at` as the reference.

3. **Given** an Entity node with only `last_accessed_at` set, **When** decay score is calculated, **Then** the calculation should use `last_accessed_at` correctly.

---

### Edge Cases

- What happens when the decay config file is missing entirely? (Should log warning and use defaults)
- What happens when the config file has invalid format? (Should fail startup with clear error)
- What happens when maintenance times out during gauge refresh? (Should log warning but not fail maintenance)
- What happens when the database is temporarily unavailable during gauge refresh? (Should handle gracefully)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST copy decay configuration file to the expected location during container startup
- **FR-002**: System MUST load decay configuration from the file (180-day half-life) instead of using code defaults (30-day half-life)
- **FR-003**: System MUST refresh monitoring gauge metrics after each maintenance cycle completes
- **FR-004**: System MUST handle NULL timestamps in decay calculation without silent failures
- **FR-005**: System MUST log when decay configuration is loaded, including the source path and key values
- **FR-006**: System MUST log when gauge metrics are refreshed after maintenance
- **FR-007**: System MUST NOT fail maintenance if gauge refresh encounters an error (graceful degradation)

### Key Entities

- **Entity Node**: Knowledge graph node with decay-related attributes (`decay_score`, `last_accessed_at`, `created_at`, `importance`, `stability`, `lifecycle_state`)
- **Decay Configuration**: Configuration file containing `base_half_life_days`, thresholds, and weight settings
- **Monitoring Metrics**: Gauge metrics including average decay score, memory counts by state, and average importance/stability

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Decay scores for 2-day-old moderate-importance memories should be approximately 0.46% (within 0.1% tolerance) when using the configured 180-day half-life
- **SC-002**: Monitoring `knowledge_decay_score_avg` metric matches actual average within 1% after maintenance completes
- **SC-003**: Container startup logs indicate successful configuration loading from the expected path
- **SC-004**: No silent failures occur when Entity nodes have NULL timestamp values (verified by test coverage)
- **SC-005**: System correctly calculates decay for 100% of Entity nodes regardless of timestamp state

## Assumptions

- The existing decay calculation formula is mathematically correct (verified by diagnostic data)
- Timestamp parsing works correctly for properly formatted values (verified by diagnostic data showing correct `calculated_days`)
- The 180-day half-life is the intended configuration (specified in `config/decay-config.yaml`)
- Monitoring metrics are consumed by external systems that rely on accurate values

## Dependencies

- Existing decay scoring implementation (Feature 009)
- Container build and deployment process
- Metrics exporter infrastructure

## Out of Scope

- Changes to the decay calculation formula itself
- Changes to the half-life value in the configuration
- New monitoring metrics
- Changes to the maintenance scheduling interval
