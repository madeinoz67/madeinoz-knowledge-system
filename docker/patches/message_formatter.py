"""
Message Formatter - OpenRouter Cache Control Support

Feature: 006-gemini-prompt-caching
Purpose: Convert simple messages to multipart format with cache_control markers
"""

import os
import logging
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)


def is_caching_enabled() -> bool:
    """
    Check if prompt caching is enabled via environment variable.

    Returns:
        True if MADEINOZ_KNOWLEDGE_PROMPT_CACHE_ENABLED is true, False otherwise
    """
    return os.getenv("MADEINOZ_KNOWLEDGE_PROMPT_CACHE_ENABLED", "true").lower() == "true"


def is_gemini_model(model: str) -> bool:
    """
    Check if model is a Gemini model that supports caching via OpenRouter.

    Args:
        model: Model identifier (e.g., 'google/gemini-2.0-flash-001')

    Returns:
        True if model is a Gemini variant, False otherwise
    """
    if not model:
        return False

    # OpenRouter Gemini model patterns
    gemini_patterns = [
        "google/gemini",
        "gemini-",
        "gemini/"
    ]

    model_lower = model.lower()
    return any(pattern in model_lower for pattern in gemini_patterns)


def is_cacheable_request(messages: List[Dict[str, Any]], min_tokens: int = 1024) -> bool:
    """
    Check if request meets minimum token threshold for caching.

    Args:
        messages: List of message dictionaries
        min_tokens: Minimum token count for caching (default: 1024)

    Returns:
        True if request likely exceeds min_tokens, False otherwise

    Note:
        This is a heuristic estimate. OpenRouter makes the final decision based on
        actual token count after tokenization.
    """
    total_chars = 0

    for message in messages:
        content = message.get("content", "")

        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    total_chars += len(part["text"])

    # Rough estimate: ~4 characters per token for English text
    estimated_tokens = total_chars // 4

    return estimated_tokens >= min_tokens


def convert_to_multipart(content: Union[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Convert simple string content to multipart format.

    Args:
        content: Either a string or already multipart content list

    Returns:
        List of content parts in multipart format

    Example:
        Input: "System prompt text"
        Output: [{"type": "text", "text": "System prompt text"}]
    """
    # Already multipart format
    if isinstance(content, list):
        return content

    # Convert string to multipart
    if isinstance(content, str):
        return [{"type": "text", "text": content}]

    # Fallback for unexpected types
    logger.warning(f"Unexpected content type: {type(content)}")
    return [{"type": "text", "text": str(content)}]


def add_cache_control_marker(content_parts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Add cache_control marker to the last text content part.

    OpenRouter caching requires the cache_control marker to be on the content
    part that should be cached (typically the last part of system prompts).

    Args:
        content_parts: List of multipart content dictionaries

    Returns:
        Modified content parts with cache_control marker added

    Example:
        Input: [{"type": "text", "text": "System prompt"}]
        Output: [{"type": "text", "text": "System prompt", "cache_control": {"type": "ephemeral"}}]
    """
    if not content_parts:
        return content_parts

    # Find the last text part and add cache_control
    for i in range(len(content_parts) - 1, -1, -1):
        part = content_parts[i]
        if part.get("type") == "text":
            part["cache_control"] = {"type": "ephemeral"}
            break

    return content_parts


def format_message_for_caching(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform a message to include cache_control markers for OpenRouter caching.

    Only applies to system messages. User and assistant messages are passed through
    unchanged to avoid interfering with conversation flow.

    Args:
        message: Message dictionary with 'role' and 'content'

    Returns:
        Modified message with multipart content and cache_control marker

    Example:
        Input:
            {"role": "system", "content": "You are a helpful assistant..."}

        Output:
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": "You are a helpful assistant...",
                        "cache_control": {"type": "ephemeral"}
                    }
                ]
            }
    """
    # Only transform system messages
    if message.get("role") != "system":
        return message

    content = message.get("content", "")

    # Convert to multipart format
    content_parts = convert_to_multipart(content)

    # Add cache_control marker
    content_parts = add_cache_control_marker(content_parts)

    # Return modified message
    return {
        "role": message["role"],
        "content": content_parts
    }


def format_messages_for_caching(
    messages: List[Dict[str, Any]],
    model: str
) -> List[Dict[str, Any]]:
    """
    Format all messages in a request for OpenRouter caching.

    Checks if caching should be applied and transforms messages accordingly.
    This is the main entry point for request preprocessing.

    Args:
        messages: List of message dictionaries
        model: Model identifier

    Returns:
        Messages list, potentially transformed for caching

    Note:
        - Only applies to Gemini models when caching is enabled
        - Only transforms system messages
        - Passes through unchanged if caching not applicable
    """
    # Check if caching should be applied
    if not is_caching_enabled():
        logger.debug("Prompt caching disabled via environment variable")
        return messages

    if not is_gemini_model(model):
        logger.debug(f"Model {model} is not a Gemini model, skipping cache formatting")
        return messages

    if not is_cacheable_request(messages):
        logger.debug("Request below minimum token threshold, skipping cache formatting")
        return messages

    # Transform messages
    formatted_messages = []
    for message in messages:
        formatted_messages.append(format_message_for_caching(message))

    logger.debug(f"Formatted {len(messages)} messages for caching")
    return formatted_messages
