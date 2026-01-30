# Phase 0: Research & Technical Decisions

**Feature**: Remote MCP Access for Knowledge CLI
**Date**: 2026-01-30

## Research Questions

1. **MCP Remote Connection Patterns**: How does the MCP protocol handle remote connections over HTTP/HTTPS?
2. **TLS Implementation in Bun/Node.js**: What is the standard pattern for HTTPS clients with certificate verification options?
3. **Docker External Access**: What are the security considerations for binding MCP server to 0.0.0.0?
4. **Configuration File Best Practices**: How should connection profiles be structured and validated?

---

## Decision 1: MCP Remote Connection Approach

**Decision**: Use standard HTTP/HTTPS transport with configurable baseURL

**Rationale**:
- The MCP protocol uses standard HTTP for transport (SSE for streaming)
- The existing `MCPClientConfig` already supports `baseURL` parameter
- The current `DEFAULT_BASE_URL` is `http://localhost:8001/mcp`
- No protocol changes needed - only configuration

**Alternatives Considered**:
- **WebSocket transport**: Not needed; MCP already defines SSE for server-sent events
- **Custom protocol**: Unnecessary complexity; HTTP is sufficient
- **SSH tunneling**: Could work but adds user friction; better to support direct TLS

**Implementation Notes**:
- Extend `MCPClientConfig` interface to include protocol, host, port separately
- Support both `http://` and `https://` prefixes in baseURL construction
- Default to `http://localhost:8001/mcp` for backward compatibility

---

## Decision 2: TLS/SSL Implementation

**Decision**: Use Bun/Node.js native `https` module with custom agent for certificate control

**Rationale**:
- Bun's `fetch` API supports HTTPS natively
- For certificate verification control, use `https.Agent` with custom options
- Allow `rejectUnauthorized: false` for self-signed certificates (opt-in via env var)
- No additional dependencies needed

**Alternatives Considered**:
- **node-fetch**: Unnecessary; Bun has native fetch
- **axios**: Adds dependency; fetch is sufficient
- **Custom TLS wrapper**: Over-engineering; native APIs work

**Implementation Notes**:
```typescript
// New TLS configuration interface
interface TLSConfig {
  rejectUnauthorized?: boolean;  // Default: true
  cert?: string;                 // Client certificate path
  key?: string;                  // Client key path
  ca?: string;                   // CA certificate path
}

// Extended MCP client config
interface MCPClientConfigExtended extends MCPClientConfig {
  protocol?: 'http' | 'https';
  host?: string;
  port?: number;
  tls?: TLSConfig;
}
```

**Environment Variables**:
- `MADEINOZ_KNOWLEDGE_PROTOCOL`: `http` (default) or `https`
- `MADEINOZ_KNOWLEDGE_HOST`: hostname or IP address (default: `localhost`)
- `MADEINOZ_KNOWLEDGE_PORT`: port number (default: `8001`)
- `MADEINOZ_KNOWLEDGE_TLS_VERIFY`: `true` (default) or `false`
- `MADEINOZ_KNOWLEDGE_TLS_CA`: Path to CA certificate file
- `MADEINOZ_KNOWLEDGE_TLS_CERT`: Path to client certificate
- `MADEINOZ_KNOWLEDGE_TLS_KEY`: Path to client private key

---

## Decision 3: Docker Network Configuration

**Decision**: Bind MCP server to `0.0.0.0` via environment variable, keep container network isolated

**Rationale**:
- Current docker-compose binds `8000:8000` to host; service already accessible externally
- MCP server (Python/uvicorn) needs to listen on `0.0.0.0` instead of default `127.0.0.1`
- Container remains on isolated bridge network (`madeinoz-knowledge-net`)
- Security managed via firewall rules and TLS encryption

**Alternatives Considered**:
- **Host networking**: Breaks isolation; not recommended
- **Reverse proxy**: Adds complexity; can be added later by users
- **VPN only**: Too restrictive; should be user's choice

**Implementation Notes**:
- Add `MCP_HOST` environment variable to Python server (default: `127.0.0.1`)
- Map `MADEINOZ_KNOWLEDGE_MCP_HOST` → `MCP_HOST` in entrypoint.sh
- Update docker-compose to pass `MCP_HOST=0.0.0.0` for external access
- TLS/SSL termination can be handled by:
  - **Option A**: uvicorn with configured certificates (simpler)
  - **Option B**: Reverse proxy (nginx/traefik) in front of container (more flexible)

**Security Considerations**:
- TLS/SSL encryption required for production deployments
- Rate limiting recommended (can be added via reverse proxy)
- Network policies/firewall should restrict access by IP/CIDR when possible
- Consider authentication middleware for multi-user scenarios (future enhancement)

---

## Decision 4: Connection Profile Management

**Decision**: YAML-based configuration file with profile switching via environment variable

**Rationale**:
- YAML is human-readable and already used in this project (docker-compose)
- Easy to validate and parse with `js-yaml` library
- Profiles can be version-controlled or kept local (user's choice)
- Single environment variable (`MADEINOZ_KNOWLEDGE_PROFILE`) for switching

**Alternatives Considered**:
- **JSON**: Less readable for humans; harder to comment
- **TOML**: Not as widely used in Node.js ecosystem
- **Database**: Overkill for small number of profiles
- **CLI arguments**: Cumbersome for frequent switching

**Profile Structure**:
```yaml
# config/knowledge-profiles.yaml
version: "1.0"
default_profile: default

profiles:
  default:
    host: localhost
    port: 8001
    protocol: http
    tls:
      verify: true

  production:
    host: knowledge.example.com
    port: 443
    protocol: https
    tls:
      verify: true
      ca: /path/to/ca.pem

  development:
    host: 192.168.1.100
    port: 8000
    protocol: https
    tls:
      verify: false  # Self-signed cert
```

**Implementation Notes**:
- Profile file location: `$PAI_DIR/config/knowledge-profiles.yaml` or fallback to `~/.claude/config/knowledge-profiles.yaml`
- `MADEINOZ_KNOWLEDGE_PROFILE` environment variable overrides default
- Individual environment variables (`MADEINOZ_KNOWLEDGE_HOST`, etc.) take precedence over profile values
- Validation on load: required fields (host, port, protocol), valid enum values

---

## Decision 5: Server-Side TLS Support

**Decision**: Support TLS via uvicorn's SSL configuration with certificate volume mounts

**Rationale**:
- Uvicorn has built-in SSL support via standard `ssl.SSLContext`
- Certificate files can be mounted as Docker volumes
- Keeps container image immutable (certificates are external)
- Compatible with standard certificate management tools

**Implementation Notes**:
- Add environment variables to Python server:
  - `MCP_TLS_ENABLED`: `true` or `false`
  - `MCP_TLS_CERTPATH`: Path to certificate file
  - `MCP_TLS_KEYPATH`: Path to private key file
- Update docker-compose to mount certificate volumes when TLS enabled
- Add health check for TLS port (default: 443 or configurable)

**Docker Compose Snippet**:
```yaml
services:
  graphiti-mcp:
    environment:
      - MCP_HOST=0.0.0.0
      - MCP_TLS_ENABLED=${MCP_TLS_ENABLED:-false}
      - MCP_TLS_CERTPATH=${MCP_TLS_CERTPATH:-/certs/cert.pem}
      - MCP_TLS_KEYPATH=${MCP_TLS_KEYPATH:-/certs/key.pem}
    volumes:
      - ${MCP_CERTS_DIR:-./certs}:/certs:ro
    ports:
      - "8000:8000"   # HTTP
      - "8443:8443"   # HTTPS (when TLS enabled)
```

---

## Summary of Technical Decisions

| Decision | Choice | Key Benefit |
|----------|--------|-------------|
| Transport | HTTP/HTTPS with configurable baseURL | Uses existing MCP protocol |
| TLS | Native Node.js/Bun HTTPS with custom agent | No new dependencies |
| Docker Binding | 0.0.0.0 via env var, isolated network | Secure, flexible |
| Profiles | YAML file with env var switching | Human-readable, simple |
| Server TLS | Uvicorn SSL with volume mounts | Standard Python pattern |

---

## Open Questions Resolved

1. **Q**: Should we support WebSocket transport for MCP?
   **A**: No, MCP defines SSE for streaming; HTTP/HTTPS is sufficient.

2. **Q**: How do we handle self-signed certificates?
   **A**: `MADEINOZ_KNOWLEDGE_TLS_VERIFY=false` allows opt-out.

3. **Q**: Should the server require TLS by default?
   **A**: No, maintain backward compatibility. TLS opt-in for production.

4. **Q**: Can users override profile values with environment variables?
   **A**: Yes, individual env vars take precedence over profile config.
