# Document Ingestion Workflow

**Objective:** Ingest documents (PDFs, markdown, text files) into the RAG system for semantic search using Docling parsing and Qdrant vector storage.

---

## Step 1: Announce Workflow

```bash
~/.claude/Tools/SkillWorkflowNotification DocumentIngestion MadeinozKnowledgeSystem
```

**Output to user:**
```
Running the **DocumentIngestion** workflow from the **MadeinozKnowledgeSystem** skill...
```

---

## Step 2: Identify Documents to Ingest

**Supported Document Types:**
- PDF documents (.pdf)
- Markdown files (.md)
- Text files (.txt)
- Code files (with syntax awareness)

**Ingestion Sources:**

| Source | Path | Description |
|--------|------|-------------|
| **Inbox** | `knowledge/inbox/` | Drop files here for automatic pickup |
| **Processed** | `knowledge/processed/` | Canonical storage after successful ingestion |
| **Custom path** | Any path | Explicit path via CLI argument |

---

## Step 3: Prepare Documents

**Before ingestion:**

1. **Drop files in inbox:**
   ```bash
   cp /path/to/your/document.pdf knowledge/inbox/
   ```

2. **Verify files are readable:**
   ```bash
   ls -la knowledge/inbox/
   ```

3. **Check document quality:**
   - PDFs should have selectable text (not scanned images)
   - Markdown should be well-structured with headings
   - Avoid corrupted or password-protected files

---

## Step 4: Execute Ingestion (CLI-First)

### Primary: RAG CLI (via Bash)

**Ingest all documents in inbox:**

```bash
bun run ~/.claude/skills/Knowledge/tools/rag-cli.ts ingest --all
```

**What happens during ingestion:**
1. **Parsing:** Docling extracts text, structure, and metadata
2. **Chunking:** Semantic chunking (512-768 tokens, 10-20% overlap)
3. **Embedding:** Generate embeddings via Ollama (bge-large-en-v1.5)
4. **Storage:** Store chunks in Qdrant with metadata
5. **Indexing:** Create search indices for fast retrieval

**Output includes:**
- Documents processed count
- Chunks created count
- Any errors or warnings
- Processing time

### Fallback: MCP Tool (Only if CLI fails)

**⚠️ Only use MCP if CLI returns connection/execution errors.**

```typescript
// MCP Tool: rag.ingest (if available)
rag_ingest({
  path: "/path/to/knowledge/inbox/",
  recursive: true
})
```

---

## Step 5: Verify Ingestion

**Check ingested documents:**

```bash
# List all ingested documents
bun run ~/.claude/skills/Knowledge/tools/rag-cli.ts list

# Search to verify content is searchable
bun run ~/.claude/skills/Knowledge/tools/rag-cli.ts search "document content query"

# Check specific document
bun run ~/.claude/skills/Knowledge/tools/rag-cli.ts get <chunk-id>
```

**Verify Qdrant health:**

```bash
bun run ~/.claude/skills/Knowledge/tools/rag-cli.ts health
```

---

## Step 6: Present Results

**Format ingestion results for user:**

```markdown
📄 **Document Ingestion Complete**

**Summary:**
- ✓ Documents processed: [X]
- ✓ Chunks created: [Y]
- ✓ Average chunk size: [Z] tokens
- ⏱️ Processing time: [T] seconds

**Ingested Documents:**
1. [document1.pdf] → [N] chunks
2. [document2.md] → [M] chunks
3. [document3.txt] → [K] chunks

---

**💡 Next Steps:**
1. **Search documents:** Use RAGSearchDocuments workflow
2. **Verify quality:** Search for key topics from ingested docs
3. **Promote evidence:** Use EvidencePromotion for high-value content

**📚 Documents moved to:** `knowledge/processed/`
```

**If ingestion had errors:**
```markdown
⚠️ **Document Ingestion Completed with Errors**

**Successful:** [X] documents
**Failed:** [Y] documents

**Errors:**
1. [filename] - [error reason]
   - Suggestion: [how to fix]

**To retry failed documents:**
1. Fix the issue (e.g., remove password from PDF)
2. Re-run: `rag ingest --all`
```

---

## Ingestion Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Document Ingestion Pipeline                                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  knowledge/inbox/     ┌─────────────┐    ┌─────────────┐   │
│  ┌─────────────┐      │   Docling   │    │   Semantic  │   │
│  │ document.pdf│ ───▶ │   Parser    │───▶│   Chunking  │   │
│  │ readme.md   │      │             │    │ 512-768 tok │   │
│  │ notes.txt   │      └─────────────┘    └──────┬──────┘   │
│  └─────────────┘                                 │          │
│                                                  ▼          │
│                                          ┌─────────────┐   │
│                                          │   Ollama    │   │
│                                          │  Embedding  │   │
│                                          │ bge-large   │   │
│                                          └──────┬──────┘   │
│                                                  │          │
│                                                  ▼          │
│                                          ┌─────────────┐   │
│                                          │   Qdrant    │   │
│                                          │  Vector DB  │   │
│                                          │  Port 6333  │   │
│                                          └─────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration

**Environment Variables:**

```bash
# Qdrant Configuration
MADEINOZ_KNOWLEDGE_QDRANT_URL=http://localhost:6333
MADEINOZ_KNOWLEDGE_QDRANT_COLLECTION=lkap_documents
MADEINOZ_KNOWLEDGE_QDRANT_EMBEDDING_DIMENSION=1024
MADEINOZ_KNOWLEDGE_QDRANT_CHUNK_SIZE_MIN=512
MADEINOZ_KNOWLEDGE_QDRANT_CHUNK_SIZE_MAX=768
MADEINOZ_KNOWLEDGE_QDRANT_CHUNK_OVERLAP=100

# Ollama Configuration (for embeddings)
MADEINOZ_KNOWLEDGE_OLLAMA_BASE_URL=http://localhost:11434
MADEINOZ_KNOWLEDGE_OLLAMA_EMBEDDING_MODEL=bge-large-en-v1.5
```

---

## Troubleshooting

**Ingestion Fails:**
```bash
# Check Qdrant is running
docker compose -f docker/docker-compose-qdrant.yml ps

# Check Ollama is running (for embeddings)
curl http://localhost:11434/api/tags

# Start services if needed
docker compose -f docker/docker-compose-qdrant.yml up -d
docker compose -f docker/docker-compose-ollama.yml up -d
```

**PDF Parsing Errors:**
- Ensure PDF has selectable text (not scanned images)
- Remove password protection
- Try converting to text first if problematic

**Embedding Failures:**
- Check Ollama is running: `ollama list`
- Verify model is available: `ollama pull bge-large-en-v1.5`
- Check Ollama logs for errors

**Chunk Quality Issues:**
- Documents too short → May not chunk properly
- Poor structure → May have odd chunk boundaries
- Mixed content → Consider separating by type

**Storage Issues:**
- Check Qdrant disk space
- Verify collection exists: `rag health`
- Check Qdrant logs: `docker logs qdrant`

---

## Best Practices

**Document Preparation:**
- Use descriptive filenames
- Organize by topic/project
- Include metadata in markdown frontmatter
- Remove duplicate content before ingestion

**Batch Ingestion:**
- Group related documents together
- Ingest by priority (highest-value first)
- Test with small batch before large imports
- Monitor for errors during bulk ingestion

**Quality Assurance:**
- Search after ingestion to verify
- Check chunk boundaries make sense
- Verify metadata is captured correctly
- Promote high-value content to knowledge graph

---

## Examples

**Example 1: Ingest Technical Documentation**

User: "Ingest all the PDFs in my documentation folder"

```bash
# Copy to inbox
cp ~/Documents/technical-docs/*.pdf knowledge/inbox/

# Ingest
bun run ~/.claude/skills/Knowledge/tools/rag-cli.ts ingest --all
```

**Example 2: Ingest Project READMEs**

User: "Add all project READMEs to the document system"

```bash
# Find and copy READMEs
find ~/projects -name "README.md" -exec cp {} knowledge/inbox/ \;

# Ingest
bun run ~/.claude/skills/Knowledge/tools/rag-cli.ts ingest --all
```

**Example 3: Verify After Ingestion**

User: "Check if my API docs were ingested correctly"

```bash
# List documents
bun run ~/.claude/skills/Knowledge/tools/rag-cli.ts list

# Search for key content
bun run ~/.claude/skills/Knowledge/tools/rag-cli.ts search "API endpoint authentication" --top-k=5
```

---

## Related Workflows

- `RAGSearchDocuments.md` - Search ingested documents
- `EvidencePromotion.md` - Promote document evidence to knowledge graph
- `BulkImport.md` - Bulk import to knowledge graph (alternative path)
