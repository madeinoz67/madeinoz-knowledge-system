# Research: Investigative Search with Connected Entities

**Feature**: 020-investigative-search
**Date**: 2026-02-04

## Overview

This document captures research findings and technical decisions for implementing the investigative search feature.

## Research Decisions

### 1. Graph Traversal Patterns

**Question**: How to perform efficient multi-hop graph traversal with cycle detection in Neo4j/FalkorDB?

**Decision**: Use database-specific traversal strategies
- **Neo4j**: Cypher variable-length paths with `MATCH path = (start)-[*1..3]-(end)`
- **FalkorDB**: Custom breadth-first traversal with visited entity tracking

**Rationale**:
- Neo4j's native path queries are optimized for variable-length traversal
- FalkorDB has limited path query support, requires custom implementation
- Both approaches can share cycle detection logic (visited set)

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|------------------|
| Recursive queries | Depth limits cause stack overflow |
| Multiple round-trips | Poor performance (N+1 query problem) |
| Allow duplicates | Messy output, hard to follow |

**References**:
- Neo4j variable-length paths: https://neo4j.com/docs/cypher-manual/current/paths/
- FalkorDB graph queries: https://docs.falkordb.com/

---

### 2. Entity Name Resolution Strategy

**Question**: How to include entity names in relationship responses without N+1 queries?

**Decision**: Return full entity objects (with name, type, UUID) inline in connections array

**Rationale**:
- Single query round-trip for optimal performance
- Matches Codanna's `analyze_impact` pattern (returns full context)
- AI consumers get all data needed for display without additional lookups
- UUID included for programmatic follow-up queries

**Response Structure**:
```json
{
  "entity": {
    "uuid": "...",
    "name": "Phone: +1-555-0199",
    "type": "Phone",
    "attributes": {...}
  },
  "connections": [
    {
      "relationship": "OWNED_BY",
      "target_entity": {
        "uuid": "...",
        "name": "John Doe",
        "type": "Person"
      }
    }
  ]
}
```

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|------------------|
| UUID-only with client-side lookup | Multiple queries required, defeats purpose |
| Name-only without UUID | Cannot programmatically follow connections |
| Lazy loading | Adds complexity, violates single-query goal |

---

### 3. Cycle Detection Strategy

**Question**: How to detect and handle cycles during graph traversal?

**Decision**: Track visited entities in a set, skip already-visited entities, report cycles in metadata

**Rationale**:
- Prevents infinite loops (A → B → C → A)
- O(1) lookup for visited check
- Provides visibility to users about cycles in their data
- Minimal performance overhead

**Algorithm**:
```python
visited = set()
cycles = []

def traverse(entity, depth):
    if entity.uuid in visited:
        cycles.append(entity.uuid)
        return

    visited.add(entity.uuid)
    # ... traverse connections

    # Optional: remove from visited for alternative paths
    # visited.remove(entity.uuid)
```

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|------------------|
| Depth-first with recursion limit | Stack overflow on deep graphs |
| Allow duplicates | Messy output, exponential blowup |
| Path-based cycle detection | More complex, not needed for our use case |

**Cycle Reporting**:
```json
{
  "metadata": {
    "cycles_detected": 2,
    "cycles_pruned": ["uuid-abc", "uuid-def"]
  }
}
```

---

### 4. Connection Depth Limits

**Question**: What is the appropriate maximum depth for investigative search?

**Decision**: Limit to 3 hops maximum

**Rationale**:
- 1-hop: Direct connections (immediate context)
- 2-hop: Friends of friends (broader context)
- 3-hop: Extended network (comprehensive view)
- 4+ hops: Too noisy, performance issues, rarely useful

**Performance Impact** (estimated):
| Depth | Max Nodes (branching=3) | Query Time |
|-------|------------------------|------------|
| 1 | 3 | < 100ms |
| 2 | 9 | < 500ms |
| 3 | 27 | < 2s |
| 4 | 81 | > 5s |

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|------------------|
| Unlimited depth | Runaway queries, poor performance |
| 2-hop max | Too limiting for CTI investigations |
| 5-hop max | Performance unacceptable |

---

### 5. Relationship Type Filtering

**Question**: How to filter by relationship type efficiently?

**Decision**: Apply relationship type filter during traversal (not post-processing)

**Rationale**:
- Reduces graph traversal work
- Lower memory usage
- Faster response times

**Implementation**:
```cypher
// Neo4j: Filter in WHERE clause
MATCH path = (start)-[r*1..3]-(end)
WHERE type(r) IN $relationship_types
RETURN path

// FalkorDB: Filter during BFS
for edge in get_edges(start):
    if edge.relationship_type in filter_types:
        traverse(edge)
```

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|------------------|
| Post-process filtering | Traverses unnecessary edges |
| Regex matching | Slower, less precise |

---

## Best Practices Research

### Graph Query Performance

**Finding**: Early filtering and indexing are critical for performance

**Recommendations**:
1. Filter by relationship_type before traversal
2. Use index hints on entity names (if available)
3. Limit result sets with max_connections threshold (500)
4. Warn users when results exceed threshold

**Sources**:
- Neo4j Query Tuning: https://neo4j.com/docs/operations-manual/current/performance/query-tuning/
- FalkorDB Performance: https://docs.falkordb.com/FalkorDB/Performance/

---

### API Response Format

**Finding**: Follow existing response type patterns for consistency

**Recommendations**:
1. Create InvestigateResult response type following NodeResult/FactSearchResponse patterns
2. Use Pydantic models for validation
3. Include metadata for cycles, warnings, skipped entities
4. Maintain backward compatibility with existing tools

**Existing Patterns** (from response_types.py):
```python
class NodeResult(BaseModel):
    uuid: str | None
    name: str
    labels: list[str]
    created_at: str | None
    summary: str | None
    attributes: dict[str, Any]
```

---

## Technical Constraints

### Neo4j vs FalkorDB Differences

| Aspect | Neo4j | FalkorDB |
|--------|-------|----------|
| Variable-length paths | Native support (`*1..3`) | Limited, requires custom |
| Path functions | `nodes()`, `relationships()` | Manual traversal |
| Cycle detection | Automatic (path uniqueness) | Manual tracking required |
| Lucene query | Not required | Required (with sanitization) |

**Mitigation**: Abstract traversal logic into database driver layer, use factory pattern for database-specific implementations.

---

## Performance Targets

From spec SC-001: **Investigative search completes for entities with up to 100 direct connections in under 2 seconds**

**Breakdown**:
| Operation | Target Time |
|-----------|-------------|
| Entity lookup | < 50ms |
| Graph traversal (3 hops) | < 1500ms |
| Entity name resolution | < 200ms |
| Response formatting | < 250ms |
| **Total** | **< 2000ms (2s)** |

**Scaling**: For entities with >100 connections, return warning message and suggest filters.

---

## Security Considerations

### Query Depth Limiting

**Risk**: Malicious users could request deep traversals to DoS the server

**Mitigation**:
- Hard limit of 3 hops maximum
- Validate depth parameter on server side
- Return error for invalid depth values

### Connection Count Limiting

**Risk**: Dense graphs (hub entities) could return thousands of connections

**Mitigation**:
- Warning threshold at 500 connections
- Soft limit with user notification
- Suggest relationship type filters

---

## Open Questions

None - all research questions resolved.

## Next Steps

1. Create data-model.md with entity definitions
2. Create contracts/investigate-entity.yaml with API specification
3. Create quickstart.md with user-facing documentation
4. Proceed to Phase 2: Implementation (via /speckit.tasks)
