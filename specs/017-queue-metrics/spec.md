# Feature Specification: Queue Processing Metrics

**Feature Branch**: `017-queue-metrics`
**Created**: 2026-02-03
**Status**: Draft
**Input**: GitHub Issue #61 - Queue processing metrics for input monitoring (queue depth, latency, throughput, consumer health)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Monitor Queue Backlog Growth (Priority: P1)

As a system operator, I want to see the current queue depth and backlog trends so that I can detect growing backlogs before they become critical problems.

**Why this priority**: This is the most critical observability gap - without visibility into queue depth, operators cannot detect when the knowledge system is falling behind processing incoming data, leading to unbounded delays and potential data loss.

**Independent Test**: Can be fully tested by (1) sending messages to the queue, (2) querying the metrics endpoint to verify queue depth is reported, and (3) visualizing the metric in a dashboard. Delivers immediate value by showing whether the system is keeping up with input load.

**Acceptance Scenarios**:

1. **Given** the system is processing messages normally, **When** I check the queue depth metric, **Then** I see the current number of messages waiting to be processed
2. **Given** messages are being enqueued faster than processed, **When** I observe the queue depth over time, **Then** I see the backlog increasing and can calculate time to catch up
3. **Given** the queue is empty and processing is keeping up, **When** I check queue depth, **Then** I see depth at or near zero

---

### User Story 2 - Detect Processing Latency Issues (Priority: P1)

As a system operator, I want to measure message processing latency so that I can identify performance regressions and ensure timely data ingestion.

**Why this priority**: Processing latency directly impacts user experience - slow processing means stale knowledge in the graph. Detecting latency spikes helps identify degradation before users are affected.

**Independent Test**: Can be fully tested by (1) sending test messages with known timestamps, (2) measuring processing duration via metrics, and (3) verifying latency percentiles are within acceptable thresholds. Delivers value by enabling SLA monitoring.

**Acceptance Scenarios**:

1. **Given** a message is processed successfully, **When** I query processing duration metrics, **Then** I see the time elapsed from enqueue to completion
2. **Given** processing is functioning normally, **When** I view P50/P95/P99 latency percentiles, **Then** I see values within expected performance targets
3. **Given** a performance regression occurs (e.g., slow database), **When** I check latency metrics, **Then** I see elevated percentiles indicating the problem

---

### User Story 3 - Monitor Consumer Health and Saturation (Priority: P2)

As a system operator, I want to see consumer utilization and lag so that I can identify degraded or crashed consumers before backlogs accumulate.

**Why this priority**: Consumer health monitoring enables proactive intervention - detecting a stuck consumer early prevents hours of backlog buildup. Critical for production reliability but secondary to basic depth/latency visibility.

**Independent Test**: Can be fully tested by (1) running normal consumers, (2) stopping a consumer to simulate failure, and (3) verifying lag and saturation metrics reflect the degraded state. Delivers value by enabling capacity planning.

**Acceptance Scenarios**:

1. **Given** consumers are healthy and keeping up, **When** I check consumer lag, **Then** I see lag expressed as time-to-catch-up (seconds), not raw message count
2. **Given** all consumers are operating normally, **When** I check consumer saturation, **Then** I see utilization below 85% indicating capacity headroom
3. **Given** a consumer crashes or slows down, **When** I observe lag and saturation metrics, **Then** I see lag increasing and saturation approaching 100%

---

### User Story 4 - Track Processing Failures and Retries (Priority: P2)

As a system operator, I want to see failure rates and retry counts so that I can identify problematic message types or systemic issues causing errors.

**Why this priority**: Failure tracking is essential for debugging but doesn't directly prevent incidents like backlog monitoring does. Provides diagnostic value after the fact.

**Independent Test**: Can be fully tested by (1) sending messages that will fail processing, (2) verifying failure counter increments, and (3) checking retry counts. Delivers value by enabling error rate alerting.

**Acceptance Scenarios**:

1. **Given** a message fails to process, **When** I query failure metrics, **Then** I see the failure counter incremented with error type label
2. **Given** failed messages are being retried, **When** I check retry metrics, **Then** I see retry count increasing
3. **Given** processing is healthy, **When** I view error rate (failures/total), **Then** I see it near zero

---

### User Story 5 - Visualize Metrics in Dashboard (Priority: P3)

As a system operator, I want a pre-built dashboard showing all queue metrics so that I can quickly assess system health without building custom visualizations.

**Why this priority**: Dashboards improve operator experience but don't provide new data - they present metrics already exposed by the system. Nice-to-have for usability but lowest priority for data availability.

**Independent Test**: Can be fully tested by (1) importing the dashboard into Grafana, (2) verifying all panels query the correct metrics, and (3) confirming data displays correctly. Delivers value by reducing time to insight.

**Acceptance Scenarios**:

1. **Given** the metrics are exposed, **When** I open the queue metrics dashboard, **Then** I see panels for queue depth, latency, consumer health, and throughput
2. **Given** I want historical context, **When** I adjust the time range on the dashboard, **Then** I see metrics plotted over the selected period
3. **Given** an alert threshold is breached, **When** I view the dashboard, **Then** I see the affected panel highlighted or annotated

---

### Edge Cases

- **Queue depth spikes**: What happens when a sudden influx of messages causes queue depth to exceed 10x normal levels? The metric should accurately report the depth without saturation or data loss.
- **Consumer crash**: How does the system handle metrics when all consumers crash? Lag should increase to infinity or a maximum value, saturation should show 100%.
- **Processing halt**: What happens when processing stops but messages continue arriving? Queue depth grows indefinitely, lag increases, wait time histogram buckets may overflow.
- **Zero metrics**: How are metrics reported when the queue has never had messages? Gauges should report zero, counters should start at 0, histograms should have no data.
- **Rapid retry loops**: What happens when a message fails repeatedly causing rapid retries? Retry counter should increment per attempt, failure counter should count each failure.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST expose a counter metric tracking total messages processed, labeled by queue name and status (success/failure)
- **FR-002**: System MUST expose a counter metric tracking total processing failures, labeled by queue name and error type
- **FR-003**: System MUST expose a counter metric tracking total retry attempts, labeled by queue name
- **FR-004**: System MUST expose a gauge metric showing current queue depth (number of messages waiting), labeled by queue name and priority level
- **FR-005**: System MUST expose a gauge metric showing consumer lag in seconds (time to catch up), labeled by queue name and consumer group
- **FR-006**: System MUST expose a gauge metric showing consumer saturation (0-1 ratio), labeled by queue name and consumer group
- **FR-007**: System MUST expose a gauge metric showing number of active consumers, labeled by queue name
- **FR-008**: System MUST expose a histogram metric showing message processing duration in seconds, with buckets covering microsecond to minute ranges
- **FR-009**: System MUST expose a histogram metric showing message wait time (time spent in queue before processing), with the same buckets as processing duration
- **FR-010**: System MUST expose a histogram metric showing end-to-end latency (from enqueue to completion), with the same buckets as processing duration
- **FR-011**: System MUST calculate consumer lag as time (seconds), not message count, using the formula: `lag_in_seconds = current_message_lag / average_processing_rate`
- **FR-012**: System MUST avoid high-cardinality labels (message IDs, timestamps, user IDs) that would cause metric explosion
- **FR-013**: System MUST make all metrics available via the existing Prometheus endpoint on port 9090
- **FR-014**: System MUST instrument enqueue and dequeue operations to capture queue depth changes
- **FR-015**: System MUST measure processing duration from message dequeue to completion (success or failure)
- **FR-016**: System MUST handle gracefully when metrics collection is not available (e.g., OpenTelemetry not installed) by logging a warning and continuing operation

### Key Entities

- **Queue Message**: Represents an item awaiting processing in the queue. Attributes: priority level, enqueue timestamp, dequeue timestamp, processing start/end timestamps, status (pending/processing/completed/failed), error type (if failed).
- **Queue**: Represents the message queue itself. Attributes: queue name, current depth (number of messages waiting), active consumer count.
- **Consumer**: Represents a worker processing messages from the queue. Attributes: consumer group ID, current saturation (ratio of active processing to capacity), lag in seconds (time to catch up on backlog).
- **Processing Attempt**: Represents one attempt to process a message. Attributes: attempt number (1 for initial, 2+ for retries), duration in seconds, result (success/failure), error type (if failed).
- **Metric**: Represents a collected measurement exposed via Prometheus. Attributes: metric name, type (counter/gauge/histogram), labels (key-value pairs), value.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Operators can identify a growing backlog within 5 minutes of onset by checking queue depth trends, reducing mean time to detection (MTTD) for capacity issues from hours to minutes
- **SC-002**: Operators can determine consumer health at a glance by viewing consumer lag expressed as time-to-catch-up, enabling immediate assessment of severity (e.g., "2 minutes behind" vs "5000 messages behind")
- **SC-003**: Processing latency regressions are detected within 1 minute by monitoring P95 latency percentiles, allowing rapid rollback of performance-degrading changes
- **SC-004**: System capacity planning is enabled by correlating queue depth, consumer saturation, and processing rate, allowing operators to predict when additional consumers are needed
- **SC-005**: Failed processing is debuggable by reviewing error type labels on failure metrics, reducing mean time to resolution (MTTR) for data ingestion issues
- **SC-006**: All metrics are queryable via the existing Prometheus endpoint without additional authentication or configuration, maintaining consistency with existing observability infrastructure
- **SC-007**: Dashboard users can assess overall queue health in under 30 seconds by viewing a single pre-built dashboard with panels for depth, latency, consumer health, and throughput

## Assumptions

- QueueService is already imported from the Graphiti library (`from services.queue_service import QueueService`) and will be instrumented rather than modified
- Existing metrics infrastructure (Prometheus exporter on port 9090, OpenTelemetry meter) is available for reuse
- Grafana is already deployed and configured with Prometheus as a data source
- Standard industry histogram buckets for latency (0.005s to 10s) are appropriate for this use case
- Consumer lag formula (`lag_in_seconds = current_lag / average_processing_rate`) assumes processing rate is measured as messages per second
- Alerting thresholds suggested in the issue (lag > 300s critical, depth > 2x batch size warning, saturation > 85% critical) are reasonable defaults but may need adjustment based on actual usage patterns
- Dashboard creation is optional (nice-to-have) and not required for the core feature to deliver value
