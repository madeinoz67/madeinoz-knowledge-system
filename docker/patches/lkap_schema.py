"""
Knowledge Graph Database Schema for LKAP Facts (Feature 022)
Local Knowledge Augmentation Platform

This document describes how LKAP Facts are stored in the Knowledge Graph (Neo4j/FalkorDB).

FACT NODES
==========

Facts are stored as Neo4j nodes with typed labels:

(:Fact:Constraint)   - Limitation or restriction
(:Fact:Erratum)      - Documented error or bug
(:Fact:Workaround)   - Mitigation for a problem
(:Fact:API)          - Function or interface
(:Fact:BuildFlag)    - Compiler or build flag
(:Fact:ProtocolRule) - Communication protocol rule
(:Fact:Detection)    - Security detection rule
(:Fact:Indicator)    - Threat intelligence indicator

FACT PROPERTIES
================

Each Fact node has:
- fact_id: string (UUID) - Unique identifier
- type: string - Fact type (Constraint, Erratum, etc.)
- entity: string - Entity name (e.g., "STM32H7.GPIO.max_speed")
- value: string - Fact value (e.g., "120MHz")
- scope: string (optional) - Scope constraint
- version: string (optional) - Applicable version
- valid_until: datetime (optional) - Expiration timestamp
- evidence_ids: list[string] - Source evidence references
- created_at: datetime - Creation timestamp
- deprecated_at: datetime (optional) - Deprecation timestamp
- deprecated_by: string (optional) - Who deprecated

RELATIONSHIPS
============

(:Evidence)-[:PROVES]->(:Fact)
  Links evidence chunks to facts they support

(:Fact)-[:CONFLICTS_WITH]->(:Fact)
  Links conflicting facts (bidirectional)

(:Document)-[:CONTAINS]->(:Evidence)
  Links documents to evidence within them

(:Fact)-[:HAS_PROVENANCE]->(:Evidence)
  Links facts to their evidence chain

INDEXES
=======

CREATE INDEX ON :Fact(fact_id);
CREATE INDEX ON :Fact(entity);
CREATE INDEX ON :Fact(type);
CREATE INDEX ON :Fact(conflict_id);
CREATE INDEX ON :Evidence(evidence_id);
CREATE INDEX ON :Evidence(chunk_id);
CREATE INDEX ON :Conflict(conflict_id);

CONFLICT DETECTION CYPHER
==========================

// Find conflicting facts (same entity + type, different values)
MATCH (f1:Fact), (f2:Fact)
WHERE f1.entity = f2.entity
  AND f1.type = f2.type
  AND f1.value <> f2.value
  AND (f1.valid_until IS NULL OR f1.valid_until > datetime())
  AND (f2.valid_until IS NULL OR f2.valid_until > datetime())
  AND f1 <> f2
OPTIONAL MATCH (f1)-[:PROVES]->(e1:Evidence)
OPTIONAL MATCH (f2)-[:PROVES]->(e2:Evidence)
RETURN f1, f2, e1, e2

MIGRATION NOTES
===============

When the MCP server starts, it should:
1. Verify constraints exist
2. Create indexes if missing
3. Validate Fact type enum values match ontology
"""
