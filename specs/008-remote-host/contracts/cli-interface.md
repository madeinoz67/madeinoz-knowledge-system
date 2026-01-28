# CLI Interface Contract: Remote Host Configuration

**Feature**: 008-remote-host | **Version**: 1.0.0

## Contract Versioning

This document defines the CLI interface contract for remote host configuration in the knowledge-cli tool.

**Version**: 1.0.0
**Last Updated**: 2026-01-28

---

## Command Line Flags

### New Flags

| Flag | Type | Environment Variable | Default | Description |
|------|------|---------------------|---------|-------------|
| `--host <value>` | string | `MADEINOZ_KNOWLEDGE_HOST` | `localhost` | Target MCP server hostname or IP address (may include `https://` prefix) |
| `--port <value>` | number | `MADEINOZ_KNOWLEDGE_PORT` | `8000` | Target MCP server port (1-65535) |
| `--insecure` | flag | *(none)* | `false` | Skip TLS certificate validation for HTTPS connections |
| `--verbose` | flag | `MADEINOZ_KNOWLEDGE_VERBOSE` | `false` | Enable detailed diagnostic output |

### Flag Behavior

**Priority**: CLI flags take precedence over environment variables.

**Example**:
```bash
# CLI flag overrides environment variable
export MADEINOZ_KNOWLEDGE_HOST=env-host.com
knowledge-cli --host cli-host.com get_status
# Result: Connects to cli-host.com:8000
```

---

## Usage Examples

### Basic Remote Connection

```bash
# Connect to remote server with default port
knowledge-cli --host remote.example.com get_status

# Connect to remote server with custom port
knowledge-cli --host db.company.internal --port 9000 search_nodes "test"

# Connect using IPv4 address
knowledge-cli --host 192.168.1.100 --port 3000 add_memory "test data"
```

### Environment Variable Configuration

```bash
# Set persistent configuration
export MADEINOZ_KNOWLEDGE_HOST=knowledge.company.com
export MADEINOZ_KNOWLEDGE_PORT=9000

# All commands now use the configured host
knowledge-cli get_status
knowledge-cli search_nodes "query"

# Override with CLI flag when needed
knowledge-cli --host localhost --port 8000 get_status
```

### HTTPS with TLS Validation

```bash
# Connect to HTTPS server (certificates validated by default)
knowledge-cli --host https://secure-knowledge.com get_status

# Skip certificate validation for self-signed certs
knowledge-cli --host https://dev.local --port 9443 --insecure get_status
```

### Verbose Diagnostics

```bash
# Enable detailed output for troubleshooting
knowledge-cli --host example.com --verbose get_status

# Output includes:
# - DNS resolution details
# - Connection timing
# - Certificate information (for HTTPS)
# - Server response headers
```

---

## Error Messages

### Input Validation Errors

| Scenario | Error Message |
|----------|---------------|
| Empty host | `Error: Host cannot be empty.` |
| Invalid port | `Error: Invalid port: {value}. Must be between 1-65535.` |
| Non-numeric port | `Error: Port must be a number. Received: {value}` |

### Connection Errors

| Scenario | Error Message |
|----------|---------------|
| Connection timeout | `Error: Connection to {host}:{port} timed out after 10s.` |
| Connection refused | `Error: Connection to {host}:{port} was refused. Verify the server is running.` |
| DNS failure | `Error: DNS resolution failed for {host}. Verify the hostname is correct.` |
| TLS validation failed | `Error: TLS certificate validation failed for {host}. Use --insecure to bypass (not recommended for production).` |

### Verbose Error Format

When `--verbose` is enabled, errors include additional context:

```
Error: Connection to remote.example.com:9000 timed out after 10s.

Verbose Details:
- Resolved address: 192.0.2.45:9000
- Connection attempt started: 2026-01-28T10:30:45Z
- Timeout triggered: 2026-01-28T10:30:55Z
- DNS resolution: 45ms
- Connection attempts: 1

Troubleshooting:
1. Verify network connectivity to remote.example.com
2. Check if the server is running: ssh remote.example.com "systemctl status knowledge-server"
3. Test basic connectivity: telnet remote.example.com 9000
4. Check firewall rules on the remote server
```

---

## Backward Compatibility

### Default Behavior (No Flags)

When no `--host` or `--port` flags are provided:

```bash
knowledge-cli get_status
```

**Behavior**: Connects to `localhost:8000` (existing default).

**Rationale**: Maintains 100% backward compatibility with existing workflows.

---

## Environment Variable Reference

### Complete Variable List

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MADEINOZ_KNOWLEDGE_HOST` | string | `localhost` | Default MCP server hostname |
| `MADEINOZ_KNOWLEDGE_PORT` | string | `8000` | Default MCP server port |
| `MADEINOZ_KNOWLEDGE_VERBOSE` | string | `""` | Set to `"true"` for verbose output |

### Shell Configuration Example

```bash
# ~/.bashrc or ~/.zshrc
export MADEINOZ_KNOWLEDGE_HOST=knowledge.company.internal
export MADEINOZ_KNOWLEDGE_PORT=9000
export MADEINOZ_KNOWLEDGE_VERBOSE=true
```

---

## Help Text Updates

### Updated Help Output

```
knowledge-cli - CLI for Knowledge MCP Server

USAGE:
  knowledge-cli [OPTIONS] <COMMAND>

OPTIONS:
  --host <value>         Target MCP server hostname or IP (default: localhost)
                         Environment: MADEINOZ_KNOWLEDGE_HOST
  --port <value>         Target MCP server port (default: 8000)
                         Environment: MADEINOZ_KNOWLEDGE_PORT
  --insecure             Skip TLS certificate validation for HTTPS (USE WITH CAUTION)
  --verbose              Enable detailed diagnostic output
  -h, --help             Show help information

COMMANDS:
  get_status             Check server connection status
  search_nodes <query>   Search for entities in the knowledge graph
  add_memory <content>   Store new content in the knowledge graph
  ...                    [other commands]

EXAMPLES:
  # Connect to remote server
  knowledge-cli --host remote.example.com --port 9000 get_status

  # Use environment variables
  export MADEINOZ_KNOWLEDGE_HOST=remote.example.com
  knowledge-cli get_status

  # HTTPS with self-signed certificate
  knowledge-cli --host https://dev.local --insecure get_status
```

---

## Implementation Checklist

- [ ] Add `--host` flag parsing to CLI argument parser
- [ ] Add `--port` flag parsing with validation (1-65535)
- [ ] Add `--insecure` flag (boolean, CLI-only)
- [ ] Add `--verbose` flag (boolean, supports environment variable)
- [ ] Read `MADEINOZ_KNOWLEDGE_HOST` environment variable
- [ ] Read `MADEINOZ_KNOWLEDGE_PORT` environment variable
- [ ] Read `MADEINOZ_KNOWLEDGE_VERBOSE` environment variable
- [ ] Implement connection timeout (10 seconds)
- [ ] Implement TLS certificate validation (default: enabled)
- [ ] Implement `--insecure` flag to skip TLS validation
- [ ] Update error messages with host/port details
- [ ] Implement verbose diagnostic output
- [ ] Update help text with examples
- [ ] Add tests for flag parsing
- [ ] Add tests for environment variable fallback
- [ ] Add tests for port validation
- [ ] Add tests for connection timeout
- [ ] Add tests for TLS validation behavior

---

## Non-Functional Requirements

| Requirement | Value | Notes |
|-------------|-------|-------|
| Connection Timeout | 10 seconds | Configurable for future enhancement |
| Flag Parsing Time | < 5ms | Should be imperceptible |
| Error Message Latency | < 100ms | Error detection and display |
| Backward Compatibility | 100% | No breaking changes to existing behavior |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-28 | Initial contract definition |
