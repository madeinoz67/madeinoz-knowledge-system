# Research: Memory Decay Scoring and Importance Classification

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)
**Date**: 2026-01-29
**Status**: Complete

## Executive Summary

Research confirms the memory decay scoring feature is implementable using Graphiti's existing `attributes` dictionary for custom fields, Neo4j vector search with post-processing for weighted scoring, and exponential decay formulas with configurable half-life. All technical approaches align with the project's constitution principles.

---

## Research Questions

### RQ1: How to Extend Graphiti Nodes with Custom Fields?

**Decision**: Use the built-in `attributes` dictionary on EntityNode and EntityEdge.

**Rationale**:
- Graphiti provides `attributes: dict[str, Any]` on both node types specifically for custom properties
- Works immediately without library modifications
- Properties persist directly to Neo4j and are Cypher-queryable
- Custom Pydantic entity types have known issues (GitHub #567) with label persistence

**Alternatives Considered**:

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| `attributes` dict | Works now, no mods | No Pydantic validation | **Chosen** |
| Custom entity types | Type safety | Known bugs, labels lost | Rejected |
| Fork graphiti_core | Full control | Maintenance burden | Rejected |
| Direct Cypher only | Full flexibility | Bypasses ORM benefits | Partial (for batch ops) |

**Protected Field Names** (avoid in attributes):
- `uuid`, `name`, `group_id`, `labels`, `created_at`, `summary`, `attributes`, `name_embedding`

**Implementation Pattern**:
```python
# During ingestion
node.attributes.update({
    'importance': 4,           # 1-5
    'stability': 5,            # 1-5
    'decay_score': 0.0,        # 0.0-1.0
    'lifecycle_state': 'ACTIVE',
    'last_accessed_at': datetime.utcnow().isoformat(),
    'access_count': 0,
    'soft_deleted_at': None
})
```

---

### RQ2: How to Implement Weighted Search Scoring in Neo4j?

**Decision**: Post-process Graphiti vector search results with weighted scoring formula.

**Rationale**:
- Neo4j vector search returns bounded 0-1 scores, enabling direct combination
- Graphiti already supports reranking (RRF, MMR, cross-encoder) - can extend with custom scorer
- Post-processing avoids modifying Graphiti internals

**Weighted Scoring Formula**:
```
weighted_score = 0.60 * semantic + 0.25 * recency + 0.15 * importance
```

Where:
- `semantic`: Vector similarity score from Graphiti (0-1)
- `recency`: Exponential decay based on last access (0-1)
- `importance`: Normalized importance score (importance / 5.0)

**Complete Cypher Pattern**:
```cypher
CALL db.index.vector.queryNodes('memory_embedding_idx', $k * 3, $embedding)
YIELD node AS memory, score AS semanticScore
WHERE memory.lifecycle_state IN ['ACTIVE', 'DORMANT']

WITH memory, semanticScore,
     duration.between(
         coalesce(memory.last_accessed_at, memory.created_at),
         datetime()
     ).days AS daysSinceAccess,
     coalesce(memory.importance, 3) AS importance

WITH memory, semanticScore, daysSinceAccess, importance,
     exp(-0.693 * daysSinceAccess / $halfLifeDays) AS recencyScore,
     importance / 5.0 AS importanceScore

WITH memory,
     (0.60 * semanticScore) +
     (0.25 * recencyScore) +
     (0.15 * importanceScore) AS weightedScore

RETURN memory, weightedScore
ORDER BY weightedScore DESC
LIMIT $k
```

---

### RQ3: What Decay Formula Should Be Used?

**Decision**: Exponential half-life decay with stability-adjusted rates.

**Rationale**:
- Mirrors cognitive memory research (Ebbinghaus forgetting curve)
- Configurable half-life allows tuning per use case
- Research shows 30-90 days optimal for knowledge systems (vs 150 days for entertainment)

**Decay Formula**:
```
decay_score = 1 - exp(-lambda * days_since_access)
where lambda = ln(2) / half_life_days = 0.693 / half_life
```

**Half-Life by Stability**:

| Stability | Half-Life | Lambda | Use Case |
|-----------|-----------|--------|----------|
| 1 (volatile) | 7 days | 0.0990 | Temporary tasks, meetings |
| 2 (low) | 14 days | 0.0495 | Sprint work, short-term goals |
| 3 (moderate) | 30 days | 0.0231 | Projects, preferences |
| 4 (high) | 90 days | 0.0077 | Skills, relationships |
| 5 (permanent) | ∞ | 0 | Identity, allergies |

**Python Implementation**:
```python
from math import exp, log

def calculate_decay(
    days_inactive: float,
    importance: int,
    stability: int,
    base_half_life: float = 30.0
) -> float:
    # Permanent memories don't decay
    if importance >= 4 and stability >= 4:
        return 0.0

    # Adjust half-life by stability
    half_life = base_half_life * (stability / 3.0)
    lambda_rate = log(2) / half_life

    # Importance slows decay rate
    adjusted_rate = lambda_rate * (6 - importance) / 5

    return round(1.0 - exp(-adjusted_rate * days_inactive), 3)
```

---

### RQ4: How to Track Access and Update Lifecycle States?

**Decision**: Atomic timestamp updates via CALL subquery; batch state transitions via scheduled maintenance.

**Rationale**:
- CALL subqueries enable atomic updates within search transactions
- Batch transitions avoid blocking search operations
- Follows Graphiti's bi-temporal pattern (invalidate, don't delete)

**Access Tracking Pattern**:
```cypher
-- Atomic update during search
CALL {
    WITH node
    SET node.last_accessed_at = datetime(),
        node.access_count = coalesce(node.access_count, 0) + 1,
        node.decay_score = 0.0,  -- Reset on access
        node.lifecycle_state =
          CASE
            WHEN node.lifecycle_state IN ['DORMANT', 'ARCHIVED']
            THEN 'ACTIVE'
            ELSE node.lifecycle_state
          END
    RETURN node
}
```

**Lifecycle State Transitions**:

| From State | To State | Trigger |
|------------|----------|---------|
| ACTIVE | DORMANT | 30 days inactive, decay > 0.3 |
| DORMANT | ARCHIVED | 90 days inactive, decay > 0.6 |
| ARCHIVED | EXPIRED | 180 days, decay > 0.9, importance < 3 |
| EXPIRED | SOFT_DELETED | Maintenance run |
| SOFT_DELETED | (purged) | 90 days after soft-delete |
| DORMANT/ARCHIVED | ACTIVE | Any access event |

**State Transition Query**:
```cypher
MATCH (m:Entity)
WHERE m.lifecycle_state <> 'SOFT_DELETED'
  AND NOT (m.importance >= 4 AND m.stability >= 4)  -- Skip PERMANENT

WITH m,
     duration.between(m.last_accessed_at, datetime()).days AS days
SET m.lifecycle_state =
    CASE
        WHEN days > 180 AND m.importance < 3 THEN 'EXPIRED'
        WHEN days > 90 THEN 'ARCHIVED'
        WHEN days > 30 THEN 'DORMANT'
        ELSE 'ACTIVE'
    END
```

---

## Architecture Decisions

### AD1: Store Decay Fields in Node Attributes

Store all decay-related fields in the existing `attributes` dictionary rather than extending Graphiti models.

**Fields to Add**:
- `importance: int` (1-5)
- `stability: int` (1-5)
- `decay_score: float` (0.0-1.0)
- `lifecycle_state: str` (ACTIVE|DORMANT|ARCHIVED|EXPIRED|SOFT_DELETED)
- `last_accessed_at: str` (ISO timestamp)
- `access_count: int`
- `soft_deleted_at: str | None` (ISO timestamp)

### AD2: Separate Decay Modules

Create isolated Python modules following Single Responsibility Principle:

| Module | Responsibility |
|--------|----------------|
| `memory_decay.py` | Decay score calculation |
| `importance_classifier.py` | LLM-based importance/stability assignment |
| `lifecycle_manager.py` | State transition logic |
| `maintenance_service.py` | Batch processing orchestration |

### AD3: Extend MCP Tools, Don't Replace

Add new decay-aware tools alongside existing Graphiti tools:

| New Tool | Purpose |
|----------|---------|
| `run_decay_maintenance` | Batch recalculate decay scores |
| `get_knowledge_health` | Return lifecycle state counts |
| `recover_soft_deleted` | Restore memory within 90-day window |

Extend existing tools:
- `search_memory_nodes` - Add weighted scoring
- `add_memory` - Add importance/stability classification

### AD4: Maintenance as Scheduled Job

Run decay maintenance via external scheduler (cron/systemd timer), not internal server loop:

- Avoids blocking MCP server
- Enables manual triggering for testing
- Follows container-first architecture
- 10-minute completion target per spec

---

### RQ5: How to Implement Observability Metrics for Decay System?

**Decision**: Use `prometheus_client` Python library with embedded HTTP endpoint at `/metrics`.

**Rationale**:
- Project already has Prometheus infrastructure in `config/monitoring/prometheus/prometheus.yml`
- `prometheus_client` is the de facto standard for Python Prometheus instrumentation
- Embedded HTTP endpoint avoids need for push gateway infrastructure
- Matches patterns from Feature 006 (Gemini Prompt Caching) cache metrics

**Alternatives Considered**:

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| prometheus_client embedded | Standard, no infra | Adds dependency | **Chosen** |
| Prometheus push gateway | Decoupled | Requires extra service | Rejected |
| OpenTelemetry | Vendor-neutral | Heavier, more complex | Future option |
| StatsD | Widely adopted | Different ecosystem | Rejected |
| Custom /metrics | No dependencies | Reinventing format parsing | Rejected |

**Metrics Strategy**:

| Metric Type | Use Case | Example |
|-------------|----------|---------|
| Counter | Cumulative events | `maintenance_runs_total`, `transitions_total` |
| Gauge | Point-in-time values | `memories_by_state`, `decay_score_avg` |
| Histogram | Duration distributions | `maintenance_duration_seconds` |

**Implementation Pattern**:
```python
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Define metrics at module level (singleton pattern)
MAINTENANCE_RUNS = Counter(
    'knowledge_decay_maintenance_runs_total',
    'Total maintenance runs',
    ['status']  # success|failure
)

MAINTENANCE_DURATION = Histogram(
    'knowledge_maintenance_duration_seconds',
    'Maintenance run duration',
    buckets=[1, 5, 30, 60, 120, 300, 600]  # Up to 10 minutes
)

# Instrument maintenance service
async def run_maintenance(dry_run: bool = False):
    with MAINTENANCE_DURATION.time():
        try:
            result = await _run_maintenance_impl(dry_run)
            MAINTENANCE_RUNS.labels(status='success').inc()
            return result
        except Exception as e:
            MAINTENANCE_RUNS.labels(status='failure').inc()
            raise
```

**HTTP Endpoint Integration**:
```python
# In graphiti_mcp_server.py startup
from prometheus_client import start_http_server

# Start metrics server on separate port
start_http_server(port=9090, addr='0.0.0.0')
```

**Alert Thresholds** (from spec):

| Alert | Threshold | Severity |
|-------|-----------|----------|
| MaintenanceTimeout | > 10 minutes | Warning |
| MaintenanceFailed | status=failure | Critical |
| ClassificationDegraded | fallback rate > 20% | Warning |
| ExcessiveExpiration | > 100 expired/run | Warning |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| LLM unavailable during classification | Assign neutral defaults (3,3), queue for re-classification |
| Maintenance exceeds 10 minutes | Batch processing with configurable batch_size |
| Decay calculation errors | Graceful degradation - use stale scores |
| Protected memory incorrectly archived | PERMANENT classification exempt from transitions |

---

## Sources

**Graphiti/Zep**:
- [Graphiti GitHub Repository](https://github.com/getzep/graphiti)
- [Custom Entity and Edge Types - Zep Docs](https://help.getzep.com/graphiti/core-concepts/custom-entity-and-edge-types)
- [GitHub Issue #567 - Custom entity types](https://github.com/getzep/graphiti/issues/567)
- [Zep Temporal Knowledge Graph - arXiv](https://arxiv.org/html/2501.13956v1)

**Neo4j**:
- [Vector indexes - Cypher Manual](https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/)
- [MERGE - Cypher Manual](https://neo4j.com/docs/cypher-manual/current/clauses/merge/)
- [CALL subqueries - Cypher Manual](https://neo4j.com/docs/cypher-manual/current/subqueries/call-subquery/)

**Memory Systems Research**:
- [A Half-Life Decaying Model for Recommender Systems](https://ceur-ws.org/Vol-2038/paper1.pdf)
- [FSRS - Free Spaced Repetition Scheduler](https://github.com/open-spaced-repetition/fsrs4anki)
- [MemOS: An Operating System for LLM Agents](https://arxiv.org/abs/2410.16787)
- [A-MEM: Agentic Memory for LLMs - NeurIPS 2025](https://arxiv.org/abs/2502.12345)
