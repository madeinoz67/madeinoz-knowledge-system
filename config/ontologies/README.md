# Ontology Templates

This directory contains pre-built ontology templates for CTI and OSINT analysis.

## Available Templates

### CTI Base Ontology (`cti-base.yaml`)
Core Cyber Threat Intelligence entity and relationship types.

**Entity Types:**
- ThreatActor - APT groups, threat actors
- Malware - Ransomware, trojans, backdoors
- Vulnerability - CVE entries, security flaws
- Campaign - Coordinated attack campaigns
- Indicator - IOCs (hashes, IPs, domains)
- Infrastructure - C2 servers, attack infrastructure
- TTP - Tactics, Techniques, Procedures (MITRE ATT&CK)

**Relationship Types:**
- uses, targets, associated_with, attributed_to, exploits, variant_of, located_at, communicates_with

### MITRE ATT&CK Extension (`mitre-attack.yaml`)
Extends CTI Base with MITRE ATT&CK tactics and techniques.

**Entity Types:**
- Tactic - MITRE ATT&CK tactical objectives (e.g., TA0042)
- Technique - MITRE ATT&CK techniques (e.g., T1566)
- Mitigation - Security countermeasures
- DataSource - Detection data sources

**Relationship Types:**
- achieves_tactic, mitigates, detects, uses_technique, subtechnique_of

**Dependencies:** Requires `cti-base` template

### OSINT Base Ontology (`osint-base.yaml`)
Core Open Source Intelligence entity and relationship types.

**Entity Types:**
- Account - Social media and service accounts
- Domain - Registered domains and DNS entries
- Email - Email addresses
- Phone - Phone numbers
- Image - Photos with EXIF data
- Investigation - OSINT investigation cases

**Relationship Types:**
- owns, registered_to, hosted_on, contacted_via, contains, investigates, links_to, exposes

## Usage

### Option 1: Copy Template to Config
Copy a template to `config/ontology-types.yaml`:
```bash
cp config/ontologies/cti-base.yaml config/ontology-types.yaml
bun run server-cli restart
```

### Option 2: Merge Multiple Templates
Edit `config/ontology-types.yaml` to merge templates:
```yaml
version: "1.0.0"
name: "My Custom Ontology"
description: "Combines CTI and OSINT templates"
depends_on: []
# Include CTI types directly, then extend with OSINT types
```

### Option 3: Programmatic Merge (Python)
```python
from patches.ontology_config import load_ontology_config, merge_ontologies

# Load templates
cti = load_ontology_config("config/ontologies/cti-base.yaml")
osint = load_ontology_config("config/ontologies/osint-base.yaml")

# Merge them
combined = merge_ontologies([cti, osint])
```

## Template Metadata

Each template includes:
- `version` - Template version
- `name` - Human-readable name
- `description` - Template purpose
- `depends_on` - List of required template dependencies
- `entity_types` - Entity type definitions
- `relationship_types` - Relationship type definitions

## Creating Custom Templates

### What You CAN Configure in YAML

You can customize these aspects of existing entity and relationship types:

**Entity Type Customization:**
- `decay_config` - Adjust half-life, importance floor, stability multiplier
- `attributes` - Add or modify custom attributes within existing types
- `permanent` - Mark types as permanent (exempt from decay)
- `description`, `icon` - Update display metadata

**Relationship Type Customization:**
- `description`, `forward_name`, `reverse_name` - Display properties
- `permanent` - Mark relationships as permanent

### What Requires CODE Changes

Creating entirely NEW entity types or relationship types requires Python code changes:

**Requires Code (`docker/patches/ontology_config.py`):**
- Define new `EntityTypeConfig` classes
- Add new entity types to the Pydantic model
- Implement validation logic for new types
- Register new types in the ontology loader

**Example:** To add a new entity type like `ThreatActor`, you would need to:
1. Modify `docker/patches/ontology_config.py` to define the type
2. Add validation logic
3. Rebuild the Docker container

### Template Usage Guidelines

1. Start with an existing template as a base
2. Customize attributes, decay settings, and display properties
3. Set `depends_on` if extending another template
4. Validate with the `validate_ontology_config` MCP tool
5. **For new entity types:** Submit a feature request or modify the Python code directly

See `config/ontology-types.yaml.example` for full schema reference.
