"""
Unit Tests for Queue Metrics Exporter

Feature: 017-queue-metrics
Tests: Queue metrics recording, consumer health, and thread safety

Tests verify that:
1. QueueMetricsExporter creates correct metric types
2. Recording methods update counters and gauges correctly
3. Error categorization prevents high cardinality
4. Thread-safe state updates work correctly
5. Graceful degradation when OpenTelemetry unavailable
6. Performance overhead is minimal (< 1ms per recording)
"""

import pytest
import time
import threading
from unittest.mock import MagicMock, patch
import sys
import os

# Add patches directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'patches'))


class TestQueueMetricsExporterWithoutOTEL:
    """Test QueueMetricsExporter when OpenTelemetry is not available."""

    def test_init_without_meter(self):
        """QueueMetricsExporter should handle None meter gracefully."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        assert exporter._meter is None
        assert exporter._counters == {}
        assert exporter._gauges == {}
        assert exporter._histograms == {}
        # State tracking should still be initialized
        assert exporter._state_lock is not None

    def test_record_enqueue_without_meter(self):
        """Enqueue recording should not raise when meter is None."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        # Should not raise
        exporter.record_enqueue(queue_name="test", priority="normal")

    def test_record_dequeue_without_meter(self):
        """Dequeue recording should not raise when meter is None."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        # Should not raise
        exporter.record_dequeue(queue_name="test")

    def test_record_processing_complete_without_meter(self):
        """Processing complete should not raise when meter is None."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        # Should not raise
        exporter.record_processing_complete(
            queue_name="test",
            duration=0.5,
            success=True
        )

    def test_record_processing_complete_failure_without_meter(self):
        """Processing failure should not raise when meter is None."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        # Should not raise
        exporter.record_processing_complete(
            queue_name="test",
            duration=0.5,
            success=False,
            error_type="ConnectionError"
        )

    def test_record_retry_without_meter(self):
        """Retry recording should not raise when meter is None."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        # Should not raise
        exporter.record_retry(queue_name="test")

    def test_update_queue_depth_without_meter(self):
        """Queue depth update should not raise when meter is None."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        # Should not raise
        exporter.update_queue_depth(queue_name="test", depth=100)

    def test_update_consumer_metrics_without_meter(self):
        """Consumer metrics update should not raise when meter is None."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        # Should not raise
        exporter.update_consumer_metrics(
            queue_name="test",
            active=5,
            saturation=0.75,
            lag_seconds=30.0
        )


class TestQueueMetricsExporterStateTracking:
    """Test state tracking for queue depth and consumer metrics."""

    def test_initial_state(self):
        """Initial state should have default values."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        assert exporter._enqueued_total == {}
        assert exporter._processed_total == {}
        assert exporter._failed_total == {}
        assert exporter._queue_depth == {}
        assert exporter._consumer_saturation == 0.0
        assert exporter._consumer_lag_seconds == 0.0
        assert exporter._active_consumers == 1

    def test_enqueue_increments_internal_counter(self):
        """record_enqueue should increment internal enqueue counter."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        exporter.record_enqueue("test_queue")

        assert exporter._enqueued_total.get("test_queue") == 1

        # Second enqueue
        exporter.record_enqueue("test_queue")
        assert exporter._enqueued_total.get("test_queue") == 2

    def test_enqueue_increments_queue_depth(self):
        """record_enqueue should increment queue depth."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        exporter.record_enqueue("test_queue")
        assert exporter._queue_depth.get("test_queue") == 1

        exporter.record_enqueue("test_queue")
        assert exporter._queue_depth.get("test_queue") == 2

    def test_dequeue_decrements_queue_depth(self):
        """record_dequeue should decrement queue depth."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        # Enqueue first
        exporter.record_enqueue("test_queue")
        assert exporter._queue_depth.get("test_queue") == 1

        # Dequeue
        exporter.record_dequeue("test_queue")
        assert exporter._queue_depth.get("test_queue") == 0

    def test_dequeue_below_zero(self):
        """Queue depth should not go below zero."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        # Dequeue without enqueue
        exporter.record_dequeue("test_queue")
        assert exporter._queue_depth.get("test_queue") == 0

    def test_update_queue_depth_sets_exact_value(self):
        """update_queue_depth should set exact value."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        exporter.update_queue_depth("test_queue", depth=42)
        assert exporter._queue_depth.get("test_queue") == 42

    def test_update_queue_depth_clamps_negative(self):
        """update_queue_depth should clamp negative values to zero."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        exporter.update_queue_depth("test_queue", depth=-10)
        assert exporter._queue_depth.get("test_queue") == 0

    def test_update_consumer_metrics(self):
        """update_consumer_metrics should set all consumer metrics."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        exporter.update_consumer_metrics(
            queue_name="test",
            active=10,
            saturation=0.95,
            lag_seconds=120.0
        )

        assert exporter._active_consumers == 10
        assert exporter._consumer_saturation == 0.95
        assert exporter._consumer_lag_seconds == 120.0

    def test_update_consumer_metrics_clamps_values(self):
        """Consumer metrics should be clamped to valid ranges."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        # Negative active consumers
        exporter.update_consumer_metrics(active=-5)
        assert exporter._active_consumers == 0

        # Saturation above 1.0
        exporter.update_consumer_metrics(saturation=1.5)
        assert exporter._consumer_saturation == 1.0

        # Negative saturation
        exporter.update_consumer_metrics(saturation=-0.5)
        assert exporter._consumer_saturation == 0.0

        # Negative lag
        exporter.update_consumer_metrics(lag_seconds=-10.0)
        assert exporter._consumer_lag_seconds == 0.0


class TestQueueMetricsExporterWithMockedMeter:
    """Test QueueMetricsExporter with a mocked meter."""

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
        from metrics_exporter import QueueMetricsExporter

        meter = self.create_mock_meter()
        exporter = QueueMetricsExporter(meter=meter)

        expected_counters = [
            "messages_processed",
            "messages_failed",
            "retries",
        ]

        for counter_name in expected_counters:
            assert counter_name in exporter._counters, f"Counter {counter_name} not created"

    def test_gauges_created(self):
        """All expected gauges should be created."""
        from metrics_exporter import QueueMetricsExporter

        meter = self.create_mock_meter()
        exporter = QueueMetricsExporter(meter=meter)

        expected_gauges = [
            "queue_depth",
            "consumer_lag",
            "consumer_saturation",
            "active_consumers",
        ]

        for gauge_name in expected_gauges:
            assert gauge_name in exporter._gauges, f"Gauge {gauge_name} not created"

    def test_histograms_created(self):
        """All expected histograms should be created."""
        from metrics_exporter import QueueMetricsExporter

        meter = self.create_mock_meter()
        exporter = QueueMetricsExporter(meter=meter)

        expected_histograms = [
            "processing_duration",
            "wait_time",
            "end_to_end_latency",
        ]

        for histogram_name in expected_histograms:
            assert histogram_name in exporter._histograms, f"Histogram {histogram_name} not created"

    def test_record_enqueue_increments_counter(self):
        """record_enqueue should update internal counters."""
        from metrics_exporter import QueueMetricsExporter

        meter = self.create_mock_meter()
        exporter = QueueMetricsExporter(meter=meter)

        exporter.record_enqueue("test_queue", priority="high")

        # Check internal state
        assert exporter._enqueued_total["test_queue"] == 1
        assert exporter._queue_depth["test_queue"] == 1

    def test_record_dequeue_decrements_depth(self):
        """record_dequeue should decrement queue depth."""
        from metrics_exporter import QueueMetricsExporter

        meter = self.create_mock_meter()
        exporter = QueueMetricsExporter(meter=meter)

        # First enqueue
        exporter.record_enqueue("test_queue")
        assert exporter._queue_depth["test_queue"] == 1

        # Then dequeue
        exporter.record_dequeue("test_queue")
        assert exporter._queue_depth["test_queue"] == 0

    def test_record_processing_complete_success(self):
        """Processing complete with success should update counters."""
        from metrics_exporter import QueueMetricsExporter

        meter = self.create_mock_meter()
        exporter = QueueMetricsExporter(meter=meter)

        exporter.record_processing_complete(
            queue_name="test_queue",
            duration=0.5,
            success=True
        )

        # Check processed counter called with success status
        exporter._counters["messages_processed"].add.assert_called()
        call_args = exporter._counters["messages_processed"].add.call_args
        assert call_args[0][0] == 1
        assert call_args[0][1]["status"] == "success"

        # Check histogram recorded
        exporter._histograms["processing_duration"].record.assert_called()

    def test_record_processing_complete_failure(self):
        """Processing complete with failure should update failure counter."""
        from metrics_exporter import QueueMetricsExporter

        meter = self.create_mock_meter()
        exporter = QueueMetricsExporter(meter=meter)

        exporter.record_processing_complete(
            queue_name="test_queue",
            duration=0.5,
            success=False,
            error_type="ConnectionError"
        )

        # Check failure counter called
        exporter._counters["messages_failed"].add.assert_called()
        call_args = exporter._counters["messages_failed"].add.call_args
        assert call_args[0][0] == 1

    def test_record_retry_increments_counter(self):
        """record_retry should increment retry counter."""
        from metrics_exporter import QueueMetricsExporter

        meter = self.create_mock_meter()
        exporter = QueueMetricsExporter(meter=meter)

        exporter.record_retry("test_queue")

        exporter._counters["retries"].add.assert_called_with(1, {"queue_name": "test_queue"})

    def test_record_processing_complete_records_histograms(self):
        """Processing complete should record all relevant histograms."""
        from metrics_exporter import QueueMetricsExporter

        meter = self.create_mock_meter()
        exporter = QueueMetricsExporter(meter=meter)

        # First enqueue to set timestamp
        exporter.record_enqueue("test_queue")

        # Small delay to simulate wait time
        time.sleep(0.01)

        # Complete processing
        duration = 0.1
        exporter.record_processing_complete(
            queue_name="test_queue",
            duration=duration,
            success=True
        )

        # Check processing duration recorded
        exporter._histograms["processing_duration"].record.assert_called()
        duration_call = exporter._histograms["processing_duration"].record.call_args
        assert duration_call[0][0] == duration

    def test_metric_names_follow_messaging_prefix(self):
        """All metric names should use messaging_ prefix."""
        from metrics_exporter import QueueMetricsExporter

        meter = self.create_mock_meter()
        created_names = []

        def capture_name(**kwargs):
            created_names.append(kwargs.get('name', ''))
            return MagicMock()

        meter.create_counter = capture_name
        meter.create_observable_gauge = capture_name
        meter.create_histogram = capture_name

        QueueMetricsExporter(meter=meter)

        # All names should start with messaging_
        for name in created_names:
            assert name.startswith("messaging_"), f"Metric {name} should start with messaging_"


class TestErrorCategorization:
    """Test error categorization to prevent high cardinality."""

    def test_categorize_connection_errors(self):
        """Connection errors should map to ConnectionError category."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        assert exporter._categorize_error("ConnectionError") == "ConnectionError"
        assert exporter._categorize_error("ConnectionRefusedError") == "ConnectionError"
        assert exporter._categorize_error("OperationalError") == "ConnectionError"

    def test_categorize_validation_errors(self):
        """Validation errors should map to ValidationError category."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        assert exporter._categorize_error("ValidationError") == "ValidationError"
        assert exporter._categorize_error("ValueError") == "ValidationError"
        assert exporter._categorize_error("PydanticException") == "ValidationError"

    def test_categorize_timeout_errors(self):
        """Timeout errors should map to TimeoutError category."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        assert exporter._categorize_error("TimeoutError") == "TimeoutError"
        assert exporter._categorize_error("AsyncTimeoutError") == "TimeoutError"

    def test_categorize_rate_limit_errors(self):
        """Rate limit errors should map to RateLimitError category."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        assert exporter._categorize_error("RateLimitError") == "RateLimitError"
        assert exporter._categorize_error("RateLimitExceededError") == "RateLimitError"

    def test_categorize_unknown_errors(self):
        """Unknown errors should map to UnknownError category."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        assert exporter._categorize_error("SomeRandomError") == "UnknownError"
        assert exporter._categorize_error("") == "UnknownError"
        assert exporter._categorize_error(None) == "UnknownError"

    def test_partial_error_name_matching(self):
        """Error categorization should handle partial matches."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        # Should match ConnectionError substring
        assert exporter._categorize_error("DatabaseConnectionError") == "ConnectionError"


class TestThreadSafety:
    """Test thread-safe state updates."""

    def test_concurrent_enqueue_operations(self):
        """Concurrent enqueue operations should be thread-safe."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        num_threads = 10
        operations_per_thread = 100

        def enqueue_worker():
            for _ in range(operations_per_thread):
                exporter.record_enqueue("test_queue")

        threads = [threading.Thread(target=enqueue_worker) for _ in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All operations should be counted
        expected_count = num_threads * operations_per_thread
        assert exporter._enqueued_total["test_queue"] == expected_count
        assert exporter._queue_depth["test_queue"] == expected_count

    def test_concurrent_dequeue_operations(self):
        """Concurrent dequeue operations should be thread-safe."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        # First enqueue some messages
        initial_count = 100
        for _ in range(initial_count):
            exporter.record_enqueue("test_queue")

        assert exporter._queue_depth["test_queue"] == initial_count

        num_threads = 10
        operations_per_thread = 10

        def dequeue_worker():
            for _ in range(operations_per_thread):
                exporter.record_dequeue("test_queue")

        threads = [threading.Thread(target=dequeue_worker) for _ in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Depth should decrease by total dequeue operations
        expected_depth = initial_count - (num_threads * operations_per_thread)
        assert exporter._queue_depth["test_queue"] == expected_depth

    def test_concurrent_mixed_operations(self):
        """Mixed concurrent operations should be thread-safe."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        num_enqueues = 50
        num_dequeues = 30

        def enqueue_worker():
            for _ in range(num_enqueues):
                exporter.record_enqueue("test_queue")

        def dequeue_worker():
            for _ in range(num_dequeues):
                exporter.record_dequeue("test_queue")

        enqueue_thread = threading.Thread(target=enqueue_worker)
        dequeue_thread = threading.Thread(target=dequeue_worker)

        enqueue_thread.start()
        dequeue_thread.start()
        enqueue_thread.join()
        dequeue_thread.join()

        # Net change should be enqueues - dequeues
        expected_depth = num_enqueues - num_dequeues
        assert exporter._queue_depth["test_queue"] == expected_depth

    def test_concurrent_consumer_metric_updates(self):
        """Consumer metric updates should be thread-safe."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        num_threads = 10
        updates_per_thread = 50

        def update_worker(thread_id):
            for i in range(updates_per_thread):
                exporter.update_consumer_metrics(
                    active=thread_id,
                    saturation=0.5,
                    lag_seconds=i
                )

        threads = [threading.Thread(target=update_worker, args=(i,)) for i in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Final value should be from last update
        # (exact value depends on thread scheduling, but should be valid)
        assert 0 <= exporter._consumer_saturation <= 1.0
        assert exporter._active_consumers >= 0


class TestPerformanceOverhead:
    """Test performance overhead of metric recording."""

    def test_record_enqueue_overhead(self):
        """Enqueue recording should complete in under 1ms."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        iterations = 1000
        start = time.perf_counter()

        for _ in range(iterations):
            exporter.record_enqueue("test_queue")

        elapsed = time.perf_counter() - start
        avg_time_ms = (elapsed / iterations) * 1000

        # Average time per operation should be well under 1ms
        assert avg_time_ms < 1.0, f"Enqueue took {avg_time_ms:.3f}ms avg (target: < 1ms)"

    def test_record_dequeue_overhead(self):
        """Dequeue recording should complete in under 1ms."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)
        exporter.record_enqueue("test_queue")  # Pre-populate

        iterations = 1000
        start = time.perf_counter()

        for _ in range(iterations):
            exporter.record_dequeue("test_queue")

        elapsed = time.perf_counter() - start
        avg_time_ms = (elapsed / iterations) * 1000

        assert avg_time_ms < 1.0, f"Dequeue took {avg_time_ms:.3f}ms avg (target: < 1ms)"

    def test_record_processing_complete_overhead(self):
        """Processing complete recording should complete in under 1ms."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        iterations = 1000
        start = time.perf_counter()

        for _ in range(iterations):
            exporter.record_processing_complete(
                queue_name="test_queue",
                duration=0.5,
                success=True
            )

        elapsed = time.perf_counter() - start
        avg_time_ms = (elapsed / iterations) * 1000

        assert avg_time_ms < 1.0, f"Processing complete took {avg_time_ms:.3f}ms avg (target: < 1ms)"

    def test_update_queue_depth_overhead(self):
        """Queue depth update should complete in under 1ms."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        iterations = 1000
        start = time.perf_counter()

        for _ in range(iterations):
            exporter.update_queue_depth("test_queue", depth=100)

        elapsed = time.perf_counter() - start
        avg_time_ms = (elapsed / iterations) * 1000

        assert avg_time_ms < 1.0, f"Queue depth update took {avg_time_ms:.3f}ms avg (target: < 1ms)"

    def test_update_consumer_metrics_overhead(self):
        """Consumer metrics update should complete in under 1ms."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        iterations = 1000
        start = time.perf_counter()

        for _ in range(iterations):
            exporter.update_consumer_metrics(
                active=5,
                saturation=0.75,
                lag_seconds=30.0
            )

        elapsed = time.perf_counter() - start
        avg_time_ms = (elapsed / iterations) * 1000

        assert avg_time_ms < 1.0, f"Consumer metrics update took {avg_time_ms:.3f}ms avg (target: < 1ms)"

    def test_error_categorization_overhead(self):
        """Error categorization should complete in under 0.1ms."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        iterations = 10000
        start = time.perf_counter()

        for _ in range(iterations):
            exporter._categorize_error("ConnectionError")

        elapsed = time.perf_counter() - start
        avg_time_ms = (elapsed / iterations) * 1000

        # Error categorization should be very fast
        assert avg_time_ms < 0.1, f"Error categorization took {avg_time_ms:.4f}ms avg (target: < 0.1ms)"


class TestGlobalAccessorFunctions:
    """Test global accessor functions for queue metrics."""

    def test_get_queue_metrics_exporter_returns_none_initially(self):
        """get_queue_metrics_exporter should return None before initialization."""
        import metrics_exporter
        # Reset global state
        metrics_exporter._queue_metrics_exporter = None

        result = metrics_exporter.get_queue_metrics_exporter()
        assert result is None

    def test_initialize_queue_metrics_exporter_without_cache_exporter(self):
        """initialize_queue_metrics_exporter should return None if cache exporter not initialized."""
        import metrics_exporter
        # Reset global state
        metrics_exporter._queue_metrics_exporter = None
        metrics_exporter._metrics_exporter = None

        result = metrics_exporter.initialize_queue_metrics_exporter()
        assert result is None

    def test_initialize_queue_metrics_exporter_returns_same_instance(self):
        """initialize_queue_metrics_exporter should return same instance on subsequent calls."""
        import metrics_exporter

        # Mock the cache exporter
        mock_meter = MagicMock()
        metrics_exporter._metrics_exporter = MagicMock()
        metrics_exporter._metrics_exporter._meter = mock_meter

        # First call
        first = metrics_exporter.initialize_queue_metrics_exporter()
        # Second call
        second = metrics_exporter.initialize_queue_metrics_exporter()

        assert first is second


class TestQueueMetricLabels:
    """Test label handling for queue metrics."""

    def test_enqueue_with_different_queues(self):
        """Metrics should track different queues separately."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        exporter.record_enqueue("queue_a")
        exporter.record_enqueue("queue_b")
        exporter.record_enqueue("queue_a")

        assert exporter._enqueued_total["queue_a"] == 2
        assert exporter._enqueued_total["queue_b"] == 1

    def test_enqueue_with_different_priorities(self):
        """Priority should be tracked (internal state only)."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        exporter.record_enqueue("test", priority="low")
        exporter.record_enqueue("test", priority="high")

        # Both enqueues should be counted
        assert exporter._enqueued_total["test"] == 2


class TestProcessingStartContextManager:
    """Test the record_processing_start context manager."""

    def test_context_manager_yields(self):
        """Context manager should yield None."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        with exporter.record_processing_start("test_queue") as result:
            assert result is None

    def test_context_manager_records_start_time(self):
        """Context manager should record start timestamp."""
        from metrics_exporter import QueueMetricsExporter

        exporter = QueueMetricsExporter(meter=None)

        before = time.time()
        with exporter.record_processing_start("test_queue"):
            start = exporter._processing_start_times.get("test_queue")
            assert start is not None
            assert start >= before
        after = time.time()

        # Start time should be between before and after
        assert before <= start <= after


# Pytest configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
