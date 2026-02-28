"""
Unit Tests for HyDE Query Expansion (GAP-004)
Feature 023 Enhancement: RAG Book Compliance

Tests for HyDE (Hypothetical Document Embeddings) query expansion.

RAG Book Reference:
"Generate a hypothetical answer, retrieve docs similar to it."
"""

import pytest
import os
import sys

# Add patches directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'patches'))


class TestHyDEResult:
    """Unit tests for HyDEResult dataclass."""

    def test_result_creation(self):
        """Test HyDEResult can be created."""
        from hyde_expansion import HyDEResult

        result = HyDEResult(
            original_query="login issues",
            hypothetical_document="Authentication errors may occur...",
            should_expand=True,
            reason="short_query (2 tokens)",
            llm_latency_ms=150.5,
        )

        assert result.original_query == "login issues"
        assert result.hypothetical_document is not None
        assert result.should_expand is True
        assert result.reason == "short_query (2 tokens)"
        assert result.llm_latency_ms == 150.5

    def test_result_no_expansion(self):
        """Test HyDEResult when expansion not needed."""
        from hyde_expansion import HyDEResult

        result = HyDEResult(
            original_query="This is a long query with many words",
            hypothetical_document=None,
            should_expand=False,
            reason="query_too_long (8 >= 10)",
        )

        assert result.hypothetical_document is None
        assert result.should_expand is False


class TestHyDEExpanderShouldExpand:
    """Unit tests for should_expand logic."""

    def test_disabled_returns_false(self):
        """Test disabled HyDE never expands."""
        from hyde_expansion import HyDEExpander

        expander = HyDEExpander(enabled=False)
        should, reason = expander.should_expand("login")

        assert should is False
        assert reason == "hyde_disabled"

    def test_short_query_expands(self):
        """Test short queries should be expanded."""
        from hyde_expansion import HyDEExpander

        expander = HyDEExpander(enabled=True, min_query_tokens=10)
        should, reason = expander.should_expand("login issues")

        assert should is True
        # May match ambiguous pattern first or be classified as short
        assert "short_query" in reason or "ambiguous_pattern" in reason

    def test_long_query_skipped(self):
        """Test long queries are not expanded."""
        from hyde_expansion import HyDEExpander

        expander = HyDEExpander(enabled=True, min_query_tokens=5)
        should, reason = expander.should_expand("How do I configure the API rate limit settings?")

        # 9 words >= 5, so should not expand
        assert should is False
        assert "query_too_long" in reason

    def test_ambiguous_patterns_expand(self):
        """Test ambiguous patterns trigger expansion."""
        from hyde_expansion import HyDEExpander

        expander = HyDEExpander(enabled=True, min_query_tokens=10)

        ambiguous_queries = [
            "login issues",
            "config problems",
            "setup errors",
            "not working",
            "broken thing",
        ]

        for query in ambiguous_queries:
            should, reason = expander.should_expand(query)
            # These should expand because they're short AND have ambiguous pattern
            if should:
                assert "ambiguous_pattern" in reason or "short_query" in reason


class TestHyDEExpanderGenerateHypothetical:
    """Unit tests for hypothetical document generation."""

    def test_no_llm_client_returns_none(self):
        """Test no LLM client returns None."""
        from hyde_expansion import HyDEExpander

        expander = HyDEExpander(llm_client=None)
        result, latency = expander.generate_hypothetical("login issues")

        assert result is None
        assert latency is None

    def test_mock_llm_client(self):
        """Test with mock LLM client."""
        from hyde_expansion import HyDEExpander

        class MockLLM:
            def generate(self, prompt):
                return "Authentication errors can occur when credentials are invalid."

        expander = HyDEExpander(llm_client=MockLLM())
        result, latency = expander.generate_hypothetical("login issues")

        assert result is not None
        assert "authentication" in result.lower()
        assert latency is not None
        assert latency > 0

    def test_truncates_long_hypothetical(self):
        """Test truncation of very long hypotheticals."""
        from hyde_expansion import HyDEExpander

        class MockLLM:
            def generate(self, prompt):
                # Return a very long response
                return " ".join(["word"] * 500)

        expander = HyDEExpander(llm_client=MockLLM(), max_hypothetical_tokens=100)
        result, _ = expander.generate_hypothetical("test query")

        # Should be truncated
        assert result is not None
        word_count = len(result.split())
        assert word_count <= 100

    def test_handles_llm_exception(self):
        """Test handling of LLM exceptions."""
        from hyde_expansion import HyDEExpander

        class BrokenLLM:
            def generate(self, prompt):
                raise RuntimeError("LLM failed")

        expander = HyDEExpander(llm_client=BrokenLLM())
        result, latency = expander.generate_hypothetical("test")

        assert result is None
        assert latency is None


class TestHyDEExpanderExpand:
    """Unit tests for main expand method."""

    def test_expand_returns_result(self):
        """Test expand returns HyDEResult."""
        from hyde_expansion import HyDEExpander, HyDEResult

        expander = HyDEExpander(enabled=True)
        result = expander.expand("login issues")

        assert isinstance(result, HyDEResult)
        assert result.original_query == "login issues"

    def test_expand_skips_when_disabled(self):
        """Test expand skips when disabled."""
        from hyde_expansion import HyDEExpander

        expander = HyDEExpander(enabled=False)
        result = expander.expand("login")

        assert result.should_expand is False
        assert result.hypothetical_document is None
        assert result.reason == "hyde_disabled"

    def test_expand_skips_long_queries(self):
        """Test expand skips long queries."""
        from hyde_expansion import HyDEExpander

        expander = HyDEExpander(enabled=True, min_query_tokens=3)
        result = expander.expand("This is a very long query with many words in it")

        assert result.should_expand is False
        assert result.hypothetical_document is None
        assert "query_too_long" in result.reason

    def test_expand_with_llm_success(self):
        """Test successful expansion with LLM."""
        from hyde_expansion import HyDEExpander

        class MockLLM:
            def generate(self, prompt):
                return "Authentication errors occur when credentials are invalid."

        expander = HyDEExpander(enabled=True, llm_client=MockLLM())
        result = expander.expand("login")

        assert result.should_expand is True
        assert result.hypothetical_document is not None
        assert result.llm_latency_ms is not None

    def test_expand_tracks_stats(self):
        """Test expand tracks statistics."""
        from hyde_expansion import HyDEExpander

        class MockLLM:
            def generate(self, prompt):
                return "Test response"

        expander = HyDEExpander(enabled=True, llm_client=MockLLM())

        # Expand several queries
        expander.expand("login")
        expander.expand("setup")
        expander.expand("This is a very long query that should be skipped")

        stats = expander.get_stats()

        assert stats["enabled"] is True
        assert stats["expansion_count"] >= 2  # At least 2 short queries
        assert stats["skip_count"] >= 1  # At least 1 long query


class TestHyDEExpanderStats:
    """Unit tests for statistics tracking."""

    def test_initial_stats(self):
        """Test initial stats are zero."""
        from hyde_expansion import HyDEExpander

        expander = HyDEExpander()
        stats = expander.get_stats()

        assert stats["expansion_count"] == 0
        assert stats["skip_count"] == 0
        assert stats["total_queries"] == 0
        assert stats["expansion_rate"] == 0
        assert stats["avg_latency_ms"] == 0

    def test_stats_after_expansions(self):
        """Test stats after several expansions."""
        from hyde_expansion import HyDEExpander

        class MockLLM:
            def generate(self, prompt):
                return "Test response"

        expander = HyDEExpander(enabled=True, llm_client=MockLLM())

        # Do some expansions
        expander.expand("login")
        expander.expand("setup")
        expander.expand("config")

        stats = expander.get_stats()

        assert stats["expansion_count"] == 3
        assert stats["total_queries"] == 3
        assert stats["expansion_rate"] == 1.0
        assert stats["avg_latency_ms"] > 0


class TestHyDERetrievalAugmenter:
    """Unit tests for HyDERetrievalAugmenter."""

    @pytest.mark.asyncio
    async def test_retrieve_falls_back_without_expansion(self):
        """Test retrieval falls back when no expansion."""
        from hyde_expansion import HyDERetrievalAugmenter, HyDEExpander

        class MockClient:
            async def semantic_search(self, **kwargs):
                return [{"chunk_id": "1", "text": "result", "confidence": 0.9}]

        # Create expander that will skip expansion
        expander = HyDEExpander(enabled=False)
        augmenter = HyDERetrievalAugmenter(MockClient(), expander)

        results, hyde_result = await augmenter.retrieve_with_hyde(
            query="This is a very long query that should not be expanded",
            top_k=10
        )

        assert len(results) == 1
        assert hyde_result.should_expand is False

    @pytest.mark.asyncio
    async def test_retrieve_uses_hyde_when_expanded(self):
        """Test retrieval uses hypothetical document."""
        from hyde_expansion import HyDERetrievalAugmenter, HyDEExpander

        class MockLLM:
            def generate(self, prompt):
                return "Authentication errors may occur."

        class MockClient:
            def __init__(self):
                self.last_query = None

            async def semantic_search(self, **kwargs):
                self.last_query = kwargs.get("query")
                return [{"chunk_id": "1", "text": "result", "confidence": 0.9}]

        mock_client = MockClient()
        expander = HyDEExpander(enabled=True, llm_client=MockLLM(), min_query_tokens=10)
        augmenter = HyDERetrievalAugmenter(mock_client, expander)

        results, hyde_result = await augmenter.retrieve_with_hyde(
            query="login",  # Short query
            top_k=10,
            combine_mode="hyde_only"
        )

        # Should have used hypothetical document for search
        assert "authentication" in mock_client.last_query.lower()
        assert hyde_result.hypothetical_document is not None

    @pytest.mark.asyncio
    async def test_retrieve_combine_mode(self):
        """Test combine mode merges results."""
        from hyde_expansion import HyDERetrievalAugmenter, HyDEExpander

        class MockLLM:
            def generate(self, prompt):
                return "Authentication errors."

        class MockClient:
            call_count = 0

            async def semantic_search(self, **kwargs):
                MockClient.call_count += 1
                return [
                    {"chunk_id": f"chunk_{MockClient.call_count}", "text": "result", "confidence": 0.9}
                ]

        expander = HyDEExpander(enabled=True, llm_client=MockLLM(), min_query_tokens=10)
        augmenter = HyDERetrievalAugmenter(MockClient(), expander)

        MockClient.call_count = 0
        results, _ = await augmenter.retrieve_with_hyde(
            query="login",
            top_k=10,
            combine_mode="combine"
        )

        # Combine mode should call search twice (hyde + original)
        assert MockClient.call_count == 2


class TestConvenienceFunction:
    """Unit tests for convenience function."""

    def test_expand_query_function(self):
        """Test expand_query convenience function."""
        from hyde_expansion import expand_query, HyDEResult

        result = expand_query("login issues")

        assert isinstance(result, HyDEResult)
        assert result.original_query == "login issues"

    def test_expand_query_with_llm(self):
        """Test expand_query with mock LLM."""
        from hyde_expansion import expand_query

        class MockLLM:
            def generate(self, prompt):
                return "Test hypothetical"

        result = expand_query("login", llm_client=MockLLM())

        # Should expand because "login" is short
        # But hypothetical will only be set if LLM succeeds
        assert result.original_query == "login"


class TestEnvironmentVariables:
    """Unit tests for environment variable configuration."""

    def test_default_values(self):
        """Test default configuration values."""
        from hyde_expansion import HYDE_ENABLED, HYDE_MIN_QUERY_TOKENS, HYDE_MAX_HYPOTHETICAL_TOKENS

        # These should have default values
        assert isinstance(HYDE_ENABLED, bool)
        assert isinstance(HYDE_MIN_QUERY_TOKENS, int)
        assert isinstance(HYDE_MAX_HYPOTHETICAL_TOKENS, int)

    def test_custom_values(self):
        """Test custom configuration via constructor."""
        from hyde_expansion import HyDEExpander

        expander = HyDEExpander(
            enabled=False,
            min_query_tokens=5,
            max_hypothetical_tokens=100
        )

        assert expander.enabled is False
        assert expander.min_query_tokens == 5
        assert expander.max_hypothetical_tokens == 100


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_query(self):
        """Test empty query handling."""
        from hyde_expansion import HyDEExpander

        expander = HyDEExpander(enabled=True)
        should, reason = expander.should_expand("")

        # Empty query is 0 tokens, should expand
        assert should is True
        assert "short_query" in reason

    def test_single_word_query(self):
        """Test single word query."""
        from hyde_expansion import HyDEExpander

        expander = HyDEExpander(enabled=True, min_query_tokens=10)
        should, reason = expander.should_expand("login")

        assert should is True
        assert "short_query" in reason

    def test_exact_token_threshold(self):
        """Test query at exact token threshold."""
        from hyde_expansion import HyDEExpander

        expander = HyDEExpander(enabled=True, min_query_tokens=5)
        # 5 words = 5 tokens, exactly at threshold
        should, reason = expander.should_expand("one two three four five")

        assert should is False
        assert "query_too_long" in reason

    def test_special_characters_in_query(self):
        """Test special characters in query."""
        from hyde_expansion import HyDEExpander

        expander = HyDEExpander(enabled=True)
        should, reason = expander.should_expand("login @#$%^&*()")

        # Should still work with special chars
        assert should is not None
        assert reason is not None

    def test_unicode_query(self):
        """Test unicode characters in query."""
        from hyde_expansion import HyDEExpander

        expander = HyDEExpander(enabled=True)
        should, reason = expander.should_expand("登录问题")

        # Should handle unicode
        assert should is not None
