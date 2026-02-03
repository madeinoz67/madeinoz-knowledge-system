# Data Model: Queue Processing Metrics

**Feature**: 017-queue-metrics
**Date**: 2026-02-03

## Overview

This document describes the data structures and metric definitions for the QueueMetricsExporter. The model follows OpenTelemetry semantic conventions for messaging metrics where applicable.

## Metric Definitions

### Counter Metrics (monotonically increasing)

#### messaging_messages_processed_total
- **Type**: Counter
- **Unit**: 1 (messages)
- **Description**: Total number of messages processed successfully
- **Labels**:
  - `queue_name` (str): Name of the queue (e.g., "default", "maintenance")
  - `status` (str): "success" or "failure"

#### messaging_messages_failed_total
- **Type**: Counter
- **Unit**: 1 (failures)
- **Description**: Total number of message processing failures
- **Labels**:
  - `queue_name` (str): Name of the queue
  - `error_type` (str): Type of error (e.g., "ConnectionError", "ValidationError", "Timeout")

#### messaging_retries_total
- **Type**: Counter
- **Unit**: 1 (retry attempts)
- **Description**: Total number of retry attempts
- **Labels**:
  - `queue_name` (str): Name of the queue

### Gauge Metrics (point-in-time state)

#### messaging_queue_depth
- **Type**: Gauge
- **Unit**: 1 (messages)
- **Description**: Current number of messages waiting in the queue
- **Labels**:
  - `queue_name` (str): Name of the queue
  - `priority` (str): Priority level ("low", "normal", "high")

**Calculation**: `queue_depth = enqueued_total - processed_total - failed_total`

#### messaging_consumer_lag_seconds
- **Type**: Gauge
- **Unit**: seconds (s)
- **Description**: Time for consumer to catch up on current backlog
- **Labels**:
  - `queue_name` (str): Name of the queue
  - `consumer_group` (str): Consumer group identifier

**Calculation**: `lag_seconds = queue_depth / processing_rate` (with div-by-zero guard)

#### messaging_consumer_saturation
- **Type**: Gauge
- **Unit**: 1 (ratio 0-1)
- **Description**: Consumer utilization ratio
- **Labels**:
  - `queue_name` (str): Name of the queue
  - `consumer_group` (str): Consumer group identifier

**Note**: Since QueueService doesn't expose internal metrics, this may be calculated as:
- `saturation = min(1.0, processing_rate / max_expected_rate)`
- Or omitted if not measurable

#### messaging_active_consumers
- **Type**: Gauge
- **Unit**: 1 (consumers)
- **Description**: Number of active consumers
- **Labels**:
  - `queue_name` (str): Name of the queue

**Note**: QueueService doesn't expose this. Will be set to 1 (single consumer) or omitted.

### Histogram Metrics (distributions)

#### messaging_processing_duration_seconds
- **Type**: Histogram
- **Unit**: seconds (s)
- **Description**: Time taken to process a single message
- **Buckets**: `[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10]`
- **Labels**: None (to avoid cardinality)

#### messaging_wait_time_seconds
- **Type**: Histogram
- **Unit**: seconds (s)
- **Description**: Time message spends waiting in queue before processing
- **Buckets**: Same as processing_duration_seconds
- **Labels**: None

**Calculation**: `wait_time = processing_start_time - enqueue_time`

#### messaging_end_to_end_latency_seconds
- **Type**: Histogram
- **Unit**: seconds (s)
- **Description**: Total time from message enqueue to completion
- **Buckets**: Same as processing_duration_seconds
- **Labels**: None

**Calculation**: `e2e_latency = processing_duration + wait_time`

## Internal State Structures

### QueueMetricsExporter State

```python
class QueueMetricsExporter:
    # OpenTelemetry meter (shared with other exporters)
    _meter: Optional[Any]

    # Metric instruments
    _counters: Dict[str, Counter]
    _gauges: Dict[str, Gauge]
    _histograms: Dict[str, Histogram]

    # Running counters for gauge calculations
    _enqueued_total: Dict[str, int]        # queue_name -> count
    _processed_total: Dict[str, int]       # queue_name -> count
    _failed_total: Dict[str, int]          # queue_name -> count

    # Timing state for wait time calculation
    _enqueue_times: Dict[str, float]       # message_id -> timestamp

    # Processing rate tracking for lag calculation
    _processing_start_time: float          # Server start time
    _last_processed_count: Dict[str, int]  # For rate calculation
```

## Data Flow

```
User Request
    |
    v
[Enqueue] ----> record_enqueue() ----> counter(enqueued_total)++
    |                                        |
    |                                        v
    |                                   gauge(queue_depth)++
    |
    v
queue_service.add_episode()
    |
    +---> Success ----> record_processing_complete() ----> counter(processed_total)++
    |                                                          |
    |                                                          v
    |                                                     gauge(queue_depth)--
    |                                                          |
    |                                                          v
    |                                                     histogram(duration)++
    |
    +---> Failure ----> record_processing_complete(error) ----> counter(failed_total)++
                                                                     |
                                                                     v
                                                                counter(failures)++
```

## Label Cardinality Analysis

| Label | Cardinality | Risk | Mitigation |
|-------|-------------|------|------------|
| queue_name | Low (1-3) | Low | Fixed set of queue names |
| status | Low (2) | Low | Only "success" or "failure" |
| error_type | Medium (5-20) | Medium | Use coarse categories (e.g., "Timeout" not "Timeout: ConnectionRefused: localhost:8080") |
| priority | Low (3) | Low | "low", "normal", "high" |
| consumer_group | Low (1-2) | Low | Usually single group |

**Total estimated cardinality**: ~3 queues × 2 statuses × ~10 error types × 3 priorities = ~180 series (acceptable)

## Prometheus Query Examples

### Queue Depth Over Time
```promql
messaging_queue_depth{queue_name="default"}
```

### Processing Latency P95
```promql
histogram_quantile(0.95,
  sum(rate(messaging_processing_duration_seconds_bucket[5m])) by (le)
)
```

### Consumer Lag (Time to Catch Up)
```promql
messaging_consumer_lag_seconds{queue_name="default"}
```

### Error Rate
```promql
sum(rate(messaging_messages_failed_total[5m])) /
sum(rate(messaging_messages_processed_total[5m])) * 100
```

### Throughput (messages/second)
```promql
sum(rate(messaging_messages_processed_total{status="success"}[5m]))
```

## Implementation Considerations

1. **Thread Safety**: OpenTelemetry instruments are thread-safe, but internal counters should use threading.Lock() if accessed from multiple threads.

2. **Metric Persistence**: Counts reset on server restart. For persistent metrics, use Prometheus's recording rules or external aggregation.

3. **Histogram Memory**: Each histogram with 14 buckets uses ~200-300 bytes. With 3 histograms, memory overhead is < 1KB per queue.

4. **Exponential Backoff**: If queue is growing (depth increasing exponentially), consider adding an alert on `rate(messaging_queue_depth[5m]) > 0`.

5. **Missing Data**: When no messages are processed, counters stop incrementing (stale metrics). Gauges should still report current state (depth = 0 when empty).
