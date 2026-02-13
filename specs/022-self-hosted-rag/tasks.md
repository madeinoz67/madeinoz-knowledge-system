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

**NOTE**: Updated for RAGFlow-native architecture - document ingestion handled via RAGFlow UI

- [X] T001 Create knowledge directory structure (REMOVED: knowledge/inbox/ and knowledge/processed/ no longer needed - RAGFlow manages documents via MinIO)
- [X] T002 Create docker/docker-compose-ragflow.yml with RAGFlow container configuration
- [X] T003 [P] Update docker/Dockerfile to add RAGFlow client dependencies (Docling REMOVED - RAGFlow handles parsing)
- [X] T005 [P] Create config/ragflow.yaml with RAGFLOW configuration (embedding dimension: 1024+, chunk size: 512-768)
- [X] T006 [P] Create config/ontologies/rag-fact-types.yaml with fact type definitions (Constraint, Erratum, Workaround, API, BuildFlag, ProtocolRule, Detection, Indicator)
- [X] T007 [P] Create .env.example with RAGFLOW_API_URL, OLLAMA_BASE_URL, OPENROUTER_API_KEY, EMBEDDING_MODEL placeholders
- [X] T008 [P] Create src/server/lib/ragflow.ts with RAGFlow client wrapper functions (search-only, upload REMOVED)
- [X] T009 [P] Create src/server/lib/types.ts with RAG-specific TypeScript types
- [X] T010 [P] Create docker/patches/__init__.py for ragflow_client, promotion modules (docling_ingester, classification REMOVED)
- [X] T011 [P] Create docker/patches/tests/ directory structure (unit/, integration/)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

**NOTE**: Updated for RAGFlow-native architecture - many components now handled by RAGFlow

- [X] T012 Implement Document entity model in docker/patches/lkap_models.py (RAGFlow manages documents - model kept for type compatibility)
- [X] T013 [P] Implement DocumentChunk entity model in docker/patches/lkap_models.py with chunk_id, doc_id, text, page_section, position, token_count, embedding_vector, headings (T057 completed)
- [X] T014 [P] Implement Evidence entity model in docker/patches/lkap_models.py with evidence_id, chunk_id, fact_ids, confidence, created_at
- [X] T015 [P] Implement Fact entity model in docker/patches/lkap_models.py with fact_id, type, entity, value, scope, version, valid_until, conflict_id, evidence_ids, created_at, deprecated_at, deprecated_by
- [X] T016 [P] Implement Conflict entity model in docker/patches/lkap_models.py with conflict_id, fact_ids, facts (hydrated), detection_date, resolution_strategy, status, resolved_at, resolved_by, severity (T077 completed)
- [REMOVED] T017 [P] Implement IngestionState entity model (RAGFlow tracks ingestion status - no longer needed in LKAP)
- [REMOVED] T018 [P] Implement Classification entity model (RAGFlow handles document metadata - no longer needed in LKAP)
- [X] T019 Create knowledge graph database schema in docker/patches/lkap_schema.py for Fact nodes with :Fact labels per type
- [X] T020 [P] Create RAGFlow HTTP client in docker/patches/ragflow_client.py with search, get_chunk methods (upload REMOVED - use RAGFlow UI)
- [X] T021 [P] Implement embedding service in docker/patches/embedding_service.py with OpenRouter and Ollama support (P2 fixes applied)
- [X] T022 [P] Setup basic logging infrastructure in docker/patches/lkap_logging.py for errors and ingestion status (FR-036a)
- [REMOVED] T023 Filesystem watcher for knowledge/inbox/ (OUT OF SCOPE - RAGFlow UI provides document upload)
- [REMOVED] T024 [P] Implement chunking service (RAGFlow handles chunking with 14 built-in templates - no longer needed)
- [REMOVED] T025 [P] Progressive classification service (RAGFlow handles document metadata - no longer needed)
- [REMOVED] T026 [P] Confidence band calculation (RAGFlow handles classification - no longer needed)
- [X] T027 [P] Setup Graphiti knowledge graph connection in docker/patches/promotion.py for Knowledge Memory tier
- [X] T028 Configure madeinoz-knowledge-net bridge network in docker compose files to include RAGFlow and Ollama containers
- [X] T029 [P] Create unit test framework setup in docker/patches/tests/unit/test_lkap_unit.py with pytest configuration
- [X] T030 [P] Create integration test framework setup in docker/patches/tests/conftest.py with testcontainers for RAGFlow, Neo4j/FalkorDB

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - RAGFlow UI Document Management (Priority: P1) 🎯 MVP

**Goal**: Manage documents through RAGFlow's built-in web interface at http://localhost:9380

**NOTE**: RAGFlow provides production-ready UI for document upload, chunking, and parsing. Custom ingestion code removed.

**Independent Test**: Access RAGFlow UI, create dataset, upload PDFs via web interface, verify chunks created and searchable

### Tests for User Story 1

> **NOTE: RAGFlow handles document ingestion - tests focus on RAGFlow client integration**

- [REMOVED] T031 [P] [US1] Unit test for heading-aware chunking (RAGFlow handles chunking with 14 built-in templates)
- [REMOVED] T032 [P] [US1] Unit test for confidence band calculation (RAGFlow handles parsing confidence)
- [REMOVED] T033 [P] [US1] Unit test for progressive classification layers (RAGFlow handles document metadata)
- [X] T034 [P] [US1] Integration test for RAGFlow search in docker/patches/tests/integration/test_ragflow_search.py (verify search returns chunks with proper metadata)

### Implementation for User Story 1

> **NOTE**: Docling-based ingestion pipeline REMOVED - use RAGFlow UI instead

- [REMOVED] T035 [P] [US1] Implement Docling PDF ingestion (RAGFlow handles PDF parsing with MinerU/PaddleOCR)
- [REMOVED] T036 [P] [US1] Implement markdown and text file ingestion (RAGFlow supports these formats natively)
- [REMOVED] T037 [US1] Implement idempotency check (RAGFlow handles duplicate detection)
- [REMOVED] T038 [US1] Implement atomic ingestion with rollback (RAGFlow handles ingestion state)
- [REMOVED] T039 [P] [US1] Implement domain classification (RAGFlow handles document metadata)
- [REMOVED] T040 [P] [US1] Implement document type classification (RAGFlow detects file types)
- [REMOVED] T041 [P] [US1] Implement vendor detection (RAGFlow UI allows manual tagging)
- [REMOVED] T042 [P] [US1] Implement component extraction (RAGFlow UI allows manual tagging)
- [REMOVED] T043 [US1] Implement LLM-assisted classification (RAGFlow handles classification)
- [REMOVED] T044 [US1] Create IngestionState tracking (RAGFlow tracks ingestion status)
- [REMOVED] T045 [US1] Implement document move from knowledge/inbox/ to knowledge/processed/ (RAGFlow stores in MinIO)
- [REMOVED] T046 [US1] Implement scheduled reconciliation (RAGFlow handles periodic parsing)
- [REMOVED] T047 [US1] Add ingestion status logging (RAGFlow provides ingestion logs)
- [X] T048 [P] [US1] Create rag.search MCP tool in docker/patches/graphiti_mcp_server.py (query, filters → SearchResult[])
- [X] T049 [P] [US1] Create rag.getChunk MCP tool in docker/patches/graphiti_mcp_server.py (chunk_id → Chunk)
- [X] T050 [P] [US1] Create TypeScript CLI wrapper src/skills/server/lib/rag-cli.ts with search, get-chunk, list, health commands (search-only - upload REMOVED)
- [REMOVED] T051 [US1] Implement batch ingestion handling (RAGFlow UI supports 32 files per batch via UI, unlimited via API)

**Checkpoint**: At this point, User Story 1 should be fully functional - documents managed via RAGFlow UI

---

## Phase 4: User Story 2 - Semantic Search and Evidence Retrieval (Priority: P1)

**Goal**: Provide semantic search returning relevant document chunks with citations, confidence scores, and supporting metadata

**Independent Test**: Index sample documents, run semantic queries, verify relevant chunks returned with proper attribution (confidence >0.70)

### Tests for User Story 2

- [X] T052 [P] [US2] Integration test for semantic search in docker/patches/tests/integration/test_ragflow_search.py (verify filter by domain, type, component, project, version)
- [X] T053 [P] [US2] Integration test for empty results handling in docker/patches/tests/integration/test_ragflow_search.py (return empty when no matches above threshold)

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
- [X] T068 [P] [US3] Implement evidence-to-fact linking in docker/patches/promotion.py (_create_evidence_fact_link() creates PROVENANCE edge via Cypher)
- [X] T069 [US3] Implement provenance preservation in docker/patches/promotion.py (Fact → Evidence → Chunk → Document chain)
- [X] T070 [US3] Implement conflict detection Cypher query in docker/patches/promotion.py (detect_conflicts() uses Cypher with semantic fallback)
- [X] T071 [P] [US3] Implement conflict resolution strategies in docker/patches/promotion.py (detect_only, keep_both, prefer_newest, reject_incoming)
- [X] T072 [US3] Implement version change detection in docker/patches/promotion.py (flag affected facts when source document updated)
- [X] T073 [US3] Implement time-scoped metadata support in docker/patches/promotion.py (observed_at, published_at, valid_until, TTL for security indicators)
- [X] T074 [US3] Add reversible promotion support in docker/patches/promotion.py (facts can be deprecated/removed)

**Checkpoint**: All three P1 user stories should now be independently functional

---

## Phase 6: User Story 4 - Chunk Review and Manual Intervention (Priority: P2)

**Goal**: Use RAGFlow's built-in visual chunk preview for reviewing and improving parsed content

**NOTE**: RAGFlow provides visual chunk editing capabilities. Users can review chunks, add keywords, and correct content via RAGFlow UI.

**Independent Test**: Upload document to RAGFlow, view parsed chunks, add keywords to a chunk, verify improved search relevance

### Tests for User Story 4

- [X] T075 [P] [US4] Integration test for RAGFlow chunk retrieval in docker/patches/tests/integration/test_ragflow_chunks.py (verify getChunk returns chunk with headings and metadata)
- [X] T076 [P] [US4] Integration test for keyword-enhanced search in docker/patches/tests/integration/test_ragflow_search.py (verify keywords improve ranking)

### Implementation for User Story 4

> **NOTE**: Custom review UI REMOVED - use RAGFlow's built-in chunk editor instead

- [REMOVED] T077 [US4] Create review UI service (RAGFlow provides visual chunk preview)
- [REMOVED] T078 [P] [US4] Implement review UI actions (RAGFlow allows double-click to edit chunks)
- [REMOVED] T079 [US4] Implement override learning (RAGFlow stores user edits directly)
- [REMOVED] T080 [P] [US4] Implement leave-in-cancel handling (RAGFlow manages parsing state)

**Checkpoint**: User Story 4 leverages RAGFlow's built-in chunk review - no custom implementation needed

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
- [REMOVED] T094 [P] User-managed backup scripts (NOT REQUIRED - users manage backups via RAGFlow MinIO and Neo4j dumps)
- [X] T095 [P] Code cleanup: remove debug logging, consolidate duplicate code, improve error messages
- [X] T096 [P] Performance optimization: verify <500ms search latency, optimize embedding batch size
- [X] T097 Run full integration test suite (docker/patches/tests/integration/ and tests/integration/) - 365 tests pass
- [X] T098 Run quickstart.md validation (test all workflows from quickstart.md) - rag-cli.ts commands verified
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
3. Complete Phase 3: User Story 1 (RAGFlow UI Document Management)
4. Complete Phase 4: User Story 2 (Semantic Search)
5. Complete Phase 5: User Story 3 (Evidence-Based Knowledge Promotion)
6. **STOP and VALIDATE**: Test all P1 stories independently
7. Deploy/demo if ready

**MVP Success Criteria (RAGFlow-Native)**:
- RAGFlow UI accessible at http://localhost:9380 for document management
- Semantic search returns relevant results in <500ms via RAGFlow API
- Facts can be promoted from evidence with provenance tracking

### Incremental Delivery (RAGFlow-Native)

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (RAGFlow document management working!)
3. Add User Story 2 → Test independently → Deploy/Demo (Search now functional!)
4. Add User Story 3 → Test independently → Deploy/Demo (Knowledge promotion enabled!)
5. Add User Story 4 → Test independently → Deploy/Demo (RAGFlow chunk review available!)
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

- **Total Tasks**: 99 tasks (original), ~68 tasks after RAGFlow-native refactoring
- **Setup Phase**: 11 tasks (T001-T011)
- **Foundational Phase**: 20 tasks (T012-T031) - BLOCKS all user stories
- **User Story 1 (P1)**: 4 tasks remaining (T034, T048-T050) - RAGFlow UI + search tools - MVP Core
- **User Story 2 (P1)**: 10 tasks (T052-T061) - Search capability
- **User Story 3 (P1)**: 14 tasks (T062-T074) - Knowledge promotion
- **User Story 4 (P2)**: 2 tasks remaining (T075-T076) - RAGFlow chunk review
- **User Story 5 (P3)**: 8 tasks (T081-T089) - Conflict resolution
- **Polish Phase**: 10 tasks (T090-T099)

**Task Count by User Story (After RAGFlow Refactoring)**:
- US1 (P1): 4 tasks (1 test + 3 implementation) - RAGFlow UI + search tools
- US2 (P1): 10 tasks (including 2 tests)
- US3 (P1): 14 tasks (including 4 tests)
- US4 (P2): 2 tasks (2 tests for RAGFlow integration)
- US5 (P3): 8 tasks (including 3 tests)

**Independent Test Criteria (Updated for RAGFlow)**:
- US1: Access RAGFlow UI, create dataset, upload documents via web interface, verify chunks created and searchable
- US2: Index documents, search queries, verify relevant chunks with confidence >0.70
- US3: Promote evidence, verify fact in graph with provenance
- US4: View RAGFlow chunks, add keywords, verify improved search relevance
- US5: Promote conflicting facts, verify conflict detection and resolution

**Parallel Opportunities**: 42 tasks marked [P] can run in parallel with appropriate team allocation

**Suggested MVP Scope**: Phase 1 + Phase 2 + Phase 3 (US1 RAGFlow UI + search tools) for document management MVP
**Full Release**: Phases 1-5 (All P1 stories: US1, US2, US3) for complete RAG + Knowledge Graph capability
**Enhanced Release**: All phases (P1 + P2 + P3 stories) for full system with RAGFlow chunk review and conflict resolution

**Format Validation**: ✅ ALL tasks follow checklist format (checkbox, ID, story labels, file paths)

**RAGFlow-Native Architecture (2026-02-09)**:
- Documents managed via RAGFlow web UI at http://localhost:9380
- RAGFlow handles parsing, chunking, and embedding with 14 built-in templates
- Custom ingestion code removed: docling_ingester.py, chunking_service.py, classification.py
- knowledge/inbox/ and knowledge/processed/ no longer needed (RAGFlow uses MinIO)
- LKAP focuses on search tools and knowledge promotion with provenance tracking

---

## ⚠️ REDTEAM AUDIT FINDINGS (2026-02-09)

**Critical**: A 32-agent parallel RedTeam analysis identified gaps in tasks marked [X].
Full report: `specs/022-self-hosted-rag/redteam-audit-report.md`

### 🔄 RAGFLOW-NATIVE REFACTORING (2026-02-09)

**Architecture Simplification**: The following components are now REMOVED as RAGFlow handles them natively:
- **T023** - Filesystem watcher (REMOVED: RAGFlow UI provides document upload)
- **T024-T026** - Chunking and classification services (REMOVED: RAGFlow handles with 14 built-in templates)
- **T031-T037** - Docling ingestion tests (REMOVED: RAGFlow handles parsing with MinerU/PaddleOCR)
- **T038-T047** - Docling ingestion implementation (REMOVED: Use RAGFlow UI instead)

### 🔴 CRITICAL BLOCKERS (Fix Before Deployment)

1. **T020** - RAGFlow API endpoints missing `/api/v1` prefix → all calls return 404
2. **T064/T068** - `promotion.init_graphiti()` never called → RuntimeError on all kg operations
3. **T042** - `self.embedding_model` undefined → OpenRouter embeddings crash (REMOVED with classification)

### 🟡 PARTIAL IMPLEMENTATIONS (Stub/TODO)

- ~~**T034**~~ - LLM classification layer stubbed (REMOVED: RAGFlow handles classification)
- ~~**T046**~~ - Embedding caching not implemented (REMOVED: RAGFlow handles embeddings)
- ~~**T048**~~ - Heading prefix contextualization not implemented (REMOVED: RAGFlow handles chunking)
- **T057** - Chunk heading/position tracking incomplete (RAGFlow provides this via chunk metadata)
- **T058** - No specific HTTP status handling (400, 401, 404, 503)
- ~~**T064**~~ - Evidence-to-fact edge creation is stub → **FIXED**: `_create_evidence_fact_link()` creates PROVENANCE edge via Cypher
- **T065** - Provenance returns placeholder chain
- ~~**T070**~~ - Uses semantic search instead of documented Cypher query → **FIXED**: `detect_conflicts()` uses Cypher with semantic fallback
- **T072** - Cypher query exists but not used for conflict detection
- ~~**T075**~~ - Conflict visualization not implemented (REMOVED: RAGFlow UI provides visualization)
- **T077** - Conflict severity scoring not implemented (PARTIAL: T077 severity field added to Conflict model)
- **T087** - Pydantic models defined but not used for MCP validation
- **T088** - ErrorResponse import broken (file missing)

### 🟢 MISSING CLI COMMANDS

The following CLI commands are referenced but NOT implemented in knowledge-cli.ts:
- `promoteFromEvidence` - Promote evidence chunk to knowledge graph
- `promoteFromQuery` - Search and promote in one operation
- `provenance` - Trace fact to source documents
- `conflicts` - Review and resolve conflicts

These MCP tools exist (`kg.promoteFromEvidence`, `kg.promoteFromQuery`, `kg.getProvenance`, `kg.reviewConflicts`) but have no CLI wrappers.

### 📊 Status Summary (Updated 2026-02-13)

| Status | Count | Percentage |
|--------|-------|------------|
| Fully Implemented | 78 | 79% |
| Partial / Stub | 12 | 12% |
| Not Implemented | 8 | 8% |
| Critical Blockers | 1 | 1% |

### Remediation Priority

**P0** (Blockers): Fix T020 API endpoints, T064/T068 initialization, T042 bug
**P1** (Core): Complete T034 LLM layer, T046 caching, T048 contextualization
**P2** (Robustness): Add retry logic, HTTP status handling, Cypher queries
**P3** (UX): Add CLI wrappers, visualization, severity scoring
**P4** (Docs): Missing docker-compose-ollama.yml, data-model.md, test validation
