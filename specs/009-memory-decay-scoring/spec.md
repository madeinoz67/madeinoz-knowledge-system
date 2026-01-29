# Feature Specification: Memory Decay Scoring and Importance Classification

**Feature Branch**: `009-memory-decay-scoring`
**Created**: 2026-01-29
**Status**: Draft
**Input**: User description: "Implement memory decay scoring and importance classification for the Knowledge system based on PAI Memory System concepts"

## Overview

This feature adds memory decay scoring, importance classification, and lifecycle management to the Knowledge system. Based on research from PAI Memory System concepts (validated by Zep/Graphiti architecture, MemOS, Mem0, and A-MEM NeurIPS 2025), these enhancements enable the system to prioritize relevant memories, forget stale information, and maintain sustainable graph growth while leveraging the existing bi-temporal model.

## Clarifications

### Session 2026-01-29

- Q: What is the acceptable time window for maintenance completion? → A: 10 minutes maximum
- Q: What happens if LLM is unavailable during classification? → A: Assign neutral defaults (importance=3, stability=3) and queue for re-classification
- Q: What should happen to memories that reach EXPIRED state by default? → A: Soft-delete (mark as deleted but retain in graph for 90 days, allowing recovery; permanent deletion requires explicit admin action)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Relevance-Weighted Search Results (Priority: P1)

As a user searching my knowledge graph, I want search results ranked by a combination of semantic relevance, recency, and importance so that the most useful memories appear first, not just the most semantically similar ones.

**Why this priority**: This is the core value proposition - without relevance-weighted retrieval, the system cannot prioritize important or recent memories over stale ones. Every search operation benefits from this capability.

**Independent Test**: Can be fully tested by performing a search and verifying results are ordered by weighted score (semantic + recency + importance) rather than semantic similarity alone.

**Acceptance Scenarios**:

1. **Given** a knowledge graph with memories of varying ages and importance levels, **When** I search for a topic, **Then** results are ranked by weighted score combining semantic relevance, recency, and importance.
2. **Given** two memories with equal semantic similarity, **When** one is more recent and important, **Then** that memory ranks higher in results.
3. **Given** an old but highly important memory, **When** compared to a recent but trivial memory, **Then** the important memory maintains competitive ranking despite age.

---

### User Story 2 - Importance and Stability Scoring at Ingestion (Priority: P1)

As a user adding new knowledge, I want the system to automatically classify each memory's importance (how critical to my identity/work) and stability (how likely to change) so that memories are properly prioritized for retention and retrieval.

**Why this priority**: Classification at ingestion is foundational - all other features (decay, lifecycle, retrieval weighting) depend on having importance and stability scores assigned to memories.

**Independent Test**: Can be fully tested by adding a memory and verifying importance and stability scores are assigned and stored in the knowledge graph.

**Acceptance Scenarios**:

1. **Given** I add a memory about a permanent fact (e.g., "I am allergic to shellfish"), **When** the memory is ingested, **Then** it is classified with high importance (4-5) and high stability (4-5).
2. **Given** I add a memory about a temporary state (e.g., "Working on payment feature this sprint"), **When** the memory is ingested, **Then** it is classified with moderate importance (2-3) and low stability (1-2).
3. **Given** I add a memory about a personal preference (e.g., "Prefers TypeScript over JavaScript"), **When** the memory is ingested, **Then** it is classified with moderate importance (3) and moderate-high stability (3-4).

---

### User Story 3 - Memory Decay Over Time (Priority: P2)

As a system administrator, I want memories to accumulate decay scores over time based on their importance and access patterns so that stale, unimportant memories naturally lose relevance without manual intervention.

**Why this priority**: Decay enables sustainable graph growth by preventing unbounded accumulation. It's a natural extension of importance scoring but not strictly required for initial value delivery.

**Independent Test**: Can be fully tested by adding memories, waiting for decay calculation to run, and verifying decay scores increase for unused low-importance memories.

**Acceptance Scenarios**:

1. **Given** a memory with low importance (1-2) and low stability (1-2), **When** it has not been accessed for 30 days, **Then** its decay score indicates significant relevance reduction.
2. **Given** a memory with high importance (4-5), **When** any amount of time passes without access, **Then** its decay score remains minimal or zero (never decays).
3. **Given** a memory is accessed (via search result click or explicit retrieval), **When** the access is recorded, **Then** the memory's last access timestamp is updated and decay score resets.

---

### User Story 4 - Memory Lifecycle State Management (Priority: P2)

As a user, I want my memories to transition through defined lifecycle states (Active, Dormant, Archived, Expired, Soft-Deleted) based on their usage and decay so that I can understand and manage my knowledge graph health.

**Why this priority**: Lifecycle states provide visibility into memory health and enable automated cleanup, but the core value (weighted retrieval) can work without explicit state management.

**Independent Test**: Can be fully tested by verifying memories transition through states based on access patterns and decay thresholds.

**Acceptance Scenarios**:

1. **Given** a newly added memory, **When** it is ingested, **Then** it starts in the ACTIVE state.
2. **Given** an active memory with moderate importance, **When** it has not been accessed for 30 days, **Then** it transitions to DORMANT state.
3. **Given** a dormant memory with low importance, **When** it has not been accessed for 90 days, **Then** it transitions to ARCHIVED state.
4. **Given** an archived memory, **When** it is accessed via search, **Then** it transitions back to ACTIVE state.
5. **Given** an expired memory, **When** maintenance runs, **Then** it transitions to SOFT_DELETED state with a 90-day retention window.
6. **Given** a soft-deleted memory within 90 days, **When** an admin recovers it, **Then** it transitions to ARCHIVED state for re-evaluation.

---

### User Story 5 - Maintenance and Health Reporting (Priority: P3)

As a system administrator, I want automated nightly maintenance that recalculates decay scores and generates health reports so that the knowledge graph remains performant without manual intervention.

**Why this priority**: Maintenance automation is important for long-term sustainability but can be deferred until core features are validated.

**Independent Test**: Can be fully tested by running the maintenance process and verifying decay scores are updated and health metrics are generated.

**Acceptance Scenarios**:

1. **Given** a scheduled maintenance window, **When** the nightly job runs, **Then** all memory decay scores are recalculated based on current timestamps.
2. **Given** maintenance completes, **When** I request a health report, **Then** I see counts of memories by state (Active, Dormant, Archived, Expired) and average decay scores.
3. **Given** memories in the Expired state, **When** maintenance runs, **Then** expired memories are soft-deleted (marked deleted, retained 90 days for recovery, permanent deletion requires admin action).

---

### Edge Cases

- What happens when a memory has conflicting importance signals (explicitly marked important but rarely accessed)?
  - Explicit importance takes precedence; access patterns only influence decay, not base importance.

- How does the system handle bulk imports with thousands of memories?
  - Importance classification runs asynchronously; initial ingestion assigns default scores that are refined by background processing.

- What happens when the decay calculation service is unavailable?
  - Retrieval continues using last-known decay scores; stale scores are flagged for recalculation on next maintenance run.

- How are memories with high importance and stability protected from accidental archival?
  - Memories with importance >= 4 AND stability >= 4 are classified as PERMANENT and exempt from decay transitions.

- What happens to soft-deleted memories after 90 days?
  - Soft-deleted memories are permanently removed after 90 days unless recovered. Recovery restores the memory to ARCHIVED state for re-evaluation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST assign importance scores (1-5) to each memory at ingestion time, where 1=trivial and 5=core identity.
- **FR-002**: System MUST assign stability scores (1-5) to each memory at ingestion time, where 1=changes frequently and 5=permanent.
- **FR-003**: System MUST calculate decay scores for all non-permanent memories based on time since last access.
- **FR-004**: System MUST use weighted scoring for search results combining semantic relevance, recency, and importance.
- **FR-005**: System MUST track last access timestamp for each memory when it is retrieved via search.
- **FR-006**: System MUST support five memory lifecycle states: ACTIVE, DORMANT, ARCHIVED, EXPIRED, SOFT_DELETED.
- **FR-007**: System MUST transition memories between lifecycle states based on configured decay thresholds.
- **FR-008**: System MUST exempt memories with importance >= 4 AND stability >= 4 from decay transitions (PERMANENT classification).
- **FR-009**: System MUST provide a maintenance process that recalculates decay scores for all memories.
- **FR-010**: System MUST provide health metrics showing memory counts by lifecycle state.
- **FR-011**: System MUST re-activate (transition to ACTIVE) any archived or dormant memory that is accessed.
- **FR-012**: System MUST soft-delete expired memories (mark deleted, retain 90 days) rather than hard-delete by default.
- **FR-013**: System MUST provide admin capability to recover soft-deleted memories within the 90-day retention period.

### Key Entities

- **Memory Node**: Extended with importance (1-5), stability (1-5), decay_score (0.0-1.0), lifecycle_state (ACTIVE|DORMANT|ARCHIVED|EXPIRED|SOFT_DELETED), last_accessed_at (timestamp), access_count (integer), soft_deleted_at (timestamp, nullable).
- **Memory Edge**: Extended with importance and stability scores for relationship-level classification.
- **Decay Configuration**: Decay rate, state transition thresholds, permanent classification rules.
- **Health Metrics**: Aggregate counts by state, average decay scores, memory age distribution.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users find relevant information 40% faster compared to pure semantic search (measured by clicks to find target memory).
- **SC-002**: Knowledge graph storage growth rate reduced by 30% through automated archival of stale memories.
- **SC-003**: 95% of search queries return results weighted by importance within the same response time as current semantic search (no performance degradation).
- **SC-004**: Users report high confidence (4+ out of 5) that important memories are prioritized in search results.
- **SC-005**: Maintenance process completes within 10 minutes without impacting system availability.
- **SC-006**: Zero permanent memories (importance >= 4, stability >= 4) incorrectly archived or expired.

## Observability Metrics

### Prometheus Metrics

The decay system exposes metrics for monitoring via Prometheus scraping.

#### Counter Metrics

| Metric | Labels | Description |
|--------|--------|-------------|
| `knowledge_decay_maintenance_runs_total` | `status` (success\|failure) | Total maintenance runs |
| `knowledge_decay_scores_updated_total` | - | Cumulative decay scores recalculated |
| `knowledge_lifecycle_transitions_total` | `from_state`, `to_state` | State transition counts |
| `knowledge_memories_purged_total` | - | Soft-deleted memories permanently removed |
| `knowledge_classification_requests_total` | `status` (success\|fallback\|error) | LLM classification attempts |

#### Gauge Metrics

| Metric | Labels | Description |
|--------|--------|-------------|
| `knowledge_memories_by_state` | `state` (ACTIVE\|DORMANT\|ARCHIVED\|EXPIRED\|SOFT_DELETED\|PERMANENT) | Current count per lifecycle state |
| `knowledge_decay_score_avg` | - | Average decay score across all non-permanent memories |
| `knowledge_importance_avg` | - | Average importance score |
| `knowledge_stability_avg` | - | Average stability score |
| `knowledge_memories_total` | - | Total memory count (excluding soft-deleted) |

#### Histogram Metrics

| Metric | Buckets | Description |
|--------|---------|-------------|
| `knowledge_maintenance_duration_seconds` | 1, 5, 30, 60, 120, 300, 600 | Maintenance run duration |
| `knowledge_classification_latency_seconds` | 0.1, 0.5, 1, 2, 5 | LLM classification response time |
| `knowledge_search_weighted_latency_seconds` | 0.01, 0.05, 0.1, 0.5, 1 | Weighted search scoring overhead |

### Health Check Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health/decay` | GET | Decay system status (last maintenance, next scheduled) |
| `/metrics` | GET | Prometheus metrics endpoint |

### Logging Patterns

All decay operations use structured JSON logging with consistent fields:

```json
{
  "timestamp": "ISO8601",
  "level": "INFO|WARN|ERROR",
  "component": "decay|lifecycle|maintenance|classifier",
  "operation": "calculate|transition|classify|purge",
  "memory_uuid": "optional",
  "duration_ms": "optional",
  "details": {}
}
```

#### Key Log Events

| Component | Operation | Level | Trigger |
|-----------|-----------|-------|---------|
| maintenance | start | INFO | Maintenance run begins |
| maintenance | complete | INFO | Maintenance run finishes |
| maintenance | timeout | WARN | Maintenance exceeds 10-minute limit |
| lifecycle | transition | INFO | Any state change |
| lifecycle | reactivate | INFO | DORMANT/ARCHIVED → ACTIVE on access |
| classifier | fallback | WARN | LLM unavailable, using defaults |
| classifier | error | ERROR | Classification failed completely |

### Dashboard Requirements

The health report MCP tool (`get_knowledge_health`) provides data for dashboards:

1. **State Distribution**: Pie chart showing memories by lifecycle state
2. **Decay Trend**: Line chart of average decay score over time
3. **Age Distribution**: Bar chart of memories by age bucket (7d, 30d, 90d, 90d+)
4. **Maintenance History**: Table of last 10 maintenance runs with duration/counts
5. **Classification Quality**: Success/fallback/error ratio over time

### Alerting Rules

| Alert | Condition | Severity |
|-------|-----------|----------|
| `MaintenanceTimeout` | Maintenance duration > 10 minutes | Warning |
| `MaintenanceFailed` | Maintenance status = failure | Critical |
| `ClassificationDegraded` | Fallback rate > 20% in 1 hour | Warning |
| `ExcessiveExpiration` | > 100 memories expired in single run | Warning |
| `PermanentMemoryArchived` | Any permanent memory transitions out of ACTIVE | Critical |

## Assumptions

- The existing Graphiti bi-temporal model (t_valid, t_invalid) provides the foundation for temporal tracking.
- Importance and stability scores can be reliably inferred by the LLM during ingestion using established patterns.
- Users accept that automated classification may occasionally require manual correction.
- Decay calculations can run asynchronously without blocking user operations.
- The decay rate is a sensible default based on production implementations (Mem0, MemOS).

## Out of Scope

- User interface for manually adjusting importance/stability scores (future enhancement).
- Real-time decay recalculation on every query (batch processing only).
- Machine learning model training for custom importance prediction.
- Integration with external calendar/task systems for context-aware importance.
