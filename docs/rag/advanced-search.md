---
title: "Advanced RAG Search"
description: "Advanced retrieval techniques including reranking, hybrid search, HyDE, and multi-query"
---

# Advanced RAG Search

The RAG system includes several advanced retrieval techniques that improve search accuracy and recall. These are enabled by default and can be configured via environment variables.

## Overview

| Feature | Purpose | Improvement |
|---------|---------|-------------|
| **Reranker** | Cross-encoder relevance scoring | +30-40% accuracy |
| **Hybrid Search** | BM25 + dense vector fusion | +20% recall |
| **HyDE** | Hypothetical document expansion | Better for short queries |
| **Multi-Query** | Query variant generation | Covers more interpretations |
| **Query Classifier** | Adaptive retrieval routing | Right strategy per query |

## Search Pipeline

```
Query → Query Classifier → [HyDE?] → [Multi-Query?] → Hybrid Search → Reranker → Results
            ↓                    ↓            ↓              ↓            ↓
        Type: factual       Expand      3 variants     Dense+BM25   Cross-encoder
            conceptual       short        merged         RRF         top-k
```

---

## Reranker

Cross-encoder reranking improves retrieval accuracy by 30-40% by using a more precise (but slower) model to score candidates.

### How It Works

1. **Initial retrieval**: Bi-encoder (fast, approximates relevance) returns top-20
2. **Reranking**: Cross-encoder (slow, precise) scores each candidate
3. **Final results**: Top-10 by cross-encoder score

### When Reranking Helps

- **High-precision requirements** - Need the most relevant results
- **Complex queries** - Multiple concepts or ambiguous terms
- **Production systems** - "Never skip reranking for production RAG"

### Configuration

```bash
# Enable/disable reranking (default: true)
MADEINOZ_KNOWLEDGE_RERANKER_ENABLED=true

# Cross-encoder model
MADEINOZ_KNOWLEDGE_RERANKER_MODEL=BAAI/bge-reranker-base

# Candidates to rerank (default: 20)
MADEINOZ_KNOWLEDGE_RERANKER_TOP_K=20

# Final results after reranking (default: 10)
MADEINOZ_KNOWLEDGE_RERANKER_FINAL_K=10

# Provider: local, openrouter, cohere (default: local)
MADEINOZ_KNOWLEDGE_RERANKER_PROVIDER=local
```

---

## Hybrid Search

Combines vector similarity (dense) with keyword matching (sparse/BM25) for better recall, especially for:

- **Acronyms and proper nouns** - "GPT-4" vs "GPT" and "4"
- **Exact phrase matching** - "machine learning" as phrase
- **Rare terms** - Not well-represented in embedding space

### How It Works

1. **Dense retrieval**: Vector similarity via Qdrant
2. **Sparse retrieval**: BM25 keyword matching via Qdrant text index
3. **Fusion**: Reciprocal Rank Fusion (RRF) combines results

### RRF Formula

```
score(d) = sum(1 / (k + rank)) for each result list
k = 60 (dampens rank impact)
```

### Configuration

```bash
# Enable hybrid search (default: true)
MADEINOZ_KNOWLEDGE_HYBRID_ENABLED=true

# Weight for dense vs sparse (default: 0.7 = favor dense)
MADEINOZ_KNOWLEDGE_HYBRID_ALPHA=0.7

# RRF constant k (default: 60)
MADEINOZ_KNOWLEDGE_HYBRID_RRF_K=60
```

---

## HyDE (Hypothetical Document Embeddings)

Generates a hypothetical answer to the query, then retrieves documents similar to that hypothetical document. Best for short, ambiguous queries.

### How It Works

1. **Query**: "login issues"
2. **Hypothetical doc**: "Authentication errors may occur due to invalid credentials, expired sessions, or password reset requirements..."
3. **Retrieve**: Find docs similar to hypothetical

### When HyDE Helps

- Short, ambiguous queries ("login issues")
- Queries with little domain terminology
- Documents are more verbose than queries

### When to Skip HyDE

- Long, specific queries (already contain good keywords)
- Latency is critical (requires LLM call)
- LLM might hallucinate domain terminology

### Configuration

```bash
# Enable HyDE expansion (default: true)
MADEINOZ_KNOWLEDGE_HYDE_ENABLED=true

# Min query tokens to trigger HyDE (default: 10)
MADEINOZ_KNOWLEDGE_HYDE_MIN_QUERY_TOKENS=10

# Max tokens in hypothetical document (default: 200)
MADEINOZ_KNOWLEDGE_HYDE_MAX_HYPOTHETICAL_TOKENS=200
```

### Cost

- Adds LLM call per query (~$0.002 per query at 200 tokens)
- For 10K queries/day: ~$600/month

---

## Multi-Query Variants

Generates multiple query variants/rephrasings, retrieves for each, then merges results using RRF.

### How It Works

1. **Original query**: "How do I configure SPI?"
2. **Variants**:
   - "SPI configuration settings"
   - "Set up Serial Peripheral Interface"
   - "SPI master/slave setup guide"
3. **Retrieve** for each variant
4. **Merge** with RRF

### When Multi-Query Helps

- Complex queries with multiple interpretations
- Queries that might match different terminology
- Single query retrieval yields poor results

### When to Skip

- Simple, well-defined queries
- Exact match queries (keywords, IDs)
- Latency is critical

### Configuration

```bash
# Enable multi-query (default: true)
MADEINOZ_KNOWLEDGE_MULTI_QUERY_ENABLED=true

# Min query length to trigger (default: 10)
MADEINOZ_KNOWLEDGE_MULTI_QUERY_MIN_LENGTH=10

# Number of variants to generate (default: 3)
MADEINOZ_KNOWLEDGE_MULTI_QUERY_NUM_VARIANTS=3
```

---

## Query Classifier

Classifies query type and routes to appropriate retrieval strategy.

### Query Types

| Type | Description | Best Strategy |
|------|-------------|---------------|
| **factual** | Specific facts, exact matches | Keyword retriever |
| **procedural** | How-to, step-by-step | Hierarchical retriever |
| **conceptual** | Explanations, understanding | Vector retriever |
| **comparative** | Comparing options | Multi-document |
| **temporal** | Time-sensitive | Time-filtered |
| **ambiguous** | Needs clarification | Ask clarification |

### Classification Methods

- **Rule-based** (fast, no LLM cost) - Default
- **LLM-based** (more accurate, higher cost)
- **Hybrid** (rules first, LLM for ambiguous)

### Configuration

```bash
# Enable classification (default: true)
MADEINOZ_KNOWLEDGE_QUERY_CLASSIFIER_ENABLED=true

# Use LLM for classification (default: false = rule-based)
MADEINOZ_KNOWLEDGE_QUERY_CLASSIFIER_USE_LLM=false
```

---

## Complete Configuration Reference

Add these to your `.env` file:

```bash
# Reranker
MADEINOZ_KNOWLEDGE_RERANKER_ENABLED=true
MADEINOZ_KNOWLEDGE_RERANKER_MODEL=BAAI/bge-reranker-base
MADEINOZ_KNOWLEDGE_RERANKER_TOP_K=20
MADEINOZ_KNOWLEDGE_RERANKER_FINAL_K=10
MADEINOZ_KNOWLEDGE_RERANKER_PROVIDER=local

# Hybrid Search
MADEINOZ_KNOWLEDGE_HYBRID_ENABLED=true
MADEINOZ_KNOWLEDGE_HYBRID_ALPHA=0.7
MADEINOZ_KNOWLEDGE_HYBRID_RRF_K=60

# HyDE
MADEINOZ_KNOWLEDGE_HYDE_ENABLED=true
MADEINOZ_KNOWLEDGE_HYDE_MIN_QUERY_TOKENS=10
MADEINOZ_KNOWLEDGE_HYDE_MAX_HYPOTHETICAL_TOKENS=200

# Multi-Query
MADEINOZ_KNOWLEDGE_MULTI_QUERY_ENABLED=true
MADEINOZ_KNOWLEDGE_MULTI_QUERY_MIN_LENGTH=10
MADEINOZ_KNOWLEDGE_MULTI_QUERY_NUM_VARIANTS=3

# Query Classifier
MADEINOZ_KNOWLEDGE_QUERY_CLASSIFIER_ENABLED=true
MADEINOZ_KNOWLEDGE_QUERY_CLASSIFIER_USE_LLM=false
```

---

## Performance vs Accuracy Trade-offs

| Configuration | Latency | Accuracy | Cost | Use Case |
|--------------|---------|----------|------|----------|
| All enabled | High | Best | High | Production, critical |
| Reranker only | Medium | Good | Low | Balanced |
| Hybrid only | Low | Good | Free | Speed priority |
| All disabled | Fastest | Baseline | Free | Development |

## Disabling Features

For faster development iteration, disable advanced features:

```bash
# Fast development mode
MADEINOZ_KNOWLEDGE_RERANKER_ENABLED=false
MADEINOZ_KNOWLEDGE_HYBRID_ENABLED=false
MADEINOZ_KNOWLEDGE_HYDE_ENABLED=false
MADEINOZ_KNOWLEDGE_MULTI_QUERY_ENABLED=false
```

## Related Documentation

- [RAG Quickstart](quickstart.md) - Basic search usage
- [RAG Configuration](configuration.md) - Qdrant and Ollama setup
- [RAG Troubleshooting](troubleshooting.md) - Common issues
