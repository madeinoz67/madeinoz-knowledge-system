# Phase 1: Data Model

**Feature**: Remote MCP Access for Knowledge CLI
**Date**: 2026-01-30

## Overview

This feature introduces three new entities for managing remote MCP connections and TLS configuration. All entities are configuration-focused with no persistent storage requirements (except YAML files).

---

## Entity: ConnectionProfile

**Description**: A named configuration for connecting to a remote knowledge MCP server.

### Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | - | Unique profile identifier (e.g., "default", "production") |
| `host` | string | Yes | - | Hostname or IP address of MCP server |
| `port` | number | Yes | 8001 | TCP port for MCP endpoint |
| `protocol` | enum | Yes | http | Connection protocol: `http` or `https` |
| `basePath` | string | No | /mcp | URL path prefix for MCP endpoint |
| `timeout` | number | No | 30000 | Request timeout in milliseconds |
| `tls` | TLSConfig | No | - | TLS configuration (required if protocol=https) |

### Validation Rules

- `name`: Must be unique across profiles, alphanumeric with hyphens/underscores
- `host`: Valid hostname or IPv4/IPv6 address
- `port`: 1-65535, non-zero
- `protocol`: Must be `http` or `https`
- `timeout`: Greater than 0, recommended minimum 5000ms
- `tls`: Required when `protocol=https`

### State Transitions

Not applicable - profiles are static configuration.

---

## Entity: TLSConfig

**Description**: TLS/SSL certificate and verification settings for HTTPS connections.

### Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `verify` | boolean | No | true | Enable certificate verification |
| `ca` | string | No | - | Path to CA certificate file (PEM format) |
| `cert` | string | No | - | Path to client certificate file (PEM format) |
| `key` | string | No | - | Path to client private key file (PEM format) |
| `minVersion` | string | No | TLSv1.2 | Minimum TLS protocol version |

### Validation Rules

- `verify`: When `false`, display security warning
- `ca`: Required for custom CA certificates
- `cert`: Requires `key` to also be provided (mutual TLS)
- `key`: Requires `cert` to also be provided (mutual TLS)
- `minVersion`: One of `TLSv1.2`, `TLSv1.3`

### Security Notes

- Setting `verify=false` exposes connections to MITM attacks
- Self-signed certificates should be trusted via `ca` path, not by disabling verification
- Mutual TLS (`cert` + `key`) is optional for client authentication

---

## Entity: ConnectionState

**Description**: Runtime status of the client's connection to a remote MCP server.

### Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `profile` | string | Yes | default | Name of active connection profile |
| `status` | enum | Yes | unknown | Connection status |
| `lastConnected` | timestamp | No | - | Last successful connection time |
| `lastError` | string | No | - | Last error message (if status=error) |
| `serverVersion` | string | No | - | MCP server version from health check |

### Status Values

| Status | Description | User Action |
|--------|-------------|-------------|
| `connected` | Successfully connected and verified | None required |
| `disconnected` | Not connected (initial state or closed) | Issue connection command |
| `error` | Connection failed or lost | Check error message and config |
| `unknown` | Status not yet checked | Run health check |

### State Transitions

```
initial → unknown → connected → disconnected
                     ↓          ↓
                   error ←─────┘
```

**Transitions**:
- `unknown` → `connected`: Health check succeeds
- `unknown` → `error`: Health check fails with error
- `connected` → `disconnected`: Explicit disconnect or timeout
- `connected` → `error`: Network failure or server error
- `disconnected` → `connected`: Reconnection succeeds
- `error` → `connected`: Retry succeeds

---

## Relationships

```
ConnectionProfile 1:1 TLSConfig
     │
     │ uses
     ↓
ConnectionState (runtime instance)
```

**Relationship Rules**:
- A `ConnectionProfile` may have zero or one `TLSConfig` (required for HTTPS)
- A `ConnectionState` references exactly one `ConnectionProfile` by name
- `ConnectionState` is ephemeral (runtime only), not persisted

---

## Configuration File Structure

**Location**: `$PAI_DIR/config/knowledge-profiles.yaml` or `~/.claude/config/knowledge-profiles.yaml`

```yaml
version: "1.0"
default_profile: default

profiles:
  default:
    host: localhost
    port: 8001
    protocol: http
    basePath: /mcp
    timeout: 30000

  production:
    host: knowledge.example.com
    port: 443
    protocol: https
    basePath: /mcp
    timeout: 10000
    tls:
      verify: true
      ca: /etc/ssl/certs/ca.pem
      minVersion: TLSv1.3

  development:
    host: 192.168.1.100
    port: 8000
    protocol: https
    basePath: /mcp
    tls:
      verify: false  # Self-signed certificate
```

---

## Environment Variable Mappings

| Environment Variable | Profile Field | Priority |
|---------------------|---------------|----------|
| `MADEINOZ_KNOWLEDGE_PROFILE` | `default_profile` | Highest (selects profile) |
| `MADEINOZ_KNOWLEDGE_HOST` | `host` | Overrides profile |
| `MADEINOZ_KNOWLEDGE_PORT` | `port` | Overrides profile |
| `MADEINOZ_KNOWLEDGE_PROTOCOL` | `protocol` | Overrides profile |
| `MADEINOZ_KNOWLEDGE_TLS_VERIFY` | `tls.verify` | Overrides profile |
| `MADEINOZ_KNOWLEDGE_TLS_CA` | `tls.ca` | Overrides profile |

**Priority Order** (highest to lowest):
1. Individual environment variables
2. Selected profile from `MADEINOZ_KNOWLEDGE_PROFILE`
3. Default profile in YAML file
4. Code defaults (localhost:8001, http)

---

## TypeScript Interface Definitions

```typescript
/**
 * TLS/SSL configuration for HTTPS connections
 */
interface TLSConfig {
  /** Enable certificate verification (default: true) */
  verify?: boolean;
  /** Path to CA certificate file (PEM format) */
  ca?: string;
  /** Path to client certificate file (PEM format) */
  cert?: string;
  /** Path to client private key file (PEM format) */
  key?: string;
  /** Minimum TLS protocol version (default: TLSv1.2) */
  minVersion?: 'TLSv1.2' | 'TLSv1.3';
}

/**
 * Connection profile for a knowledge MCP server
 */
interface ConnectionProfile {
  /** Unique profile identifier */
  name: string;
  /** Hostname or IP address */
  host: string;
  /** TCP port */
  port: number;
  /** Protocol: http or https */
  protocol: 'http' | 'https';
  /** URL path prefix (default: /mcp) */
  basePath?: string;
  /** Request timeout in milliseconds (default: 30000) */
  timeout?: number;
  /** TLS configuration (required for https) */
  tls?: TLSConfig;
}

/**
 * Runtime connection state
 */
interface ConnectionState {
  /** Active profile name */
  profile: string;
  /** Connection status */
  status: 'connected' | 'disconnected' | 'error' | 'unknown';
  /** Last successful connection time */
  lastConnected?: Date;
  /** Last error message */
  lastError?: string;
  /** MCP server version */
  serverVersion?: string;
}

/**
 * Profile configuration file structure
 */
interface ProfileConfig {
  /** Config version */
  version: string;
  /** Default profile name */
  default_profile: string;
  /** Profile definitions */
  profiles: Record<string, Omit<ConnectionProfile, 'name'>>;
}
```
