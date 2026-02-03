# Quickstart: Queue Processing Metrics

**Feature**: 017-queue-metrics
**Date**: 2026-02-03

## Prerequisites

- Docker or Podman installed
- Madeinoz Knowledge System repository cloned
- Existing Prometheus/Grafana setup (optional, for dashboard)

## Step 1: Implement QueueMetricsExporter

**File**: `docker/patches/metrics_exporter.py`

Add the `QueueMetricsExporter` class following the pattern of `CacheMetricsExporter` and `DecayMetricsExporter`:

```python
class QueueMetricsExporter:
    """
    Manages OpenTelemetry/Prometheus metrics for queue processing.

    Provides counters, gauges, and histograms for tracking:
    - Message processing (success, failure, retries)
    - Queue depth and backlog growth
    - Processing latency and wait times
    - Consumer health (lag, saturation)
    """

    def __init__(self, meter: Optional[Any] = None):
        """Initialize queue metrics exporter."""
        self._meter = meter
        self._counters: Dict[str, Any] = {}
        self._gauges: Dict[str, Any] = {}
        self._histograms: Dict[str, Any] = {}
        # ... initialization code

    def _create_counters(self) -> None:
        """Create counter metrics."""
        # ... see contracts/metrics.md for full definitions

    def _create_gauges(self) -> None:
        """Create gauge metrics."""
        # ... see contracts/metrics.md for full definitions

    def _create_histograms(self) -> None:
        """Create histogram metrics."""
        # ... see contracts/metrics.md for full definitions

    # Public API methods
    def record_enqueue(self, queue_name: str, priority: str) -> None:
        """Record message enqueue event."""

    def record_processing_complete(self, queue_name: str, duration: float, success: bool, error_type: Optional[str] = None) -> None:
        """Record message processing completion."""
```

## Step 2: Add Queue Views to Meter Provider

**File**: `docker/patches/metrics_exporter.py` (in `CacheMetricsExporter._initialize_metrics()`)

Add queue histogram Views to the existing views list:

```python
# === Queue Metrics Views (Feature 017) ===
View(
    instrument_name="messaging_processing_duration_seconds",
    aggregation=ExplicitBucketHistogramAggregation(
        boundaries=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10]
    )
),
View(
    instrument_name="messaging_wait_time_seconds",
    aggregation=ExplicitBucketHistogramAggregation(
        boundaries=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10]
    )
),
View(
    instrument_name="messaging_end_to_end_latency_seconds",
    aggregation=ExplicitBucketHistogramAggregation(
        boundaries=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10]
    )
),
```

## Step 3: Initialize in MCP Server

**File**: `docker/patches/graphiti_mcp_server.py`

Add import and initialization:

```python
# Feature 017: Queue metrics exporter
try:
    from utils.metrics_exporter import initialize_queue_metrics_exporter, get_queue_metrics_exporter
    _queue_metrics_available = True
except ImportError:
    _queue_metrics_available = False

# In global variables section
queue_metrics_exporter: Optional[Any] = None

# In main() function, after decay metrics initialization
if _queue_metrics_available:
    try:
        queue_metrics_exporter = initialize_queue_metrics_exporter()
        if queue_metrics_exporter:
            logger.info("Madeinoz Patch: Feature 017 - Queue metrics exporter initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize queue metrics exporter: {e}")
```

## Step 4: Instrument Queue Operations

**File**: `docker/patches/graphiti_mcp_server.py`

Wrap the `queue_service.add_episode()` call (around line 862):

```python
# Record enqueue time for wait time calculation
enqueue_time = time.time()

if _queue_metrics_available and queue_metrics_exporter:
    try:
        queue_metrics_exporter.record_enqueue(
            queue_name=group_id or "default",
            priority="normal"  # or infer from context
        )
    except Exception as e:
        logger.warning(f"Failed to record enqueue metrics: {e}")

# Existing queue operation
await queue_service.add_episode(
    name=episode_name,
    episode_body=episode_body,
    group_id=group_id,
    source=source,
    source_description=source_description,
)

# Record processing completion
processing_duration = time.time() - enqueue_time
if _queue_metrics_available and queue_metrics_exporter:
    try:
        queue_metrics_exporter.record_processing_complete(
            queue_name=group_id or "default",
            duration=processing_duration,
            success=True
        )
    except Exception as e:
        logger.warning(f"Failed to record processing metrics: {e}")
```

## Step 5: Rebuild Containers

```bash
# Build with local changes
docker build -f docker/Dockerfile -t madeinoz-knowledge-system:local .

# Stop existing containers
bun run server-cli stop

# Start with development image
bun run server-cli start --dev
```

## Step 6: Verify Metrics

1. **Check Prometheus endpoint**:
   ```bash
   curl http://localhost:9090/metrics
   ```

2. **Look for queue metrics**:
   ```bash
   curl http://localhost:9090/metrics | grep messaging_
   ```

   Expected output:
   ```
   messaging_messages_processed_total{queue_name="default",status="success"} 42
   messaging_queue_depth{queue_name="default",priority="normal"} 5
   messaging_processing_duration_seconds_bucket{le="0.1"} 38
   # ... more metrics
   ```

3. **Send a test message**:
   ```bash
   bun run ~/.claude/skills/Knowledge/tools/capture.ts "test message for metrics"
   ```

4. **Verify metrics incremented**:
   ```bash
   curl http://localhost:9090/metrics | grep messaging_messages_processed_total
   ```

## Step 7: (Optional) Import Grafana Dashboard

The queue metrics dashboard provides a comprehensive view of queue processing health.

### Import Process

1. **Access Grafana**: Navigate to `http://localhost:3000` (default credentials: admin/admin)
2. **Import Dashboard**:
   - Click "+" → "Import Dashboard"
   - Upload `specs/017-queue-metrics/dashboard.json` via "Upload JSON file"
   - Or paste the JSON content directly
3. **Select Data Source**: Choose "Prometheus" as the data source
4. **View Dashboard**: The dashboard will load with panels for:
   - Queue Depth (current and over time)
   - Processing Latency (P50/P95/P99 percentiles)
   - Consumer Lag (Time to Catch Up)
   - Consumer Saturation (utilization gauge)
   - Throughput (Messages/Second)
   - Error Rate (percentage gauge)
   - Failures by Error Type (pie chart)
   - Retry Rate (Retries/Second)
   - Wait Time and End-to-End Latency

### Dashboard Features

- **Auto-refresh**: Every 10 seconds
- **Time range**: Last 1 hour by default (adjustable)
- **Color thresholds**:
  - Queue Depth: green (<10), yellow (10-50), red (>50)
  - Saturation: green (<50%), yellow (50-85%), red (>85%)
  - Lag: green (<30s), yellow (30-300s), red (>300s)
  - Error Rate: green (<1%), yellow (1-5%), red (>5%)
- **Responsive layout**: Panels rearrange based on screen size

### Customization

You can customize the dashboard by:
1. Clicking panel title → "Edit" to modify queries
2. Adjusting thresholds in field config for your alert levels
3. Adding additional panels for custom metrics
4. Saving as a new dashboard to preserve the original

### Screenshot Locations

After importing, the dashboard is accessible at:
- Dashboards → "Queue Processing Metrics"
- Direct URL: `http://localhost:3000/d/queue-metrics`

## Troubleshooting

### Metrics not appearing

1. Check OpenTelemetry is installed:
   ```bash
   docker exec <container> pip list | grep opentelemetry
   ```

2. Check logs for initialization errors:
   ```bash
   bun run server-cli logs | grep -i metrics
   ```

3. Verify Prometheus endpoint is accessible:
   ```bash
   curl http://localhost:9090/metrics | head
   ```

### Queue depth always zero

- Check that both `record_enqueue()` and `record_processing_complete()` are being called
- Verify queue_name matches between enqueue and dequeue
- Check for exceptions in metrics recording (logged as warnings)

### Lag showing NaN or infinity

- Processing rate calculation may have division by zero
- Ensure at least one message has been processed before calculating rate
- Add guard: `lag_seconds = depth / rate if rate > 0 else 0`

## Next Steps

After verification:

1. Run unit tests: `bun test tests/unit/metrics_exporter.test.py`
2. Run integration tests: `bun test tests/integration/queue_metrics.test.py`
3. Check performance impact: Monitor processing latency before/after
4. Set up alerting rules in Prometheus (see research.md for thresholds)
5. Create GitHub PR with changes

## Reference

- **Full API**: See [contracts/metrics.md](contracts/metrics.md)
- **Data Model**: See [data-model.md](data-model.md)
- **Research Findings**: See [research.md](research.md)
- **Main Spec**: See [spec.md](spec.md)
