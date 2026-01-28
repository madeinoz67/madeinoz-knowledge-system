# Feature Specification: Configurable Memory Sync

**Feature Branch**: `007-configurable-memory-sync`
**Created**: 2026-01-28
**Status**: Draft
**Input**: User description: "Improve memory hook system with anti-loop detection, add configurable sync levels for different PAI memory types, and deprecate realtime sync hook"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure Memory Sync Sources (Priority: P1)

As a PAI user, I want to configure which types of memory content get synced to the knowledge graph so that I can control what information is stored and avoid unnecessary data accumulation.

**Why this priority**: This is the core value proposition - giving users control over their knowledge graph content. Without configurability, users cannot tailor the system to their workflow.

**Independent Test**: Can be fully tested by modifying sync configuration and verifying only specified content types are synced to the knowledge graph.

**Acceptance Scenarios**:

1. **Given** a configuration file with RESEARCH enabled and LEARNING disabled, **When** a new research file is created in MEMORY, **Then** only research content is synced to the knowledge graph
2. **Given** a configuration file with LEARNING/ALGORITHM enabled and LEARNING/SYSTEM disabled, **When** learnings are captured, **Then** only algorithm learnings are synced
3. **Given** a configuration file with all sources disabled, **When** the sync hook runs, **Then** no content is synced to the knowledge graph
4. **Given** an invalid configuration value, **When** the sync hook initializes, **Then** the system logs a warning and uses default settings

---

### User Story 2 - Prevent Knowledge Feedback Loops (Priority: P1)

As a PAI user, I want the system to automatically detect and prevent knowledge query results from being re-synced as new learnings so that my knowledge graph does not contain recursive/duplicate content.

**Why this priority**: Critical for data integrity. Without loop prevention, knowledge queries create learnings that get re-synced, polluting the knowledge graph with meta-content about previous queries.

**Independent Test**: Can be fully tested by running a knowledge query, then verifying the query results are not subsequently synced as new episodes.

**Acceptance Scenarios**:

1. **Given** a learning file containing knowledge query output (e.g., "what do I know about X"), **When** the sync hook processes the file, **Then** the file is skipped with a log entry explaining why
2. **Given** a learning file with formatted search results from the knowledge system, **When** the sync hook processes the file, **Then** the file is detected as knowledge-derived and excluded
3. **Given** a learning file with MCP tool names related to knowledge operations, **When** the sync hook processes the file, **Then** the file is excluded from sync
4. **Given** a legitimate learning about a topic (not query output), **When** the sync hook processes the file, **Then** the file is synced normally

---

### User Story 3 - Deprecate Realtime Sync Hook (Priority: P2)

As a PAI maintainer, I want to consolidate sync functionality into a single hook so that the system is simpler to maintain and has fewer potential failure points.

**Why this priority**: Reduces complexity and eliminates the source of the current loopback issue. The main sync hook handles all sync operations adequately.

**Independent Test**: Can be tested by removing the realtime sync hook and verifying all memory content is still properly synced via the main hook.

**Acceptance Scenarios**:

1. **Given** the realtime sync hook is removed, **When** a new learning is captured during a session, **Then** the learning is synced by the main hook at session start
2. **Given** only the main sync hook is active, **When** memory files are created across multiple sessions, **Then** all files are eventually synced without gaps
3. **Given** the realtime sync hook files are deleted, **When** the system runs, **Then** no errors occur and sync behavior remains correct

---

### User Story 4 - View Sync Status and Configuration (Priority: P3)

As a PAI user, I want to see what memory sources are configured for sync and recent sync activity so that I can understand what content is being stored in my knowledge graph.

**Why this priority**: Provides transparency and debugging capability. Users need visibility into system behavior to trust and troubleshoot it.

**Independent Test**: Can be tested by running a status command and verifying it shows current configuration and recent sync activity.

**Acceptance Scenarios**:

1. **Given** sync has been configured, **When** the user requests sync status, **Then** all enabled/disabled sources are displayed
2. **Given** recent files have been synced, **When** the user requests sync status, **Then** the count and types of recently synced files are shown
3. **Given** files were skipped due to loop detection, **When** the user requests sync status, **Then** the skipped files and reasons are shown

---

### User Story 5 - Production Docker Compose for Remote Systems (Priority: P2)

As a PAI user, I want a production-ready Docker Compose configuration for deploying the knowledge graph on remote servers so that I can run the knowledge system on infrastructure that does not have PAI installed.

**Why this priority**: Enables separation of concerns - knowledge graph can run on dedicated infrastructure, improving reliability and allowing centralized access from multiple PAI instances.

**Independent Test**: Can be tested by deploying the Docker Compose configuration on a fresh server without PAI and verifying the knowledge graph is accessible.

**Acceptance Scenarios**:

1. **Given** a server without PAI installed, **When** the production Docker Compose file is deployed, **Then** the knowledge graph service starts successfully
2. **Given** the production deployment, **When** a client connects using standard credentials, **Then** the knowledge graph accepts connections and processes queries
3. **Given** the production deployment uses native naming (no PAI prefixes), **When** services are listed, **Then** service names are clean and production-appropriate (e.g., "knowledge-graph", not "madeinoz-knowledge-graph")
4. **Given** the production deployment, **When** the server restarts, **Then** services automatically restart and data persists

---

### Edge Cases

- What happens when the configuration file is missing or corrupted? System uses sensible defaults (all sources enabled except knowledge-derived content)
- How does the system handle files that match both inclusion and exclusion criteria? Exclusion takes precedence (anti-loop patterns always block)
- What happens when a file is partially synced before an error? Transaction should be atomic - either fully synced or not synced at all
- How does the system handle very large learning files? Files are synced as single episodes with content truncation if exceeding knowledge graph limits
- What happens when the remote knowledge graph is unreachable? Sync operations queue locally and retry on next session
- How does production deployment handle database migrations? Container includes automatic schema setup on first run

### Out of Scope

- Remote server provisioning, creation, or infrastructure management
- Remote container lifecycle operations (start, stop, restart) - user responsibility
- Remote monitoring, alerting, or health check automation
- Multi-region or clustered Neo4j deployments
- Automated backup/restore for remote deployments
- TLS/SSL configuration - user responsibility to add if needed
- Advanced security hardening beyond Neo4j defaults

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a configuration mechanism to enable/disable sync for each memory source type (LEARNING/ALGORITHM, LEARNING/SYSTEM, RESEARCH)
- **FR-002**: System MUST detect and exclude content that originated from knowledge graph queries before syncing
- **FR-003**: System MUST apply anti-loop detection patterns to all file content before syncing, regardless of source
- **FR-004**: System MUST log all sync decisions (synced, skipped, failed) with reasons
- **FR-005**: System MUST consolidate all sync functionality into the main sync hook (sync-memory-to-knowledge.ts)
- **FR-006**: System MUST remove or disable the realtime sync hook (sync-learning-realtime.ts) to eliminate duplicate processing
- **FR-007**: System MUST provide a mechanism to view current sync configuration and recent sync activity
- **FR-008**: System MUST use sensible defaults when configuration is missing (sync all legitimate content, exclude knowledge-derived content)
- **FR-009**: System MUST detect knowledge operations by checking for MCP tool patterns, formatted query output, and knowledge-related keywords in file content
- **FR-010**: System MUST preserve backward compatibility with existing sync state files
- **FR-011**: System MUST provide a production-ready Docker Compose configuration for standalone Neo4j deployment on remote servers
- **FR-012**: Production deployment MUST use native service naming without PAI-specific prefixes
- **FR-013**: Production deployment MUST support automatic restart on failure and data persistence
- **FR-014**: Production deployment MUST include Neo4j default authentication (user configures credentials and optional TLS)
- **FR-015**: Production Docker Compose MUST use native Neo4j environment variable names (no MADEINOZ_ prefixes)
- **FR-016**: Production Docker Compose configuration MUST remain synchronized with local compose structure across all releases
- **FR-017**: System MUST include user documentation for remote production deployment aligned with project constitution
- **FR-018**: System MUST use dual deduplication (file path AND content hash) to prevent duplicate syncing
- **FR-019**: System MUST sync memory to knowledge at SessionStart only (no SessionEnd sync)
- **FR-020**: System MUST support loading sync source paths from an external configuration file instead of hardcoding them
- **FR-021**: External configuration file MUST define path patterns, content types, and descriptions for each sync source
- **FR-022**: System MUST fall back to default paths if external configuration file is missing or invalid

### Key Entities

- **SyncConfiguration**: Settings controlling which memory sources are synced (source types, enabled/disabled flags, custom patterns)
- **SyncSourceConfig**: External configuration file defining available sync sources (path patterns, content types, descriptions)
- **SyncSource**: A category of memory content eligible for sync (path pattern, content type, description)
- **AntiLoopPattern**: A pattern used to detect knowledge-derived content (pattern string, description, match type)
- **SyncDecision**: A record of whether a file was synced or skipped (file path, decision, reason, timestamp)
- **ProductionDeployment**: A standalone Docker Compose configuration for remote servers (service definitions, volume mounts, network configuration, environment defaults)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can configure sync sources and see changes reflected within the next sync cycle
- **SC-002**: Knowledge query results are never synced back to the knowledge graph (0% false negative rate on loop detection)
- **SC-003**: Legitimate learnings are correctly identified and synced (less than 1% false positive rate on loop detection)
- **SC-004**: System operates with a single sync hook instead of two, reducing code complexity
- **SC-005**: Users can view sync status showing configuration and recent activity within 2 seconds
- **SC-006**: Existing sync state and previously synced content remain accessible after the update
- **SC-007**: Production deployment can be set up on a fresh server with a single docker-compose command
- **SC-008**: Remote knowledge graph accepts connections from PAI clients within 30 seconds of deployment

## Clarifications

### Session 2026-01-28

- Q: Which database backend should the production deployment use? → A: Neo4j only (current default, native Cypher, ports 7474/7687)
- Q: Where should sync source configuration be stored? → A: Native container environment variables only (no PAI prefixes in production compose). Production compose uses same config structure as local but with native Neo4j variable names. Remote operations (create/start/stop) are user responsibility, out of scope for pack. Configs must never diverge between releases.
- Q: What security configuration should production Docker Compose include? → A: Minimal (Neo4j default auth only, user adds TLS if needed). Security hardening is user responsibility.
- Q: How should the system determine if a file has already been synced? → A: Both file path AND content hash (skip if file path already synced OR content hash already exists).
- Q: When should memory-to-knowledge sync occur? → A: SessionStart only (sync previous session's content when new session begins).
- Q: Where should sync source paths be configured? → A: External JSON configuration file at `config/sync-sources.json`. This allows users to customize sync paths without modifying code. Falls back to built-in defaults if file is missing.

## Assumptions

- The main sync hook (sync-memory-to-knowledge.ts) already handles batch syncing correctly and will be enhanced rather than replaced
- Production deployment uses Neo4j as the sole database backend
- Anti-loop detection patterns can reliably distinguish between knowledge query output and legitimate learnings
- Local sync configuration uses existing MADEINOZ_KNOWLEDGE_* environment variable pattern
- Production compose uses native Neo4j environment variables (no pack-specific prefixes)
- Users are responsible for all remote server operations (deployment, lifecycle management)
- The PAI Memory System directory structure (LEARNING/ALGORITHM, LEARNING/SYSTEM, RESEARCH) provides sensible defaults but can be customized via external configuration
- Sync occurs at SessionStart only; content from current session is available in next session
