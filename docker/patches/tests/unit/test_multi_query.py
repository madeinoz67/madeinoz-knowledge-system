"""
Unit Tests for Multi-Query Variants (GAP-006)
Feature 023 Enhancement: RAG Book Compliance

Tests for multi-query variant generation and retrieval.

RAG Book Reference:
"Generate 3 different ways to ask this question, combine results"
"""

import pytest
import os
import sys

# Add patches directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'patches'))


class TestQueryVariant:
    """Unit tests for QueryVariant dataclass."""

    def test_variant_creation(self):
        """Test QueryVariant creation."""
        from multi_query import QueryVariant

        variant = QueryVariant(
            original="How do I fix auth errors?",
            variant="How do I resolve authentication failures?",
            variant_type="synonym",
        )

        assert variant.original == "How do I fix auth errors?"
        assert variant.variant_type == "synonym"


class TestMultiQueryResult:
    """Unit tests for MultiQueryResult dataclass."""

    def test_result_creation(self):
        """Test MultiQueryResult creation."""
        from multi_query import MultiQueryResult

        result = MultiQueryResult(
            original_query="test query",
            variants=[],
            merged_results=[{"chunk_id": "1", "text": "result"}],
            per_variant_results={},
            total_candidates=1,
            deduplication_count=0,
        )

        assert result.original_query == "test query"
        assert len(result.merged_results) == 1


class TestQueryVariantGenerator:
    """Unit tests for query variant generation."""

    def test_synonym_replacement(self):
        """Test synonym replacement."""
        from multi_query import QueryVariantGenerator

        gen = QueryVariantGenerator()
        variant = gen._synonym_replacement("How do I fix the error?")

        assert variant is not None
        # Should have replaced "fix" or "error"
        assert variant != "how do i fix the error?"

    def test_synonym_replacement_no_match(self):
        """Test synonym replacement with no synonyms."""
        from multi_query import QueryVariantGenerator

        gen = QueryVariantGenerator()
        variant = gen._synonym_replacement("Configure the xyzzy plugh")

        # No synonyms for these words
        assert variant is None

    def test_query_expansion(self):
        """Test query expansion."""
        from multi_query import QueryVariantGenerator

        gen = QueryVariantGenerator()
        expanded = gen._expand_query("How to use the api")

        # Note: expansion looks for exact word match, "api?" would not match
        if expanded is not None:
            assert "api" not in expanded.lower() or "endpoint" in expanded.lower()

    def test_query_decomposition_and(self):
        """Test query decomposition with 'and'."""
        from multi_query import QueryVariantGenerator

        gen = QueryVariantGenerator()
        decomposed = gen._decompose_query("Authentication and authorization setup")

        assert len(decomposed) == 2
        assert "authentication" in decomposed[0].lower()
        assert "authorization" in decomposed[1].lower()

    def test_query_decomposition_vs(self):
        """Test query decomposition with 'vs'."""
        from multi_query import QueryVariantGenerator

        gen = QueryVariantGenerator()
        decomposed = gen._decompose_query("PostgreSQL vs MySQL performance")

        assert len(decomposed) == 2

    def test_query_decomposition_no_conjunction(self):
        """Test decomposition with no conjunction."""
        from multi_query import QueryVariantGenerator

        gen = QueryVariantGenerator()
        decomposed = gen._decompose_query("Simple query without conjunctions")

        assert len(decomposed) == 0

    def test_generate_variants_basic(self):
        """Test basic variant generation."""
        from multi_query import QueryVariantGenerator

        gen = QueryVariantGenerator()
        variants = gen.generate_variants("How do I fix the error?", num_variants=3)

        # Should generate at least one variant
        assert len(variants) >= 1

        for v in variants:
            assert v.original == "How do I fix the error?"
            assert v.variant != v.original
            assert v.variant_type in ["synonym", "expansion", "decomposition", "rephrase"]

    def test_generate_variants_with_limit(self):
        """Test variant generation with limit."""
        from multi_query import QueryVariantGenerator

        gen = QueryVariantGenerator()
        variants = gen.generate_variants("Authentication and authorization setup", num_variants=2)

        assert len(variants) <= 2

    def test_llm_rephrase_without_client(self):
        """Test LLM rephrasing without client."""
        from multi_query import QueryVariantGenerator

        gen = QueryVariantGenerator(llm_client=None)
        variants = gen._llm_rephrase("test query", 2)

        assert variants == []

    def test_llm_rephrase_with_mock_client(self):
        """Test LLM rephrasing with mock client."""
        from multi_query import QueryVariantGenerator

        class MockLLM:
            def generate(self, prompt):
                return "1. First variant\n2. Second variant\n3. Third variant"

        gen = QueryVariantGenerator(llm_client=MockLLM())
        variants = gen._llm_rephrase("test query", 2)

        assert len(variants) == 2


class TestMultiQueryRetriever:
    """Unit tests for multi-query retriever."""

    def test_disabled_retriever(self):
        """Test disabled retriever."""
        from multi_query import MultiQueryRetriever

        retriever = MultiQueryRetriever(None, enabled=False)
        assert retriever.should_use_multi_query("Any query") is False

    def test_short_query_skipped(self):
        """Test short queries are skipped."""
        from multi_query import MultiQueryRetriever

        retriever = MultiQueryRetriever(None, enabled=True, min_length=10)
        assert retriever.should_use_multi_query("short") is False

    def test_complex_query_triggers(self):
        """Test complex queries trigger multi-query."""
        from multi_query import MultiQueryRetriever

        retriever = MultiQueryRetriever(None, enabled=True, min_length=3)

        # Queries with complex patterns
        complex_queries = [
            "Authentication and authorization setup",
            "PostgreSQL vs MySQL comparison",
            "What is the difference between REST and GraphQL",
        ]

        for query in complex_queries:
            assert retriever.should_use_multi_query(query) is True

    def test_simple_query_may_skip(self):
        """Test simple queries may skip multi-query."""
        from multi_query import MultiQueryRetriever

        retriever = MultiQueryRetriever(None, enabled=True, min_length=10)

        # Very short, simple query
        assert retriever.should_use_multi_query("config") is False

    @pytest.mark.asyncio
    async def test_retrieve_falls_back_without_multi(self):
        """Test retrieval falls back without multi-query."""
        from multi_query import MultiQueryRetriever

        class MockClient:
            async def semantic_search(self, **kwargs):
                return [{"chunk_id": "1", "text": "result", "confidence": 0.9}]

        retriever = MultiQueryRetriever(
            MockClient(),
            enabled=True,
            min_length=100,  # High threshold
        )

        result = await retriever.retrieve("short query", top_k=5)

        assert len(result.merged_results) == 1
        assert len(result.variants) == 0  # No variants for short query

    @pytest.mark.asyncio
    async def test_retrieve_with_variants(self):
        """Test retrieval with query variants."""
        from multi_query import MultiQueryRetriever

        class MockClient:
            async def semantic_search(self, **kwargs):
                query = kwargs.get("query", "")
                # Return different results for different queries
                return [
                    {
                        "chunk_id": f"chunk_{hash(query) % 100}",
                        "text": f"Result for: {query[:20]}",
                        "confidence": 0.9,
                    }
                ]

        retriever = MultiQueryRetriever(
            MockClient(),
            enabled=True,
            min_length=3,  # Low threshold
            num_variants=2,
        )

        result = await retriever.retrieve("Authentication and authorization setup", top_k=5)

        assert len(result.variants) >= 1
        assert len(result.merged_results) >= 1

    @pytest.mark.asyncio
    async def test_merge_results_deduplicates(self):
        """Test result merging deduplicates."""
        from multi_query import MultiQueryRetriever

        retriever = MultiQueryRetriever(None)

        # Same chunk in multiple result sets
        per_variant = {
            "query1": [{"chunk_id": "A", "confidence": 0.9, "text": "text"}],
            "query2": [{"chunk_id": "A", "confidence": 0.8, "text": "text"}],
        }

        merged = retriever._merge_results(per_variant, top_k=10)

        # Should deduplicate
        chunk_ids = [r.get("chunk_id") for r in merged]
        assert len(chunk_ids) == len(set(chunk_ids))

    def test_get_stats(self):
        """Test statistics tracking."""
        from multi_query import MultiQueryRetriever

        retriever = MultiQueryRetriever(None)
        stats = retriever.get_stats()

        assert "enabled" in stats
        assert "queries_processed" in stats


class TestConvenienceFunction:
    """Unit tests for convenience function."""

    @pytest.mark.asyncio
    async def test_retrieve_with_variants_function(self):
        """Test convenience function."""
        from multi_query import retrieve_with_variants

        class MockClient:
            async def semantic_search(self, **kwargs):
                return [{"chunk_id": "1", "text": "result", "confidence": 0.9}]

        result = await retrieve_with_variants("test query", MockClient())

        assert result.original_query == "test query"


class TestEnvironmentVariables:
    """Unit tests for environment configuration."""

    def test_default_values(self):
        """Test default configuration values."""
        from multi_query import (
            MULTI_QUERY_ENABLED,
            MULTI_QUERY_MIN_LENGTH,
            MULTI_QUERY_NUM_VARIANTS,
        )

        assert isinstance(MULTI_QUERY_ENABLED, bool)
        assert isinstance(MULTI_QUERY_MIN_LENGTH, int)
        assert isinstance(MULTI_QUERY_NUM_VARIANTS, int)

    def test_custom_values(self):
        """Test custom configuration via constructor."""
        from multi_query import MultiQueryRetriever

        retriever = MultiQueryRetriever(
            None,
            enabled=False,
            min_length=20,
            num_variants=5,
        )

        assert retriever.enabled is False
        assert retriever.min_length == 20
        assert retriever.num_variants == 5


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_query(self):
        """Test empty query handling."""
        from multi_query import QueryVariantGenerator

        gen = QueryVariantGenerator()
        variants = gen.generate_variants("")

        # Should handle gracefully
        assert isinstance(variants, list)

    def test_very_long_query(self):
        """Test very long query handling."""
        from multi_query import QueryVariantGenerator

        gen = QueryVariantGenerator()
        long_query = "How do I " * 100 + "configure the system?"
        variants = gen.generate_variants(long_query)

        assert isinstance(variants, list)

    def test_special_characters(self):
        """Test special characters in query."""
        from multi_query import QueryVariantGenerator

        gen = QueryVariantGenerator()
        variants = gen.generate_variants("How to fix @#$%^&*() errors?")

        assert isinstance(variants, list)

    def test_unicode_query(self):
        """Test unicode in query."""
        from multi_query import QueryVariantGenerator

        gen = QueryVariantGenerator()
        variants = gen.generate_variants("如何配置认证系统?")

        assert isinstance(variants, list)

    @pytest.mark.asyncio
    async def test_client_error_handling(self):
        """Test handling of client errors during retrieval."""
        from multi_query import MultiQueryRetriever

        class BrokenClient:
            async def semantic_search(self, **kwargs):
                raise RuntimeError("Client error")

        retriever = MultiQueryRetriever(BrokenClient(), enabled=False)

        # When client fails, exception propagates (expected behavior)
        # The partial_failure test covers error handling in multi-query mode
        with pytest.raises(RuntimeError):
            await retriever.retrieve("test query", top_k=5)

    @pytest.mark.asyncio
    async def test_partial_failure(self):
        """Test handling of partial failures."""
        from multi_query import MultiQueryRetriever

        call_count = 0

        class PartialClient:
            async def semantic_search(self, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return [{"chunk_id": "1", "text": "result", "confidence": 0.9}]
                else:
                    raise RuntimeError("Subsequent call failed")

        retriever = MultiQueryRetriever(
            PartialClient(),
            enabled=True,
            min_length=3,
            num_variants=2,
        )

        result = await retriever.retrieve("Authentication and setup", top_k=5)

        # Should have results from successful call
        assert result.total_candidates >= 1


class TestRRFMerge:
    """Unit tests for RRF merge."""

    def test_rrf_merge_basic(self):
        """Test basic RRF merge."""
        from multi_query import MultiQueryRetriever

        retriever = MultiQueryRetriever(None)

        list1 = [("A", 0.9, {"text": "a"}), ("B", 0.8, {"text": "b"}), ("C", 0.7, {"text": "c"})]
        list2 = [("B", 0.9, {"text": "b"}), ("A", 0.8, {"text": "a"}), ("D", 0.7, {"text": "d"})]

        merged = retriever._rrf_merge(list1, list2)

        # A and B appear in both, should rank higher
        assert len(merged) == 4

    def test_rrf_merge_empty(self):
        """Test RRF merge with empty list."""
        from multi_query import MultiQueryRetriever

        retriever = MultiQueryRetriever(None)

        list1 = [("A", 0.9, {"text": "a"})]
        list2 = []

        merged = retriever._rrf_merge(list1, list2)

        assert len(merged) == 1
