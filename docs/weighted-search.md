# Weighted Search Guide

## Overview

Weighted search is an enhanced search mode that combines **semantic similarity** with **recency** and **importance** to provide more relevant results. Instead of ranking purely by how well text matches your query, weighted search considers:

- **60% Semantic similarity** - How well the content matches your query meaning
- **25% Recency** - How recently the item was accessed
- **15% Importance** - How significant the item is (rated 1-5)

## When to Use Weighted Search

### Use Weighted Search (`--weighted`) when:

- **Finding important knowledge** - You want high-importance items to appear first
- **Recent context matters** - You need recently accessed information
- **Comprehensive relevance** - You want balanced ranking considering multiple factors

### Use Standard Search (no flag) when:

- **Pure semantic match** - You only care about text similarity
- **Unbiased results** - You want the raw vector embedding match
- **Unfamiliar topics** - You're exploring new concepts without established importance

## How to Use

### Basic Usage

```bash
# Standard search (semantic only)
bun run src/skills/tools/knowledge-cli.ts search_nodes "query" 10

# Weighted search (semantic + recency + importance)
bun run src/skills/tools/knowledge-cli.ts search_nodes "query" 10 --weighted
```

### With Temporal Filtering

```bash
# Weighted search for last 7 days
bun run src/skills/tools/knowledge-cli.ts search_nodes "query" 10 --weighted --since 7d

# Weighted search within date range
bun run src/skills/tools/knowledge-cli.ts search_nodes "query" 10 --weighted --since 2026-01-01 --until 2026-01-31
```

### Raw Output (for scripts/debugging)

```bash
# See full score breakdown
bun run src/skills/tools/knowledge-cli.ts search_nodes "query" 5 --weighted --raw
```

## Understanding the Results

### Standard Search Output

```json
{
  "message": "Nodes retrieved successfully",
  "nodes": [
    {
      "name": "knowledge system",
      "summary": "...",
      "created_at": "2026-02-02T12:59:36.120429+00:00",
      "attributes": {
        "importance": 4,
        "stability": 3,
        "decay_score": 0
      }
    }
  ]
}
```

### Weighted Search Output

```json
{
  "message": "Nodes retrieved with weighted scoring (5 results)",
  "nodes": [
    {
      "name": "knowledge system",
      "summary": "...",
      "created_at": "2026-02-02T12:59:36.120429+00:00",
      "attributes": {
        "weighted_score": 0.91,
        "score_breakdown": {
          "semantic": 0.90,
          "recency": 0.98,
          "importance": 0.80
        },
        "importance": 4,
        "stability": 3,
        "decay_score": 0,
        "lifecycle_state": "ACTIVE"
      }
    }
  ]
}
```

### Score Breakdown

| Field | Range | Meaning |
|-------|-------|---------|
| `weighted_score` | 0-1 | Combined relevance score (higher = better) |
| `score_breakdown.semantic` | 0-1 | Text similarity to query |
| `score_breakdown.recency` | 0-1 | How recently accessed (1 = very recent) |
| `score_breakdown.importance` | 0-1 | Importance level normalized (5 → 1.0, 1 → 0.2) |
| `importance` | 1-5 | Raw importance rating |
| `stability` | 1-5 | How stable/permanent this knowledge is |
| `decay_score` | 0-1 | Memory decay score (0 = fresh) |
| `lifecycle_state` | string | ACTIVE, DORMANT, ARCHIVED, EXPIRED, or SOFT_DELETED |

## Test Results & Examples

### Test 1: "PAI algorithm" Query

**Result:** Ranking remained the same, but weighted search added transparency.

| Rank | Item | Weighted Score | Semantic | Recency | Importance |
|------|------|----------------|----------|---------|------------|
| 1 | PAI ALGORITHM | 0.94 | 1.00 | 1.00 | 0.60 |
| 2 | PAI pack logo | 0.91 | 0.95 | 0.9998 | 0.60 |
| 3 | PAI_DIR environment | 0.88 | 0.90 | 0.9998 | 0.60 |
| 4 | fixed-threshold system | 0.85 | 0.85 | 0.9904 | 0.60 |
| 5 | DAIV_PAI speaker | 0.82 | 0.80 | 0.9885 | 0.60 |

**Observation:** All items had importance=3, so semantic scores determined ranking. Weighted search provided explainability (why items ranked where they did).

### Test 2: "knowledge" Query (Different Importance Levels)

**Result:** Weighted search changed rankings to boost high-importance items.

| Rank Change | Unweighted | Weighted | Importance | Why? |
|-------------|------------|----------|------------|------|
| ⬆️ 3→2 | knowledge system | knowledge system | **4** | High importance boosted it |
| ⬇️ 2→3 | knowledge-mcp container | knowledge-mcp container | **2** | Low importance penalized it |
| ⬆️ 4→3 | knowledge-cli | knowledge-cli | **4** | High importance helped it |

**Full Results:**

| Rank | Item (Unweighted) | Imp | Rank | Item (Weighted) | Score | Imp |
|------|-------------------|-----|------|-----------------|-------|-----|
| 1 | knowledge sy | 3 | 1 | knowledge sy | 0.94 | 3 |
| 2 | knowledge-mcp container | 2 | 2 | **knowledge system** | 0.91 | **4** |
| 3 | **knowledge system** | 4 | 3 | knowledge-mcp container | 0.88 | 2 |
| 4 | **knowledge-cli** | 4 | 3 | **knowledge-cli** | 0.88 | 4 |
| 5 | ghcr.io image | 3 | 5 | ghcr.io image | 0.82 | 3 |

**Key Insight:** When semantic scores are close, the **15% importance weight** can change rankings. High-importance items (4) get priority over low-importance items (2).

## How the Formula Works

### Calculation Example

For "knowledge system" with importance=4:

```javascript
// Component scores
semantic = 0.90    // Text similarity to "knowledge"
recency = 0.98     // Recently accessed
importance = 0.80  // importance=4 normalized to 0-1 range (4/5)

// Weighted combination
weighted_score = (semantic × 0.60) + (recency × 0.25) + (importance × 0.15)
               = (0.90 × 0.60) + (0.98 × 0.25) + (0.80 × 0.15)
               = 0.540 + 0.245 + 0.120
               = 0.905 ≈ 0.91
```

### Importance Normalization

| Raw Importance | Normalized (0-1) | Weight in Score |
|----------------|-------------------|-----------------|
| 5 (Critical) | 1.00 | 15% → contributes 0.15 |
| 4 (High) | 0.80 | 15% → contributes 0.12 |
| 3 (Medium) | 0.60 | 15% → contributes 0.09 |
| 2 (Low) | 0.40 | 15% → contributes 0.06 |
| 1 (Minimal) | 0.20 | 15% → contributes 0.03 |

**Note:** Importance is a **boosting factor**, not a filter. Low-importance items can still rank highly if they have strong semantic and recency scores.

## Best Practices

### 1. Use Weighted Search for Discovery

```bash
# Find important concepts about a topic
bun run src/skills/tools/knowledge-cli.ts search_nodes "architecture" 10 --weighted
```

### 2. Use Standard Search for Exact Matches

```bash
# Find exact text matches (code, specific terms)
bun run src/skills/tools/knowledge-cli.ts search_nodes "graphiti_api_cost" 10
```

### 3. Combine with Temporal Filters

```bash
# Important knowledge from this week
bun run src/skills/tools/knowledge-cli.ts search_nodes "decisions" 10 --weighted --since 7d

# Recent high-priority items
bun run src/skills/tools/knowledge-cli.ts search_nodes "bugs" 10 --weighted --since today
```

### 4. Use --raw for Analysis

```bash
# Export weighted scores for external analysis
bun run src/skills/tools/knowledge-cli.ts search_nodes "project" 20 --weighted --raw > results.json
```

## FAQ

**Q: Does weighted search always return different results?**

A: Not always. If all items have similar importance and recency, rankings stay similar. Weighted search primarily affects results when:
- Importance levels vary (1-5 range)
- Some items were accessed recently while others weren't
- Semantic scores are close (the 15% importance weight can tip the balance)

**Q: Should I always use weighted search?**

A: Use it as a default for knowledge discovery. The 60% semantic weight ensures text relevance is still the primary factor. Only use standard search when you need pure semantic matching.

**Q: How is importance determined?**

A: Importance is classified when knowledge is added:
- **Automatic classification** via LLM when adding episodes
- **Manual classification** via `classify_memory` command
- Based on content type, user preferences, and context

**Q: Can I see why a specific item ranked where it did?**

A: Yes! Use `--weighted --raw` to see the full score breakdown:
```bash
bun run src/skills/tools/knowledge-cli.ts search_nodes "query" 5 --weighted --raw
```

**Q: What's the difference between `importance` and `stability`?**

A:
- **Importance (1-5)**: How significant or valuable this knowledge is
- **Stability (1-5)**: How permanent or unchanging this knowledge is
- Both factors are used by the memory decay system but only importance affects search ranking

## Related Documentation

- [Memory Decay System](./memory-decay.md) - How importance and stability are calculated
- [CLI Reference](./reference/cli.md) - Complete command documentation
- [Configuration](./reference/configuration.md) - Setting up the knowledge system
