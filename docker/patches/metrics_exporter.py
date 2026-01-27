"""
Metrics Exporter - OpenTelemetry/Prometheus Integration

Feature: 006-gemini-prompt-caching
Purpose: Expose cache statistics via Prometheus metrics endpoint
"""

import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Optional opentelemetry imports - gracefully degrade if not installed
try:
    from opentelemetry import metrics
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.view import View, ExplicitBucketHistogramAggregation
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from prometheus_client import start_http_server
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    logger.warning("OpenTelemetry not available - metrics export disabled")
    OPENTELEMETRY_AVAILABLE = False
    metrics = None
    MeterProvider = None
    View = None
    ExplicitBucketHistogramAggregation = None
    PrometheusMetricReader = None
    start_http_server = None


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
        self._histograms: Dict[str, Any] = {}
        self._session_metrics = {"hits": 0, "misses": 0, "requests": 0}

        if self.enabled:
            self._initialize_metrics()

    def _initialize_metrics(self) -> None:
        """
        Initialize OpenTelemetry meter provider and Prometheus exporter.

        Creates meter for 'graphiti.cache' namespace and starts HTTP server.
        """
        if not OPENTELEMETRY_AVAILABLE:
            logger.info("Metrics export disabled - OpenTelemetry not available")
            self.enabled = False
            return

        try:
            # Create Prometheus metric reader
            reader = PrometheusMetricReader()

            # Define custom bucket boundaries for histograms
            # Cost buckets: micro-dollar to dollar scale
            # - Low end ($0.00001-$0.01): cheap models like Gemini Flash, GPT-4o-mini
            # - Mid range ($0.01-$0.10): standard models like GPT-4o, Claude Sonnet
            # - High end ($0.10-$1.00): expensive models like GPT-4, Claude Opus
            # - Very high ($1.00-$5.00): large context requests on expensive models
            cost_buckets = [
                0.000005, 0.00001, 0.000025, 0.00005, 0.0001,
                0.00025, 0.0005, 0.001, 0.0025, 0.005, 0.01,
                0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0
            ]
            # Token buckets: LLM request sizes (10 to 100k+ tokens)
            # - Small (10-500): simple queries
            # - Medium (500-5000): typical requests
            # - Large (5000-50000): context-heavy requests
            # - Very large (50000-200000): max context models
            token_buckets = [
                10, 25, 50, 100, 250, 500, 1000, 2000, 3000, 5000,
                10000, 25000, 50000, 100000, 200000
            ]
            # Duration buckets: LLM request latency in seconds
            # - Fast (0.1-1s): cached/simple requests
            # - Normal (1-10s): typical LLM calls
            # - Slow (10-60s): complex reasoning, large context
            # - Very slow (60-300s): timeout territory
            duration_buckets = [
                0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0,
                15.0, 30.0, 60.0, 120.0, 300.0
            ]

            # Create views with custom bucket boundaries
            views = [
                # Cost histogram views
                View(
                    instrument_name="graphiti_api_cost_per_request",
                    aggregation=ExplicitBucketHistogramAggregation(boundaries=cost_buckets)
                ),
                View(
                    instrument_name="graphiti_api_input_cost_per_request",
                    aggregation=ExplicitBucketHistogramAggregation(boundaries=cost_buckets)
                ),
                View(
                    instrument_name="graphiti_api_output_cost_per_request",
                    aggregation=ExplicitBucketHistogramAggregation(boundaries=cost_buckets)
                ),
                # Cache savings histogram views
                View(
                    instrument_name="graphiti_cache_cost_saved_per_request",
                    aggregation=ExplicitBucketHistogramAggregation(boundaries=cost_buckets)
                ),
                View(
                    instrument_name="graphiti_cache_tokens_saved_per_request",
                    aggregation=ExplicitBucketHistogramAggregation(boundaries=token_buckets)
                ),
                # Token histogram views
                View(
                    instrument_name="graphiti_prompt_tokens_per_request",
                    aggregation=ExplicitBucketHistogramAggregation(boundaries=token_buckets)
                ),
                View(
                    instrument_name="graphiti_completion_tokens_per_request",
                    aggregation=ExplicitBucketHistogramAggregation(boundaries=token_buckets)
                ),
                View(
                    instrument_name="graphiti_total_tokens_per_request",
                    aggregation=ExplicitBucketHistogramAggregation(boundaries=token_buckets)
                ),
                # Duration histogram view
                View(
                    instrument_name="graphiti_llm_request_duration_seconds",
                    aggregation=ExplicitBucketHistogramAggregation(boundaries=duration_buckets)
                ),
            ]

            # Set up meter provider with custom views
            provider = MeterProvider(metric_readers=[reader], views=views)
            metrics.set_meter_provider(provider)

            # Get meter for cache metrics
            self._meter = metrics.get_meter("graphiti.cache", version="1.0.0")

            # Create metrics
            self._create_counters()
            self._create_gauges()
            self._create_histograms()

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
            # Per-model metrics (with model label for distribution)
            "cache_hits_total": self._meter.create_counter(
                name="graphiti_cache_hits_total",
                description="Total number of cache hits since server start (per model)",
                unit="1"
            ),
            "cache_misses_total": self._meter.create_counter(
                name="graphiti_cache_misses_total",
                description="Total number of cache misses since server start (per model)",
                unit="1"
            ),
            "cache_tokens_saved_total": self._meter.create_counter(
                name="graphiti_cache_tokens_saved_total",
                description="Total tokens saved via caching since server start (per model)",
                unit="1"
            ),
            "cache_cost_saved_total": self._meter.create_counter(
                name="graphiti_cache_cost_saved_total",
                description="Total cost savings in USD from caching since server start (per model)",
                unit="USD"
            ),
            "cache_requests_total": self._meter.create_counter(
                name="graphiti_cache_requests_total",
                description="Total API requests with cache metrics since server start (per model)",
                unit="1"
            ),
            # Aggregate metrics (without model label for totals across all models)
            "cache_hits_all_models": self._meter.create_counter(
                name="graphiti_cache_hits_all_models_total",
                description="Total cache hits across all models combined",
                unit="1"
            ),
            "cache_misses_all_models": self._meter.create_counter(
                name="graphiti_cache_misses_all_models_total",
                description="Total cache misses across all models combined",
                unit="1"
            ),
            "cache_tokens_saved_all_models": self._meter.create_counter(
                name="graphiti_cache_tokens_saved_all_models_total",
                description="Total tokens saved across all models combined",
                unit="1"
            ),
            "cache_cost_saved_all_models": self._meter.create_counter(
                name="graphiti_cache_cost_saved_all_models_total",
                description="Total cost savings across all models combined",
                unit="USD"
            ),
            "cache_requests_all_models": self._meter.create_counter(
                name="graphiti_cache_requests_all_models_total",
                description="Total API requests across all models combined",
                unit="1"
            ),
            # === Token Usage Metrics (per-model) ===
            "prompt_tokens_total": self._meter.create_counter(
                name="graphiti_prompt_tokens_total",
                description="Total prompt/input tokens used since server start (per model)",
                unit="1"
            ),
            "completion_tokens_total": self._meter.create_counter(
                name="graphiti_completion_tokens_total",
                description="Total completion/output tokens used since server start (per model)",
                unit="1"
            ),
            "total_tokens_total": self._meter.create_counter(
                name="graphiti_total_tokens_total",
                description="Total tokens (prompt + completion) used since server start (per model)",
                unit="1"
            ),
            # === Token Usage Metrics (aggregate) ===
            "prompt_tokens_all_models": self._meter.create_counter(
                name="graphiti_prompt_tokens_all_models_total",
                description="Total prompt tokens across all models combined",
                unit="1"
            ),
            "completion_tokens_all_models": self._meter.create_counter(
                name="graphiti_completion_tokens_all_models_total",
                description="Total completion tokens across all models combined",
                unit="1"
            ),
            "total_tokens_all_models": self._meter.create_counter(
                name="graphiti_total_tokens_all_models_total",
                description="Total tokens across all models combined",
                unit="1"
            ),
            # === Cost Metrics (per-model) ===
            "api_cost_total": self._meter.create_counter(
                name="graphiti_api_cost_total",
                description="Total API cost in USD since server start (per model)",
                unit="USD"
            ),
            "api_input_cost_total": self._meter.create_counter(
                name="graphiti_api_input_cost_total",
                description="Total input/prompt cost in USD since server start (per model)",
                unit="USD"
            ),
            "api_output_cost_total": self._meter.create_counter(
                name="graphiti_api_output_cost_total",
                description="Total output/completion cost in USD since server start (per model)",
                unit="USD"
            ),
            # === Cost Metrics (aggregate) ===
            "api_cost_all_models": self._meter.create_counter(
                name="graphiti_api_cost_all_models_total",
                description="Total API cost across all models combined",
                unit="USD"
            ),
            "api_input_cost_all_models": self._meter.create_counter(
                name="graphiti_api_input_cost_all_models_total",
                description="Total input cost across all models combined",
                unit="USD"
            ),
            "api_output_cost_all_models": self._meter.create_counter(
                name="graphiti_api_output_cost_all_models_total",
                description="Total output cost across all models combined",
                unit="USD"
            ),
            # === Error Metrics ===
            "llm_errors_total": self._meter.create_counter(
                name="graphiti_llm_errors_total",
                description="Total LLM API errors by type (per model)",
                unit="1"
            ),
            "llm_errors_all_models": self._meter.create_counter(
                name="graphiti_llm_errors_all_models_total",
                description="Total LLM API errors across all models",
                unit="1"
            ),
            # === Throughput Metrics ===
            "episodes_processed_total": self._meter.create_counter(
                name="graphiti_episodes_processed_total",
                description="Total episodes processed (per group_id)",
                unit="1"
            ),
            "episodes_processed_all_groups": self._meter.create_counter(
                name="graphiti_episodes_processed_all_groups_total",
                description="Total episodes processed across all groups",
                unit="1"
            ),
            # === Cache Write Metrics ===
            "cache_write_tokens_total": self._meter.create_counter(
                name="graphiti_cache_write_tokens_total",
                description="Total tokens written to cache (per model)",
                unit="1"
            ),
            "cache_write_tokens_all_models": self._meter.create_counter(
                name="graphiti_cache_write_tokens_all_models_total",
                description="Total tokens written to cache across all models",
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
            """Return cache enabled status (1=enabled, 0=disabled).

            Checks the PROMPT_CACHE_ENABLED env var (prefix stripped in container),
            NOT the metrics exporter enabled status.
            """
            cache_enabled = os.getenv("PROMPT_CACHE_ENABLED", "false").lower() == "true"
            return [metrics.Observation(1 if cache_enabled else 0)]

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

    def _create_histograms(self) -> None:
        """
        Create histogram metrics for per-request distributions.

        Histograms track the distribution of values, enabling percentile calculations
        (p50, p95, p99) for token usage and costs per request.
        """
        if not self._meter:
            return

        self._histograms = {
            # === Token Histograms (per request) ===
            "prompt_tokens_per_request": self._meter.create_histogram(
                name="graphiti_prompt_tokens_per_request",
                description="Distribution of prompt/input tokens per request",
                unit="1"
            ),
            "completion_tokens_per_request": self._meter.create_histogram(
                name="graphiti_completion_tokens_per_request",
                description="Distribution of completion/output tokens per request",
                unit="1"
            ),
            "total_tokens_per_request": self._meter.create_histogram(
                name="graphiti_total_tokens_per_request",
                description="Distribution of total tokens per request",
                unit="1"
            ),
            # === Cost Histograms (per request) ===
            "api_cost_per_request": self._meter.create_histogram(
                name="graphiti_api_cost_per_request",
                description="Distribution of total API cost per request in USD",
                unit="USD"
            ),
            "api_input_cost_per_request": self._meter.create_histogram(
                name="graphiti_api_input_cost_per_request",
                description="Distribution of input/prompt cost per request in USD",
                unit="USD"
            ),
            "api_output_cost_per_request": self._meter.create_histogram(
                name="graphiti_api_output_cost_per_request",
                description="Distribution of output/completion cost per request in USD",
                unit="USD"
            ),
            # === Cache Savings Histograms (per request, on cache hit) ===
            "cache_tokens_saved_per_request": self._meter.create_histogram(
                name="graphiti_cache_tokens_saved_per_request",
                description="Distribution of tokens saved per cache hit request",
                unit="1"
            ),
            "cache_cost_saved_per_request": self._meter.create_histogram(
                name="graphiti_cache_cost_saved_per_request",
                description="Distribution of cost saved per cache hit request in USD",
                unit="USD"
            ),
            # === Duration Histogram (per request) ===
            "llm_request_duration": self._meter.create_histogram(
                name="graphiti_llm_request_duration_seconds",
                description="Distribution of LLM request latency in seconds",
                unit="s"
            )
        }

    def record_cache_hit(self, model: str, tokens_saved: int, cost_saved: float) -> None:
        """
        Record a cache hit event.

        Metrics are recorded twice:
        1. With model label for per-model distribution
        2. Without label for total across all models

        Also records histogram data for per-request distribution analysis.

        Args:
            model: Gemini model identifier
            tokens_saved: Number of tokens served from cache
            cost_saved: Cost savings in USD
        """
        if not self.enabled or not self._counters:
            return

        try:
            # Record per-model metrics (with model label)
            attributes = {"model": model}
            self._counters["cache_hits_total"].add(1, attributes)
            self._counters["cache_tokens_saved_total"].add(tokens_saved, attributes)
            self._counters["cache_cost_saved_total"].add(cost_saved, attributes)
            self._counters["cache_requests_total"].add(1, attributes)

            # Record aggregate metrics (no label - totals across all models)
            self._counters["cache_hits_all_models"].add(1)
            self._counters["cache_tokens_saved_all_models"].add(tokens_saved)
            self._counters["cache_cost_saved_all_models"].add(cost_saved)
            self._counters["cache_requests_all_models"].add(1)

            # Record histogram metrics (per-request distributions with model label)
            if self._histograms:
                self._histograms["cache_tokens_saved_per_request"].record(tokens_saved, attributes)
                self._histograms["cache_cost_saved_per_request"].record(cost_saved, attributes)

            # Update session metrics for hit rate calculation
            self._session_metrics["hits"] += 1
            self._session_metrics["requests"] += 1

        except Exception as e:
            logger.error(f"Failed to record cache hit: {e}")

    def record_cache_miss(self, model: str) -> None:
        """
        Record a cache miss event.

        Metrics are recorded twice:
        1. With model label for per-model distribution
        2. Without label for total across all models

        Args:
            model: Gemini model identifier
        """
        if not self.enabled or not self._counters:
            return

        try:
            # Record per-model metrics (with model label)
            attributes = {"model": model}
            self._counters["cache_misses_total"].add(1, attributes)
            self._counters["cache_requests_total"].add(1, attributes)

            # Record aggregate metrics (no label - totals across all models)
            self._counters["cache_misses_all_models"].add(1)
            self._counters["cache_requests_all_models"].add(1)

            # Update session metrics for hit rate calculation
            self._session_metrics["misses"] += 1
            self._session_metrics["requests"] += 1

        except Exception as e:
            logger.error(f"Failed to record cache miss: {e}")

    def record_request_metrics(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        total_cost: float,
        input_cost: float = 0.0,
        output_cost: float = 0.0
    ) -> None:
        """
        Record token usage and cost metrics for an API request.

        This method records general metrics for ALL requests, independent of cache status.
        Metrics are recorded twice:
        1. With model label for per-model distribution
        2. Without label for total across all models

        Args:
            model: Model identifier (e.g., 'google/gemini-2.0-flash-001')
            prompt_tokens: Number of input/prompt tokens
            completion_tokens: Number of output/completion tokens
            total_tokens: Total tokens (prompt + completion)
            total_cost: Total API cost in USD
            input_cost: Input/prompt cost in USD (optional, for breakdown)
            output_cost: Output/completion cost in USD (optional, for breakdown)
        """
        if not self.enabled or not self._counters:
            return

        try:
            # Record per-model metrics (with model label)
            attributes = {"model": model}
            self._counters["prompt_tokens_total"].add(prompt_tokens, attributes)
            self._counters["completion_tokens_total"].add(completion_tokens, attributes)
            self._counters["total_tokens_total"].add(total_tokens, attributes)
            self._counters["api_cost_total"].add(total_cost, attributes)
            if input_cost > 0:
                self._counters["api_input_cost_total"].add(input_cost, attributes)
            if output_cost > 0:
                self._counters["api_output_cost_total"].add(output_cost, attributes)

            # Record aggregate metrics (no label - totals across all models)
            self._counters["prompt_tokens_all_models"].add(prompt_tokens)
            self._counters["completion_tokens_all_models"].add(completion_tokens)
            self._counters["total_tokens_all_models"].add(total_tokens)
            self._counters["api_cost_all_models"].add(total_cost)
            if input_cost > 0:
                self._counters["api_input_cost_all_models"].add(input_cost)
            if output_cost > 0:
                self._counters["api_output_cost_all_models"].add(output_cost)

            # Record histogram metrics (per-request distributions with model label)
            if self._histograms:
                self._histograms["prompt_tokens_per_request"].record(prompt_tokens, attributes)
                self._histograms["completion_tokens_per_request"].record(completion_tokens, attributes)
                self._histograms["total_tokens_per_request"].record(total_tokens, attributes)
                self._histograms["api_cost_per_request"].record(total_cost, attributes)
                if input_cost > 0:
                    self._histograms["api_input_cost_per_request"].record(input_cost, attributes)
                if output_cost > 0:
                    self._histograms["api_output_cost_per_request"].record(output_cost, attributes)

            logger.debug(
                f"Recorded request metrics: model={model}, "
                f"tokens={prompt_tokens}+{completion_tokens}={total_tokens}, "
                f"cost=${total_cost:.6f}"
            )

        except Exception as e:
            logger.error(f"Failed to record request metrics: {e}")

    def record_request_duration(self, model: str, duration_seconds: float) -> None:
        """
        Record the duration of an LLM API request.

        Args:
            model: Model identifier (e.g., 'google/gemini-2.5-flash')
            duration_seconds: Request duration in seconds
        """
        if not self.enabled or not self._histograms:
            return

        try:
            attributes = {"model": model}
            self._histograms["llm_request_duration"].record(duration_seconds, attributes)
            logger.debug(f"Recorded request duration: model={model}, duration={duration_seconds:.3f}s")
        except Exception as e:
            logger.error(f"Failed to record request duration: {e}")

    def record_error(self, model: str, error_type: str) -> None:
        """
        Record an LLM API error.

        Args:
            model: Model identifier (e.g., 'google/gemini-2.5-flash')
            error_type: Error type/category (e.g., 'rate_limit', 'timeout', 'invalid_response')
        """
        if not self.enabled or not self._counters:
            return

        try:
            # Record per-model with error type
            attributes = {"model": model, "error_type": error_type}
            self._counters["llm_errors_total"].add(1, attributes)

            # Record aggregate
            self._counters["llm_errors_all_models"].add(1)

            logger.debug(f"Recorded LLM error: model={model}, type={error_type}")
        except Exception as e:
            logger.error(f"Failed to record error metric: {e}")

    def record_episode_processed(self, group_id: str) -> None:
        """
        Record an episode being processed by Graphiti.

        Args:
            group_id: The group/namespace for the episode
        """
        if not self.enabled or not self._counters:
            return

        try:
            # Record per-group
            attributes = {"group_id": group_id}
            self._counters["episodes_processed_total"].add(1, attributes)

            # Record aggregate
            self._counters["episodes_processed_all_groups"].add(1)

            logger.debug(f"Recorded episode processed: group_id={group_id}")
        except Exception as e:
            logger.error(f"Failed to record episode metric: {e}")

    def record_cache_write(self, model: str, tokens_written: int) -> None:
        """
        Record tokens written to cache (cache creation).

        Args:
            model: Model identifier (e.g., 'google/gemini-2.5-flash')
            tokens_written: Number of tokens written to cache
        """
        if not self.enabled or not self._counters:
            return

        try:
            # Record per-model
            attributes = {"model": model}
            self._counters["cache_write_tokens_total"].add(tokens_written, attributes)

            # Record aggregate
            self._counters["cache_write_tokens_all_models"].add(tokens_written)

            logger.debug(f"Recorded cache write: model={model}, tokens={tokens_written}")
        except Exception as e:
            logger.error(f"Failed to record cache write metric: {e}")


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
