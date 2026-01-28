# Remote Production Deployment

<!-- AI-SUMMARY: Production deployment guide for standalone Neo4j + Graphiti MCP server on remote servers. Uses docker-compose-production.yml with native service names. Requires: NEO4J_PASSWORD, OPENAI_API_KEY. Ports: 7474 (Neo4j Browser), 7687 (Bolt), 8000 (MCP). Connect from PAI via mcp-remote or knowledge-client library. -->

Deploy the Knowledge Graph system on remote servers without PAI infrastructure.

## Overview

The production Docker Compose configuration provides:

- **Standalone deployment** - No PAI or local infrastructure required
- **Native naming** - Clean service names (neo4j, knowledge-mcp)
- **Native environment variables** - Standard Neo4j/OpenAI variable names
- **Data persistence** - Docker volumes for database storage
- **Auto-restart** - Services restart automatically on failure

## Quick Start

### 1. Copy Files to Server

```bash
# Copy the production compose file
scp src/skills/server/docker-compose-production.yml user@server:/opt/knowledge-graph/

# SSH to server
ssh user@server
cd /opt/knowledge-graph
```

### 2. Create Environment File

```bash
cat > .env << 'EOF'
# Required
NEO4J_PASSWORD=your-secure-password-here
OPENAI_API_KEY=sk-your-openai-key

# Optional (defaults shown)
MODEL_NAME=gpt-4o-mini
EMBEDDING_MODEL_NAME=text-embedding-3-small
LOG_LEVEL=INFO
EOF

# Secure the file
chmod 600 .env
```

### 3. Start Services

```bash
docker compose -f docker-compose-production.yml up -d
```

### 4. Verify Deployment

```bash
# Check service status
docker compose -f docker-compose-production.yml ps

# Check health endpoints
curl http://localhost:8000/health
curl http://localhost:7474

# View logs
docker compose -f docker-compose-production.yml logs -f
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEO4J_PASSWORD` | Yes | `changeme` | Neo4j database password |
| `OPENAI_API_KEY` | Yes | - | OpenAI API key for LLM operations |
| `MODEL_NAME` | No | `gpt-4o-mini` | LLM model for entity extraction |
| `EMBEDDING_MODEL_NAME` | No | `text-embedding-3-small` | Embedding model |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |

### Alternative LLM Providers

For Anthropic Claude:

```bash
ANTHROPIC_API_KEY=sk-ant-your-key
MODEL_NAME=claude-3-5-haiku-latest
```

For Google Gemini:

```bash
GOOGLE_API_KEY=your-google-key
MODEL_NAME=gemini-2.0-flash
```

### Ports

| Port | Service | Protocol | Description |
|------|---------|----------|-------------|
| 7474 | Neo4j | HTTP | Neo4j Browser interface |
| 7687 | Neo4j | Bolt | Neo4j database protocol |
| 8000 | knowledge-mcp | HTTP | MCP server endpoint |
| 9090 | knowledge-mcp | HTTP | Prometheus metrics |

## Connecting from PAI

Configure your PAI MCP client to connect to the remote server:

```json
{
  "mcpServers": {
    "madeinoz-knowledge": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://your-server:8000/mcp"]
    }
  }
}
```

Or using the knowledge-client library:

```typescript
import { KnowledgeClient } from './lib/knowledge-client';

const client = new KnowledgeClient({
  endpoint: 'http://your-server:8000',
});
```

## Operations

### View Logs

```bash
# All services
docker compose -f docker-compose-production.yml logs -f

# Specific service
docker compose -f docker-compose-production.yml logs -f knowledge-mcp
docker compose -f docker-compose-production.yml logs -f neo4j
```

### Stop Services

```bash
docker compose -f docker-compose-production.yml down
```

### Restart Services

```bash
docker compose -f docker-compose-production.yml restart
```

### Update Services

```bash
docker compose -f docker-compose-production.yml pull
docker compose -f docker-compose-production.yml up -d
```

### Backup Data

```bash
# Stop services first
docker compose -f docker-compose-production.yml down

# Backup Neo4j data volume
docker run --rm -v knowledge-graph_neo4j-data:/data -v $(pwd):/backup alpine \
  tar cvf /backup/neo4j-backup-$(date +%Y%m%d).tar /data

# Restart services
docker compose -f docker-compose-production.yml up -d
```

## Security Considerations

1. **Change default password** - Never use `changeme` in production
2. **Secure .env file** - Set permissions to 600 (owner read/write only)
3. **Firewall rules** - Restrict port access to trusted IPs
4. **TLS/SSL** - Consider adding reverse proxy with TLS for production
5. **API keys** - Rotate API keys regularly

### Adding TLS with Nginx

Example nginx configuration for TLS termination:

```nginx
server {
    listen 443 ssl;
    server_name knowledge.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/knowledge.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/knowledge.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Troubleshooting

### Services won't start

```bash
# Check Docker status
docker info

# Check available resources
free -h
df -h

# Check logs for errors
docker compose -f docker-compose-production.yml logs
```

### Neo4j fails health check

```bash
# Wait for initialization (can take 60+ seconds on first run)
docker logs neo4j

# Check memory settings
docker stats neo4j
```

### MCP server can't connect to Neo4j

```bash
# Verify Neo4j is healthy
docker compose -f docker-compose-production.yml ps

# Check network connectivity
docker exec knowledge-mcp ping neo4j
```

### Out of memory

Reduce Neo4j memory settings in docker-compose-production.yml:

```yaml
environment:
  - NEO4J_server_memory_heap_max__size=512m
  - NEO4J_server_memory_pagecache_size=256m
```
