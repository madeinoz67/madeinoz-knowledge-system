"""
Unit Tests for Progressive Classification Layers (T033 - US1)
Local Knowledge Augmentation Platform

Tests 4-layer progressive classification per Research Decision RT-003:
Layer 1: Hard signals (path, filename, vendor markers) → weight: 1.0
Layer 2: Content analysis (title, TOC, headings) → weight: 0.8
Layer 3: LLM classification → weight: 0.6-0.9
Layer 4: User confirmation → weight: 1.0 (overrides all)
"""

import pytest
from classification import ProgressiveClassifier
from lkap_models import Domain


class TestProgressiveClassificationLayers:
    """Unit tests for progressive classification layers (T033)"""

    @pytest.fixture
    def classifier(self):
        return ProgressiveClassifier()

    def test_layer1_hard_signals_path(self, classifier):
        """Verify Layer 1 (hard signals) from path provides 1.0 confidence"""
        result = classifier.classify_domain(
            filename="STM32H743_Datasheet.pdf",
            path="/docs/embedded/hardware/",
        )

        assert result.value == Domain.EMBEDDED.value
        assert "path" in result.signal_sources
        assert result.confidence >= 1.0  # Hard signals give 1.0

    def test_layer1_hard_signals_filename(self, classifier):
        """Verify Layer 1 detects vendor markers from filename"""
        # STMicroelectronics vendor marker
        result = classifier.classify_domain(
            filename="STM32_Document.pdf",
            path="/docs/",
        )

        assert result.value == Domain.EMBEDDED.value
        # TODO: Add vendor detection test when implemented

    def test_layer2_content_analysis(self, classifier):
        """Verify Layer 2 (content analysis) provides 0.8 confidence"""
        result = classifier.classify_domain(
            filename="document.pdf",
            path="/docs/",
            title="GPIO Configuration Guide",
            content="microcontroller embedded system firmware",
        )

        # Should detect embedded domain from content keywords
        # with 0.8 weight (when LLM layer is not implemented)
        assert result.value == Domain.EMBEDDED.value
        assert "content_analysis" in result.signal_sources
        assert result.confidence >= 0.8

    def test_layer3_llm_classification(self, classifier):
        """Verify Layer 3 (LLM) provides 0.42-0.63 confidence (with 0.7 multiplier)"""
        # TODO: Implement LLM classification layer
        # For now, verify fallback behavior when LLM not available
        result = classifier.classify_domain(
            filename="api_reference.md",
            path="/docs/",
            title="API Reference",
            content="Software library documentation",
        )

        # Should use best available signal (content or path)
        # LLM layer would add confidence when implemented
        assert result.value is not None

    def test_layer4_user_override(self, classifier):
        """Verify Layer 4 (user override) overrides all other layers"""
        # First, get normal classification
        normal_result = classifier.classify_domain(
            filename="document.pdf",
            path="/docs/",
        )

        # Save user override
        classifier.save_user_override(
            path="/docs/",
            field="domain",
            original_value=normal_result.value,
            new_value=Domain.SECURITY.value,
        )

        # Verify override is applied
        override_result = classifier.classify_domain(
            filename="document.pdf",
            path="/docs/",
        )

        assert override_result.value == Domain.SECURITY.value
        assert "user_override" in override_result.signal_sources
        assert override_result.confidence == 1.0  # Override gives 1.0

    def test_confidence_calculation_multiple_signals(self, classifier):
        """Verify best signal wins when multiple layers provide input"""
        # Document with both path AND content signals
        result = classifier.classify_domain(
            filename="mcu_guide.pdf",
            path="/embedded/",
            title="Microcontroller Reference",
            content="GPIO for embedded systems",
        )

        # Should have high confidence from multiple signals
        assert result.confidence >= 0.8  # At least one strong signal
        assert result.value == Domain.EMBEDDED.value
        assert len(result.signal_sources) >= 1
