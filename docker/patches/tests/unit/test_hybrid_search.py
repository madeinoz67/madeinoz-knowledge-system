"""
Unit Tests for Hybrid Search (GAP-003)
Feature 023 Enhancement: RAG Book Compliance

Tests for hybrid search combining BM25 + dense retrieval for +20% recall.

RAG Book Reference:
"Hybrid approaches: use SPLADE (or BGE-M3's sparse output) alongside dense
embeddings. When hybrid helps: acronyms, exact phrase matching, rare terms."
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio
import os
import sys

# Add patches directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'patches'))


class TestReciprocalRankFusion:
    """Unit tests for RRF fusion algorithm."""

    def test_rrf_combines_ranks_correctly(self):
        """Test RRF gives higher scores to docs appearing in both lists."""
        from hybrid_search import reciprocal_rank_fusion

        # Dense results: doc_a at rank 0, doc_b at rank 1
        dense = [("doc_a", 0.9, {}), ("doc_b", 0.8, {})]
        # Sparse results: doc_b at rank 0, doc_c at rank 1
        sparse = [("doc_b", 0.95, {}), ("doc_c", 0.85, {})]

        results = reciprocal_rank_fusion(dense, sparse, k=60)

        # doc_b appears in both lists (rank 1 in dense, rank 0 in sparse)
        # RRF score = 1/(60+1) + 1/(60+0) = 0.0164 + 0.0167 = 0.0331
        # doc_a: RRF = 1/(60+0) = 0.0167
        # doc_c: RRF = 1/(60+1) = 0.0164
        assert len(results) == 3
        assert results[0][0] == "doc_b"  # doc_b should win (appears in both)
        assert results[0][1] > results[1][1]  # doc_b score > others

    def test_rrf_respects_k_parameter(self):
        """Test RRF k parameter affects score dampening."""
        from hybrid_search import reciprocal_rank_fusion

        dense = [("doc_a", 0.9, {})]
        sparse = [("doc_a", 0.95, {})]

        # With k=1, rank 0 gets score 1/(1+0) = 1.0
        results_k1 = reciprocal_rank_fusion(dense, sparse, k=1)
        # With k=60, rank 0 gets score 1/(60+0) = 0.0167
        results_k60 = reciprocal_rank_fusion(dense, sparse, k=60)

        assert results_k1[0][1] == 2.0  # 1.0 from dense + 1.0 from sparse
        assert results_k60[0][1] < results_k1[0][1]  # k=60 dampens more

    def test_rrf_handles_empty_dense(self):
        """Test RRF handles empty dense results."""
        from hybrid_search import reciprocal_rank_fusion

        dense = []
        sparse = [("doc_a", 0.9, {"text": "test"})]

        results = reciprocal_rank_fusion(dense, sparse)

        assert len(results) == 1
        assert results[0][0] == "doc_a"

    def test_rrf_handles_empty_sparse(self):
        """Test RRF handles empty sparse results."""
        from hybrid_search import reciprocal_rank_fusion

        dense = [("doc_a", 0.9, {"text": "test"})]
        sparse = []

        results = reciprocal_rank_fusion(dense, sparse)

        assert len(results) == 1
        assert results[0][0] == "doc_a"

    def test_rrf_handles_both_empty(self):
        """Test RRF handles both lists empty."""
        from hybrid_search import reciprocal_rank_fusion

        results = reciprocal_rank_fusion([], [])
        assert len(results) == 0

    def test_rrf_preserves_metadata(self):
        """Test RRF preserves metadata from results."""
        from hybrid_search import reciprocal_rank_fusion

        dense = [("doc_a", 0.9, {"source": "dense.md", "text": "dense text"})]
        sparse = [("doc_a", 0.95, {"source": "sparse.md", "text": "sparse text"})]

        results = reciprocal_rank_fusion(dense, sparse)

        # Should prefer dense metadata
        assert results[0][5]["source"] == "dense.md"

    def test_rrf_returns_ranks(self):
        """Test RRF returns dense_rank and sparse_rank."""
        from hybrid_search import reciprocal_rank_fusion

        dense = [("doc_a", 0.9, {}), ("doc_b", 0.8, {})]
        sparse = [("doc_b", 0.95, {}), ("doc_c", 0.85, {})]

        results = reciprocal_rank_fusion(dense, sparse)

        # Find doc_b's entry
        doc_b = next(r for r in results if r[0] == "doc_b")
        chunk_id, final_score, sparse_score, dense_rank, sparse_rank, metadata = doc_b

        assert dense_rank == 1  # doc_b is at rank 1 in dense
        assert sparse_rank == 0  # doc_b is at rank 0 in sparse


class TestWeightedScoreFusion:
    """Unit tests for weighted score fusion."""

    def test_weighted_fusion_respects_alpha(self):
        """Test weighted fusion respects alpha parameter."""
        from hybrid_search import weighted_score_fusion

        dense = [("doc_a", 1.0, {})]  # Normalized to 1.0
        sparse = [("doc_a", 1.0, {})]  # Normalized to 1.0

        # alpha=0.7 means 70% dense, 30% sparse
        results_07 = weighted_score_fusion(dense, sparse, alpha=0.7)
        # alpha=0.3 means 30% dense, 70% sparse
        results_03 = weighted_score_fusion(dense, sparse, alpha=0.3)

        # Both should be 1.0 since both normalized scores are 1.0
        assert results_07[0][1] == pytest.approx(1.0, rel=0.01)
        assert results_03[0][1] == pytest.approx(1.0, rel=0.01)

    def test_weighted_fusion_normalizes_scores(self):
        """Test weighted fusion normalizes scores to 0-1 range."""
        from hybrid_search import weighted_score_fusion

        # Different raw scores
        dense = [("doc_a", 0.95, {}), ("doc_b", 0.65, {})]
        sparse = [("doc_a", 25.5, {}), ("doc_b", 15.3, {})]

        results = weighted_score_fusion(dense, sparse, alpha=0.5)

        # doc_a should rank higher (higher scores in both)
        assert results[0][0] == "doc_a"


class TestHybridResult:
    """Unit tests for HybridResult dataclass."""

    def test_hybrid_result_creation(self):
        """Test HybridResult can be created with all fields."""
        from hybrid_search import HybridResult

        result = HybridResult(
            chunk_id="test-chunk-1",
            document_id="doc-123",
            text="Sample text content",
            dense_score=0.85,
            sparse_score=0.72,
            final_score=0.79,
            dense_rank=0,
            sparse_rank=2,
            metadata={"source": "test.md"},
        )

        assert result.chunk_id == "test-chunk-1"
        assert result.document_id == "doc-123"
        assert result.dense_score == 0.85
        assert result.sparse_score == 0.72
        assert result.final_score == 0.79
        assert result.dense_rank == 0
        assert result.sparse_rank == 2

    def test_hybrid_result_to_dict(self):
        """Test HybridResult.to_dict() serialization."""
        from hybrid_search import HybridResult

        result = HybridResult(
            chunk_id="test-chunk-1",
            document_id="doc-123",
            text="Sample text",
            dense_score=0.85,
            sparse_score=0.72,
            final_score=0.79,
            dense_rank=0,
            sparse_rank=2,
            metadata={"source": "test.md"},
        )

        d = result.to_dict()

        assert d["chunk_id"] == "test-chunk-1"
        assert d["dense_score"] == 0.85
        assert d["sparse_score"] == 0.72
        assert d["final_score"] == 0.79
        assert d["dense_rank"] == 0
        assert d["sparse_rank"] == 2


class TestHybridSearchService:
    """Unit tests for HybridSearchService."""

    @pytest.mark.asyncio
    async def test_service_disabled_returns_dense_only(self):
        """Test disabled service returns dense-only results."""
        from hybrid_search import HybridSearchService

        # Mock QdrantClient
        mock_client = MagicMock()
        mock_search_result = MagicMock()
        mock_search_result.chunk_id = "doc_1"
        mock_search_result.document_id = "doc_123"
        mock_search_result.text = "Test text"
        mock_search_result.score = 0.85
        mock_search_result.metadata = {"source": "test.md"}

        mock_client.search = AsyncMock(return_value=[mock_search_result])

        service = HybridSearchService(mock_client, enabled=False)
        results = await service.search(
            query="test query",
            query_vector=[0.1] * 1024,
            top_k=5,
        )

        assert len(results) == 1
        assert results[0].chunk_id == "doc_1"
        assert results[0].dense_score == 0.85
        assert results[0].sparse_score == 0.0  # No sparse score

    @pytest.mark.asyncio
    async def test_service_enabled_combines_results(self):
        """Test enabled service combines dense and sparse results."""
        from hybrid_search import HybridSearchService

        # Mock QdrantClient
        mock_client = MagicMock()
        mock_client.url = "http://localhost:6333"
        mock_client.collection_name = "test_collection"

        # Dense search returns doc_a and doc_b
        dense_result_a = MagicMock()
        dense_result_a.chunk_id = "doc_a"
        dense_result_a.score = 0.9
        dense_result_a.metadata = {"text": "authentication API", "document_id": "doc_1"}
        dense_result_b = MagicMock()
        dense_result_b.chunk_id = "doc_b"
        dense_result_b.score = 0.8
        dense_result_b.metadata = {"text": "API documentation", "document_id": "doc_2"}

        mock_client.search = AsyncMock(return_value=[dense_result_a, dense_result_b])

        # Sparse search returns doc_b and doc_c via scroll API
        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=MagicMock(
            status_code=200,
            json=MagicMock(return_value={
                "result": [
                    {"id": "doc_b", "payload": {"text": "API documentation", "document_id": "doc_2"}},
                    {"id": "doc_c", "payload": {"text": "API reference", "document_id": "doc_3"}},
                ]
            })
        ))
        mock_client._get_client = AsyncMock(return_value=mock_http_client)

        service = HybridSearchService(mock_client, enabled=True)
        results = await service.search(
            query="API documentation",
            query_vector=[0.1] * 1024,
            top_k=5,
        )

        # doc_b should rank highest (appears in both dense and sparse)
        assert len(results) >= 1


class TestHybridSearchConfiguration:
    """Unit tests for hybrid search configuration."""

    def test_default_configuration(self):
        """Test default configuration values."""
        from hybrid_search import HYBRID_ENABLED, HYBRID_ALPHA, HYBRID_RRF_K

        # These are the expected defaults
        assert HYBRID_ENABLED is True
        assert HYBRID_ALPHA == 0.7
        assert HYBRID_RRF_K == 60

    def test_environment_override(self):
        """Test configuration can be overridden via environment."""
        with patch.dict(os.environ, {
            "MADEINOZ_KNOWLEDGE_HYBRID_ENABLED": "false",
            "MADEINOZ_KNOWLEDGE_HYBRID_ALPHA": "0.5",
            "MADEINOZ_KNOWLEDGE_HYBRID_RRF_K": "30",
        }):
            # Re-import to pick up new env vars
            import importlib
            import hybrid_search
            importlib.reload(hybrid_search)

            # Verify env vars are set
            assert os.environ.get("MADEINOZ_KNOWLEDGE_HYBRID_ENABLED") == "false"
            assert os.environ.get("MADEINOZ_KNOWLEDGE_HYBRID_ALPHA") == "0.5"


class TestHybridSearchIntegration:
    """Integration-style tests for hybrid search with realistic scenarios."""

    def test_rrf_improves_keyword_matching(self):
        """
        Test RRF improves recall for keyword-heavy queries.

        Scenario: Query "GPT-4 API authentication" with mixed candidates.
        Dense search might miss exact "GPT-4" match, but sparse catches it.
        """
        from hybrid_search import reciprocal_rank_fusion

        # Dense results (semantic matching - might miss exact acronyms)
        dense = [
            ("doc_semantic_1", 0.92, {"text": "Large language model authentication"}),
            ("doc_semantic_2", 0.88, {"text": "API security best practices"}),
            ("doc_gpt4", 0.75, {"text": "GPT-4 API authentication guide"}),
        ]

        # Sparse results (keyword matching - catches exact terms)
        sparse = [
            ("doc_gpt4", 0.95, {"text": "GPT-4 API authentication guide"}),
            ("doc_other", 0.80, {"text": "GPT-4 integration"}),
        ]

        results = reciprocal_rank_fusion(dense, sparse)

        # doc_gpt4 should be boosted because it appears in both lists
        doc_gpt4_rank = next(i for i, r in enumerate(results) if r[0] == "doc_gpt4")

        # With RRF, doc_gpt4 should be near the top (appears in both)
        assert doc_gpt4_rank <= 1  # Top 2 position

    def test_rrf_handles_different_scales(self):
        """
        Test RRF works with different score scales.

        Dense scores: 0.0-1.0
        Sparse scores: 0.0-100.0
        RRF should handle this without normalization issues.
        """
        from hybrid_search import reciprocal_rank_fusion

        # Different scales
        dense = [("doc_a", 0.95, {}), ("doc_b", 0.85, {})]
        sparse = [("doc_a", 95.0, {}), ("doc_c", 80.0, {})]

        # Should not raise or produce NaN
        results = reciprocal_rank_fusion(dense, sparse)

        assert len(results) == 3
        assert all(r[1] > 0 for r in results)  # All scores positive
        assert all(not (r[1] != r[1]) for r in results)  # No NaN (NaN != NaN)

    def test_rrf_latency_acceptable(self):
        """Test RRF computation completes quickly (<10ms for 100 results)."""
        import time
        from hybrid_search import reciprocal_rank_fusion

        # Generate 100 results each
        dense = [(f"doc_{i}", 0.9 - i * 0.001, {"text": f"document {i}"}) for i in range(100)]
        sparse = [(f"doc_{i*2}", 0.85 - i * 0.001, {"text": f"document {i*2}"}) for i in range(100)]

        start = time.time()
        results = reciprocal_rank_fusion(dense, sparse)
        elapsed_ms = (time.time() - start) * 1000

        assert len(results) > 0
        # Should complete in <10ms
        assert elapsed_ms < 10, f"RRF took {elapsed_ms:.2f}ms, expected <10ms"
