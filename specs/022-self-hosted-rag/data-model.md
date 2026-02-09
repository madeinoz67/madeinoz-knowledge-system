# Data Model: Local Knowledge Augmentation Platform (LKAP)

**Feature**: 022-self-hosted-rag
**Date**: 2026-02-09
**Phase**: 1 - Design & Contracts

## Overview

This document defines the core entities, attributes, and relationships for the LKAP system. The data model spans two tiers: Document Memory (RAG) for transient evidence and Knowledge Memory (Graph) for durable facts.

## Entity Definitions

### Document

**Description**: Source file with metadata, tracked through ingestion lifecycle

**Attributes**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| doc_id | string | Yes | Unique document identifier (UUID) |
| hash | string | Yes | SHA-256 hash of source file (idempotency check) |
| filename | string | Yes | Original filename |
| path | string | Yes | Canonical storage path (processed/<doc_id>/<version>/) |
| domain | enum | Yes | embedded, software, security, cloud, standards |
| type | enum | No | PDF, markdown, text, HTML |
| vendor | string | No | Vendor name (e.g., "ST", "NXP", "ARM") |
| component | string | No | Component name (e.g., "STM32H7", "ESP32") |
| version | string | No | Document version (e.g., "v1.0", "Rev C") |
| projects | list[string] | No | Associated project tags (metadata) |
| sensitivity | enum | No | public, internal, confidential, restricted |
| upload_date | datetime | Yes | Timestamp of initial upload |
| content_hash | string | Yes | Hash of content (for change detection) |

**Relationships**:
- `Document 1:N DocumentChunk` (one document has many chunks)
- `Document 1:N Evidence` (chunks used as evidence for facts)
- `Document 1:1 IngestionState` (processing status tracking)

**Indexes**:
- `idx_document_hash` (hash) - for idempotency check
- `idx_document_domain` (domain) - for filtering
- `idx_document_upload_date` (upload_date) - for time-based queries

---

### DocumentChunk

**Description**: Segment of document content with embedding vector

**Attributes**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| chunk_id | string | Yes | Unique chunk identifier (UUID) |
| doc_id | string (FK) | Yes | Parent document reference |
| text | string | Yes | Chunk text content |
| page_section | string | No | Page number or section identifier |
| position | int | Yes | Position in document (sequence) |
| token_count | int | Yes | Token count (512-768 range) |
| embedding_vector | vector[1024+] | Yes | Embedding vector (1024+ dimensions) |
| created_at | datetime | Yes | Timestamp of chunk creation |

**Relationships**:
- `DocumentChunk N:1 Document` (belongs to one document)
- `DocumentChunk 1:N Evidence` (one chunk can evidence multiple facts)

**Validation Rules**:
- `token_count BETWEEN 256 AND 1024` (enforce chunk size limits)
- `embedding_vector` dimension must match configured model (1024+)

---

### Evidence

**Description**: Reference from document chunk to promoted fact (provenance link)

**Attributes**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| evidence_id | string | Yes | Unique evidence identifier (UUID) |
| chunk_id | string (FK) | Yes | Source chunk reference |
| fact_ids | list[string] (FK) | Yes | Facts this evidence supports |
| confidence | float | Yes | Confidence score (0.0-1.0) |
| created_at | datetime | Yes | Timestamp of evidence creation |

**Relationships**:
- `Evidence N:1 DocumentChunk` (references one chunk)
- `Evidence N:M Fact` (can support multiple facts)

**Validation Rules**:
- `confidence BETWEEN 0.0 AND 1.0`

---

### Fact

**Description**: Typed knowledge in Knowledge Graph with conflict awareness

**Attributes**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| fact_id | string | Yes | Unique fact identifier (UUID) |
| type | enum | Yes | Constraint, Erratum, Workaround, API, BuildFlag, ProtocolRule, Detection, Indicator |
| entity | string | Yes | Entity name (e.g., "STM32H7.GPIO.max_speed") |
| value | string | Yes | Fact value (e.g., "120MHz") |
| scope | string | No | Scope constraint (e.g., "v1.0 only", "GPIO Port A") |
| version | string | No | Applicable version (if version-specific) |
| valid_until | datetime | No | Expiration timestamp (for time-sensitive facts) |
| conflict_id | string (FK) | No | Reference to conflict record (if conflicted) |
| evidence_ids | list[string] (FK) | Yes | Source evidence references |
| created_at | datetime | Yes | Timestamp of fact creation |
| deprecated_at | datetime | No | Timestamp if fact was deprecated |
| deprecated_by | string | No | User or system who deprecated |

**Relationships**:
- `Fact N:M Evidence` (many-to-many via evidence_ids)
- `Fact N:1 Conflict` (optional, if conflicted)
- `Fact 1:N ProvenanceNode` (for provenance subgraph)

**Validation Rules**:
- At least one evidence_id required (no orphaned facts)
- `valid_until` must be in future if set
- `value` must be non-empty

**Fact Type Enum Values**:

| Type | Description | Example |
|------|-------------|---------|
| Constraint | Limitation or restriction | "max clock frequency: 120MHz" |
| Erratum | Documented error or bug | "REV A silicon bug: I2C hang" |
| Workaround | Mitigation for a problem | "Use I2C2 instead of I2C1" |
| API | Function or interface | "HAL_GPIO_Init()" |
| BuildFlag | Compiler or build flag | "-DUSE_HAL_DRIVER" |
| ProtocolRule | Communication protocol rule | "I2C max freq: 400kHz" |
| Detection | Security detection rule | "C2 beacon pattern detected" |
| Indicator | Threat indicator | "IP: 192.168.1.100 associated with APT28" |

---

### Conflict

**Description**: Detected contradiction between facts

**Attributes**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| conflict_id | string | Yes | Unique conflict identifier (UUID) |
| fact_ids | list[string] (FK) | Yes | Conflicting fact references (2+) |
| detection_date | datetime | Yes | Timestamp of conflict detection |
| resolution_strategy | enum | Yes | detect_only, keep_both, prefer_newest, reject_incoming |
| status | enum | Yes | open, resolved, deferred |
| resolved_at | datetime | No | Timestamp of resolution |
| resolved_by | string | No | User who resolved conflict |

**Relationships**:
- `Conflict 1:N Fact` (one conflict involves multiple facts)

**Validation Rules**:
- At least 2 fact_ids required
- `status` transitions: open → resolved OR open → deferred

**Resolution Strategies**:

| Strategy | Description | When to Use |
|----------|-------------|-------------|
| detect_only | Flag conflicts, no auto-resolution | Initial detection, manual review |
| keep_both | Retain all facts with scope metadata | Different versions, different contexts |
| prefer_newest | Accept fact with latest created_at | Temporal precedence |
| reject_incoming | Preserve existing fact | Existing fact is more authoritative |

---

### IngestionState

**Description**: Processing status tracking for document ingestion

**Attributes**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| doc_id | string (FK) | Yes | Document reference |
| status | enum | Yes | pending, processing, completed, failed, review_required |
| confidence_band | enum | No | high (≥0.85), medium (0.70-0.84), low (<0.70) |
| chunks_processed | int | Yes | Number of chunks created |
| chunks_total | int | No | Expected total chunks (if known) |
| error_message | string | No | Error details if status is failed |
| last_update | datetime | Yes | Timestamp of last status change |

**Relationships**:
- `IngestionState 1:1 Document` (one state per document)

**Validation Rules**:
- `chunks_processed` must be ≥ 0
- `confidence_band` required when status is completed or review_required

**Status Transitions**:

```
pending → processing → completed
                    → review_required → completed
                    → failed
processing → failed
```

---

### Classification

**Description**: Metadata inference result with confidence tracking

**Attributes**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| classification_id | string | Yes | Unique classification identifier (UUID) |
| doc_id | string (FK) | Yes | Document reference |
| field_name | string | Yes | Field being classified (domain, type, vendor, component) |
| value | string | Yes | Classified value |
| confidence | float | Yes | Confidence score (0.0-1.0) |
| signal_sources | list[string] | Yes | Sources that contributed to classification |
| user_override | boolean | Yes | Whether user overrode automatic classification |
| created_at | datetime | Yes | Timestamp of classification |

**Relationships**:
- `Classification N:1 Document` (one doc has many classifications)

**Validation Rules**:
- `confidence BETWEEN 0.0 AND 1.0`
- At least one signal_source required

**Signal Sources Examples**:

| Source | Example |
|--------|---------|
| path | "docs/embedded/stm32/" |
| filename | "STM32H743_Datasheet.pdf" |
| vendor_marker | "STMicroelectronics" in title |
| content_analysis | "Table of Contents: GPIO, SPI, I2C" |
| llm_classification | "LLM: domain=embedded, confidence=0.82" |
| user_override | "User changed domain from software to embedded" |

---

## Relationships Summary

```
Document (1) ──┬── (N) DocumentChunk
               │
               ├── (N) Evidence ──┬── (M) Fact
               │                  │
               └── (1) IngestionState
                                  │
                                  └── (N) Conflict
```

## Storage Mapping

### RAGFlow (Vector DB)

- **DocumentChunk** stored as RAGFlow "documents"
- **embedding_vector** stored in RAGFlow vector index
- **metadata** stored as RAGFlow document metadata

### Neo4j/FalkorDB (Knowledge Graph)

- **Fact** stored as Neo4j nodes with labels `:Fact:Constraint`, `:Fact:Erratum`, etc.
- **Evidence** stored as `:Evidence` nodes
- **Document** stored as `:Document` nodes
- **Relationships**:
  - `(:Evidence)-[:PROVES]->(:Fact)`
  - `(:Fact)-[:CONFLICTS_WITH]->(:Fact)`
  - `(:Document)-[:CONTAINS]->(:Evidence)`

### Filesystem (Document Storage)

```
knowledge/
├── inbox/                    # Watch folder (transient)
│   └── *.pdf, *.md, *.txt   # Pending documents
└── processed/                # Canonical storage
    └── <doc_id>/
        └── <version>/
            └── original.pdf   # Original file
            └── structured.md # Docling output (if applicable)
```

## State Transitions

### Document Ingestion State

```
[pending] → [processing] → [completed]
                           → [review_required] → [completed]
                           → [failed]
```

### Fact Lifecycle

```
[created] → [active] → [deprecated] → [archived]
              ↓
         [conflicted] → [resolved]
```

### Conflict Resolution

```
[detected] → [open] → [resolved]
                      ↓
                   [deferred]
```

## Indexes and Performance

### Primary Indexes

- `Document.doc_id` (primary key)
- `DocumentChunk.chunk_id` (primary key)
- `Fact.fact_id` (primary key)
- `Evidence.evidence_id` (primary key)

### Secondary Indexes

- `Document.hash` (idempotency)
- `Document.domain` (filtering)
- `Document.upload_date` (temporal queries)
- `Fact.entity` (entity lookup)
- `Fact.type` (fact type filtering)
- `Fact.conflict_id` (conflict lookup)
- `IngestionState.status` (processing queue)

### Vector Index

- RAGFlow vector index on `DocumentChunk.embedding_vector`
- Dimension: 1024+ (configurable)
- Metric: Cosine similarity
