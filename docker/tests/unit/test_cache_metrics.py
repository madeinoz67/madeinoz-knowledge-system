"""
Unit Tests: CacheMetrics Dataclass (Feature 006)

Tests dataclass validation, cost calculations, and serialization:
- T024: CacheMetrics dataclass validation
- T025: cost_saved calculation formula
- T026: savings_percent calculation

Prerequisites:
- cache_metrics.py module with CacheMetrics and PricingTier
"""

try:
    import pytest
except ImportError:
    pytest = None  # Allow running without pytest for standalone execution

from typing import Dict, Any
import sys
from pathlib import Path

# Add docker/patches to path for imports
docker_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(docker_dir / "patches"))

from cache_metrics import CacheMetrics, PricingTier


# Test Fixtures

def _pytest_fixture_decorator(func):
    """Conditional pytest.fixture decorator."""
    if pytest is not None:
        return pytest.fixture(func)
    return func

@_pytest_fixture_decorator
def sample_pricing():
    """Sample pricing tier for Gemini 2.0 Flash."""
    return PricingTier(
        model="google/gemini-2.0-flash-001",
        input_per_million=0.10,  # $0.10 per 1M input tokens
        cached_input_per_million=0.01,  # $0.01 per 1M cached tokens (90% discount)
        output_per_million=0.30,  # $0.30 per 1M output tokens
    )


@_pytest_fixture_decorator
def cache_hit_response():
    """Sample OpenRouter response with cache hit."""
    return {
        "id": "gen-test123",
        "model": "google/gemini-2.0-flash-001",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Test response",
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


@_pytest_fixture_decorator
def cache_miss_response():
    """Sample OpenRouter response with cache miss."""
    return {
        "id": "gen-test-miss",
        "model": "google/gemini-2.0-flash-001",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Test response",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 2048,
            "completion_tokens": 342,
            "cached_tokens": 0,  # No cache hit
        },
        # No cache_discount field
    }


# T024: CacheMetrics dataclass validation

def test_cache_metrics_dataclass_fields():
    """
    T024: Verify CacheMetrics has all required fields.

    Tests that:
    1. All 10 fields are present and accessible
    2. Field types match expectations
    3. Dataclass is immutable (frozen=False but fields should exist)
    """
    metrics = CacheMetrics(
        cache_hit=True,
        cached_tokens=1000,
        prompt_tokens=2000,
        completion_tokens=500,
        tokens_saved=1000,
        cost_without_cache=0.15,
        actual_cost=0.10,
        cost_saved=0.05,
        savings_percent=33.33,
        model="google/gemini-2.0-flash-001",
    )

    # Verify all fields present
    assert hasattr(metrics, "cache_hit")
    assert hasattr(metrics, "cached_tokens")
    assert hasattr(metrics, "prompt_tokens")
    assert hasattr(metrics, "completion_tokens")
    assert hasattr(metrics, "tokens_saved")
    assert hasattr(metrics, "cost_without_cache")
    assert hasattr(metrics, "actual_cost")
    assert hasattr(metrics, "cost_saved")
    assert hasattr(metrics, "savings_percent")
    assert hasattr(metrics, "model")

    # Verify field types
    assert isinstance(metrics.cache_hit, bool)
    assert isinstance(metrics.cached_tokens, int)
    assert isinstance(metrics.prompt_tokens, int)
    assert isinstance(metrics.completion_tokens, int)
    assert isinstance(metrics.tokens_saved, int)
    assert isinstance(metrics.cost_without_cache, float)
    assert isinstance(metrics.actual_cost, float)
    assert isinstance(metrics.cost_saved, float)
    assert isinstance(metrics.savings_percent, float)
    assert isinstance(metrics.model, str)

    print("✓ CacheMetrics dataclass validation passed")


def test_cache_metrics_to_dict_serialization():
    """
    T024: Verify to_dict() returns all 10 fields.

    Tests that:
    1. to_dict() returns dictionary with 10 keys
    2. All field names match expected keys
    3. Values are JSON-serializable
    """
    metrics = CacheMetrics(
        cache_hit=True,
        cached_tokens=1000,
        prompt_tokens=2000,
        completion_tokens=500,
        tokens_saved=1000,
        cost_without_cache=0.15,
        actual_cost=0.10,
        cost_saved=0.05,
        savings_percent=33.33,
        model="google/gemini-2.0-flash-001",
    )

    result = metrics.to_dict()

    # Verify 10 fields present
    assert len(result) == 10, f"Expected 10 fields, got {len(result)}"

    # Verify all expected keys
    expected_keys = {
        "cache_hit", "cached_tokens", "prompt_tokens", "completion_tokens",
        "tokens_saved", "cost_without_cache", "actual_cost", "cost_saved",
        "savings_percent", "model"
    }
    assert set(result.keys()) == expected_keys

    # Verify values match
    assert result["cache_hit"] == True
    assert result["cached_tokens"] == 1000
    assert result["prompt_tokens"] == 2000
    assert result["completion_tokens"] == 500
    assert result["tokens_saved"] == 1000
    assert result["cost_without_cache"] == 0.15
    assert result["actual_cost"] == 0.10
    assert result["cost_saved"] == 0.05
    assert result["savings_percent"] == 33.33
    assert result["model"] == "google/gemini-2.0-flash-001"

    print("✓ CacheMetrics to_dict() serialization passed")


# T025: cost_saved calculation formula

def test_cost_saved_calculation_cache_hit(sample_pricing, cache_hit_response):
    """
    T025: Verify cost_saved = cost_without_cache - actual_cost (cache hit).

    Tests that:
    1. cost_without_cache uses full input price
    2. actual_cost uses cache_read_price for cached tokens
    3. cost_saved is the difference
    """
    metrics = CacheMetrics.from_openrouter_response(
        cache_hit_response,
        "google/gemini-2.0-flash-001",
        sample_pricing
    )

    # Expected calculations (pricing per million tokens):
    # cost_without_cache = (2048 * 0.10 / 1_000_000) + (342 * 0.30 / 1_000_000)
    #                    = 0.0002048 + 0.0001026 = 0.0003074
    expected_cost_without_cache = (2048 * 0.10 / 1_000_000) + (342 * 0.30 / 1_000_000)

    # actual_cost = (uncached_tokens * input / 1M) + (cached_tokens * cached_input / 1M) + (completion * output / 1M)
    # uncached_tokens = 2048 - 1523 = 525
    uncached_tokens = 2048 - 1523
    expected_actual_cost = (
        (uncached_tokens * 0.10 / 1_000_000) +
        (1523 * 0.01 / 1_000_000) +
        (342 * 0.30 / 1_000_000)
    )
    # = 0.0000525 + 0.00001523 + 0.0001026 = 0.00017033

    expected_cost_saved = expected_cost_without_cache - expected_actual_cost

    # Verify formula: cost_saved = cost_without_cache - actual_cost
    assert abs(metrics.cost_without_cache - expected_cost_without_cache) < 0.0001
    assert abs(metrics.actual_cost - expected_actual_cost) < 0.0001
    assert abs(metrics.cost_saved - expected_cost_saved) < 0.0001

    # Verify cost_saved is positive (savings occurred)
    assert metrics.cost_saved > 0

    print(f"✓ cost_saved calculation validated (cache hit)")
    print(f"  - cost_without_cache: ${metrics.cost_without_cache:.6f}")
    print(f"  - actual_cost: ${metrics.actual_cost:.6f}")
    print(f"  - cost_saved: ${metrics.cost_saved:.6f}")


def test_cost_saved_calculation_cache_miss(sample_pricing, cache_miss_response):
    """
    T025: Verify cost_saved = 0 when no cache hit.

    Tests that:
    1. cost_without_cache equals actual_cost (no caching)
    2. cost_saved is 0
    """
    metrics = CacheMetrics.from_openrouter_response(
        cache_miss_response,
        "google/gemini-2.0-flash-001",
        sample_pricing
    )

    # No cache hit means cost_without_cache == actual_cost
    assert abs(metrics.cost_without_cache - metrics.actual_cost) < 0.0001
    assert metrics.cost_saved == 0.0
    assert metrics.tokens_saved == 0

    print("✓ cost_saved calculation validated (cache miss = $0)")


def test_cost_saved_edge_case_100_percent_cached(sample_pricing):
    """
    T025: Verify cost_saved when 100% of prompt tokens are cached.

    Tests edge case:
    1. All prompt tokens come from cache
    2. cost_saved reflects maximum possible savings
    """
    response = {
        "id": "gen-test-100",
        "model": "google/gemini-2.0-flash-001",
        "choices": [{"message": {"role": "assistant", "content": "Test"}, "finish_reason": "stop"}],
        "usage": {
            "prompt_tokens": 2000,
            "completion_tokens": 100,
            "cached_tokens": 2000,  # 100% cached
        },
        "cache_discount": 0.75,  # Maximum discount
    }

    metrics = CacheMetrics.from_openrouter_response(
        response,
        "google/gemini-2.0-flash-001",
        sample_pricing
    )

    # Expected (pricing per million):
    # cost_without_cache = (2000 * 0.10 / 1M) + (100 * 0.30 / 1M) = 0.0002 + 0.00003 = 0.00023
    # actual_cost = (0 * 0.10 / 1M) + (2000 * 0.01 / 1M) + (100 * 0.30 / 1M) = 0 + 0.00002 + 0.00003 = 0.00005
    # cost_saved = 0.00023 - 0.00005 = 0.00018

    expected_cost_without_cache = (2000 * 0.10 / 1_000_000) + (100 * 0.30 / 1_000_000)
    expected_actual_cost = (0 * 0.10 / 1_000_000) + (2000 * 0.01 / 1_000_000) + (100 * 0.30 / 1_000_000)
    expected_cost_saved = expected_cost_without_cache - expected_actual_cost

    assert abs(metrics.cost_without_cache - expected_cost_without_cache) < 0.0001
    assert abs(metrics.actual_cost - expected_actual_cost) < 0.0001
    assert abs(metrics.cost_saved - expected_cost_saved) < 0.0001

    print("✓ cost_saved edge case validated (100% cached)")


# T026: savings_percent calculation

def test_savings_percent_calculation(sample_pricing, cache_hit_response):
    """
    T026: Verify savings_percent = (cost_saved / cost_without_cache) * 100.

    Tests that:
    1. savings_percent uses correct formula
    2. Result is between 0-100
    3. Matches expected percentage from cost_saved and cost_without_cache
    """
    metrics = CacheMetrics.from_openrouter_response(
        cache_hit_response,
        "google/gemini-2.0-flash-001",
        sample_pricing
    )

    # Formula: (cost_saved / cost_without_cache) * 100
    expected_savings_percent = (metrics.cost_saved / metrics.cost_without_cache) * 100

    assert abs(metrics.savings_percent - expected_savings_percent) < 0.01

    # Verify range
    assert 0 <= metrics.savings_percent <= 100

    # Verify cache hit has positive savings
    assert metrics.savings_percent > 0

    print(f"✓ savings_percent calculation validated: {metrics.savings_percent:.2f}%")


def test_savings_percent_zero_on_cache_miss(sample_pricing, cache_miss_response):
    """
    T026: Verify savings_percent = 0 when no cache hit.
    """
    metrics = CacheMetrics.from_openrouter_response(
        cache_miss_response,
        "google/gemini-2.0-flash-001",
        sample_pricing
    )

    assert metrics.savings_percent == 0.0

    print("✓ savings_percent validated (cache miss = 0%)")


def test_savings_percent_edge_case_100_percent(sample_pricing):
    """
    T026: Verify savings_percent approaches maximum with full cache hit.

    Tests edge case:
    1. 100% of prompt tokens cached
    2. savings_percent reflects maximum possible savings
    """
    response = {
        "id": "gen-test-100",
        "model": "google/gemini-2.0-flash-001",
        "choices": [{"message": {"role": "assistant", "content": "Test"}, "finish_reason": "stop"}],
        "usage": {
            "prompt_tokens": 2000,
            "completion_tokens": 100,
            "cached_tokens": 2000,
        },
        "cache_discount": 0.75,
    }

    metrics = CacheMetrics.from_openrouter_response(
        response,
        "google/gemini-2.0-flash-001",
        sample_pricing
    )

    # With 100% cached and 75% discount, savings should be substantial
    # Expected: (0.1125 / 0.18) * 100 = 62.5%
    expected_savings_percent = (metrics.cost_saved / metrics.cost_without_cache) * 100

    assert abs(metrics.savings_percent - expected_savings_percent) < 0.01
    assert metrics.savings_percent > 60  # Should be around 62.5%

    print(f"✓ savings_percent edge case validated: {metrics.savings_percent:.2f}%")


# Test Runner

if __name__ == "__main__":
    """Run tests directly with python docker/tests/unit/test_cache_metrics.py"""
    print("=" * 80)
    print("Running Unit Tests: CacheMetrics Dataclass")
    print("=" * 80)

    # Create fixtures
    pricing = PricingTier(
        model="google/gemini-2.0-flash-001",
        input_per_million=0.10,
        cached_input_per_million=0.01,
        output_per_million=0.30,
    )

    cache_hit = {
        "id": "gen-test123",
        "model": "google/gemini-2.0-flash-001",
        "choices": [{"message": {"role": "assistant", "content": "Test"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 2048, "completion_tokens": 342, "cached_tokens": 1523},
        "cache_discount": 0.2769,
    }

    cache_miss = {
        "id": "gen-test-miss",
        "model": "google/gemini-2.0-flash-001",
        "choices": [{"message": {"role": "assistant", "content": "Test"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 2048, "completion_tokens": 342, "cached_tokens": 0},
    }

    # Run tests
    print("\n[T024] Dataclass Validation:")
    print("-" * 80)
    test_cache_metrics_dataclass_fields()
    test_cache_metrics_to_dict_serialization()

    print("\n[T025] cost_saved Calculation:")
    print("-" * 80)
    test_cost_saved_calculation_cache_hit(pricing, cache_hit)
    test_cost_saved_calculation_cache_miss(pricing, cache_miss)
    test_cost_saved_edge_case_100_percent_cached(pricing)

    print("\n[T026] savings_percent Calculation:")
    print("-" * 80)
    test_savings_percent_calculation(pricing, cache_hit)
    test_savings_percent_zero_on_cache_miss(pricing, cache_miss)
    test_savings_percent_edge_case_100_percent(pricing)

    print("\n" + "=" * 80)
    print("All unit tests completed successfully!")
    print("=" * 80)
