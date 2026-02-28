---
title: "RAG Troubleshooting"
description: "Common issues and solutions for Document Memory"
---

<!-- AI-FRIENDLY SUMMARY
System: Document Memory (RAG) Troubleshooting
Purpose: Solve common Qdrant, Ollama, and ingestion issues

Common Issues:
1. Qdrant connection failed - Check container, ports, URL
2. Documents not ingesting - Check inbox, permissions, logs
3. Search returns no results - Check ingestion, health, threshold
4. Ollama embeddings failing - Check container, model, URL
5. Slow search performance - Check index, cache, resources

Diagnostic Commands:
- docker ps | grep qdrant
- docker logs qdrant
- bun run rag-cli.ts health
- curl http://localhost:11434/api/tags
-->

# RAG Troubleshooting

Common issues and solutions for Document Memory (RAG).

## Quick Diagnostics

```bash
# Check all services
bun run src/skills/server/lib/rag-cli.ts health

# Check Qdrant container
docker ps | grep qdrant

# Check Ollama container
docker ps | grep ollama

# Check Qdrant logs
docker logs qdrant

# Check Ollama logs
docker logs ollama
```

## Qdrant Issues

### Qdrant connection failed

**Symptoms:**
- `rag.health()` returns connection error
- Search commands timeout
- `Connection refused` errors

**Solutions:**

```bash
# Check Qdrant is running
docker ps | grep qdrant

# Start if not running
docker compose -f docker/docker-compose-qdrant.yml up -d

# Check logs for errors
docker logs qdrant

# Restart if needed
docker compose -f docker/docker-compose-qdrant.yml restart

# Verify URL configuration
echo $MADEINOZ_KNOWLEDGE_QDRANT_URL
# Should be: http://localhost:6333
```

### Port already in use

**Symptoms:**
- Qdrant container fails to start
- `port 6333 already in use` error

**Solutions:**

```bash
# Find process using port
lsof -i :6333

# Kill the process
kill -9 <PID>

# Or change port in docker-compose
# ports:
#   - "6334:6333"  # Use 6334 externally
```

### Collection not found

**Symptoms:**
- `Collection 'lkap_documents' not found`
- Empty search results

**Solutions:**

```bash
# Check collection exists
curl http://localhost:6333/collections/lkap_documents

# Collection is auto-created on first ingestion
# Run ingestion first
bun run src/skills/server/lib/rag-cli.ts ingest knowledge/inbox/
```

## Ingestion Issues

### Documents not ingesting

**Symptoms:**
- Documents stay in `knowledge/inbox/`
- No chunks created
- Ingestion returns errors

**Solutions:**

```bash
# Check inbox directory exists
ls -la knowledge/inbox/

# Check file permissions
chmod 644 knowledge/inbox/*

# Check file format is supported
# Supported: .pdf, .md, .mdx, .txt

# Check MCP server logs
docker logs madeinoz-knowledge-mcp

# Try manual ingestion
bun run src/skills/server/lib/rag-cli.ts ingest knowledge/inbox/specific-file.pdf
```

### Docling parser errors

**Symptoms:**
- PDF parsing fails
- Empty or garbled text extraction

**Solutions:**

```bash
# Check Docling is installed (in container)
docker exec madeinoz-knowledge-mcp pip show docling

# Check PDF is not password-protected
# Docling cannot parse encrypted PDFs

# Try converting PDF to text first
pdftotext document.pdf document.txt
cp document.txt knowledge/inbox/
```

### Duplicate document detection

**Symptoms:**
- Document not ingested
- "Document already exists" message

**Solutions:**

```bash
# Documents are tracked by content hash
# If content changed, it will be re-ingested

# To force re-ingest, delete from processed
rm knowledge/processed/document.pdf

# Re-run ingestion
bun run src/skills/server/lib/rag-cli.ts ingest knowledge/inbox/document.pdf
```

## Search Issues

### Search returns no results

**Symptoms:**
- Search returns empty array
- `rag.search()` finds nothing

**Solutions:**

```bash
# Verify documents are ingested
bun run src/skills/server/lib/rag-cli.ts list

# Check health
bun run src/skills/server/lib/rag-cli.ts health

# Lower confidence threshold
MADEINOZ_KNOWLEDGE_QDRANT_CONFIDENCE_THRESHOLD=0.60

# Try broader search terms
bun run src/skills/server/lib/rag-cli.ts search "GPIO"  # Instead of "GPIO configuration"
```

### Low confidence results

**Symptoms:**
- Results have confidence < 0.70
- Irrelevant chunks returned

**Solutions:**

```bash
# Increase confidence threshold
MADEINOZ_KNOWLEDGE_QDRANT_CONFIDENCE_THRESHOLD=0.80

# Use more specific queries
bun run src/skills/server/lib/rag-cli.ts search "STM32F4 GPIO mode configuration register"

# Add filters if available
bun run src/skills/server/lib/rag-cli.ts search "GPIO" --domain=embedded
```

### Search is slow

**Symptoms:**
- Search takes > 2 seconds
- Timeouts occur

**Solutions:**

```bash
# Check Qdrant resources
docker stats qdrant

# Reduce top_k
bun run src/skills/server/lib/rag-cli.ts search "query" --top-k=5

# Check collection size
curl http://localhost:6333/collections/lkap_documents

# Consider increasing container resources
# in docker-compose-qdrant.yml:
# deploy:
#   resources:
#     limits:
#       memory: 2G
```

## Ollama Issues

### Ollama not running

**Symptoms:**
- Embedding generation fails
- `Connection refused` to localhost:11434

**Solutions:**

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama container
docker compose -f docker/docker-compose-ollama.yml up -d

# Check logs
docker logs ollama
```

### Model not found

**Symptoms:**
- `model 'bge-large-en-v1.5' not found`
- Embedding requests fail

**Solutions:**

```bash
# Pull the embedding model
ollama pull bge-large-en-v1.5

# Or inside container
docker exec ollama ollama pull bge-large-en-v1.5

# Verify model exists
curl http://localhost:11434/api/tags | jq '.models[].name'
```

### Embedding rate limiting

**Symptoms:**
- Slow ingestion
- Rate limit errors

**Solutions:**

```bash
# Increase rate limit
MADEINOZ_KNOWLEDGE_EMBEDDING_RATE_LIMIT=120

# Or disable rate limiting (not recommended)
MADEINOZ_KNOWLEDGE_EMBEDDING_RATE_LIMIT=0
```

## Performance Tuning

### Memory optimization

```yaml
# docker-compose-qdrant.yml
services:
  qdrant:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 512M
```

### Search optimization

```bash
# Reduce default top_k
MADEINOZ_KNOWLEDGE_QDRANT_DEFAULT_TOP_K=5

# Increase confidence threshold
MADEINOZ_KNOWLEDGE_QDRANT_CONFIDENCE_THRESHOLD=0.80
```

### Chunking optimization

```bash
# Larger chunks for better context
MADEINOZ_KNOWLEDGE_QDRANT_CHUNK_SIZE_MIN=768
MADEINOZ_KNOWLEDGE_QDRANT_CHUNK_SIZE_MAX=1024
MADEINOZ_KNOWLEDGE_QDRANT_CHUNK_OVERLAP=150
```

## Getting Help

1. Check logs: `docker logs qdrant` and `docker logs ollama`
2. Run health check: `bun run rag-cli.ts health`
3. Check configuration: Review `.env` settings
4. Consult [RAG Configuration](configuration.md) for correct settings
5. File an issue on GitHub with:
   - Error messages
   - Container logs
   - Configuration (without secrets)
