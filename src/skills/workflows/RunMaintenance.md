# Run Maintenance Workflow

**Objective:** Trigger maintenance cycle to recalculate decay scores, transition lifecycle states, and clean up soft-deleted memories.

---

## Step 1: Announce Workflow

```bash
~/.claude/Tools/SkillWorkflowNotification RunMaintenance MadeinozKnowledgeSystem
```

**Output to user:**
```
Running the **RunMaintenance** workflow from the **MadeinozKnowledgeSystem** skill...
```

---

## Step 2: Verify Pre-Conditions

**Check server is running:**

```bash
bun run tools/knowledge-cli.ts health
```

**Expected response:**
```
✓ Server healthy
```

**If server is not healthy:**
- Stop and troubleshoot (see GetStatus workflow)
- Do not run maintenance on unhealthy system

---

## Step 3: Run Maintenance Cycle

**Use CLI (primary) to trigger maintenance:**

```bash
# Run full maintenance cycle
bun run tools/knowledge-cli.ts run_maintenance

# Dry run to preview changes
bun run tools/knowledge-cli.ts run_maintenance --dry-run
```

**Or use MCP tool (fallback only if CLI fails):**

```typescript
// Run full maintenance cycle
run_decay_maintenance({})
```

**Maintenance performs (in order):**
1. **Step 0:** Classify unclassified nodes (assign importance/stability)
2. **Step 1:** Recalculate decay scores for all memories
3. **Step 2:** Transition lifecycle states based on thresholds
4. **Step 3:** Soft-delete expired memories
5. **Step 4:** Purge soft-deleted memories past 90-day retention

**Expected completion time:** Under 10 minutes for graphs up to 10k memories

---

## Step 4: Present Maintenance Results

**Format maintenance results for user:**

```markdown
🔧 **Knowledge Graph Maintenance Complete**

---

**⏱️ Execution Summary**

- **Status:** [Success / Failed]
- **Duration:** [X.XX] seconds
- **Completed At:** [date/time]
- **Error:** [error message if failed]

---

**📊 Processing Statistics**

- **Total Memories Processed:** [N]
- **Nodes Classified:** [N]
  - Using LLM: [Yes/No]
  - Classified: [N]
  - Failed: [N]

---

**🔄 Decay Scores Updated**

- **Decay Scores Recalculated:** [N]

**Impact:**
- Memories with increased decay: [N]
- Memories with decreased decay: [N]
- Memories unchanged: [N]

---

**📋 Lifecycle State Transitions**

| Transition | Count | Details |
|------------|-------|---------|
| ACTIVE → DORMANT | [N] | 30+ days inactive |
| DORMANT → ARCHIVED | [N] | 90+ days inactive |
| ARCHIVED → EXPIRED | [N] | 180+ days, low importance |
| EXPIRED → SOFT_DELETED | [N] | Soft-delete retention started |
| DORMANT/ARCHIVED → ACTIVE | [N] | Reactivated on access |

**Net State Changes:**
- Active memories: [delta]
- Dormant memories: [delta]
- Archived memories: [delta]
- Expired memories: [delta]
- Soft-deleted memories: [delta]

---

**🗑️ Cleanup Operations**

- **Soft-Deleted Memories Purged:** [N]
  - Retention window expired (> 90 days)
  - Permanently removed from graph

**Soft-Deleted Retained:** [N]
  - Still within 90-day recovery window
  - Can be recovered if needed

---

**✅ Maintenance Summary**

Overall Result: [🟢 Success / 🟡 Warnings / 🔴 Failed]

**Next Scheduled Maintenance:** [recommendation based on completion time]
```

---

## Maintenance Parameters

**Default Configuration:**

```yaml
# config/decay-config.yaml
decay:
  base_half_life_days: 30
  retention:
    soft_delete_days: 90
  thresholds:
    dormant:
      days: 30
      decay_score: 0.3
    archived:
      days: 90
      decay_score: 0.5
    expired:
      days: 180
      decay_score: 0.7
      max_importance: 2

maintenance:
  batch_size: 500
  max_duration_seconds: 600  # 10 minutes
```

**Custom parameters (if needed):**

```typescript
// Run with custom parameters
run_decay_maintenance({
  batch_size: 1000,  // Larger batches for faster processing
  max_duration_seconds: 300  // 5-minute timeout
})
```

---

## Maintenance Frequency Recommendations

**Recommended Schedule:**

| Graph Size | Recommended Frequency |
|------------|----------------------|
| < 1,000 memories | Monthly |
| 1,000 - 10,000 memories | Weekly |
| 10,000 - 100,000 memories | Daily or Weekly |
| > 100,000 memories | Daily |

**Signs Maintenance is Needed:**

- Average decay scores seem stale (based on health report)
- New memories added but not classified
- Lifecycle states haven't changed recently
- Soft-deleted memories accumulating

---

## Maintenance Timeout Handling

**If maintenance exceeds 10-minute timeout:**

1. **Graceful Completion:** Maintenance stops at current batch
2. **Partial Results:** Returns progress up to timeout point
3. **Next Run:** Continues from where it left off

**To handle large graphs:**

```bash
# Run maintenance in multiple smaller batches
run_decay_maintenance({ batch_size: 100 })
# Repeat until all memories processed
```

---

## Troubleshooting

**Maintenance Fails:**

1. Check server health:
   ```bash
   bun run tools/knowledge-cli.ts health
   ```

2. Check database connectivity:
   ```bash
   # Neo4j
   curl http://localhost:7474

   # FalkorDB
   redis-cli -h localhost -p 6379 ping
   ```

3. Check container logs:
   ```bash
   bun run tools/logs.ts --mcp | tail -100
   ```

**Slow Maintenance:**

1. Run during off-peak hours
2. Check database performance
3. Review config/decay-config.yaml for batch_size settings (requires server restart)

**Classification Failures:**

- LLM unavailable: Falls back to defaults (importance=3, stability=3)
- Check LLM API key and quota
- Review logs for classification errors

---

## Post-Maintenance Actions

**After Successful Maintenance:**

1. **Review Health Report:**
   ```bash
   bun run tools/knowledge-cli.ts health_metrics
   ```

2. **Check for Unexpected Transitions:**
   - Many memories moved to DORMANT/ARCHIVED?
   - Permanent memories incorrectly transitioned? (should not happen)
   - High number of expired memories?

3. **Search by Lifecycle State:**
   ```bash
   # Find archived memories that might need recovery
   bun run tools/knowledge-cli.ts search_nodes "[topic]" --since 30d
   ```

4. **Recover Important Memories (if needed):**
   ```bash
   bun run tools/knowledge-cli.ts recover_memory "[uuid]"
   ```

---

## Integration with Other Workflows

**Before:**
- GetStatus - Ensure server is healthy
- HealthReport - Get baseline metrics before maintenance

**After:**
- HealthReport - Compare post-maintenance metrics: `bun run tools/knowledge-cli.ts health_metrics`
- SearchKnowledge - Find memories in specific states

**Related Workflows:**
- `HealthReport.md` - View detailed decay and lifecycle metrics
- `GetStatus.md` - Check server operational health
- `SearchKnowledge.md` - Find and review memories by lifecycle state
