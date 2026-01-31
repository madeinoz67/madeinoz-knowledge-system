"""
Unit Tests for Metrics Exporter

Feature: 009-memory-decay-scoring
Tests: T067 - Metrics registration and recording

Tests verify that:
1. DecayMetricsExporter creates correct metric types
2. Recording methods work correctly
3. State counts and averages update properly
4. Global accessor functions work
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import sys
import os

# Add patches directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'patches'))


class TestDecayMetricsExporterWithoutOTEL:
    """Test DecayMetricsExporter when OpenTelemetry is not available."""

    def test_init_without_meter(self):
        """DecayMetricsExporter should handle None meter gracefully."""
        from metrics_exporter import DecayMetricsExporter

        exporter = DecayMetricsExporter(meter=None)

        assert exporter._meter is None
        assert exporter._counters == {}
        assert exporter._gauges == {}
        assert exporter._histograms == {}
        # State tracking should still be initialized
        assert "ACTIVE" in exporter._state_counts
        assert exporter._state_counts["ACTIVE"] == 0

    def test_record_maintenance_run_without_meter(self):
        """Recording should not raise when meter is None."""
        from metrics_exporter import DecayMetricsExporter

        exporter = DecayMetricsExporter(meter=None)

        # Should not raise
        exporter.record_maintenance_run(status="success", duration_seconds=5.0, scores_updated=100)

    def test_record_lifecycle_transition_without_meter(self):
        """Lifecycle transition recording should not raise when meter is None."""
        from metrics_exporter import DecayMetricsExporter

        exporter = DecayMetricsExporter(meter=None)

        # Should not raise
        exporter.record_lifecycle_transition(from_state="ACTIVE", to_state="DORMANT", count=5)

    def test_record_classification_without_meter(self):
        """Classification recording should not raise when meter is None."""
        from metrics_exporter import DecayMetricsExporter

        exporter = DecayMetricsExporter(meter=None)

        # Should not raise
        exporter.record_classification(status="success", latency_seconds=1.5)

    def test_record_memories_purged_without_meter(self):
        """Purge recording should not raise when meter is None."""
        from metrics_exporter import DecayMetricsExporter

        exporter = DecayMetricsExporter(meter=None)

        # Should not raise
        exporter.record_memories_purged(count=10)

    def test_record_weighted_search_without_meter(self):
        """Weighted search recording should not raise when meter is None."""
        from metrics_exporter import DecayMetricsExporter

        exporter = DecayMetricsExporter(meter=None)

        # Should not raise
        exporter.record_weighted_search(latency_seconds=0.05)


class TestDecayMetricsExporterStateTracking:
    """Test state count and average tracking."""

    def test_update_state_counts(self):
        """State counts should update correctly."""
        from metrics_exporter import DecayMetricsExporter

        exporter = DecayMetricsExporter(meter=None)

        exporter.update_state_counts({
            "ACTIVE": 100,
            "DORMANT": 50,
            "ARCHIVED": 25,
            "EXPIRED": 10,
            "SOFT_DELETED": 5,
        })

        assert exporter._state_counts["ACTIVE"] == 100
        assert exporter._state_counts["DORMANT"] == 50
        assert exporter._state_counts["ARCHIVED"] == 25
        assert exporter._state_counts["EXPIRED"] == 10
        assert exporter._state_counts["SOFT_DELETED"] == 5
        assert exporter._state_counts["PERMANENT"] == 30

    def test_update_state_counts_partial(self):
        """Partial state count updates should only affect specified states."""
        from metrics_exporter import DecayMetricsExporter

        exporter = DecayMetricsExporter(meter=None)

        # First update
        exporter.update_state_counts({"ACTIVE": 100})
        assert exporter._state_counts["ACTIVE"] == 100
        assert exporter._state_counts["DORMANT"] == 0  # Unchanged

        # Second partial update
        exporter.update_state_counts({"DORMANT": 50})
        assert exporter._state_counts["ACTIVE"] == 100  # Still 100
        assert exporter._state_counts["DORMANT"] == 50

    def test_update_state_counts_ignores_unknown_states(self):
        """Unknown states should be ignored."""
        from metrics_exporter import DecayMetricsExporter

        exporter = DecayMetricsExporter(meter=None)

        # Should not raise and should not add unknown state
        exporter.update_state_counts({"UNKNOWN_STATE": 999})

        assert "UNKNOWN_STATE" not in exporter._state_counts

    def test_update_averages(self):
        """Averages should update correctly."""
        from metrics_exporter import DecayMetricsExporter

        exporter = DecayMetricsExporter(meter=None)

        exporter.update_averages(
            decay=0.45,
            importance=3.7,
            stability=4.2,
            total=500
        )

        assert exporter._averages["decay_score"] == 0.45
        assert exporter._averages["importance"] == 3.7
        assert exporter._averages["stability"] == 4.2
        assert exporter._total_memories == 500

    def test_initial_state_counts(self):
        """Initial state counts should all be zero."""
        from metrics_exporter import DecayMetricsExporter

        exporter = DecayMetricsExporter(meter=None)

        for state in ["ACTIVE", "DORMANT", "ARCHIVED", "EXPIRED", "SOFT_DELETED"]:
            assert exporter._state_counts[state] == 0

    def test_initial_averages(self):
        """Initial averages should have sensible defaults."""
        from metrics_exporter import DecayMetricsExporter

        exporter = DecayMetricsExporter(meter=None)

        assert exporter._averages["decay_score"] == 0.0
        assert exporter._averages["importance"] == 3.0  # Neutral default
        assert exporter._averages["stability"] == 3.0   # Neutral default
        assert exporter._total_memories == 0


class TestDecayMetricsExporterWithMockedMeter:
    """Test DecayMetricsExporter with a mocked meter."""

    def create_mock_meter(self):
        """Create a mock OpenTelemetry meter."""
        meter = MagicMock()

        # Mock counter creation
        def mock_create_counter(**kwargs):
            counter = MagicMock()
            counter.name = kwargs.get('name', 'unknown')
            return counter
        meter.create_counter = mock_create_counter

        # Mock gauge creation
        def mock_create_observable_gauge(**kwargs):
            gauge = MagicMock()
            gauge.name = kwargs.get('name', 'unknown')
            return gauge
        meter.create_observable_gauge = mock_create_observable_gauge

        # Mock histogram creation
        def mock_create_histogram(**kwargs):
            histogram = MagicMock()
            histogram.name = kwargs.get('name', 'unknown')
            return histogram
        meter.create_histogram = mock_create_histogram

        return meter

    def test_counters_created(self):
        """All expected counters should be created."""
        from metrics_exporter import DecayMetricsExporter

        meter = self.create_mock_meter()
        exporter = DecayMetricsExporter(meter=meter)

        expected_counters = [
            "maintenance_runs",
            "scores_updated",
            "memories_purged",
            "lifecycle_transitions",
            "classification_requests",
            "weighted_searches",
        ]

        for counter_name in expected_counters:
            assert counter_name in exporter._counters, f"Counter {counter_name} not created"

    def test_gauges_created(self):
        """All expected gauges should be created."""
        from metrics_exporter import DecayMetricsExporter

        meter = self.create_mock_meter()
        exporter = DecayMetricsExporter(meter=meter)

        expected_gauges = [
            "memories_by_state",
            "decay_score_avg",
            "importance_avg",
            "stability_avg",
            "memories_total",
        ]

        for gauge_name in expected_gauges:
            assert gauge_name in exporter._gauges, f"Gauge {gauge_name} not created"

    def test_histograms_created(self):
        """All expected histograms should be created."""
        from metrics_exporter import DecayMetricsExporter

        meter = self.create_mock_meter()
        exporter = DecayMetricsExporter(meter=meter)

        expected_histograms = [
            "maintenance_duration",
            "classification_latency",
            "weighted_search_latency",
        ]

        for histogram_name in expected_histograms:
            assert histogram_name in exporter._histograms, f"Histogram {histogram_name} not created"

    def test_record_maintenance_run_calls_counter(self):
        """record_maintenance_run should call counter.add()."""
        from metrics_exporter import DecayMetricsExporter

        meter = self.create_mock_meter()
        exporter = DecayMetricsExporter(meter=meter)

        exporter.record_maintenance_run(status="success", duration_seconds=5.0, scores_updated=100)

        # Check counter was called
        exporter._counters["maintenance_runs"].add.assert_called_with(1, {"status": "success"})
        exporter._counters["scores_updated"].add.assert_called_with(100)

    def test_record_lifecycle_transition_calls_counter(self):
        """record_lifecycle_transition should call counter.add() with labels."""
        from metrics_exporter import DecayMetricsExporter

        meter = self.create_mock_meter()
        exporter = DecayMetricsExporter(meter=meter)

        exporter.record_lifecycle_transition(from_state="ACTIVE", to_state="DORMANT", count=5)

        exporter._counters["lifecycle_transitions"].add.assert_called_with(
            5,
            {"from_state": "ACTIVE", "to_state": "DORMANT"}
        )

    def test_record_classification_calls_counter_and_histogram(self):
        """record_classification should update counter and histogram."""
        from metrics_exporter import DecayMetricsExporter

        meter = self.create_mock_meter()
        exporter = DecayMetricsExporter(meter=meter)

        exporter.record_classification(status="success", latency_seconds=1.5)

        exporter._counters["classification_requests"].add.assert_called_with(1, {"status": "success"})
        exporter._histograms["classification_latency"].record.assert_called_with(1.5)

    def test_record_weighted_search_calls_counter_and_histogram(self):
        """record_weighted_search should update counter and histogram."""
        from metrics_exporter import DecayMetricsExporter

        meter = self.create_mock_meter()
        exporter = DecayMetricsExporter(meter=meter)

        exporter.record_weighted_search(latency_seconds=0.05)

        exporter._counters["weighted_searches"].add.assert_called_with(1)
        exporter._histograms["weighted_search_latency"].record.assert_called_with(0.05)

    def test_counters_preinitialized_with_known_labels(self):
        """Counters should be pre-initialized with known label values at startup."""
        from metrics_exporter import DecayMetricsExporter

        meter = self.create_mock_meter()
        exporter = DecayMetricsExporter(meter=meter)

        # Verify importance levels were pre-initialized (5 series)
        importance_levels = ["TRIVIAL", "LOW", "MODERATE", "HIGH", "CORE"]
        for level in importance_levels:
            exporter._counters["access_by_importance"].add.assert_any_call(0, {"level": level})

        # Verify lifecycle states were pre-initialized (5 series)
        lifecycle_states = ["ACTIVE", "DORMANT", "ARCHIVED", "EXPIRED", "SOFT_DELETED"]
        for state in lifecycle_states:
            exporter._counters["access_by_state"].add.assert_any_call(0, {"state": state})

        # Verify maintenance status pre-initialized (2 series)
        for status in ["success", "failure"]:
            exporter._counters["maintenance_runs"].add.assert_any_call(0, {"status": status})

        # Verify classification status pre-initialized (3 series)
        for status in ["success", "failure", "fallback"]:
            exporter._counters["classification_requests"].add.assert_any_call(0, {"status": status})

        # Verify reactivation sources pre-initialized (2 series)
        for from_state in ["DORMANT", "ARCHIVED"]:
            exporter._counters["reactivations"].add.assert_any_call(0, {"from_state": from_state})

        # Verify valid lifecycle transitions pre-initialized (7 series)
        valid_transitions = [
            ("ACTIVE", "DORMANT"),
            ("DORMANT", "ARCHIVED"),
            ("DORMANT", "ACTIVE"),
            ("ARCHIVED", "EXPIRED"),
            ("ARCHIVED", "ACTIVE"),
            ("EXPIRED", "SOFT_DELETED"),
            ("SOFT_DELETED", "ARCHIVED"),
        ]
        for from_state, to_state in valid_transitions:
            exporter._counters["lifecycle_transitions"].add.assert_any_call(
                0,
                {"from_state": from_state, "to_state": to_state}
            )


class TestGlobalAccessorFunctions:
    """Test global accessor functions for metrics exporters."""

    def test_get_decay_metrics_exporter_returns_none_initially(self):
        """get_decay_metrics_exporter should return None before initialization."""
        # Reset global state
        import metrics_exporter
        metrics_exporter._decay_metrics_exporter = None

        result = metrics_exporter.get_decay_metrics_exporter()
        assert result is None

    def test_get_metrics_exporter_returns_none_initially(self):
        """get_metrics_exporter should return None before initialization."""
        # Reset global state
        import metrics_exporter
        metrics_exporter._metrics_exporter = None

        result = metrics_exporter.get_metrics_exporter()
        assert result is None


class TestCacheMetricsExporterBasics:
    """Basic tests for CacheMetricsExporter (Feature 006)."""

    def test_init_disabled(self):
        """CacheMetricsExporter should accept enabled=False."""
        from metrics_exporter import CacheMetricsExporter

        exporter = CacheMetricsExporter(enabled=False)

        assert exporter.enabled is False
        assert exporter._meter is None

    def test_session_metrics_tracking(self):
        """Session metrics should track hits/misses/requests."""
        from metrics_exporter import CacheMetricsExporter

        exporter = CacheMetricsExporter(enabled=False)

        # Initial state
        assert exporter._session_metrics["hits"] == 0
        assert exporter._session_metrics["misses"] == 0
        assert exporter._session_metrics["requests"] == 0

    def test_record_cache_hit_disabled(self):
        """record_cache_hit should not raise when disabled."""
        from metrics_exporter import CacheMetricsExporter

        exporter = CacheMetricsExporter(enabled=False)

        # Should not raise
        exporter.record_cache_hit(model="test-model", tokens_saved=100, cost_saved=0.001)

    def test_record_cache_miss_disabled(self):
        """record_cache_miss should not raise when disabled."""
        from metrics_exporter import CacheMetricsExporter

        exporter = CacheMetricsExporter(enabled=False)

        # Should not raise
        exporter.record_cache_miss(model="test-model")


class TestMetricNames:
    """Test that metric names follow conventions."""

    def test_decay_counter_names(self):
        """Decay counter names should follow knowledge_ prefix convention."""
        from metrics_exporter import DecayMetricsExporter

        meter = MagicMock()
        created_names = []

        def capture_counter(**kwargs):
            created_names.append(kwargs.get('name', ''))
            return MagicMock()

        meter.create_counter = capture_counter
        meter.create_observable_gauge = MagicMock(return_value=MagicMock())
        meter.create_histogram = MagicMock(return_value=MagicMock())

        DecayMetricsExporter(meter=meter)

        # All counter names should start with knowledge_
        for name in created_names:
            assert name.startswith("knowledge_"), f"Counter {name} should start with knowledge_"

    def test_decay_histogram_names(self):
        """Decay histogram names should follow knowledge_ prefix convention."""
        from metrics_exporter import DecayMetricsExporter

        meter = MagicMock()
        created_names = []

        def capture_histogram(**kwargs):
            created_names.append(kwargs.get('name', ''))
            return MagicMock()

        meter.create_counter = MagicMock(return_value=MagicMock())
        meter.create_observable_gauge = MagicMock(return_value=MagicMock())
        meter.create_histogram = capture_histogram

        DecayMetricsExporter(meter=meter)

        # All histogram names should start with knowledge_
        for name in created_names:
            assert name.startswith("knowledge_"), f"Histogram {name} should start with knowledge_"


# Pytest configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
