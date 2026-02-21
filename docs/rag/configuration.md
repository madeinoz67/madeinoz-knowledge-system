---
title: "RAG Configuration"
description: "Configure Qdrant and Ollama for Document Memory"
---

<!-- AI-FRIENDLY SUMMARY
System: Document Memory (RAG) Configuration
Purpose: Environment variables and settings for Qdrant and Ollama

Configuration Prefix: MADEINOZ_KNOWLEDGE_QDRANT_*

Key Variables:
- QDRANT_URL: API endpoint (default: http://localhost:6333)
- QDRANT_COLLECTION: Collection name (default: lkap_documents)
- QDRANT_API_KEY: Authentication for cloud deployments
- QDRANT_CONFIDENCE_THRESHOLD: Minimum search confidence (default: 0.70)

Chunking Settings:
- CHUNK_SIZE_MIN: 512 tokens
- CHUNK_SIZE_MAX: 768 tokens
- CHUNK_OVERLAP: 100 tokens

Ollama Settings:
- OLLAMA_URL: http://localhost:11434
- OLLAMA_MODEL: bge-large-en-v1.5

Security:
- TLS_VERIFY: true (recommended)
- EMBEDDING_RATE_LIMIT: 60 requests/minute
-->

# RAG Configuration

Configuration options for Document Memory (RAG) using Qdrant and Ollama.

## Required Variables

```bash
# Qdrant API endpoint
MADEINOZ_KNOWLEDGE_QDRANT_URL=http://localhost:6333

# Qdrant collection name
MADEINOZ_KNOWLEDGE_QDRANT_COLLECTION=lkap_documents
```

## Qdrant Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MADEINOZ_KNOWLEDGE_QDRANT_URL` | `http://localhost:6333` | Qdrant API endpoint |
| `MADEINOZ_KNOWLEDGE_QDRANT_COLLECTION` | `lkap_documents` | Collection name for document chunks |
| `MADEINOZ_KNOWLEDGE_QDRANT_API_KEY` | *(none)* | API key for cloud deployments |
| `MADEINOZ_KNOWLEDGE_QDRANT_TLS_VERIFY` | `true` | Verify TLS certificates |

### Search Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MADEINOZ_KNOWLEDGE_QDRANT_CONFIDENCE_THRESHOLD` | `0.70` | Minimum confidence for search results |
| `MADEINOZ_KNOWLEDGE_QDRANT_DEFAULT_TOP_K` | `10` | Default number of results |
| `MADEINOZ_KNOWLEDGE_QDRANT_MAX_TOP_K` | `100` | Maximum results per query |

### Embedding Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MADEINOZ_KNOWLEDGE_QDRANT_EMBEDDING_DIMENSION` | `1024` | Vector dimension (bge-large-en-v1.5) |

## Chunking Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MADEINOZ_KNOWLEDGE_QDRANT_CHUNK_SIZE_MIN` | `512` | Minimum chunk size (tokens) |
| `MADEINOZ_KNOWLEDGE_QDRANT_CHUNK_SIZE_MAX` | `768` | Maximum chunk size (tokens) |
| `MADEINOZ_KNOWLEDGE_QDRANT_CHUNK_OVERLAP` | `100` | Overlap between chunks (tokens) |

## Ollama Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MADEINOZ_KNOWLEDGE_QDRANT_OLLAMA_URL` | `http://localhost:11434` | Ollama API endpoint |
| `MADEINOZ_KNOWLEDGE_QDRANT_OLLAMA_MODEL` | `bge-large-en-v1.5` | Embedding model |

## Security Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MADEINOZ_KNOWLEDGE_QDRANT_TLS_VERIFY` | `true` | Verify TLS certificates |
| `MADEINOZ_KNOWLEDGE_EMBEDDING_RATE_LIMIT` | `60` | Max embedding requests per minute |

### TLS Configuration

For production deployments with TLS:

```bash
# Enable TLS verification (recommended)
MADEINOZ_KNOWLEDGE_QDRANT_TLS_VERIFY=true

# For self-signed certificates (development only)
MADEINOZ_KNOWLEDGE_QDRANT_TLS_VERIFY=false
```

### Rate Limiting

Prevent overwhelming the embedding service:

```bash
# Limit to 60 embedding requests per minute
MADEINOZ_KNOWLEDGE_EMBEDDING_RATE_LIMIT=60
```

## Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `MADEINOZ_KNOWLEDGE_QDRANT_LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |

## Example Configuration

### Development

```bash
# .env.dev
MADEINOZ_KNOWLEDGE_QDRANT_URL=http://localhost:6333
MADEINOZ_KNOWLEDGE_QDRANT_COLLECTION=lkap_documents_dev
MADEINOZ_KNOWLEDGE_QDRANT_CONFIDENCE_THRESHOLD=0.65
MADEINOZ_KNOWLEDGE_QDRANT_TLS_VERIFY=false
MADEINOZ_KNOWLEDGE_QDRANT_LOG_LEVEL=DEBUG
```

### Production

```bash
# .env
MADEINOZ_KNOWLEDGE_QDRANT_URL=https://qdrant.example.com
MADEINOZ_KNOWLEDGE_QDRANT_API_KEY=your-api-key
MADEINOZ_KNOWLEDGE_QDRANT_COLLECTION=lkap_documents
MADEINOZ_KNOWLEDGE_QDRANT_CONFIDENCE_THRESHOLD=0.75
MADEINOZ_KNOWLEDGE_QDRANT_TLS_VERIFY=true
MADEINOZ_KNOWLEDGE_EMBEDDING_RATE_LIMIT=60
MADEINOZ_KNOWLEDGE_QDRANT_LOG_LEVEL=WARNING
```

## Docker Configuration

### Qdrant Container

```yaml
# docker/docker-compose-qdrant.yml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__LOG_LEVEL=INFO

volumes:
  qdrant_data:
```

### Ollama Container

```yaml
# docker/docker-compose-ollama.yml
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  ollama_data:
```

## Related Topics

- **[RAG Quickstart](quickstart.md)** - Get started with RAG
- **[RAG Troubleshooting](troubleshooting.md)** - Solve common issues
- **[Document Memory Concepts](concepts.md)** - Understand RAG architecture
- **[Configuration Reference](../reference/configuration.md)** - Full configuration guide
