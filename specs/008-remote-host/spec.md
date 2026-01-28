# Feature Specification: Knowledge CLI Remote Host Support

**Feature Branch**: `remote-host`
**Created**: 2026-01-28
**Status**: Draft
**Input**: User description: "for the current knowledge-cli tool is hardcoded to use localhost, we need to add remote host capabilities"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Connect to Remote Knowledge Server (Priority: P1)

A user needs to connect the knowledge-cli tool to a Knowledge MCP server running on a remote machine, enabling them to interact with knowledge graphs hosted across their infrastructure instead of only on localhost.

**Why this priority**: This is the core capability requested. Without it, users are limited to localhost-only connections, preventing distributed knowledge graph deployments and multi-machine workflows.

**Independent Test**: Can be fully tested by running `knowledge-cli.ts --host <remote-host> --port <port> get_status` and verifying it connects to the remote server instead of localhost.

**Acceptance Scenarios**:

1. **Given** the knowledge-cli tool is installed, **When** user provides `--host example.com` and `--port 9000`, **Then** the CLI connects to `http://example.com:9000/mcp` instead of localhost
2. **Given** no host/port flags are provided, **When** user runs any command, **Then** the CLI defaults to localhost:8000 (backward compatible behavior)
3. **Given** an invalid hostname, **When** user runs a command, **Then** the CLI returns a clear error message indicating connection failure

---

### User Story 2 - Environment Variable Configuration (Priority: P2)

A user wants to configure remote host settings via environment variables, avoiding the need to specify host/port on every command and enabling script-friendly configuration.

**Why this priority**: Environment variables are a standard configuration pattern that improves usability for automated scripts and persistent configurations. Less critical than basic CLI flags but important for operational workflows.

**Independent Test**: Can be fully tested by setting `MADEINOZ_KNOWLEDGE_HOST` and `MADEINOZ_KNOWLEDGE_PORT` environment variables and running commands without flags, verifying the configured values are used.

**Acceptance Scenarios**:

1. **Given** `MADEINOZ_KNOWLEDGE_HOST=remote.example.com` is set, **When** user runs a command without `--host`, **Then** the CLI connects to the configured host
2. **Given** `MADEINOZ_KNOWLEDGE_PORT=9000` is set, **When** user runs a command without `--port`, **Then** the CLI connects to the configured port
3. **Given** both environment variables and CLI flags are set, **When** user runs a command with `--host`, **Then** the CLI flag takes precedence over environment variables

---

### User Story 3 - Connection Verification and Diagnostics (Priority: P3)

A user wants to verify connectivity to a remote Knowledge server before executing commands and receive helpful diagnostic information when connection issues occur.

**Why this priority**: Improves user experience by providing early feedback on configuration issues. Lower priority because users can work around connection errors through trial-and-error, but diagnostics reduce frustration.

**Independent Test**: Can be fully tested by running the `health` command with various valid and invalid host configurations and verifying appropriate success/error messages.

**Acceptance Scenarios**:

1. **Given** a valid remote host configuration, **When** user runs `health` command, **Then** the CLI confirms successful connection to the remote server
2. **Given** an unreachable remote host, **When** user runs any command, **Then** the CLI provides a clear error message with the hostname/port that failed
3. **Given** connection timeout occurs, **When** user runs a command, **Then** the CLI indicates timeout instead of a generic error

---

### Edge Cases

- What happens when user provides an IP address instead of hostname? (Must support both formats)
- How does system handle SSL/TLS connections to HTTPS endpoints? (Validates certificates by default; `--insecure` flag skips validation for self-signed certs)
- What happens when port number is outside valid range (1-65535)? (Should validate and reject invalid ports)
- How does system handle DNS resolution failures? (Should provide clear error message)
- What happens when remote server requires authentication? (Out of scope for this feature - auth would require additional work)
- How does system handle connection timeouts to remote hosts? (10 second timeout with clear error message)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept a `--host` flag to specify the remote Knowledge MCP server hostname or IP address
- **FR-002**: System MUST accept a `--port` flag to specify the remote Knowledge MCP server port number
- **FR-003**: System MUST default to `localhost:8000` when no host/port flags are provided (backward compatibility)
- **FR-004**: System MUST construct the complete MCP server URL as `http://{host}:{port}/mcp` or `https://{host}:{port}/mcp`
- **FR-005**: System MUST support `MADEINOZ_KNOWLEDGE_HOST` environment variable for persistent host configuration
- **FR-006**: System MUST support `MADEINOZ_KNOWLEDGE_PORT` environment variable for persistent port configuration
- **FR-007**: System MUST prioritize CLI flags over environment variables when both are present
- **FR-008**: System MUST validate port numbers are within valid range (1-65535)
- **FR-009**: System MUST provide clear error messages when connection to remote host fails
- **FR-010**: System MUST indicate connection status (hostname/port) in health check output
- **FR-011**: System MUST support IPv4 addresses in addition to hostnames
- **FR-012**: System MUST construct HTTPS URLs when user specifies `https://` prefix in host parameter
- **FR-013**: System MUST validate TLS/SSL certificates by default for HTTPS connections
- **FR-014**: System MUST accept an `--insecure` flag to skip certificate validation for self-signed/invalid certificates
- **FR-015**: System MUST provide clear error messages including hostname and port by default
- **FR-016**: System MUST accept a `--verbose` flag that enables detailed diagnostic output (DNS resolution, connection timing, certificate details)
- **FR-017**: User documentation MUST be updated following Constitution Principle VIII (Dual-Audience Documentation), including:
  - Updated CLI help text with new flags and environment variables
  - Updated docs/index.md with AI-friendly summary and quick reference card
  - Updated docs/getting-started/ with remote connection examples
  - All documentation tables for new options, environment variables, and error messages

### Key Entities

- **Remote Host Configuration**: Represents the target Knowledge MCP server endpoint
  - Attributes: hostname/IP address, port number, protocol (http/https)
  - Sources: CLI flags, environment variables, default values
  - Priority: CLI flags > environment variables > defaults

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can successfully connect to remote Knowledge MCP servers by specifying `--host` and `--port` flags
- **SC-002**: Existing workflows using localhost continue to work without any configuration changes (100% backward compatibility)
- **SC-003**: Connection attempts to invalid hosts return clear error messages within 10 seconds (connection timeout)
- **SC-004**: Environment variable configuration works consistently across all CLI commands
- **SC-005**: Help text includes examples of remote host usage
- **SC-006**: Health command displays the connected server's hostname and port
- **SC-007**: User documentation includes AI-friendly summaries, structured tables, and examples per Constitution Principle VIII

## Clarifications

### Session 2026-01-28

- Q: What is the connection timeout value for remote Knowledge MCP servers? → A: 10 seconds
- Q: How should the CLI handle TLS/SSL certificate validation for HTTPS connections to remote servers? → A: Validate by default, add --insecure flag to skip validation
- Q: What level of logging/verbosity should the CLI provide for connection diagnostics? → A: Standard errors by default, --verbose flag for detailed diagnostics

## Assumptions

1. Remote Knowledge MCP servers are already running and accessible on the network
2. Network connectivity between the CLI machine and remote server exists
3. Remote servers use the same MCP protocol and API as the local server
4. No authentication is required for basic remote connections (auth is future work)
5. Users have valid DNS or IP address information for remote hosts
6. Remote servers have appropriate CORS/network configurations to accept connections

## Out of Scope

1. Authentication/authorization for remote connections
2. Connection pooling or load balancing across multiple servers
3. Automatic server discovery mechanisms
4. SSH tunneling or VPN configuration
5. Persistent connection profiles or saved configurations
6. Connection retry logic for transient network failures
