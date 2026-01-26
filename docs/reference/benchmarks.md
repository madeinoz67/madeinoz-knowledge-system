---
title: "Model Benchmark Results"
description: "Performance benchmarks for LLM and embedding models with the Madeinoz Knowledge System"
---

# Model Benchmark Results - MadeInOz Knowledge System

**Last Updated:** 2026-01-18
**Database:** Neo4j (neo4j:5.28.0)
**MCP Server:** zepai/knowledge-graph-mcp:standalone
**Local Ollama Tests:** NVIDIA RTX 4090 GPU (24GB VRAM)

---

## Executive Summary

!!! success "Key Finding: Hybrid Architecture is Optimal"
    The best configuration combines **cloud LLM for entity extraction** with **local Ollama embeddings for search**. This approach delivers cloud-quality accuracy with local speed and cost savings.

### Real-World Test Results

We tested 15 different models with actual MCP integration via Graphiti. The results were decisive:

- ✅ **6 models work** with Graphiti's strict Pydantic schemas
- ❌ **9 models fail** with validation errors or timeouts
- 🏆 **Gemini 2.0 Flash is the best value** - cheapest working model with best entity extraction

!!! warning "Critical Discovery"
    ALL open-source models (Llama 3.1 8B, Llama 3.3 70B, Mistral 7B, DeepSeek V3) **FAIL** in real MCP integration despite passing simple JSON tests. They produce Pydantic validation errors with Graphiti's entity/relationship schemas.

---

## Recommended Configurations

| Use Case | LLM | Embedding | Cost/1K Ops | Why This? |
|----------|-----|-----------|-------------|-----------|
| **Best Value** | Gemini 2.0 Flash | MxBai (Ollama) | $0.125 | Cheapest working model, extracts 8 entities, 16.4s |
| **Most Reliable** | GPT-4o Mini | MxBai (Ollama) | $0.129 | Production-proven, 7 entities, 18.4s |
| **Fastest** | GPT-4o | MxBai (Ollama) | $2.155 | 12.4s extraction, 6 entities |
| **Premium** | Claude 3.5 Haiku | MxBai (Ollama) | $0.816 | 7 entities, 24.7s |

!!! tip "Hybrid Approach = Best Results"
    Use **cloud LLM** (accurate entity extraction) + **local Ollama embeddings** (free, 9x faster). This combines the strengths of both approaches.

---

## Embedding Models: Local vs Cloud

### Why Embeddings Matter

Embeddings power semantic search. Every time you search your knowledge graph, embeddings convert your query into a vector and find similar vectors in the database. **Choose wisely - you cannot change models without re-indexing all data.**

### Benchmark Results

Tested for semantic similarity accuracy using 8 test pairs (5 similar, 3 dissimilar).

| Rank | Model | Provider | Quality | Cost/1M | Speed | Dimensions |
|------|-------|----------|---------|---------|-------|------------|
| 1 | **Embed 3 Small** | OpenRouter | 78.2% | $0.02 | 824ms | 1536 |
| 2 | Embed 3 Large | OpenRouter | 77.3% | $0.13 | 863ms | 3072 |
| 3 | **MxBai Embed Large** ⭐ | Ollama | 73.9% | **FREE** | **87ms** | 1024 |
| 4 | Nomic Embed Text | Ollama | 63.5% | FREE | 93ms | 768 |
| 5 | Ada 002 | OpenRouter | 58.8% | $0.10 | 801ms | 1536 |

⭐ **Recommended**: MxBai Embed Large via Ollama

### Key Insights

!!! success "MxBai Embed Large Wins"
    - **Quality**: 73.9% (only 4% lower than best paid model)
    - **Speed**: 87ms (9x faster than cloud models)
    - **Cost**: FREE (runs locally via Ollama)
    - **Dimensions**: 1024 (good balance - not too large, not too small)

!!! info "When to Use Cloud Embeddings"
    Use **Embed 3 Small** if you:
    - Don't have GPU/can't run Ollama locally
    - Need absolute best quality (78.2% vs 73.9%)
    - Don't mind 9x slower queries and $0.02/1M cost

### ⚠️ CRITICAL: Changing Embedding Models Breaks Everything

!!! danger "No Migration Path - Choose Once"
    **Switching embedding models requires re-indexing ALL data.** Each model produces different vector dimensions:

    | Model | Dimensions |
    |-------|------------|
    | mxbai-embed-large | 1024 |
    | nomic-embed-text | 768 |
    | text-embedding-3-small | 1536 |
    | text-embedding-3-large | 3072 |

    Neo4j's vector search requires all vectors to have identical dimensions. If you index with Model A (768 dims) then switch to Model B (1024 dims), **all searches fail** with:

    ```
    Invalid input for 'vector.similarity.cosine()':
    The supplied vectors do not have the same number of dimensions
    ```

**To switch models safely:**

1. **Export important knowledge** (manually note key facts)
2. **Clear the graph**: Use `clear_graph` MCP tool
3. **Update config**:

   ```env
   MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL=your-new-model
   MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS=matching-dimension
   ```

4. **Restart the server**
5. **Re-add all knowledge**

!!! tip "Best Practice"
    Choose `mxbai-embed-large` at installation and never change it. Best balance of quality (73.9%), speed (87ms), and cost (FREE).

---

## LLM Models: What Actually Works

### Real-Life MCP Integration Test Results

We tested **all 15 models** with actual Graphiti integration, not just simple JSON extraction. The test used a complex business scenario requiring extraction of companies, people, locations, and relationships.

**Test Input:**

```
"During the Q4 planning meeting at TechCorp headquarters in Austin, CEO Sarah
Martinez announced a strategic partnership with CloudBase Inc, brokered by
Morgan Stanley. The deal includes cloud infrastructure migration and a
200-person engineering team based in Seattle."
```

**Expected Entities:** TechCorp, Sarah Martinez, CloudBase Inc, Morgan Stanley, Austin, Seattle

### ✅ Working Models (6/15)

These models successfully extract entities AND relationships, passing Graphiti's strict Pydantic validation:

| Rank | Model | Cost/1K | Entities | Time | Quality Score |
|------|-------|---------|----------|------|---------------|
| 1 | **Gemini 2.0 Flash** 🏆 | $0.125 | 8/5 | 16.4s | ⭐⭐⭐⭐⭐ |
| 2 | Qwen 2.5 72B | $0.126 | 8/5 | 30.8s | ⭐⭐⭐⭐ |
| 3 | GPT-4o Mini | $0.129 | 7/5 | 18.4s | ⭐⭐⭐⭐⭐ |
| 4 | Claude 3.5 Haiku | $0.816 | 7/5 | 24.7s | ⭐⭐⭐⭐ |
| 5 | GPT-4o | $2.155 | 6/5 | 12.4s | ⭐⭐⭐⭐⭐ |
| 6 | Grok 3 | $2.163 | 8/5 | 22.5s | ⭐⭐⭐ |

!!! note "Entity Count Explanation"
    "8/5" means: Extracted 8 entities total (including extras beyond the 5 required). This shows the model identified additional relevant entities like "cloud infrastructure" or "Q4 planning meeting".

### ❌ Failed Models (9/15)

These models **DO NOT WORK** with Graphiti despite passing simple JSON tests:

| Model | Cost/1K | Error Type | Why It Fails |
|-------|---------|------------|--------------|
| Llama 3.1 8B | $0.0145 | Pydantic validation | Invalid ExtractedEdges schema |
| Llama 3.3 70B | $0.114 | Processing timeout | Cannot complete extraction |
| Mistral 7B | $0.0167 | Pydantic validation | Invalid ExtractedEntities schema |
| DeepSeek V3 | $0.0585 | Pydantic validation | Invalid ExtractedEntities schema |
| Claude Sonnet 4 | $4.215 | Processing timeout | Too slow for Graphiti |
| Grok 4 Fast | $0.280 | Pydantic validation | Invalid ExtractedEntities schema |
| Grok 4.1 Fast | $0.434 | Processing timeout | Cannot complete extraction |
| Grok 3 Mini | $0.560 | Processing timeout | Cannot complete extraction |
| Grok 4 | $11.842 | Processing timeout | Even most expensive Grok fails |

!!! warning "Why Open-Source Models Fail"
    Llama, Mistral, and DeepSeek models cannot produce JSON that matches Graphiti's strict Pydantic schemas. They work for simple JSON extraction but fail when integrated with the actual knowledge graph system. The "cheap" models listed in early benchmarks **DO NOT WORK** in production.

### Cost vs Performance vs Accuracy Matrix

| Model | Cost | Speed | Entities | Best For |
|-------|------|-------|----------|----------|
| **Gemini 2.0 Flash** | 💰 Cheapest | ⚡ Fast (16s) | 🎯 Most (8) | **RECOMMENDED** |
| GPT-4o Mini | 💰 Cheap | ⚡ Fast (18s) | 🎯 Good (7) | Reliability |
| Qwen 2.5 72B | 💰 Cheap | 🐌 Slow (31s) | 🎯 Most (8) | Quality over speed |
| Claude 3.5 Haiku | 💰💰 Mid | ⚡ Medium (25s) | 🎯 Good (7) | Claude ecosystem |
| GPT-4o | 💰💰💰 Premium | ⚡⚡ Fastest (12s) | 🎯 Good (6) | Speed critical |
| Grok 3 | 💰💰💰 Premium | ⚡ Medium (23s) | 🎯 Most (8) | xAI ecosystem |

!!! tip "Model Selection Guide"
    - **Default choice**: Gemini 2.0 Flash ($0.125/1K, 8 entities, fast)
    - **Need reliability**: GPT-4o Mini ($0.129/1K, production-proven)
    - **Need speed**: GPT-4o ($2.155/1K, 12s extraction)
    - **Already use Claude**: Claude 3.5 Haiku ($0.816/1K)
    - **Already use xAI**: Grok 3 only (all other Grok variants fail)

---

## Configuration Examples

### Best Value Configuration (Recommended)

Use **Gemini 2.0 Flash + MxBai Embed Large** for optimal cost/performance:

```env
# LLM: Gemini 2.0 Flash via OpenRouter
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openrouter
MADEINOZ_KNOWLEDGE_OPENAI_API_KEY=sk-or-v1-...
MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL=https://openrouter.ai/api/v1
MADEINOZ_KNOWLEDGE_MODEL_NAME=google/gemini-2.0-flash-001

# Embeddings: MxBai via Ollama (local)
MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER=ollama
MADEINOZ_KNOWLEDGE_EMBEDDER_BASE_URL=http://localhost:11434/v1
MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL=mxbai-embed-large
MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS=1024
```

**Cost**: $0.125/1K operations + FREE embeddings
**Performance**: 16.4s extraction, 87ms search
**Quality**: 8 entities extracted, 73.9% embedding quality

### Production-Proven Configuration

Use **GPT-4o Mini + MxBai** for reliability:

```env
# LLM: GPT-4o Mini via OpenRouter
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openrouter
MADEINOZ_KNOWLEDGE_OPENAI_API_KEY=sk-or-v1-...
MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL=https://openrouter.ai/api/v1
MADEINOZ_KNOWLEDGE_MODEL_NAME=openai/gpt-4o-mini

# Embeddings: MxBai via Ollama (local)
MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER=ollama
MADEINOZ_KNOWLEDGE_EMBEDDER_BASE_URL=http://localhost:11434/v1
MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL=mxbai-embed-large
MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS=1024
```

**Cost**: $0.129/1K operations + FREE embeddings
**Performance**: 18.4s extraction, 87ms search
**Quality**: 7 entities extracted, 73.9% embedding quality

### Speed-Critical Configuration

Use **GPT-4o + MxBai** when speed matters more than cost:

```env
# LLM: GPT-4o via OpenRouter
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openrouter
MADEINOZ_KNOWLEDGE_OPENAI_API_KEY=sk-or-v1-...
MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL=https://openrouter.ai/api/v1
MADEINOZ_KNOWLEDGE_MODEL_NAME=openai/gpt-4o

# Embeddings: MxBai via Ollama (local)
MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER=ollama
MADEINOZ_KNOWLEDGE_EMBEDDER_BASE_URL=http://localhost:11434/v1
MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL=mxbai-embed-large
MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS=1024
```

**Cost**: $2.155/1K operations + FREE embeddings
**Performance**: 12.4s extraction (fastest), 87ms search
**Quality**: 6 entities extracted, 73.9% embedding quality

### Cloud-Only Configuration

Use **GPT-4o Mini + Embed 3 Small** if you can't run Ollama locally:

```env
# LLM: GPT-4o Mini via OpenRouter
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openrouter
MADEINOZ_KNOWLEDGE_OPENAI_API_KEY=sk-or-v1-...
MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL=https://openrouter.ai/api/v1
MADEINOZ_KNOWLEDGE_MODEL_NAME=openai/gpt-4o-mini

# Embeddings: Embed 3 Small via OpenRouter
MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER=openrouter
MADEINOZ_KNOWLEDGE_EMBEDDER_BASE_URL=https://openrouter.ai/api/v1
MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL=openai/text-embedding-3-small
MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS=1536
```

**Cost**: $0.129/1K + $0.02/1M embeddings
**Performance**: 18.4s extraction, 824ms search (9x slower)
**Quality**: 7 entities extracted, 78.2% embedding quality (4% better)

---

## Cost Analysis

### Monthly Cost Comparison (10,000 operations)

| Configuration | LLM Cost | Embed Cost | Total/Month |
|---------------|----------|------------|-------------|
| **Gemini 2.0 Flash + MxBai** (Recommended) | $1.25 | $0 | **$1.25** |
| GPT-4o Mini + MxBai (Production) | $1.29 | $0 | **$1.29** |
| GPT-4o + MxBai (Speed) | $21.55 | $0 | **$21.55** |
| GPT-4o Mini + Embed 3 Small (Cloud-only) | $1.29 | $0.20 | **$1.49** |

!!! success "Cost Savings with Hybrid"
    Using local Ollama embeddings saves **$0.20/10K operations** compared to cloud embeddings, while delivering 9x faster search queries.

### What You Actually Pay For

- **LLM calls**: Every `add_memory` operation (entity/relationship extraction)
- **Embedding calls**: Every `add_memory` (encode episode) + every search query
- **Database**: FREE (self-hosted Neo4j or FalkorDB)

**Example monthly breakdown** (1000 episodes added, 5000 searches):

- Gemini 2.0 Flash (1000 extractions): $0.125
- MxBai embeddings (1000 + 5000 operations): $0.00 (local)
- **Total**: $0.125/month

---

## Real-Life Validation Tests

### Test 1: Business Entity Extraction

**Input:**

```
"During the Q4 planning meeting, CEO Michael Chen announced that TechVentures
Inc will acquire DataFlow Systems for $500 million. The deal, brokered by
Goldman Sachs, includes all patents and the 200-person engineering team based
in Seattle."
```

**Results with GPT-4o Mini:**

✅ **Extracted Entities** (verified in Neo4j):

- DataFlow Systems
- Goldman Sachs
- Michael Chen
- Seattle
- TechVentures Inc

✅ **Extracted Facts**:

- "The acquisition deal of DataFlow Systems was brokered by Goldman Sachs"
- "TechVentures Inc will acquire DataFlow Systems for $500 million"
- "DataFlow Systems has a 200-person engineering team based in Seattle"

**Validation**: 5/5 entities, 3 relationship facts extracted successfully

### Test 2: Technical Team Context

**Input:**

```
"Team uses TypeScript with Bun runtime. Sarah, our tech lead, chose Hono for
the HTTP framework because it's lightweight and fast."
```

**Results with GPT-4o Mini:**

✅ **Extracted Entities**:

- TypeScript
- Bun
- Sarah
- Hono
- HTTP framework

✅ **Extracted Facts**:

- "The team uses TypeScript with Bun"
- "Hono is an HTTP framework"
- "Sarah chose Hono as the HTTP framework"

**Validation**: All entities and relationships captured correctly

### Test 3: MCP Operation Performance

Tested all MCP operations with real data:

| Operation | Success Rate | Avg Time | Results |
|-----------|--------------|----------|---------|
| add_memory | 100% (3/3) | ~6ms | All episodes queued |
| search_nodes | 100% (3/3) | ~60ms | 10 nodes per query |
| search_memory_facts | 100% (3/3) | ~50ms | 9 facts per query |
| get_episodes | 100% (1/1) | ~5ms | All episodes retrieved |

!!! success "Production Ready"
    All MCP operations work reliably with the recommended Gemini 2.0 Flash + MxBai configuration.

---

## Technical Testing Details

### Test Environment

- **Database**: Neo4j 5.28.0 (docker)
- **MCP Server**: zepai/knowledge-graph-mcp:standalone
- **Ollama**: Running on NVIDIA RTX 4090 GPU (24GB VRAM)
- **Network**: Local Docker network for Neo4j, separate Ollama instance

### Test Scripts

- `test-all-llms-mcp.ts` - Comprehensive MCP test for 10 benchmark models
- `test-grok-llms-mcp.ts` - Grok models MCP test (5 variants)
- `test-search-debug.ts` - MCP integration validation script

### Methodology

1. **Entity Extraction Test**: Complex business scenario with 5+ entities
2. **Validation**: Check Neo4j directly for extracted entities/relationships
3. **Schema Compliance**: Verify Pydantic validation passes
4. **Timeout**: 60s limit for extraction (production realistic)
5. **Success Criteria**: All entities extracted + valid JSON schemas

---

## Conclusion

### Key Takeaways

!!! success "What Works"
    1. **Hybrid architecture** (cloud LLM + local embeddings) is optimal
    2. **Gemini 2.0 Flash** is the best value at $0.125/1K
    3. **MxBai Embed Large** via Ollama is best embedding choice (free, fast, good quality)
    4. **Only 6 models work** with Graphiti - ignore benchmarks showing cheap open-source models

!!! warning "What Doesn't Work"
    1. **ALL open-source LLMs fail** (Llama, Mistral, DeepSeek) - Pydantic validation errors
    2. **Most Grok variants fail** - Only Grok 3 works ($2.16/1K)
    3. **"Fast" models fail** - Speed optimizations break schema compliance
    4. **Simple JSON tests lie** - Real MCP integration is the only valid test

!!! tip "Recommended Setup"
    Start with **Gemini 2.0 Flash + MxBai Embed Large**:
    - Costs $0.125/1K operations (cheapest working model)
    - Extracts 8 entities (best performance)
    - 16.4s extraction time (fast enough)
    - FREE, fast local embeddings (87ms searches)
    - Total cost: ~$1.25/month for 10K operations

### Migration from Other Configs

If you're currently using:

- **GPT-4o Mini**: Switch to Gemini 2.0 Flash (3% savings, 1 more entity extracted)
- **Claude Sonnet 4**: Switch to Gemini 2.0 Flash (97% savings, no timeouts)
- **Llama/Mistral/DeepSeek**: Switch to Gemini 2.0 Flash (these don't actually work)
- **Any cloud embeddings**: Switch to MxBai via Ollama (saves $0.02-$0.13/1M, 9x faster)

### Future Considerations

- **Watch for Graphiti updates** that might support open-source models
- **Monitor Ollama** for new embedding models with better quality
- **Test new cloud models** as they're released (especially cheaper options)

**The bottom line**: Don't trust simple JSON benchmarks. Real MCP integration with Graphiti is the only valid test. Use this guide to choose models that actually work in production.
