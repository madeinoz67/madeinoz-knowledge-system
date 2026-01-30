# Data Model: LLM Client for Maintenance Classification

**Feature**: 011-maintenance-llm-client-fix
**Date**: 2026-01-30

## Overview

This feature is a bug fix to existing code - no new data models are introduced. The changes ensure that the existing data model correctly stores importance and stability scores classified by the LLM.

## Existing Data Model (No Changes)

### Entity Node Attributes

| Attribute | Type | Description | Source |
|-----------|------|-------------|--------|
| `importance` | Integer (1-5) | Memory importance: 1=trivial, 5=core | LLM classification |
| `stability` | Integer (1-5) | Memory stability: 1=volatile, 5=permanent | LLM classification |
| `lifecycle_state` | String | Entity lifecycle: ACTIVE, DORMANT, ARCHIVED, etc. | Maintenance service |
| `decay_score` | Float | Calculated decay based on importance, stability, time | Decay calculator |
| `last_accessed_at` | DateTime | Last time entity was accessed | Maintenance service |
| `access_count` | Integer | Number of times entity has been accessed | Maintenance service |

### Classification Result (Dictionary)

```python
{
    "found": int,          # Number of unclassified nodes found
    "classified": int,     # Number successfully classified
    "failed": int,         # Number that failed classification
    "using_llm": bool      # Whether LLM was used (vs defaults)
}
```

## State Transitions

### Node Classification Flow

```
Episode Added (add_memory)
    ↓
Graphiti Background Processing
    ↓
Entity Created (importance=NULL, stability=NULL)
    ↓
Immediate Classification (NEW - background task)
    ↓
Entity Updated (importance=1-5, stability=1-5)
    ↓
OR Maintenance Cycle (backup)
    ↓
Entity Updated (importance=1-5, stability=1-5)
```

## Validation Rules

### Importance Score (1-5)

| Value | Label | Description |
|-------|-------|-------------|
| 1 | Trivial | Can forget immediately |
| 2 | Low | Useful but replaceable |
| 3 | Moderate | General knowledge (default) |
| 4 | High | Important to work/identity |
| 5 | Core | Fundamental, never forget |

**Validation**: Must be integer between 1-5. Out-of-range values from LLM are clamped.

### Stability Score (1-5)

| Value | Label | Description |
|-------|-------|-------------|
| 1 | Volatile | Changes in hours/days |
| 2 | Low | Changes in days/weeks |
| 3 | Moderate | Changes in weeks/months |
| 4 | High | Changes in months/years |
| 5 | Permanent | Never changes |

**Validation**: Must be integer between 1-5. Out-of-range values from LLM are clamped.

### Permanent Classification

**Rule**: Entity is PERMANENT if `importance >= 4` AND `stability >= 4`

**Implication**: Permanent entities are exempt from decay scoring.

## Query Patterns

### Find Unclassified Nodes

```cypher
MATCH (n:Entity)
WHERE n.`attributes.importance` IS NULL
   OR n.`attributes.stability` IS NULL
RETURN n
LIMIT {batch_size}
```

### Update Node with Classification

```cypher
MATCH (n:Entity)
WHERE n.uuid = {uuid}
SET n.`attributes.importance` = {importance},
    n.`attributes.stability` = {stability},
    n.`attributes.lifecycle_state` = 'ACTIVE',
    n.`attributes.decay_score` = 0.0,
    n.`attributes.last_accessed_at` = datetime(),
    n.`attributes.access_count` = 0
```

## No Schema Changes Required

This feature does not introduce any new node types, relationships, or attributes. It fixes a bug where existing attributes were not being populated correctly.

## Indexes

Existing indexes are sufficient:
- `lifecycle_state` index (created in feature 009)
- `uuid` unique constraint (Graphiti default)
- Vector embeddings (Graphiti default)
