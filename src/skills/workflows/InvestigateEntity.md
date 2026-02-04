# Investigative Search Workflow

**Feature 020**: Graph traversal for entity connection analysis

## Triggers

- "investigate entity", "investigate [entity name]"
- "find connections", "show connections", "entity connections"
- "graph traversal", "connected entities", "entity network"
- "threat hunting", "related entities", "link analysis"

## Purpose

Discover entities connected to a target entity through graph traversal, enabling:
- **Threat Hunting**: Trace malware to threat actors, infrastructure, and campaigns
- **OSINT Analysis**: Map relationships between accounts, domains, and investigations
- **Knowledge Exploration**: Find related concepts, people, and organizations

## Usage

### Basic Investigation

```bash
# Investigate an entity (1-hop by default)
bun run tools/knowledge-cli.ts investigate "apt28"

# Investigate with deeper traversal
bun run tools/knowledge-cli.ts investigate "apt28" --depth 2
bun run tools/knowledge-cli.ts investigate "trinity-mini" --depth 3
```

### Filter by Relationship Type

```bash
# Only show specific relationship types
bun run tools/knowledge-cli.ts investigate "apt28" --relationship-type attributed_to --relationship-type uses

# Combine depth and relationship filters
bun run tools/knowledge-cli.ts investigate "malware-x" --depth 2 --relationship-type variant_of
```

## Options

| Option | Description | Default | Range |
|--------|-------------|---------|-------|
| `--depth <N>` | Traversal depth (hops from source) | 1 | 1-3 |
| `--relationship-type` | Filter by relationship type (multiple allowed) | All types | Any valid type |

## Output Format

```
Entity: [TYPE] name - summary
Created: [timestamp] | Importance: [score] | Stability: [score]

Connections (2-hop):
  1. [RELATIONSHIP] target-name [TYPE] (hop 1)
     → [RELATIONSHIP] next-target [TYPE] (hop 2)

Investigation completed in 234ms
```

## Relationship Types

**Standard**: related_to, contains, located_at, part_of

**CTI (Feature 018)**:
- `uses` - Malware uses TTPs
- `targets` - Campaign targets organization
- `attributed_to` - Attack attributed to threat actor
- `exploits` - Malware exploits vulnerability
- `variant_of` - Malware is variant of parent

**OSINT (Feature 018)**:
- `owns` - Person owns account
- `hosted_on` - Domain hosted on infrastructure
- `investigates` - Investigation investigates entity
- `links_to` - Indicator links to infrastructure

## Examples

### Example 1: Threat Actor Investigation

User: "Investigate apt28 connections"

```bash
bun run tools/knowledge-cli.ts investigate "apt28" --depth 2
```

Output:
```
Entity: THREAT_ACTOR APT28 - Russian state-sponsored threat actor
Created: 2026-01-15 | Importance: 5 | Stability: 5

Connections (2-hop):
  1. [attributed_to] Sandworm Team [THREAT_ACTOR] (hop 1)
  2. [uses] Covenant [MALWARE] (hop 1)
     → [exploits] CVE-2023-1234 [VULNERABILITY] (hop 2)
  3. [targets] Energy Sector [ORGANIZATION] (hop 1)
  4. [uses] Sobek [MALWARE] (hop 1)
     → [variant_of] Sombra [MALWARE] (hop 2)

Investigation completed in 456ms
```

### Example 2: OSINT Account Analysis

User: "Find connections to @suspicious_user"

```bash
bun run tools/knowledge-cli.ts investigate "@suspicious_user" --depth 2 --relationship-type owns
```

### Example 3: Malware Family Tracing

User: "Show what trinity-mini connects to"

```bash
bun run tools/knowledge-cli.ts investigate "trinity-mini" --depth 3
```

## Use Cases

| Domain | Example | Depth |
|--------|---------|-------|
| **Threat Intel** | Trace malware → threat actor → campaign | 2-3 |
| **OSINT** | Map account → person → other accounts | 2 |
| **Due Diligence** | Company → subsidiaries → executives | 2 |
| **Research** | Concept → related concepts → documents | 1-2 |

## Performance Notes

- **Depth 1**: < 100ms typical
- **Depth 2**: 100-500ms typical
- **Depth 3**: 500-2000ms typical (highly connected entities)

**Warning**: Entities with 500+ connections may trigger performance alerts.

## Related Workflows

- **SearchKnowledge** - Find entities by semantic search
- **SearchFacts** - Find specific relationships
- **OntologyManagement** - Configure custom entity/relationship types
