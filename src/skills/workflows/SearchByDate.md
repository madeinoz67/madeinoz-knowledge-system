# Search By Date Workflow

**Objective:** Retrieve knowledge from the Graphiti knowledge graph filtered by date/time, enabling temporal queries like "what did I learn today" or "show knowledge from last week."

---

## Step 1: Announce Workflow

```bash
~/.claude/Tools/SkillWorkflowNotification SearchByDate MadeinozKnowledgeSystem
```

**Output to user:**
```
Running the **SearchByDate** workflow from the **MadeinozKnowledgeSystem** skill...
```

---

## Step 2: Parse Temporal Request

**Extract temporal intent from user request:**

**Common Patterns:**
- "What did I learn today?"
- "Show knowledge from yesterday"
- "What have I added this week?"
- "Find facts from January"
- "Knowledge from the last 7 days"
- "Show me what I captured last month"

**Extract key components:**
1. **Time reference:** today, yesterday, last week, specific date, date range
2. **Search topic:** Optional filter for specific subjects
3. **Result type:** Nodes (entities) or facts (relationships)

---

## Step 3: Build Temporal Query

**Map user's temporal language to date filters:**

| User Says | --since | --until |
|-----------|---------|---------|
| "today" | today | (none) |
| "yesterday" | yesterday | today |
| "this week" | 7d | (none) |
| "last week" | 14d | 7d |
| "last month" | 1m | (none) |
| "January 2026" | 2026-01-01 | 2026-01-31 |
| "last 3 days" | 3d | (none) |

**Date Format Reference:**
- **ISO 8601:** `2026-01-26`, `2026-01-26T00:00:00Z`
- **Relative:** `today`, `yesterday`, `now`
- **Duration:** `7d`, `7 days`, `1w`, `1 week`, `1m`, `1 month`

---

## Step 4: Execute Temporal Search (CLI-First)

### Primary: Knowledge CLI (via Bash)

**ALWAYS try CLI first - it's more reliable and token-efficient:**

```bash
# Search nodes from today
bun run tools/knowledge-cli.ts search_nodes "query" --since today

# Search facts from last 7 days
bun run tools/knowledge-cli.ts search_facts "query" --since 7d

# Search within a date range
bun run tools/knowledge-cli.ts search_nodes "query" --since 2026-01-01 --until 2026-01-15

# Yesterday's knowledge
bun run tools/knowledge-cli.ts search_nodes "query" --since yesterday --until today

# Last month
bun run tools/knowledge-cli.ts search_facts "query" --since 1m
```

**Parameters:**
- First argument (required) - Natural language search query (use "*" for all topics)
- Second argument (optional) - Number of results (default: 5)
- `--since <date>` - Filter results created after this date
- `--until <date>` - Filter results created before this date

### Fallback: MCP Tool (Only if CLI fails)

**Only use MCP if CLI returns connection/execution errors.**

```typescript
search_nodes({
  query: "search terms",
  created_after: "today",  // ISO or relative date
  created_before: "now",   // Optional upper bound
  max_nodes: 10
})

search_memory_facts({
  query: "search terms",
  created_after: "7d",     // Last 7 days
  max_facts: 10
})
```

---

## Step 5: Present Results

**Format temporal results for user:**

```markdown
📅 **Knowledge from [Time Period]**

Based on your knowledge graph, here's what was captured [today/this week/etc.]:

**Entities Added:**
1. **[Entity Name]** ([Type]) - Created [date]
   - Summary: [Brief description]

2. **[Entity Name]** ([Type]) - Created [date]
   - Summary: [Brief description]

**Facts Established:**
- [Entity A] → [relationship] → [Entity B] (Created [date])
- [Entity C] → [relationship] → [Entity D] (Created [date])

📊 **Summary:**
- [X] entities added
- [Y] relationships established
- Most active topics: [list of topics]
```

**If no results found:**
```markdown
❌ **No Knowledge Found for [Time Period]**

I couldn't find any information captured [during this time period].

This could mean:
1. No knowledge was captured during this time
2. Try a broader date range
3. The search query may be too specific

Suggestions:
- Use a broader search query
- Extend the date range with --since
- Check GetRecent for the latest additions
```

---

## Examples

### Example 1: Today's Learning

**User:** "What did I learn today?"

```bash
bun run tools/knowledge-cli.ts search_nodes "*" 10 --since today
```

### Example 2: Last Week's Decisions

**User:** "Show me decisions from last week"

```bash
bun run tools/knowledge-cli.ts search_facts "decision" 10 --since 7d
```

### Example 3: Specific Date Range

**User:** "Knowledge from January 15-20"

```bash
bun run tools/knowledge-cli.ts search_nodes "*" 20 --since 2026-01-15 --until 2026-01-20
```

### Example 4: Yesterday's Research

**User:** "What did we research yesterday?"

```bash
bun run tools/knowledge-cli.ts search_nodes "research" --since yesterday --until today
```

### Example 5: Last Month Overview

**User:** "Give me an overview of last month's knowledge"

```bash
bun run tools/knowledge-cli.ts search_nodes "*" 20 --since 1m
bun run tools/knowledge-cli.ts search_facts "*" 20 --since 1m
```

---

## Trigger Patterns

This workflow is triggered by:

**Explicit Temporal Queries:**
- "what did I learn today"
- "knowledge from last week"
- "show January entries"
- "what was captured yesterday"
- "recent knowledge additions"

**Time-Based Questions:**
- "what's new in my knowledge base"
- "latest knowledge entries"
- "what have I added recently"

---

## Best Practices

**Date Selection:**
- Start with broader ranges, narrow down if needed
- Use relative dates (7d, 1w, 1m) for convenience
- Use ISO dates for precise boundaries

**Query Construction:**
- Use "*" or very broad query for "show me everything from [time]"
- Combine topic + temporal for focused results
- Request more results when filtering by time (knowledge may be sparse)

**Result Interpretation:**
- Pay attention to created_at timestamps
- Look for patterns in what was learned over time
- Consider combining with topic-based search for depth

---

## Integration with Other Workflows

**Complements:**
- `SearchKnowledge.md` - Add temporal filters to topic searches
- `SearchFacts.md` - Find relationships from specific time periods
- `GetRecent.md` - For quick "what's new" without date math

**Workflow Chaining:**
1. SearchByDate to find when something was learned
2. SearchKnowledge to find related topics
3. SearchFacts to explore relationships

---

**Related Workflows:**
- `SearchKnowledge.md` - Topic-based entity search
- `SearchFacts.md` - Relationship search
- `GetRecent.md` - Recent episodes without filters
- `CaptureEpisode.md` - Add new knowledge
