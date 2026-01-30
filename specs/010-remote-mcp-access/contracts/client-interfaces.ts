# API Contracts

**Feature**: Remote MCP Access for Knowledge CLI
**Date**: 2026-01-30

## Overview

This document defines the interfaces for the remote MCP access feature. The contracts are organized by layer: configuration, client, and CLI.

---

## Client Layer Contracts

### MCPClientConfig (Extended)

**Location**: `src/skills/lib/mcp-client.ts`

**Extension of existing interface**:

```typescript
/**
 * TLS configuration for HTTPS connections
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
}

/**
 * Extended MCP Client configuration with remote support
 */
interface MCPClientConfigExtended extends MCPClientConfig {
  /** Protocol: http or https */
  protocol?: 'http' | 'https';
  /** Hostname or IP address */
  host?: string;
  /** TCP port */
  port?: number;
  /** TLS configuration */
  tls?: TLSConfig;
  /** Connection profile name (loads from file) */
  profile?: string;
}
```

**Changes**:
- `MCPClientConfig` is extended with new optional fields
- All new fields have sensible defaults for backward compatibility
- `baseURL` is constructed from `protocol`, `host`, `port`, and `basePath`

---

### Connection Profile Manager

**Location**: `src/skills/lib/connection-profile.ts` (NEW FILE)

```typescript
/**
 * Connection profile configuration
 */
interface ConnectionProfileData {
  name: string;
  host: string;
  port: number;
  protocol: 'http' | 'https';
  basePath?: string;
  timeout?: number;
  tls?: {
    verify?: boolean;
    ca?: string;
    cert?: string;
    key?: string;
  };
}

/**
 * Profile configuration file structure
 */
interface ProfileConfigFile {
  version: string;
  default_profile: string;
  profiles: Record<string, Omit<ConnectionProfileData, 'name'>>;
}

/**
 * Connection Profile Manager
 * Loads and validates connection profiles from YAML files
 */
class ConnectionProfileManager {
  /**
   * Load a profile by name
   * @param profileName - Profile name to load (default: "default")
   * @returns Profile configuration or null if not found
   */
  loadProfile(profileName: string): ConnectionProfileData | null;

  /**
   * List all available profile names
   * @returns Array of profile names
   */
  listProfiles(): string[];

  /**
   * Validate profile configuration
   * @param profile - Profile to validate
   * @returns Validation result with errors if invalid
   */
  validateProfile(profile: ConnectionProfileData): { valid: boolean; errors: string[] };
}

/**
 * Load profile with environment variable overrides
 * @param profileName - Profile name to load
 * @returns Profile configuration with env vars applied
 */
function loadProfileWithOverrides(profileName: string): MCPClientConfigExtended;
```

---

## CLI Layer Contracts

### Knowledge CLI Commands

**Location**: `src/skills/tools/knowledge-cli.ts`

**New/Modified Commands**:

```typescript
/**
 * Display connection status
 */
interface StatusCommandResult {
  profile: string;
  host: string;
  port: number;
  protocol: string;
  status: 'connected' | 'disconnected' | 'error' | 'unknown';
  serverVersion?: string;
  lastConnected?: string;
  lastError?: string;
}

/**
 * List available connection profiles
 */
interface ListProfilesResult {
  default: string;
  profiles: string[];
  current: string;
}

/**
 * Test connection to MCP server
 */
interface TestConnectionResult {
  success: boolean;
  host: string;
  port: number;
  protocol: string;
  latency?: number;
  error?: string;
}
```

**New CLI Flags**:

| Flag | Description | Example |
|------|-------------|---------|
| `--profile <name>` | Use specific connection profile | `--profile production` |
| `--host <hostname>` | Override profile host | `--host knowledge.example.com` |
| `--port <port>` | Override profile port | `--port 8443` |
| `--protocol <http\|https>` | Override profile protocol | `--protocol https` |
| `--tls-no-verify` | Disable TLS verification | `--tls-no-verify` |
| `--status` | Show connection status | `--status` |

---

## Server Layer Contracts (Python)

### MCP Server Configuration

**Location**: `docker/patches/graphiti_mcp_server.py`

**New Environment Variables**:

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_HOST` | `127.0.0.1` | Bind address for MCP server (use `0.0.0.0` for external access) |
| `MCP_PORT` | `8000` | TCP port for MCP HTTP endpoint |
| `MCP_TLS_ENABLED` | `false` | Enable TLS/SSL for HTTPS endpoint |
| `MCP_TLS_CERTPATH` | - | Path to TLS certificate file |
| `MCP_TLS_KEYPATH` | - | Path to TLS private key file |

**New Server Endpoints** (extend existing):

```
GET /health - Existing health check
  Response: { status: "healthy", version: "x.x.x", tls: boolean }

GET /config - Server configuration info
  Response: { host: string, port: number, tls: boolean, profiles: string[] }
```

---

## Configuration Layer Contracts

### Environment Variables

**Location**: `src/server/lib/config.ts` (MODIFIED)

**New Mappings** (added to existing `mapPrefixes`):

```typescript
const mappings: Record<string, string> = {
  // ... existing mappings ...

  // Remote MCP Access (Feature 010)
  MADEINOZ_KNOWLEDGE_PROFILE: 'KNOWLEDGE_PROFILE',
  MADEINOZ_KNOWLEDGE_HOST: 'KNOWLEDGE_HOST',
  MADEINOZ_KNOWLEDGE_PORT: 'KNOWLEDGE_PORT',
  MADEINOZ_KNOWLEDGE_PROTOCOL: 'KNOWLEDGE_PROTOCOL',
  MADEINOZ_KNOWLEDGE_BASE_PATH: 'KNOWLEDGE_BASE_PATH',
  MADEINOZ_KNOWLEDGE_TLS_VERIFY: 'KNOWLEDGE_TLS_VERIFY',
  MADEINOZ_KNOWLEDGE_TLS_CA: 'KNOWLEDGE_TLS_CA',
  MADEINOZ_KNOWLEDGE_TLS_CERT: 'KNOWLEDGE_TLS_CERT',
  MADEINOZ_KNOWLEDGE_TLS_KEY: 'KNOWLEDGE_TLS_KEY',
};
```

### YAML Configuration File

**Location**: `$PAI_DIR/config/knowledge-profiles.yaml`

**Schema** (see `data-model.md` for full definition):

```yaml
version: "1.0"
default_profile: default

profiles:
  default:
    host: localhost
    port: 8001
    protocol: http

  # Additional profiles...
```

---

## Docker Compose Contracts

### New Volume Mounts

**For TLS Certificates** (when `MCP_TLS_ENABLED=true`):

```yaml
services:
  graphiti-mcp:
    volumes:
      # Mount certificate directory as read-only
      - ${MCP_CERTS_DIR:-./certs}:/certs:ro
```

### New Environment Variables

**Added to docker-compose files**:

```yaml
services:
  graphiti-mcp:
    environment:
      # Remote access support
      - MCP_HOST=${MCP_HOST:-127.0.0.1}
      - MCP_PORT=${MCP_PORT:-8000}
      # TLS support
      - MCP_TLS_ENABLED=${MCP_TLS_ENABLED:-false}
      - MCP_TLS_CERTPATH=${MCP_TLS_CERTPATH:-/certs/cert.pem}
      - MCP_TLS_KEYPATH=${MCP_TLS_KEYPATH:-/certs/key.pem}
```

---

## Error Handling Contracts

### Error Codes

| Code | Message | Condition |
|------|---------|-----------|
| `E_HOST_UNREACHABLE` | "Unable to reach host {host}:{port}" | DNS resolution or connection timeout |
| `E_TLS_VERIFICATION_FAILED` | "Certificate verification failed" | Invalid certificate |
| `E_TLS_HANDSHAKE_FAILED` | "TLS handshake failed" | Protocol mismatch or cipher error |
| `E_PROFILE_NOT_FOUND` | "Profile '{name}' not found" | Unknown profile name |
| `E_PROFILE_INVALID` | "Profile '{name}' is invalid: {errors}" | Validation failed |
| `E_CONNECTION_TIMEOUT` | "Connection timed out after {timeout}ms" | Request timeout |
| `E_SERVER_ERROR` | "Server returned error: {status}" | HTTP error response |

### Error Response Format

```typescript
interface ConnectionError {
  code: string;
  message: string;
  details?: {
    host?: string;
    port?: number;
    profile?: string;
    cause?: string;
  };
  suggestions?: string[];
}
```

---

## Backward Compatibility Guarantees

1. **Default Behavior**: Without any configuration, client connects to `http://localhost:8001/mcp`
2. **Existing API**: All existing `MCPClient` methods remain unchanged
3. **Optional Features**: All new fields are optional with sensible defaults
4. **Profile Loading**: Only activates if `MADEINOZ_KNOWLEDGE_PROFILE` is set
5. **Environment Variables**: Individual env vars work without profile file
