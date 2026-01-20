# Feature Specification: Fix Sync Hook Protocol Mismatch

**Feature Branch**: `003-fix-issue-2`
**Created**: 2026-01-20
**Status**: Draft
**Input**: User description: "fix issue https://github.com/madeinoz67/madeinoz-knowledge-system/issues/2"

## Clarifications

### Session 2026-01-20

- Q: What level of operational logging should the sync hook provide? → A: Errors + warnings + sync stats (files processed, succeeded, failed, skipped)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sync Memory Files to Knowledge Graph (Priority: P1)

As a PAI user, I want my memory files (LEARNING/ and RESEARCH/) to automatically sync to the knowledge graph when I start a session, so that my accumulated knowledge is available for semantic search and relationship discovery.

**Why this priority**: This is the core functionality of the Knowledge Pack. Without working sync, the knowledge graph cannot capture user learnings and research, making the entire system ineffective for knowledge management.

**Independent Test**: Can be fully tested by (1) starting the MCP server, (2) placing a test markdown file in LEARNING/ALGORITHM/, (3) running the sync hook, and (4) verifying the content appears in the knowledge graph via search. Delivers value by persisting user knowledge in a queryable graph.

**Acceptance Scenarios**:

1. **Given** the MCP server is running at localhost:8000, **When** the sync hook executes during SessionStart, **Then** new memory files are successfully added to the knowledge graph and marked as synced
2. **Given** a previously synced file with unchanged content, **When** the sync hook runs again, **Then** the file is skipped (not duplicated) and sync completes without errors
3. **Given** the MCP server is temporarily unavailable, **When** the sync hook executes, **Then** it retries with exponential backoff and gracefully degrades without blocking session startup
4. **Given** a memory file with YAML frontmatter containing rating and metadata, **When** the file is synced, **Then** the metadata is preserved in the knowledge graph episode

---

### User Story 2 - Manual Sync Operations (Priority: P2)

As a PAI user, I want to manually trigger sync operations with options like --all, --dry-run, and --verbose, so that I can control sync behavior and diagnose issues.

**Why this priority**: Manual sync is a useful debugging and administrative feature but is secondary to automatic sync. Users can still benefit from automatic sync even without manual controls.

**Independent Test**: Can be fully tested by (1) running the CLI with various flags, (2) verifying output messages match expected behavior, and (3) checking that --dry-run does not actually modify the knowledge graph. Delivers value by providing administrative control.

**Acceptance Scenarios**:

1. **Given** the sync script is run with --dry-run flag, **When** the operation completes, **Then** files are listed but no actual API calls are made to the MCP server
2. **Given** the sync script is run with --all flag, **When** the operation completes, **Then** all memory files are re-synced regardless of previous sync state
3. **Given** the sync script is run with --verbose flag, **When** the operation completes, **Then** detailed progress messages are shown including retry attempts and server health status
4. **Given** the sync script is run without flags, **When** the operation completes, **Then** only new or modified files are synced (default incremental behavior)

---

### User Story 3 - Health Check and Monitoring (Priority: P3)

As a PAI user, I want the sync hook to verify MCP server health before attempting sync operations, so that I receive clear feedback about connection issues.

**Why this priority**: Health checks improve user experience but are not critical to core sync functionality. The sync will fail gracefully even without explicit health checks.

**Independent Test**: Can be fully tested by (1) starting the sync hook with the server offline, (2) observing the retry behavior, and (3) confirming the appropriate error message is displayed. Delivers value by providing clear status feedback.

**Acceptance Scenarios**:

1. **Given** the MCP server is not running, **When** the sync hook starts, **Then** it attempts connection with retries and reports "MCP server offline after retries"
2. **Given** the MCP server is running, **When** the sync hook starts, **Then** it successfully establishes a connection and proceeds with sync operations
3. **Given** the MCP server becomes available during retry attempts, **When** the connection succeeds, **Then** sync operations proceed normally without requiring manual intervention

---

### Edge Cases

- What happens when memory directory does not exist at ~/.claude/MEMORY/?
- How does system handle files larger than 5000 characters (episode body limit)?
- What occurs when YAML frontmatter is malformed or missing?
- How does sync handle special characters in search queries (e.g., hyphens in CTI identifiers like "apt-28")?
- What happens when MCP server responds with HTTP 429 (rate limit) or 5xx errors?
- How does system handle concurrent sync operations (multiple hooks firing simultaneously)?
- What occurs when network latency causes requests to exceed the timeout threshold?
- How does system behave when database backend type changes (Neo4j vs FalkorDB)?
- What happens when MADEINOZ_KNOWLEDGE_DB environment variable is invalid or missing?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST establish MCP session via HTTP POST to /mcp/ endpoint with JSON-RPC 2.0 protocol
- **FR-002**: System MUST include Mcp-Session-Id header in all requests after session initialization
- **FR-003**: System MUST parse response body as SSE format (extract data: lines from response text)
- **FR-004**: System MUST determine query sanitization requirements based on MADEINOZ_KNOWLEDGE_DB environment variable (neo4j or falkorodb)
- **FR-005**: System MUST escape Lucene/RediSearch special characters (+ - && || ! ( ) { } [ ] ^ " ~ * ? : \ /) when database type is falkorodb
- **FR-006**: System MUST NOT escape special characters when database type is neo4j (uses native Cypher queries)
- **FR-007**: System MUST retry failed requests with exponential backoff for retryable errors (timeout, ECONNREFUSED, abort)
- **FR-008**: System MUST track synced files by content hash to avoid duplicate episodes
- **FR-009**: System MUST support group_id parameter for organizing knowledge by type (learning, research)
- **FR-010**: System MUST limit episode body to 5000 characters (server constraint)
- **FR-011**: System MUST limit episode name to 200 characters (server constraint)
- **FR-012**: System MUST parse YAML frontmatter from markdown files for metadata extraction
- **FR-013**: System MUST gracefully degrade when MCP server is unavailable (non-blocking hook execution)
- **FR-014**: System MUST provide --dry-run flag to preview sync operations without making API calls
- **FR-015**: System MUST provide --all flag to force re-sync of all files regardless of sync state
- **FR-016**: System MUST provide --verbose flag for detailed logging of sync operations including errors, warnings, and sync statistics (files processed, succeeded, failed, skipped)
- **FR-017**: System MUST default to neo4j database type if MADEINOZ_KNOWLEDGE_DB is not set
- **FR-018**: System MUST validate MADEINOZ_KNOWLEDGE_DB value and reject unsupported database types

### Key Entities

- **Episode**: A knowledge entry representing a single document/memory, containing name, body, source, metadata, and group_id
- **Sync State**: Persistent tracking of previously synced files with file paths, content hashes, and capture types
- **MCP Session**: A server-side session identified by Mcp-Session-Id header for request routing
- **Memory File**: Markdown file in LEARNING/ or RESEARCH/ directories with optional YAML frontmatter

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Sync operations complete within 15 seconds for batches of 20 files
- **SC-002**: Sync hook does not block session startup when MCP server is unavailable
- **SC-003**: 100% of new memory files are successfully added to knowledge graph on first sync attempt
- **SC-004**: Duplicate content is detected and skipped based on SHA-256 hash comparison
- **SC-005**: Special characters in search queries are properly escaped based on database type (FalkorDB) or passed through (Neo4j)
- **SC-006**: Session initialization succeeds on first attempt when server is healthy
- **SC-007**: Health check returns success within 5 seconds when server is running
- **SC-008**: Sync operations maintain state across multiple runs (incremental sync works)
- **SC-009**: System correctly switches sanitization behavior when MADEINOZ_KNOWLEDGE_DB changes between neo4j and falkorodb

## Assumptions

1. MCP server runs at http://localhost:8000/mcp/ by default (configurable via MADEINOZ_KNOWLEDGE_MCP_URL)
2. PAI Memory System directory is at ~/.claude/MEMORY/ (standard PAI installation)
3. Neo4j or FalkorDB backend is already running and accessible via Docker/Podman containers
4. Database backend type is configured via MADEINOZ_KNOWLEDGE_DB environment variable (valid values: neo4j, falkorodb)
5. Default database type is neo4j if MADEINOZ_KNOWLEDGE_DB is not set
6. YAML frontmatter uses standard PAI v7.0 schema (rating, source, tags, capture_type, timestamp)
7. Users have read/write permissions for ~/.claude/MEMORY/ and sync state files
8. Network latency between hook and MCP server is typically under 100ms (local environment)
9. Episode body content over 5000 characters is truncated (not an error)
10. Content hash (SHA-256) provides sufficient deduplication for text-based memory files
11. SSE response format uses "data: " prefix for JSON content (standard Server-Sent Events)
12. JSON-RPC 2.0 protocol version "2024-11-05" is supported by the MCP server
13. FalkorDB uses RediSearch/Lucene syntax requiring special character escaping
14. Neo4j uses native Cypher queries which do not require Lucene escaping
