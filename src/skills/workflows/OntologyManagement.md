# Ontology Management Workflow

**Feature 018**: OSINT/CTI custom entity and relationship types

## Triggers

- "list ontology", "custom entity types", "CTI entities", "OSINT entities"
- "ontology config", "validate ontology", "check ontology"
- "reload ontology", "refresh ontology types"

## Purpose

Manage custom entity types and relationship types for Cyber Threat Intelligence (CTI) and Open Source Intelligence (OSINT) workflows.

## OSINT/CTI Entity Types

### CTI Entities

| Type | Description | Example |
|------|-------------|---------|
| **ThreatActor** | Malicious actors, APT groups | APT28, Sandworm |
| **Malware** | Malicious software, ransomware | LockBit 3.0, TrickBot |
| **Vulnerability** | CVE, security flaws | CVE-2023-23397 |
| **Campaign** | Coordinated threat activities | Operation Winter Vivern |
| **Indicator** | IoCs, hashes, IPs, domains | 192.168.1.1, malware.exe |
| **Infrastructure** | C2 servers, attack infrastructure | malicious-c2[.]com |
| **TTP** | Tactics, Techniques, Procedures | Phishing, Lateral Movement |

### OSINT Entities

| Type | Description | Example |
|------|-------------|---------|
| **Account** | Social media, email accounts | @target_user, admin@example.com |
| **Domain** | Registered domains, DNS | suspicious-domain[.]com |
| **Email** | Email addresses | target@company.com |
| **Phone** | Phone numbers, mobile devices | +1-555-0123 |
| **Image** | Photos, screenshots, media | evidence_screenshot.png |
| **Investigation** | OSINT investigations, cases | Case-2024-001 |

## Relationship Types

### CTI Relationships

| Relationship | From → To | Example |
|--------------|-----------|---------|
| `uses` | ThreatActor/Malware → TTP | APT28 uses Phishing |
| `targets` | ThreatActor/Campaign → Org | APT28 targets Energy Sector |
| `attributed_to` | Attack → ThreatActor | Attack attributed to APT28 |
| `exploits` | Malware → Vulnerability | LockBit exploits CVE-2023-1234 |
| `variant_of` | Malware → Malware | BlackCat variant of ALPHV |
| `located_at` | Infrastructure → Location | C2 located_at Russia |
| `communicates_with` | Infrastructure → Infrastructure | Bot1 communicates_with C2 |
| `associated_with` | Any → Any | Campaign associated_with ThreatActor |

### OSINT Relationships

| Relationship | From → To | Example |
|--------------|-----------|---------|
| `owns` | Person → Account | User owns @twitter_handle |
| `registered_to` | Domain → Person/Org | Domain registered_to John Doe |
| `hosted_on` | Domain → Infrastructure | Domain hosted_on 1.2.3.4 |
| `contacted_via` | Person → Phone/Email | User contacted_via phone |
| `contains` | Investigation → Evidence | Case contains image |
| `investigates` | Investigation → Entity | Case investigates ThreatActor |
| `links_to` | Indicator → Infrastructure | IP links_to Domain |
| `exposes` | Evidence → Entity | Screenshot exposes Account |

## CLI Commands

### List Ontology Types

```bash
# Show all custom entity and relationship types
bun run tools/knowledge-cli.ts ontology:list
```

Output:
```
Custom Entity Types (13):
  CTI: ThreatActor, Malware, Vulnerability, Campaign, Indicator, Infrastructure, TTP
  OSINT: Account, Domain, Email, Phone, Image, Investigation

Custom Relationship Types (17):
  CTI: uses, targets, attributed_to, exploits, variant_of, located_at, communicates_with, associated_with
  OSINT: owns, registered_to, hosted_on, contacted_via, contains, investigates, links_to, exposes

Configured from: config/ontology-types.yaml
Template: cti-base (7 entity types, 8 relationship types)
Loaded: 2026-02-04T12:00:00Z
```

### Validate Ontology

```bash
# Validate ontology configuration
bun run tools/knowledge-cli.ts ontology:validate
```

Output:
```
✓ Ontology configuration is valid
  - 13 entity types defined
  - 17 relationship types defined
  - No duplicate type names
  - No invalid YAML syntax
```

### Reload Ontology

```bash
# Hot-reload ontology configuration (no restart required)
bun run tools/knowledge-cli.ts ontology:reload
```

Use after editing `config/ontology-types.yaml` or `config/ontologies/` templates.

## Configuration

Ontology types are configured in `config/ontology-types.yaml`:

```yaml
custom_entity_types:
  cti:
    - ThreatActor
    - Malware
    - Vulnerability
    - Campaign
    - Indicator
    - Infrastructure
    - TTP
  osint:
    - Account
    - Domain
    - Email
    - Phone
    - Image
    - Investigation

custom_relationship_types:
  cti:
    - uses
    - targets
    - attributed_to
    # ... more types
  osint:
    - owns
    - registered_to
    # ... more types
```

## Templates

Pre-built ontology templates available in `config/ontologies/`:

| Template | Description | File |
|----------|-------------|------|
| `cti-base` | Basic CTI entities (7) | `cti-base.yaml` |
| `mitre-attack` | MITRE ATT&CK aligned | `mitre-attack.yaml` |
| `osint-base` | OSINT entities (6) | `osint-base.yaml` |

Switch templates by editing `config/ontology-types.yaml` and reloading.

## Examples

### Example 1: List Available Types

User: "What entity types are available?"

```bash
bun run tools/knowledge-cli.ts ontology:list
```

### Example 2: Validate After Edit

User: "Check if my ontology config is valid"

```bash
bun run tools/knowledge-cli.ts ontology:validate
```

### Example 3: Apply New Configuration

User: "I added custom types, reload the config"

```bash
bun run tools/knowledge-cli.ts ontology:reload
```

## Related Workflows

- **InvestigateEntity** - Use custom entity types for graph traversal
- **StixImport** - Import STIX 2.1 bundles with custom types
- **CaptureEpisode** - Episodes automatically extract custom entities

## MCP Tools

| Tool | Description |
|------|-------------|
| `list_ontology_types` | List custom entity and relationship types |
| `validate_ontology` | Validate ontology configuration |
| `reload_ontology` | Hot-reload ontology from config file |
