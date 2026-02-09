"""
Unit Tests for Confidence Band Calculation (T032 - US1)
Local Knowledge Augmentation Platform

Tests confidence band thresholds per Research Decision RT-003:
- High (≥0.85): Auto-accept
- Medium (0.70-0.84): Optional review
- Low (<0.70): Required review
"""

import pytest
from classification import ProgressiveClassifier


class TestConfidenceBandCalculation:
    """Unit tests for confidence band calculation (T032)"""

    @pytest.fixture
    def classifier(self):
        return ProgressiveClassifier()

    def test_high_band_upper_boundary(self, classifier):
        """Verify 0.85 threshold (minimum for HIGH)"""
        band = classifier.get_confidence_band(0.85)
        assert band.value == "high"

    def test_high_band_extends_to_1(self, classifier):
        """Verify HIGH band extends to 1.0"""
        band = classifier.get_confidence_band(1.0)
        assert band.value == "high"

    def test_medium_band_lower_boundary(self, classifier):
        """Verify 0.70 threshold (minimum for MEDIUM)"""
        band = classifier.get_confidence_band(0.70)
        assert band.value == "medium"

    def test_medium_band_upper_boundary(self, classifier):
        """Verify 0.84 maps to MEDIUM (not HIGH)"""
        band = classifier.get_confidence_band(0.84)
        assert band.value == "medium"

    def test_low_band_upper_boundary(self, classifier):
        """Verify 0.69 maps to LOW"""
        band = classifier.get_confidence_band(0.69)
        assert band.value == "low"

    def test_low_band_extends_to_zero(self, classifier):
        """Verify LOW band extends to 0.0"""
        band = classifier.get_confidence_band(0.0)
        assert band.value == "low"

    def test_threshold_boundaries_dont_overlap(self, classifier):
        """Verify bands don't overlap - each value maps to exactly one band"""
        # Check boundary values don't map to multiple bands
        assert classifier.get_confidence_band(0.84) != classifier.get_confidence_band(0.85)
        assert classifier.get_confidence_band(0.69) != classifier.get_confidence_band(0.70)
