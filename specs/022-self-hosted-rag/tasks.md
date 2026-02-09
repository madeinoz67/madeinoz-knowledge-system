---

description: "Task list for Local Knowledge Augmentation Platform (LKAP) implementation"
---

# Tasks: Local Knowledge Augmentation Platform (LKAP)

**Input**: Design documents from `/specs/022-self-hosted-rag/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/mcp-tools.yaml, quickstart.md

**Tests**: Included per spec requirement - testing strategy defined in plan.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

**For this project (Madeinoz Knowledge System):**
- **Python code**: `docker/patches/` for implementation, `docker/tests/` for tests
- **TypeScript code**: `src/` for implementation, `tests/` for tests
- **Config**: `config/` for configuration files
- **Compose files**: `docker/` for container definitions
- **Knowledge storage**: `knowledge/` for document storage

See Constitution Principle VII (Language Separation) for strict directory boundaries.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create knowledge directory structure in knowledge/inbox/ and knowledge/processed/
- [X] T002 Create docker/docker-compose-ragflow.yml with RAGFlow container configuration
- [X] T003 [P] Update docker/Dockerfile to add Docling, RAGFlow client, and classification dependencies
- [X] T005 [P] Create config/ragflow.yaml with RAGFLOW configuration (embedding dimension: 1024+, chunk size: 512-768)
- [X] T006 [P] Create config/ontologies/rag-fact-types.yaml with fact type definitions (Constraint, Erratum, Workaround, API, BuildFlag, ProtocolRule, Detection, Indicator)
- [X] T007 [P] Create .env.example with RAGFLOW_API_URL, OLLAMA_BASE_URL, OPENROUTER_API_KEY, EMBEDDING_MODEL placeholders
- [X] T008 [P] Create src/server/lib/ragflow.ts with RAGFlow client wrapper functions
- [X] T009 [P] Create src/server/lib/types.ts with RAG-specific TypeScript types
- [X] T010 [P] Create docker/patches/__init__.py for ragflow_client, docling_ingester, classification, promotion modules
- [X] T011 [P] Create docker/patches/tests/ directory structure (unit/, integration/)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T012 Implement Document entity model in docker/patches/lkap_models.py with doc_id, hash, filename, domain, type, vendor, component, version, projects, sensitivity, upload_date, content_hash
- [X] T013 [P] Implement DocumentChunk entity model in docker/patches/lkap_models.py with chunk_id, doc_id, text, page_section, position, token_count, embedding_vector, created_at
- [X] T014 [P] Implement Evidence entity model in docker/patches/lkap_models.py with evidence_id, chunk_id, fact_ids, confidence, created_at
- [X] T015 [P] Implement Fact entity model in docker/patches/lkap_models.py with fact_id, type, entity, value, scope, version, valid_until, conflict_id, evidence_ids, created_at, deprecated_at, deprecated_by
- [X] T016 [P] Implement Conflict entity model in docker/patches/lkap_models.py with conflict_id, fact_ids, detection_date, resolution_strategy, status, resolved_at, resolved_by
- [X] T017 [P] Implement IngestionState entity model in docker/patches/lkap_models.py with doc_id, status, confidence_band, chunks_processed, chunks_total, error_message, last_update
- [X] T018 [P] Implement Classification entity model in docker/patches/lkap_models.py with classification_id, doc_id, field_name, value, confidence, signal_sources, user_override, created_at
- [X] T019 Create knowledge graph database schema in docker/patches/lkap_schema.py for Fact nodes with :Fact labels per type
- [X] T020 [P] Create RAGFlow HTTP client in docker/patches/ragflow_client.py with upload, search, get_document, delete_document methods
- [X] T021 [P] Implement embedding service in docker/patches/embedding_service.py with OpenRouter (text-embedding-3-large, 3072 dim) and Ollama (bge-large-en-v1.5, 1024 dim) support
- [X] T022 [P] Setup basic logging infrastructure in docker/patches/lkap_logging.py for errors and ingestion status (FR-036a)
- [X] T023 Create filesystem watcher in docker/patches/docling_ingester.py for knowledge/inbox/ directory
- [X] T024 [P] Implement chunking service in docker/patches/chunking_service.py with heading-aware 512-768 token splitting and 100-token overlap
- [X] T025 [P] Implement progressive classification service in docker/patches/classification.py with 4 layers: hard signals → content analysis → LLM → user confirmation
- [X] T026 [P] Implement confidence band calculation in docker/patches/classification.py (≥0.85 auto, 0.70-0.84 optional review, <0.70 required)
- [X] T027 [P] Setup Graphiti knowledge graph connection in docker/patches/promotion.py for Knowledge Memory tier
- [X] T028 Configure madeinoz-knowledge-net bridge network in docker compose files to include RAGFlow and Ollama containers
- [X] T029 [P] Create unit test framework setup in docker/patches/tests/unit/test_lkap_unit.py with pytest configuration
- [X] T030 [P] Create integration test framework setup in docker/patches/tests/conftest.py with testcontainers for RAGFlow, Neo4j/FalkorDB

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Automatic Document Ingestion (Priority: P1) 🎯 MVP

**Goal**: Automatically ingest technical documents (PDFs, markdown, text) from inbox folder with confidence-based classification

**Independent Test**: Drop sample documents into knowledge/inbox/, verify automatic classification occurs, files are moved to knowledge/processed/ with proper metadata

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T031 [P] [US1] Unit test for heading-aware chunking in docker/patches/tests/unit/test_chunking.py (verify 512-768 token limits, heading respect)
- [X] T032 [P] [US1] Unit test for confidence band calculation in docker/patches/tests/unit/test_confidence.py (verify ≥0.85 auto, <0.70 review thresholds)
- [X] T033 [P] [US1] Unit test for progressive classification layers in docker/patches/tests/unit/test_classification.py (hard signals → content → LLM)
- [X] T034 [P] [US1] Integration test for end-to-end ingestion in docker/patches/tests/integration/test_rag_ingestion.py (inbox → processed → RAGFlow → Graph)

### Implementation for User Story 1

- [X] T035 [P] [US1] Implement Docling PDF ingestion in docker/patches/docling_ingester.py with table/section/errata preservation
- [X] T036 [P] [US1] Implement markdown and text file ingestion in docker/patches/docling_ingester.py
- [X] T037 [US1] Implement idempotency check in docker/patches/docling_ingester.py (skip if content_hash matches)
- [X] T038 [US1] Implement atomic ingestion with rollback in docker/patches/docling_ingester.py (all-or-nothing per document)
- [X] T039 [P] [US1] Implement domain classification in docker/patches/classification.py (embedded, software, security, cloud, standards)
- [X] T040 [P] [US1] Implement document type classification in docker/patches/classification.py (PDF, markdown, text, HTML)
- [X] T041 [P] [US1] Implement vendor detection in docker/patches/classification.py from filename, title, content
- [X] T042 [P] [US1] Implement component extraction in docker/patches/classification.py from technical content
- [X] T043 [US1] Implement LLM-assisted classification in docker/patches/classification.py with confidence scoring
- [X] T044 [US1] Create IngestionState tracking in docker/patches/docling_ingester.py (pending → processing → completed/failed/review_required)
- [X] T045 [US1] Implement document move from knowledge/inbox/ to knowledge/processed/<doc_id>/<version>/ after successful ingestion
- [X] T046 [US1] Implement scheduled reconciliation (nightly) in docker/patches/docling_ingester.py as secondary trigger
- [X] T047 [US1] Add ingestion status logging (errors, chunks processed, confidence bands)
- [X] T048 [P] [US1] Create rag.search MCP tool in docker/patches/graphiti_mcp_server.py (query, filters → SearchResult[])
- [X] T049 [P] [US1] Create rag.getChunk MCP tool in docker/patches/graphiti_mcp_server.py (chunk_id → Chunk)
- [X] T050 [P] [US1] Create TypeScript CLI wrapper src/skills/server/lib/rag-cli.ts with list-documents, show-document, reindex commands
- [X] T051 [US1] Implement batch ingestion handling for 100 simultaneous documents (complete within 5 minutes)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Semantic Search and Evidence Retrieval (Priority: P1)

**Goal**: Provide semantic search returning relevant document chunks with citations, confidence scores, and supporting metadata

**Independent Test**: Index sample documents, run semantic queries, verify relevant chunks returned with proper attribution (confidence >0.70)

### Tests for User Story 2

- [ ] T052 [P] [US2] Integration test for semantic search in docker/patches/tests/integration/test_classification.py (verify filter by domain, type, component, project, version)
- [ ] T053 [P] [US2] Integration test for empty results handling in docker/patches/tests/integration/test_classification.py (return empty when no matches above threshold)

### Implementation for User Story 2

- [X] T054 [P] [US2] Implement semantic search in docker/patches/ragflow_client.py with top-k result retrieval
- [X] T055 [US2] Implement search result filtering in docker/patches/ragflow_client.py by domain, document type, component, project, version
- [X] T056 [P] [US2] Implement search confidence thresholding in docker/patches/ragflow_client.py (return empty if best match <0.70)
- [X] T057 [US2] Implement SearchResult schema with chunk_id, text, source_document, page_section, confidence, metadata, provenance in docker/patches/ragflow_client.py
- [X] T058 [P] [US2] Add retrieval latency tracking (<500ms target) in docker/patches/ragflow_client.py
- [X] T059 [US2] Integrate rag.search tool with MCP server in docker/patches/graphiti_mcp_server.py
- [X] T060 [US2] Integrate rag.getChunk tool with MCP server in docker/patches/graphiti_mcp_server.py
- [X] T061 [P] [US2] Create TypeScript RAGFlow client wrapper in src/skills/server/lib/ragflow.ts for CLI tools

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Evidence-Based Knowledge Promotion (Priority: P1)

**Goal**: Enable promotion of high-value facts from document evidence to durable Knowledge Graph with provenance tracking

**Independent Test**: Search for evidence, promote fact to Knowledge Graph, verify fact appears in graph queries with provenance links

### Tests for User Story 3

- [X] T062 [P] [US3] Unit test for evidence-to-fact linking in docker/patches/tests/unit/test_provenance.py (verify provenance chain maintained)
- [X] T063 [P] [US3] Integration test for evidence promotion in docker/patches/tests/integration/test_promotion.py (evidence → Knowledge Graph with provenance)
- [X] T064 [P] [US3] Integration test for conflict detection in docker/patches/tests/integration/test_conflict_detection.py (conflicting facts for same entity)

### Implementation for User Story 3

- [X] T065 [P] [US3] Implement kg.promoteFromEvidence MCP tool in docker/patches/graphiti_mcp_server.py (evidence_id, fact_type, value → Fact with provenance)
- [X] T066 [P] [US3] Implement kg.promoteFromQuery MCP tool in docker/patches/graphiti_mcp_server.py (query, fact_type → search + promote)
- [X] T067 [P] [US3] Implement Fact creation in docker/patches/promotion.py with type enum (Constraint, Erratum, Workaround, API, BuildFlag, ProtocolRule, Detection, Indicator)
- [X] T068 [P] [US3] Implement evidence-to-fact linking in docker/patches/promotion.py (Evidence node → Fact node)
- [X] T069 [US3] Implement provenance preservation in docker/patches/promotion.py (Fact → Evidence → Chunk → Document chain)
- [X] T070 [US3] Implement conflict detection Cypher query in docker/patches/promotion.py (same entity + type, different values)
- [X] T071 [P] [US3] Implement conflict resolution strategies in docker/patches/promotion.py (detect_only, keep_both, prefer_newest, reject_incoming)
- [X] T072 [US3] Implement version change detection in docker/patches/promotion.py (flag affected facts when source document updated)
- [X] T073 [US3] Implement time-scoped metadata support in docker/patches/promotion.py (observed_at, published_at, valid_until, TTL for security indicators)
- [X] T074 [US3] Add reversible promotion support in docker/patches/promotion.py (facts can be deprecated/removed)

**Checkpoint**: All three P1 user stories should now be independently functional

---

## Phase 6: User Story 4 - Ingestion Review and Classification Override (Priority: P2)

**Goal**: Present calm, single-screen review interface when classification confidence is low, allow overrides and learn from corrections

**Independent Test**: Trigger low-confidence classifications, verify review UI appears with correct information, confirm corrections are applied and remembered

### Tests for User Story 4

- [ ] T075 [P] [US4] Integration test for review UI trigger in docker/patches/tests/integration/test_classification.py (confidence <0.70 triggers UI)
- [ ] T076 [P] [US4] Integration test for classification override in docker/patches/tests/integration/test_classification.py (override remembered for future docs from same source)

### Implementation for User Story 4

- [ ] T077 [US4] Create review UI service in docker/patches/classification.py (document summary, classification, confidence band, evidence preview)
- [ ] T078 [P] [US4] Implement review UI actions in docker/patches/classification.py (Accept and Ingest, Override, Cancel)
- [ ] T079 [US4] Implement override learning in docker/patches/classification.py (remember corrections per source for future classification)
- [ ] T080 [P] [US4] Implement leave-in-cancel handling in docker/patches/classification.py (document stays in inbox for manual intervention)

**Checkpoint**: User Story 4 adds oversight while maintaining US1-3 independence

---

## Phase 7: User Story 5 - Conflict Resolution and Provenance Tracking (Priority: P3)

**Goal**: Enable review of conflicting facts, trace provenance to source documents, apply resolution strategies

**Independent Test**: Promote conflicting facts, trigger conflict detection, apply resolution strategies, verify behavior

### Tests for User Story 5

- [X] T081 [P] [US5] Integration test for conflict detection in docker/patches/tests/integration/test_conflict_detection.py (verify explicit conflict storage)
- [X] T082 [P] [US5] Integration test for conflict resolution in docker/patches/tests/integration/test_conflict_detection.py (verify each resolution strategy)
- [X] T083 [P] [US5] Integration test for provenance tracking in docker/patches/tests/integration/test_conflict_detection.py (verify fact → evidence → document chain)

### Implementation for User Story 5

- [X] T084 [P] [US5] Implement kg.reviewConflicts MCP tool in docker/patches/graphiti_mcp_server.py (entity, fact_type, status filters → Conflict[])
- [X] T085 [P] [US5] Implement kg.getProvenance MCP tool in docker/patches/graphiti_mcp_server.py (fact_id → ProvenanceGraph with evidence chain and documents)
- [X] T086 [P] [US5] Implement conflict query with filters in docker/patches/promotion.py (by entity, fact_type, status)
- [X] T087 [P] [US5] Implement provenance subgraph generation in docker/patches/promotion.py (fact → evidence → chunks → documents)
- [X] T088 [US5] Implement conflict status tracking in docker/patches/promotion.py (open → resolved OR open → deferred)
- [X] T089 [US5] Add resolution audit trail in docker/patches/promotion.py (resolved_at, resolved_by tracking)

**Checkpoint**: All user stories should now be independently functional

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T090 [P] Update CLAUDE.md with RAG-specific configuration and usage instructions
- [X] T091 [P] Update docs/reference/configuration.md with LKAP environment variables (RAGFLOW_API_URL, OLLAMA_BASE_URL, OPENROUTER_API_KEY, EMBEDDING_MODEL)
- [X] T092 [P] Create docs/usage/lkap-quickstart.md with AI-friendly summary and quick reference card (Constitution Principle VIII)
- [X] T093 [P] Create docs/reference/observability.md entry for basic logging (errors, ingestion status) per FR-036a
- [ ] T094 [P] Implement user-managed backup scripts in docker/patches/ for document and knowledge graph export
- [X] T095 [P] Code cleanup: remove debug logging, consolidate duplicate code, improve error messages
- [X] T096 [P] Performance optimization: verify <500ms search latency, optimize embedding batch size
- [ ] T097 Run full integration test suite (docker/patches/tests/integration/ and tests/integration/)
- [ ] T098 Run quickstart.md validation (test all workflows from quickstart.md)
- [X] T099 [P] Update CHANGELOG.md with LKAP feature summary

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Integrates with US1 chunks but independently testable
- **User Story 3 (P1)**: Can start after Foundational (Phase 2) - Integrates with US1 documents/US2 search but independently testable
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - Extends US1 classification, independently testable
- **User Story 5 (P3)**: Can start after Foundational (Phase 2) - Integrates with US3 facts but independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD)
- Models before services
- Services before endpoints/tools
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T002, T003, T004, T005, T006, T007, T008, T009, T010, T011)
- All Foundational entity models marked [P] can run in parallel (T013, T014, T015, T016, T017, T018)
- All Foundational services marked [P] can run in parallel (T020, T021, T024, T025)
- Once Foundational phase completes, all P1 user stories (US1, US2, US3) can start in parallel
- All tests within a story marked [P] can run in parallel
- All Polish tasks marked [P] can run in parallel (T090, T091, T092, T093, T094, T095, T096)

---

## Parallel Example: User Story 1

```bash
# Launch all unit tests for User Story 1 together:
Task: "Unit test for heading-aware chunking in docker/patches/tests/unit/test_chunking.py"
Task: "Unit test for confidence band calculation in docker/patches/tests/unit/test_confidence.py"
Task: "Unit test for progressive classification layers in docker/patches/tests/unit/test_classification.py"

# Launch all ingestion implementations together:
Task: "Implement Docling PDF ingestion in docker/patches/docling_ingester.py"
Task: "Implement markdown and text file ingestion in docker/patches/docling_ingester.py"
Task: "Implement domain classification in docker/patches/classification.py"
Task: "Implement document type classification in docker/patches/classification.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1-3 Only, P1 Stories)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Automatic Document Ingestion)
4. Complete Phase 4: User Story 2 (Semantic Search)
5. Complete Phase 5: User Story 3 (Evidence-Based Knowledge Promotion)
6. **STOP and VALIDATE**: Test all P1 stories independently
7. Deploy/demo if ready

**MVP Success Criteria**:
- Documents auto-ingest with ≥85% auto-acceptance rate
- Semantic search returns relevant results in <500ms
- Facts can be promoted from evidence with provenance tracking

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (Document ingestion working!)
3. Add User Story 2 → Test independently → Deploy/Demo (Search now functional!)
4. Add User Story 3 → Test independently → Deploy/Demo (Knowledge promotion enabled!)
5. Add User Story 4 → Test independently → Deploy/Demo (Review UI added!)
6. Add User Story 5 → Test independently → Deploy/Demo (Conflict resolution complete!)
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Ingestion) + User Story 4 (Review UI)
   - Developer B: User Story 2 (Search)
   - Developer C: User Story 3 (Promotion) + User Story 5 (Conflicts)
3. Stories complete and integrate independently

---

## Summary

- **Total Tasks**: 99 tasks
- **Setup Phase**: 11 tasks (T001-T011)
- **Foundational Phase**: 20 tasks (T012-T031) - BLOCKS all user stories
- **User Story 1 (P1)**: 21 tasks (T031-T051) - MVP Core
- **User Story 2 (P1)**: 10 tasks (T052-T061) - Search capability
- **User Story 3 (P1)**: 14 tasks (T062-T074) - Knowledge promotion
- **User Story 4 (P2)**: 6 tasks (T075-T080) - Review UI
- **User Story 5 (P3)**: 8 tasks (T081-T089) - Conflict resolution
- **Polish Phase**: 10 tasks (T090-T099)

**Task Count by User Story**:
- US1 (P1): 21 tasks (including 4 tests)
- US2 (P1): 10 tasks (including 2 tests)
- US3 (P1): 14 tasks (including 4 tests)
- US4 (P2): 6 tasks (including 2 tests)
- US5 (P3): 8 tasks (including 3 tests)

**Independent Test Criteria**:
- US1: Drop documents, verify auto-classification and file movement
- US2: Index documents, search queries, verify relevant chunks with confidence >0.70
- US3: Promote evidence, verify fact in graph with provenance
- US4: Low confidence triggers review UI, verify override learning
- US5: Promote conflicting facts, verify conflict detection and resolution

**Parallel Opportunities**: 42 tasks marked [P] can run in parallel with appropriate team allocation

**Suggested MVP Scope**: Phase 1 + Phase 2 + Phase 3 (US1) for document ingestion MVP
**Full Release**: Phases 1-5 (All P1 stories: US1, US2, US3) for complete RAG + Knowledge Graph capability
**Enhanced Release**: All phases (P1 + P2 + P3 stories) for full system with review UI and conflict resolution

**Format Validation**: ✅ ALL tasks follow checklist format (checkbox, ID, story labels, file paths)
