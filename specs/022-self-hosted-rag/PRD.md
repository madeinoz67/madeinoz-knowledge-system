# Product Requirements Document (PRD)

## Product Name

**Local Knowledge Augmentation Platform (LKAP)**
(Working name – internal system)

---

## 1. Problem Statement

Modern technical work (embedded development, software engineering, cyber security operations) depends on external documentation and data that is:

* Fragmented (PDFs, SDK docs, standards, detections, reports)
* Frequently updated
* Often contradictory across versions
* Poorly indexed by general LLMs
* Hard to reuse across projects
* Easy to misclassify or forget

Conventional RAG systems:

* Re-read documents repeatedly
* Lose context over time
* Provide no durable memory
* Do not manage versioning or conflicts
* Require users to manage taxonomy manually

Knowledge Graphs solve durability but are not designed for raw document ingestion.

This system must combine both — without burdening users.

---

## 2. Product Vision

Build a local-first, self-hosted knowledge platform that:

1. Automatically ingests and classifies technical documents and data
2. Provides citation-backed retrieval (RAG) for daily work
3. Allows selective, evidence-bound promotion of facts into a durable Knowledge Graph
4. Integrates seamlessly with Claude via MCP
5. Minimizes user friction through smart defaults and a single review surface

The system behaves like a technical memory with a conscience:

* fast when confident
* careful when uncertain
* explicit about provenance

---

## 3. Goals and Non-Goals

### Goals

* Automatic, explainable document classification
* High-quality PDF ingestion (tables, sections, errata)
* Evidence-bound retrieval and promotion
* Version-aware and conflict-aware knowledge
* Domain-agnostic (embedded, software, security)
* Claude-first developer experience
* Fully local and self-hosted

### Non-Goals

* Autonomous knowledge curation without oversight
* Replacing human judgment on conflicts
* Visual diagram semantic understanding (Phase 1)
* Building a general-purpose search engine

---

## 4. Target Users

### Primary

* Embedded developers
* Software engineers (Python-heavy)
* Cyber security engineers and SOC analysts
* Systems engineers

### Secondary

* AI agents via Claude-code
* Internal automation workflows
* Future collaborators

---

## 5. Core Architecture

### Components

Layer: Ingestion
Component: Docling
Responsibility: Convert PDFs into structured Markdown or JSON

Layer: RAG
Component: RAGFlow
Responsibility: Index and retrieve document chunks

Layer: Embeddings
Component: Ollama
Responsibility: Local embeddings and optional local LLM

Layer: Interface
Component: MCP Server (Bun)
Responsibility: Tool interface for Claude

Layer: Knowledge
Component: Graph Knowledge System
Responsibility: Durable entities, facts, and relationships

Layer: UX
Component: Ingestion Review UI
Responsibility: Single-screen confirmation when needed

---

## 6. Knowledge Model

### Two-Tier Memory

#### Document Memory (RAG)

* High volume
* Versioned
* Noisy
* Citation-centric
* Short-lived relevance

#### Knowledge Memory (KG)

* Low volume
* High signal
* Typed
* Version- and conflict-aware
* Long-lived

Promotion from RAG to KG is explicit, auditable, and reversible.

---

## 7. Ingestion Lifecycle

### 7.1 Folder Roles

Inbox (transient)
Path: knowledge/inbox

* Watch folder
* Files processed once
* Never queried directly
* Emptied after successful ingestion

Processed (canonical)
Path: knowledge/processed/<doc_id>/<version>

* Immutable
* Source of truth
* Referenced by KG and RAG

Archive (optional)

* Long-term raw storage

---

### 7.2 Triggering Model

Primary: Event-driven (filesystem watcher)
Secondary: Scheduled reconciliation (e.g. nightly)

Ingestion must be:

* Idempotent (hash-based)
* Atomic
* Stable-file aware
* Auditable

---

## 8. Metadata and Taxonomy Strategy

### 8.1 Domain-First, Project-Overlay

Domain defines what the document is.
Project defines where it is used.

Domains are structural.
Projects are metadata tags.

Example domains:

* embedded
* software
* security
* cloud
* standards

---

### 8.2 Directory Structure as Metadata Hint

Directory paths:

* Provide default metadata
* Do not define identity
* Are overridden by explicit metadata or content

Identity is always:
hash plus canonical document ID plus version.

---

## 9. Automatic Metadata Determination

### 9.1 Progressive Classification Layers

1. Hard signals: path, filename, hash, vendor markers
2. Content analysis: title, table of contents, headings, keywords
3. LLM-assisted classification: guarded and explainable
4. User confirmation: only if confidence is low

Each inferred field includes:

* value
* confidence
* signal sources

---

### 9.2 Confidence Policy

Confidence ≥ 0.85
Behavior: Auto-accept

Confidence 0.70–0.84
Behavior: Accept with optional review

Confidence < 0.70
Behavior: User confirmation required

---

## 10. One-Screen Ingestion Review UI

### Purpose

Provide a single calm confirmation screen when classification is uncertain, without turning ingestion into a form.

### Characteristics

* Summary-first
* Confidence-explicit
* Evidence-visible
* At most one decision
* Learns from corrections

### UI Sections

1. Document summary (name, hash)
2. Classification summary and confidence band
3. Evidence preview explaining the classification
4. Optional context (projects, sensitivity)
5. Review section shown only if needed
6. Actions: Accept and Ingest, Override, Cancel

User corrections can be remembered per source.

---

## 11. Functional Requirements

### 11.1 Ingestion

* The system shall auto-classify domain, document type, vendor, and component
* The system shall prompt the user only when confidence is below threshold
* The system shall freeze metadata after ingestion
* The system shall move files out of the inbox after successful ingestion

---

### 11.2 Retrieval (RAG)

* The system shall support semantic search
* The system shall return chunks with text, source, page or section, and confidence
* The system shall support filters by domain, document type, component, project, and version

---

### 11.3 Promote-to-KG

* The system shall promote only evidence-backed facts
* The system shall support promotion from explicit evidence or search queries
* The system shall support typed facts such as:

  * Constraint
  * Erratum
  * Workaround
  * API
  * BuildFlag
  * ProtocolRule
  * Detection
  * Indicator

---

### 11.4 Conflict Handling

* The system shall detect conflicting facts
* The system shall store conflicts explicitly
* The system shall support resolution strategies:

  * Detect only
  * Keep both with scope
  * Prefer newest
  * Reject incoming

---

### 11.5 Provenance

* The system shall link every fact to evidence chunks and original documents
* The system shall return provenance subgraphs on request

---

## 12. Security-Specific Requirements

* Time-scoped metadata such as observed_at, published_at, and valid_until or TTL
* Sensitivity tagging
* Optional retention policies for indicators of compromise
* Separation of documents from operational data

---

## 13. MCP Interface

All capabilities are exposed via MCP tools:

* rag.search – Retrieve evidence
* rag.getChunk – Fetch an exact chunk
* kg.promoteFromEvidence – Promote knowledge
* kg.promoteFromQuery – Search and promote
* kg.reviewConflicts – Review conflicts
* kg.getProvenance – Trace facts

Schemas are considered normative.

---

## 14. User Workflows

Embedded, software, and security workflows:

1. User drops documents into inbox
2. System automatically classifies them
3. Review UI appears only if uncertain
4. Documents are indexed and searchable
5. High-value facts are promoted over time
6. Knowledge Graph becomes the primary source of truth

---

## 15. Non-Functional Requirements

### Performance

* Local retrieval under 500 ms in typical cases
* Ingestion completes in minutes, not hours

### Reliability

* No silent reclassification
* No promotion without evidence

### Maintainability

* Replaceable RAG and embedding components
* Clear separation of concerns

### Security

* Fully local by default
* No mandatory external APIs

---

## 16. MVP Scope

### In Scope

* Docling ingestion
* RAGFlow retrieval
* MCP wrapper
* Ingestion Review UI
* Promote types: Constraint, Erratum, API

### Out of Scope

* Diagram semantic understanding
* Autonomous conflict resolution
* Multi-user workflows

---

## 17. Success Metrics

* Reduced repeated document lookups
* Faster embedded bring-up and debugging
* Fewer rediscovered issues
* Claude answers increasingly backed by the Knowledge Graph
* Minimal user interruptions during ingestion

---

## 18. Summary

This system treats documents as evidence, knowledge as curated truth, and users as validators rather than data entry clerks.

By combining automatic ingestion, explainable classification, friction-free review, and durable knowledge promotion, LKAP becomes a long-lived technical memory rather than another document chat tool.
