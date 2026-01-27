"""
Unit Tests: SessionMetrics Dataclass (Feature 006)

Tests session-level accumulation of cache metrics:
- T027: SessionMetrics.record_request() accumulation logic

Prerequisites:
- session_metrics.py module with SessionMetrics
- cache_metrics.py module with CacheMetrics
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

from session_metrics import SessionMetrics
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
        input_per_million=0.10,
        cached_input_per_million=0.01,
        output_per_million=0.30,
    )


@_pytest_fixture_decorator
def cache_hit_metrics(sample_pricing):
    """Sample CacheMetrics for a cache hit."""
    return CacheMetrics(
        cache_hit=True,
        cached_tokens=1523,
        prompt_tokens=2048,
        completion_tokens=342,
        tokens_saved=1523,
        cost_without_cache=0.2562,
        actual_cost=0.1707,
        cost_saved=0.0855,
        savings_percent=33.37,
        model="google/gemini-2.0-flash-001",
    )


@_pytest_fixture_decorator
def cache_miss_metrics(sample_pricing):
    """Sample CacheMetrics for a cache miss."""
    return CacheMetrics(
        cache_hit=False,
        cached_tokens=0,
        prompt_tokens=2048,
        completion_tokens=342,
        tokens_saved=0,
        cost_without_cache=0.2562,
        actual_cost=0.2562,
        cost_saved=0.0,
        savings_percent=0.0,
        model="google/gemini-2.0-flash-001",
    )


# T027: SessionMetrics.record_request() accumulation

def test_session_metrics_initial_state():
    """
    T027: Verify SessionMetrics initializes to zero state.

    Tests that:
    1. All counters start at 0
    2. get_summary() returns zero values
    """
    session = SessionMetrics()

    assert session.total_requests == 0
    assert session.cache_hits == 0
    assert session.total_cached_tokens == 0
    assert session.total_cost_saved == 0.0

    summary = session.get_summary()
    assert summary["total_requests"] == 0
    assert summary["cache_hits"] == 0
    assert summary["cache_hit_rate"] == 0.0
    assert summary["total_cached_tokens"] == 0
    assert summary["total_cost_saved"] == 0.0

    print("✓ SessionMetrics initial state validated")


def test_record_request_single_cache_hit(cache_hit_metrics):
    """
    T027: Verify record_request() updates all counters for cache hit.

    Tests that:
    1. total_requests increments by 1
    2. cache_hits increments by 1
    3. total_cached_tokens increases
    4. total_cost_saved increases
    """
    session = SessionMetrics()

    session.record_request(cache_hit_metrics)

    assert session.total_requests == 1
    assert session.cache_hits == 1
    assert session.total_cached_tokens == 1523
    assert abs(session.total_cost_saved - 0.0855) < 0.0001

    summary = session.get_summary()
    assert summary["total_requests"] == 1
    assert summary["cache_hits"] == 1
    assert summary["cache_hit_rate"] == 100.0  # 1/1 = 100%

    print("✓ record_request() single cache hit validated")


def test_record_request_single_cache_miss(cache_miss_metrics):
    """
    T027: Verify record_request() updates counters for cache miss.

    Tests that:
    1. total_requests increments by 1
    2. cache_hits stays at 0
    3. total_cached_tokens stays at 0
    4. total_cost_saved stays at 0
    """
    session = SessionMetrics()

    session.record_request(cache_miss_metrics)

    assert session.total_requests == 1
    assert session.cache_hits == 0
    assert session.total_cached_tokens == 0
    assert session.total_cost_saved == 0.0

    summary = session.get_summary()
    assert summary["total_requests"] == 1
    assert summary["cache_hits"] == 0
    assert summary["cache_hit_rate"] == 0.0  # 0/1 = 0%

    print("✓ record_request() single cache miss validated")


def test_record_request_accumulation_multiple_hits(cache_hit_metrics):
    """
    T027: Verify record_request() accumulates across multiple requests.

    Tests that:
    1. Counters accumulate correctly
    2. cache_hit_rate reflects proportion of hits
    3. total_cached_tokens and total_cost_saved sum correctly
    """
    session = SessionMetrics()

    # Record 3 identical cache hits
    session.record_request(cache_hit_metrics)
    session.record_request(cache_hit_metrics)
    session.record_request(cache_hit_metrics)

    assert session.total_requests == 3
    assert session.cache_hits == 3
    assert session.total_cached_tokens == 1523 * 3  # 4569
    assert abs(session.total_cost_saved - (0.0855 * 3)) < 0.0001  # ~0.2565

    summary = session.get_summary()
    assert summary["total_requests"] == 3
    assert summary["cache_hits"] == 3
    assert summary["cache_hit_rate"] == 100.0  # 3/3 = 100%

    print("✓ record_request() multiple cache hits accumulation validated")


def test_record_request_mixed_hits_and_misses(cache_hit_metrics, cache_miss_metrics):
    """
    T027: Verify record_request() handles mixed cache hit/miss pattern.

    Tests that:
    1. Counters distinguish hits from misses
    2. cache_hit_rate calculates correctly with mixed results
    3. Totals only accumulate from cache hits
    """
    session = SessionMetrics()

    # Pattern: HIT, MISS, HIT, MISS, HIT = 3 hits, 2 misses
    session.record_request(cache_hit_metrics)
    session.record_request(cache_miss_metrics)
    session.record_request(cache_hit_metrics)
    session.record_request(cache_miss_metrics)
    session.record_request(cache_hit_metrics)

    assert session.total_requests == 5
    assert session.cache_hits == 3
    assert session.total_cached_tokens == 1523 * 3  # Only hits contribute
    assert abs(session.total_cost_saved - (0.0855 * 3)) < 0.0001  # Only hits contribute

    summary = session.get_summary()
    assert summary["total_requests"] == 5
    assert summary["cache_hits"] == 3
    assert abs(summary["cache_hit_rate"] - 60.0) < 0.01  # 3/5 = 60%

    print("✓ record_request() mixed pattern accumulation validated")
    print(f"  - cache_hit_rate: {summary['cache_hit_rate']:.1f}%")


def test_record_request_varying_costs(sample_pricing):
    """
    T027: Verify record_request() handles varying cache_metrics values.

    Tests that:
    1. Different cost_saved values accumulate correctly
    2. Different cached_tokens values sum correctly
    3. cache_hit tracking is binary per request
    """
    session = SessionMetrics()

    # Create varying cache hit metrics
    hit1 = CacheMetrics(
        cache_hit=True, cached_tokens=1000, prompt_tokens=2000, completion_tokens=300,
        tokens_saved=1000, cost_without_cache=0.20, actual_cost=0.15, cost_saved=0.05,
        savings_percent=25.0, model="google/gemini-2.0-flash-001",
    )
    hit2 = CacheMetrics(
        cache_hit=True, cached_tokens=1500, prompt_tokens=2500, completion_tokens=400,
        tokens_saved=1500, cost_without_cache=0.30, actual_cost=0.20, cost_saved=0.10,
        savings_percent=33.33, model="google/gemini-2.0-flash-001",
    )
    hit3 = CacheMetrics(
        cache_hit=True, cached_tokens=2000, prompt_tokens=3000, completion_tokens=500,
        tokens_saved=2000, cost_without_cache=0.40, actual_cost=0.25, cost_saved=0.15,
        savings_percent=37.5, model="google/gemini-2.0-flash-001",
    )

    session.record_request(hit1)
    session.record_request(hit2)
    session.record_request(hit3)

    assert session.total_requests == 3
    assert session.cache_hits == 3
    assert session.total_cached_tokens == 1000 + 1500 + 2000  # 4500
    assert abs(session.total_cost_saved - (0.05 + 0.10 + 0.15)) < 0.0001  # 0.30

    print("✓ record_request() varying costs accumulation validated")


def test_get_summary_comprehensive(cache_hit_metrics, cache_miss_metrics):
    """
    T027: Verify get_summary() returns all required fields.

    Tests that:
    1. All summary fields are present
    2. cache_hit_rate calculates correctly
    3. Totals match accumulated values
    """
    session = SessionMetrics()

    # Pattern: HIT, HIT, MISS, HIT = 3 hits, 1 miss, 4 total
    session.record_request(cache_hit_metrics)
    session.record_request(cache_hit_metrics)
    session.record_request(cache_miss_metrics)
    session.record_request(cache_hit_metrics)

    summary = session.get_summary()

    # Verify all fields present
    assert "total_requests" in summary
    assert "cache_hits" in summary
    assert "cache_hit_rate" in summary
    assert "total_cached_tokens" in summary
    assert "total_cost_saved" in summary

    # Verify values
    assert summary["total_requests"] == 4
    assert summary["cache_hits"] == 3
    assert abs(summary["cache_hit_rate"] - 75.0) < 0.01  # 3/4 = 75%
    assert summary["total_cached_tokens"] == 1523 * 3  # 4569
    assert abs(summary["total_cost_saved"] - (0.0855 * 3)) < 0.0001  # ~0.2565

    print("✓ get_summary() comprehensive validation passed")
    print(f"  - total_requests: {summary['total_requests']}")
    print(f"  - cache_hits: {summary['cache_hits']}")
    print(f"  - cache_hit_rate: {summary['cache_hit_rate']:.1f}%")
    print(f"  - total_cached_tokens: {summary['total_cached_tokens']}")
    print(f"  - total_cost_saved: ${summary['total_cost_saved']:.4f}")


def test_cache_hit_rate_edge_cases():
    """
    T027: Verify cache_hit_rate handles edge cases.

    Tests:
    1. 0% hit rate (all misses)
    2. 100% hit rate (all hits)
    3. Division by zero protection (no requests)
    """
    # Edge case 1: All misses
    session_all_misses = SessionMetrics()
    miss_metrics = CacheMetrics(
        cache_hit=False, cached_tokens=0, prompt_tokens=2000, completion_tokens=300,
        tokens_saved=0, cost_without_cache=0.20, actual_cost=0.20, cost_saved=0.0,
        savings_percent=0.0, model="test-model",
    )
    session_all_misses.record_request(miss_metrics)
    session_all_misses.record_request(miss_metrics)

    summary_misses = session_all_misses.get_summary()
    assert summary_misses["cache_hit_rate"] == 0.0

    # Edge case 2: All hits
    session_all_hits = SessionMetrics()
    hit_metrics = CacheMetrics(
        cache_hit=True, cached_tokens=1000, prompt_tokens=2000, completion_tokens=300,
        tokens_saved=1000, cost_without_cache=0.20, actual_cost=0.15, cost_saved=0.05,
        savings_percent=25.0, model="test-model",
    )
    session_all_hits.record_request(hit_metrics)
    session_all_hits.record_request(hit_metrics)

    summary_hits = session_all_hits.get_summary()
    assert summary_hits["cache_hit_rate"] == 100.0

    # Edge case 3: No requests (division by zero protection)
    session_empty = SessionMetrics()
    summary_empty = session_empty.get_summary()
    assert summary_empty["cache_hit_rate"] == 0.0  # Should not crash

    print("✓ cache_hit_rate edge cases validated")


# Test Runner

if __name__ == "__main__":
    """Run tests directly with python docker/tests/unit/test_session_metrics.py"""
    print("=" * 80)
    print("Running Unit Tests: SessionMetrics Dataclass")
    print("=" * 80)

    # Create fixtures
    pricing = PricingTier(
        model="google/gemini-2.0-flash-001",
        input_per_million=0.10,
        cached_input_per_million=0.01,
        output_per_million=0.30,
    )

    hit_metrics = CacheMetrics(
        cache_hit=True, cached_tokens=1523, prompt_tokens=2048, completion_tokens=342,
        tokens_saved=1523, cost_without_cache=0.2562, actual_cost=0.1707, cost_saved=0.0855,
        savings_percent=33.37, model="google/gemini-2.0-flash-001",
    )

    miss_metrics = CacheMetrics(
        cache_hit=False, cached_tokens=0, prompt_tokens=2048, completion_tokens=342,
        tokens_saved=0, cost_without_cache=0.2562, actual_cost=0.2562, cost_saved=0.0,
        savings_percent=0.0, model="google/gemini-2.0-flash-001",
    )

    # Run tests
    print("\n[T027] SessionMetrics Accumulation:")
    print("-" * 80)
    test_session_metrics_initial_state()
    test_record_request_single_cache_hit(hit_metrics)
    test_record_request_single_cache_miss(miss_metrics)
    test_record_request_accumulation_multiple_hits(hit_metrics)
    test_record_request_mixed_hits_and_misses(hit_metrics, miss_metrics)
    test_record_request_varying_costs(pricing)
    test_get_summary_comprehensive(hit_metrics, miss_metrics)
    test_cache_hit_rate_edge_cases()

    print("\n" + "=" * 80)
    print("All unit tests completed successfully!")
    print("=" * 80)
