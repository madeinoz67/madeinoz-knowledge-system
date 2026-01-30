# Feature Specification: Remote MCP Access for Knowledge CLI

**Feature Branch**: `010-remote-mcp-access`
**Created**: 2026-01-30
**Status**: Draft
**Input**: User description: "Feature: Add remote MCP access to knowledge-cli - The knowledge-cli currently only supports localhost access. Add support for remote MCP connections to enable accessing the knowledge graph from remote systems (Claude Code instances on different machines, AI agents, etc.). Include environment variable configuration, connection URL parameters, TLS/SSL support, and multiple knowledge system profiles."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Remote Machine Access (Priority: P1)

A developer runs the knowledge MCP server on their home server but wants to access the knowledge graph from their laptop using Claude Code. They need to connect to the remote server securely and perform all the same operations they could do locally (search nodes, query facts, add memories, retrieve episodes).

**Why this priority**: This is the core use case that enables multi-machine workflows. Without this, users are limited to single-machine setups. This delivers immediate value by enabling the primary "remote access" scenario.

**Independent Test**: Can be fully tested by configuring a remote host, establishing a connection, and performing a knowledge search query. Delivers the ability to access knowledge from a different machine.

**Acceptance Scenarios**:

1. **Given** the MCP server is running on a remote machine, **When** a user sets the `MADEINOZ_KNOWLEDGE_HOST` environment variable to the remote host, **Then** the knowledge CLI successfully connects and responds to queries
2. **Given** a valid remote host configuration, **When** a user executes a search operation, **Then** results are returned as expected with appropriate latency
3. **Given** a remote connection is active, **When** a user adds a memory, **Then** the memory is persisted on the remote server
4. **Given** an unreachable remote host, **When** the knowledge CLI attempts connection, **Then** a clear error message is displayed indicating the connection failure

---

### User Story 2 - Secure Encrypted Connections (Priority: P2)

A system administrator needs to deploy the knowledge MCP server in a production environment where traffic traverses untrusted networks. They require TLS/SSL encryption to protect sensitive knowledge data in transit.

**Why this priority**: Security is critical for production deployments and team environments. Without encryption, sensitive knowledge could be intercepted. This enables safe remote access over public networks.

**Independent Test**: Can be fully tested by configuring TLS certificates, establishing an HTTPS connection, and verifying encrypted traffic. Delivers secure remote access capabilities.

**Acceptance Scenarios**:

1. **Given** TLS is configured with a valid certificate, **When** a user connects via HTTPS, **Then** the connection succeeds without security warnings
2. **Given** TLS is enabled, **When** network traffic is inspected, **Then** data appears encrypted
3. **Given** a self-signed certificate is used, **When** a user connects, **Then** they are prompted to verify or accept the certificate
4. **Given** an expired or invalid certificate, **When** a connection attempt is made, **Then** a clear certificate error is displayed

---

### User Story 3 - Multiple Knowledge System Profiles (Priority: P3)

A researcher maintains separate knowledge graphs for personal projects, work research, and collaborative team knowledge. They need to easily switch between these different knowledge systems without manually reconfiguring connection settings each time.

**Why this priority**: Multi-environment support enhances productivity for power users and teams. This is a quality-of-life improvement that doesn't block core functionality but significantly improves the user experience.

**Independent Test**: Can be fully tested by defining multiple profiles, switching between them, and verifying connections to different knowledge systems. Delivers the ability to manage multiple knowledge contexts.

**Acceptance Scenarios**:

1. **Given** multiple profiles are configured, **When** a user selects a profile by name, **Then** the CLI connects to the configured host for that profile
2. **Given** no profile is specified, **When** the CLI starts, **Then** it uses the "default" profile
3. **Given** a specified profile does not exist, **When** the CLI attempts to use it, **Then** a clear error lists available profiles
4. **Given** profiles are stored in a configuration file, **When** the file is modified, **Then** changes are reflected in the next CLI session without requiring code changes

---

### User Story 4 - Team Knowledge Sharing (Priority: P3)

A team wants to run a centralized knowledge graph that multiple members can access simultaneously. They need to connect from different machines to the same knowledge system, with proper security controls.

**Why this priority**: This enables collaborative knowledge management. It's an advanced use case that builds on the core remote access functionality.

**Independent Test**: Can be fully tested by having multiple clients connect to the same server simultaneously and perform concurrent operations. Delivers collaborative knowledge access.

**Acceptance Scenarios**:

1. **Given** multiple users connect to the same remote knowledge server, **When** one user adds a memory, **Then** other users can search and retrieve that memory
2. **Given** concurrent connections are active, **When** multiple users query simultaneously, **Then** all queries complete successfully without data corruption
3. **Given** authentication is configured, **When** a user without valid credentials attempts connection, **Then** access is denied with an appropriate error message

---

### Edge Cases

- What happens when the remote server becomes unavailable after initial connection succeeds?
- How does the system handle network latency and timeouts during queries?
- What happens when the remote server's TLS certificate changes between connections?
- How does the system behave when DNS resolution fails for the configured host?
- What happens when connection profiles contain conflicting or invalid configurations?
- How does the system handle very large query results over high-latency connections?
- What happens when a remote user exceeds rate limits or sends malformed requests?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow users to specify a remote host address for the knowledge MCP server via environment variable configuration
- **FR-002**: The system MUST support specifying a port number for remote connections
- **FR-003**: The system MUST support both HTTP and HTTPS protocols for remote connections
- **FR-004**: The MCP server MUST be configurable to listen on external network interfaces (0.0.0.0) instead of only localhost
- **FR-005**: The system MUST support TLS/SSL encrypted connections when using HTTPS protocol
- **FR-006**: The system MUST allow users to configure and switch between multiple knowledge system connection profiles
- **FR-007**: The system MUST provide clear error messages when remote connection attempts fail
- **FR-008**: The system MUST support configurable connection timeouts for remote operations
- **FR-009**: The system MUST validate connection profiles and report configuration errors before attempting connection
- **FR-010**: The system MUST maintain backward compatibility by defaulting to localhost when no remote configuration is provided
- **FR-011**: The system MUST support TLS certificate verification for HTTPS connections
- **FR-012**: The system MUST allow users to optionally bypass certificate verification for self-signed certificates
- **FR-013**: The system MUST display connection status information when connecting to remote hosts

### Key Entities

- **Connection Profile**: A named configuration containing host, port, protocol, and TLS settings for connecting to a knowledge system
- **Remote Server Configuration**: Settings that control how the MCP server accepts connections (listening interface, port, TLS certificates)
- **Connection State**: The current status of the client's connection to a remote knowledge system (connected, disconnected, error)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can successfully connect to a remote knowledge server from a different machine within 5 seconds of configuration
- **SC-002**: Remote knowledge queries complete with latency under 2 seconds on standard broadband connections
- **SC-003**: 100% of remote connections using valid TLS certificates establish without security warnings
- **SC-004**: Users can switch between connection profiles using a single command or environment variable
- **SC-005**: Connection failures produce actionable error messages that indicate the specific problem (host unreachable, timeout, certificate error)
- **SC-006**: The system supports at least 10 concurrent remote connections without performance degradation
- **SC-007**: 95% of users can successfully configure remote access on their first attempt using provided documentation
- **SC-008**: All existing localhost functionality continues to work without any configuration changes

### Assumptions

- Users have network connectivity between the client machine and the remote knowledge server
- Firewall and network policies allow traffic on the configured ports
- For TLS/SSL, users can obtain or generate appropriate certificates (self-signed for development, CA-signed for production)
- The remote server has sufficient resources to handle concurrent connections
- DNS resolution is available for hostname-based connections (or users can provide IP addresses)

### Dependencies

- Docker/Podman container runtime for the MCP server
- Neo4j or FalkorDB backend database
- Network connectivity between client and server
- TLS certificates (if using HTTPS protocol)

### Out of Scope

- Authentication and authorization beyond TLS certificate validation
- User management and access control lists
- Multi-region or multi-cloud deployment configurations
- API gateway or reverse proxy configurations
- Load balancing across multiple server instances
- Data synchronization between separate knowledge graphs
- Web-based user interface for remote management
