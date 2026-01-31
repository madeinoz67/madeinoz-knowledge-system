# Quickstart: Memory Access Metrics

**Feature**: 015-memory-access-metrics
**Audience**: Knowledge system maintainers and developers

## Overview

This feature instruments search operations to record memory access patterns (importance, lifecycle state, age) for visualization in the Memory Access Patterns dashboard.

## Prerequisites

- Knowledge system containers running (`bun run server-cli start`)
- Grafana accessible at http://localhost:3000
- Memory Access Patterns dashboard deployed (feature #37 / PR #42)

## Verifying Metrics

### Check Metrics Endpoint

```bash
# Check if metrics are being exported
curl -s http://localhost:9091/metrics | grep "knowledge_access_by"

# Expected output:
# knowledge_access_by_importance_total{level="CRITICAL"} N
# knowledge_access_by_importance_total{level="HIGH"} N
# knowledge_access_by_importance_total{level="MEDIUM"} N
# knowledge_access_by_importance_total{level="LOW"} N
```

### Generate Test Data

```bash
# Use knowledge CLI to perform searches (generates access metrics)
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts --profile development search_nodes "test"
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts --profile development search_facts "test"
```

### View Dashboard

1. Open Grafana: http://localhost:3000 (or http://localhost:3002 for dev)
2. Navigate to Dashboards → Browse
3. Select "Memory Access Patterns"
4. Verify panels show data (not "No data")

## Troubleshooting

### Metrics Not Appearing

1. **Verify containers are running**:
   ```bash
   bun run server-cli status
   ```

2. **Check metrics endpoint**:
   ```bash
   curl http://localhost:9091/metrics | grep knowledge_access
   ```

3. **Rebuild containers** (if code was changed):
   ```bash
   docker build -f docker/Dockerfile -t madeinoz-knowledge-system:local .
   bun run server-cli stop
   bun run server-cli start --dev
   ```

### Dashboard Shows "No Data"

1. **Perform search operations** to generate metrics
2. **Wait 30-60 seconds** for Prometheus to scrape metrics
3. **Check time range** - dashboard defaults to 24h, ensure recent activity is visible
4. **Refresh dashboard** (auto-refreshes every 30s)

### Incorrect Labels

If importance labels don't match (CORE instead of CRITICAL):
1. Check `metrics_exporter.py` line ~1438 for label mapping
2. Rebuild and restart containers
3. Clear Prometheus metrics or wait for next scrape

## Development

### Running Tests

```bash
# Run Python tests for access metrics
cd docker/patches
pytest tests/test_access_metrics.py -v
```

### Adding New Metrics

Follow the pattern in `metrics_exporter.py`:
1. Define metric in `_create_counters()` or `_create_histograms()`
2. Add recording function (e.g., `record_*()`)
3. Call recording function from appropriate location
4. Update `docs/reference/observability.md`
5. Add dashboard panel if needed

## Related Documentation

- [Memory Access Patterns Dashboard](../014-memory-access-dashboard/)
- [Observability & Metrics](../../../docs/reference/observability.md)
- [Memory Decay Scoring](../009-memory-decay-scoring/)
