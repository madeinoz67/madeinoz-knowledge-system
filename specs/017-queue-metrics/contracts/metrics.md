# Metrics Contract: QueueMetricsExporter

**Feature**: 017-queue-metrics
**Version**: 1.0.0
**Date**: 2026-02-03

## Contract Overview

This contract defines the public API of the `QueueMetricsExporter` class and the expected behavior of all metric recording methods.

## Class Definition

```python
class QueueMetricsExporter:
    """
    Manages OpenTelemetry/Prometheus metrics for queue processing.

    Thread-safe: All public methods are safe to call from multiple threads.
    Graceful degradation: Methods do nothing if metrics are disabled or unavailable.
    """

    def __init__(self, meter: Optional[Any] = None) -> None:
        """
        Initialize queue metrics exporter.

        Args:
            meter: OpenTelemetry meter instance (shared with other exporters).
                   If None, metrics will be disabled.

        Raises:
            ImportError: If OpenTelemetry is not available (caught by caller).
        """
```

## Public Methods

### record_enqueue()

**Purpose**: Record a message being enqueued for processing.

**Signature**:
```python
def record_enqueue(self, queue_name: str, priority: str) -> None
```

**Parameters**:
- `queue_name` (str): Name of the queue (e.g., "default", "maintenance")
- `priority` (str): Priority level ("low", "normal", "high")

**Side Effects**:
- Increments internal `_enqueued_total[queue_name]` counter
- Updates `messaging_queue_depth` gauge (increments)
- Records timestamp for wait time calculation

**Errors**: Silently logs warnings and continues if metrics unavailable

**Example**:
```python
queue_metrics.record_enqueue(queue_name="default", priority="normal")
```

---

### record_processing_start()

**Purpose**: Mark the start of message processing (returns context manager for timing).

**Signature**:
```python
@contextlib.contextmanager
def record_processing_start(self, queue_name: str) -> Iterator[None]
```

**Parameters**:
- `queue_name` (str): Name of the queue

**Side Effects**:
- Records start timestamp for duration calculation

**Example**:
```python
with queue_metrics.record_processing_start("default"):
    result = process_message()
```

---

### record_processing_complete()

**Purpose**: Record completion of message processing (success or failure).

**Signature**:
```python
def record_processing_complete(
    self,
    queue_name: str,
    duration: float,
    success: bool,
    error_type: Optional[str] = None
) -> None
```

**Parameters**:
- `queue_name` (str): Name of the queue
- `duration` (float): Processing duration in seconds
- `success` (bool): True if successful, False if failed
- `error_type` (str, optional): Type of error if success=False (e.g., "ConnectionError", "ValidationError")

**Side Effects**:
- Increments `messaging_messages_processed_total` with status label
- If success=False, increments `messaging_messages_failed_total` with error_type label
- Records `messaging_processing_duration_seconds` histogram
- Updates `messaging_queue_depth` gauge (decrements)
- Updates processing rate for lag calculation
- Records `messaging_end_to_end_latency_seconds` histogram

**Error Type Categories** (for consistency):
- `ConnectionError`: Network/database connection issues
- `ValidationError`: Invalid input data
- `TimeoutError`: Operation timed out
- `RateLimitError`: API rate limit exceeded
- `UnknownError`: Other errors

**Example**:
```python
try:
    await process_message()
    queue_metrics.record_processing_complete("default", 0.5, True)
except Exception as e:
    queue_metrics.record_processing_complete("default", 0.2, False, type(e).__name__)
```

---

### record_retry()

**Purpose**: Record a retry attempt for a failed message.

**Signature**:
```python
def record_retry(self, queue_name: str) -> None
```

**Parameters**:
- `queue_name` (str): Name of the queue

**Side Effects**:
- Increments `messaging_retries_total` counter

**Example**:
```python
if attempt > 1:
    queue_metrics.record_retry("default")
```

---

### update_queue_depth()

**Purpose**: Manually set the queue depth gauge (for external synchronization).

**Signature**:
```python
def update_queue_depth(self, queue_name: str, depth: int, priority: str) -> None
```

**Parameters**:
- `queue_name` (str): Name of the queue
- `depth` (int): Current queue depth (must be >= 0)
- `priority` (str): Priority level

**Side Effects**:
- Sets `messaging_queue_depth` gauge to exact value

**Use Case**: When queue depth is known from external source (e.g., QueueService exposes it in future)

**Example**:
```python
queue_metrics.update_queue_depth("default", 42, "normal")
```

---

### update_consumer_metrics()

**Purpose**: Update consumer health metrics (saturation, lag, active count).

**Signature**:
```python
def update_consumer_metrics(
    self,
    queue_name: str,
    consumer_group: str,
    active: int,
    saturation: float,
    lag_seconds: float
) -> None
```

**Parameters**:
- `queue_name` (str): Name of the queue
- `consumer_group` (str): Consumer group identifier
- `active` (int): Number of active consumers (>= 0)
- `saturation` (float): Utilization ratio 0.0 to 1.0
- `lag_seconds` (float): Time to catch up, in seconds (>= 0)

**Side Effects**:
- Sets `messaging_active_consumers` gauge
- Sets `messaging_consumer_saturation` gauge
- Sets `messaging_consumer_lag_seconds` gauge

**Use Case**: Called periodically (e.g., every 30 seconds) to update consumer health

**Example**:
```python
queue_metrics.update_consumer_metrics(
    queue_name="default",
    consumer_group="workers",
    active=1,
    saturation=0.65,
    lag_seconds=12.5
)
```

---

## Module-Level Functions

### initialize_queue_metrics_exporter()

**Purpose**: Initialize and return a QueueMetricsExporter instance.

**Signature**:
```python
def initialize_queue_metrics_exporter() -> Optional[QueueMetricsExporter]
```

**Returns**: QueueMetricsExporter instance or None if unavailable

**Side Effects**:
- Creates QueueMetricsExporter with shared meter from CacheMetricsExporter
- Logs initialization status

---

### get_queue_metrics_exporter()

**Purpose**: Get the global QueueMetricsExporter instance.

**Signature**:
```python
def get_queue_metrics_exporter() -> Optional[QueueMetricsExporter]
```

**Returns**: The exporter instance or None

---

## Metric Labels Reference

### queue_name
- **Type**: String
- **Values**: "default", "maintenance", or custom
- **Cardinality**: Low (typically 1-3)

### status
- **Type**: String
- **Values**: "success", "failure"
- **Cardinality**: 2

### error_type
- **Type**: String
- **Values**: "ConnectionError", "ValidationError", "TimeoutError", "RateLimitError", "UnknownError"
- **Cardinality**: Medium (5-10 typical)

### priority
- **Type**: String
- **Values**: "low", "normal", "high"
- **Cardinality**: 3

### consumer_group
- **Type**: String
- **Values**: "workers", "maintenance", or custom
- **Cardinality**: Low (typically 1-2)

## Thread Safety Guarantees

- All public methods are thread-safe
- Internal counters use `threading.Lock()` for synchronization
- OpenTelemetry metric operations are inherently thread-safe

## Error Handling

All methods follow these error handling rules:

1. **OpenTelemetry Unavailable**: Log warning and return silently
2. **Invalid Parameters**: Log error and return silently
3. **Metric Recording Failure**: Log warning and continue
4. **Never Raise**: Public methods never raise exceptions to caller

## Performance Constraints

- **Overhead per call**: < 50 microseconds (target)
- **Memory overhead**: < 1KB per queue
- **No blocking**: No I/O or network operations in hot path

## Testing Checklist

- [ ] Counter increments correctly on each call
- [ ] Gauge updates reflect correct values
- [ ] Histogram records durations in correct buckets
- [ ] Labels are applied correctly
- [ ] Thread safety under concurrent calls
- [ ] Graceful degradation when OpenTelemetry unavailable
- [ ] Memory usage doesn't grow unbounded
- [ ] No exceptions raised to caller
