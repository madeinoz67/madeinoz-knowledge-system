# Data Model: Graph Traversal Entities

**Feature**: 021-fix-async-session
**Date**: 2026-02-05

## Overview

This document defines the data structures used in graph traversal operations. The entities are derived from the GraphTraversal class in `docker/patches/utils/graph_traversal.py`.

## Core Entities

### TraversalResult

**Purpose**: Result of a graph traversal operation containing all connections found and metadata about the traversal.

**Attributes**:
| Attribute | Type | Description |
|-----------|------|-------------|
| `connections` | `List[Dict[str, Any]]` | List of connected entities with relationship information |
| `depth_explored` | `int` | Maximum depth reached during traversal |
| `total_connections_explored` | `int` | Total connections examined (including cycles) |
| `connections_returned` | `int` | Number of unique connections returned after cycle pruning |
| `cycles_detected` | `int` | Count of cycles detected during traversal |
| `cycles_pruned` | `List[str]` | UUIDs of entities pruned due to cycle detection |
| `entities_skipped` | `int` | Count of entities skipped for any reason |
| `query_duration_ms` | `float \| None` | Time taken for traversal in milliseconds |
| `max_connections_exceeded` | `bool` | Whether connection count exceeded 500 threshold |
| `warning` | `str \| None` | Warning message if thresholds exceeded |

**Validation Rules**:
- `depth_explored` must be between 1 and 3
- `connections_returned` ≤ `total_connections_explored`
- `max_connections_exceeded` = true only if `total_connections_explored` ≥ 500

### Connection

**Purpose**: Represents a single connection (relationship) between entities in the traversal result.

**Structure** (Dict):
```python
{
    "relationship": str,        # Type of relationship (e.g., "USES", "OWNS")
    "direction": str,           # "bidirectional" for undirected graphs
    "target_entity": {           # Connected entity
        "uuid": str,
        "name": str,
        "labels": List[str],
        "summary": str | None,
        "created_at": str | None,
        "group_id": str | None,
        "attributes": Dict | None
    },
    "hop_distance": int,         # Number of hops from start entity
    "fact": str                  # Human-readable fact description
}
```

**Validation Rules**:
- `hop_distance` ≥ 1 and ≤ max_depth
- `target_entity.uuid` must not be null/empty
- `relationship` must be a non-empty string

### EntityInfo

**Purpose**: Information about an entity in the knowledge graph.

**Attributes**:
| Attribute | Type | Description |
|-----------|------|-------------|
| `uuid` | `str` | Unique identifier for the entity |
| `name` | `str` | Human-readable name |
| `labels` | `List[str]` | Type labels assigned to the entity |
| `summary` | `str \| None` | Text summary of the entity |
| `created_at` | `str \| None` | ISO timestamp of entity creation |
| `group_id` | `str \| None` | Knowledge graph group identifier |
| `attributes` | `Dict[str, Any] \| None` | Additional entity attributes |

**Validation Rules**:
- `uuid` must be unique across the graph
- `name` must not be empty
- `labels` must contain at least one label
- `created_at` must be valid ISO 8601 timestamp if present

## Relationships

```
TraversalResult
    ├── Connection[*]      (0 to ∞)
    │   └── target_entity → EntityInfo
    └── metadata (self-referential)
```

## Data Flow

```
investigate_entity (MCP tool)
    ↓
    Search for entity by name → EntityInfo
    ↓
    GraphTraversal.traverse(uuid)
    ↓
    _traverse_neo4j_async() or _traverse_falkordb_sync()
    ↓
    TraversalResult
    └── Connection[*]
        └── EntityInfo
```

## State Transitions

**No state transitions** - These are immutable data structures representing traversal results.

## Notes

- All entities use Python dataclasses for clarity
- Connections are returned as Dict for JSON serialization
- Cycle detection prevents duplicate connections in results
- Max 500 connections returned before warning threshold
