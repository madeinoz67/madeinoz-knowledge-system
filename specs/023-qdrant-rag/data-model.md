# Data Model: Qdrant RAG Migration

**Feature**: 023-qdrant-rag
**Date**: 2026-02-13

## Entity Overview

This feature introduces 4 core entities stored in Qdrant as vector points with payloads.

```
┌─────────────┐     contains     ┌─────────────┐
│  Document   │─────────────────▶│    Chunk    │
│             │     1:N          │             │
└─────────────┘                  └──────┬──────┘
                                        │
                                        │ has
                                        ▼
                                 ┌─────────────┐
                                 │  Embedding  │
                                 │ (1024-dim)  │
                                 └─────────────┘

┌─────────────┐     returns     ┌─────────────┐
│ SearchResult│◀────────────────│    Query    │
│             │     N:1         │             │
└─────────────┘                 └─────────────┘
```

---

## Entity: Document

Represents a source file (PDF, markdown, text) in the knowledge base.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| doc_id | UUID | Yes | Unique document identifier |
| filename | string | Yes | Original filename |
| file_type | enum | Yes | pdf, markdown, text |
| file_hash | string | Yes | SHA-256 hash for deduplication |
| domain | string | No | Knowledge domain (embedded, security, etc.) |
| project | string | No | Project identifier |
| component | string | No | Component/hardware identifier |
| ingested_at | datetime | Yes | Ingestion timestamp |
| chunk_count | integer | Yes | Number of chunks generated |
| status | enum | Yes | pending, processing, completed, failed |
| error_message | string | No | Error details if failed |

**State Transitions**:
```
pending → processing → completed
                   ↘ failed
```

**Validation Rules**:
- filename must not be empty
- file_hash must be 64 characters (SHA-256 hex)
- chunk_count must be >= 1 for completed status

---

## Entity: Chunk

Represents a text segment from a document with associated metadata.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| chunk_id | UUID | Yes | Unique chunk identifier |
| doc_id | UUID | Yes | Parent document reference |
| text | string | Yes | Chunk text content |
| token_count | integer | Yes | Number of tokens |
| page_number | integer | No | Page number in source |
| section_headings | string[] | No | Hierarchical headings |
| char_start | integer | Yes | Start character position |
| char_end | integer | Yes | End character position |
| position | integer | Yes | Chunk order in document |
| metadata | object | No | Additional metadata |

**Validation Rules**:
- text must not be empty
- token_count must be between 512-768
- char_start < char_end
- position must be >= 0

**Qdrant Payload Structure**:
```json
{
  "chunk_id": "uuid",
  "doc_id": "uuid",
  "text": "chunk content...",
  "token_count": 550,
  "page_number": 15,
  "section_headings": ["Chapter 3", "GPIO Configuration"],
  "char_start": 12000,
  "char_end": 12500,
  "position": 42,
  "metadata": {
    "domain": "embedded",
    "project": "stm32h7",
    "component": "GPIO"
  }
}
```

---

## Entity: Embedding

Vector representation of chunk text for semantic search.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| vector | float[1024] | Yes | 1024-dimensional embedding vector |
| model | string | Yes | Embedding model name |
| created_at | datetime | Yes | Embedding generation time |

**Validation Rules**:
- vector length must be exactly 1024
- all values must be finite (no NaN/Inf)
- model must be "bge-large-en-v1.5"

**Storage**: Embedding vector stored as Qdrant point vector, not in payload.

---

## Entity: SearchResult

Represents a search result with chunk and relevance score.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| chunk_id | UUID | Yes | Chunk identifier |
| text | string | Yes | Chunk text content |
| source_document | string | Yes | Source filename |
| page_section | string | No | Page/section reference |
| confidence | float | Yes | Relevance score (0.0-1.0) |
| metadata | object | No | Chunk metadata |

**Validation Rules**:
- confidence must be between 0.0 and 1.0
- Only return results with confidence >= 0.70

**JSON Response Format**:
```json
{
  "chunk_id": "uuid",
  "text": "chunk content...",
  "source_document": "stm32h7-reference.pdf",
  "page_section": "Section 3.2 - GPIO Configuration",
  "confidence": 0.92,
  "metadata": {
    "page_number": 15,
    "headings": ["GPIO Configuration"],
    "domain": "embedded"
  }
}
```

---

## Entity: IngestionResult

Result of document ingestion operation.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| doc_id | UUID | Yes | Document identifier |
| filename | string | Yes | Ingested filename |
| status | enum | Yes | success, skipped, failed |
| chunk_count | integer | Yes | Chunks created (0 if failed) |
| error_message | string | No | Error details if failed |
| duration_ms | integer | Yes | Processing time |

---

## Qdrant Collection Schema

```yaml
collection: lkap_documents
vectors:
  size: 1024
  distance: Cosine
payload_schema:
  chunk_id: keyword
  doc_id: keyword
  text: text
  token_count: integer
  page_number: integer
  section_headings: array[keyword]
  char_start: integer
  char_end: integer
  position: integer
  metadata.domain: keyword
  metadata.project: keyword
  metadata.component: keyword
  metadata.type: keyword
```

**Indexes**:
- `chunk_id` (unique lookup)
- `doc_id` (document chunk listing)
- `metadata.domain` (filtering)
- `metadata.project` (filtering)
- `metadata.component` (filtering)
