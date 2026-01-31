# Data Model: Memory Decay Scoring and Importance Classification

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)
**Date**: 2026-01-29
**Status**: Draft

## Overview

This document defines the data model extensions for memory decay scoring. All new fields are stored in the existing Graphiti `attributes` dictionary to avoid library modifications.

---

## Extended Entity Schema

### Memory Node (EntityNode Extension)

Graphiti's `EntityNode` extended with decay tracking via `attributes`:

```python
@dataclass
class MemoryDecayAttributes:
    """Decay-related attributes stored in EntityNode.attributes"""

    # Classification (assigned at ingestion)
    importance: int          # 1-5, where 1=trivial, 5=core identity
    stability: int           # 1-5, where 1=volatile, 5=permanent

    # Decay tracking (calculated by maintenance)
    decay_score: float       # 0.0-1.0, where 0=fresh, 1=fully decayed
    lifecycle_state: str     # ACTIVE|DORMANT|ARCHIVED|EXPIRED|SOFT_DELETED

    # Access tracking (updated on retrieval)
    last_accessed_at: str    # ISO 8601 timestamp
    access_count: int        # Total access count

    # Soft-delete tracking
    soft_deleted_at: str | None  # ISO 8601 timestamp when soft-deleted
```

**Neo4j Property Mapping**:

| Python Field | Neo4j Property | Type | Index |
|--------------|----------------|------|-------|
| importance | `attributes.importance` | Integer | - |
| stability | `attributes.stability` | Integer | - |
| decay_score | `attributes.decay_score` | Float | - |
| lifecycle_state | `attributes.lifecycle_state` | String | Yes (for filtering) |
| last_accessed_at | `attributes.last_accessed_at` | String | - |
| access_count | `attributes.access_count` | Integer | - |
| soft_deleted_at | `attributes.soft_deleted_at` | String | - |

---

## Enumerations

### ImportanceLevel

```python
class ImportanceLevel(IntEnum):
    """Memory importance classification"""
    TRIVIAL = 1       # Ephemeral, can forget quickly
    LOW = 2           # Useful but replaceable
    MODERATE = 3      # Default, general knowledge
    HIGH = 4          # Important to work/identity
    CORE = 5          # Fundamental, never forget

    @classmethod
    def permanent_threshold(cls) -> int:
        return cls.HIGH  # 4
```

**Examples by Level**:

| Level | Example Content |
|-------|-----------------|
| 1 - TRIVIAL | "User mentioned the weather" |
| 2 - LOW | "Working on payment feature this sprint" |
| 3 - MODERATE | "Prefers TypeScript over JavaScript" |
| 4 - HIGH | "Senior engineer at Acme Corp" |
| 5 - CORE | "Allergic to shellfish" |

### StabilityLevel

```python
class StabilityLevel(IntEnum):
    """Memory stability/volatility classification"""
    VOLATILE = 1      # Changes frequently (hours/days)
    LOW = 2           # Changes regularly (days/weeks)
    MODERATE = 3      # Changes occasionally (weeks/months)
    HIGH = 4          # Rarely changes (months/years)
    PERMANENT = 5     # Never changes (facts, identity)

    @classmethod
    def permanent_threshold(cls) -> int:
        return cls.HIGH  # 4
```

**Examples by Level**:

| Level | Example Content |
|-------|-----------------|
| 1 - VOLATILE | "Current task: debugging auth" |
| 2 - LOW | "Sprint goal: complete payments" |
| 3 - MODERATE | "Tech stack: Python + Neo4j" |
| 4 - HIGH | "Works at Acme Corp" |
| 5 - PERMANENT | "Born in Sydney, Australia" |

### LifecycleState

```python
class LifecycleState(str, Enum):
    """Memory lifecycle states"""
    ACTIVE = "ACTIVE"           # Recently accessed, full relevance
    DORMANT = "DORMANT"         # Not accessed 30+ days
    ARCHIVED = "ARCHIVED"       # Not accessed 90+ days, low priority
    EXPIRED = "EXPIRED"         # Marked for deletion
    SOFT_DELETED = "SOFT_DELETED"  # Deleted, in 90-day recovery window
```

**State Transition Diagram**:

```
                    access
    ┌─────────────────────────────────────────┐
    │                                         │
    ▼                                         │
┌───────┐   30 days   ┌─────────┐   90 days   ├──────────┐
│ACTIVE │────────────▶│ DORMANT │────────────▶│ ARCHIVED │
└───────┘             └─────────┘             └──────────┘
    ▲                     │                       │
    │                     │ access                │ 180 days
    │                     ▼                       │ importance < 3
    │                 ┌───────┐                   ▼
    │                 │ACTIVE │◀──────────────┌─────────┐
    │                 └───────┘    access     │ EXPIRED │
    │                                         └─────────┘
    │                                              │
    │                                              │ maintenance
    │                                              ▼
    │                                        ┌─────────────┐
    │◀───────────────────────────────────────│SOFT_DELETED │
         admin recover                       └─────────────┘
                                                   │
                                                   │ 90 days
                                                   ▼
                                              (permanent delete)
```

---

## Classification Rules

### Permanent Memory Classification

Memories with `importance >= 4 AND stability >= 4` are classified as PERMANENT:

```python
def is_permanent(importance: int, stability: int) -> bool:
    """Check if memory qualifies as permanent (exempt from decay)"""
    return importance >= 4 and stability >= 4
```

**Permanent memories**:
- Never accumulate decay score (always 0.0)
- Never transition states (always ACTIVE)
- Not subject to archival or deletion

### Default Classification

When LLM classification fails or is unavailable:

```python
DEFAULT_IMPORTANCE = 3  # MODERATE
DEFAULT_STABILITY = 3   # MODERATE
```

---

## Decay Configuration

### DecayConfig

```python
@dataclass
class DecayConfig:
    """Configuration for decay calculation"""

    # Base half-life in days (adjusted by stability)
    # 180 days provides better retention for personal knowledge graphs
    base_half_life_days: float = 180.0

    # State transition thresholds (days since last access)
    dormant_threshold_days: int = 30
    archived_threshold_days: int = 90
    expired_threshold_days: int = 180

    # Decay score thresholds for transitions
    dormant_decay_threshold: float = 0.3
    archived_decay_threshold: float = 0.6
    expired_decay_threshold: float = 0.9

    # Soft-delete retention period
    soft_delete_retention_days: int = 90

    # Minimum importance for expired transition
    expired_importance_threshold: int = 3

    # Batch processing
    maintenance_batch_size: int = 500
```

### YAML Configuration File

`config/decay-config.yaml`:

```yaml
decay:
  # 180-day half-life: memories reach 50% decay after 6 months
  base_half_life_days: 180

  thresholds:
    dormant:
      days: 90            # Min days + decay >= 0.3 (~93 days actual)
      decay_score: 0.3
    archived:
      days: 180           # Min days + decay >= 0.6 (~238 days actual)
      decay_score: 0.6
    expired:
      days: 360           # Min days + decay >= 0.9 (~598 days actual)
      decay_score: 0.9
      max_importance: 3   # Only expire if importance <= 3

  retention:
    soft_delete_days: 90

  maintenance:
    batch_size: 500
    max_duration_minutes: 10
    schedule_interval_hours: 24  # Run daily

  weights:
    semantic: 0.60
    recency: 0.25
    importance: 0.15
```

---

## Health Metrics

### KnowledgeHealthMetrics

```python
@dataclass
class KnowledgeHealthMetrics:
    """Health report for knowledge graph"""

    # Counts by lifecycle state
    active_count: int
    dormant_count: int
    archived_count: int
    expired_count: int
    soft_deleted_count: int
    permanent_count: int  # importance >= 4 AND stability >= 4

    # Aggregates
    total_memories: int
    average_decay_score: float
    average_importance: float
    average_stability: float

    # Age distribution (aligned with lifecycle thresholds: 30/90/180/365 days)
    memories_under_7_days: int
    memories_7_to_30_days: int
    memories_30_to_90_days: int
    memories_90_to_180_days: int
    memories_180_to_365_days: int
    memories_over_365_days: int

    # Maintenance info
    last_maintenance_at: str  # ISO timestamp
    maintenance_duration_seconds: float
    memories_processed: int
    state_transitions: int

    # Timestamp
    generated_at: str  # ISO timestamp
```

**JSON Response Format**:

```json
{
  "states": {
    "active": 1250,
    "dormant": 340,
    "archived": 180,
    "expired": 25,
    "soft_deleted": 12,
    "permanent": 45
  },
  "aggregates": {
    "total": 1852,
    "average_decay": 0.23,
    "average_importance": 3.1,
    "average_stability": 3.4
  },
  "age_distribution": {
    "under_7_days": 89,
    "7_to_30_days": 412,
    "30_to_90_days": 651,
    "90_to_180_days": 420,
    "180_to_365_days": 180,
    "over_365_days": 100
  },
  "maintenance": {
    "last_run": "2026-01-29T03:00:00Z",
    "duration_seconds": 245.3,
    "processed": 1852,
    "transitions": 47
  },
  "generated_at": "2026-01-29T12:34:56Z"
}
```

---

## Neo4j Indexes

Required indexes for efficient queries:

```cypher
-- Lifecycle state index for filtering
CREATE INDEX memory_lifecycle_state IF NOT EXISTS
FOR (n:Entity)
ON (n.`attributes.lifecycle_state`);

-- Composite index for maintenance queries
CREATE INDEX memory_decay_composite IF NOT EXISTS
FOR (n:Entity)
ON (n.`attributes.lifecycle_state`, n.`attributes.importance`);
```

---

## Migration Path

### Initial Backfill Query

For existing memories without decay attributes:

```cypher
MATCH (n:Entity)
WHERE n.`attributes.importance` IS NULL

SET n.`attributes.importance` = 3,
    n.`attributes.stability` = 3,
    n.`attributes.decay_score` = 0.0,
    n.`attributes.lifecycle_state` = 'ACTIVE',
    n.`attributes.last_accessed_at` = toString(n.created_at),
    n.`attributes.access_count` = 0,
    n.`attributes.soft_deleted_at` = null

RETURN count(n) AS backfilled
```

---

## Observability Metrics

### PrometheusMetrics

```python
@dataclass
class PrometheusMetricsConfig:
    """Configuration for Prometheus metrics export"""

    # Metrics server
    port: int = 9090
    host: str = "0.0.0.0"

    # Metric prefixes
    namespace: str = "knowledge"
    subsystem: str = "decay"

    # Histogram buckets
    maintenance_duration_buckets: tuple = (1, 5, 30, 60, 120, 300, 600)
    classification_latency_buckets: tuple = (0.1, 0.5, 1, 2, 5)
    search_latency_buckets: tuple = (0.01, 0.05, 0.1, 0.5, 1)
```

### Metric Definitions

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `knowledge_decay_maintenance_runs_total` | Counter | status | Total maintenance runs |
| `knowledge_decay_scores_updated_total` | Counter | - | Cumulative decay scores recalculated |
| `knowledge_lifecycle_transitions_total` | Counter | from_state, to_state | State transition counts |
| `knowledge_memories_purged_total` | Counter | - | Soft-deleted permanently removed |
| `knowledge_classification_requests_total` | Counter | status | LLM classification attempts |
| `knowledge_memories_by_state` | Gauge | state | Current count per lifecycle state |
| `knowledge_decay_score_avg` | Gauge | - | Average decay score |
| `knowledge_importance_avg` | Gauge | - | Average importance score |
| `knowledge_stability_avg` | Gauge | - | Average stability score |
| `knowledge_memories_total` | Gauge | - | Total memory count |
| `knowledge_maintenance_duration_seconds` | Histogram | - | Maintenance run duration |
| `knowledge_classification_latency_seconds` | Histogram | - | LLM classification response time |
| `knowledge_search_weighted_latency_seconds` | Histogram | - | Weighted search scoring overhead |

### Label Values

**status** (Counter labels):
- `success` - Operation completed successfully
- `failure` - Operation failed with error
- `fallback` - Operation used fallback behavior (e.g., default classification)

**state** (Gauge labels):
- `ACTIVE` - Recently accessed memories
- `DORMANT` - Not accessed 30+ days
- `ARCHIVED` - Not accessed 90+ days
- `EXPIRED` - Marked for deletion
- `SOFT_DELETED` - In 90-day recovery window
- `PERMANENT` - Exempt from decay (importance >= 4 AND stability >= 4)

**from_state / to_state** (Transition labels):
- Same values as state labels
- Used to track specific transition patterns

### Alert Rules (Prometheus)

```yaml
# prometheus/alerts/knowledge.yml
groups:
  - name: knowledge_decay
    rules:
      - alert: MaintenanceTimeout
        expr: knowledge_maintenance_duration_seconds > 600
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: Knowledge maintenance exceeded 10-minute timeout

      - alert: MaintenanceFailed
        expr: increase(knowledge_decay_maintenance_runs_total{status="failure"}[1h]) > 0
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: Knowledge maintenance failed

      - alert: ClassificationDegraded
        expr: |
          rate(knowledge_classification_requests_total{status="fallback"}[1h])
          / rate(knowledge_classification_requests_total[1h]) > 0.2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: LLM classification fallback rate exceeds 20%

      - alert: ExcessiveExpiration
        expr: increase(knowledge_lifecycle_transitions_total{to_state="EXPIRED"}[1h]) > 100
        for: 0m
        labels:
          severity: warning
        annotations:
          summary: More than 100 memories expired in last hour
```

---

### Classification Queue

New memories without LLM classification are queued for async processing:

```python
CLASSIFICATION_QUEUE_KEY = "decay:classification:pending"

# Add to queue on ingestion failure
await redis.lpush(CLASSIFICATION_QUEUE_KEY, memory_uuid)

# Process queue in maintenance
while uuid := await redis.rpop(CLASSIFICATION_QUEUE_KEY):
    await classify_memory(uuid)
```
