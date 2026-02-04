# Data Model: Investigative Search with Connected Entities

**Feature**: 020-investigative-search
**Date**: 2026-02-04

## Overview

This document defines the data structures for the investigative search feature. These structures are used for API responses between the MCP server, CLI, and AI consumers.

## Core Entities

### InvestigateResult

The primary response structure for an investigate query.

```typescript
interface InvestigateResult {
  // The primary entity that was searched for
  entity: Entity;

  // All connected entities found during traversal
  connections: Connection[];

  // Metadata about the investigation
  metadata: InvestigationMetadata;

  // Optional warning message (e.g., too many connections)
  warning?: string;
}
```

**Fields**:
- `entity`: The starting entity for the investigation
- `connections`: Array of all connections found (1-3 hops)
- `metadata`: Cycle counts, skipped entities, performance info
- `warning`: Optional message for edge cases (large result sets)

---

### Entity

Represents a node in the knowledge graph with full context.

```typescript
interface Entity {
  // Unique identifier for the entity
  uuid: string;

  // Human-readable name
  name: string;

  // Entity type(s) - can be multiple labels
  labels: string[];

  // Optional summary/description
  summary?: string;

  // When the entity was created
  created_at?: string;  // ISO 8601 timestamp

  // Group ID for multi-tenant scenarios
  group_id?: string;

  // Extended attributes (scores, lifecycle, etc.)
  attributes?: EntityAttributes;
}
```

**EntityAttributes** (optional):
```typescript
interface EntityAttributes {
  // Weighted search score (if applicable)
  weighted_score?: number;
  score_breakdown?: {
    semantic?: number;
    recency?: number;
    importance?: number;
  };

  // Memory lifecycle state (Feature 009)
  lifecycle_state?: 'ACTIVE' | 'DORMANT' | 'ARCHIVED' | 'EXPIRED' | 'SOFT_DELETED';

  // Importance and stability scores
  importance?: number;  // 1-5
  stability?: number;   // 1-5

  // Decay score
  decay_score?: number;  // 0.0-1.0

  // Last access time
  last_accessed_at?: string;

  // Custom attributes for CTI entities
  custom_attributes?: Record<string, unknown>;
}
```

---

### Connection

Represents a relationship edge between two entities.

```typescript
interface Connection {
  // The type of relationship (e.g., "OWNED_BY", "USES", "TARGETS")
  relationship: string;

  // Direction of the relationship
  direction: 'outgoing' | 'incoming' | 'bidirectional';

  // The entity at the other end of this connection
  target_entity: Entity;

  // Hop distance from the primary entity (1 = direct, 2 = friend of friend, etc.)
  hop_distance: number;

  // Optional confidence score for the relationship
  confidence?: number;

  // Optional fact description
  fact?: string;
}
```

**Relationship Direction**:
- `outgoing`: Primary entity → target (e.g., Person → OWNS → Phone)
- `incoming`: Target → primary entity (e.g., Phone → OWNED_BY → Person)
- `bidirectional`: Mutual relationship (rare in CTI data)

---

### InvestigationMetadata

Metadata about the investigation process and results.

```typescript
interface InvestigationMetadata {
  // Number of hops explored (1-3)
  depth_explored: number;

  // Total connections found (before filtering)
  total_connections_explored: number;

  // Connections returned (after filtering)
  connections_returned: number;

  // Cycle detection
  cycles_detected: number;
  cycles_pruned: string[];  // UUIDs of entities where cycles were detected

  // Entity filtering
  entities_skipped?: number;  // Deleted or soft-deleted entities

  // Relationship type filtering (if applied)
  relationship_types_filtered?: string[];

  // Performance metrics
  query_duration_ms?: number;

  // Warning threshold exceeded
  max_connections_exceeded?: boolean;
}
```

---

## State Transitions

Not applicable - this feature does not modify entity state, only reads.

---

## Validation Rules

### InvestigateResult Validation

| Field | Validation Rule |
|-------|----------------|
| `entity` | Must not be null, must have valid UUID |
| `connections` | Can be empty array, must not contain null elements |
| `metadata.depth_explored` | Must be 1, 2, or 3 |
| `metadata.cycles_detected` | Must be >= 0 |

### Entity Validation

| Field | Validation Rule |
|-------|----------------|
| `uuid` | Must be valid UUID string |
| `name` | Must not be empty, max 500 characters |
| `labels` | Must not be empty, max 10 labels |
| `created_at` | Must be valid ISO 8601 timestamp if present |

### Connection Validation

| Field | Validation Rule |
|-------|----------------|
| `relationship` | Must not be empty |
| `direction` | Must be one of: outgoing, incoming, bidirectional |
| `hop_distance` | Must be >= 1 and <= depth_explored |
| `target_entity` | Must not be null, must have valid UUID |

---

## Relationship Types

### Standard Relationship Types

These are common relationship types in the knowledge graph:

| Type | Direction | Description |
|------|-----------|-------------|
| `OWNED_BY` | outgoing | Entity is owned by another entity |
| `CONTACTED_VIA` | outgoing | Communication relationship |
| `LOCATED_AT` | outgoing | Physical location |
| `RELATED_TO` | bidirectional | General relationship |
| `PART_OF` | outgoing | Membership/containment |

### CTI Relationship Types (Feature 019)

Custom relationship types for OSINT/CTI data:

| Type | Direction | Source → Target |
|------|-----------|----------------|
| `USES` | outgoing | ThreatActor → Malware |
| `TARGETS` | outgoing | ThreatActor → Organization |
| `ATTRIBUTED_TO` | incoming | Campaign → ThreatActor |
| `EXPLOITS` | outgoing | Malware → Vulnerability |
| `VARIANT_OF` | bidirectional | Indicator → Indicator |
| `HOSTED_ON` | outgoing | Account → Domain |

---

## Example Response

```json
{
  "entity": {
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "name": "+1-555-0199",
    "labels": ["Phone"],
    "summary": "Phone number associated with suspicious activity",
    "created_at": "2026-02-04T10:30:00Z",
    "group_id": "main",
    "attributes": {
      "lifecycle_state": "ACTIVE",
      "importance": 3,
      "stability": 2
    }
  },
  "connections": [
    {
      "relationship": "OWNED_BY",
      "direction": "incoming",
      "target_entity": {
        "uuid": "660e8400-e29b-41d4-a716-446655440001",
        "name": "John Doe",
        "labels": ["Person"],
        "summary": "Person of interest",
        "created_at": "2026-02-01T09:00:00Z",
        "group_id": "main"
      },
      "hop_distance": 1,
      "fact": "Phone owned by John Doe"
    },
    {
      "relationship": "CONTACTED_VIA",
      "direction": "outgoing",
      "target_entity": {
        "uuid": "770e8400-e29b-41d4-a716-446655440002",
        "name": "@suspicious_actor",
        "labels": ["Account"],
        "summary": "Social media account",
        "created_at": "2026-02-03T14:20:00Z",
        "group_id": "main"
      },
      "hop_distance": 1,
      "fact": "Phone used to contact @suspicious_actor"
    }
  ],
  "metadata": {
    "depth_explored": 1,
    "total_connections_explored": 2,
    "connections_returned": 2,
    "cycles_detected": 0,
    "cycles_pruned": [],
    "query_duration_ms": 145
  }
}
```

---

## Edge Cases

### No Connections Found

```json
{
  "entity": { /* ... */ },
  "connections": [],
  "metadata": {
    "depth_explored": 1,
    "total_connections_explored": 0,
    "connections_returned": 0,
    "cycles_detected": 0,
    "cycles_pruned": []
  }
}
```

### Cycle Detected

```json
{
  "entity": { /* ... */ },
  "connections": [ /* ... */ ],
  "metadata": {
    "depth_explored": 2,
    "total_connections_explored": 15,
    "connections_returned": 12,
    "cycles_detected": 3,
    "cycles_pruned": ["uuid-abc", "uuid-def", "uuid-ghi"]
  }
}
```

### Too Many Connections Warning

```json
{
  "entity": { /* ... */ },
  "connections": [ /* truncated to 500 */ ],
  "warning": "Found 1,247 connections (showing first 500). Use --relationship-type filter to narrow results.",
  "metadata": {
    "depth_explored": 1,
    "total_connections_explored": 1247,
    "connections_returned": 500,
    "cycles_detected": 0,
    "cycles_pruned": [],
    "max_connections_exceeded": true
  }
}
```

---

## Dependencies

- Feature 009 (Memory Decay Scoring) - for EntityAttributes (lifecycle_state, importance, stability)
- Feature 019 (OSINT/CTI Ontology Support) - for custom relationship types and entity labels
- Existing Graphiti core types - nodes, edges, episodes
