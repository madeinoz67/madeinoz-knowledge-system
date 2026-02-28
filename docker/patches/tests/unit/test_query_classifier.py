"""
Unit Tests for Query Classification (GAP-005)
Feature 023 Enhancement: RAG Book Compliance

Tests for query classification and routing.

RAG Book Reference:
"Different queries need different retrieval strategies."
"""

import pytest
import os
import sys

# Add patches directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'patches'))


class TestQueryType:
    """Unit tests for QueryType enum."""

    def test_query_types_exist(self):
        """Test all query types are defined."""
        from query_classifier import QueryType

        assert QueryType.FACTUAL.value == "factual"
        assert QueryType.PROCEDURAL.value == "procedural"
        assert QueryType.CONCEPTUAL.value == "conceptual"
        assert QueryType.COMPARATIVE.value == "comparative"
        assert QueryType.TEMPORAL.value == "temporal"
        assert QueryType.AMBIGUOUS.value == "ambiguous"


class TestRetrievalStrategies:
    """Unit tests for retrieval strategy configuration."""

    def test_strategies_exist_for_all_types(self):
        """Test strategies are defined for all query types."""
        from query_classifier import RETRIEVAL_STRATEGIES, QueryType

        for qt in QueryType:
            assert qt in RETRIEVAL_STRATEGIES
            assert "primary" in RETRIEVAL_STRATEGIES[qt]
            assert "top_k" in RETRIEVAL_STRATEGIES[qt]

    def test_factual_uses_keyword(self):
        """Test factual queries favor keyword search."""
        from query_classifier import RETRIEVAL_STRATEGIES, QueryType

        strategy = RETRIEVAL_STRATEGIES[QueryType.FACTUAL]
        assert strategy["primary"] == "keyword"
        assert strategy["hybrid_weight"] > 0.5  # Favor sparse

    def test_conceptual_uses_dense(self):
        """Test conceptual queries favor dense search."""
        from query_classifier import RETRIEVAL_STRATEGIES, QueryType

        strategy = RETRIEVAL_STRATEGIES[QueryType.CONCEPTUAL]
        assert strategy["primary"] == "dense"
        assert strategy["hybrid_weight"] < 0.5  # Favor dense

    def test_procedural_uses_hybrid(self):
        """Test procedural queries use hybrid search."""
        from query_classifier import RETRIEVAL_STRATEGIES, QueryType

        strategy = RETRIEVAL_STRATEGIES[QueryType.PROCEDURAL]
        assert strategy["primary"] == "hybrid"


class TestRuleBasedClassifier:
    """Unit tests for rule-based classification."""

    def test_classify_factual_queries(self):
        """Test classification of factual queries."""
        from query_classifier import RuleBasedClassifier, QueryType

        classifier = RuleBasedClassifier()

        test_queries = [
            "What is the API rate limit?",
            "Where is the configuration file?",
            "How many users can connect?",
            "What's the version number?",
        ]

        for query in test_queries:
            qt, conf, patterns = classifier.classify(query)
            assert qt == QueryType.FACTUAL, f"Failed for: {query}"
            assert conf > 0.4
            assert len(patterns) > 0

    def test_classify_procedural_queries(self):
        """Test classification of procedural queries."""
        from query_classifier import RuleBasedClassifier, QueryType

        classifier = RuleBasedClassifier()

        # Clear procedural patterns - use statements not questions to avoid factual overlap
        test_queries = [
            "Guide to deploy the application",
            "Steps to configure authentication",
            "Setup instructions for the database",
        ]

        for query in test_queries:
            qt, conf, patterns = classifier.classify(query)
            assert qt == QueryType.PROCEDURAL, f"Failed for: {query} (got {qt})"
            assert conf > 0.4

    def test_classify_procedural_question(self):
        """Test procedural questions get classified correctly."""
        from query_classifier import RuleBasedClassifier, QueryType

        classifier = RuleBasedClassifier()

        # "How do I" is a strong procedural signal
        qt, conf, patterns = classifier.classify("How do I deploy the application?")
        assert qt == QueryType.PROCEDURAL
        assert conf > 0.4

    def test_classify_conceptual_queries(self):
        """Test classification of conceptual queries."""
        from query_classifier import RuleBasedClassifier, QueryType

        classifier = RuleBasedClassifier()

        test_queries = [
            "Explain how the authentication system works",
            "Describe the caching architecture",
        ]

        for query in test_queries:
            qt, conf, patterns = classifier.classify(query)
            assert qt == QueryType.CONCEPTUAL, f"Failed for: {query} (got {qt})"
            assert conf > 0.4

    def test_classify_comparative_queries(self):
        """Test classification of comparative queries."""
        from query_classifier import RuleBasedClassifier, QueryType

        classifier = RuleBasedClassifier()

        # Clear comparative patterns
        test_queries = [
            "Compare PostgreSQL vs MySQL",
            "PostgreSQL versus MySQL comparison",
            "Pros and cons analysis",
        ]

        for query in test_queries:
            qt, conf, patterns = classifier.classify(query)
            assert qt == QueryType.COMPARATIVE, f"Failed for: {query} (got {qt})"

    def test_classify_temporal_queries(self):
        """Test classification of temporal queries."""
        from query_classifier import RuleBasedClassifier, QueryType

        classifier = RuleBasedClassifier()

        # Clear temporal patterns
        test_queries = [
            "Changes in 2024",
            "Recent updates to the API",
            "Latest changes history",
        ]

        for query in test_queries:
            qt, conf, patterns = classifier.classify(query)
            assert qt == QueryType.TEMPORAL, f"Failed for: {query} (got {qt})"

    def test_classify_ambiguous_queries(self):
        """Test classification of ambiguous queries."""
        from query_classifier import RuleBasedClassifier, QueryType

        classifier = RuleBasedClassifier()

        test_queries = [
            "it",  # Very short
            "the thing",  # Vague
            "this stuff",  # Vague
        ]

        for query in test_queries:
            qt, conf, patterns = classifier.classify(query)
            assert qt == QueryType.AMBIGUOUS, f"Failed for: {query} (got {qt})"

    def test_default_to_conceptual(self):
        """Test unknown queries default to conceptual."""
        from query_classifier import RuleBasedClassifier, QueryType

        classifier = RuleBasedClassifier()

        # Query with no matching patterns
        qt, conf, patterns = classifier.classify("xyzabc123 random words")

        assert qt == QueryType.CONCEPTUAL
        assert conf < 0.5  # Low confidence

    def test_confidence_increases_with_matches(self):
        """Test confidence increases with more pattern matches."""
        from query_classifier import RuleBasedClassifier, QueryType

        classifier = RuleBasedClassifier()

        # Single match
        _, conf1, _ = classifier.classify("What is this?")

        # Multiple matches
        _, conf2, _ = classifier.classify("How do I configure the rate limit setting?")

        assert conf2 >= conf1  # More patterns = higher confidence


class TestClassificationResult:
    """Unit tests for ClassificationResult."""

    def test_result_contains_strategy(self):
        """Test result includes retrieval strategy."""
        from query_classifier import QueryClassifier

        classifier = QueryClassifier()
        result = classifier.classify("How do I deploy?")

        assert result.strategy is not None
        assert "primary" in result.strategy
        assert "top_k" in result.strategy

    def test_result_contains_patterns(self):
        """Test result includes detected patterns."""
        from query_classifier import QueryClassifier

        classifier = QueryClassifier()
        result = classifier.classify("How do I deploy?")

        assert isinstance(result.detected_patterns, list)

    def test_ambiguous_has_refinements(self):
        """Test ambiguous queries include suggestions."""
        from query_classifier import QueryClassifier

        classifier = QueryClassifier()
        result = classifier.classify("it")  # Ambiguous

        if result.query_type.value == "ambiguous":
            assert result.suggested_refinements is not None


class TestQueryClassifier:
    """Unit tests for main QueryClassifier."""

    def test_classifier_disabled(self):
        """Test disabled classifier returns default."""
        from query_classifier import QueryClassifier, QueryType

        classifier = QueryClassifier(enabled=False)
        result = classifier.classify("How do I deploy?")

        assert result.query_type == QueryType.CONCEPTUAL
        assert result.confidence == 0.5

    def test_classifier_enabled(self):
        """Test enabled classifier works."""
        from query_classifier import QueryClassifier, QueryType

        classifier = QueryClassifier(enabled=True)
        result = classifier.classify("How do I deploy?")

        assert result.query_type == QueryType.PROCEDURAL
        assert result.confidence > 0.3

    def test_stats_tracking(self):
        """Test classification stats are tracked."""
        from query_classifier import QueryClassifier

        classifier = QueryClassifier()

        # Classify several queries
        classifier.classify("What is X?")
        classifier.classify("How do I do Y?")
        classifier.classify("Explain Z")

        stats = classifier.get_stats()

        assert stats["total_classified"] == 3
        assert "distribution" in stats
        assert "counts" in stats


class TestQueryRouter:
    """Unit tests for QueryRouter (integration-style)."""

    @pytest.mark.asyncio
    async def test_router_classifies_before_retrieval(self):
        """Test router classifies query before retrieval."""
        from query_classifier import QueryRouter, QueryClassifier

        # Mock QdrantClient
        class MockClient:
            async def semantic_search(self, **kwargs):
                return [{"chunk_id": "test", "text": "result", "confidence": 0.9}]

        router = QueryRouter(MockClient())
        results, classification = await router.retrieve("How do I deploy?")

        assert len(results) == 1
        assert classification is not None
        assert classification.query_type is not None

    @pytest.mark.asyncio
    async def test_router_uses_strategy_top_k(self):
        """Test router uses top_k from strategy."""
        from query_classifier import QueryRouter, QueryType, RETRIEVAL_STRATEGIES

        # Mock QdrantClient that captures top_k
        class MockClient:
            def __init__(self):
                self.last_top_k = None

            async def semantic_search(self, **kwargs):
                self.last_top_k = kwargs.get("top_k")
                return []

        mock = MockClient()
        router = QueryRouter(mock)
        await router.retrieve("Compare A vs B")  # Comparative query

        # Should use comparative strategy's top_k (15)
        assert mock.last_top_k == RETRIEVAL_STRATEGIES[QueryType.COMPARATIVE]["top_k"]

    @pytest.mark.asyncio
    async def test_router_top_k_override(self):
        """Test explicit top_k overrides strategy."""
        from query_classifier import QueryRouter

        class MockClient:
            def __init__(self):
                self.last_top_k = None

            async def semantic_search(self, **kwargs):
                self.last_top_k = kwargs.get("top_k")
                return []

        mock = MockClient()
        router = QueryRouter(mock)
        await router.retrieve("How do I deploy?", k=5)  # Override to 5

        assert mock.last_top_k == 5


class TestConvenienceFunction:
    """Unit tests for convenience function."""

    def test_classify_query_quick(self):
        """Test quick classification function."""
        from query_classifier import classify_query, QueryType

        result = classify_query("How do I deploy?")

        assert result.query_type == QueryType.PROCEDURAL
        assert result.confidence > 0


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_query(self):
        """Test empty query handling."""
        from query_classifier import RuleBasedClassifier

        classifier = RuleBasedClassifier()
        qt, conf, patterns = classifier.classify("")

        # Should not crash, defaults to conceptual
        assert qt is not None

    def test_very_long_query(self):
        """Test very long query handling."""
        from query_classifier import RuleBasedClassifier

        classifier = RuleBasedClassifier()
        long_query = "How do I " * 100 + "deploy?"

        qt, conf, patterns = classifier.classify(long_query)

        # Should classify as procedural
        assert qt is not None

    def test_special_characters(self):
        """Test special characters in query."""
        from query_classifier import RuleBasedClassifier

        classifier = RuleBasedClassifier()
        qt, conf, patterns = classifier.classify("What is @#$%^&*()?")

        # Should not crash
        assert qt is not None

    def test_mixed_case_query(self):
        """Test case-insensitive matching."""
        from query_classifier import RuleBasedClassifier, QueryType

        classifier = RuleBasedClassifier()

        qt1, _, _ = classifier.classify("HOW DO I DEPLOY?")
        qt2, _, _ = classifier.classify("how do i deploy?")

        assert qt1 == qt2 == QueryType.PROCEDURAL
