"""
Caching Wrapper - OpenRouter Prompt Caching Integration

Feature: 006-gemini-prompt-caching
Purpose: Monkey-patch OpenAI client to add cache_control markers and extract metrics
"""

import os
import logging
from typing import Any, Dict, List
from functools import wraps

logger = logging.getLogger(__name__)


def wrap_openai_client_for_caching(client: Any, model: str) -> Any:
    """
    Wrap an OpenAI-compatible client to add prompt caching support.

    This function monkey-patches the client's chat.completions.create method to:
    1. Format messages with cache_control markers (request preprocessing)
    2. Extract cache metrics from responses (response post-processing)

    Args:
        client: OpenAI-compatible client instance
        model: Model identifier (e.g., 'google/gemini-2.0-flash-001')

    Returns:
        The same client instance with patched methods
    """
    try:
        # Import caching modules
        from patches.message_formatter import format_messages_for_caching, is_gemini_model
        from patches.cache_metrics import CacheMetrics, get_pricing_tier
        from patches.session_metrics import SessionMetrics
        from patches.metrics_exporter import get_metrics_exporter

        # Check if caching should be applied
        if not is_gemini_model(model):
            logger.debug(f"Model {model} is not Gemini, skipping caching wrapper")
            return client

        # Store original method
        original_create = client.chat.completions.create

        # Create session metrics instance (stored on client for persistence)
        if not hasattr(client, '_cache_session_metrics'):
            client._cache_session_metrics = SessionMetrics()

        @wraps(original_create)
        async def create_with_caching(*args, **kwargs):
            """Wrapped create method with caching support."""

            # PHASE 1: REQUEST PREPROCESSING
            # Format messages with cache_control markers
            if 'messages' in kwargs:
                original_messages = kwargs['messages']
                kwargs['messages'] = format_messages_for_caching(original_messages, model)

                if os.getenv("MADEINOZ_KNOWLEDGE_PROMPT_CACHE_LOG_REQUESTS", "false").lower() == "true":
                    logger.info(f"Formatted {len(kwargs['messages'])} messages for caching")

            # Call original method
            response = await original_create(*args, **kwargs)

            # PHASE 2: RESPONSE POST-PROCESSING
            # Extract cache metrics if enabled
            metrics_enabled = os.getenv("MADEINOZ_KNOWLEDGE_PROMPT_CACHE_METRICS_ENABLED", "true").lower() == "true"

            if metrics_enabled:
                try:
                    # Get pricing tier
                    pricing = get_pricing_tier(model)
                    if pricing:
                        # Convert response to dict if needed
                        if hasattr(response, "model_dump"):
                            response_dict = response.model_dump()
                        elif hasattr(response, "to_dict"):
                            response_dict = response.to_dict()
                        elif isinstance(response, dict):
                            response_dict = response
                        else:
                            response_dict = None

                        if response_dict:
                            # Extract cache metrics
                            cache_metrics = CacheMetrics.from_openrouter_response(
                                response_dict,
                                model,
                                pricing
                            )

                            # Record to session metrics
                            client._cache_session_metrics.record_request(cache_metrics)

                            # Record to Prometheus/OpenTelemetry
                            metrics_exporter = get_metrics_exporter()
                            if metrics_exporter:
                                if cache_metrics.cache_hit:
                                    metrics_exporter.record_cache_hit(
                                        model,
                                        cache_metrics.tokens_saved,
                                        cache_metrics.cost_saved
                                    )
                                else:
                                    metrics_exporter.record_cache_miss(model)

                            # Attach metrics to response object for MCP layer to access
                            if hasattr(response, '__dict__'):
                                response._cache_metrics = cache_metrics

                            if os.getenv("MADEINOZ_KNOWLEDGE_PROMPT_CACHE_LOG_REQUESTS", "false").lower() == "true":
                                logger.info(
                                    f"Cache metrics: hit={cache_metrics.cache_hit}, "
                                    f"cached_tokens={cache_metrics.cached_tokens}, "
                                    f"cost_saved=${cache_metrics.cost_saved:.6f}"
                                )

                except Exception as e:
                    logger.error(f"Failed to extract cache metrics: {e}", exc_info=True)

            return response

        # Replace the method
        client.chat.completions.create = create_with_caching
        logger.info(f"Wrapped OpenAI client for caching support (model: {model})")

    except ImportError as e:
        logger.warning(f"Caching modules not available: {e}")
    except Exception as e:
        logger.error(f"Failed to wrap client for caching: {e}", exc_info=True)

    return client
