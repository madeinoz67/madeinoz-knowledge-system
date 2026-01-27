"""
Caching Wrapper - OpenRouter Prompt Caching Integration

Feature: 006-gemini-prompt-caching
Purpose: Monkey-patch OpenAI client to add cache_control markers and extract metrics

Wraps BOTH OpenAI API endpoints used by Graphiti:
1. chat.completions.create - for regular JSON responses
2. responses.parse - for structured responses (Pydantic models)
"""

import os
import time
import logging
from typing import Any
from functools import wraps
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def wrap_openai_client_for_caching(client: Any, model: str) -> Any:
    """
    Wrap an OpenAI-compatible client to add prompt caching support.

    This function monkey-patches BOTH of the client's completion methods to:
    1. Format messages with cache_control markers (request preprocessing)
    2. Extract cache metrics from responses (response post-processing)

    Args:
        client: OpenAI-compatible client instance (Graphiti's LLMClient wrapper)
        model: Model identifier (e.g., 'google/gemini-2.0-flash-001')

    Returns:
        The same client instance with patched methods
    """
    try:
        # Import caching modules
        from utils.message_formatter import format_messages_for_caching, is_gemini_model
        from utils.cache_metrics import CacheMetrics, get_pricing_tier
        from utils.session_metrics import SessionMetrics
        from utils.metrics_exporter import get_metrics_exporter

        # Check if caching should be applied
        if not is_gemini_model(model):
            logger.debug(f"Model {model} is not Gemini, skipping caching wrapper")
            return client

        # Graphiti's LLMClient wrappers have a .client attribute that contains the underlying OpenAI client
        # We need to wrap that underlying client, not the Graphiti wrapper
        if hasattr(client, 'client') and hasattr(client.client, 'chat'):
            underlying_client = client.client
        elif hasattr(client, 'chat'):
            underlying_client = client
        else:
            logger.warning(f"Client {type(client).__name__} doesn't have expected structure for caching wrapper")
            return client

        # Detect provider from base_url to determine which endpoints to wrap
        provider_name = "Unknown"
        is_openrouter = False
        if hasattr(underlying_client, 'base_url'):
            base_url = str(underlying_client.base_url)
            # Use urlparse for proper hostname validation
            # Check exact match or subdomain (with leading dot) to satisfy CodeQL
            parsed = urlparse(base_url)
            hostname = (parsed.hostname or "").lower()
            if hostname == 'openrouter.ai' or hostname.endswith('.openrouter.ai'):
                provider_name = "OpenRouter"
                is_openrouter = True
            elif hostname == 'api.openai.com' or hostname.endswith('.api.openai.com'):
                provider_name = "OpenAI"
            logger.info(f"Detected provider: {provider_name} (base_url: {base_url})")

        # Create session metrics instance (stored on client for persistence)
        if not hasattr(client, '_cache_session_metrics'):
            client._cache_session_metrics = SessionMetrics()

        # Helper function to extract and record cache metrics (shared by both wrappers)
        def extract_and_record_metrics(response: Any) -> None:
            """Extract cache metrics from response and record to Prometheus."""
            metrics_enabled = os.getenv("MADEINOZ_KNOWLEDGE_PROMPT_CACHE_METRICS_ENABLED", "true").lower() == "true"

            if not metrics_enabled:
                return

            try:
                # DEBUG: Log response structure
                if os.getenv("MADEINOZ_KNOWLEDGE_PROMPT_CACHE_LOG_REQUESTS", "false").lower() == "true":
                    logger.info(f"📦 Response type: {type(response).__name__}")
                    logger.info(f"📦 Response dir: {[attr for attr in dir(response) if not attr.startswith('_')]}")

                    # Inspect usage attribute directly
                    if hasattr(response, 'usage'):
                        logger.info(f"📦 response.usage type: {type(response.usage)}")
                        logger.info(f"📦 response.usage value: {response.usage}")
                        if response.usage is not None:
                            logger.info(f"📦 response.usage dir: {[attr for attr in dir(response.usage) if not attr.startswith('_')]}")
                            # Try to access common usage fields directly
                            if hasattr(response.usage, 'prompt_tokens'):
                                logger.info(f"📦 response.usage.prompt_tokens: {response.usage.prompt_tokens}")
                            if hasattr(response.usage, 'completion_tokens'):
                                logger.info(f"📦 response.usage.completion_tokens: {response.usage.completion_tokens}")
                            if hasattr(response.usage, 'prompt_tokens_details'):
                                logger.info(f"📦 response.usage.prompt_tokens_details: {response.usage.prompt_tokens_details}")

                # Get pricing tier
                pricing = get_pricing_tier(model)
                if not pricing:
                    return

                # Convert response to dict if needed
                # Special handling for ParsedResponse with ResponseUsage object
                if hasattr(response, "usage") and response.usage is not None:
                    # Access ResponseUsage object directly and transform to expected format
                    usage_obj = response.usage
                    response_dict = {
                        "usage": {
                            "prompt_tokens": getattr(usage_obj, 'input_tokens', 0),
                            "completion_tokens": getattr(usage_obj, 'output_tokens', 0),
                            # Try both field names: OpenAI SDK uses input_tokens_details, OpenRouter API uses prompt_tokens_details
                            "cached_tokens": (
                                getattr(getattr(usage_obj, 'prompt_tokens_details', None), 'cached_tokens', 0)
                                if hasattr(usage_obj, 'prompt_tokens_details') and getattr(usage_obj, 'prompt_tokens_details', None)
                                else getattr(getattr(usage_obj, 'input_tokens_details', None), 'cached_tokens', 0)
                                if hasattr(usage_obj, 'input_tokens_details') and getattr(usage_obj, 'input_tokens_details', None)
                                else 0
                            ),
                            "total_tokens": getattr(usage_obj, 'total_tokens', 0)
                        }
                    }
                    # Include cost if available
                    if hasattr(usage_obj, 'cost'):
                        response_dict["cost"] = usage_obj.cost
                    if hasattr(usage_obj, 'cost_details'):
                        response_dict["cost_details"] = usage_obj.cost_details
                elif hasattr(response, "model_dump"):
                    response_dict = response.model_dump()
                elif hasattr(response, "to_dict"):
                    response_dict = response.to_dict()
                elif isinstance(response, dict):
                    response_dict = response
                else:
                    return

                # DEBUG: Log pricing/token fields from response
                if os.getenv("MADEINOZ_KNOWLEDGE_PROMPT_CACHE_LOG_REQUESTS", "false").lower() == "true":
                    logger.info("=" * 70)
                    logger.info("📊 RESPONSE PRICE MARKERS:")

                    # OpenRouter format (root-level fields)
                    if "tokens_prompt" in response_dict:
                        logger.info(f"  tokens_prompt: {response_dict.get('tokens_prompt')}")
                    if "tokens_completion" in response_dict:
                        logger.info(f"  tokens_completion: {response_dict.get('tokens_completion')}")
                    if "native_tokens_cached" in response_dict:
                        logger.info(f"  native_tokens_cached: {response_dict.get('native_tokens_cached')}")
                    if "native_tokens_prompt" in response_dict:
                        logger.info(f"  native_tokens_prompt: {response_dict.get('native_tokens_prompt')}")
                    if "native_tokens_completion" in response_dict:
                        logger.info(f"  native_tokens_completion: {response_dict.get('native_tokens_completion')}")

                    # OpenAI format (usage object)
                    if "usage" in response_dict:
                        usage = response_dict["usage"]
                        logger.info(f"  usage.prompt_tokens: {usage.get('prompt_tokens')}")
                        logger.info(f"  usage.completion_tokens: {usage.get('completion_tokens')}")
                        logger.info(f"  usage.cached_tokens: {usage.get('cached_tokens')}")

                    # Cost fields (if present)
                    cost_fields = ["cost", "total_cost", "prompt_cost", "completion_cost"]
                    for field in cost_fields:
                        if field in response_dict:
                            logger.info(f"  {field}: {response_dict.get(field)}")

                    logger.info("=" * 70)

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
                    # Record cache-specific metrics (hit/miss)
                    if cache_metrics.cache_hit:
                        metrics_exporter.record_cache_hit(
                            model,
                            cache_metrics.tokens_saved,
                            cache_metrics.cost_saved
                        )
                    else:
                        metrics_exporter.record_cache_miss(model)

                    # Record general request metrics (tokens, costs) - works even with caching disabled
                    usage = response_dict.get("usage", {})
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
                    total_cost = response_dict.get("cost", 0.0)

                    # Extract cost breakdown if available
                    # OpenRouter actual response uses: upstream_inference_input_cost, upstream_inference_output_cost
                    # (docs say prompt_cost/completions_cost but actual API differs)
                    cost_details = response_dict.get("cost_details", {})
                    if isinstance(cost_details, dict):
                        input_cost = cost_details.get("upstream_inference_input_cost", 0.0) or 0.0
                        output_cost = cost_details.get("upstream_inference_output_cost", 0.0) or 0.0
                    else:
                        # cost_details might be an object with attributes
                        input_cost = getattr(cost_details, 'upstream_inference_input_cost', 0.0) or 0.0
                        output_cost = getattr(cost_details, 'upstream_inference_output_cost', 0.0) or 0.0

                    logger.debug(f"📊 Metrics: prompt={prompt_tokens}, completion={completion_tokens}, cost=${total_cost:.6f}, input_cost=${input_cost:.6f}, output_cost=${output_cost:.6f}")

                    metrics_exporter.record_request_metrics(
                        model=model,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        total_cost=total_cost,
                        input_cost=input_cost,
                        output_cost=output_cost
                    )

                    # Record cache writes (tokens written to cache on cache miss)
                    # Gemini returns cache_creation_input_tokens when new cache is created
                    cache_write_tokens = 0
                    # Check in usage dict
                    if 'cache_creation_input_tokens' in usage:
                        cache_write_tokens = usage.get('cache_creation_input_tokens', 0)
                    # Check in prompt_tokens_details
                    elif 'prompt_tokens_details' in usage:
                        details = usage.get('prompt_tokens_details', {})
                        if isinstance(details, dict):
                            cache_write_tokens = details.get('cache_creation_input_tokens', 0) or 0

                    if cache_write_tokens > 0:
                        metrics_exporter.record_cache_write(model, cache_write_tokens)
                        logger.debug(f"📝 Cache write: {cache_write_tokens} tokens written to cache")

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

        # WRAPPER 1: chat.completions.create (used for regular JSON responses)
        if hasattr(underlying_client.chat.completions, 'create'):
            original_create = underlying_client.chat.completions.create

            @wraps(original_create)
            async def create_with_caching(*args, **kwargs):
                """Wrapped chat.completions.create method with caching support."""

                # ALWAYS log this to verify wrapper is being called
                import sys
                print(f"🔍🔍🔍 WRAPPER CALLED: chat.completions.create for model: {model}", file=sys.stderr, flush=True)
                logger.info(f"🔍 chat.completions.create CALLED for model: {model}")

                # PHASE 1: REQUEST PREPROCESSING
                # Format messages with cache_control markers
                if 'messages' in kwargs:
                    original_messages = kwargs['messages']
                    kwargs['messages'] = format_messages_for_caching(original_messages, model)

                    if os.getenv("MADEINOZ_KNOWLEDGE_PROMPT_CACHE_LOG_REQUESTS", "false").lower() == "true":
                        logger.info(f"Formatted {len(kwargs['messages'])} messages for caching")

                # Call original method with timing and error tracking
                start_time = time.monotonic()
                try:
                    response = await original_create(*args, **kwargs)
                except Exception as e:
                    # Record error and duration on failure
                    duration = time.monotonic() - start_time
                    metrics_exporter = get_metrics_exporter()
                    if metrics_exporter:
                        # Categorize error type
                        error_type = type(e).__name__
                        if 'rate' in str(e).lower() or 'limit' in str(e).lower():
                            error_type = 'rate_limit'
                        elif 'timeout' in str(e).lower():
                            error_type = 'timeout'
                        metrics_exporter.record_error(model, error_type)
                        metrics_exporter.record_request_duration(model, duration)
                    raise

                # Record successful request duration
                duration = time.monotonic() - start_time
                metrics_exporter = get_metrics_exporter()
                if metrics_exporter:
                    metrics_exporter.record_request_duration(model, duration)

                # PHASE 2: RESPONSE POST-PROCESSING
                extract_and_record_metrics(response)

                return response

            # Replace the method
            underlying_client.chat.completions.create = create_with_caching
            logger.info(f"Wrapped chat.completions.create for caching support")

        # WRAPPER 2: responses.parse (used for structured Pydantic responses)
        # OpenRouter DOES support responses.parse - diagnostic testing confirmed execution path
        if hasattr(underlying_client, 'responses') and hasattr(underlying_client.responses, 'parse'):
            original_parse = underlying_client.responses.parse

            @wraps(original_parse)
            async def parse_with_caching(*args, **kwargs):
                """Wrapped responses.parse method with caching support."""

                logger.info(f"🔍 responses.parse CALLED for model: {model}")

                # PHASE 1: REQUEST PREPROCESSING
                # CRITICAL BUG FIX: OpenRouter's /responses endpoint does NOT support multipart format
                # Multipart content with cache_control markers causes 400 BadRequestError
                # Error: "expected string, received array" at content path
                #
                # Root Cause: format_messages_for_caching() converts content to:
                #   content: [{"type": "text", "text": "...", "cache_control": {...}}]
                # But /responses endpoint requires:
                #   content: "string"
                #
                # Solution: Skip caching for responses.parse endpoint entirely
                # Note: Caching ONLY works with chat.completions.create endpoint
                #
                # Future: Research if cache_control can be added without multipart format
                # For now: responses.parse always bypasses caching

                if os.getenv("MADEINOZ_KNOWLEDGE_PROMPT_CACHE_LOG_REQUESTS", "false").lower() == "true":
                    logger.info("⚠️ Skipping cache formatting for responses.parse (multipart not supported)")

                # Call original method with timing and error tracking
                start_time = time.monotonic()
                try:
                    response = await original_parse(*args, **kwargs)
                except Exception as e:
                    # Record error and duration on failure
                    duration = time.monotonic() - start_time
                    metrics_exporter = get_metrics_exporter()
                    if metrics_exporter:
                        # Categorize error type
                        error_type = type(e).__name__
                        if 'rate' in str(e).lower() or 'limit' in str(e).lower():
                            error_type = 'rate_limit'
                        elif 'timeout' in str(e).lower():
                            error_type = 'timeout'
                        metrics_exporter.record_error(model, error_type)
                        metrics_exporter.record_request_duration(model, duration)
                    raise

                # Record successful request duration
                duration = time.monotonic() - start_time
                metrics_exporter = get_metrics_exporter()
                if metrics_exporter:
                    metrics_exporter.record_request_duration(model, duration)

                # PHASE 2: RESPONSE POST-PROCESSING
                extract_and_record_metrics(response)

                return response

            # Replace the method
            underlying_client.responses.parse = parse_with_caching
            logger.info(f"Wrapped responses.parse for caching support")

        logger.info(f"✅ Wrapped OpenAI client for caching support (provider: {provider_name}, model: {model}, client: {type(client).__name__})")

    except ImportError as e:
        logger.warning(f"Caching modules not available: {e}")
    except Exception as e:
        logger.error(f"Failed to wrap client for caching: {e}", exc_info=True)

    return client
