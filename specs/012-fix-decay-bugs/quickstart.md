# Quickstart: Fix Decay Calculation Bugs

**Feature**: 012-fix-decay-bugs
**Branch**: `012-fix-decay-bugs`

## What Changed

Fixed three bugs in the memory decay scoring system:

1. **Config Path Mismatch (P1)**: Decay config file was not being copied to the expected location during container startup, causing 30-day default instead of 180-day configured half-life
2. **Stale Prometheus Metrics (P2)**: Gauge metrics were not refreshed after maintenance runs
3. **Timestamp NULL Handling (P3)**: Decay calculation could fail silently with NULL timestamps

## Files Changed

| File | Lines Changed | Description |
|------|---------------|-------------|
| `src/skills/server/entrypoint.sh` | +1 | Add decay config copy after database config copy |
| `docker/patches/maintenance_service.py` | +5 | Call `get_health_metrics()` after maintenance to refresh gauges |
| `docker/patches/memory_decay.py` | ~10 | Replace Cypher coalesce with safe CASE statement |

## Testing the Fixes

### 1. Rebuild and Start the Server

```bash
# From repository root
cd /Users/seaton/Documents/src/madeinoz-knowledge-system

# Rebuild image (required after code changes)
docker build -f docker/Dockerfile -t madeinoz-knowledge-system:local .

# Stop and restart containers
bun run server-cli stop
bun run server-cli start --dev
```

### 2. Verify Config Loading (Bug #1)

Check container logs for successful config loading:

```bash
bun run server-cli logs | grep -i "decay config"
```

**Expected**: `Loaded decay config from /app/mcp/config/decay-config.yaml`
**Bug indicator**: `Using default decay config` or no decay config message

### 3. Add Test Memories and Verify Decay Scores (Bug #1)

```bash
# Add a test memory
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts add "Test memory for decay verification"

# Wait a moment, then run maintenance
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts run_maintenance

# Check health metrics
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts health
```

**Expected**: 2-day-old memories should show ~0.46% decay (not 2.7%)

### 4. Verify Metrics Refresh (Bug #2)

```bash
# Run maintenance
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts run_maintenance

# Immediately query Prometheus endpoint
curl http://localhost:9090/metrics | grep knowledge_decay_score_avg

# Compare to direct database query
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts health
```

**Expected**: Prometheus `knowledge_decay_score_avg` matches the health report average

### 5. Verify NULL Timestamp Handling (Bug #3)

Create a test Entity with NULL timestamps directly in Neo4j:

```cypher
// In Neo4j Browser (localhost:7474)
CREATE (n:Entity {
  uuid: 'test-null-timestamps',
  name: 'Test NULL Node',
  created_at: NULL
})
```

Then run maintenance:

```bash
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts run_maintenance
```

**Expected**: No errors, node gets decay_score = 0.0

## Verification Checklist

- [ ] Container logs show "Loaded decay config from /app/mcp/config/decay-config.yaml"
- [ ] 2-day-old memories show ~0.46% decay (not 2.7%)
- [ ] Prometheus metrics match database averages immediately after maintenance
- [ ] Maintenance completes without errors when NULL timestamp nodes exist
- [ ] Server logs show "Gauge metrics refreshed after maintenance"

## Mathematical Verification

### Correct (180-day half-life)

```
For base=180, stability=3, importance=3, days=2:
half_life = 180 × 1.0 = 180
lambda = 0.693 / 180 = 0.00385
adjusted_rate = 0.00385 × 0.6 = 0.00231
decay = 1 - exp(-0.00231 × 2) = 0.0046 (0.46%)
```

### Bug (30-day half-life default)

```
For base=30, stability=3, importance=3, days=2:
half_life = 30 × 1.0 = 30
lambda = 0.693 / 30 = 0.0231
adjusted_rate = 0.0231 × 0.6 = 0.0139
decay = 1 - exp(-0.0139 × 2) = 0.027 (2.7%)
```

## Troubleshooting

### Issue: Decay scores still showing 2.7% for 2-day memories

**Cause**: Config still not being loaded

**Fix**:
1. Verify `/tmp/decay-config.yaml` exists in container: `docker exec <container> ls -la /tmp/`
2. Verify entrypoint.sh has the copy command
3. Rebuild image: `docker build --no-cache -f docker/Dockerfile -t madeinoz-knowledge-system:local .`

### Issue: Prometheus metrics still stale

**Cause**: `get_health_metrics()` call not executing or failing silently

**Fix**: Check server logs for "Failed to refresh gauge metrics" warning

### Issue: Maintenance fails with NULL timestamp errors

**Cause**: CASE statement not applied correctly

**Fix**: Verify `memory_decay.py` has the updated `BATCH_DECAY_UPDATE_QUERY`

## Success Criteria

- **SC-001**: Decay scores for 2-day-old moderate-importance memories ~0.46% (within 0.1% tolerance)
- **SC-002**: Prometheus `knowledge_decay_score_avg` matches actual average within 1%
- **SC-003**: Container startup logs indicate successful config loading
- **SC-004**: No silent failures with NULL timestamp values
- **SC-005**: System correctly calculates decay for 100% of Entity nodes
