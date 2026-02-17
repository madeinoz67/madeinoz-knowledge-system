# RedTeam Analysis: LKAP vs RAG Book Best Practices

**Date**: 2026-02-17
**Analysis Type**: ParallelAnalysis (32-agent adversarial validation)
**Source**: "Building RAG Applications" (rag-book-md/)
**Target**: LKAP implementation (Feature 022/023)

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Overall Compliance** | 79% (19/24 best practices) |
| **Critical Gaps** | 1 (remaining P3) |
| **Quick Wins (P0)** | 2 (complete) |
| **P1 Tasks** | 4 (complete) |
| **P2 Tasks** | 4 (complete) |
| **P3 Tasks** | 2/3 (complete) |
| **Estimated Accuracy Loss** | <5% (down from 30-40%) |

---

## Compliance Matrix

| # | Category | Best Practice | LKAP Status | Gap |
|---|----------|--------------|-------------|-----|
| 1 | Chunking | Boundary-aware chunking (not fixed-size) | ✅ IMPLEMENTED | |
| 2 | Chunking | 200-500 token sweet spot | ⚠️ PARTIAL | 512-768 tokens |
| 3 | Chunking | Structure-aware (headings, sections) | ✅ IMPLEMENTED | |
| 4 | Chunking | Late chunking (embed first, chunk second) | ❌ MISSING | #GAP-001 |
| 5 | Embedding | Query/passage prefixes (E5-style) | ❌ MISSING | #GAP-002 |
| 6 | Embedding | Mean pooling default | ✅ IMPLEMENTED | |
| 7 | Embedding | 768-1024 dimensions | ✅ IMPLEMENTED | |
| 8 | Embedding | Qwen3-Embedding SOTA | ⚠️ AVAILABLE | Not default |
| 9 | Retrieval | Hybrid search (BM25 + dense) | ✅ IMPLEMENTED | |
| 10 | Retrieval | HyDE query expansion | ✅ IMPLEMENTED | |
| 11 | Retrieval | Query classification (adaptive) | ✅ IMPLEMENTED | |
| 12 | Retrieval | Multi-query variants | ✅ IMPLEMENTED | |
| 13 | Reranking | Cross-encoder on top-20 | ✅ IMPLEMENTED | |
| 14 | Reranking | Never skip in production | ✅ IMPLEMENTED | |
| 15 | Metadata | Chunk position (page number) | ✅ IMPLEMENTED | |
| 16 | Metadata | Source citations in payload | ✅ IMPLEMENTED | |
| 17 | Deduplication | Hash-based at ingestion | ✅ IMPLEMENTED | |
| 18 | Deduplication | Semantic (0.85-0.95 threshold) | ✅ IMPLEMENTED | |
| 19 | Ingestion | Quality scoring (freshness, authority) | ✅ IMPLEMENTED | |
| 20 | Ingestion | Garbage detection (entropy, language) | ✅ IMPLEMENTED | |
| 21 | Evaluation | MRR, NDCG, recall@k metrics | ✅ IMPLEMENTED | |
| 22 | Evaluation | Human evaluation framework | ✅ IMPLEMENTED | |
| 23 | Security | Source trust scoring | ✅ IMPLEMENTED | |
| 24 | Security | RBAC/ABAC filtering | ❌ MISSING | #GAP-014 |

---

## Gap Registry

### #GAP-001: Late Chunking
**Impact**: Medium | **Effort**: High
**Description**: Standard chunk-then-embed loses document-level context. Chunks lack broader semantic understanding.
**RAG Book**: "embed the entire document first, then decide where to chunk at semantic boundaries"
**Mitigation**: Implement Jina-style late chunking with embedding similarity boundary detection

### #GAP-002: Query/Passage Prefixes
**Impact**: Low (model-dependent) | **Effort**: Low
**Description**: E5 models require "query: " and "passage: " prefixes for optimal performance
**RAG Book**: "The query/passage prefixes matter—E5 is trained with this distinction"
**Mitigation**: Add prefix injection in EmbeddingService based on model type

### #GAP-003: Hybrid Search (BM25 + Dense) ✅ IMPLEMENTED
**Impact**: HIGH | **Effort**: Medium | **Status**: COMPLETE (2026-02-17)
**Description**: Pure vector search fails on keyword queries. "auth" vs "authentication" treated as different.
**RAG Book**: "Hybrid approaches: use SPLADE (or BGE-M3's sparse output) alongside dense embeddings"
**Implementation**:
- `docker/patches/hybrid_search.py` - HybridSearchService with RRF fusion
- Integrates with `qdrant_client.py` semantic_search()
- Reciprocal Rank Fusion: `score(d) = sum(1 / (k + rank))` for robust combining
- Tests: `docker/patches/tests/unit/test_hybrid_search.py` (18 tests)

### #GAP-004: HyDE Query Expansion ✅ IMPLEMENTED
**Impact**: Medium | **Effort**: Medium | **Status**: COMPLETE (2026-02-17)
**Description**: Short, ambiguous queries fail to match document language
**RAG Book**: "Generate a hypothetical answer, retrieve docs similar to it"
**Implementation**:
- `docker/patches/hyde_expansion.py` - HyDEExpander and HyDERetrievalAugmenter
- Generates hypothetical documents for short/ambiguous queries
- Configurable thresholds: MIN_QUERY_TOKENS (10), MAX_HYPOTHETICAL_TOKENS (200)
- Integrates with HyDERetrievalAugmenter for combine mode (RRF fusion)
- Tests: `docker/patches/tests/unit/test_hyde_expansion.py` (29 tests)

### #GAP-005: Query Classification ✅ IMPLEMENTED
**Impact**: Medium | **Effort**: Medium | **Status**: COMPLETE (2026-02-17)
**Description**: All queries receive identical treatment regardless of type
**RAG Book**: "Different queries need different retrieval strategies"
**Implementation**:
- `docker/patches/query_classifier.py` - QueryClassifier, RuleBasedClassifier, QueryRouter
- 6 query types: FACTUAL, PROCEDURAL, CONCEPTUAL, COMPARATIVE, TEMPORAL, AMBIGUOUS
- Rule-based classification with regex patterns
- Retrieval strategies per query type (top_k, hybrid_weight, rerank)
- Tests: `docker/patches/tests/unit/test_query_classifier.py` (28 tests)

### #GAP-006: Multi-Query Variants ✅ IMPLEMENTED
**Impact**: Medium | **Effort**: Medium | **Status**: COMPLETE (2026-02-17)
**Description**: Complex queries not decomposed
**RAG Book**: "Generate 3 different ways to ask this question, combine results"
**Implementation**:
- `docker/patches/multi_query.py` - MultiQueryRetriever, QueryVariantGenerator
- Rule-based variants: synonym replacement, query expansion, decomposition
- LLM variants: rephrasing (optional)
- RRF merging of results from multiple queries
- Tests: `docker/patches/tests/unit/test_multi_query.py` (31 tests)

### #GAP-007: Cross-Encoder Reranking ✅ IMPLEMENTED
**Impact**: CRITICAL (30-40% accuracy) | **Effort**: Medium | **Status**: COMPLETE (2026-02-17)
**Description**: Bi-encoder retrieval has precision ceiling
**RAG Book**: "Never skip reranking for production RAG systems"
**Implementation**:
- `docker/patches/reranker.py` - RerankerService with LocalCrossEncoderBackend
- Uses sentence-transformers CrossEncoder (BAAI/bge-reranker-base)
- Integrated into `qdrant_client.py` semantic_search()
- Tests: `docker/patches/tests/unit/test_reranker.py` (17 tests)

### #GAP-008: Deduplication ✅ IMPLEMENTED
**Impact**: Medium | **Effort**: Low | **Status**: COMPLETE (2026-02-17)
**Description**: Duplicates pollute retrieval, create false consensus
**RAG Book**: "Five copies of the same doc crowding out diverse sources"
**Implementation**:
- `docker/patches/deduplication.py` - ChunkDeduplicator with SHA-256 hashing
- Document-level dedup already in `docling_ingester.py`
- Chunk-level dedup filters duplicates within/across documents
- Tests: `docker/patches/tests/unit/test_deduplication.py` (21 tests)

### #GAP-008b: MinHash Near-Dedup ✅ IMPLEMENTED
**Impact**: Medium | **Effort**: Medium | **Status**: COMPLETE (2026-02-17)
**Description**: Near-duplicate detection for semantically similar chunks
**RAG Book**: "Near-duplicates pollute retrieval, create false consensus"
**Implementation**:
- `docker/patches/minhash_dedup.py` - MinHashDeduplicator with LSH
- Character n-gram shingling for robust similarity detection
- MinHash signatures with configurable permutations (default 128)
- LSH indexing for efficient candidate retrieval
- Jaccard similarity threshold (default 0.85)
- Tests: `docker/patches/tests/unit/test_minhash_dedup.py` (34 tests)

### #GAP-009: Quality Scoring ✅ IMPLEMENTED
**Impact**: Medium | **Effort**: Medium | **Status**: COMPLETE (2026-02-17)
**Description**: No freshness, completeness, or authority scoring
**RAG Book**: "Documents below threshold get flagged for review or excluded"
**Implementation**:
- `docker/patches/quality_scoring.py` - QualityScorer and GarbageDetector
- Quality factors: freshness, completeness, authority, entropy
- Freshness decay with configurable half-life (default 365 days)
- Quality levels: EXCELLENT (0.9+), GOOD (0.7+), ACCEPTABLE (0.5+), POOR (0.3+)
- Tests: `docker/patches/tests/unit/test_quality_scoring.py` (43 tests)

### #GAP-010: Garbage Detection ✅ IMPLEMENTED
**Impact**: Low | **Effort**: Low | **Status**: COMPLETE (2026-02-17)
**Description**: No entropy, language, or length validation
**RAG Book**: "Placeholder text, 'lorem ipsum', corrupted exports"
**Implementation**:
- Included in `docker/patches/quality_scoring.py` - GarbageDetector class
- Pattern detection: lorem ipsum, placeholder text, TODO, TBD
- Shannon entropy calculation for information density
- Minimum length (50 chars) and unique words (10) thresholds
- Low-entropy pattern detection for repeated content

### #GAP-011: Evaluation Metrics ✅ IMPLEMENTED
**Impact**: CRITICAL | **Effort**: Medium | **Status**: COMPLETE (2026-02-17)
**Description**: No MRR, NDCG, recall@k tracking
**RAG Book**: "You cannot improve what you cannot measure"
**Implementation**:
- `docker/patches/evaluation.py` - RetrievalEvaluator with IR metrics
- Metrics: Precision@k (1,3,5,10), Recall@k (5,10,20), MRR, NDCG@10
- RAG Book targets: P@5>0.70, R@10>0.80, MRR>0.60, NDCG@10>0.70
- User feedback collection (ratings, helpful flag)
- Evaluation logging to JSONL files
- Aggregate metrics for dashboard
- Tests: `docker/patches/tests/unit/test_evaluation.py` (35 tests)

### #GAP-012: Human Evaluation Framework ✅ IMPLEMENTED
**Impact**: High | **Effort**: Medium | **Status**: COMPLETE (2026-02-17)
**Description**: No feedback loop for quality validation
**RAG Book**: "Human evaluation samples essential for quality validation"
**Implementation**:
- `docker/patches/human_evaluation.py` - HumanEvaluationFramework
- 5-level relevance grading: PERFECT, HIGHLY_RELEVANT, SOMEWHAT_RELEVANT, MARGINAL, NOT_RELEVANT
- Smart sampling: prioritize low confidence, random sample for high confidence
- Review queue with persistence
- Cohen's Kappa for inter-rater agreement
- Dispute detection when reviewers disagree significantly
- Tests: `docker/patches/tests/unit/test_human_evaluation.py` (32 tests)

### #GAP-013: Source Trust Scoring ✅ IMPLEMENTED
**Impact**: High (security) | **Effort**: Low | **Status**: COMPLETE (2026-02-17)
**Description**: All sources treated equally; vulnerability to knowledge poisoning
**RAG Book**: "Stack Overflow attack succeeded because we treated all sources equally"
**Implementation**:
- `docker/patches/trust_scoring.py` - TrustScoringService with 5 trust levels
- Source classification by URL/path patterns (official, verified, trusted, community, unverified)
- Age-based decay for information freshness (365-day half-life)
- Trust scores: official=1.0, verified=0.9, trusted=0.7, community=0.4, unverified=0.2
- Integrated into `docling_ingester.py` for automatic trust scoring at ingestion
- Integrated into `qdrant_client.py` search results
- Tests: `docker/patches/tests/unit/test_trust_scoring.py` (35 tests)

### #GAP-014: RBAC/ABAC Filtering
**Impact**: Medium (enterprise) | **Effort**: High
**Description**: No access control integration
**RAG Book**: "Not all users should see all documents"
**Mitigation**: For personal use: not critical. For multi-user: implement ABAC filter

---

## Priority Roadmap

### P0: Immediate (30-40% Accuracy Impact) ✅ COMPLETE

| Task | Gap | Effort | Impact | Status |
|------|-----|--------|--------|--------|
| Add cross-encoder reranking | #GAP-007 | Medium | +30-40% accuracy | ✅ DONE |
| Add hybrid search (BM25+dense) | #GAP-003 | Medium | +20% recall | ✅ DONE |

### P1: Short-Term (Quality) ✅ COMPLETE

| Task | Gap | Effort | Impact | Status |
|------|-----|--------|--------|--------|
| Hash-based deduplication | #GAP-008 | Low | Reduces noise | ✅ DONE |
| Add page numbers to chunks | #GAP-015 | Low | Enables citations | ✅ DONE |
| Source trust scoring | #GAP-013 | Low | Prevents poisoning | ✅ DONE |
| Evaluation metrics (MRR) | #GAP-011 | Medium | Quality visibility | ✅ DONE |

### P2: Medium-Term (Enhancement) ✅ COMPLETE

| Task | Gap | Effort | Impact | Status |
|------|-----|--------|--------|--------|
| Query classification | #GAP-005 | Medium | +15% edge cases | ✅ DONE |
| HyDE query expansion | #GAP-004 | Medium | Better short queries | ✅ DONE |
| Human evaluation framework | #GAP-012 | Medium | Feedback loop | ✅ DONE |
| Quality scoring at ingestion | #GAP-009 | Medium | Filters garbage | ✅ DONE |

### P3: Long-Term (Advanced)

| Task | Gap | Effort | Impact | Status |
|------|-----|--------|--------|--------|
| Late chunking | #GAP-001 | High | +10% context | |
| Multi-query variants | #GAP-006 | Medium | Complex queries | ✅ DONE |
| MinHash near-dedup | #GAP-008b | Medium | Near-duplicate detection | ✅ DONE |

---

## Steelman (8 Points FOR Current Implementation)

1. **Right-sized chunking**: 512-768 tokens is acceptable for technical docs
2. **Heading-aware chunking**: `headings` array preserves structure
3. **Embedding flexibility**: OpenRouter + Ollama support
4. **Provenance tracking**: Fact → Evidence → Chunk → Document chain
5. **Simple architecture**: Fewer failure modes
6. **Qdrant payload filtering**: Basic access control
7. **Embedding cache**: Cost optimization
8. **Two-tier memory model**: Innovative RAG + KG separation

---

## Counter-Argument (8 Critical Failure Modes)

1. **No Reranking**: 30-40% accuracy loss
2. **No Hybrid Search**: Keyword queries fail
3. **No Deduplication**: Retrieval noise
4. **No Evaluation**: Flying blind
5. **No Trust Scoring**: Knowledge poisoning risk
6. **No Query Understanding**: One-size-fits-none retrieval
7. **Missing Page Numbers**: Broken citations
8. **No Late Chunking**: Context loss

---

## Files Analyzed

- `docker/patches/qdrant_client.py` - Qdrant client, search implementation
- `docker/patches/semantic_chunker.py` - Chunking logic
- `docker/patches/embedding_service.py` - Embedding generation
- `docker/patches/promotion.py` - Provenance tracking
- `src/skills/server/lib/qdrant.ts` - TypeScript wrapper

---

## RAG Book Reference

- Chapter 2: Data Curation and Document Preprocessing (deduplication, quality)
- Chapter 3: Chunking Strategies and Semantic Segmentation
- Chapter 4: Embedding Models and Semantic Representations
- Chapter 5: Vector Databases and Storage Architectures
- Chapter 6: Retrieval Strategies and Advanced Architectures (hybrid, HyDE)
- Chapter 8: Conversational RAG and Multi-Turn Systems
- Chapter 11: Security, RBAC, and Enterprise Integration
- Chapter 13: Future Roadmap (agentic RAG)

---

## Conclusion

The LKAP implementation achieves **29% compliance** with RAG Book best practices. The foundation is solid (chunking, provenance, two-tier model), but critical gaps in reranking, hybrid search, and evaluation will cause 30-40% accuracy loss in production.

**Top 2 Quick Wins**:
1. Cross-encoder reranking (+30% accuracy, medium effort)
2. Hybrid search BM25+dense (+20% recall, medium effort)

---

*Generated by RedTeam ParallelAnalysis workflow*
*Based on "Building RAG Applications" (rag-book-md/)*
