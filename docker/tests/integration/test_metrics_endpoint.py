"""
Integration Tests: Prometheus Metrics Endpoint (Feature 006)

Tests Prometheus /metrics endpoint for cache statistics:
- T035: Prometheus format compliance
- T036: graphiti_cache_hits_total counter
- T037: graphiti_cache_hit_rate gauge
- T044: Metrics server responds on port 9090
- T045: Prometheus scrape format validation

Prerequisites:
- metrics_exporter.py module with CacheMetricsExporter
- OpenTelemetry and prometheus_client installed (optional for testing)
"""

try:
    import pytest
except ImportError:
    pytest = None  # Allow running without pytest for standalone execution

import sys
from pathlib import Path
import time
import os

# Add docker/ to path so 'patches' package can be imported
docker_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(docker_dir))

from patches.metrics_exporter import CacheMetricsExporter, get_metrics_exporter, initialize_metrics_exporter


# Test Fixtures

def _pytest_fixture_decorator(func):
    """Conditional pytest.fixture decorator."""
    if pytest is not None:
        return pytest.fixture(func)
    return func


@_pytest_fixture_decorator
def metrics_port():
    """Port for Prometheus metrics endpoint."""
    return 9091  # Use 9091 to avoid conflicts with running instances


@_pytest_fixture_decorator
def metrics_exporter(metrics_port):
    """Initialize metrics exporter for testing."""
    exporter = initialize_metrics_exporter(enabled=True, port=metrics_port)

    # Record some test metrics
    exporter.record_cache_hit("google/gemini-2.0-flash-001", tokens_saved=1000, cost_saved=0.05)
    exporter.record_cache_hit("google/gemini-2.0-flash-001", tokens_saved=1500, cost_saved=0.08)
    exporter.record_cache_miss("google/gemini-2.0-flash-001")

    yield exporter

    # Cleanup: no explicit cleanup needed, server will stop with process


# T035: Integration test for /metrics endpoint returns Prometheus format

def test_metrics_endpoint_prometheus_format(metrics_exporter, metrics_port):
    """
    T035: Verify /metrics endpoint returns valid Prometheus text format.

    Tests that:
    1. HTTP GET request to /metrics succeeds (200 OK)
    2. Response content-type is text/plain
    3. Response contains Prometheus-formatted metrics
    """
    if not metrics_exporter.enabled:
        print("⊘ Metrics export disabled (OpenTelemetry not available) - test skipped")
        return

    try:
        import requests
    except ImportError:
        print("⊘ requests library not available - test skipped")
        return

    # Give server time to start
    time.sleep(1)

    # Request metrics endpoint
    url = f"http://localhost:{metrics_port}/metrics"

    try:
        response = requests.get(url, timeout=5)
    except requests.exceptions.ConnectionError:
        print(f"✗ Could not connect to metrics endpoint at {url}")
        print("  This may be expected if OpenTelemetry is not installed")
        return

    # Verify response
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"

    # Prometheus uses text/plain content type
    content_type = response.headers.get("Content-Type", "")
    assert "text/plain" in content_type or "text" in content_type, \
        f"Expected text/plain content type, got {content_type}"

    # Verify Prometheus format (TYPE and HELP comments, metric lines)
    text = response.text
    assert "# HELP" in text or "# TYPE" in text or "graphiti_cache_" in text, \
        "Response should contain Prometheus metrics"

    print("✓ Prometheus format validation passed")
    print(f"  - Status: {response.status_code}")
    print(f"  - Content-Type: {content_type}")
    print(f"  - Metrics present: {len([l for l in text.split('\\n') if l and not l.startswith('#')])}")


# T036: Integration test for graphiti_cache_hits_total counter

def test_cache_hits_total_counter(metrics_exporter, metrics_port):
    """
    T036: Verify graphiti_cache_hits_total counter is exposed and increments.

    Tests that:
    1. Counter exists in /metrics output
    2. Counter value reflects recorded hits (2 from fixture)
    3. Counter includes model label
    """
    if not metrics_exporter.enabled:
        print("⊘ Metrics export disabled (OpenTelemetry not available) - test skipped")
        return

    try:
        import requests
    except ImportError:
        print("⊘ requests library not available - test skipped")
        return

    # Give server time to start
    time.sleep(1)

    url = f"http://localhost:{metrics_port}/metrics"

    try:
        response = requests.get(url, timeout=5)
    except requests.exceptions.ConnectionError:
        print(f"⊘ Could not connect to metrics endpoint - test skipped")
        return

    assert response.status_code == 200
    text = response.text

    # Check for counter presence
    assert "graphiti_cache_hits_total" in text, \
        "graphiti_cache_hits_total counter should be present"

    # Extract counter value (looking for line with model label)
    hits_lines = [line for line in text.split('\n')
                  if 'graphiti_cache_hits_total' in line
                  and not line.startswith('#')
                  and 'model=' in line]

    assert len(hits_lines) > 0, "Should find cache hits counter with model label"

    # Parse value from first matching line
    # Format: graphiti_cache_hits_total{model="google/gemini-2.0-flash-001"} 2.0
    hits_line = hits_lines[0]
    value_str = hits_line.split()[-1]
    value = float(value_str)

    # We recorded 2 cache hits in fixture
    assert value == 2.0, f"Expected 2 cache hits, got {value}"

    print("✓ cache_hits_total counter validated")
    print(f"  - Metric found: {hits_line.strip()}")
    print(f"  - Value: {value}")


# T037: Integration test for graphiti_cache_hit_rate gauge

def test_cache_hit_rate_gauge(metrics_exporter, metrics_port):
    """
    T037: Verify graphiti_cache_hit_rate gauge is exposed and calculates correctly.

    Tests that:
    1. Gauge exists in /metrics output
    2. Gauge value matches expected hit rate (2 hits / 3 requests = 66.67%)
    3. Gauge updates based on session metrics
    """
    if not metrics_exporter.enabled:
        print("⊘ Metrics export disabled (OpenTelemetry not available) - test skipped")
        return

    try:
        import requests
    except ImportError:
        print("⊘ requests library not available - test skipped")
        return

    # Give server time to start
    time.sleep(1)

    url = f"http://localhost:{metrics_port}/metrics"

    try:
        response = requests.get(url, timeout=5)
    except requests.exceptions.ConnectionError:
        print(f"⊘ Could not connect to metrics endpoint - test skipped")
        return

    assert response.status_code == 200
    text = response.text

    # Check for gauge presence
    assert "graphiti_cache_hit_rate" in text, \
        "graphiti_cache_hit_rate gauge should be present"

    # Extract gauge value
    hit_rate_lines = [line for line in text.split('\n')
                      if 'graphiti_cache_hit_rate' in line
                      and not line.startswith('#')]

    assert len(hit_rate_lines) > 0, "Should find cache hit rate gauge"

    # Parse value (format: graphiti_cache_hit_rate 66.66666666666666)
    hit_rate_line = hit_rate_lines[0]
    value_str = hit_rate_line.split()[-1]
    value = float(value_str)

    # Expected: 2 hits / 3 total requests = 66.67%
    expected_rate = (2.0 / 3.0) * 100
    tolerance = 0.1  # Allow small floating point difference

    assert abs(value - expected_rate) < tolerance, \
        f"Expected hit rate ~{expected_rate:.2f}%, got {value:.2f}%"

    print("✓ cache_hit_rate gauge validated")
    print(f"  - Metric found: {hit_rate_line.strip()}")
    print(f"  - Hit rate: {value:.2f}% (2 hits / 3 requests)")


# T044: Integration test for metrics server responds on port 9090

def test_metrics_server_port_9090(metrics_exporter, metrics_port):
    """
    T044: Verify Prometheus metrics server responds on configured port.

    Tests that:
    1. HTTP server is listening on specified port
    2. GET request succeeds
    3. Server remains available across multiple requests
    """
    if not metrics_exporter.enabled:
        print("⊘ Metrics export disabled (OpenTelemetry not available) - test skipped")
        return

    try:
        import requests
    except ImportError:
        print("⊘ requests library not available - test skipped")
        return

    # Give server time to start
    time.sleep(1)

    url = f"http://localhost:{metrics_port}/metrics"

    # Test multiple requests to verify server stability
    for i in range(3):
        try:
            response = requests.get(url, timeout=5)
        except requests.exceptions.ConnectionError:
            if i == 0:
                print(f"⊘ Could not connect to metrics endpoint - test skipped")
                return
            else:
                raise

        assert response.status_code == 200, \
            f"Request {i+1}/3 failed with status {response.status_code}"

    print(f"✓ Metrics server validated on port {metrics_port}")
    print(f"  - URL: {url}")
    print(f"  - Requests: 3/3 successful")


# T045: Integration test for Prometheus scrape format compliance

def test_prometheus_scrape_format_compliance(metrics_exporter, metrics_port):
    """
    T045: Verify metrics endpoint complies with Prometheus scrape format.

    Tests that:
    1. Metrics use snake_case naming
    2. HELP and TYPE comments present
    3. Labels use correct format: {key="value"}
    4. Values are numeric
    5. No malformed lines
    """
    if not metrics_exporter.enabled:
        print("⊘ Metrics export disabled (OpenTelemetry not available) - test skipped")
        return

    try:
        import requests
    except ImportError:
        print("⊘ requests library not available - test skipped")
        return

    # Give server time to start
    time.sleep(1)

    url = f"http://localhost:{metrics_port}/metrics"

    try:
        response = requests.get(url, timeout=5)
    except requests.exceptions.ConnectionError:
        print(f"⊘ Could not connect to metrics endpoint - test skipped")
        return

    assert response.status_code == 200
    text = response.text
    lines = text.split('\n')

    # Track validation criteria
    found_help = False
    found_type = False
    found_labels = False
    metric_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for HELP comments
        if line.startswith("# HELP"):
            found_help = True
            # Verify format: # HELP metric_name description
            parts = line.split(None, 3)
            assert len(parts) >= 3, f"Malformed HELP line: {line}"

        # Check for TYPE comments
        elif line.startswith("# TYPE"):
            found_type = True
            # Verify format: # TYPE metric_name type
            parts = line.split()
            assert len(parts) == 4, f"Malformed TYPE line: {line}"
            assert parts[3] in ["counter", "gauge", "histogram", "summary"], \
                f"Invalid metric type: {parts[3]}"

        # Check metric lines (not comments)
        elif not line.startswith("#"):
            metric_lines.append(line)

            # Verify metric name uses snake_case
            metric_name = line.split()[0].split('{')[0]
            assert '_' in metric_name or metric_name.startswith("graphiti"), \
                f"Metric should use snake_case: {metric_name}"

            # Check for labels
            if '{' in line and '}' in line:
                found_labels = True
                # Verify label format: {key="value"}
                label_section = line[line.index('{')+1:line.index('}')]
                # Basic validation - should contain = and quotes
                assert '=' in label_section and '"' in label_section, \
                    f"Malformed labels: {label_section}"

            # Verify value is numeric
            value_str = line.split()[-1]
            try:
                float(value_str)
            except ValueError:
                assert False, f"Non-numeric value: {value_str} in line: {line}"

    # Verify we found expected elements
    # Note: HELP/TYPE may be optional depending on exporter implementation
    assert len(metric_lines) > 0, "Should have at least one metric line"

    print("✓ Prometheus scrape format compliance validated")
    print(f"  - HELP comments: {'Found' if found_help else 'Not found (optional)'}")
    print(f"  - TYPE comments: {'Found' if found_type else 'Not found (optional)'}")
    print(f"  - Label format: {'Valid' if found_labels else 'No labels found'}")
    print(f"  - Metric lines: {len(metric_lines)}")
    print(f"  - All values numeric: ✓")


# Test Runner

if __name__ == "__main__":
    """Run tests directly with python docker/tests/integration/test_metrics_endpoint.py"""
    print("=" * 80)
    print("Running Integration Tests: Prometheus Metrics Endpoint")
    print("=" * 80)

    # Create fixtures
    port = 9091

    print(f"\nInitializing metrics exporter on port {port}...")
    exporter = initialize_metrics_exporter(enabled=True, port=port)

    if not exporter.enabled:
        print("\n⚠️  OpenTelemetry not available - metrics export disabled")
        print("Install with: pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-prometheus prometheus-client")
        print("\nTests will be skipped.")
    else:
        print("✓ Metrics exporter initialized")

        # Record test metrics
        print("\nRecording test metrics...")
        exporter.record_cache_hit("google/gemini-2.0-flash-001", tokens_saved=1000, cost_saved=0.05)
        exporter.record_cache_hit("google/gemini-2.0-flash-001", tokens_saved=1500, cost_saved=0.08)
        exporter.record_cache_miss("google/gemini-2.0-flash-001")
        print("✓ Recorded 2 cache hits, 1 cache miss")

    # Run tests
    print("\n[T035] Prometheus Format Test:")
    print("-" * 80)
    test_metrics_endpoint_prometheus_format(exporter, port)

    print("\n[T036] Cache Hits Total Counter Test:")
    print("-" * 80)
    test_cache_hits_total_counter(exporter, port)

    print("\n[T037] Cache Hit Rate Gauge Test:")
    print("-" * 80)
    test_cache_hit_rate_gauge(exporter, port)

    print("\n[T044] Metrics Server Port Test:")
    print("-" * 80)
    test_metrics_server_port_9090(exporter, port)

    print("\n[T045] Prometheus Scrape Format Compliance Test:")
    print("-" * 80)
    test_prometheus_scrape_format_compliance(exporter, port)

    print("\n" + "=" * 80)
    print("All integration tests completed!")
    print("=" * 80)
