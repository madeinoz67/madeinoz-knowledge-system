# Quickstart: Memory Decay Scoring Development

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)
**Date**: 2026-01-29

## Prerequisites

- Docker or Podman installed
- Bun runtime (for TypeScript tools)
- Python 3.11+ (for server development)
- Neo4j or FalkorDB backend running

## Quick Setup

### 1. Start the Knowledge System

```bash
# From repository root
cd /Users/seaton/Documents/src/madeinoz-knowledge-system

# Start containers (Neo4j + MCP server)
bun run start

# Verify health
curl http://localhost:8000/health
```

### 2. Create Feature Branch

```bash
git checkout -b 009-memory-decay-scoring
```

### 3. Install Python Dependencies

```bash
cd docker/patches
pip install -e ".[dev]"  # If pyproject.toml exists
# OR
pip install pydantic pytest pytest-asyncio
```

## Development Workflow

### Running Tests

```bash
# Python unit tests
cd docker/patches
pytest tests/unit -v

# Python integration tests (requires running Neo4j)
pytest tests/integration -v

# TypeScript tests
bun test
```

### Testing MCP Tools

```bash
# Test add_memory with importance classification
bun run src/skills/tools/test-mcp.ts add_memory \
  --content "I prefer dark mode in all applications" \
  --source "user_preference"

# Test weighted search
bun run src/skills/tools/test-mcp.ts search_memory_nodes \
  --query "user preferences"

# Test health metrics (after decay implementation)
bun run src/skills/tools/test-mcp.ts get_knowledge_health
```

### Direct Cypher Testing

```bash
# Connect to Neo4j browser
open http://localhost:7474

# Test decay score query
MATCH (n:Entity)
WHERE n.`attributes.lifecycle_state` = 'ACTIVE'
RETURN n.name, n.`attributes.importance`, n.`attributes.decay_score`
LIMIT 10;

# Test weighted search
CALL db.index.vector.queryNodes('entity_name_embedding', 10, $embedding)
YIELD node, score
WITH node, score,
     coalesce(node.`attributes.importance`, 3) / 5.0 AS imp,
     exp(-0.0231 * duration.between(node.created_at, datetime()).days) AS rec
RETURN node.name, 0.6*score + 0.25*rec + 0.15*imp AS weighted
ORDER BY weighted DESC;
```

## File Structure

After implementing this feature:

```
docker/patches/
├── graphiti_mcp_server.py      # Extended with decay tools
├── memory_decay.py             # NEW: Decay calculation
├── importance_classifier.py    # NEW: LLM classification
├── lifecycle_manager.py        # NEW: State transitions
├── maintenance_service.py      # NEW: Batch processing
└── tests/
    ├── unit/
    │   ├── test_memory_decay.py
    │   ├── test_importance_classifier.py
    │   └── test_lifecycle_manager.py
    └── integration/
        └── test_decay_integration.py

src/skills/
├── SKILL.md                    # Updated with health intents
└── workflows/
    └── health-report.md        # NEW: Health workflow

config/
└── decay-config.yaml           # NEW: Decay configuration
```

## Key Implementation Points

### 1. Decay Calculation Module

`docker/patches/memory_decay.py`:

```python
from math import exp, log
from datetime import datetime, timezone

class DecayCalculator:
    def __init__(self, base_half_life: float = 30.0):
        self.base_half_life = base_half_life

    def calculate(
        self,
        importance: int,
        stability: int,
        last_accessed: datetime | None,
        created_at: datetime
    ) -> float:
        # Permanent memories don't decay
        if importance >= 4 and stability >= 4:
            return 0.0

        reference = last_accessed or created_at
        now = datetime.now(timezone.utc)
        days = (now - reference).days

        # Half-life adjusted by stability
        half_life = self.base_half_life * (stability / 3.0)
        lambda_rate = log(2) / half_life

        # Importance slows decay
        adjusted = lambda_rate * (6 - importance) / 5

        return round(1.0 - exp(-adjusted * days), 3)
```

### 2. Importance Classifier

`docker/patches/importance_classifier.py`:

```python
CLASSIFICATION_PROMPT = """
Classify this memory for importance and stability.

Memory: {content}

Importance (1-5):
1 = Trivial (can forget immediately)
2 = Low (useful but replaceable)
3 = Moderate (general knowledge)
4 = High (important to work/identity)
5 = Core (fundamental, never forget)

Stability (1-5):
1 = Volatile (changes in hours/days)
2 = Low (changes in days/weeks)
3 = Moderate (changes in weeks/months)
4 = High (changes in months/years)
5 = Permanent (never changes)

Respond with JSON: {{"importance": N, "stability": N}}
"""

async def classify_memory(content: str, llm_client) -> tuple[int, int]:
    try:
        response = await llm_client.complete(
            CLASSIFICATION_PROMPT.format(content=content)
        )
        result = json.loads(response)
        return result["importance"], result["stability"]
    except Exception:
        return 3, 3  # Neutral defaults
```

### 3. Weighted Search Extension

Modify `graphiti_mcp_server.py`:

```python
def calculate_weighted_score(
    semantic_score: float,
    days_since_access: int,
    importance: int,
    half_life: float = 30.0
) -> float:
    recency = exp(-0.693 * days_since_access / half_life)
    importance_norm = importance / 5.0
    return (0.60 * semantic_score +
            0.25 * recency +
            0.15 * importance_norm)
```

## Testing Checklist

- [ ] Decay calculation returns 0.0 for permanent memories
- [ ] Decay score increases with time since access
- [ ] Higher importance = slower decay
- [ ] Higher stability = slower decay
- [ ] Lifecycle transitions occur at correct thresholds
- [ ] Soft-delete retains memory for 90 days
- [ ] Recovery restores to ARCHIVED state
- [ ] Weighted search ranks fresh important memories higher
- [ ] Maintenance completes within 10 minutes
- [ ] Health metrics accurately reflect graph state

## Configuration

### Environment Variables

```bash
# Decay configuration
export DECAY_BASE_HALF_LIFE_DAYS=30
export DECAY_DORMANT_THRESHOLD_DAYS=30
export DECAY_ARCHIVED_THRESHOLD_DAYS=90
export DECAY_SOFT_DELETE_RETENTION_DAYS=90

# Weights
export DECAY_WEIGHT_SEMANTIC=0.60
export DECAY_WEIGHT_RECENCY=0.25
export DECAY_WEIGHT_IMPORTANCE=0.15

# Maintenance
export DECAY_MAINTENANCE_BATCH_SIZE=500
```

### YAML Config

`config/decay-config.yaml` - See [data-model.md](./data-model.md) for full schema.

## Troubleshooting

### Decay scores not updating

1. Check maintenance job ran: `bun run src/skills/tools/test-mcp.ts get_knowledge_health`
2. Verify Neo4j connectivity: `curl http://localhost:7474`
3. Check logs: `bun run logs`

### LLM classification failing

1. Verify OpenAI API key: `echo $OPENAI_API_KEY`
2. Check rate limits in logs
3. Memories should get default scores (3, 3) on failure

### Weighted search not working

1. Ensure attributes exist on nodes (run backfill migration)
2. Check vector index exists: `SHOW INDEXES` in Neo4j
3. Verify `lifecycle_state` filter is working

## Next Steps

After feature implementation:

1. Run `/speckit.tasks` to generate implementation tasks
2. Follow task order respecting dependencies
3. Run tests after each module
4. Update CHANGELOG.md with feature summary
