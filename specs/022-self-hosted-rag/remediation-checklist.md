# LKAP Remediation Checklist

**Generated**: 2026-02-09
**Source**: RedTeam Audit Report
**Purpose**: Actionable fixes prioritized by severity

---

## 🔴 P0 - CRITICAL BLOCKERS (Fix Before ANY Deployment)

*These will cause runtime failures. Fix immediately.*

### 1. Fix RAGFlow API Endpoints (T020)
**File**: `docker/patches/ragflow_client.py`
**Issue**: All endpoints use `/api/*` but RAGFlow API requires `/api/v1/*`

**Changes**:
```python
# Line 118: upload_document()
- ENDPOINT = "/api/documents"
+ ENDPOINT = "/api/v1/documents"

# Line 155: search()
- ENDPOINT = "/api/search"
+ ENDPOINT = "/api/v1/search"

# Line 188: get_chunk()
- ENDPOINT = f"/api/documents/{chunk_id}"
+ ENDPOINT = f"/api/v1/documents/{chunk_id}"

# Line 204: delete_document()
- ENDPOINT = f"/api/documents/{doc_id}"
+ ENDPOINT = f"/api/v1/documents/{doc_id}"

# Line 220: list_documents()
- ENDPOINT = "/api/documents"
+ ENDPOINT = "/api/v1/documents"
```

**Verification**: Run `bun run rag-cli.ts health` - should return 200 OK

---

### 2. Initialize Promotion Module (T064/T068)
**File**: `docker/patches/graphiti_mcp_server.py`
**Issue**: `promotion.init_graphiti()` never called, all kg operations crash

**Add after line 815** (in `GraphitiService.initialize()` after Graphiti client creation):
```python
# Initialize promotion module with Graphiti client
from . import promotion
promotion.init_graphiti(self.graphiti)
```

**Verification**: Call `kg.promoteFromEvidence` MCP tool - should not raise RuntimeError

---

### 3. Fix Embedding Service Bug (T042)
**File**: `docker/patches/embedding_service.py`
**Issue**: `self.embedding_model` undefined, should be `self.model`

**Changes**:
```python
# Line 120: _embed_openrouter()
- model = self.embedding_model
+ model = self.model

# Line 150: _embed_openrouter() (second occurrence)
- model = self.embedding_model
+ model = self.model
```

**Verification**: Test OpenRouter embedding generation - should not raise AttributeError

---

## 🟡 P1 - COMPLETE CORE FUNCTIONALITY

*These are stubs or incomplete but won't crash. Complete for MVP.*

### 4. Implement LLM Classification Layer (T034)
**File**: `docker/patches/classification.py`
**Issue**: Layer 3 stubbed with TODO at lines 110-115

**Action**: Implement LLM-based classification with confidence scoring

```python
# Replace stub at lines 110-115
# Layer 3: LLM classification
if confidence < 0.8:
    llm_result = await self._classify_with_llm(content)
    if llm_result.confidence > 0.6:
        scores.append(llm_result.confidence * 0.7)
        return ClassificationResult(
            domain=llm_result.domain,
            confidence=max(scores),
            sources=sources + ["llm"]
        )
```

---

### 5. Implement Embedding Caching (T046)
**File**: `docker/patches/embedding_service.py`
**Issue**: No caching, repeated embeddings waste API calls

**Action**: Add in-memory LRU cache or Redis caching

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def _cache_key(text: str, provider: str) -> str:
    return f"{provider}:{hash(text)}"

# In embed() method, check cache before API call
```

---

### 6. Implement Heading Contextualization (T048)
**File**: `docker/patches/chunking_service.py`
**Issue**: `contextualize_chunk()` exists but never used

**Action**: Call `contextualize_chunk()` before embedding

```python
# In embed(), before generating embedding:
contextualized_text = contextualize_chunk(chunk)
embeddings = await self._embed_openrouter([contextualized_text])
```

---

### 7. Implement Duplicate Detection DB Lookup (T026)
**File**: `docker/patches/docling_ingester.py`
**Issue**: `_is_already_ingested()` returns False unconditionally (TODO)

**Action**: Query ingestion state database

```python
# Replace lines 210-227
async def _is_already_ingested(self, content_hash: str) -> bool:
    """Check if document with this hash was already ingested."""
    # Query ingestion state database
    existing = await self.db.get_document_by_hash(content_hash)
    return existing is not None
```

---

### 8. Implement Evidence-to-Fact Edge Creation (T064)
**File**: `docker/patches/promotion.py`
**Issue**: `_create_evidence_fact_link()` at lines 585-595 is stub

**Action**: Use Graphiti's edge creation API

```python
# Replace stub at lines 585-595
async def _create_evidence_fact_link(
    self,
    evidence_id: str,
    fact_id: str
) -> None:
    """Create PROVENANCE edge from Evidence to Fact."""
    await self.graphiti.add_edge(
        source=evidence_id,
        target=fact_id,
        edge_name="PROVENANCE",
        attributes={"created_at": datetime.utcnow()}
    )
```

---

### 9. Implement RAGFlow Integration in Provenance (T065)
**File**: `docker/patches/promotion.py`
**Issue**: `get_provenance()` returns placeholder chain at lines 540-547

**Action**: Query RAGFlow for actual chunk data

```python
# Replace placeholder at lines 540-547
from .ragflow_client import get_ragflow_client

ragflow = get_ragflow_client()
chunk_data = await ragflow.get_chunk(evidence.chunk_id)
evidence_chain.append({
    "chunk_id": evidence.chunk_id,
    "text": chunk_data.text,
    "source": chunk_data.source_document
})
```

---

## 🟢 P2 - IMPROVE ROBUSTNESS

*Enhance error handling, use proper queries.*

### 10. Add Retry Logic with Exponential Backoff (T047)
**File**: `docker/patches/embedding_service.py`

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def _embed_openrouter(self, texts: List[str]) -> List[List[float]]:
    # Existing implementation with automatic retries
```

---

### 11. Add HTTP Status-Specific Error Handling (T058)
**File**: `docker/patches/ragflow_client.py`

```python
# In _request() method, add status handling
if response.status_code == 400:
    raise RuntimeError(f"Bad request: {response.text}")
elif response.status_code == 401:
    raise RuntimeError("RAGFlow authentication failed")
elif response.status_code == 404:
    raise RuntimeError(f"Resource not found: {url}")
elif response.status_code >= 500:
    # Retry on server errors
    return await self._retry_request(url, method, **kwargs)
```

---

### 12. Implement Cypher Query for Conflict Detection (T070)
**File**: `docker/patches/promotion.py`
**Issue**: Uses semantic search instead of documented Cypher query

**Action**: Replace `graphiti.search()` with actual Cypher query

```python
# In detect_conflicts(), replace lines 376-382
query = """
MATCH (f1:Fact), (f2:Fact)
WHERE f1.entity = $entity
  AND f1.fact_type = $fact_type
  AND f1.uuid <> f2.uuid
  AND f2.entity = $entity
  AND f2.fact_type = $fact_type
  AND f1.value <> f2.value
  AND (f1.valid_until IS NULL OR f1.valid_until > datetime())
  AND (f2.valid_until IS NULL OR f2.valid_until > datetime())
RETURN f1, f2
"""
results = await self.graphiti.driver.execute_query(query, ...)
```

---

### 13. Use Pydantic Models for MCP Tool Validation (T087)
**File**: `docker/patches/graphiti_mcp_server.py`

```python
# In kg_promoteFromEvidence(), use Pydantic model
from .lkap_models import PromoteFromEvidenceRequest

@mcp.tool()
async def kg_promoteFromEvidence(**kwargs) -> Fact | ErrorResponse:
    # Validate input
    try:
        request = PromoteFromEvidenceRequest(**kwargs)
    except ValidationError as e:
        return ErrorResponse(error=f"Invalid input: {e}")
    # Rest of implementation...
```

---

### 14. Fix ErrorResponse Import (T088)
**File**: `docker/patches/graphiti_mcp_server.py`
**Issue**: `from models.response_types import ErrorResponse` at line 38 fails

**Action**: Create file or remove dependency

```python
# Option 1: Create docker/patches/models/response_types.py
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    error: str
    details: dict | None = None

# Option 2: Use inline dict instead
# Return {"error": "..."} instead of ErrorResponse(error="...")
```

---

## 🔵 P3 - COMPLETE USER EXPERIENCE

*Missing CLI commands and visualization.*

### 15. Add knowledge-cli.ts promote Commands (T095)
**File**: `src/skills/tools/knowledge-cli.ts`

```typescript
// Add new command
promote: {
  command: 'promote <evidenceId> <factType> <value>',
  describe: 'Promote evidence chunk to knowledge graph fact',
  handler: async (argv: { evidenceId: string; factType: string; value: string }) => {
    const result = await mcpClient.callTool({
      name: 'kg_promoteFromEvidence',
      arguments: {
        evidence_id: argv.evidenceId,
        fact_type: argv.factType,
        value: argv.value
      }
    });
    console.log(JSON.stringify(result, null, 2));
  }
}
```

---

### 16. Add knowledge-cli.ts provenance Command (T096)

```typescript
provenance: {
  command: 'provenance <factId>',
  describe: 'Trace fact to source documents',
  handler: async (argv: { factId: string }) => {
    const result = await mcpClient.callTool({
      name: 'kg_getProvenance',
      arguments: { fact_id: argv.factId }
    });
    console.log(JSON.stringify(result, null, 2));
  }
}
```

---

### 17. Add knowledge-cli.ts conflicts Command (T097)

```typescript
conflicts: {
  command: 'conflicts [entity] [factType]',
  describe: 'Review and resolve conflicts',
  handler: async (argv: { entity?: string; factType?: string }) => {
    const result = await mcpClient.callTool({
      name: 'kg_reviewConflicts',
      arguments: {
        entity: argv.entity,
        fact_type: argv.factType,
        status: 'open'
      }
    });
    console.log(JSON.stringify(result, null, 2));
  }
}
```

---

### 18. Implement Conflict Visualization (T075)
**File**: `docker/patches/promotion.py`

```python
def visualize_conflicts(self, conflicts: List[Conflict]) -> str:
    """Generate ASCII visualization of conflict relationships."""
    output = []
    for conflict in conflicts:
        output.append(f"Conflict {conflict.conflict_id}:")
        for fact_id in conflict.fact_ids:
            fact = self.get_fact(fact_id)
            output.append(f"  └─ {fact.entity} = {fact.value} ({fact.fact_type})")
    return "\n".join(output)
```

---

### 19. Implement Conflict Severity Scoring (T077)
**File**: `docker/patches/lkap_models.py`

```python
class Conflict(BaseModel):
    # ... existing fields ...
    severity: Literal["critical", "major", "minor"] = "minor"

# In promotion.py, calculate severity
def _calculate_severity(self, conflict: Conflict) -> str:
    """Determine conflict severity based on fact types and values."""
    if conflict.fact_types == {"CONSTRAINT", "CONSTRAINT"}:
        return "critical"
    elif conflict.fact_types == {"API", "API"}:
        return "major"
    return "minor"
```

---

### 20. Implement Manual Review Workflow UI (T078)
**Status**: Defer - requires frontend or TUI framework
**Recommendation**: Mark as out-of-scope for v1.0, use CLI instead

---

## ⚪ P4 - DOCUMENTATION & OPTIONAL

### 21. Create docker-compose-ollama.yml
**File**: `docker/docker-compose-ollama.yml`

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    container_name: madeinoz-knowledge-ollama
    restart: unless-stopped
    networks:
      - madeinoz-knowledge-net
    ports:
      - "11434:11434"
    environment:
      - OLLAMA_NUM_GPU=${MADEINOZ_KNOWLEDGE_OLLAMA_NUM_GPU:-0}
      - OLLAMA_NUM_THREAD=${MADEINOZ_KNOWLEDGE_OLLAMA_NUM_THREAD:-4}
    volumes:
      - ollama-data:/root/.ollama
    # Pull bge-large-en-v1.5 on startup
    command: sh -c "ollama serve & sleep 5 && ollama pull bge-large-en-v1.5 && wait"

volumes:
  ollama-data:
```

---

### 22. Create specs/022-self-hosted-rag/data-model.md

```markdown
# LKAP Data Model

## Entities

### Document
- id: str (primary key)
- hash: str (SHA-256 content hash)
- filename: str
- domain: Domain enum
- type: DocumentType enum
- ...

### DocumentChunk
- id: str
- doc_id: str (foreign key)
- text: str
- headings: List[str]
- position: int
- token_count: int
- ...

## Relationships

- Document CONTAINS Chunk
- Evidence PROVES Fact
- Fact CONFLICTS_WITH Fact
- Fact HAS_PROVENANCE Evidence
```

---

### 23. Run Full Integration Test Suite (T097)
```bash
# Run all integration tests
cd docker/patches
pytest tests/integration/ -v --tb=short

# Run with coverage
pytest tests/integration/ --cov=. --cov-report=html
```

---

### 24. Validate quickstart.md Workflows (T098)
**Action**: Manually test each workflow in docs/usage/lkap-quickstart.md

**Checklist**:
- [ ] Start RAGFlow container successfully
- [ ] Drop document in knowledge/inbox/
- [ ] Verify document moves to knowledge/processed/
- [ ] Run semantic search and get results
- [ ] Promote evidence to fact
- [ ] Verify fact in knowledge graph
- [ ] Trace provenance back to document
---

## Verification Checklist

After completing fixes, verify:

- [ ] All P0 blockers resolved
- [ ] `bun run rag-cli.ts health` returns OK
- [ ] `kg.promoteFromEvidence` MCP tool works without error
- [ ] OpenRouter embeddings generate successfully
- [ ] Integration test suite passes
- [ ] All CLI commands functional
- [ ] Documentation updated

---

**Next Steps**:
1. Fix all P0 blockers (estimated 1-2 hours)
2. Complete P1 items for MVP (estimated 4-6 hours)
3. Address P2 for robustness (estimated 2-4 hours)
4. Implement P3 CLI commands (estimated 2-3 hours)
5. Complete P4 documentation (estimated 1 hour)

**Total Estimated Effort**: 10-16 hours for complete remediation
**MVP Effort** (P0 + P1): 5-8 hours
