# STIX Import Workflow

**Feature 018**: Import STIX 2.1 bundles for threat intelligence

## Triggers

- "import STIX", "STIX bundle", "threat intel import", "CTI data"
- "import threat intelligence", "load STIX file", "MITRE ATT&CK"

## Purpose

Import cyber threat intelligence from STIX 2.1 (Structured Threat Information Expression) bundles into the knowledge graph, enabling:
- **MITRE ATT&CK Integration**: Import techniques, tactics, and actor data
- **Threat Intel Feeds**: Commercial CTI feeds (Recorded Future, Flashpoint, etc.)
- **Vulnerability Data**: CVE records in STIX format
- **Indicator Sharing**: IoC exchange between teams and tools

## Supported STIX Objects

| STIX Type | Mapped To | Description |
|-----------|-----------|-------------|
| `threat-actor` | ThreatActor | APT groups, malicious actors |
| `malware` | Malware | Malicious software families |
| `vulnerability` | Vulnerability | CVE records, security flaws |
| `indicator` | Indicator | IoCs (IPs, domains, hashes, emails) |
| `attack-pattern` | TTP | MITRE ATT&CK techniques |
| `infrastructure` | Infrastructure | C2 servers, attack infrastructure |
| `campaign` | Campaign | Coordinated threat activities |
| `identity` | Organization/Organization | Companies, agencies |
| `location` | Location | Countries, regions |
| `relationship` | Custom Relationship | STIX relationships |

## CLI Commands

### Import STIX Bundle

```bash
# Import from local file
bun run tools/knowledge-cli.ts stix:import ./apt28-stix.json

# Import from URL
bun run tools/knowledge-cli.ts stix:import https://attack.mitre.org/docs/APT28-STIX.json

# Import with group_id specified
bun run tools/knowledge-cli.ts stix:import ./threat-intel.json --group-id cti-feed
```

### Check Import Status

```bash
# Get latest import status
bun run tools/knowledge-cli.ts stix:status
```

Output:
```
STIX Import Status:
  Last Import: 2026-02-04T12:00:00Z
  Source: apt28-stix.json
  Status: SUCCESS
  Objects Processed: 47
    - threat-actor: 1
    - malware: 3
    - indicator: 28
    - attack-pattern: 8
    - relationship: 7
  Errors: 0
  Duration: 2.3s
```

## Import Process

1. **Parse STIX Bundle** - Validate JSON and STIX 2.1 schema
2. **Map Object Types** - Convert STIX types to ontology entities
3. **Extract Relationships** - Create edges between entities
4. **Store Episodes** - Each bundle becomes an episode with source tracking
5. **Report Results** - Summary of objects processed and any errors

## STIX to Knowledge Graph Mapping

### Entity Mapping

| STIX Object | Knowledge Entity | Example |
|-------------|------------------|---------|
| `threat-actor` | ThreatActor | APT28, Sandworm |
| `malware` | Malware | TrickBot, LockBit |
| `vulnerability` | Vulnerability | CVE-2023-23397 |
| `indicator` | Indicator | IP, domain, hash |
| `attack-pattern` | TTP | Phishing, Lateral Movement |
| `infrastructure` | Infrastructure | C2 servers |
| `campaign` | Campaign | Operation names |
| `identity` (class=organization) | Organization | Target companies |

### Relationship Mapping

| STIX Relationship | Knowledge Relationship |
|-------------------|----------------------|
| `uses` | uses |
| `targets` | targets |
| `attributed-to` | attributed_to |
| `exploits` | exploits |
| `related-to` | associated_with |
| `located-at` | located_at |
| `communicates-with` | communicates_with |

## Examples

### Example 1: Import MITRE ATT&CK Data

User: "Import APT28 from MITRE ATT&CK"

```bash
bun run tools/knowledge-cli.ts stix:import https://attack.mitre.org/docs/APT28-STIX.json
```

Result:
```
✓ Importing from: https://attack.mitre.org/docs/APT28-STIX.json
  Processing STIX 2.1 bundle...
  ✓ Parsed 47 STIX objects
  ✓ Created 1 ThreatActor: APT28
  ✓ Created 3 Malware: X-Agent, X-Tunnel, Sedreco
  ✓ Created 28 Indicators: IPs, domains, hashes
  ✓ Created 8 TTPs: attack techniques
  ✓ Created 7 relationships

  Import complete: 47 objects in 2.3s
```

### Example 2: Import Vulnerability Feed

User: "Import CVE data from STIX file"

```bash
bun run tools/knowledge-cli.ts stix:import ./cve-feed-2024.json --group-id vulnerabilities
```

### Example 3: Import Commercial CTI Feed

User: "Load Recorded Future export"

```bash
bun run tools/knowledge-cli.ts stix:import ./recorded-future-export.json
```

### Example 4: Check Import Results

User: "Did the last import work?"

```bash
bun run tools/knowledge-cli.ts stix:status
```

## Input Formats

**Local Files:**
- JSON files with `.json` extension
- STIX 2.1 bundle format

**URLs:**
- HTTP/HTTPS URLs
- Must return valid STIX 2.1 JSON

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `Invalid STIX format` | Not STIX 2.1 JSON | Validate file format |
| `Unknown object type` | Unsupported STIX type | Check object mapping |
| `Missing required field` | Malformed STIX object | Fix source data |
| `Network error` | URL unreachable | Check URL or download first |

## Best Practices

1. **Validate First** - Check STIX files with online validator before import
2. **Use Groups** - Separate feeds by `--group-id` for better organization
3. **Check Status** - Run `stix:status` after import to verify results
4. **Investigate After** - Use `investigate` command to explore imported entities

## Investigation After Import

After importing STIX data, use investigative search:

```bash
# Explore imported threat actor
bun run tools/knowledge-cli.ts investigate "APT28" --depth 2

# Find all malware used by actor
bun run tools/knowledge-cli.ts investigate "APT28" --relationship-type uses

# Trace indicators to infrastructure
bun run tools/knowledge-cli.ts investigate "192.168.1.1" --depth 2 --relationship-type hosted_on
```

## Related Workflows

- **InvestigateEntity** - Explore imported threat intel relationships
- **OntologyManagement** - Configure STIX object type mappings
- **SearchKnowledge** - Find imported entities by semantic search

## STIX Resources

- **STIX 2.1 Specification**: https://oasis-tcs.github.io/cti-documentation/
- **MITRE ATT&CK STIX**: https://attack.mitre.org/docs/
- **STIX Validator**: https://github.com/oasis-tcs/cti-python-stix2

## MCP Tools

| Tool | Description |
|------|-------------|
| `import_stix_bundle` | Import STIX 2.1 bundle from file or URL |
| `get_stix_import_status` | Get status of most recent import |
