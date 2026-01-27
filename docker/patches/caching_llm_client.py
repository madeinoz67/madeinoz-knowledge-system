"""
Caching LLM Client Wrapper - OpenRouter Prompt Caching Support

Feature: 006-gemini-prompt-caching
Purpose: Wrap LLM clients to add cache_control markers and extract cache metrics
"""

import os
import logging
from typing import Any, Dict, List, Optional, Tuple
from graphiti_core.llm_client import LLMClient

# Import caching modules
from .cache_metrics import CacheMetrics, get_pricing_tier
from .message_formatter import format_messages_for_caching, is_gemini_model
from .session_metrics import SessionMetrics
from .metrics_exporter import get_metrics_exporter

logger = logging.getLogger(__name__)


class CachingLLMClient:
    """
    Wraps an LLM client to add prompt caching support for Gemini via OpenRouter.

    This wrapper:
    1. Formats request messages with cache_control markers (REQUEST preprocessing)
    2. Extracts cache metrics from responses (RESPONSE post-processing)
    3. Records metrics to Prometheus/OpenTelemetry
    4. Maintains session-level statistics
    """

    def __init__(self, wrapped_client: LLMClient, model: str):
        """
        Initialize caching wrapper.

        Args:
            wrapped_client: The actual LLM client to wrap
            model: Model identifier (e.g., 'google/gemini-2.0-flash-001')
        """
        self.wrapped_client = wrapped_client
        self.model = model
        self.session_metrics = SessionMetrics()

        # Check if metrics and caching are enabled
        self.metrics_enabled = os.getenv("MADEINOZ_KNOWLEDGE_PROMPT_CACHE_METRICS_ENABLED", "true").lower() == "true"
        self.log_requests = os.getenv("MADEINOZ_KNOWLEDGE_PROMPT_CACHE_LOG_REQUESTS", "false").lower() == "true"

    def _preprocess_request(self, messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Preprocess request to add cache_control markers if applicable.

        Args:
            messages: Original message list

        Returns:
            Tuple of (processed_messages, was_modified)
        """
        if not is_gemini_model(self.model):
            return messages, False

        original_count = len(messages)
        processed = format_messages_for_caching(messages, self.model)

        was_modified = (processed != messages)

        if was_modified and self.log_requests:
            logger.info(f"Added cache_control markers to {original_count} messages for model {self.model}")

        return processed, was_modified

    def _postprocess_response(self, response: Any) -> Optional[CacheMetrics]:
        """
        Extract cache metrics from LLM response.

        Args:
            response: OpenAI-compatible API response

        Returns:
            CacheMetrics if available, None otherwise
        """
        if not self.metrics_enabled:
            return None

        if not is_gemini_model(self.model):
            return None

        try:
            # Get pricing tier for cost calculations
            pricing = get_pricing_tier(self.model)
            if not pricing:
                logger.warning(f"No pricing tier found for model {self.model}")
                return None

            # Extract metrics from response
            # Response structure varies by client, need to handle both dict and object
            if hasattr(response, "model_dump"):
                response_dict = response.model_dump()
            elif hasattr(response, "to_dict"):
                response_dict = response.to_dict()
            elif isinstance(response, dict):
                response_dict = response
            else:
                logger.warning(f"Unexpected response type: {type(response)}")
                return None

            # Extract cache metrics
            cache_metrics = CacheMetrics.from_openrouter_response(
                response_dict,
                self.model,
                pricing
            )

            # Record to session metrics
            self.session_metrics.record_request(cache_metrics)

            # Record to Prometheus/OpenTelemetry
            metrics_exporter = get_metrics_exporter()
            if metrics_exporter:
                if cache_metrics.cache_hit:
                    metrics_exporter.record_cache_hit(
                        self.model,
                        cache_metrics.tokens_saved,
                        cache_metrics.cost_saved
                    )
                else:
                    metrics_exporter.record_cache_miss(self.model)

            # Log if requested
            if self.log_requests:
                logger.info(
                    f"Cache metrics: hit={cache_metrics.cache_hit}, "
                    f"cached_tokens={cache_metrics.cached_tokens}, "
                    f"cost_saved=${cache_metrics.cost_saved:.6f} "
                    f"({cache_metrics.savings_percent:.1f}%)"
                )

            return cache_metrics

        except Exception as e:
            logger.error(f"Failed to extract cache metrics: {e}", exc_info=True)
            return None

    # Delegate all attributes to wrapped client
    def __getattr__(self, name: str) -> Any:
        """
        Delegate attribute access to wrapped client.

        This allows the wrapper to be used as a drop-in replacement for the
        original LLM client.
        """
        return getattr(self.wrapped_client, name)

    def __str__(self) -> str:
        return f"CachingLLMClient(model={self.model}, wrapped={self.wrapped_client})"

    def __repr__(self) -> str:
        return self.__str__()
