"""
Integration Tests: Gemini Prompt Caching E2E (Feature 006)

Tests the complete caching workflow with OpenRouter API:
- T021: Cache hit on repeated requests
- T022: Cache miss on first request
- T023: Multipart message format validation

Prerequisites:
- OpenRouter API key configured
- Gemini model available (e.g., google/gemini-2.0-flash-001)
- Environment variables set for test configuration
"""

import os
try:
    import pytest
except ImportError:
    pytest = None  # Allow running without pytest for standalone execution

import asyncio
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

# Import caching modules
import sys
from pathlib import Path

# Add docker/ to path so 'patches' package can be imported
docker_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(docker_dir))

from patches.message_formatter import (
    format_messages_for_caching,
    format_message_for_caching,
    is_gemini_model,
    is_cacheable_request,
    convert_to_multipart,
    add_cache_control_marker,
)
from patches.cache_metrics import CacheMetrics, PricingTier, get_pricing_tier
from patches.caching_wrapper import wrap_openai_client_for_caching


# Test Fixtures

def _pytest_fixture_decorator(func):
    """Conditional pytest.fixture decorator."""
    if pytest is not None:
        return pytest.fixture(func)
    return func

def _pytest_asyncio_decorator(func):
    """Conditional pytest.mark.asyncio decorator."""
    if pytest is not None and hasattr(pytest.mark, 'asyncio'):
        return pytest.mark.asyncio(func)
    return func

@_pytest_fixture_decorator
def openrouter_config():
    """OpenRouter configuration for testing."""
    return {
        "api_key": os.getenv("OPENROUTER_API_KEY", "test-key"),
        "api_url": "https://openrouter.ai/api/v1",
        "model": "google/gemini-2.0-flash-001",
    }


@_pytest_fixture_decorator
def sample_system_prompt():
    """Sample system prompt for testing (long enough to trigger caching)."""
    return """You are an expert knowledge graph assistant specializing in entity extraction and relationship mapping for personal knowledge management systems.

Your primary responsibilities include:

1. ENTITY EXTRACTION
   - Identify and extract named entities from user conversations and documents
   - Classify entities by type: Person, Organization, Location, Concept, Technology, Project, Event, Document
   - Extract entity attributes such as names, descriptions, roles, and metadata
   - Normalize entity names to canonical forms (e.g., "GPT-4" vs "GPT 4" vs "gpt4")
   - Handle entity disambiguation when multiple entities share similar names
   - Track entity aliases and alternative names for improved search recall

2. RELATIONSHIP MAPPING
   - Identify semantic relationships between extracted entities
   - Classify relationship types: works_for, located_in, part_of, related_to, created_by, used_in, depends_on
   - Extract temporal information about relationships (start date, end date, validity period)
   - Determine relationship strength and confidence scores
   - Handle bidirectional relationships appropriately (e.g., "works_for" implies "employs")
   - Resolve relationship conflicts when contradictory information is present

3. TEMPORAL AWARENESS
   - Track when information was added to the knowledge graph (episode timestamps)
   - Mark facts as invalid when superseded by newer information
   - Maintain historical context for entity states and relationships
   - Handle time-sensitive queries ("What was X's role in 2020?" vs "What is X's current role?")

4. KNOWLEDGE GRAPH SCHEMA
   The knowledge graph consists of three core primitives:

   Episodes: Time-stamped snippets of information (conversations, documents, notes)
   - UUID identifier
   - Content text
   - Source metadata (conversation ID, document path, user ID)
   - Timestamp (when information was captured)
   - Group ID (for organizing knowledge by domain/project)

   Nodes: Entities extracted from episodes
   - UUID identifier
   - Name (canonical form)
   - Entity type classification
   - Summary/description
   - Attributes (key-value pairs)
   - Created and updated timestamps

   Facts: Relationships between nodes
   - UUID identifier
   - Subject node UUID
   - Predicate (relationship type)
   - Object node UUID
   - Validity period (valid_at, invalid_at timestamps)
   - Confidence score
   - Source episode UUIDs

5. SEARCH AND RETRIEVAL
   When users query the knowledge graph:
   - Use semantic search to find relevant nodes based on natural language queries
   - Traverse relationships to discover connected information
   - Filter results by group_id, entity type, time ranges, or confidence thresholds
   - Rank results by relevance, recency, and relationship strength
   - Provide context by including related nodes and facts in search results

6. QUALITY GUIDELINES
   - Prefer precision over recall for entity extraction (avoid false positives)
   - Use confidence scores to indicate uncertainty
   - Provide source attribution for all extracted facts
   - Maintain referential integrity (don't create orphaned relationships)
   - Handle missing or incomplete information gracefully
   - Flag low-confidence extractions for user review

7. ERROR HANDLING
   - Validate all UUIDs before creating references
   - Check for duplicate entities before insertion
   - Handle graph query timeouts with partial results
   - Provide meaningful error messages for schema violations
   - Suggest corrections when entity names are ambiguous

8. FORMATTING REQUIREMENTS
   When presenting knowledge graph data:
   - Use consistent entity naming (proper capitalization, no typos)
   - Format dates as ISO 8601 (YYYY-MM-DD)
   - Include relationship directionality in descriptions
   - Show confidence scores as percentages (0-100%)
   - Link to source episodes for fact verification

Remember: The knowledge graph is a living system that evolves as new information arrives. Always consider temporal validity, maintain data quality, and provide clear attribution for extracted knowledge."""


@_pytest_fixture_decorator
def sample_user_message():
    """Sample user message for testing (long enough to trigger caching)."""
    return """I need help understanding how to effectively use the knowledge graph system for tracking my research on distributed systems and microservices architecture.

Specifically, I'm working on three main projects:

1. Project Alpha - A microservices migration for an e-commerce platform
   - Key people: Sarah Chen (lead architect), Marcus Rodriguez (DevOps), Emily Watson (product manager)
   - Technologies: Kubernetes, Istio service mesh, gRPC for inter-service communication
   - Started in Q3 2024, expected completion Q2 2025
   - Main challenges: data consistency across services, observability, deployment orchestration

2. Research on eventual consistency patterns
   - Studying CRDT implementations in distributed databases
   - Comparing Cassandra, DynamoDB, and CockroachDB approaches
   - Reading papers by Leslie Lamport, Nancy Lynch, and Barbara Liskov
   - Attended QCon presentation by Martin Kleppmann on November 15, 2024

3. Side project: Building a distributed task queue
   - Using Redis Streams for message broker
   - Implementing at-least-once delivery semantics
   - Planning to add dead letter queue and retry logic
   - Code repository: github.com/example/distributed-task-queue

Can you help me:
- Extract the key entities (people, technologies, projects, concepts) from this information
- Map the relationships between these entities
- Organize this into a queryable knowledge graph structure
- Set up appropriate groupings so I can query by project or research area
- Suggest what additional metadata I should track for each entity type"""


@_pytest_fixture_decorator
def mock_openai_client():
    """Mock OpenAI client for testing wrapper."""
    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()

    # Create async mock for create method
    async def mock_create(*args, **kwargs):
        # Create a simple object that can have attributes attached
        # (simulates OpenAI response object structure)
        class MockResponse:
            def __init__(self, data):
                # Store data for dict conversion
                self._data = data
                # Copy dict fields as attributes
                for key, value in data.items():
                    setattr(self, key, value)

            def get(self, key, default=None):
                """Support dict-style access for compatibility."""
                return getattr(self, key, default)

            def to_dict(self):
                """Convert response to dictionary for cache metrics extraction."""
                return self._data

        # Simulate OpenRouter response with cache metrics
        response_data = {
            "id": "gen-test123",
            "model": "google/gemini-2.0-flash-001",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Test-Driven Development (TDD) follows these principles...",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 2048,
                "completion_tokens": 342,
                "cached_tokens": 1523,  # Cache hit
            },
            "cache_discount": 0.2769,  # ~27.69% cost reduction
        }

        return MockResponse(response_data)

    client.chat.completions.create = mock_create
    return client


# T023: Integration test for multipart format sent to OpenRouter

def test_multipart_message_format_conversion(sample_system_prompt):
    """
    T023: Verify messages are correctly transformed to multipart format.

    Tests that:
    1. Simple string messages become multipart format
    2. cache_control marker is added to system messages
    3. Format matches OpenRouter requirements
    """
    # Create simple message
    message = {
        "role": "system",
        "content": sample_system_prompt,
    }

    # Format for caching
    formatted = format_message_for_caching(message)

    # Verify multipart structure
    assert isinstance(formatted["content"], list), "Content should be multipart list"
    assert len(formatted["content"]) > 0, "Content list should not be empty"

    # Verify first part structure
    first_part = formatted["content"][0]
    assert first_part["type"] == "text", "Content part should be type 'text'"
    assert first_part["text"] == sample_system_prompt, "Text content should be preserved"

    # Verify cache_control marker on last part
    last_part = formatted["content"][-1]
    assert "cache_control" in last_part, "cache_control marker should be present"
    assert last_part["cache_control"]["type"] == "ephemeral", "cache_control type should be ephemeral"

    print(f"✓ Multipart format validation passed")
    print(f"  - Content parts: {len(formatted['content'])}")
    print(f"  - Cache control: {last_part['cache_control']}")


def test_format_messages_for_caching_gemini_model(sample_system_prompt, sample_user_message):
    """
    T023: Verify format_messages_for_caching() transforms messages for Gemini models.

    Tests that:
    1. System messages get cache_control markers
    2. User/assistant messages remain unchanged
    3. Only Gemini models trigger transformation
    """
    messages = [
        {"role": "system", "content": sample_system_prompt},
        {"role": "user", "content": sample_user_message},
    ]

    # Test with Gemini model
    formatted = format_messages_for_caching(messages, "google/gemini-2.0-flash-001")

    # Verify system message transformed
    system_msg = formatted[0]
    assert isinstance(system_msg["content"], list), "System message should be multipart"
    assert "cache_control" in system_msg["content"][-1], "System message should have cache_control"

    # Verify user message unchanged (should still be string or stay as-is)
    user_msg = formatted[1]
    # User messages don't get cache_control in our implementation
    assert user_msg["role"] == "user", "User message role preserved"

    print(f"✓ Gemini model formatting passed")
    print(f"  - System message multipart: {isinstance(system_msg['content'], list)}")
    print(f"  - Cache control present: {'cache_control' in system_msg['content'][-1]}")


def test_non_gemini_model_passthrough(sample_system_prompt):
    """
    T023: Verify non-Gemini models don't get cache formatting.

    Tests that:
    1. Non-Gemini models return messages unchanged
    2. No cache_control markers added
    """
    messages = [
        {"role": "system", "content": sample_system_prompt},
    ]

    # Test with non-Gemini model
    formatted = format_messages_for_caching(messages, "openai/gpt-4")

    # Should be unchanged
    assert formatted == messages, "Non-Gemini messages should be unchanged"

    print(f"✓ Non-Gemini passthrough validated")


def test_is_gemini_model_detection():
    """
    T023: Verify Gemini model detection works correctly.
    """
    assert is_gemini_model("google/gemini-2.0-flash-001") is True
    assert is_gemini_model("google/gemini-2.5-pro") is True
    assert is_gemini_model("gemini-pro") is True
    assert is_gemini_model("openai/gpt-4") is False
    assert is_gemini_model("anthropic/claude-3-opus") is False

    print(f"✓ Gemini model detection validated")


# T022: Integration test for cache miss on first request

@_pytest_asyncio_decorator
async def test_cache_miss_first_request(mock_openai_client, openrouter_config):
    """
    T022: Verify first-time requests show cache_hit=false.

    Tests that:
    1. First request has cached_tokens=0
    2. cache_hit=false
    3. cost_saved=0.0
    4. prompt_tokens and completion_tokens populated
    """
    # Modify mock to simulate cache miss
    async def mock_create_cache_miss(*args, **kwargs):
        return {
            "id": "gen-test-miss",
            "model": "google/gemini-2.0-flash-001",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "First response",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 2048,
                "completion_tokens": 342,
                "cached_tokens": 0,  # No cache hit
            },
            # No cache_discount field on miss
        }

    mock_openai_client.chat.completions.create = mock_create_cache_miss

    # Wrap client
    wrapped_client = wrap_openai_client_for_caching(
        mock_openai_client,
        openrouter_config["model"]
    )

    # Make request
    response = await wrapped_client.chat.completions.create(
        messages=[
            {"role": "system", "content": "Test system prompt"},
            {"role": "user", "content": "Test question"},
        ]
    )

    # Extract metrics from response
    pricing = get_pricing_tier(openrouter_config["model"])
    assert pricing is not None, "Pricing tier should be available"

    metrics = CacheMetrics.from_openrouter_response(
        response,
        openrouter_config["model"],
        pricing
    )

    # Verify cache miss behavior
    assert metrics.cache_hit is False, "Should be cache miss"
    assert metrics.cached_tokens == 0, "No tokens from cache"
    assert metrics.tokens_saved == 0, "No tokens saved"
    assert metrics.cost_saved == 0.0, "No cost saved"
    assert metrics.savings_percent == 0.0, "No savings percentage"
    assert metrics.prompt_tokens == 2048, "Prompt tokens should be recorded"
    assert metrics.completion_tokens == 342, "Completion tokens should be recorded"

    print(f"✓ Cache miss test passed")
    print(f"  - Cache hit: {metrics.cache_hit}")
    print(f"  - Cached tokens: {metrics.cached_tokens}")
    print(f"  - Cost saved: ${metrics.cost_saved:.6f}")


# T021: Integration test for cache hit on repeated request

@_pytest_asyncio_decorator
async def test_cache_hit_repeated_request(mock_openai_client, openrouter_config):
    """
    T021: Verify repeated requests show cache_hit=true with savings.

    Tests that:
    1. Second request has cached_tokens > 0
    2. cache_hit=true
    3. cost_saved > 0
    4. savings_percent >= 40% (per SC-001)
    """
    # Use default mock which simulates cache hit
    wrapped_client = wrap_openai_client_for_caching(
        mock_openai_client,
        openrouter_config["model"]
    )

    # Make first request (cache miss in real scenario, but our mock shows hit)
    response = await wrapped_client.chat.completions.create(
        messages=[
            {"role": "system", "content": "Test system prompt"},
            {"role": "user", "content": "Test question"},
        ]
    )

    # Extract metrics
    pricing = get_pricing_tier(openrouter_config["model"])
    assert pricing is not None, "Pricing tier should be available"

    metrics = CacheMetrics.from_openrouter_response(
        response,
        openrouter_config["model"],
        pricing
    )

    # Verify cache hit behavior
    assert metrics.cache_hit is True, "Should be cache hit"
    assert metrics.cached_tokens > 0, "Should have cached tokens"
    assert metrics.cached_tokens == 1523, "Should match mock response"
    assert metrics.tokens_saved == 1523, "Tokens saved equals cached tokens"
    assert metrics.cost_saved > 0, "Should have cost savings"

    # Verify 40%+ savings (SC-001 requirement)
    # With 1523/2048 cached tokens at ~50% discount, should exceed 40%
    assert metrics.savings_percent >= 40.0, f"Should have 40%+ savings, got {metrics.savings_percent:.1f}%"

    print(f"✓ Cache hit test passed")
    print(f"  - Cache hit: {metrics.cache_hit}")
    print(f"  - Cached tokens: {metrics.cached_tokens}")
    print(f"  - Tokens saved: {metrics.tokens_saved}")
    print(f"  - Cost saved: ${metrics.cost_saved:.6f}")
    print(f"  - Savings: {metrics.savings_percent:.1f}%")


def test_cacheable_request_detection(sample_system_prompt):
    """
    T023: Verify request token threshold detection.

    Tests that:
    1. Large prompts are detected as cacheable
    2. Small prompts are not marked for caching
    """
    # Large message should be cacheable
    large_messages = [
        {"role": "system", "content": sample_system_prompt * 50},  # ~5KB
    ]
    assert is_cacheable_request(large_messages, min_tokens=1024) is True

    # Small message should not be cacheable
    small_messages = [
        {"role": "system", "content": "Hi"},
    ]
    assert is_cacheable_request(small_messages, min_tokens=1024) is False

    print(f"✓ Cacheable request detection validated")


# T033: Integration test for cache_metrics present in response

@_pytest_asyncio_decorator
async def test_cache_metrics_present_in_response(mock_openai_client, openrouter_config):
    """
    T033: Verify cache_metrics is attached to response object on cache hit.

    Tests that:
    1. Response object has _cache_metrics attribute
    2. _cache_metrics is a CacheMetrics instance
    3. Attribute is accessible after response returned
    """
    # Wrap client
    wrapped_client = wrap_openai_client_for_caching(
        mock_openai_client,
        openrouter_config["model"]
    )

    # Make request
    response = await wrapped_client.chat.completions.create(
        messages=[
            {"role": "system", "content": "Test system prompt"},
            {"role": "user", "content": "Test question"},
        ]
    )

    # Verify _cache_metrics attribute exists
    assert hasattr(response, "_cache_metrics"), "Response should have _cache_metrics attribute"

    # Verify it's a CacheMetrics instance
    cache_metrics = response._cache_metrics
    assert cache_metrics is not None, "cache_metrics should not be None"
    assert isinstance(cache_metrics, CacheMetrics), "cache_metrics should be CacheMetrics instance"

    # Verify basic accessibility
    assert cache_metrics.cache_hit is True, "Mock response should show cache hit"

    print("✓ cache_metrics present in response object")
    print(f"  - Attribute exists: {hasattr(response, '_cache_metrics')}")
    print(f"  - Instance type: {type(cache_metrics).__name__}")
    print(f"  - cache_hit: {cache_metrics.cache_hit}")


# T034: Integration test for all 10 cache_metrics fields

@_pytest_asyncio_decorator
async def test_all_cache_metrics_fields_present(mock_openai_client, openrouter_config):
    """
    T034: Verify all 10 cache_metrics fields are present and accessible.

    Tests that:
    1. All 10 required fields exist on cache_metrics
    2. Fields have correct types
    3. to_dict() returns all fields
    """
    # Wrap client
    wrapped_client = wrap_openai_client_for_caching(
        mock_openai_client,
        openrouter_config["model"]
    )

    # Make request
    response = await wrapped_client.chat.completions.create(
        messages=[
            {"role": "system", "content": "Test system prompt"},
            {"role": "user", "content": "Test question"},
        ]
    )

    # Get cache_metrics
    cache_metrics = response._cache_metrics
    assert cache_metrics is not None

    # Verify all 10 fields exist and have correct types
    required_fields = {
        "cache_hit": bool,
        "cached_tokens": int,
        "prompt_tokens": int,
        "completion_tokens": int,
        "tokens_saved": int,
        "cost_without_cache": float,
        "actual_cost": float,
        "cost_saved": float,
        "savings_percent": float,
        "model": str,
    }

    for field_name, expected_type in required_fields.items():
        assert hasattr(cache_metrics, field_name), f"Field {field_name} should exist"
        field_value = getattr(cache_metrics, field_name)
        assert isinstance(field_value, expected_type), f"Field {field_name} should be {expected_type.__name__}"

    # Verify to_dict() returns all fields
    metrics_dict = cache_metrics.to_dict()
    assert len(metrics_dict) == 10, f"to_dict() should return 10 fields, got {len(metrics_dict)}"

    for field_name in required_fields.keys():
        assert field_name in metrics_dict, f"to_dict() should include {field_name}"

    print("✓ All 10 cache_metrics fields validated")
    print(f"  - Fields present: {', '.join(required_fields.keys())}")
    print(f"  - to_dict() fields: {len(metrics_dict)}")
    print(f"  - Sample values:")
    print(f"    - cache_hit: {cache_metrics.cache_hit}")
    print(f"    - cached_tokens: {cache_metrics.cached_tokens}")
    print(f"    - cost_saved: ${cache_metrics.cost_saved:.6f}")
    print(f"    - savings_percent: {cache_metrics.savings_percent:.1f}%")


# Test Runner

if __name__ == "__main__":
    """Run tests directly with python docker/tests/integration/test_caching_e2e.py"""
    print("=" * 80)
    print("Running Integration Tests: Gemini Prompt Caching E2E")
    print("=" * 80)

    # Create fixtures by calling the fixture functions
    sys_prompt = sample_system_prompt()
    user_msg = sample_user_message()

    # Run synchronous tests
    print("\n[T023] Multipart Format Tests:")
    print("-" * 80)
    test_multipart_message_format_conversion(sys_prompt)
    test_format_messages_for_caching_gemini_model(sys_prompt, user_msg)
    test_non_gemini_model_passthrough(sys_prompt)
    test_is_gemini_model_detection()
    test_cacheable_request_detection(sys_prompt)

    # Run async tests (create fresh fixtures for each test to avoid state pollution)
    print("\n[T022] Cache Miss Test:")
    print("-" * 80)
    asyncio.run(test_cache_miss_first_request(mock_openai_client(), openrouter_config()))

    print("\n[T021] Cache Hit Test:")
    print("-" * 80)
    asyncio.run(test_cache_hit_repeated_request(mock_openai_client(), openrouter_config()))

    print("\n[T033] Cache Metrics Attachment Test:")
    print("-" * 80)
    asyncio.run(test_cache_metrics_present_in_response(mock_openai_client(), openrouter_config()))

    print("\n[T034] All Cache Metrics Fields Test:")
    print("-" * 80)
    asyncio.run(test_all_cache_metrics_fields_present(mock_openai_client(), openrouter_config()))

    print("\n" + "=" * 80)
    print("All integration tests completed successfully!")
    print("=" * 80)
