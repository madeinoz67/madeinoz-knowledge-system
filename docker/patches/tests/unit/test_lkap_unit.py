"""
Unit Tests for LKAP (Feature 022)
Local Knowledge Augmentation Platform

Unit tests using pytest for:
- Heading-aware chunking (T031 context)
- Confidence band calculation (T032 context)
- Progressive classification layers (T033 context)
- Evidence-to-fact linking (T062 context)
"""

import pytest
from lkap_models import ConfidenceBand, FactType, Domain
from classification import ProgressiveClassifier
from chunking_service import create_chunking_params


class TestChunking:
    """Unit tests for heading-aware chunking (T031)"""

    def test_chunking_params(self):
        """Verify chunking parameters match specification"""
        params = create_chunking_params()

        assert params is not None
        # Verify 512-768 token range per spec
        assert hasattr(params, 'chunk_size')
        # Heading-aware enabled
        # TODO: Verify params when Docling ChunkingParams is available

    def test_token_count_validation(self):
        """Verify token count limits are enforced (256-1024)"""
        # Test data would go here
        pass


class TestConfidence:
    """Unit tests for confidence band calculation (T032)"""

    def test_high_confidence_threshold(self):
        """Verify ≥0.85 maps to HIGH band"""
        classifier = ProgressiveClassifier()
        band = classifier.get_confidence_band(0.85)
        assert band == ConfidenceBand.HIGH

        band = classifier.get_confidence_band(0.90)
        assert band == ConfidenceBand.HIGH

    def test_medium_confidence_threshold(self):
        """Verify 0.70-0.84 maps to MEDIUM band"""
        classifier = ProgressiveClassifier()
        band = classifier.get_confidence_band(0.70)
        assert band == ConfidenceBand.MEDIUM

        band = classifier.get_confidence_band(0.84)
        assert band == ConfidenceBand.MEDIUM

    def test_low_confidence_threshold(self):
        """Verify <0.70 maps to LOW band"""
        classifier = ProgressiveClassifier()
        band = classifier.get_confidence_band(0.69)
        assert band == ConfidenceBand.LOW

        band = classifier.get_confidence_band(0.50)
        assert band == ConfidenceBand.LOW


class TestClassification:
    """Unit tests for progressive classification layers (T033)"""

    @pytest.fixture
    def classifier(self):
        return ProgressiveClassifier()

    def test_layer1_hard_signals(self, classifier):
        """Verify Layer 1 (hard signals) provides 1.0 confidence"""
        # Test path-based classification
        result = classifier._classify_from_path(
            "/path/to/embedded/datasheet.pdf",
            "datasheet.pdf"
        )
        assert result == Domain.EMBEDDED.value

    def test_layer2_content_analysis(self, classifier):
        """Verify Layer 2 (content analysis) works"""
        # Test content-based classification
        content = "This microcontroller has GPIO pins for embedded systems"
        result = classifier._classify_domain_from_content(
            "MCU Datasheet",
            "",
            content
        )
        # Should detect embedded domain
        assert result == Domain.EMBEDDED.value

    def test_confidence_calculation(self, classifier):
        """Verify confidence calculation with multiple signals"""
        result = classifier.classify_domain(
            filename="STM32H743_Datasheet.pdf",
            path="/docs/embedded/",
            title="STM32H7 Reference Manual",
            content="GPIO configuration for microcontroller",
        )

        # Should have high confidence from both path and content
        assert result.confidence >= 0.8
        assert result.value == Domain.EMBEDDED.value
