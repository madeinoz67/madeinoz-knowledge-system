---

description: "Task list for Qdrant RAG Migration implementation"
---

# Tasks: Qdrant RAG Migration

**Input**: Design documents from `/specs/023-qdrant-rag/`
**Prerequisites**: plan.md, spec.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

**For this project (Madeinoz Knowledge System):**
- **Python code**: `docker/patches/` for implementation, `docker/patches/tests/` for tests
- **TypeScript code**: `src/` for implementation, `tests/` for tests
- **Config**: `config/` for configuration files
- **Compose files**: `docker/` for container definitions
- **Knowledge storage**: `knowledge/` for document storage

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and container setup

- [X] T001 Create knowledge directory structure: `knowledge/inbox/` and `knowledge/processed/`
- [X] T002 Create docker/docker-compose-qdrant.yml with Qdrant container configuration (port 6333, 69MB image)
- [X] T003 [P] Update docker/Dockerfile to add Docling dependencies (`docling`, `docling-core`) and remove RAGFlow deps
- [X] T004 [P] Create config/qdrant.yaml with Qdrant configuration (collection name, embedding dimension: 1024)
- [X] T005 [P] Update config/.env.example with Qdrant environment variables (QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION)
- [X] T006 [P] Create docker/patches/tests/unit/test_qdrant_setup.py with basic connectivity tests

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Implement OllamaEmbedder class in docker/patches/ollama_embedder.py with bge-large-en-v1.5 model (1024 dimensions)
- [X] T008 [P] Implement SemanticChunker class in docker/patches/semantic_chunker.py with 512-768 token chunks, 10-20% overlap
- [X] T009 [P] Update docker/patches/qdrant_client.py with collection creation, health check, and connection pooling
- [X] T010 [P] Create DocumentChunk model in docker/patches/lkap_models.py with chunk_id, text, token_count, page_number, headings, source_document_id
- [X] T011 [P] Create IngestionResult model in docker/patches/lkap_models.py with doc_id, chunk_count, status, error_message
- [X] T012 Update docker/patches/__init__.py to export new modules (ollama_embedder, semantic_chunker)
- [X] T013 Create Qdrant collection schema with payload indexes for filtering (domain, project, component, type)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Document Ingestion (Priority: P1) 🎯 MVP

**Goal**: Ingest PDF and markdown documents into Qdrant with semantic chunking and embeddings

**Independent Test**: Place document in `knowledge/inbox/`, run ingest CLI, verify chunks in Qdrant with embeddings

### Tests for User Story 1

- [ ] T014 [P] [US1] Unit test for PDF parsing in docker/patches/tests/unit/test_docling_ingester.py
- [ ] T015 [P] [US1] Unit test for markdown parsing in docker/patches/tests/unit/test_docling_ingester.py
- [ ] T016 [P] [US1] Unit test for semantic chunking in docker/patches/tests/unit/test_semantic_chunker.py
- [ ] T017 [P] [US1] Integration test for full ingestion pipeline in docker/patches/tests/integration/test_ingestion.py

### Implementation for User Story 1

- [X] T018 [P] [US1] Implement DoclingIngester.parse_pdf() in docker/patches/docling_ingester.py with table extraction
- [X] T019 [P] [US1] Implement DoclingIngester.parse_markdown() in docker/patches/docling_ingester.py with heading awareness
- [X] T020 [P] [US1] Implement DoclingIngester.parse_text() in docker/patches/docling_ingester.py for plain text
- [X] T021 [US1] Implement DoclingIngester.ingest() orchestrating parsing → chunking → embedding → storage
- [X] T022 [US1] Implement idempotent ingestion check using document hash in docker/patches/docling_ingester.py
- [X] T023 [US1] Implement document move from inbox/ to processed/ after successful ingestion
- [X] T024 [US1] Add ingestion error handling with rollback on partial failure
- [X] T025 [US1] Add ingestion logging with progress and status in docker/patches/lkap_logging.py

**Checkpoint**: At this point, User Story 1 should be fully functional - documents can be ingested into Qdrant

---

## Phase 4: User Story 2 - Semantic Search (Priority: P1)

**Goal**: Provide semantic search returning relevant chunks with confidence scores

**Independent Test**: Ingest documents, run search query via CLI or MCP, verify ranked results with scores >0.70

### Tests for User Story 2

- [ ] T026 [P] [US2] Unit test for semantic search in docker/patches/tests/unit/test_qdrant_search.py
- [ ] T027 [P] [US2] Integration test for search with filters in docker/patches/tests/integration/test_search.py
- [ ] T028 [P] [US2] Integration test for empty results handling in docker/patches/tests/integration/test_search.py

### Implementation for User Story 2

- [X] T029 [P] [US2] Implement QdrantClient.search() with top-k retrieval and confidence threshold (0.70)
- [X] T030 [US2] Implement search result filtering by metadata (domain, project, component, type)
- [X] T031 [US2] Implement SearchResult model with chunk_id, text, source, page, confidence, metadata
- [X] T032 [US2] Add search latency tracking (<500ms target) with logging
- [X] T033 [US2] Implement empty result handling (return [], not error)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Chunk Retrieval (Priority: P2)

**Goal**: Retrieve specific chunks by ID with full metadata

**Independent Test**: Search for document, get chunk ID, retrieve chunk directly, verify all metadata

### Tests for User Story 3

- [ ] T034 [P] [US3] Unit test for chunk retrieval in docker/patches/tests/unit/test_qdrant_client.py
- [ ] T035 [P] [US3] Integration test for chunk not found handling in docker/patches/tests/integration/test_retrieval.py

### Implementation for User Story 3

- [X] T036 [US3] Implement QdrantClient.get_chunk() with full metadata retrieval
- [X] T037 [US3] Implement "chunk not found" error with clear message
- [X] T038 [US3] Add chunk retrieval logging

**Checkpoint**: Chunk retrieval working independently

---

## Phase 6: User Story 4 - MCP Tool Integration (Priority: P2)

**Goal**: Expose RAG capabilities through MCP tools for AI assistants

**Independent Test**: Call MCP tools from client, verify search/retrieval/ingest work correctly

### Tests for User Story 4

- [ ] T039 [P] [US4] Contract test for rag.search MCP tool in docker/patches/tests/contract/test_rag_tools.py
- [ ] T040 [P] [US4] Contract test for rag.getChunk MCP tool in docker/patches/tests/contract/test_rag_tools.py
- [ ] T041 [P] [US4] Contract test for rag.ingest MCP tool in docker/patches/tests/contract/test_rag_tools.py

### Implementation for User Story 4

- [X] T042 [US4] Implement rag.search MCP tool in docker/patches/graphiti_mcp_server.py using QdrantClient
- [X] T043 [US4] Implement rag.getChunk MCP tool in docker/patches/graphiti_mcp_server.py
- [X] T044 [US4] Implement rag.ingest MCP tool in docker/patches/graphiti_mcp_server.py
- [X] T045 [US4] Update TypeScript CLI wrapper src/skills/server/lib/rag-cli.ts with Qdrant endpoints
- [X] T046 [US4] Create src/skills/server/lib/qdrant.ts TypeScript wrapper for Qdrant HTTP API
- [X] T047 [US4] Add rag.health MCP tool for Qdrant connectivity check

**Checkpoint**: All MCP tools functional

---

## Phase 7: User Story 5 - RAGFlow Removal (Priority: P3)

**Goal**: Remove all RAGFlow dependencies for lightweight system

**Independent Test**: Search codebase for "ragflow" (should be 0 matches), verify all tests pass

### Implementation for User Story 5

- [X] T048 [US5] Remove RAGFlowClient import from docker/patches/graphiti_mcp_server.py
- [X] T049 [US5] Delete docker/patches/ragflow_client.py
- [X] T050 [US5] Delete docker/docker-compose-ragflow.yml
- [X] T051 [US5] Update docker/patches/tests/integration/ tests to use Qdrant instead of RAGFlow
- [X] T052 [US5] Remove RAGFlow environment variables from config/.env.example
- [X] T053 [US5] Remove RAGFlow references from docker/Dockerfile
- [X] T054 [US5] Update docs/usage/lkap-quickstart.md with Qdrant instructions

**Checkpoint**: RAGFlow completely removed

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T055 [P] Update CLAUDE.md with Qdrant-specific configuration and usage instructions
- [ ] T056 [P] Update docs/reference/configuration.md with Qdrant environment variables
- [ ] T057 [P] Update docs/usage/lkap-quickstart.md with Qdrant workflow
- [ ] T058 [P] Update docs/reference/observability.md with Qdrant metrics
- [ ] T059 Code cleanup: remove debug logging, consolidate duplicate code
- [ ] T060 Performance optimization: verify <500ms search latency, optimize batch embedding
- [ ] T061 Run full test suite: `bun test` and `pytest docker/patches/tests/`
- [ ] T062 Run quickstart.md validation (test all CLI commands)
- [ ] T063 Update CHANGELOG.md with Qdrant migration summary

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US1 (Ingestion) and US2 (Search) can run in parallel (both P1)
  - US3 (Retrieval) depends on US2 search infrastructure
  - US4 (MCP Tools) depends on US1, US2, US3 being functional
  - US5 (Removal) should be done last after all features work
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational - Independent of US1 (search works on pre-existing data)
- **User Story 3 (P2)**: Can start after US2 - Depends on chunk structure from search
- **User Story 4 (P2)**: Can start after US1, US2, US3 - Integrates all capabilities
- **User Story 5 (P3)**: Can start after US4 - Only after all features migrated

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T003-T006)
- All Foundational tasks marked [P] can run in parallel (T008-T011)
- US1 and US2 can run in parallel (both P1)
- All tests within a story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for PDF parsing in docker/patches/tests/unit/test_docling_ingester.py"
Task: "Unit test for markdown parsing in docker/patches/tests/unit/test_docling_ingester.py"
Task: "Unit test for semantic chunking in docker/patches/tests/unit/test_semantic_chunker.py"

# Launch all parsing implementations together:
Task: "Implement DoclingIngester.parse_pdf() in docker/patches/docling_ingester.py"
Task: "Implement DoclingIngester.parse_markdown() in docker/patches/docling_ingester.py"
Task: "Implement DoclingIngester.parse_text() in docker/patches/docling_ingester.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Ingestion)
4. Complete Phase 4: User Story 2 (Search)
5. **STOP and VALIDATE**: Test ingestion and search independently
6. Deploy/demo if ready

**MVP Success Criteria**:
- Documents can be ingested into Qdrant
- Semantic search returns relevant chunks with confidence scores
- Memory footprint under 200MB (vs 3.5GB for RAGFlow)

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (Ingestion working!)
3. Add User Story 2 → Test independently → Deploy/Demo (Search functional!)
4. Add User Story 3 → Test independently → Deploy/Demo (Full retrieval!)
5. Add User Story 4 → Test independently → Deploy/Demo (MCP tools available!)
6. Add User Story 5 → Test independently → Deploy/Demo (RAGFlow removed!)
7. Each story adds value without breaking previous stories

---

## Summary

- **Total Tasks**: 63 tasks
- **Setup Phase**: 6 tasks (T001-T006)
- **Foundational Phase**: 7 tasks (T007-T013)
- **User Story 1 (P1)**: 12 tasks (T014-T025) - Document Ingestion
- **User Story 2 (P1)**: 8 tasks (T026-T033) - Semantic Search
- **User Story 3 (P2)**: 5 tasks (T034-T038) - Chunk Retrieval
- **User Story 4 (P2)**: 9 tasks (T039-T047) - MCP Tool Integration
- **User Story 5 (P3)**: 7 tasks (T048-T054) - RAGFlow Removal
- **Polish Phase**: 9 tasks (T055-T063)

**Task Count by User Story**:
- US1 (P1): 12 tasks (4 tests + 8 implementation)
- US2 (P1): 8 tasks (3 tests + 5 implementation)
- US3 (P2): 5 tasks (2 tests + 3 implementation)
- US4 (P2): 9 tasks (3 tests + 6 implementation)
- US5 (P3): 7 tasks (0 tests + 7 implementation)

**Independent Test Criteria**:
- US1: Place document in inbox/, run ingest, verify chunks in Qdrant
- US2: Ingest documents, search query, verify ranked results with scores >0.70
- US3: Get chunk by ID, verify full metadata returned
- US4: Call MCP tools from client, verify all operations work
- US5: Search codebase for "ragflow", verify 0 matches, all tests pass

**Parallel Opportunities**: 28 tasks marked [P] can run in parallel

**Suggested MVP Scope**: Phase 1 + Phase 2 + Phase 3 (US1 Ingestion) for document management MVP
**Full Release**: Phases 1-6 (US1-US4) for complete RAG with MCP tools
**Complete Migration**: All phases (US1-US5 + Polish) for full RAGFlow removal

**Format Validation**: ✅ ALL tasks follow checklist format (checkbox, ID, story labels, file paths)
