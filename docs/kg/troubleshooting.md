---
title: "Knowledge Memory Troubleshooting"
description: "Common issues and solutions for Knowledge Memory"
---

<!-- AI-FRIENDLY SUMMARY
System: Knowledge Memory (KG) Troubleshooting
Purpose: Solve common Neo4j, LLM, and entity extraction issues

Common Issues:
1. Neo4j connection failed - Check container, ports, password
2. Entity extraction errors - Check LLM API key, model compatibility
3. Search returns no results - Check ingestion, embeddings
4. LLM API errors - Check API key, rate limits, model availability
5. Memory decay issues - Check decay configuration

Diagnostic Commands:
- bun run server-cli status
- docker logs neo4j
- bun run server-cli logs
-->

# Knowledge Memory Troubleshooting

Common issues and solutions for Knowledge Memory (Knowledge Graph).

## Quick Diagnostics

```bash
# Check server status
bun run server-cli status

# Check Neo4j container
docker ps | grep neo4j

# Check Neo4j logs
docker logs neo4j

# Check MCP server logs
bun run server-cli logs
```

## Neo4j Issues

### Neo4j connection failed

**Symptoms:**
- `add_memory()` returns connection error
- `ServiceUnavailable` errors
- Authentication failures

**Solutions:**

```bash
# Check Neo4j is running
docker ps | grep neo4j

# Start if not running
bun run server-cli start

# Check logs for errors
docker logs neo4j

# Restart if needed
bun run server-cli stop
bun run server-cli start

# Verify password configuration
echo $MADEINOZ_KNOWLEDGE_NEO4J_PASSWORD
```

### Authentication failed

**Symptoms:**
- `AuthError` or `unauthorized`
- Password rejected

**Solutions:**

```bash
# Check password in .env
grep NEO4J_PASSWORD .env

# Reset Neo4j password
bun run server-cli stop
docker volume rm madeinoz-knowledge-system_neo4j_data
bun run server-cli start
# Set new password in .env first!
```

### Port already in use

**Symptoms:**
- Neo4j container fails to start
- `port 7687 already in use`

**Solutions:**

```bash
# Find process using port
lsof -i :7687

# Kill the process
kill -9 <PID>

# Or change port in docker-compose
# ports:
#   - "7688:7687"  # Use 7688 externally
```

## Entity Extraction Issues

### LLM API errors

**Symptoms:**
- Entity extraction fails
- `API error` or `rate limit` messages

**Solutions:**

```bash
# Check API key is set
echo $OPENAI_API_KEY

# Check API key validity
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models

# Check rate limits
# Wait and retry, or reduce SEMAPHORE_LIMIT
MADEINOZ_KNOWLEDGE_SEMAPHORE_LIMIT=5
```

### Model compatibility issues

**Symptoms:**
- Pydantic validation errors
- Entity extraction returns malformed data

**Solutions:**

```bash
# Use compatible model
MADEINOZ_KNOWLEDGE_MODEL_NAME=gpt-4o-mini

# Incompatible models (DO NOT USE):
# - All Llama variants
# - All Mistral variants

# If using OpenRouter
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openrouter
MADEINOZ_KNOWLEDGE_MODEL_NAME=anthropic/claude-3.5-haiku
```

### Poor entity extraction quality

**Symptoms:**
- Entities not extracted correctly
- Missing relationships
- Wrong entity types

**Solutions:**

```bash
# Use better model
MADEINOZ_KNOWLEDGE_MODEL_NAME=gpt-4o  # Instead of gpt-4o-mini

# Provide more context in episodes
# Bad: "Docker is cool"
# Good: "Docker is a container runtime platform that uses a daemon
#        process for managing containers. It's similar to Podman but
#        requires root privileges."

# Be explicit about relationships
# Bad: "Podman and Docker are different"
# Good: "Podman is an alternative to Docker that doesn't require a daemon"
```

## Search Issues

### Search returns no results

**Symptoms:**
- `search_memory_nodes()` returns empty
- No entities found

**Solutions:**

```bash
# Verify knowledge was added
get_episodes(group_id="main", limit=10)

# Check if entities exist
curl -u neo4j:$PASSWORD http://localhost:7474/db/neo4j/tx/commit \
  -H "Content-Type: application/json" \
  -d '{"statements":[{"statement":"MATCH (n) RETURN count(n)"}]}'

# Try broader search terms
search_memory_nodes(query="container")  # Instead of "container runtime orchestration"
```

### Slow search performance

**Symptoms:**
- Search takes > 2 seconds
- Timeouts occur

**Solutions:**

```bash
# Reduce search limit
MADEINOZ_KNOWLEDGE_SEARCH_LIMIT=5

# Check Neo4j resources
docker stats neo4j

# Increase Neo4j memory
# In docker-compose-neo4j.yml:
# NEO4J_server_memory_heap_initial__size=1G
# NEO4J_server_memory_pagecache_size=512M
```

## Memory Decay Issues

### Knowledge disappearing unexpectedly

**Symptoms:**
- Old knowledge no longer found
- Entities deleted without action

**Solutions:**

```bash
# Check decay configuration
echo $MADEINOZ_KNOWLEDGE_DECAY_ENABLED
echo $MADEINOZ_KNOWLEDGE_DECAY_HALF_LIFE

# Disable decay if not wanted
MADEINOZ_KNOWLEDGE_DECAY_ENABLED=false

# Increase half-life (default 180 days)
MADEINOZ_KNOWLEDGE_DECAY_HALF_LIFE=365
```

### Decay maintenance failing

**Symptoms:**
- Errors during maintenance
- Memory not decaying

**Solutions:**

```bash
# Run maintenance manually
run_maintenance()

# Check logs for errors
bun run server-cli logs

# Verify decay is enabled
MADEINOZ_KNOWLEDGE_DECAY_ENABLED=true
```

## FalkorDB Issues

### FalkorDB connection failed

**Symptoms:**
- Connection to Redis fails
- FalkorDB not responding

**Solutions:**

```bash
# Check FalkorDB is running
docker ps | grep falkordb

# Check port
curl http://localhost:3000

# Verify configuration
echo $MADEINOZ_KNOWLEDGE_GRAPH_BACKEND  # Should be "falkordb"
echo $MADEINOZ_KNOWLEDGE_FALKORDB_HOST
echo $MADEINOZ_KNOWLEDGE_FALKORDB_PORT
```

### Lucene query errors

**Symptoms:**
- Search syntax errors
- Special characters causing failures

**Solutions:**

```bash
# Special characters are automatically escaped
# Ensure you're using the latest version

# If issues persist, avoid special characters in queries
# Bad: "search for APT-28"
# Good: "search for APT 28" or "search for APT28"
```

## Performance Tuning

### Memory optimization

```yaml
# docker-compose-neo4j.yml
services:
  neo4j:
    environment:
      - NEO4J_server_memory_heap_initial__size=1G
      - NEO4J_server_memory_heap_max__size=2G
      - NEO4J_server_memory_pagecache_size=512M
```

### Concurrency tuning

```bash
# Reduce concurrent LLM calls (avoid rate limits)
MADEINOZ_KNOWLEDGE_SEMAPHORE_LIMIT=5

# Reduce search results
MADEINOZ_KNOWLEDGE_SEARCH_LIMIT=5
```

## Getting Help

1. Check logs: `docker logs neo4j` and `bun run server-cli logs`
2. Check status: `bun run server-cli status`
3. Check configuration: Review `.env` settings
4. Consult [KG Configuration](configuration.md) for correct settings
5. File an issue on GitHub with:
   - Error messages
   - Container logs
   - Configuration (without secrets)
