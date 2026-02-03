# Research: Queue Processing Metrics

**Feature**: 017-queue-metrics
**Date**: 2026-02-03
**Method**: Codebase analysis using codanna, grep, and file reading

## Question 1: How does QueueService expose queue state?

### Finding

QueueService is an external library from Graphiti (`from services.queue_service import QueueService`). Based on spec #011 research:

> **Key Findings**: Graphiti QueueService is external library with no hooks

QueueService does NOT expose internal queue state through public APIs. The interface is limited to:
- `queue_service.initialize(graphiti_client)` - Setup
- `queue_service.add_episode(...)` - Enqueue for processing

### Implications

We cannot directly query queue depth or consumer status from QueueService. Must use indirect measurement:

**Queue Depth Approximation**:
```
depth = enqueued_total - processed_total - failed_total
```

**Consumer Lag Calculation**:
```
processing_rate = processed_total / uptime_seconds
lag_seconds = depth / processing_rate (if rate > 0)
```

**Consumer Saturation**:
Since QueueService doesn't expose this, we may need to:
- Use a fixed assumption (e.g., single consumer, saturation = depth / batch_size)
- Skip this metric if not measurable
- Track via proxy (processing_stalled if depth > 0 and processed_total not increasing)

## Question 2: What instrumentation points exist?

### Finding

From codebase analysis of `docker/patches/graphiti_mcp_server.py`:

**Enqueue Point** (line 862):
```python
await queue_service.add_episode(
    name=episode_name,
    episode_body=episode_body,
    group_id=group_id,
    source=source,
    source_description=source_description,
)
```

This is the ONLY interaction point with QueueService in the codebase.

### Implications

- Wrap the `add_episode()` call with metrics recording
- Record enqueue timestamp for wait time calculation
- Record processing duration with try/except around the call
- No separate dequeue point visible - QueueService handles internally

**Instrumentation Pattern**:
```python
enqueue_time = time.time()
queue_metrics.record_enqueue(queue_name="default", priority="normal")

try:
    await queue_service.add_episode(...)
    duration = time.time() - enqueue_time
    queue_metrics.record_processing_complete("default", duration, True)
except Exception as e:
    duration = time.time() - enqueue_time
    queue_metrics.record_processing_complete("default", duration, False, error_type=type(e).__name__)
```

## Question 3: Does OpenTelemetry support required metric types?

### Finding

From analysis of `docker/patches/metrics_exporter.py`:

**Counters**: Fully supported via `meter.create_counter()`
- Used for: cache_hits_total, cache_misses_total, etc.

**Gauges**: Fully supported via `meter.create_gauge()`
- Used for: Decay state counts, importance/stability distributions

**Histograms**: Fully supported via `meter.create_histogram()` with custom buckets
- Used for: duration, cost, token distributions
- Custom buckets configured via `View` and `ExplicitBucketHistogramAggregation`

**Labels**: Fully supported via attributes dict
- Example: `{"model": "gpt-4o-mini", "cache_status": "hit"}`

### Implications

All required metric types from the spec are supported:
- Counters: messages_processed_total, messages_failed_total, retries_total
- Gauges: queue_depth, consumer_lag_seconds, consumer_saturation, active_consumers
- Histograms: processing_duration_seconds, wait_time_seconds, end_to_end_latency_seconds

**Bucket Configuration**:
The spec recommends buckets `[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10]`

These are slightly different from existing duration_buckets `[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 15.0, 30.0, 60.0, 120.0, 300.0]` but can be added as new Views.

## Question 4: What are the performance implications?

### Finding

From existing metrics implementation patterns:

**Overhead Sources**:
1. OpenTelemetry SDK operations (increment, record)
2. Prometheus HTTP server scrape (separate thread)
3. Dictionary lookups for label attributes

**Mitigation in Existing Code**:
- Graceful degradation if OpenTelemetry unavailable
- Optional enablement via `enabled` flag
- Shared meter across exporters (single Prometheus endpoint)

### Estimated Overhead

Based on typical OpenTelemetry overhead:
- Counter increment: ~1-5 microseconds
- Histogram recording: ~5-20 microseconds
- Gauge update: ~1-5 microseconds

Per message overhead: < 50 microseconds (well under 1ms target)

### Recommendations

1. Make metrics collection configurable (environment variable)
2. Use conditional checks: `if queue_metrics_enabled: ...`
3. Batch updates where possible (gauges can be updated less frequently)
4. Avoid high-cardinality labels (message_id, timestamp)

## Summary

| Question | Answer | Risk Level |
|----------|--------|------------|
| QueueService exposes state? | No - must approximate depth and lag | Medium |
| Instrumentation points? | Single point at add_episode() | Low |
| OpenTelemetry capable? | Yes - all metric types supported | None |
| Performance impact? | Negligible (< 50μs per message) | None |

## Implementation Notes

1. **Queue Depth Tracking**: Maintain running counters in QueueMetricsExporter
   - Increment on enqueue
   - Decrement on successful processing
   - Expose as gauge

2. **Consumer Saturation**: Since QueueService is opaque, use heuristic:
   - Assume single consumer
   - Track processing rate (messages/second over sliding window)
   - Saturation = (processing_rate / max_expected_rate) or skip

3. **Lag Calculation**:
   - Track `processed_total` and `uptime_seconds`
   - `processing_rate = processed_total / uptime_seconds`
   - `lag_seconds = queue_depth / processing_rate` (with div-by-zero guard)

4. **Priority Support**: The spec mentions priority labels, but QueueService.add_episode() doesn't expose priority. May need to:
   - Omit priority label (use "default" always)
   - Infer from source or other metadata
