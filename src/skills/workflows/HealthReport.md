# Health Report Workflow

**Objective:** Get detailed memory decay metrics, lifecycle state distribution, and knowledge graph health information.

---

## Step 1: Announce Workflow

```bash
~/.claude/Tools/SkillWorkflowNotification HealthReport MadeinozKnowledgeSystem
```

**Output to user:**
```
Running the **HealthReport** workflow from the **MadeinozKnowledgeSystem** skill...
```

---

## Step 2: Get Knowledge Health Metrics

**Use MCP tool for detailed health metrics:**

```typescript
// Get comprehensive health report with decay metrics
get_knowledge_health({})
```

**This returns:**
- Memory counts by lifecycle state (ACTIVE, DORMANT, ARCHIVED, EXPIRED, SOFT_DELETED, PERMANENT)
- Aggregate statistics (total, average decay, average importance, average stability)
- Age distribution (under 7 days, 7-30 days, 30-90 days, over 90 days)
- Last maintenance run information

---

## Step 3: Present Health Report

**Format health information for user:**

```markdown
📊 **Knowledge Graph Health Report**
 Memory Decay & Lifecycle Status

---

**🔄 Memory Lifecycle Distribution**

| State | Count | Percentage | Description |
|-------|-------|------------|-------------|
| **ACTIVE** | [N] | [X]% | Recently accessed, full relevance |
| **DORMANT** | [N] | [X]% | Not accessed 30+ days |
| **ARCHIVED** | [N] | [X]% | Not accessed 90+ days |
| **EXPIRED** | [N] | [X]% | Marked for deletion |
| **SOFT_DELETED** | [N] | [X]% | Deleted but recoverable (90 days) |
| **PERMANENT** | [N] | [X]% | Exempt from decay (importance ≥4, stability ≥4) |

---

**📈 Aggregate Metrics**

**Total Memories:** [N] (excluding soft-deleted)

**Decay Scores:**
- Average Decay Score: [X.XX] (0.0 = fresh, 1.0 = fully decayed)
- Decay Rate: [healthy/elevated/concerning]

**Classification:**
- Average Importance: [X.XX]/5.0 (1=trivial, 5=core)
- Average Stability: [X.XX]/5.0 (1=volatile, 5=permanent)

---

**📅 Memory Age Distribution**

| Age Bucket | Count | Percentage |
|------------|-------|------------|
| **Under 7 days** | [N] | [X]% |
| **7-30 days** | [N] | [X]% |
| **30-90 days** | [N] | [X]% |
| **Over 90 days** | [N] | [X]% |

---

**⚙️ Last Maintenance**

- **Last Run:** [date/time]
- **Duration:** [X.XX] seconds
- **Memories Processed:** [N]
- **State Transitions:** [N]
- **Decay Scores Updated:** [N]
- **Soft-Deleted Purged:** [N]

---

**🎯 Health Status**

Overall Status: [🟢 Healthy / 🟡 Warning / 🔴 Action Needed]

**Recommendations:**
- [Based on metrics above]
```

---

## Health Indicators

**🟢 Healthy Status:**
- Average decay score < 0.4
- Active memories > 50%
- Dormant + Archived < 30%
- No expired memories
- Maintenance ran within last 7 days

**🟡 Warning Status:**
- Average decay score 0.4-0.6
- Active memories 30-50%
- Dormant + Archived 30-50%
- Few expired memories (< 10)
- Maintenance ran 7-14 days ago

**🔴 Action Needed:**
- Average decay score > 0.6
- Active memories < 30%
- Dormant + Archived > 50%
- Many expired memories (> 10)
- Maintenance not run in 14+ days

---

## Decay Score Interpretation

**What Decay Scores Mean:**

| Score Range | Interpretation | Action |
|-------------|----------------|--------|
| 0.0 - 0.2 | Fresh | No action needed |
| 0.2 - 0.4 | Slightly stale | Consider re-accessing if important |
| 0.4 - 0.6 | Moderately stale | May transition to DORMANT soon |
| 0.6 - 0.8 | Significantly stale | Likely DORMANT/ARCHIVED, consider reviewing |
| 0.8 - 1.0 | Fully decayed | Candidate for archival/deletion |

**Factors Affecting Decay:**
- **Time since last access** - Primary factor
- **Stability score** - Higher stability = slower decay
- **Importance score** - Higher importance = slower decay
- **Permanent memories** (importance ≥4, stability ≥4) - Never decay

---

## Lifecycle State Transitions

**Automatic Transitions (During Maintenance):**

```
ACTIVE → DORMANT (30+ days inactive, decay ≥ 0.3)
   ↓
DORMANT → ARCHIVED (90+ days inactive, decay ≥ 0.5)
   ↓
ARCHIVED → EXPIRED (180+ days inactive, decay ≥ 0.7, importance < 3)
   ↓
EXPIRED → SOFT_DELETED (on maintenance run)
   ↓
SOFT_DELETED → (purged after 90-day retention)
```

**Reactivation (On Access):**
- Any access to DORMANT or ARCHIVED memory → immediately back to ACTIVE
- Decay score resets to 0.0
- Last accessed timestamp updated

**Permanent Memories:**
- Never transition from ACTIVE
- Decay score always 0.0
- Exempt from all lifecycle transitions

---

## Maintenance Recommendations

**When to Run Maintenance:**

1. **Scheduled:** Run weekly to recalculate decay scores
2. **After bulk import:** Classify new memories
3. **High decay scores:** Recalculate after significant time has passed
4. **Before cleanup:** Identify expired memories for review

**How to Run Maintenance:**

See `RunMaintenance.md` workflow for detailed instructions.

---

## Integration with Other Workflows

**Before:**
- GetStatus - Ensure server is healthy before requesting health report

**After:**
- RunMaintenance - If health shows stale decay scores
- SearchKnowledge - Review memories in concerning lifecycle states

**Related Workflows:**
- `RunMaintenance.md` - Update decay scores and transition states
- `GetStatus.md` - Check server operational health
- `SearchKnowledge.md` - Find memories in specific lifecycle states
