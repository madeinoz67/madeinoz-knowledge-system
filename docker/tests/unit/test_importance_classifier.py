"""
Unit Tests for Importance Classifier

Feature: 009-memory-decay-scoring
Tests: T014 - Classification logic, T015 - is_permanent() edge cases

Tests verify that:
1. classify_memory() returns importance and stability scores (1-5)
2. LLM fallback returns defaults (3, 3) when classification fails
3. is_permanent() correctly identifies permanent memories
4. Response parsing handles various LLM output formats
5. Score validation clamps values to 1-5 range
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os

# Add patches directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'patches'))


class TestIsPermanent:
    """Test is_permanent() function (T015)."""

    def test_permanent_at_threshold(self):
        """Importance=4, stability=4 should be permanent (boundary)."""
        from importance_classifier import is_permanent

        assert is_permanent(4, 4) is True

    def test_permanent_above_threshold(self):
        """Importance=5, stability=5 should be permanent (core memory)."""
        from importance_classifier import is_permanent

        assert is_permanent(5, 5) is True

    def test_not_permanent_importance_below(self):
        """Importance=3, stability=4 should NOT be permanent."""
        from importance_classifier import is_permanent

        assert is_permanent(3, 4) is False

    def test_not_permanent_stability_below(self):
        """Importance=4, stability=3 should NOT be permanent."""
        from importance_classifier import is_permanent

        assert is_permanent(4, 3) is False

    def test_not_permanent_both_below(self):
        """Importance=3, stability=3 should NOT be permanent (neutral memory)."""
        from importance_classifier import is_permanent

        assert is_permanent(3, 3) is False

    def test_not_permanent_minimum_values(self):
        """Importance=1, stability=1 should NOT be permanent (trivial memory)."""
        from importance_classifier import is_permanent

        assert is_permanent(1, 1) is False

    def test_permanent_mixed_high_values(self):
        """Importance=5, stability=4 should be permanent."""
        from importance_classifier import is_permanent

        assert is_permanent(5, 4) is True

    def test_permanent_reversed_high_values(self):
        """Importance=4, stability=5 should be permanent."""
        from importance_classifier import is_permanent

        assert is_permanent(4, 5) is True


class TestValidateScore:
    """Test validate_score() function."""

    def test_valid_score_in_range(self):
        """Score 3 should return 3."""
        from importance_classifier import validate_score

        assert validate_score(3, "importance") == 3

    def test_score_at_minimum(self):
        """Score 1 should return 1."""
        from importance_classifier import validate_score

        assert validate_score(1, "stability") == 1

    def test_score_at_maximum(self):
        """Score 5 should return 5."""
        from importance_classifier import validate_score

        assert validate_score(5, "importance") == 5

    def test_score_below_minimum_clamped(self):
        """Score 0 should be clamped to 1."""
        from importance_classifier import validate_score

        assert validate_score(0, "importance") == 1

    def test_negative_score_clamped(self):
        """Negative score should be clamped to 1."""
        from importance_classifier import validate_score

        assert validate_score(-5, "stability") == 1

    def test_score_above_maximum_clamped(self):
        """Score 6 should be clamped to 5."""
        from importance_classifier import validate_score

        assert validate_score(6, "importance") == 5

    def test_large_score_clamped(self):
        """Score 100 should be clamped to 5."""
        from importance_classifier import validate_score

        assert validate_score(100, "stability") == 5

    def test_string_integer_converted(self):
        """String '4' should convert to integer 4."""
        from importance_classifier import validate_score

        assert validate_score("4", "importance") == 4

    def test_float_truncated(self):
        """Float 3.7 should truncate to integer 3."""
        from importance_classifier import validate_score

        assert validate_score(3.7, "stability") == 3

    def test_invalid_string_returns_default(self):
        """Non-numeric string should return default."""
        from importance_classifier import validate_score

        # Default is 3 for both importance and stability
        assert validate_score("high", "importance") == 3

    def test_none_returns_default(self):
        """None should return default."""
        from importance_classifier import validate_score

        assert validate_score(None, "stability") == 3


class TestParseClassificationResponse:
    """Test parse_classification_response() function."""

    def test_clean_json_response(self):
        """Parse clean JSON response."""
        from importance_classifier import parse_classification_response

        response = '{"importance": 4, "stability": 3}'
        importance, stability = parse_classification_response(response)

        assert importance == 4
        assert stability == 3

    def test_json_with_whitespace(self):
        """Parse JSON with extra whitespace."""
        from importance_classifier import parse_classification_response

        response = '  { "importance": 2, "stability": 5 }  '
        importance, stability = parse_classification_response(response)

        assert importance == 2
        assert stability == 5

    def test_json_with_text_prefix(self):
        """Parse JSON embedded in explanatory text."""
        from importance_classifier import parse_classification_response

        response = 'Based on my analysis of this memory, I would classify it as: {"importance": 5, "stability": 4}'
        importance, stability = parse_classification_response(response)

        assert importance == 5
        assert stability == 4

    def test_markdown_code_block(self):
        """Parse JSON in markdown code block."""
        from importance_classifier import parse_classification_response

        response = '```json\n{"importance": 3, "stability": 3}\n```'
        importance, stability = parse_classification_response(response)

        assert importance == 3
        assert stability == 3

    def test_markdown_code_block_without_language(self):
        """Parse JSON in markdown code block without language hint."""
        from importance_classifier import parse_classification_response

        response = '```\n{"importance": 4, "stability": 2}\n```'
        importance, stability = parse_classification_response(response)

        assert importance == 4
        assert stability == 2

    def test_json_with_text_suffix(self):
        """Parse JSON with explanatory text after."""
        from importance_classifier import parse_classification_response

        response = '{"importance": 1, "stability": 1} This is a trivial memory.'
        importance, stability = parse_classification_response(response)

        assert importance == 1
        assert stability == 1

    def test_out_of_range_values_clamped(self):
        """Out of range values should be clamped."""
        from importance_classifier import parse_classification_response

        response = '{"importance": 10, "stability": -1}'
        importance, stability = parse_classification_response(response)

        assert importance == 5  # Clamped from 10
        assert stability == 1   # Clamped from -1

    def test_invalid_response_raises_error(self):
        """Invalid response should raise ValueError."""
        from importance_classifier import parse_classification_response

        with pytest.raises(ValueError):
            parse_classification_response("This is not JSON at all")

    def test_empty_response_raises_error(self):
        """Empty response should raise ValueError."""
        from importance_classifier import parse_classification_response

        with pytest.raises(ValueError):
            parse_classification_response("")

    def test_partial_json_raises_error(self):
        """Incomplete JSON should raise ValueError."""
        from importance_classifier import parse_classification_response

        with pytest.raises(ValueError):
            parse_classification_response('{"importance": 3')


class TestClassifyMemory:
    """Test classify_memory() async function (T014)."""

    @pytest.mark.asyncio
    async def test_no_llm_client_returns_defaults(self):
        """No LLM client should return default values (3, 3)."""
        from importance_classifier import classify_memory

        importance, stability = await classify_memory("Test content", llm_client=None)

        assert importance == 3
        assert stability == 3

    @pytest.mark.asyncio
    async def test_successful_classification(self):
        """Successful LLM response should return parsed values."""
        from importance_classifier import classify_memory

        mock_client = AsyncMock()
        mock_client.generate_response = AsyncMock(
            return_value='{"importance": 4, "stability": 5}'
        )

        importance, stability = await classify_memory("Important stable memory", llm_client=mock_client)

        assert importance == 4
        assert stability == 5

    @pytest.mark.asyncio
    async def test_llm_failure_returns_defaults(self):
        """LLM exception should return default values."""
        from importance_classifier import classify_memory

        mock_client = AsyncMock()
        mock_client.generate_response = AsyncMock(side_effect=Exception("LLM unavailable"))

        importance, stability = await classify_memory("Test content", llm_client=mock_client)

        assert importance == 3
        assert stability == 3

    @pytest.mark.asyncio
    async def test_unparseable_response_returns_defaults(self):
        """Unparseable LLM response should return defaults."""
        from importance_classifier import classify_memory

        mock_client = AsyncMock()
        mock_client.generate_response = AsyncMock(
            return_value="I cannot classify this memory"
        )

        importance, stability = await classify_memory("Test content", llm_client=mock_client)

        assert importance == 3
        assert stability == 3

    @pytest.mark.asyncio
    async def test_content_truncation(self):
        """Long content should be truncated in prompt."""
        from importance_classifier import classify_memory

        mock_client = AsyncMock()
        mock_client.generate_response = AsyncMock(
            return_value='{"importance": 3, "stability": 3}'
        )

        # Create content longer than 2000 chars
        long_content = "x" * 3000

        await classify_memory(long_content, llm_client=mock_client)

        # Verify the prompt was called (content is truncated internally)
        mock_client.generate_response.assert_called_once()
        call_args = mock_client.generate_response.call_args[0][0]

        # The content in the prompt should be truncated to 2000 chars
        # Check that the actual content in the prompt is truncated
        if isinstance(call_args, str):
            # String format: check that content portion is truncated
            # The prompt contains the content, so check that the "Memory:" section has ~2000 chars of content
            memory_section = call_args.split("Memory: ")[1].split("\n")[0]
            assert len(memory_section) <= 2000
        else:
            # Message format: call_args is a list of Message objects
            # Extract content from first message
            message_content = call_args[0].content if hasattr(call_args[0], 'content') else str(call_args[0])
            memory_section = message_content.split("Memory: ")[1].split("\n")[0]
            assert len(memory_section) <= 2000

    @pytest.mark.asyncio
    async def test_source_description_included(self):
        """Source description should be included in prompt when provided."""
        from importance_classifier import classify_memory

        mock_client = AsyncMock()
        mock_client.generate_response = AsyncMock(
            return_value='{"importance": 4, "stability": 4}'
        )

        await classify_memory(
            "Test content",
            llm_client=mock_client,
            source_description="User conversation"
        )

        call_args = mock_client.generate_response.call_args[0][0]
        assert "Source: User conversation" in call_args


class TestClassifyMemoryBatch:
    """Test classify_memory_batch() async function."""

    @pytest.mark.asyncio
    async def test_batch_classification(self):
        """Batch classification should process all items."""
        from importance_classifier import classify_memory_batch

        mock_client = AsyncMock()
        mock_client.generate_response = AsyncMock(
            return_value='{"importance": 3, "stability": 3}'
        )

        contents = ["Memory 1", "Memory 2", "Memory 3"]
        results = await classify_memory_batch(contents, llm_client=mock_client)

        assert len(results) == 3
        for importance, stability in results:
            assert importance == 3
            assert stability == 3

    @pytest.mark.asyncio
    async def test_batch_without_llm(self):
        """Batch classification without LLM returns all defaults."""
        from importance_classifier import classify_memory_batch

        contents = ["Memory 1", "Memory 2"]
        results = await classify_memory_batch(contents, llm_client=None)

        assert len(results) == 2
        for importance, stability in results:
            assert importance == 3
            assert stability == 3


class TestClassificationSource:
    """Test ClassificationSource constants and get_classification_with_source()."""

    def test_source_constants_exist(self):
        """Classification source constants should be defined."""
        from importance_classifier import ClassificationSource

        assert ClassificationSource.LLM == "llm"
        assert ClassificationSource.DEFAULT == "default"
        assert ClassificationSource.MANUAL == "manual"

    def test_get_classification_with_source_llm(self):
        """get_classification_with_source should include source tracking."""
        from importance_classifier import get_classification_with_source, ClassificationSource

        result = get_classification_with_source(
            importance=4,
            stability=5,
            source=ClassificationSource.LLM
        )

        assert result["importance"] == 4
        assert result["stability"] == 5
        assert result["classification_source"] == "llm"
        assert result["is_permanent"] is True

    def test_get_classification_with_source_default(self):
        """get_classification_with_source with default source."""
        from importance_classifier import get_classification_with_source, ClassificationSource

        result = get_classification_with_source(
            importance=3,
            stability=3,
            source=ClassificationSource.DEFAULT
        )

        assert result["importance"] == 3
        assert result["stability"] == 3
        assert result["classification_source"] == "default"
        assert result["is_permanent"] is False

    def test_get_classification_with_source_manual(self):
        """get_classification_with_source with manual source."""
        from importance_classifier import get_classification_with_source, ClassificationSource

        result = get_classification_with_source(
            importance=5,
            stability=5,
            source=ClassificationSource.MANUAL
        )

        assert result["classification_source"] == "manual"
        assert result["is_permanent"] is True


class TestClassifyUnclassifiedNodes:
    """Test classify_unclassified_nodes() for T012/T013."""

    @pytest.mark.asyncio
    async def test_no_unclassified_nodes(self):
        """Should return early when no unclassified nodes exist."""
        from importance_classifier import classify_unclassified_nodes

        # Mock driver that returns 0 unclassified
        mock_driver = MagicMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_record = {"count": 0}
        mock_result.single = AsyncMock(return_value=mock_record)
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_driver.session = MagicMock(return_value=mock_session)

        result = await classify_unclassified_nodes(mock_driver, llm_client=None)

        assert result["found"] == 0
        assert result["classified"] == 0
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_classify_nodes_without_llm(self):
        """Should use defaults when no LLM client provided."""
        from importance_classifier import classify_unclassified_nodes

        # This is a simplified test - full integration would need more complex mocking
        mock_driver = MagicMock()
        mock_session = AsyncMock()

        # First query returns count
        count_result = AsyncMock()
        count_result.single = AsyncMock(return_value={"count": 0})

        mock_session.run = AsyncMock(return_value=count_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_driver.session = MagicMock(return_value=mock_session)

        result = await classify_unclassified_nodes(mock_driver, llm_client=None)

        assert result["using_llm"] is False


class TestCountUnclassifiedNodes:
    """Test count_unclassified_nodes() function."""

    @pytest.mark.asyncio
    async def test_count_returns_integer(self):
        """count_unclassified_nodes should return count from query."""
        from importance_classifier import count_unclassified_nodes

        mock_driver = MagicMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"count": 42})
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_driver.session = MagicMock(return_value=mock_session)

        count = await count_unclassified_nodes(mock_driver)

        assert count == 42

    @pytest.mark.asyncio
    async def test_count_returns_zero_when_no_record(self):
        """count_unclassified_nodes should return 0 when no record."""
        from importance_classifier import count_unclassified_nodes

        mock_driver = MagicMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_driver.session = MagicMock(return_value=mock_session)

        count = await count_unclassified_nodes(mock_driver)

        assert count == 0


# Pytest configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
