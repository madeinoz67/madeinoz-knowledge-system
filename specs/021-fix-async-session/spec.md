# Feature Specification: Fix AsyncSession Compatibility in Graph Traversal

**Feature Branch**: `021-fix-async-session`
**Created**: 2026-02-05
**Status**: Draft
**Related Issue**: https://github.com/madeinoz67/madeinoz-knowledge-system/issues/66
**Input**: User description: "fix https://github.com/madeinoz67/madeinoz-knowledge-system/issues/66 use spec 021-"

## Overview

The `investigate_entity` MCP tool (Feature 020: Investigative Search) fails when performing graph traversal because the `GraphTraversal` class uses synchronous Neo4j session syntax while the MCP server passes it an async driver. This specification defines the fix to make `GraphTraversal` compatible with async Neo4j sessions.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Investigate Entity Connections (Priority: P1)

A user wants to find all entities connected to a specific entity in their knowledge graph, traversing up to 3 hops deep, to understand relationships and discover hidden connections.

**Why this priority**: This is the primary use case for Feature 020 (Investigative Search). Without this fix, the feature is completely non-functional.

**Independent Test**: Can be fully tested by running `investigate "Apollo 11" --depth 2` against the dev knowledge graph and verifying connected entities are returned.

**Acceptance Scenarios**:

1. **Given** a running knowledge system with entities and relationships, **When** a user runs `investigate "Apollo 11" --depth 2`, **Then** the system returns all connected entities up to 2 hops away with their relationship types
2. **Given** an entity name that doesn't exist, **When** a user runs `investigate "NonExistent"`, **Then** the system returns a clear "Entity not found" error message
3. **Given** an investigation request with depth=3, **When** the graph has cycles, **Then** the system detects cycles, prunes duplicate visits, and reports cycle count in metadata

---

### User Story 2 - Filter by Relationship Type (Priority: P2)

A user wants to investigate entity connections but only for specific relationship types (e.g., "USES", "OWNS") to reduce noise and focus on relevant connections.

**Why this priority**: Important filtering capability for OSINT/CTI investigations but not required for basic functionality.

**Independent Test**: Can be tested by running `investigate "apt28" --relationship-type "uses" --relationship-type "targets"` and verifying only matching relationships are returned.

**Acceptance Scenarios**:

1. **Given** an entity with multiple relationship types, **When** a user specifies `--relationship-type "USES"`, **Then** only USES relationships are returned in results
2. **Given** an entity with no matching relationship types, **When** a user filters by a specific type, **Then** the system returns empty connections with appropriate metadata

---

### User Story 3 - Investigate Across Multiple Knowledge Groups (Priority: P3)

A user with multiple knowledge graphs (e.g., "main" and "cti") wants to investigate an entity across all groups or specific groups to find connections in different contexts.

**Why this priority**: Advanced use case for power users with multiple knowledge domains. Core functionality works with single group.

**Independent Test**: Can be tested by running investigate command against a system with multiple groups and verifying cross-group connections are found.

**Acceptance Scenarios**:

1. **Given** multiple knowledge groups with related entities, **When** a user investigates without group filter, **Then** connections from all groups are returned
2. **Given** an entity exists in multiple groups, **When** a user specifies `--group-ids "main"`, **Then** only connections from the "main" group are returned

---

### Edge Cases

- What happens when the starting entity has no connections (isolated node)?
- How does the system handle when max_depth exceeds the maximum allowed (3)?
- What happens when the Neo4j driver is unavailable or connection fails mid-traversal?
- How does the system handle entities with special characters in names (e.g., "+1-555-0199")?
- What happens when cycle detection exceeds internal tracking limits?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST perform graph traversal starting from a matched entity up to 3 hops deep
- **FR-002**: System MUST return connected entities with their names, types, UUIDs, and relationship information
- **FR-003**: System MUST support filtering by relationship types to reduce result noise
- **FR-004**: System MUST detect and handle cycles in the graph to prevent infinite loops
- **FR-005**: System MUST support both Neo4j and FalkorDB backends with equivalent functionality
- **FR-006**: System MUST work with async Neo4j driver sessions (not just synchronous sessions)
- **FR-007**: System MUST validate that max_depth is between 1 and 3, returning error if outside range
- **FR-008**: System MUST return clear error when starting entity is not found in the graph
- **FR-009**: System MUST include metadata about traversal (depth explored, cycles detected, query duration)
- **FR-010**: System MUST warn when connection count exceeds 500 to alert user to broad results

### Key Entities

- **Entity**: Represents a node in the knowledge graph with attributes (uuid, name, labels, summary, created_at, group_id)
- **Connection**: Represents a relationship between entities with type, direction, and hop distance
- **Traversal Metadata**: Information about the graph traversal operation (depth explored, cycles detected, connections returned)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `investigate` CLI command completes successfully without AsyncSession errors
- **SC-002**: Graph traversal returns results within 5 seconds for depth=2 queries on graphs with 1000 entities
- **SC-003**: Cycle detection prevents infinite loops and accurately reports cycle count in metadata
- **SC-004**: 100% of investigate requests with valid entity names return either connections or "not found" (no crashes)
- **SC-005**: Both Neo4j and FalkorDB backends produce equivalent result structures

## Assumptions

1. The async Neo4j driver is the correct choice for the MCP server architecture (async/await pattern)
2. The GraphTraversal class should support both sync and async sessions for backward compatibility
3. FalkorDB (Redis) backend also needs async support in the future
4. Maximum depth of 3 hops is sufficient for investigative search use cases
5. Connection count threshold of 500 is appropriate for warning users about broad results

## Dependencies

- Neo4j Python driver with async session support
- Existing MCP server infrastructure (graphiti_service, client.driver)
- Feature 020 specification and test suite
- Graph traversal utilities in `docker/patches/utils/graph_traversal.py`

## Out of Scope

This fix does NOT include:
- Performance optimization beyond making the feature functional
- New traversal algorithms or query patterns
- Changes to the FalkorDB implementation (only Neo4j async fix)
- UI/UX improvements to the CLI output format
