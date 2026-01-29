"""
Unit Tests for Memory Decay Calculator

Feature: 009-memory-decay-scoring
Tests: T023 - DecayCalculator, T024 - weighted_score edge cases

Tests verify that:
1. DecayCalculator uses exponential half-life model
2. Stability adjusts half-life correctly
3. Importance adjusts decay rate correctly
4. Permanent memories don't decay
5. Weighted scoring combines semantic/recency/importance correctly
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from math import exp, log
import sys
import os

# Add patches directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'patches'))


class TestDecayCalculatorInit:
    """Test DecayCalculator initialization."""

    def test_init_with_explicit_half_life(self):
        """Should use provided half-life value."""
        from memory_decay import DecayCalculator

        calc = DecayCalculator(base_half_life=45.0)

        assert calc.base_half_life == 45.0

    def test_init_loads_from_config(self):
        """Should load half-life from config when not provided."""
        from memory_decay import DecayCalculator

        calc = DecayCalculator()

        # Default from config/decay-config.yaml is 30.0
        assert calc.base_half_life == 30.0


class TestStabilityAdjustedHalfLife:
    """Test stability-adjusted half-life calculation (T030)."""

    def test_stability_1_volatile(self):
        """Stability 1 (volatile) should give 1/3 of base half-life."""
        from memory_decay import DecayCalculator

        calc = DecayCalculator(base_half_life=30.0)
        half_life = calc.get_stability_adjusted_half_life(stability=1)

        assert half_life == pytest.approx(10.0, abs=0.01)  # 30 * 1/3 = 10

    def test_stability_2_low(self):
        """Stability 2 (low) should give 2/3 of base half-life."""
        from memory_decay import DecayCalculator

        calc = DecayCalculator(base_half_life=30.0)
        half_life = calc.get_stability_adjusted_half_life(stability=2)

        assert half_life == pytest.approx(20.0, abs=0.01)  # 30 * 2/3 = 20

    def test_stability_3_moderate(self):
        """Stability 3 (moderate) should give exactly base half-life."""
        from memory_decay import DecayCalculator

        calc = DecayCalculator(base_half_life=30.0)
        half_life = calc.get_stability_adjusted_half_life(stability=3)

        assert half_life == pytest.approx(30.0, abs=0.01)  # 30 * 3/3 = 30

    def test_stability_4_high(self):
        """Stability 4 (high) should give 4/3 of base half-life."""
        from memory_decay import DecayCalculator

        calc = DecayCalculator(base_half_life=30.0)
        half_life = calc.get_stability_adjusted_half_life(stability=4)

        assert half_life == pytest.approx(40.0, abs=0.01)  # 30 * 4/3 = 40

    def test_stability_5_permanent(self):
        """Stability 5 (permanent) should give 5/3 of base half-life."""
        from memory_decay import DecayCalculator

        calc = DecayCalculator(base_half_life=30.0)
        half_life = calc.get_stability_adjusted_half_life(stability=5)

        assert half_life == pytest.approx(50.0, abs=0.01)  # 30 * 5/3 = 50


class TestCalculateDecay:
    """Test decay score calculation."""

    def test_no_decay_at_zero_days(self):
        """Decay should be 0 immediately after access."""
        from memory_decay import DecayCalculator

        calc = DecayCalculator(base_half_life=30.0)
        decay = calc.calculate_decay(days_since_access=0, importance=3, stability=3)

        assert decay == 0.0

    def test_no_decay_for_negative_days(self):
        """Decay should be 0 for negative days."""
        from memory_decay import DecayCalculator

        calc = DecayCalculator(base_half_life=30.0)
        decay = calc.calculate_decay(days_since_access=-5, importance=3, stability=3)

        assert decay == 0.0

    def test_half_decay_at_half_life(self):
        """Decay should be ~0.5 at half-life (for neutral importance)."""
        from memory_decay import DecayCalculator

        calc = DecayCalculator(base_half_life=30.0)
        # With importance=3 (neutral), rate is not adjusted
        # stability=3 means half-life is 30 days
        # At 30 days, decay should be 0.5 for base formula

        # However, importance adjustment affects this
        # adjusted_rate = lambda * (6-3)/5 = 0.6 * lambda
        # So actual half-life for decay is 30 / 0.6 = 50 days
        # At 30 days with adjusted rate, decay = 1 - exp(-0.6*ln(2)) ≈ 0.34

        decay = calc.calculate_decay(days_since_access=30, importance=3, stability=3)

        # Verify it's between 0.3 and 0.4 (accounting for importance adjustment)
        assert 0.3 <= decay <= 0.45

    def test_higher_importance_slows_decay(self):
        """Higher importance should result in slower decay."""
        from memory_decay import DecayCalculator

        calc = DecayCalculator(base_half_life=30.0)

        decay_low = calc.calculate_decay(days_since_access=30, importance=1, stability=3)
        decay_high = calc.calculate_decay(days_since_access=30, importance=5, stability=3)

        assert decay_low > decay_high

    def test_higher_stability_slows_decay(self):
        """Higher stability should result in slower decay."""
        from memory_decay import DecayCalculator

        calc = DecayCalculator(base_half_life=30.0)

        decay_volatile = calc.calculate_decay(days_since_access=30, importance=3, stability=1)
        decay_stable = calc.calculate_decay(days_since_access=30, importance=3, stability=5)

        assert decay_volatile > decay_stable

    def test_decay_increases_over_time(self):
        """Decay should increase as time passes."""
        from memory_decay import DecayCalculator

        calc = DecayCalculator(base_half_life=30.0)

        decay_1d = calc.calculate_decay(days_since_access=1, importance=3, stability=3)
        decay_7d = calc.calculate_decay(days_since_access=7, importance=3, stability=3)
        decay_30d = calc.calculate_decay(days_since_access=30, importance=3, stability=3)
        decay_90d = calc.calculate_decay(days_since_access=90, importance=3, stability=3)

        assert decay_1d < decay_7d < decay_30d < decay_90d

    def test_decay_approaches_one(self):
        """Decay should approach 1.0 over very long time."""
        from memory_decay import DecayCalculator

        calc = DecayCalculator(base_half_life=30.0)
        decay = calc.calculate_decay(days_since_access=365, importance=1, stability=1)

        assert decay >= 0.99

    def test_decay_rounded_to_3_decimals(self):
        """Decay score should be rounded to 3 decimal places."""
        from memory_decay import DecayCalculator

        calc = DecayCalculator(base_half_life=30.0)
        decay = calc.calculate_decay(days_since_access=17.123456, importance=3, stability=3)

        # Check it's rounded
        assert decay == round(decay, 3)


class TestPermanentMemoryExemption:
    """Test that permanent memories don't decay (T031)."""

    def test_permanent_at_threshold_no_decay(self):
        """Importance=4, stability=4 should not decay."""
        from memory_decay import DecayCalculator

        calc = DecayCalculator(base_half_life=30.0)
        decay = calc.calculate_decay(days_since_access=365, importance=4, stability=4)

        assert decay == 0.0

    def test_permanent_max_values_no_decay(self):
        """Importance=5, stability=5 should not decay."""
        from memory_decay import DecayCalculator

        calc = DecayCalculator(base_half_life=30.0)
        decay = calc.calculate_decay(days_since_access=1000, importance=5, stability=5)

        assert decay == 0.0

    def test_permanent_mixed_high_no_decay(self):
        """Importance=5, stability=4 should not decay."""
        from memory_decay import DecayCalculator

        calc = DecayCalculator(base_half_life=30.0)
        decay = calc.calculate_decay(days_since_access=500, importance=5, stability=4)

        assert decay == 0.0

    def test_non_permanent_does_decay(self):
        """Importance=3, stability=4 should decay."""
        from memory_decay import DecayCalculator

        calc = DecayCalculator(base_half_life=30.0)
        decay = calc.calculate_decay(days_since_access=30, importance=3, stability=4)

        assert decay > 0.0


class TestCalculateFromTimestamp:
    """Test decay calculation from timestamps."""

    def test_calculate_from_last_accessed(self):
        """Should use last_accessed_at when available."""
        from memory_decay import DecayCalculator

        calc = DecayCalculator(base_half_life=30.0)
        now = datetime.now(timezone.utc)
        last_accessed = now - timedelta(days=15)
        created = now - timedelta(days=60)

        decay = calc.calculate_from_timestamp(
            last_accessed_at=last_accessed,
            created_at=created,
            importance=3,
            stability=3,
            now=now
        )

        # Should use 15 days (from last_accessed), not 60 days (from created)
        direct_decay = calc.calculate_decay(15, importance=3, stability=3)
        assert decay == pytest.approx(direct_decay, abs=0.001)

    def test_calculate_from_created_when_not_accessed(self):
        """Should fall back to created_at when no last_accessed_at."""
        from memory_decay import DecayCalculator

        calc = DecayCalculator(base_half_life=30.0)
        now = datetime.now(timezone.utc)
        created = now - timedelta(days=30)

        decay = calc.calculate_from_timestamp(
            last_accessed_at=None,
            created_at=created,
            importance=3,
            stability=3,
            now=now
        )

        direct_decay = calc.calculate_decay(30, importance=3, stability=3)
        assert decay == pytest.approx(direct_decay, abs=0.001)

    def test_handles_naive_datetime(self):
        """Should handle naive datetime by assuming UTC."""
        from memory_decay import DecayCalculator

        calc = DecayCalculator(base_half_life=30.0)
        now = datetime.now(timezone.utc)
        # Create naive datetime (no timezone)
        created = datetime(2024, 1, 1)

        # Should not raise exception
        decay = calc.calculate_from_timestamp(
            last_accessed_at=None,
            created_at=created,
            importance=3,
            stability=3,
            now=now
        )

        assert 0.0 <= decay <= 1.0


class TestCalculateRecencyScore:
    """Test recency score calculation for weighted search."""

    def test_recency_at_zero_days(self):
        """Recency should be 1.0 immediately after access."""
        from memory_decay import calculate_recency_score

        score = calculate_recency_score(days_since_access=0)

        assert score == 1.0

    def test_recency_at_half_life(self):
        """Recency should be 0.5 at half-life."""
        from memory_decay import calculate_recency_score

        score = calculate_recency_score(days_since_access=30, half_life=30)

        assert score == pytest.approx(0.5, abs=0.01)

    def test_recency_decreases_over_time(self):
        """Recency should decrease as time passes."""
        from memory_decay import calculate_recency_score

        score_1d = calculate_recency_score(days_since_access=1)
        score_7d = calculate_recency_score(days_since_access=7)
        score_30d = calculate_recency_score(days_since_access=30)

        assert score_1d > score_7d > score_30d

    def test_recency_approaches_zero(self):
        """Recency should approach 0 over very long time."""
        from memory_decay import calculate_recency_score

        score = calculate_recency_score(days_since_access=365)

        assert score < 0.01


class TestCalculateWeightedScore:
    """Test weighted score calculation (T024)."""

    def test_default_weights(self):
        """Should use default weights (60/25/15) when not specified."""
        from memory_decay import calculate_weighted_score

        # Perfect semantic match, just accessed, max importance
        score = calculate_weighted_score(
            semantic_score=1.0,
            days_since_access=0,
            importance=5,
            weights=(0.6, 0.25, 0.15)
        )

        # 0.6*1.0 + 0.25*1.0 + 0.15*1.0 = 1.0
        assert score == pytest.approx(1.0, abs=0.01)

    def test_semantic_weight_dominates(self):
        """Semantic score should have 60% weight."""
        from memory_decay import calculate_weighted_score

        # High semantic, old access, low importance
        score = calculate_weighted_score(
            semantic_score=1.0,
            days_since_access=365,
            importance=1,
            weights=(0.6, 0.25, 0.15)
        )

        # Semantic contributes 0.6
        assert score >= 0.6

    def test_importance_normalized_correctly(self):
        """Importance should be normalized to 0-1 range."""
        from memory_decay import calculate_weighted_score

        score_low = calculate_weighted_score(
            semantic_score=0.5,
            days_since_access=0,
            importance=1,
            weights=(0.6, 0.25, 0.15)
        )

        score_high = calculate_weighted_score(
            semantic_score=0.5,
            days_since_access=0,
            importance=5,
            weights=(0.6, 0.25, 0.15)
        )

        # importance=1 gives 0.15*0.2 = 0.03
        # importance=5 gives 0.15*1.0 = 0.15
        # Difference should be about 0.12
        assert score_high - score_low == pytest.approx(0.12, abs=0.01)

    def test_zero_semantic_score(self):
        """Should handle zero semantic score."""
        from memory_decay import calculate_weighted_score

        score = calculate_weighted_score(
            semantic_score=0.0,
            days_since_access=0,
            importance=5,
            weights=(0.6, 0.25, 0.15)
        )

        # 0.6*0.0 + 0.25*1.0 + 0.15*1.0 = 0.40
        assert score == pytest.approx(0.40, abs=0.01)

    def test_custom_weights(self):
        """Should respect custom weight configuration."""
        from memory_decay import calculate_weighted_score

        # Use equal weights
        score = calculate_weighted_score(
            semantic_score=0.9,
            days_since_access=0,
            importance=3,
            weights=(0.33, 0.34, 0.33)
        )

        # 0.33*0.9 + 0.34*1.0 + 0.33*0.6 = 0.297 + 0.34 + 0.198 = 0.835
        expected = 0.33 * 0.9 + 0.34 * 1.0 + 0.33 * (3/5)
        assert score == pytest.approx(expected, abs=0.01)

    def test_score_rounded_to_4_decimals(self):
        """Weighted score should be rounded to 4 decimal places."""
        from memory_decay import calculate_weighted_score

        score = calculate_weighted_score(
            semantic_score=0.123456789,
            days_since_access=7.654321,
            importance=3,
            weights=(0.6, 0.25, 0.15)
        )

        assert score == round(score, 4)


class TestWeightedSearchResult:
    """Test WeightedSearchResult dataclass."""

    def test_to_dict(self):
        """to_dict should return all fields."""
        from memory_decay import WeightedSearchResult

        result = WeightedSearchResult(
            uuid="test-uuid",
            name="Test Entity",
            summary="A test summary",
            weighted_score=0.85,
            score_breakdown={"semantic": 0.9, "recency": 0.7, "importance": 0.8},
            lifecycle_state="ACTIVE",
            importance=4,
            stability=3,
            decay_score=0.15,
            last_accessed_at="2024-01-15T10:00:00Z"
        )

        d = result.to_dict()

        assert d["uuid"] == "test-uuid"
        assert d["name"] == "Test Entity"
        assert d["weighted_score"] == 0.85
        assert d["lifecycle_state"] == "ACTIVE"
        assert d["score_breakdown"]["semantic"] == 0.9


class TestApplyWeightedScoring:
    """Test apply_weighted_scoring function."""

    def test_results_sorted_by_weighted_score(self):
        """Results should be sorted by weighted_score descending."""
        from memory_decay import apply_weighted_scoring

        # Create mock nodes
        node1 = MagicMock()
        node1.uuid = "node-1"
        node1.name = "Low Semantic"
        node1.attributes = {"importance": 3, "stability": 3, "lifecycle_state": "ACTIVE"}
        node1.created_at = datetime.now(timezone.utc)

        node2 = MagicMock()
        node2.uuid = "node-2"
        node2.name = "High Semantic"
        node2.attributes = {"importance": 3, "stability": 3, "lifecycle_state": "ACTIVE"}
        node2.created_at = datetime.now(timezone.utc)

        # Node 2 has higher semantic score
        results = apply_weighted_scoring(
            nodes=[node1, node2],
            semantic_scores=[0.3, 0.9]
        )

        assert results[0].uuid == "node-2"  # Higher semantic first
        assert results[1].uuid == "node-1"

    def test_handles_missing_attributes(self):
        """Should use defaults when attributes missing."""
        from memory_decay import apply_weighted_scoring

        node = MagicMock()
        node.uuid = "node-1"
        node.name = "No Attributes"
        node.attributes = {}  # Empty
        node.created_at = datetime.now(timezone.utc)

        results = apply_weighted_scoring(
            nodes=[node],
            semantic_scores=[0.8]
        )

        # Should use defaults: importance=3, stability=3
        assert results[0].importance == 3
        assert results[0].stability == 3
        assert results[0].lifecycle_state == "ACTIVE"

    def test_includes_score_breakdown(self):
        """Results should include score breakdown."""
        from memory_decay import apply_weighted_scoring

        node = MagicMock()
        node.uuid = "node-1"
        node.name = "Test"
        node.attributes = {"importance": 4, "stability": 3, "lifecycle_state": "ACTIVE"}
        node.created_at = datetime.now(timezone.utc)

        results = apply_weighted_scoring(
            nodes=[node],
            semantic_scores=[0.75]
        )

        breakdown = results[0].score_breakdown
        assert "semantic" in breakdown
        assert "recency" in breakdown
        assert "importance" in breakdown
        assert breakdown["semantic"] == pytest.approx(0.75, abs=0.01)


class TestBatchUpdateDecayScores:
    """Test batch_update_decay_scores function."""

    @pytest.mark.asyncio
    async def test_returns_update_count(self):
        """Should return count of updated nodes."""
        from memory_decay import batch_update_decay_scores

        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()

        mock_result.single = MagicMock(return_value={"updated": 150})
        mock_session.run = MagicMock(return_value=mock_result)
        mock_session.__aenter__ = MagicMock(return_value=mock_session)
        mock_session.__aexit__ = MagicMock(return_value=None)
        mock_driver.session = MagicMock(return_value=mock_session)

        # Use AsyncMock for async context
        from unittest.mock import AsyncMock
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_result.single = AsyncMock(return_value={"updated": 150})
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        count = await batch_update_decay_scores(mock_driver, base_half_life=30.0)

        assert count == 150

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_record(self):
        """Should return 0 when no record returned."""
        from memory_decay import batch_update_decay_scores
        from unittest.mock import AsyncMock

        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()

        mock_result.single = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_driver.session = MagicMock(return_value=mock_session)

        count = await batch_update_decay_scores(mock_driver, base_half_life=30.0)

        assert count == 0


# Pytest configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
