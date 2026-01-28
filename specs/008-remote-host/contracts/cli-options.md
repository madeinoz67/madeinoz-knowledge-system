# CLI Options Contract: Remote Host Support

**Feature**: 008-remote-host | **Date**: 2026-01-28

## New CLI Options

### --host

| Property | Value |
|----------|-------|
| Flag | `--host` |
| Argument | `<hostname>` |
| Type | string |
| Required | No |
| Default | `localhost` (or `MADEINOZ_KNOWLEDGE_HOST` env var) |
| Description | Knowledge MCP server hostname or IP address |

**Behavior**:
- Accepts hostnames: `example.com`, `server.internal.local`
- Accepts IPv4 addresses: `192.168.1.100`, `10.0.0.5`
- Accepts protocol prefix: `https://example.com` (enables HTTPS)
- If provided, overrides `MADEINOZ_KNOWLEDGE_HOST` environment variable

**Examples**:
```bash
--host example.com
--host 192.168.1.100
--host https://secure.example.com
```

---

### --port

| Property | Value |
|----------|-------|
| Flag | `--port` |
| Argument | `<number>` |
| Type | integer |
| Required | No |
| Default | `8000` (or `MADEINOZ_KNOWLEDGE_PORT` env var) |
| Valid Range | 1-65535 |
| Description | Knowledge MCP server port number |

**Behavior**:
- Validates port is within valid range (1-65535)
- Exits with error if invalid port provided
- If provided, overrides `MADEINOZ_KNOWLEDGE_PORT` environment variable

**Examples**:
```bash
--port 9000
--port 443
--port 8080
```

**Error Cases**:
```bash
--port 0        # Error: Invalid port: 0. Port must be between 1 and 65535.
--port 65536    # Error: Invalid port: 65536. Port must be between 1 and 65535.
--port -1       # Error: Invalid port: -1. Port must be between 1 and 65535.
--port abc      # Error: Invalid port: abc. Port must be a number.
```

---

### --insecure

| Property | Value |
|----------|-------|
| Flag | `--insecure` |
| Argument | None (boolean flag) |
| Type | boolean |
| Required | No |
| Default | `false` |
| Description | Skip TLS certificate validation |

**Behavior**:
- Only affects HTTPS connections
- Allows connections to servers with self-signed certificates
- Allows connections to servers with expired certificates
- Displays warning when enabled

**Examples**:
```bash
--host https://internal.local --insecure
```

**Warning Output**:
```
⚠️  TLS certificate validation disabled (--insecure flag)
```

---

### --verbose

| Property | Value |
|----------|-------|
| Flag | `--verbose` |
| Argument | None (boolean flag) |
| Type | boolean |
| Required | No |
| Default | `false` |
| Description | Enable detailed connection diagnostics |

**Behavior**:
- Shows DNS resolution status
- Shows connection timing
- Shows TLS certificate details (for HTTPS)
- Shows full error stack traces on failure

**Examples**:
```bash
--host example.com --verbose
```

**Verbose Output Example**:
```
🔍 Connection diagnostics:
   Host: example.com
   Port: 9000
   Protocol: HTTPS
   DNS resolved: 203.0.113.50 (15ms)
   TCP connected: 45ms
   TLS handshake: 120ms
   Certificate: CN=example.com, expires 2027-01-01
   Total: 180ms
```

---

## Environment Variables

### MADEINOZ_KNOWLEDGE_HOST

| Property | Value |
|----------|-------|
| Variable | `MADEINOZ_KNOWLEDGE_HOST` |
| Type | string |
| Default | Not set (falls back to `localhost`) |
| Priority | Lower than `--host` flag |
| Description | Default server hostname when `--host` not provided |

---

### MADEINOZ_KNOWLEDGE_PORT

| Property | Value |
|----------|-------|
| Variable | `MADEINOZ_KNOWLEDGE_PORT` |
| Type | string (parsed as integer) |
| Default | Not set (falls back to `8000`) |
| Priority | Lower than `--port` flag |
| Description | Default server port when `--port` not provided |

---

## Priority Rules

Configuration values are resolved in this order (highest to lowest priority):

1. **CLI flags** (`--host`, `--port`)
2. **Environment variables** (`MADEINOZ_KNOWLEDGE_HOST`, `MADEINOZ_KNOWLEDGE_PORT`)
3. **Built-in defaults** (`localhost`, `8000`)

---

## Updated Help Text

```
Connection Options:
  --host <hostname>   Knowledge MCP server hostname or IP (default: localhost)
  --port <number>     Knowledge MCP server port (default: 8000)
  --insecure          Skip TLS certificate validation for self-signed certs
  --verbose           Enable detailed connection diagnostics

Environment Variables:
  MADEINOZ_KNOWLEDGE_HOST    Remote server hostname (overridden by --host)
  MADEINOZ_KNOWLEDGE_PORT    Remote server port (overridden by --port)
```

---

## Command Examples

```bash
# Connect to remote server on custom port
bun run src/skills/tools/knowledge-cli.ts --host example.com --port 9000 get_status

# Connect to HTTPS server
bun run src/skills/tools/knowledge-cli.ts --host https://example.com --port 443 get_status

# Connect with self-signed certificate
bun run src/skills/tools/knowledge-cli.ts --host https://internal.local --port 8443 --insecure get_status

# Verbose diagnostics
bun run src/skills/tools/knowledge-cli.ts --host example.com --verbose health

# Using environment variables
export MADEINOZ_KNOWLEDGE_HOST=example.com
export MADEINOZ_KNOWLEDGE_PORT=9000
bun run src/skills/tools/knowledge-cli.ts get_status
```
