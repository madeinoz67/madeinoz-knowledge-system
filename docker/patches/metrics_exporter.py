"""
Metrics Exporter - OpenTelemetry/Prometheus Integration

Feature: 006-gemini-prompt-caching
Purpose: Expose cache statistics via Prometheus metrics endpoint
"""

import os
import logging
from typing import Optional, Dict, Any
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from prometheus_client import start_http_server

logger = logging.getLogger(__name__)


class CacheMetricsExporter:
    """
    Manages OpenTelemetry/Prometheus metrics for cache statistics.

    Provides counters and gauges for tracking cache effectiveness, token savings,
    and cost reductions in a format compatible with Prometheus scraping.
    """

    def __init__(self, enabled: bool = True, port: int = 9090):
        """
        Initialize metrics exporter.

        Args:
            enabled: Whether metrics collection is enabled
            port: Port for Prometheus metrics HTTP server (default: 9090)
        """
        self.enabled = enabled
        self.port = port
        self._meter: Optional[Any] = None
        self._counters: Dict[str, Any] = {}
        self._gauges: Dict[str, Any] = {}
        self._session_metrics = {"hits": 0, "misses": 0, "requests": 0}

        if self.enabled:
            self._initialize_metrics()

    def _initialize_metrics(self) -> None:
        """
        Initialize OpenTelemetry meter provider and Prometheus exporter.

        Creates meter for 'graphiti.cache' namespace and starts HTTP server.
        """
        try:
            # Create Prometheus metric reader
            reader = PrometheusMetricReader()

            # Set up meter provider
            provider = MeterProvider(metric_readers=[reader])
            metrics.set_meter_provider(provider)

            # Get meter for cache metrics
            self._meter = metrics.get_meter("graphiti.cache", version="1.0.0")

            # Create metrics
            self._create_counters()
            self._create_gauges()

            # Start Prometheus HTTP server
            start_http_server(self.port)
            logger.info(f"Prometheus metrics endpoint started on port {self.port}")

        except Exception as e:
            logger.error(f"Failed to initialize metrics exporter: {e}")
            self.enabled = False

    def _create_counters(self) -> None:
        """
        Create counter metrics for cumulative statistics.

        Counters track total counts since server start and never decrease.
        """
        if not self._meter:
            return

        self._counters = {
            "cache_hits_total": self._meter.create_counter(
                name="graphiti_cache_hits_total",
                description="Total number of cache hits since server start",
                unit="1"
            ),
            "cache_misses_total": self._meter.create_counter(
                name="graphiti_cache_misses_total",
                description="Total number of cache misses since server start",
                unit="1"
            ),
            "cache_tokens_saved_total": self._meter.create_counter(
                name="graphiti_cache_tokens_saved_total",
                description="Total tokens saved via caching since server start",
                unit="1"
            ),
            "cache_cost_saved_total": self._meter.create_counter(
                name="graphiti_cache_cost_saved_total",
                description="Total cost savings in USD from caching since server start",
                unit="USD"
            ),
            "cache_requests_total": self._meter.create_counter(
                name="graphiti_cache_requests_total",
                description="Total API requests with cache metrics since server start",
                unit="1"
            )
        }

    def _create_gauges(self) -> None:
        """
        Create gauge metrics for current state values.

        Gauges track values that can go up or down over time.
        """
        if not self._meter:
            return

        # Observable gauges need callback functions
        def get_cache_hit_rate(_options):
            """Calculate current cache hit rate."""
            if self._session_metrics["requests"] == 0:
                return [metrics.Observation(0.0)]
            rate = (self._session_metrics["hits"] / self._session_metrics["requests"]) * 100
            return [metrics.Observation(rate)]

        def get_cache_enabled(_options):
            """Return cache enabled status (1=enabled, 0=disabled)."""
            return [metrics.Observation(1 if self.enabled else 0)]

        self._gauges = {
            "cache_hit_rate": self._meter.create_observable_gauge(
                name="graphiti_cache_hit_rate",
                description="Current cache hit rate as a percentage (0-100)",
                unit="%",
                callbacks=[get_cache_hit_rate]
            ),
            "cache_enabled": self._meter.create_observable_gauge(
                name="graphiti_cache_enabled",
                description="Whether caching is currently enabled (1=enabled, 0=disabled)",
                unit="1",
                callbacks=[get_cache_enabled]
            )
        }

    def record_cache_hit(self, model: str, tokens_saved: int, cost_saved: float) -> None:
        """
        Record a cache hit event.

        Args:
            model: Gemini model identifier
            tokens_saved: Number of tokens served from cache
            cost_saved: Cost savings in USD
        """
        if not self.enabled or not self._counters:
            return

        try:
            attributes = {"model": model}

            self._counters["cache_hits_total"].add(1, attributes)
            self._counters["cache_tokens_saved_total"].add(tokens_saved, attributes)
            self._counters["cache_cost_saved_total"].add(cost_saved, attributes)
            self._counters["cache_requests_total"].add(1, attributes)

            # Update session metrics for hit rate calculation
            self._session_metrics["hits"] += 1
            self._session_metrics["requests"] += 1

        except Exception as e:
            logger.error(f"Failed to record cache hit: {e}")

    def record_cache_miss(self, model: str) -> None:
        """
        Record a cache miss event.

        Args:
            model: Gemini model identifier
        """
        if not self.enabled or not self._counters:
            return

        try:
            attributes = {"model": model}

            self._counters["cache_misses_total"].add(1, attributes)
            self._counters["cache_requests_total"].add(1, attributes)

            # Update session metrics for hit rate calculation
            self._session_metrics["misses"] += 1
            self._session_metrics["requests"] += 1

        except Exception as e:
            logger.error(f"Failed to record cache miss: {e}")


# Global metrics exporter instance
_metrics_exporter: Optional[CacheMetricsExporter] = None


def initialize_metrics_exporter(enabled: bool = True, port: int = 9090) -> CacheMetricsExporter:
    """
    Initialize the global metrics exporter instance.

    Should be called once at server startup.

    Args:
        enabled: Whether metrics collection is enabled
        port: Port for Prometheus HTTP server

    Returns:
        CacheMetricsExporter instance
    """
    global _metrics_exporter

    if _metrics_exporter is None:
        _metrics_exporter = CacheMetricsExporter(enabled=enabled, port=port)
    return _metrics_exporter


def get_metrics_exporter() -> Optional[CacheMetricsExporter]:
    """
    Get the global metrics exporter instance.

    Returns:
        CacheMetricsExporter if initialized, None otherwise
    """
    return _metrics_exporter
