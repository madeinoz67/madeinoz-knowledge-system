# Quick Start: Remote Knowledge Graph Deployment

<!-- AI-FRIENDLY SUMMARY
System: Knowledge Graph Remote Deployment
Purpose: Deploy standalone Neo4j + Graphiti MCP on remote server

Key Components:
- Neo4j (graph database, ports 7474/7687)
- Graphiti MCP (knowledge API, port 8000)

Required Environment Variables:
- NEO4J_PASSWORD: Neo4j authentication password
- OPENAI_API_KEY: LLM API key for entity extraction
- MODEL_NAME: LLM model (default: gpt-4o-mini)

Commands:
- Deploy: docker compose -f docker-compose-production.yml up -d
- Status: docker compose -f docker-compose-production.yml ps
- Logs: docker compose -f docker-compose-production.yml logs -f
- Stop: docker compose -f docker-compose-production.yml down

Connection URL: http://<server-ip>:8000/mcp
Neo4j Browser: http://<server-ip>:7474
-->

## Overview

This guide covers deploying the Knowledge Graph on a remote server **without PAI infrastructure**. The production Docker Compose uses native service naming and standard environment variables.

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Docker | 20.10+ | Or Podman 4.0+ |
| Docker Compose | 2.0+ | V2 syntax |
| RAM | 2GB+ | Neo4j needs 1.5GB minimum |
| Disk | 10GB+ | For Neo4j data persistence |

## Quick Deploy

### 1. Create Environment File

```bash
# Create .env file with your configuration
cat > .env << 'EOF'
# Required: Neo4j password (change this!)
NEO4J_PASSWORD=your-secure-password-here

# Required: LLM API key for entity extraction
OPENAI_API_KEY=sk-your-openai-key-or-openrouter-key

# Optional: LLM configuration
MODEL_NAME=gpt-4o-mini
LLM_PROVIDER=openai
OPENAI_BASE_URL=https://api.openai.com/v1

# Optional: Embedder configuration (if using local Ollama)
# EMBEDDER_PROVIDER=ollama
# EMBEDDER_MODEL=mxbai-embed-large
# EMBEDDER_PROVIDER_URL=http://host.docker.internal:11434
EOF
```

### 2. Download Compose File

```bash
# Download production compose (or copy from pack)
curl -O https://raw.githubusercontent.com/[repo]/main/docker-compose-production.yml
```

### 3. Start Services

```bash
# Start in background
docker compose -f docker-compose-production.yml up -d

# Wait for health checks (~60 seconds)
docker compose -f docker-compose-production.yml ps

# Expected output:
# NAME            STATUS              PORTS
# neo4j           Up (healthy)        7474->7474, 7687->7687
# knowledge-mcp   Up (healthy)        8000->8000
```

### 4. Verify Deployment

```bash
# Check MCP health endpoint
curl http://localhost:8000/health

# Access Neo4j Browser (optional)
open http://localhost:7474
# Login: neo4j / <your NEO4J_PASSWORD>
```

## Connect from PAI Client

Configure your PAI system to use the remote knowledge graph:

```bash
# In your PAI .env file
MADEINOZ_KNOWLEDGE_MCP_URL=http://<server-ip>:8000/mcp
```

Or in MCP config:

```json
{
  "mcpServers": {
    "madeinoz-knowledge": {
      "url": "http://<server-ip>:8000/mcp"
    }
  }
}
```

## Command Reference

| Action | Command |
|--------|---------|
| Start | `docker compose -f docker-compose-production.yml up -d` |
| Stop | `docker compose -f docker-compose-production.yml down` |
| Restart | `docker compose -f docker-compose-production.yml restart` |
| View logs | `docker compose -f docker-compose-production.yml logs -f` |
| Check status | `docker compose -f docker-compose-production.yml ps` |
| Update images | `docker compose -f docker-compose-production.yml pull && docker compose -f docker-compose-production.yml up -d` |

## Port Reference

| Port | Service | Protocol | Description |
|------|---------|----------|-------------|
| 7474 | Neo4j | HTTP | Browser UI |
| 7687 | Neo4j | Bolt | Database queries |
| 8000 | MCP | HTTP | Knowledge API |

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `NEO4J_PASSWORD` | Neo4j authentication password | `your-secure-password` |
| `OPENAI_API_KEY` | LLM API key | `sk-...` |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `MODEL_NAME` | `gpt-4o-mini` | LLM model for entity extraction |
| `LLM_PROVIDER` | `openai` | LLM provider |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | API base URL |
| `EMBEDDER_PROVIDER` | `ollama` | Embedder provider |
| `EMBEDDER_MODEL` | `mxbai-embed-large` | Embedder model |
| `EMBEDDER_PROVIDER_URL` | `http://host.docker.internal:11434` | Ollama URL |

## Troubleshooting

### MCP Server Not Starting

```bash
# Check logs
docker compose -f docker-compose-production.yml logs knowledge-mcp

# Common causes:
# - Missing OPENAI_API_KEY
# - Neo4j not ready (wait longer)
# - Invalid MODEL_NAME
```

### Neo4j Health Check Failing

```bash
# Check Neo4j logs
docker compose -f docker-compose-production.yml logs neo4j

# Common causes:
# - Insufficient memory (need 1.5GB+)
# - Port 7474/7687 already in use
# - Disk full
```

### Connection Refused from PAI

```bash
# Verify MCP is accessible from external
curl http://<server-ip>:8000/health

# Common causes:
# - Firewall blocking port 8000
# - Server not listening on 0.0.0.0
# - Wrong IP address
```

## Security Notes

> **User Responsibility**: Security hardening beyond default authentication is your responsibility.

**Included**:
- Neo4j password authentication (change the default!)
- Containers run as non-root where supported
- Automatic restart on failure

**Not Included (Add if Needed)**:
- TLS/SSL encryption
- Firewall configuration
- Network isolation
- Backup automation

For production environments, consider:
1. Using strong, unique passwords
2. Adding TLS termination (nginx, traefik)
3. Restricting port access via firewall
4. Setting up automated backups

## Data Persistence

Data is stored in Docker volumes:
- `neo4j-data`: Graph database
- `neo4j-logs`: Database logs

**Backup**:
```bash
# Stop services first
docker compose -f docker-compose-production.yml down

# Backup volumes
docker run --rm -v neo4j-data:/data -v $(pwd):/backup alpine \
  tar czf /backup/neo4j-data-backup.tar.gz -C /data .

# Restart
docker compose -f docker-compose-production.yml up -d
```

**Restore**:
```bash
docker compose -f docker-compose-production.yml down
docker run --rm -v neo4j-data:/data -v $(pwd):/backup alpine \
  sh -c "rm -rf /data/* && tar xzf /backup/neo4j-data-backup.tar.gz -C /data"
docker compose -f docker-compose-production.yml up -d
```
