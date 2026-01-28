# Data Model: Knowledge CLI Remote Host Support

**Feature**: 008-remote-host | **Date**: 2026-01-28

## Overview

This feature extends the knowledge-cli tool to support remote MCP server connections. The data model is minimal—a runtime configuration object built from CLI flags, environment variables, and defaults.

---

## Core Entity: RemoteHostConfig

### Description

Represents the target Knowledge MCP server endpoint configuration. This is a runtime-only configuration (no persistent storage required).

### Attributes

| Attribute | Type | Source | Validation | Default |
|-----------|------|--------|------------|---------|
| `host` | `string` | CLI `--host`, env `MADEINOZ_KNOWLEDGE_HOST` | Non-empty string, valid hostname or IPv4 | `"localhost"` |
| `port` | `number` | CLI `--port`, env `MADEINOZ_KNOWLEDGE_PORT` | Integer, 1-65535 | `8000` |
| `protocol` | `"http" \| "https"` | Derived from `host` prefix | N/A | `"http"` (unless `host` starts with `https://`) |
| `insecure` | `boolean` | CLI `--insecure` flag only | N/A | `false` |
| `verbose` | `boolean` | CLI `--verbose`, env `MADEINOZ_KNOWLEDGE_VERBOSE` | N/A | `false` |
| `timeout` | `number` | Constant (from clarification) | N/A | `10000` (10 seconds) |

### TypeScript Interface

```typescript
interface RemoteHostConfig {
  /** Target hostname or IP address (may include protocol prefix) */
  host: string;

  /** Target port number (1-65535) */
  port: number;

  /** Derived protocol (http or https) */
  protocol: 'http' | 'https';

  /** Skip TLS certificate validation (HTTPS only) */
  insecure: boolean;

  /** Enable verbose diagnostic output */
  verbose: boolean;

  /** Connection timeout in milliseconds */
  timeout: number;
}

/** Constructed MCP server URL */
type McpServerUrl = string; // e.g., "http://example.com:9000/mcp"
```

---

## Configuration Resolution

### Priority Order

```
CLI Flag > Environment Variable > Default Value
```

### Resolution Table

| Setting | CLI Flag | Environment Variable | Default |
|---------|----------|---------------------|---------|
| Host | `--host <value>` | `MADEINOZ_KNOWLEDGE_HOST` | `localhost` |
| Port | `--port <value>` | `MADEINOZ_KNOWLEDGE_PORT` | `8000` |
| Insecure | `--insecure` (flag) | *(none - CLI only)* | `false` |
| Verbose | `--verbose` (flag) | `MADEINOZ_KNOWLEDGE_VERBOSE=true` | `false` |

---

## Derived Values

### MCP Server URL Construction

```
{protocol}://{host}:{port}/mcp
```

**Examples**:

| Input Host | Input Port | Protocol | Output URL |
|------------|------------|----------|------------|
| `localhost` | `8000` | `http` | `http://localhost:8000/mcp` |
| `example.com` | `9000` | `http` | `http://example.com:9000/mcp` |
| `https://secure.com` | `443` | `https` | `https://secure.com:443/mcp` |
| `192.168.1.10` | `3000` | `http` | `http://192.168.1.10:3000/mcp` |

### Protocol Detection

```typescript
function detectProtocol(host: string): 'http' | 'https' {
  return host.startsWith('https://') ? 'https' : 'http';
}

function stripProtocol(host: string): string {
  return host.replace(/^https?:\/\//, '');
}
```

---

## State Machine (Connection States)

This is a stateless CLI tool, but the connection process follows these states:

```
[Idle] → [Connecting] → [Connected] → [Idle]
                ↓
             [Failed]
```

| State | Description | Trigger | Next States |
|-------|-------------|---------|-------------|
| `Idle` | No active connection | CLI invocation | `Connecting` |
| `Connecting` | Attempting connection | Connect request | `Connected`, `Failed` |
| `Connected` | Request completed successfully | Server response | `Idle` |
| `Failed` | Connection error | Timeout/refused/error | `Idle` (with error) |

---

## Validation Rules

### Port Validation

```typescript
function validatePort(port: string | number): number {
  const num = typeof port === 'string' ? parseInt(port, 10) : port;
  if (isNaN(num) || num < 1 || num > 65535) {
    throw new Error(`Invalid port: ${port}. Must be between 1-65535.`);
  }
  return num;
}
```

### Host Validation

```typescript
function validateHost(host: string): string {
  if (!host || host.trim().length === 0) {
    throw new Error('Host cannot be empty.');
  }
  // Allow hostname, IPv4, or protocol-prefixed values
  // Actual connectivity validated during connection attempt
  return host.trim();
}
```

---

## Error Types

### Connection Error Categories

| Error Type | Message Pattern | Cause |
|------------|-----------------|-------|
| `InvalidPort` | "Invalid port: {port}. Must be between 1-65535." | User input validation |
| `EmptyHost` | "Host cannot be empty." | User input validation |
| `ConnectionTimeout` | "Connection to {host}:{port} timed out after 10s." | Network timeout |
| `ConnectionRefused` | "Connection to {host}:{port} was refused." | Server not running |
| `DnsFailure` | "DNS resolution failed for {host}." | Invalid hostname |
| `TlsValidationFailed` | "TLS certificate validation failed for {host}. Use --insecure to bypass." | Invalid/self-signed cert |

---

## Relationships

This configuration entity has no persistent relationships. It is consumed by:

1. **MCP Client Layer** (`src/server/lib/mcp-client.ts` or equivalent)
   - Uses `RemoteHostConfig` to construct server URL
   - Passes `insecure` flag to fetch options
   - Uses `timeout` for connection attempts

2. **CLI Layer** (`src/skills/server/tools/start.ts` or equivalent)
   - Parses CLI flags
   - Reads environment variables
   - Constructs `RemoteHostConfig` object

3. **Diagnostics** (new `--verbose` output)
   - Uses `verbose` flag to determine output detail level
   - Logs connection attempts, timing, certificate details

---

## Persistence

**None.** This is a stateless CLI configuration. No database or file storage required.

---

## Migration Notes

**Existing Behavior**: Currently hardcoded to `localhost:8000`.

**Backward Compatibility**: When no flags provided, defaults to `localhost:8000` (100% compatible).

**No Migration Required**: Runtime-only change with safe defaults.
