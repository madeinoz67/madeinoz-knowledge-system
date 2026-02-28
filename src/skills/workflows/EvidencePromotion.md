# Evidence Promotion Workflow

**Objective:** Promote high-confidence evidence from document chunks (RAG) to the knowledge graph as verified facts with full provenance tracking.

---

## Step 1: Announce Workflow

```bash
~/.claude/Tools/SkillWorkflowNotification EvidencePromotion MadeinozKnowledgeSystem
```

**Output to user:**
```
Running the **EvidencePromotion** workflow from the **MadeinozKnowledgeSystem** skill...
```

---

## Step 2: Understand Two-Tier Memory Model

**The Knowledge System uses a two-tier memory architecture:**

| Tier | System | Content | Lifecycle |
|------|--------|---------|-----------|
| **Document Memory** | Qdrant (RAG) | Raw document chunks | Transient, high-volume |
| **Knowledge Memory** | Graphiti (KG) | Verified facts with provenance | Durable, curated |

**Promotion Flow:**
```
Documents → RAG Search → Evidence Chunks → Verification → Knowledge Graph Facts
                ↑                                          ↓
                └──────────── Provenance Tracking ─────────┘
```

**When to Promote:**
- High-confidence information from trusted sources
- Reusable knowledge (procedures, constraints, APIs)
- Information you'll query frequently
- Facts that need relationship context

**When NOT to Promote:**
- Low-confidence or ambiguous content
- One-time lookup information
- Highly volatile data
- Raw excerpts without synthesis

---

## Step 3: Find Evidence to Promote

**Search documents for evidence:**

```bash
# Search for relevant content
bun run ~/.claude/skills/Knowledge/tools/rag-cli.ts search "your query" --top-k=10

# Get specific chunk details
bun run ~/.claude/skills/Knowledge/tools/rag-cli.ts get <chunk-id>
```

**Evaluate evidence quality:**
1. **Relevance:** Does it answer the question accurately?
2. **Confidence:** Is the source trustworthy?
3. **Durability:** Will this information remain valid?
4. **Utility:** Will you need to query this again?

---

## Step 4: Prepare Promotion Parameters

**Required Parameters:**

| Parameter | Description | Example |
|-----------|-------------|---------|
| `evidence_id` | Chunk ID from RAG search | `chunk_abc123` |
| `fact_type` | Type of fact to create | `constraint`, `procedure`, `requirement` |
| `value` | The actual fact content | "Max retry count is 3" |

**Optional Parameters:**

| Parameter | Description | Default |
|-----------|-------------|---------|
| `entity` | Related entity name | Auto-extracted |
| `scope` | Scope context | `global` |
| `version` | Version information | Current |
| `valid_until` | Expiration date | None |
| `resolution_strategy` | Conflict handling | `overwrite` |

---

## Step 5: Execute Promotion (CLI-First)

### Primary: Knowledge CLI (via Bash)

**Promote evidence to knowledge graph:**

```bash
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts promote <evidence_id> <fact_type> "<value>"
```

**Example:**
```bash
# Promote a constraint
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts promote chunk_xyz789 constraint "API rate limit is 100 requests per minute"

# Promote with additional parameters
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts promote chunk_xyz789 constraint "API rate limit is 100 requests per minute" --strategy merge
```

### Fallback: MCP Tool (Only if CLI fails)

**⚠️ Only use MCP if CLI returns connection/execution errors.**

```typescript
// MCP Tool: kg.promoteFromEvidence
kg_promoteFromEvidence({
  evidence_id: "chunk_xyz789",
  fact_type: "constraint",
  value: "API rate limit is 100 requests per minute",
  entity: "API",
  scope: "global",
  resolution_strategy: "overwrite"
})
```

---

## Step 6: Verify Promotion

**Verify fact was created:**

```bash
# Search knowledge graph for the new fact
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts search_facts "your promoted content"
```

**Trace provenance:**

```bash
# Get provenance for a fact
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts provenance <fact_id>
```

**Provenance shows:**
- Source document
- Original chunk
- Ingestion timestamp
- Promotion timestamp
- Any transformations applied

---

## Step 7: Present Results

**Format promotion results for user:**

```markdown
✅ **Evidence Promoted to Knowledge Graph**

**Source Evidence:**
- Chunk ID: [evidence_id]
- Document: [source_document.pdf]
- Original content: "[excerpt from chunk...]"

**Created Fact:**
- Type: [fact_type]
- Value: [promoted value]
- Entity: [related entity]
- Fact ID: [new_fact_id]

**Provenance:**
- Source: [document path]
- Ingested: [timestamp]
- Promoted: [timestamp]

---

💡 **Next Steps:**
1. Verify fact: Search knowledge graph for "[fact content]"
2. Check relationships: Use SearchFacts to find connections
3. View provenance: `knowledge provenance [fact_id]`
```

---

## Provenance Tracking

**Every promoted fact maintains a provenance chain:**

```
┌─────────────────────────────────────────────────────────────┐
│ Provenance Chain                                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │  Original   │     │   RAG       │     │  Knowledge  │   │
│  │  Document   │────▶│   Chunk     │────▶│    Fact     │   │
│  │             │     │             │     │             │   │
│  │ source.pdf  │     │ chunk_123   │     │ fact_456    │   │
│  │ page 42     │     │ confidence  │     │ verified    │   │
│  └─────────────┘     │ 0.85        │     │ connected   │   │
│                      └─────────────┘     └─────────────┘   │
│                                                              │
│  Trace: document → chunk → fact → relationships            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Query Provenance:**

```bash
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts provenance <fact_id>
```

**Returns:**
- Source document path
- Chunk ID and content
- Ingestion metadata
- Promotion timestamp
- Confidence score at time of promotion

---

## Conflict Resolution

**When promoting conflicts with existing facts:**

| Strategy | Behavior | Use When |
|----------|----------|----------|
| `overwrite` | Replace existing fact | New information is more accurate |
| `merge` | Combine facts | Information is complementary |
| `keep_both` | Create separate fact | Both versions are valid in different contexts |
| `reject` | Cancel promotion | Existing fact should be preserved |

**Specify resolution strategy:**

```bash
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts promote chunk_xyz constraint "New value" --strategy merge
```

---

## Troubleshooting

**Promotion Fails:**
```bash
# Verify evidence exists
bun run ~/.claude/skills/Knowledge/tools/rag-cli.ts get <chunk-id>

# Check knowledge graph health
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts get_status
```

**Fact Not Searchable:**
- Wait for indexing (may take a few seconds)
- Verify entity extraction succeeded
- Check fact was actually created

**Provenance Not Found:**
- Fact may have been created directly (not promoted)
- Check fact ID is correct
- Verify promotion completed successfully

**Conflict Errors:**
- Choose appropriate resolution strategy
- Review existing fact before promoting
- Consider if both facts are valid

---

## Best Practices

**Evidence Selection:**
- Choose high-confidence chunks (score > 0.80)
- Prefer structured content over prose
- Select facts with clear subject/predicate/object
- Avoid ambiguous or context-dependent content

**Fact Types:**
- `constraint` - Limitations, requirements, thresholds
- `procedure` - Steps, processes, how-to information
- `requirement` - Must-have features, specifications
- `preference` - User choices, configurations
- `definition` - Term definitions, explanations

**Provenance Maintenance:**
- Always verify promotion succeeded
- Keep source documents accessible
- Document promotion decisions
- Periodically audit provenance chains

---

## Examples

**Example 1: Promote API Constraint**

User: "The API docs say max retries is 3. Promote that to knowledge."

```bash
# Find the evidence
bun run ~/.claude/skills/Knowledge/tools/rag-cli.ts search "max retries 3"

# Promote
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts promote chunk_abc123 constraint "Maximum retry count is 3"
```

**Example 2: Promote Procedure**

User: "The authentication flow procedure from the security doc should be in the knowledge graph."

```bash
# Find the evidence
bun run ~/.claude/skills/Knowledge/tools/rag-cli.ts search "authentication flow steps"

# Promote with entity context
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts promote chunk_def456 procedure "Authentication flow: 1) Request token, 2) Validate, 3) Grant access"
```

**Example 3: Check Provenance**

User: "Where did this fact about rate limits come from?"

```bash
# Get provenance
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts provenance fact_xyz789
```

---

## Related Workflows

- `RAGSearchDocuments.md` - Find evidence to promote
- `DocumentIngestion.md` - Ingest documents for evidence
- `SearchFacts.md` - Verify promoted facts
- `SearchKnowledge.md` - Search knowledge graph
