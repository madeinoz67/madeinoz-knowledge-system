---
title: "Ollama Model Compatibility Guide"
description: "LLM and embedding model compatibility for Ollama with the Madeinoz Knowledge System"
---

# Ollama Model Compatibility Guide

This guide documents which Ollama models work with the Madeinoz Knowledge System for entity extraction and embeddings.

## Architecture Overview

The knowledge system uses two types of AI models:

| Component | Purpose | Requirements |
|-----------|---------|--------------|
| **LLM** | Entity extraction, relationship detection | Must output valid JSON matching Pydantic schemas |
| **Embedder** | Vector embeddings for semantic search | Must support `/v1/embeddings` endpoint |

## Recommended Configuration

For cost savings while maintaining reliability, we recommend a **hybrid setup**:

```env
# LLM: gemini-2.0-Flash (reliable JSON output for entity extraction)
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openai
MADEINOZ_KNOWLEDGE_MODEL_NAME=google/gemini-2.0-flash-001
MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL=https://openrouter.ai/api/v1
MADEINOZ_KNOWLEDGE_OPENAI_API_KEY=your-openrouter-api-key

# Embedder: Ollama (free local embeddings)
MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER=openai
MADEINOZ_KNOWLEDGE_EMBEDDER_BASE_URL=http://your-ollama-server:11434/v1
MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL=mxbai-embed-large
MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS=1024
```

This configuration:

- Uses gemini-2.0-flash-001 via OpenRouter for LLM (reliable and cost effective)
- Note: `LLM_PROVIDER=openai` because OpenRouter is OpenAI-compatible
- Uses Ollama for embeddings (free, runs locally)
- Reduces cloud costs while maintaining extraction quality

## Cost Comparison

| Configuration | LLM Cost | Embedding Cost | Total |
|---------------|----------|----------------|-------|
| Full OpenAI | ~$0.15/1M tokens | ~$0.02/1M tokens | $$$ |
| Hybrid (recommended) | ~$0.15/1M tokens | Free | $$ |
| Full Ollama | Free | Free | Free* |

*Full Ollama has reliability trade-offs for entity extraction.

## Model Test Results

Tested on: 2026-01-18

### Basic JSON Extraction Test

We tested 16 Ollama LLM models for basic JSON extraction capability. This test uses a simple entity extraction prompt to evaluate JSON output quality.

#### Passed (15 models)

| Model | Entities | Relationships | Response Time |
|-------|----------|---------------|---------------|
| **Deepseek-r1:8b** | 5 | 4 | 3,164ms |
| **mistral:instruct** | 4 | 3 | 3,210ms |
| **tulu3:latest** | 4 | 2 | 3,742ms |
| **llama3.1:latest** | 4 | 1 | 3,837ms |
| **mistral:latest** | 3 | 1 | 4,257ms |
| **phi4:latest** | 4 | 3 | 5,459ms |
| **qwen3-coder:latest** | 5 | 4 | 5,852ms |
| **Deepseek-r1:latest** | 5 | 4 | 5,896ms |
| **deepseek-coder-v2:latest** | 4 | 2 | 6,243ms |
| **gemma2:9b** | 5 | 2 | 6,802ms |
| **dolphin-mistral** | 5 | 1 | 6,844ms |
| **phi3:medium** | 5 | 2 | 7,993ms |
| **Qwen3:latest** | 5 | 3 | 9,581ms |
| **codestral:latest** | 4 | 3 | 10,108ms |
| **Qwen3:8b** | 5 | 3 | 16,005ms |

#### Failed (1 model)

| Model | Reason |
|-------|--------|
| **Llama3.2:latest** | Truncated JSON response |

### Important Caveats

**Basic Test vs Real Usage**: The test above uses a simplified entity extraction prompt. Graphiti uses more complex Pydantic schemas with specific field requirements. Models that pass the basic test may still fail with Graphiti's actual schemas.

**Observed Issues in Production**:

| Model | Basic Test | Graphiti Production | Issue |
|-------|------------|---------------------|-------|
| Llama3.2:latest | ❌ | ❌ | Truncated responses |
| **Deepseek-r1:8b** | ✅ | ❌ | ValidationError on NodeResolutions - outputs schema instead of data |
| Deepseek-r1:latest | ✅ | ❌ | ValidationError on NodeResolutions |
| Mistral | ✅ | ❌ | Malformed JSON on ExtractedEdges |

**Latest Test (2026-01-18)**: Deepseek-r1:8b tested with actual Graphiti schemas:

```
Error processing queued episode: 1 validation error for NodeResolutions
entity_resolutions
  Field required [type=missing, input_value={'$defs': {'NodeDuplicate...
```

The model outputs JSON schema definitions instead of data conforming to the schema.

**Recommendation**: For production LLM use, stick with OpenAI models (gpt-4o-mini, gpt-4o) which reliably produce valid JSON matching Graphiti's Pydantic schemas.

## Embedding Models

### Performance Comparison (Tested 2026-01-18)

| Rank | Model | Quality | Speed | Dimensions |
|------|-------|---------|-------|------------|
| 🥇 | **mxbai-embed-large** | 77.0% | 156ms | 1024 |
| 🥈 | nomic-embed-text-v2-moe | 76.4% | 2507ms | 768 |
| 🥉 | embeddinggemma | 75.8% | 384ms | 768 |
| 4 | qwen3-embedding:0.6b | 73.3% | 312ms | 1024 |
| 5 | nomic-embed-text | 66.0% | 426ms | 768 |

**Quality Score**: Based on semantic similarity tests (higher = better at distinguishing similar vs dissimilar content)

### Recommended Configuration

```env
MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER=openai
MADEINOZ_KNOWLEDGE_EMBEDDER_BASE_URL=http://your-ollama-server:11434/v1
MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL=mxbai-embed-large
MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS=1024
```

**Why mxbai-embed-large?**

- **Fastest** response time (156ms avg)
- **Highest** semantic quality (77.0%)
- Higher dimensions (1024) capture more nuance

### Ollama vs OpenAI Embeddings (Tested 2026-01-18)

Direct comparison between Ollama mxbai-embed-large and OpenAI text-embedding-3-small:

| Test Case | Expected | Ollama | OpenAI | Winner |
|-----------|----------|--------|--------|--------|
| Cat/Feline synonyms | high | 80.8% | 75.7% | Ollama |
| Job title synonyms | high | 93.5% | 87.1% | Ollama |
| Weather vs Programming | low | 43.4% | 22.7% | OpenAI |
| ML/DL related | high | 73.8% | 79.9% | OpenAI |
| Different countries | medium | 61.7% | 57.9% | Tie |
| Finance vs Personal | low | 28.5% | 19.9% | OpenAI |

**Summary:**

| Metric | Ollama mxbai-embed-large | OpenAI text-embedding-3-small |
|--------|--------------------------|-------------------------------|
| Dimensions | 1024 | 1536 |
| Avg response time | ~21ms | ~610ms |
| Quality wins | 3 | 2 |
| Cost | **Free** | ~$0.02/1M tokens |

**Verdict:** Ollama mxbai-embed-large wins on quality (3-2), is **29x faster**, and is **completely free**. This makes the hybrid configuration (OpenAI LLM + Ollama embeddings) the clear choice.

## Full Ollama Configuration (Experimental)

If you want to run **both** LLM and embeddings on Ollama (completely free, no cloud costs):

```env
# LLM Configuration (Ollama)
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openai
MADEINOZ_KNOWLEDGE_MODEL_NAME=mistral:instruct
MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL=http://your-ollama-server:11434/v1

# Embedder Configuration (Ollama)
MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER=openai
MADEINOZ_KNOWLEDGE_EMBEDDER_BASE_URL=http://your-ollama-server:11434/v1
MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL=mxbai-embed-large
MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS=1024
```

**Warning**: Full Ollama mode may have reliability issues with entity extraction due to JSON output formatting. Monitor logs for validation errors.

### Best Models for Full Ollama Mode

Based on our testing, if you must use Ollama for LLM, try these in order:

1. **mistral:instruct** - Fast (3.2s), good JSON compliance
2. **Deepseek-r1:8b** - Fast (3.1s), extracts more relationships
3. **phi4:latest** - Good balance of speed and quality
4. **qwen3-coder:latest** - Thorough extraction, slower

## Running the Model Test

To test models on your Ollama server:

```bash
cd src/server
bun test-ollama-models.ts
```

Results are saved to `test-results.json`.

## Troubleshooting

### "Using Embedder provider: openai" in logs

This is expected. The provider label indicates the API format (OpenAI-compatible), not the actual service. Check the HTTP request logs to verify the actual endpoint:

```
POST http://your-server:11434/v1/embeddings "HTTP/1.1 200 OK"  # Ollama
POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"   # OpenAI
```

### ValidationError on entity extraction

Local models may produce JSON that doesn't match Graphiti's exact Pydantic schema requirements. Solutions:

1. Switch to OpenAI for LLM (recommended)
2. Try a different local model
3. Use hybrid mode (OpenAI LLM + Ollama embeddings)

### Model not found

Ensure the model is pulled on your Ollama server:

```bash
ollama pull mistral:instruct
ollama pull mxbai-embed-large
```

### Connection refused

Check that Ollama is running and accessible:

```bash
curl http://your-ollama-server:11434/api/tags
```

## OpenAI-Compatible Cloud Providers

In addition to Ollama (local), the Madeinoz patch supports OpenAI-compatible cloud providers:

### Supported Providers

| Provider | Base URL | Best For |
|----------|----------|----------|
| **OpenRouter** | `https://openrouter.ai/api/v1` | Access to 200+ models (Claude, GPT-4, Llama) |
| **Together AI** | `https://api.together.xyz/v1` | Fast Llama inference |
| **Fireworks AI** | `https://api.fireworks.ai/inference/v1` | Low latency |
| **DeepInfra** | `https://api.deepinfra.com/v1/openai` | Serverless GPUs |

### Configuration Example (OpenRouter)

```env
# LLM: OpenRouter
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openai
MADEINOZ_KNOWLEDGE_MODEL_NAME=anthropic/claude-3.5-sonnet
MADEINOZ_KNOWLEDGE_OPENAI_API_KEY=sk-or-v1-your-openrouter-key
MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL=https://openrouter.ai/api/v1

# Embedder: Ollama (free, local)
MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER=openai
MADEINOZ_KNOWLEDGE_EMBEDDER_BASE_URL=http://your-ollama-server:11434/v1
MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL=mxbai-embed-large
MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS=1024
```

This configuration:

- Uses OpenRouter for LLM (access to Claude, GPT-4, etc.)
- Uses Ollama for embeddings (free, runs locally)
- Gives you flexibility to choose any model on OpenRouter

### Running the Interactive Installer

The easiest way to configure OpenAI-compatible providers is through the interactive installer:

```bash
cd src/server
bun run install.ts
```

The installer will:

1. Ask you to select "OpenAI-compatible (OpenRouter, Together, etc.)"
2. Let you choose a specific provider
3. Prompt for the API key
4. Offer Ollama or OpenAI for embeddings
5. Let you select models from the provider's catalog

## References

- [Graphiti GitHub Issue #1116](https://github.com/getzep/graphiti/issues/1116) - Ollama compatibility
- [Ollama API Documentation](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [OpenAI-compatible endpoints](https://github.com/ollama/ollama/blob/main/docs/openai.md)
- [OpenRouter Documentation](https://openrouter.ai/docs)
- [Together AI Documentation](https://docs.together.ai/)
- [Fireworks AI Documentation](https://docs.fireworks.ai/)
- [DeepInfra Documentation](https://deepinfra.com/docs)
