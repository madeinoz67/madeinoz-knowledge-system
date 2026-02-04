# Remote MCP Access

**Feature**: Remote MCP Access for Knowledge CLI
**Last Updated**: 2026-01-30

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

The Madeinoz Knowledge System supports remote MCP access, enabling you to connect to a centralized knowledge graph from different machines on your network. This capability is useful for:

- **Team knowledge sharing**: Multiple users accessing a shared knowledge graph
- **Remote development**: Accessing your knowledge graph from different machines
- **Production deployments**: Running the knowledge server on dedicated infrastructure

---

## Quick Reference

### Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `MADEINOZ_KNOWLEDGE_PROFILE` | Profile name to use | `default` | `production` |
| `MADEINOZ_KNOWLEDGE_HOST` | Server hostname or IP | `localhost` | `knowledge.example.com` |
| `MADEINOZ_KNOWLEDGE_PORT` | Server port | `8001` | `443` |
| `MADEINOZ_KNOWLEDGE_PROTOCOL` | Connection protocol | `http` | `https` |
| `MADEINOZ_KNOWLEDGE_TLS_VERIFY` | Verify TLS certificates | `true` | `false` |
| `MADEINOZ_KNOWLEDGE_TLS_CA` | CA certificate path | - | `/etc/ssl/certs/ca.pem` |
| `MADEINOZ_KNOWLEDGE_TIMEOUT` | Connection timeout (ms) | `30000` | `60000` |
| `MCP_HOST` | Server bind address | `127.0.0.1` | `0.0.0.0` |
| `MCP_PORT` | Server listening port | `8000` | `8001` |
| `MCP_TLS_ENABLED` | Enable server TLS | `false` | `true` |

**Configuration Priority** (highest to lowest):

1. CLI flags (`--host`, `--port`, etc.)
2. Individual environment variables (`MADEINOZ_KNOWLEDGE_HOST`)
3. Selected profile (`MADEINOZ_KNOWLEDGE_PROFILE`)
4. Default profile in YAML file
5. Code defaults

### CLI Commands

| Command | Description | Example |
|---------|-------------|---------|
| `bun run server start` | Start MCP server | `bun run server start` |
| `bun run server status` | Check server health | `bun run server status` |
| `bun run knowledge-cli --status` | Show connection status | `bun run knowledge-cli --status` |
| `bun run knowledge-cli --list-profiles` | List available profiles | `bun run knowledge-cli --list-profiles` |
| `bun run knowledge-cli --host <host>` | Connect to specific host | `bun run knowledge-cli --host 192.168.1.100 search_nodes "query"` |

### Default Ports

| Port | Service | Protocol |
|------|---------|----------|
| `8001` | MCP HTTP endpoint | HTTP/HTTPS |
| `8000` | MCP Server (internal) | HTTP |
| `7474` | Neo4j Browser | HTTP |
| `7687` | Neo4j Bolt Protocol | Bolt |

---

## Configuration

### Profile Configuration

Connection profiles are stored in `$PAI_DIR/config/knowledge-profiles.yaml` (or `~/.claude/config/knowledge-profiles.yaml`):

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

### TLS Configuration

For production deployments with TLS:

```yaml
profiles:
  production-tls:
    host: knowledge.example.com
    port: 443
    protocol: https
    tls:
      verify: true
      ca: /path/to/ca.pem
      minVersion: TLSv1.2
      maxVersion: TLSv1.3
```

### Timeout Configuration

Connection timeout defaults to 30 seconds (30000ms). Configure via:

```bash
# Environment variable
export MADEINOZ_KNOWLEDGE_TIMEOUT=60000  # 60 seconds

# In profile
profiles:
  slow-network:
    host: remote.example.com
    port: 8001
    timeout: 60000
```

---

## Usage

### Localhost (Default)

The knowledge CLI works out of the box with localhost:

```bash
# Start the MCP server
bun run server start

# Run a knowledge query (uses localhost:8001 by default)
bun run knowledge-cli search_nodes "my query"

# Check connection status
bun run knowledge-cli --status
```

**⚠️ Deprecation Notice**: Localhost-only access is deprecated for production deployments. Use remote access configuration for team environments.

### Remote Connection

**Using environment variables:**

```bash
# Set the remote host
export MADEINOZ_KNOWLEDGE_HOST=192.168.1.100
export MADEINOZ_KNOWLEDGE_PORT=8001

# Run knowledge commands
bun run knowledge-cli search_nodes "my query"
```

**Using CLI flags:**

```bash
# Override connection settings per command
bun run knowledge-cli --host knowledge.example.com --port 8001 search_nodes "my query"

# With HTTPS
bun run knowledge-cli --host knowledge.example.com --protocol https --port 443 search_nodes "my query"
```

**Using profiles:**

```bash
# Use specific profile
export MADEINOZ_KNOWLEDGE_PROFILE=production

# Run commands (uses production profile)
bun run knowledge-cli search_nodes "my query"

# List available profiles
bun run knowledge-cli --list-profiles
```

### Server Configuration

**Enable external access:**

```bash
# Set the MCP host to all interfaces
export MCP_HOST=0.0.0.0

# Restart the server
bun run server restart
```

**Enable TLS on server:**

```bash
# Generate self-signed certificate (development)
openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "/CN=knowledge.example.com"

# Enable TLS in environment
export MCP_TLS_ENABLED=true
export MCP_TLS_CERTPATH=/certs/cert.pem
export MCP_TLS_KEYPATH=/certs/key.pem

# Restart server with TLS
bun run server restart
```

---

## Troubleshooting

### Connection Refused

**Symptom**: `ECONNREFUSED` when connecting

**Solutions**:

1. Check server is running: `bun run server status`
2. Verify `MCP_HOST=0.0.0.0` on server
3. Check firewall allows port `8001` (or custom port)
4. Test with `curl http://<host>:<port>/health`
5. Verify network connectivity: `ping <server-host>`

**Diagnostic commands:**

```bash
# Check if server is listening
netstat -an | grep 8001

# Test HTTP endpoint
curl -v http://<host>:8001/health

# Check firewall status
sudo ufw status  # Linux
sudo pfctl -s rules  # macOS
```

### TLS Certificate Errors

**Symptom**: `certificate verify failed` or `unable to verify`

**Solutions**:

1. **For self-signed certificates** (development only):

   ```bash
   export MADEINOZ_KNOWLEDGE_TLS_VERIFY=false
   ```

2. **For custom CA certificates**:

   ```bash
   export MADEINOZ_KNOWLEDGE_TLS_CA=/path/to/ca.pem
   ```

3. **Check certificate validity**:

   ```bash
   # View certificate details
   openssl x509 -in cert.pem -noout -text

   # Check expiration
   openssl x509 -in cert.pem -noout -dates

   # Verify hostname matches
   openssl x509 -in cert.pem -noout -subject
   ```

4. **Verify certificate chain**:

   ```bash
   openssl s_client -connect knowledge.example.com:443 -showcerts
   ```

### Timeout Errors

**Symptom**: `Connection timed out` after 30 seconds

**Solutions**:

1. **Check network connectivity**:

   ```bash
   ping <server-host>
   traceroute <server-host>
   ```

2. **Increase timeout**:

   ```bash
   export MADEINOZ_KNOWLEDGE_TIMEOUT=60000  # 60 seconds
   ```

3. **Verify server is listening**:

   ```bash
   netstat -an | grep 8001
   lsof -i :8001
   ```

4. **Check for network issues**:

   ```bash
   # Test port connectivity
   nc -zv <host> 8001
   telnet <host> 8001
   ```

### Profile Not Found

**Symptom**: `Profile 'production' not found`

**Solutions**:

1. **Check profile file exists**:

   ```bash
   ls $PAI_DIR/config/knowledge-profiles.yaml
   ls ~/.claude/config/knowledge-profiles.yaml
   ```

2. **List available profiles**:

   ```bash
   bun run knowledge-cli --list-profiles
   ```

3. **Verify YAML syntax**:

   ```bash
   # Validate YAML
   python -c "import yaml; yaml.safe_load(open('$PAI_DIR/config/knowledge-profiles.yaml'))"
   ```

4. **Check profile name in YAML file**:

   ```bash
   grep -A 5 "profiles:" $PAI_DIR/config/knowledge-profiles.yaml
   ```

### Concurrent Connection Issues

**Symptom**: Errors when multiple clients connect simultaneously

**Solutions**:

1. **Check server logs for connection errors**:

   ```bash
   bun run server logs | grep -i connection
   ```

2. **Verify server configuration**:

   ```bash
   # Query server configuration
   curl http://<host>:8001/config

   # Check health endpoint
   curl http://<host>:8001/health
   ```

3. **Test concurrent connections**:

   ```bash
   # Run multiple queries in parallel
   for i in {1..10}; do
     bun run knowledge-cli search_nodes "test $i" &
   done
   wait
   ```

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
| **Avoid localhost-only** | Deprecated for production | Use remote access configuration |

---

## Network Architecture

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

## Advanced Configuration

### Reverse Proxy (nginx)

For production deployments, use a reverse proxy:

```nginx
upstream knowledge_mcp {
    server localhost:8001;
}

server {
    listen 443 ssl http2;
    server_name knowledge.example.com;

    ssl_certificate /etc/ssl/certs/knowledge.crt;
    ssl_certificate_key /etc/ssl/private/knowledge.key;

    location /mcp {
        proxy_pass http://knowledge_mcp;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /health {
        proxy_pass http://knowledge_mcp;
        access_log off;
    }
}
```

### Docker Compose Override

Create `docker-compose.override.yml` for custom configuration:

```yaml
services:
  graphiti-mcp:
    environment:
      - MCP_HOST=0.0.0.0
      - MCP_TLS_ENABLED=true
    ports:
      - "8001:8001"
      - "443:443"
    volumes:
      - ./certs:/certs:ro
```

---

## Related Documentation

- [Installation Guide](installation/index.md) - Complete installation instructions
- [Troubleshooting](troubleshooting/common-issues.md) - Common issues and solutions
- [Configuration Reference](reference/configuration.md) - Full configuration options
