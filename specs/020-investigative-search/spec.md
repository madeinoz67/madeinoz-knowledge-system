# Feature Specification: Investigative Search with Connected Entities

**Feature Branch**: `020-investigative-search`
**Created**: 2026-02-04
**Status**: Draft
**Input**: User description: "https://github.com/madeinoz67/madeinoz-knowledge-system/issues/63 include tests and user documentation"

## Overview

This feature adds investigative search capabilities that return entities with their connected relationships and related entities in a single query. This enables AI-driven OSINT/CTI investigation workflows where search results serve as "lead graphs" that can be followed and pivoted to discover related entities without additional lookups.

## Clarifications

### Session 2026-02-04

- Q: Should this be a new command or enhanced existing search? → A: New `investigate` command for clarity, plus `--include-connections` flag on existing `search_nodes` for flexibility
- Q: What should be the default connection depth? → A: 1-hop (direct connections) by default, configurable up to 3-hops to prevent runaway queries
- Q: How should circular relationships be handled? → A: Detect and track visited entities to prevent infinite loops, report cycles to user for awareness

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Investigative Search Returns Connected Entities (Priority: P1)

As an OSINT investigator, I want to search for an entity and see all its direct connections with names in a single query so that I can quickly understand the entity's network without multiple lookups.

**Why this priority**: This is the core value proposition - the entire feature exists to eliminate the need for multiple queries to understand entity relationships.

**Independent Test**: Can be fully tested by searching for an entity with known connections and verifying all related entities are returned with names and relationship types.

**Acceptance Scenarios**:

1. **Given** a knowledge graph with a Phone entity connected to a Person (via OWNED_BY) and an Account (via CONTACTED_VIA), **When** I run `investigate "+1-555-0199"`, **Then** the response includes the Phone entity with both connected entities showing their names, types, and relationship types.
2. **Given** the response from an investigate query, **When** I examine the connections array, **Then** each connection includes the relationship name, source entity name, target entity name, and all UUIDs.
3. **Given** an entity with no connections, **When** I run investigate, **Then** the response includes the entity with an empty connections array (not an error).

---

### User Story 2 - Configurable Connection Depth (Priority: P1)

As a threat intelligence analyst, I want to control how many hops deep the search explores so that I can balance comprehensive analysis against query performance.

**Why this priority**: Depth control is essential - too shallow misses important connections, too deep causes performance issues and overwhelming results.

**Independent Test**: Can be fully tested by searching with different depth values and verifying the correct number of hops are returned.

**Acceptance Scenarios**:

1. **Given** an entity with 3-hop connections (A → B → C → D), **When** I run `investigate --depth 1 "A"`, **Then** only entity B is returned in connections.
2. **Given** the same graph, **When** I run `investigate --depth 2 "A"`, **Then** entities B and C are returned in connections.
3. **Given** the same graph, **When** I run `investigate --depth 3 "A"`, **Then** entities B, C, and D are returned in connections.
4. **Given** a depth value greater than 3, **When** I run investigate, **Then** the system returns an error explaining the maximum depth limit.

---

### User Story 3 - Filterable by Relationship Type (Priority: P2)

As a security researcher, I want to filter connections by relationship type so that I can focus on specific types of relationships (e.g., only OWNED_BY, only USES) without noise from other connections.

**Why this priority**: Filtering improves signal-to-noise ratio for focused investigations but is not required for core functionality.

**Independent Test**: Can be fully tested by searching with relationship filters and verifying only matching relationships are returned.

**Acceptance Scenarios**:

1. **Given** an entity with connections via multiple relationship types (OWNED_BY, CONTACTED_VIA, LOCATED_AT), **When** I run `investigate --relationship-type OWNED_BY "phone"`, **Then** only OWNED_BY connections are returned.
2. **Given** multiple relationship types to filter, **When** I run `investigate --relationship-type OWNED_BY --relationship-type USES "threat-actor"`, **Then** connections matching either type are returned.
3. **Given** a filter for a non-existent relationship type, **When** I run investigate, **Then** the response returns the entity with an empty connections array (not an error).

---

### User Story 4 - Works with Custom Entity Types (Priority: P1)

As a CTI analyst using custom entity types (ThreatActor, Indicator, Vulnerability), I want investigate search to work with all entity types so that my CTI ontology is fully supported.

**Why this priority**: Custom entity types are a primary use case for OSINT/CTI workflows - the feature must support them from day one.

**Independent Test**: Can be fully tested by creating custom entity types and verifying investigate search returns their connections correctly.

**Acceptance Scenarios**:

1. **Given** a knowledge graph with custom entity types (ThreatActor, Malware, Vulnerability) and custom relationships (USES, EXPLOITS), **When** I run `investigate "APT28"`, **Then** the response correctly includes all connected entities with their custom types and relationships.
2. **Given** a ThreatActor entity connected to Malware via USES and to a Campaign via ATTRIBUTED_TO, **When** I search for the ThreatActor, **Then** all connections are returned with accurate custom relationship types.
3. **Given** mixed standard and custom entity types, **When** I run investigate, **Then** all connections are returned regardless of entity type origin.

---

### User Story 5 - AI-Friendly JSON Structure (Priority: P1)

As an AI agent using the knowledge system programmatically, I want the investigate response to include all entity names alongside UUIDs so that I can display and follow connections without additional lookup queries.

**Why this priority**: The entire feature exists to support AI-driven investigation - without names in the response, AI requires multiple round-trips which defeats the purpose.

**Independent Test**: Can be fully tested by programmatically calling investigate and verifying entity names are present without requiring additional queries.

**Acceptance Scenarios**:

1. **Given** an investigate query response, **When** I parse the JSON, **Then** each entity includes name, type, and UUID without requiring a separate lookup.
2. **Given** a connection in the response, **When** I examine it, **Then** both source and target entities include their names, types, and UUIDs.
3. **Given** an AI agent processing investigate results, **When** it displays the entity graph, **Then** no additional queries are needed to show entity names or types.

---

### User Story 6 - Cycle Detection and Handling (Priority: P2)

As an investigator, I want the system to detect and handle circular relationships so that my queries complete successfully and I'm aware of cycles in the data.

**Why this priority**: Cycles are common in real-world data (A employs B, B employs A via contracts) - without cycle handling, queries can loop infinitely or produce duplicate results.

**Independent Test**: Can be fully tested by creating circular relationships and verifying the query completes with appropriate cycle reporting.

**Acceptance Scenarios**:

1. **Given** entities with a circular relationship (A → B → C → A), **When** I run `investigate --depth 5 "A"`, **Then** the query completes without hanging and returns entities without duplicates.
2. **Given** a cycle is detected, **When** I examine the response, **Then** a metadata field indicates the number of cycles detected and pruned.
3. **Given** self-referential relationships (A → A), **When** I run investigate, **Then** the self-reference is included once without causing infinite loops.

---

### User Story 7 - CLI and MCP Tool Parity (Priority: P1)

As a user, I want to access investigative search from both the CLI and MCP tools so that I can use the same capability whether I'm working interactively or via AI integration.

**Why this priority**: The feature must work in both contexts - CLI-only would limit AI utility, MCP-only would limit human utility.

**Independent Test**: Can be fully tested by running the same investigate query via CLI and MCP and verifying identical results.

**Acceptance Scenarios**:

1. **Given** the knowledge CLI installed, **When** I run `knowledge investigate "query"`, **Then** the command returns connected entities with names.
2. **Given** the MCP server running, **When** I call the investigate MCP tool, **Then** it returns the same results as the CLI for the same query.
3. **Given** both CLI and MCP interfaces, **When** I pass the same parameters (depth, filters), **Then** both produce identical output structures.

---

### Edge Cases

- What happens when an entity has thousands of connections? → Return results with a warning and suggest using filters or reducing depth
- How does the system handle deleted entities in relationships? → Skip deleted entities, include metadata showing skipped count
- What happens when the search query matches no entities? → Return empty results with a clear message, not an error
- How does the system handle very long entity names in responses? → Truncate with ellipsis after 200 characters, include full name in a separate field if needed
- What happens when connection depth exceeds practical limits (e.g., 10 hops)? → Reject with error message explaining maximum depth limit

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an `investigate` command that returns entities with their connected relationships
- **FR-002**: System MUST include entity names, types, and UUIDs for all entities in investigate responses
- **FR-003**: System MUST support configurable connection depth from 1 to 3 hops
- **FR-004**: System MUST provide default depth of 1 (direct connections only)
- **FR-005**: System MUST support filtering connections by relationship type
- **FR-006**: System MUST support multiple relationship type filters in a single query
- **FR-007**: System MUST work with all custom entity types (Phone, Account, ThreatActor, Malware, etc.)
- **FR-008**: System MUST detect and handle circular relationships without infinite loops
- **FR-009**: System MUST report detected cycles in response metadata
- **FR-010**: System MUST provide both CLI command and MCP tool for investigative search
- **FR-011**: System MUST return consistent JSON structure between CLI and MCP interfaces
- **FR-012**: System MUST include comprehensive tests for investigative search functionality
- **FR-013**: System MUST include user documentation with examples for OSINT/CTI workflows

### Key Entities

- **Investigation Result**: The response structure containing the primary entity and its connections
- **Connection**: A relationship edge containing source entity, target entity, relationship type, and direction
- **Connection Graph**: The traversed entity network including the primary entity and all connected entities up to the specified depth
- **Cycle Metadata**: Information about detected circular relationships including count and affected entities

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Investigative search completes for entities with up to 100 direct connections in under 2 seconds
- **SC-002**: Users can retrieve entity connections without additional lookup queries
- **SC-003**: All custom entity types (Phone, Account, ThreatActor, etc.) are supported in investigative search
- **SC-004**: 100% of investigative search functionality is covered by automated tests
- **SC-005**: Documentation includes at least 3 complete OSINT/CTI workflow examples
- **SC-006**: CLI and MCP tools return identical results for the same investigate query
- **SC-007**: Queries with circular relationships complete successfully without hanging

## Assumptions

1. The knowledge graph database (Neo4j/FalkorDB) supports efficient graph traversal queries
2. Custom entity types from Feature 019 (OSINT/CTI Ontology Support) will be available
3. Maximum depth of 3 hops balances comprehensiveness with performance for typical investigations
4. Entity names are always available and non-null (UUID-only entities are not a valid use case)
5. Relationship directionality (source → target) is preserved in responses
6. CLI output uses JSON format by default for programmatic access
7. The MCP tool uses the same underlying query logic as the CLI command

## Dependencies

- Feature 019 (OSINT/CTI Ontology Support) - for custom entity type support
- Existing knowledge graph infrastructure (Neo4j/FalkorDB, Graphiti MCP server)
- Existing CLI framework for knowledge operations
