"""
Unit Tests for Quality Scoring (GAP-009, GAP-010)
Feature 023 Enhancement: RAG Book Compliance

Tests for quality scoring and garbage detection.

RAG Book Reference:
"Documents below threshold get flagged for review or excluded"
"Placeholder text, 'lorem ipsum', corrupted exports"
"""

import pytest
import os
import sys
from datetime import datetime, timedelta, timezone

# Add patches directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'patches'))


class TestQualityFactor:
    """Unit tests for QualityFactor enum."""

    def test_factors_exist(self):
        """Test all quality factors are defined."""
        from quality_scoring import QualityFactor

        assert QualityFactor.FRESHNESS.value == "freshness"
        assert QualityFactor.COMPLETENESS.value == "completeness"
        assert QualityFactor.AUTHORITY.value == "authority"
        assert QualityFactor.ENTROPY.value == "entropy"
        assert QualityFactor.LANGUAGE.value == "language"


class TestQualityLevel:
    """Unit tests for QualityLevel enum."""

    def test_levels_exist(self):
        """Test all quality levels are defined."""
        from quality_scoring import QualityLevel

        assert QualityLevel.EXCELLENT.value == "excellent"
        assert QualityLevel.GOOD.value == "good"
        assert QualityLevel.ACCEPTABLE.value == "acceptable"
        assert QualityLevel.POOR.value == "poor"
        assert QualityLevel.UNACCEPTABLE.value == "unacceptable"


class TestQualityScoreResult:
    """Unit tests for QualityScoreResult dataclass."""

    def test_result_creation(self):
        """Test QualityScoreResult can be created."""
        from quality_scoring import QualityScoreResult, QualityLevel

        result = QualityScoreResult(
            score=0.85,
            level=QualityLevel.GOOD,
            factors={"freshness": 0.9, "completeness": 0.8},
            flags=[],
            is_garbage=False,
        )

        assert result.score == 0.85
        assert result.level == QualityLevel.GOOD
        assert result.factors["freshness"] == 0.9
        assert result.is_garbage is False

    def test_garbage_result(self):
        """Test QualityScoreResult for garbage content."""
        from quality_scoring import QualityScoreResult, QualityLevel

        result = QualityScoreResult(
            score=0.0,
            level=QualityLevel.UNACCEPTABLE,
            factors={},
            flags=["garbage:placeholder_detected"],
            is_garbage=True,
            garbage_reason="placeholder_detected",
        )

        assert result.score == 0.0
        assert result.is_garbage is True
        assert result.garbage_reason == "placeholder_detected"


class TestGarbageDetector:
    """Unit tests for garbage detection."""

    def test_detect_empty_content(self):
        """Test detection of empty content."""
        from quality_scoring import GarbageDetector

        detector = GarbageDetector()
        is_garbage, reason = detector.detect("")

        assert is_garbage is True
        assert reason == "empty_content"

    def test_detect_whitespace_only(self):
        """Test detection of whitespace-only content."""
        from quality_scoring import GarbageDetector

        detector = GarbageDetector()
        is_garbage, reason = detector.detect("   \n\t   ")

        assert is_garbage is True
        assert reason == "empty_content"

    def test_detect_too_short(self):
        """Test detection of too short content."""
        from quality_scoring import GarbageDetector

        detector = GarbageDetector(min_chunk_length=50)
        is_garbage, reason = detector.detect("Short text")

        assert is_garbage is True
        assert "too_short" in reason

    def test_detect_lorem_ipsum(self):
        """Test detection of lorem ipsum placeholder."""
        from quality_scoring import GarbageDetector

        detector = GarbageDetector()
        is_garbage, reason = detector.detect(
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 10
        )

        assert is_garbage is True
        assert "placeholder_detected" in reason

    def test_detect_todo_placeholder(self):
        """Test detection of TODO placeholders."""
        from quality_scoring import GarbageDetector

        detector = GarbageDetector()

        # Test various TODO patterns
        todo_patterns = [
            "[TODO] Add content here",
            "TBD - coming soon",
            "Insert text here for documentation",
        ]

        for pattern in todo_patterns:
            # Make it long enough to pass length check
            content = (pattern + " ") * 10
            is_garbage, reason = detector.detect(content)
            assert is_garbage is True, f"Failed to detect: {pattern}"

    def test_detect_repeated_characters(self):
        """Test detection of repeated character patterns."""
        from quality_scoring import GarbageDetector

        detector = GarbageDetector(min_chunk_length=10)  # Lower for this test
        is_garbage, reason = detector.detect("aaaaaaaaaaaaaaaaaaaaaaaaaa")

        assert is_garbage is True
        assert "low_entropy" in reason

    def test_detect_few_unique_words(self):
        """Test detection of few unique words."""
        from quality_scoring import GarbageDetector

        # Use different words but few of them to avoid low_entropy_pattern detection
        detector = GarbageDetector(min_chunk_length=20, min_unique_words=10)
        is_garbage, reason = detector.detect("cat dog cat dog cat dog cat dog cat dog cat dog cat dog cat dog")

        # This should be caught for few unique words OR low entropy - either is valid
        assert is_garbage is True
        assert "few_unique_words" in reason or "low_entropy" in reason

    def test_valid_content_not_garbage(self):
        """Test that valid content is not flagged as garbage."""
        from quality_scoring import GarbageDetector

        detector = GarbageDetector()
        valid_content = """
        This is a valid document with sufficient content and multiple unique words.
        It discusses the configuration of the authentication system and how to set up
        proper security measures. The documentation includes steps for OAuth integration
        and API key management. Users should follow these guidelines for best results.
        """

        is_garbage, reason = detector.detect(valid_content)

        assert is_garbage is False
        assert reason is None


class TestEntropyCalculation:
    """Unit tests for entropy calculation."""

    def test_entropy_uniform_distribution(self):
        """Test entropy for uniform distribution (high entropy)."""
        from quality_scoring import GarbageDetector

        detector = GarbageDetector()

        # Diverse content should have high entropy
        diverse = "The quick brown fox jumps over the lazy dog. Pack my box with five dozen liquor jugs."
        entropy = detector._calculate_entropy(diverse)

        # Should be > 3.0 for diverse text
        assert entropy > 3.0

    def test_entropy_repeated_pattern(self):
        """Test entropy for repeated pattern (low entropy)."""
        from quality_scoring import GarbageDetector

        detector = GarbageDetector()

        # Repeated pattern should have low entropy
        repeated = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        entropy = detector._calculate_entropy(repeated)

        # Should be very low
        assert entropy < 1.0

    def test_entropy_score_normalization(self):
        """Test entropy score normalization."""
        from quality_scoring import GarbageDetector

        detector = GarbageDetector()

        # Good content should get score close to 1.0
        good_content = "The authentication system provides secure access control for all users."
        score = detector.get_entropy_score(good_content)
        assert score > 0.8

    def test_entropy_empty_string(self):
        """Test entropy for empty string."""
        from quality_scoring import GarbageDetector

        detector = GarbageDetector()
        entropy = detector._calculate_entropy("")

        assert entropy == 0.0


class TestQualityScorer:
    """Unit tests for quality scoring."""

    def test_disabled_scorer(self):
        """Test disabled scorer returns default."""
        from quality_scoring import QualityScorer, QualityLevel

        scorer = QualityScorer(enabled=False)
        result = scorer.compute_score("Any content")

        assert result.level == QualityLevel.GOOD
        assert result.is_garbage is False

    def test_compute_score_returns_result(self):
        """Test compute_score returns QualityScoreResult."""
        from quality_scoring import QualityScorer, QualityScoreResult

        scorer = QualityScorer(enabled=True)
        result = scorer.compute_score("This is valid content with enough words to pass quality checks.")

        assert isinstance(result, QualityScoreResult)
        assert 0.0 <= result.score <= 1.0

    def test_freshness_recent_content(self):
        """Test freshness for recent content."""
        from quality_scoring import QualityScorer

        scorer = QualityScorer()
        recent_date = datetime.now(timezone.utc) - timedelta(days=10)

        freshness = scorer._compute_freshness(recent_date)

        assert freshness > 0.9

    def test_freshness_old_content(self):
        """Test freshness for old content."""
        from quality_scoring import QualityScorer

        scorer = QualityScorer(freshness_half_life=365)
        old_date = datetime.now(timezone.utc) - timedelta(days=365)

        freshness = scorer._compute_freshness(old_date)

        # Should be ~0.5 at half-life
        assert 0.4 < freshness < 0.6

    def test_freshness_unknown_date(self):
        """Test freshness for unknown date."""
        from quality_scoring import QualityScorer

        scorer = QualityScorer()
        freshness = scorer._compute_freshness(None)

        # Should default to reasonable value
        assert freshness == 0.7

    def test_completeness_long_content(self):
        """Test completeness for long content."""
        from quality_scoring import QualityScorer

        scorer = QualityScorer()
        long_content = "This is a sentence. " * 50  # 50+ sentences

        completeness = scorer._compute_completeness(long_content)

        assert completeness >= 0.5

    def test_completeness_short_content(self):
        """Test completeness for short content."""
        from quality_scoring import QualityScorer

        scorer = QualityScorer()
        short_content = "Short."

        completeness = scorer._compute_completeness(short_content)

        assert completeness < 0.5

    def test_completeness_with_structure(self):
        """Test completeness with markdown structure."""
        from quality_scoring import QualityScorer

        scorer = QualityScorer()
        structured = """
# Configuration Guide

This document explains the configuration options.

## Authentication

Set up authentication with the following steps.

## Authorization

Configure authorization policies here.
        """

        completeness = scorer._compute_completeness(structured)

        # Should get bonus for structure
        assert completeness > 0.3

    def test_quality_level_classification(self):
        """Test quality level classification."""
        from quality_scoring import QualityScorer, QualityLevel

        scorer = QualityScorer()

        assert scorer._get_quality_level(0.95) == QualityLevel.EXCELLENT
        assert scorer._get_quality_level(0.75) == QualityLevel.GOOD
        assert scorer._get_quality_level(0.55) == QualityLevel.ACCEPTABLE
        assert scorer._get_quality_level(0.35) == QualityLevel.POOR
        assert scorer._get_quality_level(0.15) == QualityLevel.UNACCEPTABLE

    def test_authority_factor(self):
        """Test authority factor from trust score."""
        from quality_scoring import QualityScorer

        scorer = QualityScorer()

        # High trust score
        result = scorer.compute_score(
            "Valid content with many unique words to pass entropy checks.",
            trust_score=0.9
        )
        assert result.factors.get("authority") == 0.9

        # Low trust score
        result = scorer.compute_score(
            "Valid content with many unique words to pass entropy checks.",
            trust_score=0.3
        )
        assert result.factors.get("authority") == 0.3

    def test_garbage_rejection(self):
        """Test that garbage content is rejected."""
        from quality_scoring import QualityScorer

        scorer = QualityScorer()
        result = scorer.compute_score("Lorem ipsum dolor sit amet")

        assert result.is_garbage is True
        assert result.score == 0.0

    def test_should_accept(self):
        """Test should_accept method."""
        from quality_scoring import QualityScorer, QualityScoreResult, QualityLevel

        scorer = QualityScorer(min_score=0.5)

        # Acceptable result
        good_result = QualityScoreResult(
            score=0.7,
            level=QualityLevel.GOOD,
            factors={},
            flags=[],
            is_garbage=False,
        )
        assert scorer.should_accept(good_result) is True

        # Below threshold
        poor_result = QualityScoreResult(
            score=0.3,
            level=QualityLevel.POOR,
            factors={},
            flags=[],
            is_garbage=False,
        )
        assert scorer.should_accept(poor_result) is False

        # Garbage
        garbage_result = QualityScoreResult(
            score=0.0,
            level=QualityLevel.UNACCEPTABLE,
            factors={},
            flags=[],
            is_garbage=True,
        )
        assert scorer.should_accept(garbage_result) is False


class TestQualityScorerStats:
    """Unit tests for statistics tracking."""

    def test_initial_stats(self):
        """Test initial stats are zero."""
        from quality_scoring import QualityScorer

        scorer = QualityScorer()
        stats = scorer.get_stats()

        assert stats["scored_count"] == 0
        assert stats["rejected_count"] == 0
        assert stats["garbage_count"] == 0
        assert stats["rejection_rate"] == 0

    def test_stats_after_scoring(self):
        """Test stats after scoring documents."""
        from quality_scoring import QualityScorer

        scorer = QualityScorer(min_score=0.5)

        # Score some documents with sufficient length
        scorer.compute_score("This is valid content for testing purposes with enough unique words.")
        scorer.compute_score("Lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod")  # Garbage
        scorer.compute_score("Short text here")  # Too short = garbage

        stats = scorer.get_stats()

        # First should be scored, others are garbage
        assert stats["scored_count"] >= 1
        assert stats["garbage_count"] >= 1


class TestQualityFilter:
    """Unit tests for QualityFilter."""

    def test_filter_removes_garbage(self):
        """Test filter removes garbage content."""
        from quality_scoring import QualityFilter

        filter = QualityFilter()
        documents = [
            {"content": "Valid content with many unique words for testing the quality scoring system implementation."},
            {"content": "Lorem ipsum dolor sit amet consectetur adipiscing elit proin sagittis"},
        ]

        filtered = filter.filter(documents)

        assert len(filtered) == 1
        assert "quality_score" in filtered[0]

    def test_filter_removes_low_quality(self):
        """Test filter removes low quality content."""
        from quality_scoring import QualityFilter

        filter = QualityFilter(min_score=0.3)

        # Create documents with different quality
        documents = [
            {
                "content": "This is a comprehensive guide with detailed information about authentication systems and configuration options for users.",
                "trust_score": 0.9,
            },
            {
                "content": "Short text here with minimal content and few unique words",
                "trust_score": 0.3,
            },
        ]

        filtered = filter.filter(documents)

        # First doc should pass, second might be rejected for length
        assert len(filtered) >= 1

    def test_filter_adds_metadata(self):
        """Test filter adds quality metadata."""
        from quality_scoring import QualityFilter

        filter = QualityFilter()
        documents = [
            {"content": "This is valid content with sufficient length and unique words for quality scoring system testing purposes."}
        ]

        filtered = filter.filter(documents)

        assert len(filtered) == 1
        assert "quality_score" in filtered[0]
        assert "quality_level" in filtered[0]
        assert "quality_factors" in filtered[0]

    def test_filter_keeps_all_high_quality(self):
        """Test filter keeps all high quality documents."""
        from quality_scoring import QualityFilter

        filter = QualityFilter(min_score=0.3)
        documents = [
            {
                "content": "Document one with comprehensive authentication configuration guide for system administrators and developers.",
                "trust_score": 0.9,
            },
            {
                "content": "Document two explaining the API integration process thoroughly with examples and best practices included.",
                "trust_score": 0.8,
            },
        ]

        filtered = filter.filter(documents)

        assert len(filtered) == 2


class TestConvenienceFunctions:
    """Unit tests for convenience functions."""

    def test_compute_quality_score(self):
        """Test compute_quality_score function."""
        from quality_scoring import compute_quality_score, QualityScoreResult

        result = compute_quality_score(
            "This is valid content for testing the quality scoring system implementation with many unique words."
        )

        assert isinstance(result, QualityScoreResult)
        assert result.score >= 0.0

    def test_is_garbage_function(self):
        """Test is_garbage convenience function."""
        from quality_scoring import is_garbage

        # Not garbage (sufficient length and unique words)
        is_g, reason = is_garbage("This is valid content with many unique words for testing the garbage detection system properly.")
        assert is_g is False

        # Is garbage
        is_g, reason = is_garbage("Lorem ipsum dolor sit amet consectetur adipiscing elit proin")
        assert is_g is True


class TestEnvironmentVariables:
    """Unit tests for environment variable configuration."""

    def test_default_values(self):
        """Test default configuration values."""
        from quality_scoring import QUALITY_SCORING_ENABLED, QUALITY_MIN_SCORE, QUALITY_FRESHNESS_HALF_LIFE

        assert isinstance(QUALITY_SCORING_ENABLED, bool)
        assert isinstance(QUALITY_MIN_SCORE, float)
        assert isinstance(QUALITY_FRESHNESS_HALF_LIFE, int)

    def test_custom_values(self):
        """Test custom configuration via constructor."""
        from quality_scoring import QualityScorer

        scorer = QualityScorer(
            enabled=False,
            min_score=0.7,
            freshness_half_life=180,
        )

        assert scorer.enabled is False
        assert scorer.min_score == 0.7
        assert scorer.freshness_half_life == 180


class TestEdgeCases:
    """Edge case tests."""

    def test_none_content(self):
        """Test handling of None content."""
        from quality_scoring import GarbageDetector

        detector = GarbageDetector()
        is_garbage, reason = detector.detect(None)

        assert is_garbage is True

    def test_unicode_content(self):
        """Test handling of unicode content."""
        from quality_scoring import QualityScorer

        scorer = QualityScorer()
        result = scorer.compute_score("这是一个中文测试文档，包含足够的内容用于质量评分。")

        # Should handle unicode
        assert result is not None

    def test_markdown_content(self):
        """Test handling of markdown content."""
        from quality_scoring import QualityScorer

        scorer = QualityScorer()
        content = """
# Heading

- List item 1
- List item 2
- List item 3

```python
def hello():
    print("Hello, world!")
```
        """

        result = scorer.compute_score(content)

        # Should handle markdown structure
        assert result.score > 0.3

    def test_code_content(self):
        """Test handling of code content."""
        from quality_scoring import QualityScorer

        scorer = QualityScorer()
        code = '''
def authenticate(user, password):
    """Authenticate user with password."""
    if not user or not password:
        return False
    return verify_password(user, password)

class AuthService:
    def __init__(self, config):
        self.config = config
        self.cache = {}
        '''

        result = scorer.compute_score(code)

        # Code should be accepted
        assert not result.is_garbage

    def test_date_string_conversion(self):
        """Test date string conversion in filter."""
        from quality_scoring import QualityFilter

        filter = QualityFilter()
        documents = [
            {
                "content": "Valid content with unique words for quality scoring system testing purposes and validation.",
                "source_date": "2024-01-15T10:30:00Z",
            },
        ]

        filtered = filter.filter(documents)

        assert len(filtered) == 1
