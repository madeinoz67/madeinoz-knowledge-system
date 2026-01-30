# Quickstart Guide: Remote MCP Access

**Feature**: Remote MCP Access for Knowledge CLI
**Date**: 2026-01-30

<!-- AI-FRIENDLY SUMMARY
System: Madeinoz Knowledge System - Remote MCP Access
Purpose: Enable remote connections to knowledge graph MCP server from different machines
Key Components: MCP client (TypeScript), MCP server (Python), Docker/Podman containers, TLS/SSL support

Key Tools/Commands:
- knowledge-cli: Command-line interface for knowledge operations
- bun run server start: Start MCP server containers
- bun run server status: Check server health

Configuration Prefix: MADEINOZ_KNOWLEDGE_
Default Ports: 8001 (MCP HTTP), 8000 (MCP Server), 7474 (Neo4j Browser), 7687 (Neo4j Bolt)

Limits:
- Concurrent connections: 10+ supported
- Connection timeout: 30s default (configurable)
- TLS versions: 1.2, 1.3
-->

## Overview

This guide shows you how to connect to the Madeinoz Knowledge System MCP server from a remote machine. You'll learn how to:

1. Configure the server for external access
2. Set up TLS/SSL for secure connections
3. Create and use connection profiles
4. Troubleshoot common issues

---

## Prerequisites

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| Bun Runtime | 1.0+ | `bun --version` |
| Docker/Podman | Latest | `docker --version` or `podman --version` |
| Network Access | - | `ping <server-host>` |

---

## Quick Start: Localhost (Default)

The knowledge CLI works out of the box with localhost:

```bash
# Start the MCP server
bun run server start

# Run a knowledge query (uses localhost:8001 by default)
bun run knowledge-cli search_nodes "my query"

# Check connection status
bun run knowledge-cli --status
```

**Default Configuration**:
- Host: `localhost`
- Port: `8001`
- Protocol: `http`
- Path: `/mcp`

---

## Step 1: Enable Server External Access

By default, the MCP server binds to `127.0.0.1` (localhost only). To enable external access:

### Option A: Environment Variable (Recommended)

```bash
# Set the MCP host to all interfaces
export MCP_HOST=0.0.0.0

# Restart the server
bun run server restart
```

### Option B: Docker Compose Override

Create `docker-compose.override.yml`:

```yaml
services:
  graphiti-mcp:
    environment:
      - MCP_HOST=0.0.0.0
    ports:
      - "8001:8001"  # Ensure port is exposed
```

Then restart: `bun run server restart`

### Verify External Access

```bash
# From another machine, test the connection
curl http://<server-ip>:8001/health

# Expected response:
# {"status": "healthy", "version": "1.x.x"}
```

---

## Step 2: Connect from Remote Machine

### Using Environment Variables

```bash
# Set the remote host
export MADEINOZ_KNOWLEDGE_HOST=192.168.1.100

# Optionally set port and protocol
export MADEINOZ_KNOWLEDGE_PORT=8001
export MADEINOZ_KNOWLEDGE_PROTOCOL=http

# Run knowledge commands
bun run knowledge-cli search_nodes "my query"
```

### Using CLI Flags

```bash
# Override connection settings per command
bun run knowledge-cli --host knowledge.example.com --port 8001 search_nodes "my query"

# With HTTPS
bun run knowledge-cli --host knowledge.example.com --protocol https --port 443 search_nodes "my query"
```

---

## Step 3: Set Up TLS/SSL (Production)

For production deployments, use TLS/SSL to encrypt connections.

### Generate Self-Signed Certificate (Development)

```bash
# Create certificates directory
mkdir -p certs

# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "/CN=knowledge.example.com"
```

### Configure Server TLS

```bash
# Enable TLS in environment
export MCP_TLS_ENABLED=true
export MCP_TLS_CERTPATH=/certs/cert.pem
export MCP_TLS_KEYPATH=/certs/key.pem

# Restart server with TLS
bun run server restart
```

### Configure Client TLS

**For trusted certificates (default)**:
```bash
export MADEINOZ_KNOWLEDGE_PROTOCOL=https
export MADEINOZ_KNOWLEDGE_HOST=knowledge.example.com
export MADEINOZ_KNOWLEDGE_PORT=443
```

**For self-signed certificates (development only)**:
```bash
export MADEINOZ_KNOWLEDGE_PROTOCOL=https
export MADEINOZ_KNOWLEDGE_HOST=knowledge.example.com
export MADEINOZ_KNOWLEDGE_TLS_VERIFY=false
```

**For custom CA certificates**:
```bash
export MADEINOZ_KNOWLEDGE_TLS_CA=/path/to/ca.pem
```

---

## Step 4: Create Connection Profiles

Profiles let you quickly switch between different knowledge systems.

### Create Profile Configuration

Create `$PAI_DIR/config/knowledge-profiles.yaml`:

```yaml
version: "1.0"
default_profile: default

profiles:
  default:
    host: localhost
    port: 8001
    protocol: http

  production:
    host: knowledge.example.com
    port: 443
    protocol: https
    tls:
      verify: true
      minVersion: TLSv1.3

  development:
    host: 192.168.1.100
    port: 8000
    protocol: https
    tls:
      verify: false  # Self-signed certificate
```

### Switch Between Profiles

```bash
# Use specific profile
export MADEINOZ_KNOWLEDGE_PROFILE=production

# Run commands (uses production profile)
bun run knowledge-cli search_nodes "my query"

# List available profiles
bun run knowledge-cli --list-profiles

# Show current connection status
bun run knowledge-cli --status
```

---

## Environment Variable Reference

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `MADEINOZ_KNOWLEDGE_PROFILE` | Profile name to use | `default` | `production` |
| `MADEINOZ_KNOWLEDGE_HOST` | Server hostname or IP | `localhost` | `knowledge.example.com` |
| `MADEINOZ_KNOWLEDGE_PORT` | Server port | `8001` | `443` |
| `MADEINOZ_KNOWLEDGE_PROTOCOL` | Connection protocol | `http` | `https` |
| `MADEINOZ_KNOWLEDGE_TLS_VERIFY` | Verify TLS certificates | `true` | `false` |
| `MADEINOZ_KNOWLEDGE_TLS_CA` | CA certificate path | - | `/etc/ssl/certs/ca.pem` |
| `MCP_HOST` | Server bind address | `127.0.0.1` | `0.0.0.0` |
| `MCP_PORT` | Server listening port | `8000` | `8001` |
| `MCP_TLS_ENABLED` | Enable server TLS | `false` | `true` |

**Priority Order** (highest to lowest):
1. CLI flags (`--host`, `--port`, etc.)
2. Individual environment variables (`MADEINOZ_KNOWLEDGE_HOST`)
3. Selected profile (`MADEINOZ_KNOWLEDGE_PROFILE`)
4. Default profile in YAML file
5. Code defaults

---

## Troubleshooting

### Connection Refused

**Symptom**: `ECONNREFUSED` when connecting

**Solutions**:
1. Check server is running: `bun run server status`
2. Verify `MCP_HOST=0.0.0.0` on server
3. Check firewall allows port `8001` (or custom port)
4. Test with `curl http://<host>:<port>/health`

### TLS Certificate Errors

**Symptom**: `certificate verify failed` or `unable to verify`

**Solutions**:
1. For self-signed certs: `export MADEINOZ_KNOWLEDGE_TLS_VERIFY=false`
2. For custom CA: `export MADEINOZ_KNOWLEDGE_TLS_CA=/path/to/ca.pem`
3. Check certificate hostname matches server host
4. Verify certificate hasn't expired: `openssl x509 -in cert.pem -noout -dates`

### Timeout Errors

**Symptom**: `Connection timed out` after 30 seconds

**Solutions**:
1. Check network connectivity: `ping <server-host>`
2. Increase timeout: `export MADEINOZ_KNOWLEDGE_TIMEOUT=60000`
3. Verify server is listening: `netstat -an | grep 8001`

### Profile Not Found

**Symptom**: `Profile 'production' not found`

**Solutions**:
1. Check profile file exists: `ls $PAI_DIR/config/knowledge-profiles.yaml`
2. Verify profile name in YAML file
3. List available profiles: `bun run knowledge-cli --list-profiles`

---

## Security Best Practices

| Practice | Why | How |
|----------|-----|-----|
| **Use TLS in production** | Prevents data interception | Set `MADEINOZ_KNOWLEDGE_PROTOCOL=https` |
| **Verify certificates** | Prevents MITM attacks | Keep `MADEINOZ_KNOWLEDGE_TLS_VERIFY=true` |
| **Limit firewall access** | Reduces attack surface | Allow only trusted IP ranges |
| **Use strong certificates** | Protects against compromise | Use 2048-bit+ RSA or ECDSA |
| **Rotate certificates** | Limits exposure from compromise | Rotate annually or quarterly |
| **Monitor logs** | Detects suspicious activity | Check server logs regularly |

---

## Docker Network Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Host Machine                            │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Docker Network: madeinoz-knowledge-net           │  │
│  │                                                           │  │
│  │  ┌─────────────────┐      ┌──────────────────────────┐   │  │
│  │  │   graphiti-mcp  │◄────►│      neo4j              │   │  │
│  │  │   (0.0.0.0:8001) │      │      (172.18.0.2:7687)  │   │  │
│  │  └────────┬────────┘      └──────────────────────────┘   │  │
│  │           │                                               │  │
│  └───────────┼───────────────────────────────────────────────┘  │
│              │                                                    │
│              ▼                                                   │
│         Port 8001 (External)                                     │
│                                                                  │
└───────────┬──────────────────────────────────────────────────────┘
            │
            │ Network
            │
┌───────────▼──────────────────────────────────────────────────────┐
│                     Remote Client Machine                         │
│                                                                  │
│  knowledge-cli ──► https://knowledge.example.com:8001/mcp        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Next Steps

1. **Production Deployment**: Set up reverse proxy (nginx/traefik) for load balancing
2. **Authentication**: Implement API key or OAuth authentication (future feature)
3. **Monitoring**: Set up Prometheus metrics for connection monitoring
4. **Documentation**: See [docs/remote-access.md](../../docs/remote-access.md) for detailed guide
