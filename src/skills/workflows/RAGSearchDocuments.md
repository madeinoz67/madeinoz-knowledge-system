# RAG Search Documents Workflow

**Objective:** Search across ingested documents (PDFs, markdown, text files) using semantic similarity to find relevant content chunks with citations.

---

## Step 1: Announce Workflow

```bash
~/.claude/Tools/SkillWorkflowNotification RAGSearchDocuments MadeinozKnowledgeSystem
```

**Output to user:**
```
Running the **RAGSearchDocuments** workflow from the **MadeinozKnowledgeSystem** skill...
```

---

## Step 2: Parse Search Query

**Extract search intent from user request:**

**Direct Questions:**
- "Search documents for X"
- "Find in my documents Y"
- "What do my documents say about Z"
- "Search my PDFs for..."

**Implicit Requests:**
- "Look up X in the documentation" (implies document search)
- "Find information about Y in the ingested files"
- "What does the RAG know about Z?"

**Extract key concepts:**
- Identify main topic/keywords
- Note any domain filters (embedded, security, etc.)
- Note any document type preferences (pdf, markdown)

---

## Step 3: Build Search Query

**Construct effective semantic query:**

> **CLI Tool:** `rag-cli.ts` (wraps Qdrant vector search)

```bash
bun run ~/.claude/skills/Knowledge/tools/rag-cli.ts search "your query here" --top-k=10
```

**Query Construction Tips:**
- Use natural language queries (semantic search understands meaning)
- Include specific domain terms for better relevance
- Add context if search is ambiguous
- Keep queries focused on one main topic

**Filter Options:**
- `--domain=<type>` - Filter by domain (embedded, security, etc.)
- `--type=<type>` - Filter by document type (pdf, markdown)
- `--component=<name>` - Filter by component name
- `--project=<name>` - Filter by project name
- `--version=<ver>` - Filter by version
- `--top-k=<n>` - Maximum results (default: 10, max: 100)

**Examples:**
```bash
# Basic search
bun run ~/.claude/skills/Knowledge/tools/rag-cli.ts search "GPIO configuration"

# With domain filter
bun run ~/.claude/skills/Knowledge/tools/rag-cli.ts search "timing diagram" --domain=embedded

# Multiple filters
bun run ~/.claude/skills/Knowledge/tools/rag-cli.ts search "authentication flow" --type=pdf --project=api-gateway
```

---

## Step 4: Execute Document Search (CLI-First)

### Primary: RAG CLI (via Bash)

**ALWAYS try CLI first - it's the most reliable interface:**

```bash
bun run ~/.claude/skills/Knowledge/tools/rag-cli.ts search "search query" --top-k=10
```

**Output includes:**
- Chunk ID (for retrieval)
- Document source
- Content snippet
- Confidence score
- Metadata (domain, type, component)

### Fallback: MCP Tool (Only if CLI fails)

**⚠️ Only use MCP if CLI returns connection/execution errors.**

```typescript
// MCP Tool: rag.search (if available)
rag_search({
  query: searchQuery,
  top_k: 10,
  filters: {
    domain: "embedded",
    type: "pdf"
  }
})
```

---

## Step 5: Present Results

**Format document search results for user:**

```markdown
📄 **Document Search Results: [Query]**

Found [X] relevant chunks across [Y] documents:

**1. [Document Name]** (Score: [confidence])
> [Content snippet from chunk...]
📍 Location: [page/section if available]
🆔 Chunk ID: [chunk-id for reference]

**2. [Document Name]** (Score: [confidence])
> [Content snippet from chunk...]
📍 Location: [page/section if available]
🆔 Chunk ID: [chunk-id for reference]

---

💡 **Related Documents:**
- [List other documents that matched]

📚 **Suggested Actions:**
- Get full chunk: `rag get <chunk-id>`
- Search related: `rag search "related query"`
- Promote to knowledge: Use EvidencePromotion workflow
```

**If no results found:**
```markdown
❌ **No Documents Found**

I couldn't find any documents matching "[query]" in the RAG system.

**Suggestions:**
1. Try broader search terms
2. Check if documents have been ingested: `rag list`
3. Remove filters that may be too restrictive
4. Check Qdrant health: `rag health`

**To ingest new documents:**
Drop files in `knowledge/inbox/` and run: `rag ingest --all`
```

---

## Step 6: Retrieve Full Chunk (Optional)

**If user wants more context:**

```bash
bun run ~/.claude/skills/Knowledge/tools/rag-cli.ts get <chunk-id>
```

**Returns:**
- Full chunk content
- Complete metadata
- Source document path
- Surrounding context if available

---

## RAG vs Knowledge Graph Search

| Aspect | RAG Search (This Workflow) | Knowledge Graph Search |
|--------|---------------------------|------------------------|
| **Searches** | Raw document content | Extracted entities/facts |
| **Returns** | Content chunks with citations | Entities and relationships |
| **Best for** | Finding specific passages | Understanding connections |
| **Temporal** | Document snapshot | Evolving knowledge |
| **Confidence** | Similarity score | Graph relationship strength |

**When to use RAG:**
- Finding exact quotes or passages
- Searching recently ingested documents
- Looking for technical specifications
- Verifying source material

**When to use Knowledge Graph:**
- Understanding relationships
- Exploring connected concepts
- Finding accumulated knowledge
- Temporal queries (what did I learn when)

---

## Troubleshooting

**No Results Found:**
- Query may be too specific → Try broader terms
- Documents not ingested → Check with `rag list`
- Wrong filters applied → Remove domain/type filters
- Qdrant not running → Check with `rag health`

**Low Relevance Results:**
- Query terms may have multiple meanings → Add domain context
- Embedding model mismatch → Check Ollama/Qdrant config
- Documents may not cover topic → Ingest relevant docs

**Connection Errors:**
```bash
# Check Qdrant health
bun run ~/.claude/skills/Knowledge/tools/rag-cli.ts health

# Verify Qdrant is running
docker compose -f docker/docker-compose-qdrant.yml ps

# Start Qdrant if needed
docker compose -f docker/docker-compose-qdrant.yml up -d
```

**Slow Searches:**
- Large collection → Reduce --top-k
- Network latency → Check Qdrant connection
- Embedding model slow → Consider smaller model

---

## Best Practices

**Query Construction:**
- Start with natural language
- Add filters only if too many results
- Use domain-specific terminology
- Combine concepts for precision

**Result Interpretation:**
- Check confidence scores
- Verify source documents
- Cross-reference with knowledge graph
- Consider chunk context

**Integration with Knowledge Graph:**
1. Search documents for initial discovery
2. Verify findings in knowledge graph
3. Promote high-confidence evidence to graph
4. Use knowledge graph for relationships

---

## Examples

**Example 1: Technical Documentation Search**

User: "Search my documents for GPIO configuration"

```bash
bun run ~/.claude/skills/Knowledge/tools/rag-cli.ts search "GPIO configuration pins setup" --domain=embedded --top-k=5
```

Returns chunks from embedded systems documentation with pin configurations.

**Example 2: API Documentation Search**

User: "Find information about authentication in the API docs"

```bash
bun run ~/.claude/skills/Knowledge/tools/rag-cli.ts search "authentication JWT OAuth token" --type=pdf --project=api
```

Returns relevant sections from API documentation PDFs.

**Example 3: Error Message Lookup**

User: "What do my docs say about error 500?"

```bash
bun run ~/.claude/skills/Knowledge/tools/rag-cli.ts search "error 500 internal server error troubleshooting"
```

Returns troubleshooting guides mentioning the error.

---

## Related Workflows

- `DocumentIngestion.md` - Ingest new documents to RAG
- `EvidencePromotion.md` - Promote document evidence to knowledge graph
- `SearchKnowledge.md` - Search knowledge graph (extracted entities)
- `SearchFacts.md` - Find relationships between entities
