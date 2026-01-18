# Model Benchmark Results - MadeInOz Knowledge System

**Date:** 2026-01-18
**Database:** Neo4j (neo4j:5.28.0)
**MCP Server:** zepai/knowledge-graph-mcp:standalone
**Local Ollama Tests:** NVIDIA RTX 4090 GPU (24GB VRAM)

---

## Executive Summary

Testing revealed that the current configuration (GPT-4o-mini + MxBai Embed Large) offers excellent value. However, there are even more cost-effective options available.

### Recommended Configurations

| Use Case | LLM | Embedding | Cost/1K Ops | Notes |
|----------|-----|-----------|-------------|-------|
| **Best Value** | Llama 3.1 8B (OpenRouter) | MxBai Embed Large (Ollama) | $0.0145 | 10x cheaper than current |
| **Current Setup** | GPT-4o-mini (OpenAI) | MxBai Embed Large (Ollama) | $0.129 | Production-proven |
| **Fastest** | Grok 4 Fast (OpenRouter) | MxBai Embed Large (Ollama) | $0.28 | 603ms response time |
| **Premium** | GPT-4o (OpenRouter) | Embed 3 Small (OpenRouter) | $2.16 | Highest quality |

---

## LLM Models for Entity Extraction

All models tested for JSON entity/relationship extraction from text.

### Top Performers (100% Pass Rate, Sorted by Cost)

| Rank | Model | Provider | Cost/1K | Avg Response | Entities/Test |
|------|-------|----------|---------|--------------|---------------|
| 1 | **Llama 3.1 8B** | OpenRouter | $0.0145 | 973ms | 4.3 |
| 2 | Mistral 7B | OpenRouter | $0.0167 | 948ms | 4.0 |
| 3 | DeepSeek V3 | OpenRouter | $0.0585 | 1045ms | 4.3 |
| 4 | Llama 3.3 70B | OpenRouter | $0.114 | 1087ms | 4.3 |
| 5 | Gemini 2.0 Flash | OpenRouter | $0.125 | 1365ms | 5.3 |
| 6 | Qwen 2.5 72B | OpenRouter | $0.126 | 1113ms | 5.3 |
| 7 | **GPT-4o Mini** | OpenRouter | $0.129 | 624ms | 5.0 |
| 8 | Grok 4 Fast | OpenRouter | $0.280 | 603ms | - |
| 9 | Grok 4.1 Fast | OpenRouter | $0.434 | 1493ms | - |
| 10 | Grok 3 Mini | OpenRouter | $0.560 | 653ms | - |
| 11 | Claude 3.5 Haiku | OpenRouter | $0.816 | 1305ms | 4.3 |
| 12 | GPT-4o | OpenRouter | $2.155 | 529ms | 5.3 |
| 13 | Grok 3 | OpenRouter | $2.163 | 592ms | - |
| 14 | DeepSeek R1* | OpenRouter | $3.569 | 1321ms | 4.0 |
| 15 | Claude Sonnet 4 | OpenRouter | $4.215 | 2149ms | 5.7 |
| 16 | Grok 4 | OpenRouter | $11.842 | 516ms | - |

*DeepSeek R1 has 67% pass rate (JSON parsing issues)

### Key Findings - LLMs

1. **Best Value**: Llama 3.1 8B at $0.0145/1K is **9x cheaper** than GPT-4o-mini
2. **Fastest**: Grok 4 Fast (603ms) and GPT-4o (529ms) are the fastest
3. **Quality Leader**: Claude Sonnet 4 extracts most entities (5.7 avg) but costs 300x more than Llama
4. **Avoid**: DeepSeek R1 (inconsistent JSON), expensive premium models for this use case

---

## Embedding Models

Tested for semantic similarity accuracy using 8 test pairs (5 similar, 3 dissimilar).
**Ollama models tested on NVIDIA RTX 4090 GPU (24GB VRAM).**

### Results (Sorted by Quality Score)

| Rank | Model | Provider | Quality | Cost/1M | Speed | Dimensions |
|------|-------|----------|---------|---------|-------|------------|
| 1 | **Embed 3 Small** | OpenRouter | 78.2% | $0.02 | 824ms | 1536 |
| 2 | Embed 3 Large | OpenRouter | 77.3% | $0.13 | 863ms | 3072 |
| 3 | **MxBai Embed Large** | Ollama | 73.9% | FREE | 87ms | 1024 |
| 4 | Nomic Embed Text | Ollama | 63.5% | FREE | 93ms | 768 |
| 5 | Ada 002 | OpenRouter | 58.8% | $0.10 | 801ms | 1536 |

### Key Findings - Embeddings

1. **Best Free**: MxBai Embed Large (73.9% quality) - only 4% lower than best paid
2. **Fastest**: Ollama models (87-93ms) are 9x faster than cloud (800ms+)
3. **Best Paid**: Embed 3 Small offers best quality at lowest cloud price
4. **Avoid**: Ada 002 (lowest quality among working models)

### ⚠️ CRITICAL: Changing Embedding Models

**Switching embedding models breaks existing data.** Each model produces vectors with different dimensions:

| Model | Dimensions |
|-------|------------|
| mxbai-embed-large | 1024 |
| nomic-embed-text | 768 |
| text-embedding-3-small | 1536 |
| text-embedding-3-large | 3072 |

Neo4j's vector similarity search requires all vectors to have identical dimensions. If you:
1. Index data with Model A (e.g., nomic-embed-text @ 768 dims)
2. Then switch to Model B (e.g., mxbai-embed-large @ 1024 dims)
3. Search queries will fail with: `Invalid input for 'vector.similarity.cosine()': The supplied vectors do not have the same number of dimensions`

**To switch models safely:**

1. **Export important knowledge** (manually note key facts you want to keep)
2. **Clear the graph**: `clear_graph` via MCP
3. **Update config**:
   ```env
   MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL=your-new-model
   MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS=matching-dimension
   ```
4. **Restart the server**
5. **Re-add your knowledge**

There is **no migration path** - embeddings are fundamentally different mathematical representations. You must re-index all data.

**Best practice:** Choose an embedding model at installation and stick with it. Use `mxbai-embed-large` (1024 dims) for the best balance of quality, speed, and cost (free).

See `docs/troubleshooting.md` → "Vector Dimension Mismatch Error" for detailed fix instructions.

---

## Real-Life MCP Integration Test

Tested with Neo4j backend using current configuration:
- LLM: gpt-4o-mini (OpenAI)
- Embedder: mxbai-embed-large (Ollama @ 10.0.0.150)

### Test Data

```
Episode 1: "Team uses TypeScript with Bun. Sarah chose Hono for HTTP framework."
Episode 2: "John Smith from Acme Corp met CTO Alice Chen about payment API integration."
Episode 3: "PAI uses Neo4j graph database. GPT-4o-mini for extraction. Ollama for embeddings."
```

### Results

| Operation | Success | Avg Time | Results |
|-----------|---------|----------|---------|
| add_memory | 3/3 | ~6ms | All episodes queued |
| search_nodes | 3/3 | ~60ms | 10 nodes per query |
| search_memory_facts | 3/3 | ~50ms | 9 facts per query |
| get_episodes | 1/1 | - | 3 episodes retrieved |

### Extracted Entities (Verified in Neo4j)

```
TypeScript, Bun, Sarah, Hono, HTTP framework
John Smith, Acme Corp, Alice Chen, payment API integration
GPT-4o-mini, Ollama, Neo4j
```

### Extracted Facts

```
- "Acme Corp is involved in payment API integration"
- "John Smith met with Alice Chen about payment API integration"
- "GPT-4o-mini is used in conjunction with Ollama for embeddings"
- "The team uses TypeScript with Bun"
- "Hono is an HTTP framework"
- "Sarah chose Hono as the HTTP framework"
```

---

## Cost Comparison: Current vs Optimized

Assuming 10,000 operations/month:

| Configuration | LLM Cost | Embed Cost | Total/Month |
|---------------|----------|------------|-------------|
| **Optimized** (Llama 3.1 8B + MxBai) | $0.145 | $0 | **$0.15** |
| **Current** (GPT-4o-mini + MxBai) | $1.29 | $0 | $1.29 |
| Premium (GPT-4o + Embed 3 Small) | $21.55 | $0.002 | $21.55 |

**Savings with optimized config: 88% cost reduction**

---

## Configuration Recommendations

### For Cost-Sensitive Deployments

```env
# Use OpenRouter with Llama 3.1 8B
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openrouter
MADEINOZ_KNOWLEDGE_MODEL_NAME=meta-llama/llama-3.1-8b-instruct

# Use local Ollama for embeddings
MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER=ollama
MADEINOZ_KNOWLEDGE_EMBEDDER_BASE_URL=http://localhost:11434/v1
MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL=mxbai-embed-large
```

### For Speed-Sensitive Deployments

```env
# Use OpenRouter with Grok 4 Fast
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openrouter
MADEINOZ_KNOWLEDGE_MODEL_NAME=x-ai/grok-4-fast

# Use local Ollama for embeddings (fastest)
MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER=ollama
MADEINOZ_KNOWLEDGE_EMBEDDER_BASE_URL=http://localhost:11434/v1
MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL=mxbai-embed-large
```

### For Quality-Sensitive Deployments

```env
# Use GPT-4o for extraction
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openrouter
MADEINOZ_KNOWLEDGE_MODEL_NAME=openai/gpt-4o

# Use OpenAI Embed 3 Small
MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER=openrouter
MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL=openai/text-embedding-3-small
```

---

## Test Files

- `test-all-llms-mcp.ts` - Comprehensive MCP test script
- `test-grok-llms-mcp.ts` - Grok models MCP test script
- `test-search-debug.ts` - MCP integration test script

---

## Real-Life MCP Testing with OpenRouter

### Tested Configuration
- **LLM**: GPT-4o-mini via OpenRouter (`openai/gpt-4o-mini`)
- **Embedder**: MxBai Embed Large via Ollama
- **Database**: Neo4j 5.28.0

### Entity Extraction Test

**Input**: "During the Q4 planning meeting, CEO Michael Chen announced that TechVentures Inc will acquire DataFlow Systems for $500 million. The deal, brokered by Goldman Sachs, includes all patents and the 200-person engineering team based in Seattle."

**Extracted Entities** (verified in Neo4j):
- DataFlow Systems
- Goldman Sachs
- Michael Chen
- Seattle
- TechVentures Inc

**Extracted Facts**:
- "The acquisition deal of DataFlow Systems was brokered by Goldman Sachs"
- "TechVentures Inc will acquire DataFlow Systems for $500 million"
- "DataFlow Systems has a 200-person engineering team based in Seattle"

**Result**: ✅ 5/5 entities, 3 facts extracted successfully

### Comprehensive Model Compatibility Test (All 10 Benchmark Models)

**Test**: Real-life entity extraction via MCP with Graphiti
**Input**: "During the Q4 planning meeting at TechCorp headquarters in Austin, CEO Sarah Martinez announced a strategic partnership with CloudBase Inc..."
**Expected Entities**: TechCorp, Sarah Martinez, CloudBase, Morgan Stanley, Austin

#### Working Models (5/10)

| Rank | Model | Cost/1K | Entities | Expected | Time | Notes |
|------|-------|---------|----------|----------|------|-------|
| 1 | **Gemini 2.0 Flash** | $0.125 | 8 | 5/5 | 16.4s | **BEST VALUE** |
| 2 | Qwen 2.5 72B | $0.126 | 8 | 5/5 | 30.8s | Slowest |
| 3 | GPT-4o Mini | $0.129 | 7 | 5/5 | 18.4s | Reliable |
| 4 | Claude 3.5 Haiku | $0.816 | 7 | 5/5 | 24.7s | 6x more expensive |
| 5 | GPT-4o | $2.155 | 6 | 5/5 | 12.4s | **FASTEST** |

#### Failed Models (5/10)

| Model | Cost/1K | Error |
|-------|---------|-------|
| Llama 3.1 8B | $0.0145 | Pydantic validation error (ExtractedEdges) |
| Mistral 7B | $0.0167 | Pydantic validation error (ExtractedEntities) |
| DeepSeek V3 | $0.0585 | Pydantic validation error (ExtractedEntities) |
| Llama 3.3 70B | $0.114 | Processing timeout |
| Claude Sonnet 4 | $4.215 | Processing timeout |

### Grok Model MCP Test Results

**Test**: Real-life entity extraction via MCP with Graphiti
**All 5 Grok models tested via OpenRouter**

#### Working Grok Models (1/5)

| Model | Cost/1K | Entities | Expected | Time | Notes |
|-------|---------|----------|----------|------|-------|
| **Grok 3** | $2.163 | 8 | 5/5 | 22.5s | Only working Grok model |

#### Failed Grok Models (4/5)

| Model | Cost/1K | Error |
|-------|---------|-------|
| Grok 4 Fast | $0.280 | Pydantic validation error (ExtractedEntities) |
| Grok 4.1 Fast | $0.434 | Processing timeout |
| Grok 3 Mini | $0.560 | Processing timeout |
| Grok 4 | $11.842 | Processing timeout |

**Key Grok Findings**:
1. Only **Grok 3** works with Graphiti - all other variants fail
2. Cheaper "Fast" variants fail with validation errors (similar to open-source models)
3. Even the most expensive Grok 4 ($11.84/1K) times out
4. Grok 3 extracts 8 entities (same as Gemini 2.0 Flash) but costs 17x more

**Key Findings**:
1. All open-source models (Llama, Mistral, DeepSeek) fail Graphiti's Pydantic validation
2. **Gemini 2.0 Flash is the cheapest working model** - same cost tier as failed open-source models
3. Claude Sonnet 4 times out despite being the most expensive
4. GPT-4o is fastest but costs 17x more than Gemini 2.0 Flash

---

## Conclusion

The MadeInOz Knowledge System works correctly with Neo4j backend and OpenRouter integration. Comprehensive testing of all 15 models (10 benchmark + 5 Grok) revealed that only 6 work with Graphiti's strict Pydantic schemas.

### Optimal Configuration (UPDATED)
```env
# OpenRouter API - Use Gemini 2.0 Flash (cheapest working model)
MADEINOZ_KNOWLEDGE_OPENAI_API_KEY=sk-or-v1-...
MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL=https://openrouter.ai/api/v1
MADEINOZ_KNOWLEDGE_MODEL_NAME=google/gemini-2.0-flash-001

# Embedder (Ollama - free and fast)
MADEINOZ_KNOWLEDGE_EMBEDDER_BASE_URL=http://localhost:11434/v1
MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL=mxbai-embed-large
```

### Cost Analysis (Real-Life Tested - All 15 Models)

| Configuration | Cost/1K | Status |
|---------------|---------|--------|
| Gemini 2.0 Flash + MxBai | **$0.125** | ✅ **RECOMMENDED** |
| Qwen 2.5 72B + MxBai | $0.126 | ✅ Works (slow) |
| GPT-4o Mini + MxBai | $0.129 | ✅ Works |
| Claude 3.5 Haiku + MxBai | $0.816 | ✅ Works |
| GPT-4o + MxBai | $2.155 | ✅ Works (fastest) |
| Grok 3 + MxBai | $2.163 | ✅ Works |
| Grok 4 Fast + MxBai | $0.280 | ❌ Fails validation |
| Llama 3.1 8B + MxBai | $0.0145 | ❌ Fails validation |

### Final Recommendations

1. **Best Value**: Use **Gemini 2.0 Flash** via OpenRouter
   - Cheapest working model at $0.125/1K
   - Extracts most entities (8 vs 6-7 for others)
   - 16.4s extraction time

2. **For Speed-Critical**: Use GPT-4o via OpenRouter
   - Fastest at 12.4s extraction
   - Costs 17x more than Gemini ($2.155/1K)

3. **For xAI/Grok Users**: Use **Grok 3** (only working Grok model)
   - $2.163/1K - same tier as GPT-4o
   - Extracts 8 entities (same as Gemini)
   - 22.5s extraction time
   - Note: Grok 4 Fast, 4.1 Fast, 3 Mini, and Grok 4 all fail

4. **Avoid Open-Source Models**: Llama, Mistral, DeepSeek all fail
   - Pydantic validation errors with Graphiti schemas
   - Would need Graphiti patches to support

5. **Avoid "Fast" Model Variants**: Grok Fast variants also fail
   - Similar validation errors to open-source models
   - The speed optimizations break schema compliance

6. **For Embeddings**: Use MxBai Embed Large via Ollama
   - FREE, 87ms response time
   - 73.9% quality score

### Savings vs Original Config

| Metric | OpenAI Direct (gpt-4o-mini) | OpenRouter (Gemini 2.0 Flash) |
|--------|----------------------------|-------------------------------|
| Cost/1K | ~$0.15 | $0.125 |
| Entities | 7 | 8 |
| Speed | 18s | 16s |
| **Savings** | - | **17% cheaper, better results** |
