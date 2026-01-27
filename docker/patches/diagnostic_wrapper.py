"""
Diagnostic wrapper to instrument all LLM client methods and trace execution.
"""
import logging
import sys
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


def add_comprehensive_instrumentation(client: Any, model: str) -> Any:
    """
    Add diagnostic logging to ALL methods to understand execution flow.

    This wraps:
    1. Graphiti's high-level methods (generate_response, _generate_response)
    2. OpenAI client's low-level methods (chat.completions.create, responses.parse)
    """

    def print_and_log(msg: str):
        """Print to stderr and log for maximum visibility."""
        print(f"🔬 DIAGNOSTIC: {msg}", file=sys.stderr, flush=True)
        logger.info(f"🔬 DIAGNOSTIC: {msg}")

    # Detect if this is a Graphiti wrapper or underlying OpenAI client
    if hasattr(client, 'client') and hasattr(client.client, 'chat'):
        # This is a Graphiti OpenAIClient wrapping AsyncOpenAI
        print_and_log(f"Instrumenting Graphiti OpenAIClient for model: {model}")
        graphiti_client = client
        underlying_client = client.client

        # Wrap Graphiti's high-level methods
        if hasattr(graphiti_client, 'generate_response'):
            original_generate = graphiti_client.generate_response

            @wraps(original_generate)
            async def instrumented_generate(*args, **kwargs):
                print_and_log(f"📞 GRAPHITI: generate_response CALLED")
                result = await original_generate(*args, **kwargs)
                print_and_log(f"📞 GRAPHITI: generate_response RETURNED")
                return result

            graphiti_client.generate_response = instrumented_generate
            print_and_log("✅ Wrapped graphiti_client.generate_response")

        if hasattr(graphiti_client, '_generate_response'):
            original_internal_generate = graphiti_client._generate_response

            @wraps(original_internal_generate)
            async def instrumented_internal_generate(*args, **kwargs):
                print_and_log(f"📞 GRAPHITI: _generate_response CALLED")
                result = await original_internal_generate(*args, **kwargs)
                print_and_log(f"📞 GRAPHITI: _generate_response RETURNED")
                return result

            graphiti_client._generate_response = instrumented_internal_generate
            print_and_log("✅ Wrapped graphiti_client._generate_response")

        if hasattr(graphiti_client, '_create_completion'):
            original_create_completion = graphiti_client._create_completion

            @wraps(original_create_completion)
            async def instrumented_create_completion(*args, **kwargs):
                print_and_log(f"📞 GRAPHITI: _create_completion CALLED (uses chat.completions.create)")
                result = await original_create_completion(*args, **kwargs)
                print_and_log(f"📞 GRAPHITI: _create_completion RETURNED")
                return result

            graphiti_client._create_completion = instrumented_create_completion
            print_and_log("✅ Wrapped graphiti_client._create_completion")

        if hasattr(graphiti_client, '_create_structured_completion'):
            original_structured = graphiti_client._create_structured_completion

            @wraps(original_structured)
            async def instrumented_structured(*args, **kwargs):
                print_and_log(f"📞 GRAPHITI: _create_structured_completion CALLED (uses responses.parse)")
                result = await original_structured(*args, **kwargs)
                print_and_log(f"📞 GRAPHITI: _create_structured_completion RETURNED")
                return result

            graphiti_client._create_structured_completion = instrumented_structured
            print_and_log("✅ Wrapped graphiti_client._create_structured_completion")

        # Now wrap underlying OpenAI client methods
        if hasattr(underlying_client.chat.completions, 'create'):
            original_chat_create = underlying_client.chat.completions.create

            @wraps(original_chat_create)
            async def instrumented_chat_create(*args, **kwargs):
                print_and_log(f"🔥 OPENAI: chat.completions.create CALLED")
                result = await original_chat_create(*args, **kwargs)
                print_and_log(f"🔥 OPENAI: chat.completions.create RETURNED")
                return result

            underlying_client.chat.completions.create = instrumented_chat_create
            print_and_log("✅ Wrapped underlying_client.chat.completions.create")

        if hasattr(underlying_client, 'responses') and hasattr(underlying_client.responses, 'parse'):
            original_responses_parse = underlying_client.responses.parse

            @wraps(original_responses_parse)
            async def instrumented_responses_parse(*args, **kwargs):
                print_and_log(f"🔥 OPENAI: responses.parse CALLED")
                try:
                    result = await original_responses_parse(*args, **kwargs)
                    print_and_log(f"🔥 OPENAI: responses.parse RETURNED")
                    return result
                except Exception as e:
                    print_and_log(f"🔥 OPENAI: responses.parse FAILED: {type(e).__name__}: {e}")
                    raise

            underlying_client.responses.parse = instrumented_responses_parse
            print_and_log("✅ Wrapped underlying_client.responses.parse")
        else:
            print_and_log("⚠️ underlying_client.responses.parse NOT FOUND (OpenRouter doesn't support it)")

    return client
