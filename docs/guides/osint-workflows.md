---
title: "OSINT & CTI Workflows"
description: "Using the Madeinoz Knowledge System for Open Source Intelligence and Cyber Threat Intelligence"
---

# OSINT & CTI Workflows

> The Madeinoz Knowledge System supports custom entity types and relationships for OSINT (Open Source Intelligence) and CTI (Cyber Threat Intelligence) workflows.

## Overview

The Knowledge System includes pre-configured entity types for threat intelligence:

- **ThreatActor** - APT groups, threat actors (180-day half-life)
- **Malware** - Malicious software families (90-day half-life)
- **Vulnerability** - CVE entries, security flaws (180-day half-life)
- **Campaign** - Coordinated attack campaigns (120-day half-life)
- **Indicator** - IOCs, hashes, IPs, domains (90-day half-life)
- **Infrastructure** - C2 servers, attack infrastructure (60-day half-life)
- **TTP** - Tactics, techniques, procedures (365-day half-life)

## Custom Relationship Types

The system supports CTI-specific relationship patterns:

| Relationship | From → To | Example |
|-------------|-----------|---------|
| `uses` | ThreatActor → Malware | APT28 uses SnakeKeylogger |
| `exploits` | Malware → Vulnerability | LockBit exploits CVE-2023-XXX |
| `targets` | Campaign → Organization | Operation Panda targets finance |
| `attributed_to` | Campaign → ThreatActor | Campaign attributed to APT29 |
| `located_at` | Infrastructure → Location | C2 server located in Country X |
| `variant_of` | Malware → Malware | LockBit 3.0 variant_of LockBit 2.0 |

## Investigative Search

The `investigate` command enables multi-hop relationship traversal to discover connections in your threat intelligence data.

### Basic Entity Investigation

```bash
# Find all connections for a threat actor
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts --profile development investigate "APT28"
```

This returns:
- **Primary entity**: APT28 (name, type, UUID)
- **Connections**: All entities 1 hop away (malware used, infrastructure, indicators)
- **Metadata**: Query duration, depth explored, cycles detected

### Multi-Hop Analysis

```bash
# 2-hop traversal (friends of friends)
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts --profile development investigate "APT28" --depth 2
```

**Use cases:**
- Depth 1: Direct relationships (malware used by this actor)
- Depth 2: Second-order relationships (infrastructure used by malware, campaigns)
- Depth 3: Extended analysis (supply chain relationships)

**Warning**: High depth (3+) can return hundreds of connections. Use `--relationship-type` to filter.

### Relationship Type Filtering

```bash
# Only find malware used by a threat actor
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts --profile development \
  investigate "APT28" --relationship-type uses

# Find exploitation relationships
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts --profile development \
  investigate "LockBit" --relationship-type exploits

# Multiple relationship types
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts --profile development \
  investigate "APT28" --relationship-type uses,targets
```

## Workflow Examples

### Example 1: Track APT Campaign Evolution

```bash
# 1. Capture threat intelligence data
echo "APT28 targeted finance sector in Q1 2024 using SnakeKeylogger" | \
  bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts --profile development capture

# 2. Investigate the threat actor
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts --profile development \
  investigate "APT28" --depth 2
```

**Returns connected graph:**
```
APT28
├── [uses] → SnakeKeylogger (Malware)
├── [targets] → FinanceOrg (Organization)
└── [attributed_to] → OperationSeason (Campaign)
```

### Example 2: Malware Family Analysis

```bash
# 1. Investigate malware variant relationships
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts --profile development \
  investigate "LockBit 3.0" --relationship-type variant_of

# 2. Find all exploitation relationships
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts --profile development \
  investigate "LockBit" --depth 2 --relationship-type exploits
```

### Example 3: Infrastructure Tracking

```bash
# Track C2 infrastructure
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts --profile development \
  investigate "192.168.1.100" --depth 2
```

This can reveal:
- Which malware families used this IP
- Which threat actors operate this infrastructure
- Related indicators (domains, hashes)

## STIX 2.1 Import

The Knowledge System supports importing STIX 2.1 JSON data for CTI integration.

```python
from knowledge_graph import KnowledgeGraph
import json

# Load STIX 2.1 bundle
with open('stix_bundle.json') as f:
    stix_data = json.load(f)

# Add as episode with STIX metadata
graph = KnowledgeGraph()
graph.add_episode(
    name="STIX Import: APT28 Report",
    episode_body=json.dumps(stix_data),
    source="stix",
    source_description="MITRE ATT&CK STIX 2.1 bundle"
)
```

## Configuration Reference

### OSINT/CTI Entity Type Configuration

Entity types are configured in `config/ontology-types.yaml`:

```yaml
entity_types:
  - name: "ThreatActor"
    description: "Actor responsible for cyber threats"
    decay_config:
      half_life_days: 180  # Longer half-life for slow-changing CTI data
      importance_floor: 0.5
      stability_multiplier: 1.2

  - name: "Malware"
    description: "Malicious software families"
    decay_config:
      half_life_days: 90   # Fast-changing indicators
      importance_floor: 0.3
      stability_multiplier: 0.8
```

### Relationship Type Configuration

```yaml
relationship_types:
  - name: "uses"
    description: "Source uses target (e.g., ThreatActor uses Malware)"
    source_entity_types: ["ThreatActor", "Campaign"]
    target_entity_types: ["Malware", "Infrastructure", "TTP"]
    bidirectional: false
```

## Memory Decay for CTI Data

CTI data has different decay characteristics than personal knowledge:

- **TTPs**: Long-lived (365-day half-life) - changes rarely
- **ThreatActors**: Medium-lived (180-day) - new TTPs discovered over time
- **Indicators**: Short-lived (60-90 days) - rapidly changing IOCs
- **Infrastructure**: Very short-lived (60-day) - domains/IPs rotate quickly

**Importance Classification:**
- Permanent memories (importance ≥ 4 AND stability ≥ 4) are protected from decay
- Example: High-confidence APT attributions, well-established TTPs

## MCP Tool Access

From AI assistants or scripts:

```python
from knowledge_mcp_client import KnowledgeMCPClient

client = KnowledgeMCPClient()

# Investigate entity with 2-hop depth
result = client.investigate_entity(
    entity_name="APT28",
    max_depth=2,
    relationship_types=["uses", "targets"]
)

# Access results
print(f"Entity: {result['entity']['name']}")
print(f"Connections: {len(result['connections'])}")
for conn in result['connections']:
    print(f"  - {conn['relationship']}: {conn['target_entity']['name']}")
```

## Best Practices

### 1. Use Separate Groups for CTI Data

```bash
# Set environment variable
export MADEINOZ_KNOWLEDGE_GROUP_ID=osint-intel

# Or use profile
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts --profile development \
  search_nodes "APT28" --group-id osint-intel
```

### 2. Leverage Weighted Search for Recent IOCs

```bash
# Prioritize important, recent threat intel
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts --profile development \
  search_facts "LockBit ransomware" --weighted
```

Weighted search considers:
- **Semantic similarity (60%)** - Relevance to query
- **Recency (25%)** - Recent memories ranked higher
- **Importance (15%)** - High-importance CTI data prioritized

### 3. Run Maintenance Regularly

```bash
# Clean up expired IOCs and stale infrastructure data
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts --profile development \
  run_maintenance --dry-run  # Preview first
```

## Related Documentation

- [Configuration Reference](../reference/configuration.md) - Entity and relationship type configuration
- [CLI Reference](../reference/cli.md) - Investigate command syntax
- [Memory Decay](../usage/memory-decay.md) - Decay scoring for CTI data
- [Remote Access](../remote-access.md) - Connection profiles for CTI databases
