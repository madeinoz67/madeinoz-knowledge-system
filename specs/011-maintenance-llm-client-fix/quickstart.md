# Quickstart: LLM Client for Maintenance Classification

**Feature**: 011-maintenance-llm-client-fix
**Branch**: `011-maintenance-llm-client-fix`

## What Changed

Fixed a bug where the maintenance service was not receiving the LLM client, causing all memory classifications to use default values (importance=3, stability=3) instead of intelligently classifying based on content.

**Two fixes implemented:**
1. **LLM Client Pass-through**: Pass `client.llm_client` to `get_maintenance_service()` at 4 call sites
2. **Immediate Background Classification**: Spawn classification task immediately after `add_memory()`

## Files Changed

| File | Lines Changed | Description |
|------|---------------|-------------|
| `docker/patches/graphiti_mcp_server.py` | ~20 lines | 4 `get_maintenance_service()` calls + background task in `add_memory()` |
| `docker/patches/importance_classifier.py` | 0 | No changes (already correct) |
| `docker/patches/maintenance_service.py` | 0 | No changes (already correct) |

## Testing the Fix

### 1. Start the Server

```bash
bun run server-cli start --dev
```

### 2. Add a Test Memory

```bash
# Add a critical memory (should get importance 4-5)
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts add "My SSH key is stored at ~/.ssh/id_rsa"

# Add a trivial memory (should get importance 1-2)
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts add "I bought coffee on Tuesday"
```

### 3. Check Health Metrics

```bash
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts health
```

**Expected Output**:
```
Knowledge Graph Health:
┌─────────────────┬──────────┐
│ State           │ Count    │
├─────────────────┼──────────┤
│ Active          │ X        │
│ Dormant         │ 0        │
│ Archived        │ 0        │
│ Expired         │ 0        │
│ Soft Deleted    │ 0        │
└─────────────────┴──────────┘

Importance Distribution:
┌─────────────────┬──────────┐
│ Level           │ Count    │
├─────────────────┼──────────┤
│ Trivial (1)     │ 1        │  ← Coffee memory
│ Low (2)         │ 0        │
│ Moderate (3)    │ 0        │  ← NOT all defaults!
│ High (4)        │ 0        │
│ Core (5)        │ 1        │  ← SSH key memory
└─────────────────┴──────────┘
```

### 4. Run Maintenance (Optional)

```bash
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts run_maintenance
```

**Expected Output**:
```
Starting maintenance (dry_run=False)
Step 0: Classifying unclassified nodes
Classified 0 new nodes (LLM=True)  ← Immediate classification already ran!
```

## Verification Checklist

- [ ] `add_memory` returns immediately (non-blocking)
- [ ] Health metrics show varying importance scores (not all 3.0)
- [ ] `run_decay_maintenance` logs "LLM=True" (not "LLM=False")
- [ ] Critical topics get importance 4-5
- [ ] Trivial topics get importance 1-2
- [ ] Server logs show "Spawned immediate background classification"

## Container Rebuild Required

After pulling these changes, rebuild the Docker image:

```bash
# From repository root
cd /Users/seaton/Documents/src/madeinoz-knowledge-system

# Rebuild image
docker build -f docker/Dockerfile -t madeinoz-knowledge-system:local .

# Restart containers
bun run server-cli stop
bun run server-cli start --dev
```

## Troubleshooting

### Issue: All importance scores still 3.0

**Cause**: LLM client not configured

**Fix**: Check environment variables:
```bash
# Should see LLM configuration
env | grep LLM
```

### Issue: Classification takes hours

**Cause**: Immediate background task not spawning

**Fix**: Check logs for "Spawned immediate background classification" message

### Issue: "LLM=False" in maintenance logs

**Cause**: `get_maintenance_service()` still not receiving llm_client

**Fix**: Verify all 4 call sites pass `llm_client=client.llm_client`

## Success Criteria

✅ **SC-001**: Maintenance classifications use LLM model (not defaults) in 100% of runs when LLM is configured and available

✅ **SC-002**: At least 80% of newly added entities receive non-default importance scores (not equal to 3)

✅ **SC-003**: Immediate background classification spawns within 1 second after add_memory returns

✅ **SC-006**: System recovers gracefully from LLM failures (maintenance completes successfully with logged fallback to defaults)
