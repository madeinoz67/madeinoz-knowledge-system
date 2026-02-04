# Investigative Search Quickstart

**Feature**: 020-investigative-search
**Last Updated**: 2026-02-04

## What is Investigative Search?

Investigative search lets you find an entity and see all its connected relationships in a single query. Instead of searching for entities, then searching for relationships, then looking up each UUID to get names—you get everything at once.

**Perfect for**:
- OSINT investigations (tracking people, phone numbers, accounts)
- CTI analysis (threat actors, malware, vulnerabilities)
- Relationship mapping (who knows whom, what uses what)

---

## Quick Start

### Basic Investigation

```bash
# Investigate a phone number
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts investigate "+1-555-0199"

# Investigate a threat actor
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts investigate "APT28"
```

**Response includes**:
- The entity you searched for (with name, type, UUID)
- All directly connected entities (with names, types, UUIDs)
- Relationship types between entities

---

## Depth Control

Control how many "hops" to explore:

```bash
# 1-hop (default): Direct connections only
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts investigate "+1-555-0199"

# 2-hop: Friends of friends
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts investigate --depth 2 "+1-555-0199"

# 3-hop: Extended network
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts investigate --depth 3 "+1-555-0199"
```

**What each depth means**:
| Depth | Description | Example |
|-------|-------------|---------|
| 1 | Direct connections | Phone → Person |
| 2 | Friends of friends | Phone → Person → Organization |
| 3 | Extended network | Phone → Person → Organization → Industry |

---

## Relationship Filtering

Focus on specific relationship types:

```bash
# Only OWNED_BY relationships
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts investigate \
  --relationship-type OWNED_BY "+1-555-0199"

# Multiple relationship types
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts investigate \
  --relationship-type OWNED_BY \
  --relationship-type CONTACTED_VIA \
  "+1-555-0199"
```

**Common relationship types**:
- `OWNED_BY` - Ownership/possession
- `CONTACTED_VIA` - Communication method
- `USES` - Tool/weapon usage (CTI)
- `TARGETS` - Attack target (CTI)
- `HOSTED_ON` - Hosting location

---

## OSINT/CTI Workflows

### Workflow 1: Track a Phone Number

```bash
# Step 1: Investigate the phone
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts investigate "+1-555-0199"

# Step 2: Deep dive with 2-hop traversal
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts investigate \
  --depth 2 "+1-555-0199"

# Step 3: Filter by ownership only
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts investigate \
  --relationship-type OWNED_BY \
  "+1-555-0199"
```

### Workflow 2: Threat Actor Analysis

```bash
# Step 1: Investigate threat actor
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts investigate "APT28"

# Step 2: Find what malware they use
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts investigate \
  --relationship-type USES \
  --depth 2 \
  "APT28"

# Step 3: Find their targets
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts investigate \
  --relationship-type TARGETS \
  "APT28"
```

### Workflow 3: Account Correlation

```bash
# Step 1: Start with social media account
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts investigate "@suspicious_actor"

# Step 2: Find 2-hop connections (accounts, emails, domains)
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts investigate \
  --depth 2 \
  "@suspicious_actor"
```

---

## Understanding the Response

### Response Structure

```json
{
  "entity": {
    "uuid": "...",
    "name": "+1-555-0199",
    "labels": ["Phone"],
    "attributes": { ... }
  },
  "connections": [
    {
      "relationship": "OWNED_BY",
      "direction": "incoming",
      "target_entity": {
        "uuid": "...",
        "name": "John Doe",
        "labels": ["Person"]
      },
      "hop_distance": 1,
      "fact": "Phone owned by John Doe"
    }
  ],
  "metadata": {
    "depth_explored": 1,
    "connections_returned": 2,
    "cycles_detected": 0
  }
}
```

### Key Fields

| Field | Description |
|-------|-------------|
| `entity` | The entity you searched for |
| `connections` | Array of connected entities |
| `relationship` | Type of relationship (e.g., OWNED_BY) |
| `direction` | `outgoing` (→), `incoming` (←), or `bidirectional` (↔) |
| `hop_distance` | How many hops from the primary entity (1-3) |
| `cycles_detected` | Number of circular relationships found |

---

## Cycle Detection

The system automatically detects circular relationships:

```json
{
  "metadata": {
    "cycles_detected": 2,
    "cycles_pruned": ["uuid-abc", "uuid-def"]
  }
}
```

**What this means**:
- Your data contains cycles (e.g., A employs B, B employs A)
- The system pruned duplicates to prevent infinite loops
- You can see how many cycles were detected

---

## Performance & Limits

| Metric | Limit |
|--------|-------|
| Max depth | 3 hops |
| Max connections (warning) | 500 |
| Target response time | < 2 seconds (100 connections) |

**If you see a warning**:
```
Found 1,247 connections (showing first 500).
Use --relationship-type filter to narrow results.
```

**Solution**: Add `--relationship-type` filters to reduce noise.

---

## Common Use Cases

### Find who owns a phone

```bash
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts investigate \
  --relationship-type OWNED_BY \
  "+1-555-0199"
```

### Find what malware a threat actor uses

```bash
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts investigate \
  --relationship-type USES \
  "APT28"
```

### Find all accounts related to a person

```bash
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts investigate \
  --relationship-type CONTACTED_VIA \
  --depth 2 \
  "John Doe"
```

---

## Tips

1. **Start shallow**: Use depth 1 first, then increase to 2 or 3
2. **Filter early**: Use `--relationship-type` to narrow results
3. **Check metadata**: Look for `cycles_detected` and warnings
4. **Use the UUIDs**: Response includes UUIDs for programmatic follow-up

---

## Troubleshooting

### "Entity not found"

The search didn't match any entities. Try:
- Using a more general search term
- Checking for typos in the entity name
- Using `search_nodes` first to find the exact name

### "No connections found"

The entity exists but has no connections. This is normal for:
- Newly created entities
- Isolated entities with no relationships

### Warning about too many connections

The entity has many connections (e.g., a hub entity). Use:
- `--relationship-type` filters
- Reduce depth to 1 or 2

---

## Next Steps

- Read the [full specification](./spec.md) for detailed requirements
- See the [data model](./data-model.md) for response structure
- Check [API contract](./contracts/investigate-entity.yaml) for implementation details
