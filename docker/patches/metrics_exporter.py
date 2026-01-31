"""
Metrics Exporter - OpenTelemetry/Prometheus Integration

Features:
- 006-gemini-prompt-caching: Cache statistics via Prometheus metrics endpoint
- 009-memory-decay-scoring: Decay, lifecycle, and maintenance metrics
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
                # === Decay Metrics Views (Feature 009) ===
                # Maintenance duration: up to 10 minutes per spec
                View(
                    instrument_name="knowledge_maintenance_duration_seconds",
                    aggregation=ExplicitBucketHistogramAggregation(
                        boundaries=[1, 5, 30, 60, 120, 300, 600]
                    )
                ),
                # Classification latency: LLM response time
                View(
                    instrument_name="knowledge_classification_latency_seconds",
                    aggregation=ExplicitBucketHistogramAggregation(
                        boundaries=[0.1, 0.5, 1, 2, 5]
                    )
                ),
                # Weighted search latency: scoring overhead
                View(
                    instrument_name="knowledge_search_weighted_latency_seconds",
                    aggregation=ExplicitBucketHistogramAggregation(
                        boundaries=[0.01, 0.05, 0.1, 0.5, 1]
                    )
                ),
                # Decay score distribution: 0-1 range in 0.1 increments
                View(
                    instrument_name="knowledge_decay_score",
                    aggregation=ExplicitBucketHistogramAggregation(
                        boundaries=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
                    )
                ),
                # Importance score distribution: 1-5 integer scale
                View(
                    instrument_name="knowledge_importance_score",
                    aggregation=ExplicitBucketHistogramAggregation(
                        boundaries=[1, 2, 3, 4, 5]
                    )
                ),
                # Stability score distribution: 1-5 integer scale
                View(
                    instrument_name="knowledge_stability_score",
                    aggregation=ExplicitBucketHistogramAggregation(
                        boundaries=[1, 2, 3, 4, 5]
                    )
                ),
                # === Additional Observability Metrics ===
                # Search query latency: sub-second to multi-second
                View(
                    instrument_name="knowledge_search_query_latency_seconds",
                    aggregation=ExplicitBucketHistogramAggregation(
                        boundaries=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
                    )
                ),
                # Days since last access: 1 day to 1+ years
                View(
                    instrument_name="knowledge_days_since_last_access",
                    aggregation=ExplicitBucketHistogramAggregation(
                        boundaries=[1, 7, 30, 90, 180, 365, 730, 1095]  # 1d, 1w, 1m, 3m, 6m, 1y, 2y, 3y
                    )
                ),
                # Search result count: 0 to 100+ results
                View(
                    instrument_name="knowledge_search_result_count",
                    aggregation=ExplicitBucketHistogramAggregation(
                        boundaries=[0, 1, 5, 10, 25, 50, 100, 200]
                    )
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
                unit="1",
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


# =============================================================================
# Decay Metrics Exporter (Feature 009-memory-decay-scoring)
# =============================================================================


class DecayMetricsExporter:
    """
    Manages OpenTelemetry/Prometheus metrics for memory decay scoring.

    Provides counters, gauges, and histograms for tracking:
    - Maintenance operations (runs, durations, updates)
    - Lifecycle state transitions
    - Classification operations
    - Memory health metrics
    """

    def __init__(self, meter: Optional[Any] = None):
        """
        Initialize decay metrics exporter.

        Args:
            meter: OpenTelemetry meter to use (shares with CacheMetricsExporter)
        """
        self._meter = meter
        self._counters: Dict[str, Any] = {}
        self._gauges: Dict[str, Any] = {}
        self._histograms: Dict[str, Any] = {}
        self._state_counts: Dict[str, int] = {
            "ACTIVE": 0,
            "DORMANT": 0,
            "ARCHIVED": 0,
            "EXPIRED": 0,
            "SOFT_DELETED": 0,
            "PERMANENT": 0,
        }
        self._importance_counts: Dict[str, int] = {
            "TRIVIAL": 0,    # Importance level 1
            "LOW": 0,        # Importance level 2
            "MODERATE": 0,   # Importance level 3
            "HIGH": 0,       # Importance level 4
            "CORE": 0,       # Importance level 5
        }
        self._stability_counts: Dict[str, int] = {
            "VOLATILE": 0,   # Stability level 1
            "LOW": 0,        # Stability level 2
            "MODERATE": 0,   # Stability level 3
            "HIGH": 0,       # Stability level 4
            "PERMANENT": 0,  # Stability level 5
        }
        self._averages: Dict[str, float] = {
            "decay_score": 0.0,
            "importance": 3.0,
            "stability": 3.0,
        }
        self._total_memories: int = 0
        self._orphan_entities: int = 0  # Track entities with no relationships
        self._age_distribution: Dict[str, int] = {
            "UNDER_7_DAYS": 0,
            "DAYS_7_TO_30": 0,
            "DAYS_30_TO_90": 0,
            "DAYS_90_TO_180": 0,
            "DAYS_180_TO_365": 0,
            "OVER_365_DAYS": 0,
        }

        if self._meter:
            self._create_counters()
            self._create_gauges()
            self._create_histograms()
            self._preinitialize_known_labels()

    def _create_counters(self) -> None:
        """Create counter metrics for decay operations."""
        if not self._meter:
            return

        self._counters = {
            # Maintenance metrics
            "maintenance_runs": self._meter.create_counter(
                name="knowledge_decay_maintenance_runs_total",
                description="Total maintenance runs by status",
                unit="1"
            ),
            "scores_updated": self._meter.create_counter(
                name="knowledge_decay_scores_updated_total",
                description="Total decay scores recalculated",
                unit="1"
            ),
            "memories_purged": self._meter.create_counter(
                name="knowledge_memories_purged_total",
                description="Soft-deleted memories permanently removed",
                unit="1"
            ),
            # Lifecycle metrics
            "lifecycle_transitions": self._meter.create_counter(
                name="knowledge_lifecycle_transitions_total",
                description="State transitions by from/to state",
                unit="1"
            ),
            "reactivations": self._meter.create_counter(
                name="knowledge_reactivations_total",
                description="Memories reactivated from DORMANT/ARCHIVED to ACTIVE",
                unit="1"
            ),
            # Classification metrics
            "classification_requests": self._meter.create_counter(
                name="knowledge_classification_requests_total",
                description="LLM classification attempts by status",
                unit="1"
            ),
            # Search metrics
            "weighted_searches": self._meter.create_counter(
                name="knowledge_weighted_searches_total",
                description="Weighted search operations",
                unit="1"
            ),
            # === Additional Observability Counters ===
            "memory_access": self._meter.create_counter(
                name="knowledge_memory_access_total",
                description="Total memory access operations",
                unit="1"
            ),
            "memories_created": self._meter.create_counter(
                name="knowledge_memories_created_total",
                description="Total memories created (growth tracking)",
                unit="1"
            ),
            "zero_result_searches": self._meter.create_counter(
                name="knowledge_search_zero_results_total",
                description="Searches returning zero results",
                unit="1"
            ),
            # === Access Pattern Counters (P3) ===
            "access_by_importance": self._meter.create_counter(
                name="knowledge_access_by_importance_total",
                description="Memory accesses by importance level",
                unit="1"
            ),
            "access_by_state": self._meter.create_counter(
                name="knowledge_access_by_state_total",
                description="Memory accesses by lifecycle state at access time",
                unit="1"
            ),
        }

    def _create_gauges(self) -> None:
        """Create gauge metrics for current state values."""
        if not self._meter:
            return

        def get_state_count(state: str):
            """Factory for state count callbacks."""
            def callback(_options):
                return [metrics.Observation(self._state_counts.get(state, 0), {"state": state})]
            return callback

        def get_importance_count(level: str):
            """Factory for importance level count callbacks."""
            def callback(_options):
                return [metrics.Observation(self._importance_counts.get(level, 0), {"level": level})]
            return callback

        def get_stability_count(level: str):
            """Factory for stability level count callbacks."""
            def callback(_options):
                return [metrics.Observation(self._stability_counts.get(level, 0), {"level": level})]
            return callback

        def get_decay_avg(_options):
            return [metrics.Observation(self._averages["decay_score"])]

        def get_importance_avg(_options):
            return [metrics.Observation(self._averages["importance"])]

        def get_stability_avg(_options):
            return [metrics.Observation(self._averages["stability"])]

        def get_total(_options):
            return [metrics.Observation(self._total_memories)]

        def get_orphan_count(_options):
            return [metrics.Observation(self._orphan_entities)]

        def get_age_count(bucket: str):
            """Factory for age bucket count callbacks."""
            def callback(_options):
                return [metrics.Observation(self._age_distribution.get(bucket, 0), {"bucket": bucket})]
            return callback

        self._gauges = {
            "memories_by_state": self._meter.create_observable_gauge(
                name="knowledge_memories_by_state",
                description="Current memory count per lifecycle state",
                unit="1",
                callbacks=[
                    get_state_count("ACTIVE"),
                    get_state_count("DORMANT"),
                    get_state_count("ARCHIVED"),
                    get_state_count("EXPIRED"),
                    get_state_count("SOFT_DELETED"),
                    get_state_count("PERMANENT"),
                ]
            ),
            "memories_by_importance": self._meter.create_observable_gauge(
                name="knowledge_memories_by_importance",
                description="Current memory count per importance level",
                unit="1",
                callbacks=[
                    get_importance_count("TRIVIAL"),
                    get_importance_count("LOW"),
                    get_importance_count("MODERATE"),
                    get_importance_count("HIGH"),
                    get_importance_count("CORE"),
                ]
            ),
            "memories_by_stability": self._meter.create_observable_gauge(
                name="knowledge_memories_by_stability",
                description="Current memory count per stability level",
                unit="1",
                callbacks=[
                    get_stability_count("VOLATILE"),
                    get_stability_count("LOW"),
                    get_stability_count("MODERATE"),
                    get_stability_count("HIGH"),
                    get_stability_count("PERMANENT"),
                ]
            ),
            "decay_score_avg": self._meter.create_observable_gauge(
                name="knowledge_decay_score_avg",
                description="Average decay score across non-permanent memories",
                unit="1",
                callbacks=[get_decay_avg]
            ),
            "importance_avg": self._meter.create_observable_gauge(
                name="knowledge_importance_avg",
                description="Average importance score",
                unit="1",
                callbacks=[get_importance_avg]
            ),
            "stability_avg": self._meter.create_observable_gauge(
                name="knowledge_stability_avg",
                description="Average stability score",
                unit="1",
                callbacks=[get_stability_avg]
            ),
            "memories_total": self._meter.create_observable_gauge(
                name="knowledge_memories_total",
                description="Total memory count excluding soft-deleted",
                unit="1",
                callbacks=[get_total]
            ),
            "orphan_entities": self._meter.create_observable_gauge(
                name="knowledge_orphan_entities",
                description="Entities with no relationships (disconnected from graph)",
                unit="1",
                callbacks=[get_orphan_count]
            ),
            "memories_by_age": self._meter.create_observable_gauge(
                name="knowledge_memories_by_age",
                description="Memory count by age bucket (aligned with lifecycle thresholds)",
                unit="1",
                callbacks=[
                    get_age_count("UNDER_7_DAYS"),
                    get_age_count("DAYS_7_TO_30"),
                    get_age_count("DAYS_30_TO_90"),
                    get_age_count("DAYS_90_TO_180"),
                    get_age_count("DAYS_180_TO_365"),
                    get_age_count("OVER_365_DAYS"),
                ]
            ),
        }

    def _create_histograms(self) -> None:
        """Create histogram metrics for duration distributions."""
        if not self._meter:
            return

        self._histograms = {
            "maintenance_duration": self._meter.create_histogram(
                name="knowledge_maintenance_duration_seconds",
                description="Maintenance run duration in seconds",
                unit="s"
            ),
            "classification_latency": self._meter.create_histogram(
                name="knowledge_classification_latency_seconds",
                description="LLM classification response time in seconds",
                unit="s"
            ),
            "weighted_search_latency": self._meter.create_histogram(
                name="knowledge_search_weighted_latency_seconds",
                description="Weighted search scoring overhead in seconds",
                unit="s"
            ),
            "decay_score": self._meter.create_histogram(
                name="knowledge_decay_score",
                description="Decay score distribution (0=healthy, 1=expired)",
                unit="1"
            ),
            "importance_score": self._meter.create_histogram(
                name="knowledge_importance_score",
                description="Importance score distribution (1=trivial, 5=core)",
                unit="1"
            ),
            "stability_score": self._meter.create_histogram(
                name="knowledge_stability_score",
                description="Stability score distribution (1=volatile, 5=permanent)",
                unit="1"
            ),
            # === Additional Observability Histograms ===
            "search_query_latency": self._meter.create_histogram(
                name="knowledge_search_query_latency_seconds",
                description="Search query execution time in seconds",
                unit="s"
            ),
            "days_since_last_access": self._meter.create_histogram(
                name="knowledge_days_since_last_access",
                description="Days since last memory access (age distribution)",
                unit="d"
            ),
            "search_result_count": self._meter.create_histogram(
                name="knowledge_search_result_count",
                description="Number of results returned per search",
                unit="1"
            ),
        }

    def _preinitialize_known_labels(self) -> None:
        """
        Pre-initialize counters with known label values to 0.
        
        This ensures counter time series appear in /metrics from startup,
        following Prometheus best practices to avoid missing metrics.
        See: https://prometheus.io/docs/practices/instrumentation/#avoid-missing-metrics
        
        WARNING: Only use for bounded, finite label sets. Do NOT add
        high-cardinality labels (model, group_id, user_id) here.
        
        Total: 25 time series (5 importance + 6 lifecycle + 2 maintenance + 
                                3 classification + 2 reactivation + 7 transitions)
        """
        if not self._counters:
            return

        try:
            # Importance levels (5 series - matching ImportanceLevel enum)
            # TRIVIAL=1, LOW=2, MODERATE=3, HIGH=4, CORE=5
            importance_levels = ["TRIVIAL", "LOW", "MODERATE", "HIGH", "CORE"]
            for level in importance_levels:
                self._counters["access_by_importance"].add(0, {"level": level})

            # Lifecycle states (5 series - matching LifecycleState enum)
            lifecycle_states = ["ACTIVE", "DORMANT", "ARCHIVED", "EXPIRED", "SOFT_DELETED"]
            for state in lifecycle_states:
                self._counters["access_by_state"].add(0, {"state": state})
            
            # Maintenance status (2 series)
            for status in ["success", "failure"]:
                self._counters["maintenance_runs"].add(0, {"status": status})
            
            # Classification status (3 series)
            for status in ["success", "failure", "fallback"]:
                self._counters["classification_requests"].add(0, {"status": status})
            
            # Reactivation sources (2 series)
            for from_state in ["DORMANT", "ARCHIVED"]:
                self._counters["reactivations"].add(0, {"from_state": from_state})
            
            # Valid lifecycle transitions only (7 series)
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
                self._counters["lifecycle_transitions"].add(0, {
                    "from_state": from_state,
                    "to_state": to_state
                })
            
            logger.info("Pre-initialized decay metrics with known label values")
        except Exception as e:
            logger.error(f"Failed to pre-initialize counter labels: {e}")

    # === Recording Methods ===

    def record_maintenance_run(self, status: str, duration_seconds: float, scores_updated: int = 0) -> None:
        """
        Record a maintenance run completion.

        Args:
            status: 'success' or 'failure'
            duration_seconds: How long the maintenance took
            scores_updated: Number of decay scores recalculated
        """
        if not self._counters:
            return

        try:
            self._counters["maintenance_runs"].add(1, {"status": status})
            if scores_updated > 0:
                self._counters["scores_updated"].add(scores_updated)
            if self._histograms:
                self._histograms["maintenance_duration"].record(duration_seconds)
            logger.debug(f"Recorded maintenance run: status={status}, duration={duration_seconds:.2f}s, scores={scores_updated}")
        except Exception as e:
            logger.error(f"Failed to record maintenance run: {e}")

    def record_lifecycle_transition(self, from_state: str, to_state: str, count: int = 1) -> None:
        """
        Record lifecycle state transitions.

        Args:
            from_state: Source state (e.g., 'ACTIVE')
            to_state: Target state (e.g., 'DORMANT')
            count: Number of transitions (default 1)
        """
        if not self._counters:
            return

        try:
            self._counters["lifecycle_transitions"].add(
                count,
                {"from_state": from_state, "to_state": to_state}
            )
            logger.debug(f"Recorded transitions: {from_state} → {to_state} x{count}")
        except Exception as e:
            logger.error(f"Failed to record lifecycle transition: {e}")

    def record_reactivation(self, from_state: str, count: int = 1) -> None:
        """
        Record memory reactivation (DORMANT/ARCHIVED → ACTIVE).

        Args:
            from_state: Source state ('DORMANT' or 'ARCHIVED')
            count: Number of reactivations (default 1)
        """
        if not self._counters:
            return

        try:
            self._counters["reactivations"].add(count, {"from_state": from_state})
            logger.debug(f"Recorded reactivation: {from_state} → ACTIVE x{count}")
        except Exception as e:
            logger.error(f"Failed to record reactivation: {e}")

    def record_classification(self, status: str, latency_seconds: float = 0.0) -> None:
        """
        Record a classification operation.

        Args:
            status: 'success', 'failure', or 'fallback'
            latency_seconds: LLM response time
        """
        if not self._counters:
            return

        try:
            self._counters["classification_requests"].add(1, {"status": status})
            if latency_seconds > 0 and self._histograms:
                self._histograms["classification_latency"].record(latency_seconds)
            logger.debug(f"Recorded classification: status={status}, latency={latency_seconds:.3f}s")
        except Exception as e:
            logger.error(f"Failed to record classification: {e}")

    def record_memories_purged(self, count: int) -> None:
        """
        Record soft-deleted memories permanently removed.

        Args:
            count: Number of memories purged
        """
        if not self._counters:
            return

        try:
            self._counters["memories_purged"].add(count)
            logger.debug(f"Recorded memories purged: {count}")
        except Exception as e:
            logger.error(f"Failed to record memories purged: {e}")

    def record_weighted_search(self, latency_seconds: float) -> None:
        """
        Record a weighted search operation.

        Args:
            latency_seconds: Scoring overhead time
        """
        if not self._counters:
            return

        try:
            self._counters["weighted_searches"].add(1)
            if latency_seconds > 0 and self._histograms:
                self._histograms["weighted_search_latency"].record(latency_seconds)
            logger.debug(f"Recorded weighted search: latency={latency_seconds:.4f}s")
        except Exception as e:
            logger.error(f"Failed to record weighted search: {e}")

    def update_state_counts(self, counts: Dict[str, int]) -> None:
        """
        Update current memory counts by state.

        Args:
            counts: Dict mapping state names to counts
        """
        for state, count in counts.items():
            if state in self._state_counts:
                self._state_counts[state] = count

    def update_importance_counts(self, counts: Dict[str, int]) -> None:
        """
        Update current memory counts by importance level.

        Args:
            counts: Dict mapping importance level names to counts (TRIVIAL/LOW/MODERATE/HIGH/CORE)
        """
        for level, count in counts.items():
            if level in self._importance_counts:
                self._importance_counts[level] = count

    def update_stability_counts(self, counts: Dict[str, int]) -> None:
        """
        Update stability level counts from health check.

        Args:
            counts: Dict mapping stability level names to counts (VOLATILE/LOW/MODERATE/HIGH/PERMANENT)
        """
        for level, count in counts.items():
            if level in self._stability_counts:
                self._stability_counts[level] = count

    def update_averages(self, decay: float, importance: float, stability: float, total: int) -> None:
        """
        Update average metrics from health check.

        Args:
            decay: Average decay score
            importance: Average importance
            stability: Average stability
            total: Total memory count
        """
        self._averages["decay_score"] = decay
        self._averages["importance"] = importance
        self._averages["stability"] = stability
        self._total_memories = total

    def record_decay_score(self, score: float) -> None:
        """
        Record a decay score for distribution tracking.

        Args:
            score: Decay score value (0-1 range)
        """
        if not self._histograms:
            return
        try:
            self._histograms["decay_score"].record(score)
            logger.debug(f"Recorded decay score: {score:.3f}")
        except Exception as e:
            logger.error(f"Failed to record decay score: {e}")

    def record_importance_score(self, score: int) -> None:
        """
        Record an importance score for distribution tracking.

        Args:
            score: Importance score value (1-5 range)
        """
        if not self._histograms:
            return
        try:
            self._histograms["importance_score"].record(score)
        except Exception as e:
            logger.error(f"Failed to record importance score: {e}")

    def record_stability_score(self, score: int) -> None:
        """
        Record a stability score for distribution tracking.

        Args:
            score: Stability score value (1-5 range)
        """
        if not self._histograms:
            return
        try:
            self._histograms["stability_score"].record(score)
        except Exception as e:
            logger.error(f"Failed to record stability score: {e}")

    def record_memory_access(self) -> None:
        """Record a memory access operation."""
        if not self._counters:
            return
        try:
            self._counters["memory_access"].add(1)
            logger.debug("Recorded memory access")
        except Exception as e:
            logger.error(f"Failed to record memory access: {e}")

    def record_memory_created(self, count: int = 1) -> None:
        """
        Record memories being created.

        Args:
            count: Number of memories created (default 1)
        """
        if not self._counters:
            return
        try:
            self._counters["memories_created"].add(count)
            logger.debug(f"Recorded {count} memories created")
        except Exception as e:
            logger.error(f"Failed to record memories created: {e}")

    def record_search_execution(
        self,
        query_latency_seconds: float = 0.0,
        result_count: int = 0,
        is_zero_result: bool = False
    ) -> None:
        """
        Record a search operation.

        Args:
            query_latency_seconds: Time to execute search query
            result_count: Number of results returned
            is_zero_result: Whether the search returned no results
        """
        try:
            # Record search (weighted search counter)
            if self._counters:
                self._counters["weighted_searches"].add(1)

            # Record histograms if available
            if self._histograms:
                if query_latency_seconds > 0:
                    self._histograms["search_query_latency"].record(query_latency_seconds)
                if result_count >= 0:
                    self._histograms["search_result_count"].record(result_count)

            # Record zero result counter
            if is_zero_result and self._counters:
                self._counters["zero_result_searches"].add(1)

            logger.debug(
                f"Recorded search: latency={query_latency_seconds:.3f}s, "
                f"results={result_count}, zero={is_zero_result}"
            )
        except Exception as e:
            logger.error(f"Failed to record search metrics: {e}")

    def update_orphan_count(self, count: int) -> None:
        """
        Update the orphan entities gauge.

        Args:
            count: Number of orphan entities (no relationships)
        """
        self._orphan_entities = count

    def update_age_distribution(self, distribution: Dict[str, int]) -> None:
        """
        Update memory age distribution gauges.

        Args:
            distribution: Dict with keys aligned to lifecycle thresholds (30/90/180/365 days)
        """
        # Map from health metrics keys to internal keys
        key_mapping = {
            "under_7_days": "UNDER_7_DAYS",
            "days_7_to_30": "DAYS_7_TO_30",
            "days_30_to_90": "DAYS_30_TO_90",
            "days_90_to_180": "DAYS_90_TO_180",
            "days_180_to_365": "DAYS_180_TO_365",
            "over_365_days": "OVER_365_DAYS",
        }
        for src_key, dest_key in key_mapping.items():
            if src_key in distribution:
                self._age_distribution[dest_key] = distribution[src_key]

    def record_access_pattern(
        self,
        importance: int,
        lifecycle_state: str,
        days_since_last_access: Optional[float] = None
    ) -> None:
        """
        Record access pattern metrics when a memory is accessed.

        Tracks what kinds of memories are being accessed (by importance and state)
        and how long since they were last accessed.

        Args:
            importance: Importance level of the accessed memory (1-5)
            lifecycle_state: Lifecycle state at time of access (ACTIVE, DORMANT, etc.)
            days_since_last_access: Days since memory was last accessed (optional)
        """
        if not self._counters:
            return

        try:
            # Map importance level to label (matching system's ImportanceLevel enum)
            # TRIVIAL=1, LOW=2, MODERATE=3, HIGH=4, CORE=5
            importance_labels = {
                1: "TRIVIAL",
                2: "LOW",
                3: "MODERATE",
                4: "HIGH",
                5: "CORE",
            }
            importance_label = importance_labels.get(importance, "MODERATE")

            # Record access by importance level
            self._counters["access_by_importance"].add(1, {"level": importance_label})

            # Record access by lifecycle state
            self._counters["access_by_state"].add(1, {"state": lifecycle_state})

            # Record days since last access histogram if provided
            if days_since_last_access is not None and self._histograms:
                self._histograms["days_since_last_access"].record(days_since_last_access)

            logger.debug(
                f"Recorded access pattern: importance={importance_label}, "
                f"state={lifecycle_state}, days_since={days_since_last_access}"
            )
        except Exception as e:
            logger.error(f"Failed to record access pattern: {e}")


# =============================================================================
# Global Instances
# =============================================================================

# Global metrics exporter instance (cache)
_metrics_exporter: Optional[CacheMetricsExporter] = None

# Global decay metrics exporter instance
_decay_metrics_exporter: Optional[DecayMetricsExporter] = None


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


def initialize_decay_metrics_exporter() -> Optional[DecayMetricsExporter]:
    """
    Initialize the global decay metrics exporter instance.

    Must be called after initialize_metrics_exporter() to share the meter.

    Returns:
        DecayMetricsExporter instance, or None if metrics not available
    """
    global _decay_metrics_exporter

    if _decay_metrics_exporter is not None:
        return _decay_metrics_exporter

    cache_exporter = get_metrics_exporter()
    if cache_exporter is None or cache_exporter._meter is None:
        logger.warning("Cannot initialize decay metrics - cache exporter not initialized")
        return None

    _decay_metrics_exporter = DecayMetricsExporter(meter=cache_exporter._meter)
    logger.info("Decay metrics exporter initialized")
    return _decay_metrics_exporter


def get_decay_metrics_exporter() -> Optional[DecayMetricsExporter]:
    """
    Get the global decay metrics exporter instance.

    Returns:
        DecayMetricsExporter if initialized, None otherwise
    """
    return _decay_metrics_exporter
