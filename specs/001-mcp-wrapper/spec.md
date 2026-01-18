# Feature Specification: MCP Wrapper for Token Savings

**Feature Branch**: `001-mcp-wrapper`
**Created**: 2026-01-18
**Status**: Draft
**Input**: User description: "I want to add a wrapper to the mcp installed by this pack, with changes to the skill and workflows that will prefer to use the wrapper over direct mcp calls this is purely to save tokens so will need to validate token savings in the testing"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reduced Token Consumption for Knowledge Operations (Priority: P1)

As a user of the Madeinoz Knowledge System, I want my knowledge operations (capture, search, retrieve) to consume fewer tokens so that I can perform more operations within my context window limits and reduce API costs.

**Why this priority**: This is the core value proposition - token savings directly enable more productive sessions and reduce costs. Without this, the feature has no purpose.

**Independent Test**: Can be fully tested by measuring token counts before and after wrapper implementation for identical operations, validating that savings meet the target threshold.

**Acceptance Scenarios**:

1. **Given** a user captures knowledge using natural language, **When** the operation completes, **Then** the total tokens consumed are measurably lower than a direct operation with equivalent functionality.
2. **Given** a user searches their knowledge graph, **When** results are returned, **Then** the response format uses fewer tokens than the raw format while preserving all essential information.
3. **Given** a user retrieves recent episodes, **When** the data is returned, **Then** the output is formatted efficiently without redundant metadata.

---

### User Story 2 - Transparent Wrapper Operation (Priority: P2)

As a user, I want the wrapper to operate transparently so that I don't need to change how I interact with the knowledge system - it should just work more efficiently.

**Why this priority**: Users should not need to learn new commands or change their habits. The wrapper must be a drop-in improvement, not a new interface.

**Independent Test**: Can be tested by running the same natural language commands before and after wrapper implementation and verifying identical user-facing behavior.

**Acceptance Scenarios**:

1. **Given** existing knowledge capture commands work, **When** the wrapper is enabled, **Then** the same commands continue to work without modification.
2. **Given** existing search commands return results, **When** the wrapper is enabled, **Then** the same commands return equivalent information.
3. **Given** an operation fails, **When** the wrapper is handling the request, **Then** error messages are as clear and actionable as direct operations.

---

### User Story 3 - Measurable Token Savings Validation (Priority: P3)

As a system maintainer, I want to validate that the wrapper actually saves tokens so that I can confirm the feature delivers its promised value and identify optimization opportunities.

**Why this priority**: Without measurement, we cannot prove value or identify further optimization opportunities. This enables data-driven decisions about the feature's effectiveness.

**Independent Test**: Can be tested by running a benchmark suite that compares token usage between wrapped and direct operations, producing a report with savings percentages.

**Acceptance Scenarios**:

1. **Given** a test suite for knowledge operations exists, **When** run against the wrapper, **Then** a report is generated showing token counts for each operation type.
2. **Given** the token measurement report, **When** compared to baseline direct operations, **Then** savings percentages are clearly displayed for each operation category.
3. **Given** an operation type shows minimal or no savings, **When** reviewing the report, **Then** that operation is flagged for potential optimization or exclusion from wrapping.

---

### Edge Cases

- What happens when the wrapper fails to parse a response correctly? (Should fall back to direct operation gracefully)
- How does the wrapper handle very large knowledge graph responses that exceed normal limits?
- What happens when the underlying MCP server returns an error? (Wrapper should pass through errors without masking them)
- How are operations with special characters (hyphenated identifiers) handled through the wrapper?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a wrapper layer between skill/workflow operations and the MCP server
- **FR-002**: Wrapper MUST reduce token consumption compared to direct MCP operations for typical use cases
- **FR-003**: Wrapper MUST preserve all functional capabilities of direct MCP operations
- **FR-004**: Skill file MUST be updated to prefer wrapper operations over direct MCP calls
- **FR-005**: All existing workflows MUST be updated to use wrapper when appropriate
- **FR-006**: Wrapper MUST support all existing MCP operations: add_memory, search_nodes, search_memory_facts, get_episodes, delete_episode, delete_entity_edge, clear_graph, get_status
- **FR-007**: System MUST provide a mechanism to measure and compare token usage between wrapped and direct operations
- **FR-008**: Wrapper MUST handle errors gracefully without masking underlying issues
- **FR-009**: Wrapper MUST work with both Neo4j and FalkorDB backends without modification

### Key Entities

- **Wrapper**: Intermediary layer that transforms MCP operations for token efficiency
- **Token Measurement**: Captured data comparing input/output token counts for operations
- **Operation Result**: Transformed response from MCP that preserves meaning with fewer tokens

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Average token consumption per knowledge capture operation is reduced by at least 25% compared to direct operations
- **SC-002**: Average token consumption per search operation is reduced by at least 30% compared to direct operations
- **SC-003**: All existing test cases pass without modification when wrapper is enabled
- **SC-004**: User-facing behavior remains identical - same inputs produce functionally equivalent outputs
- **SC-005**: Token savings are validated through a benchmark suite producing a measurable report with before/after comparisons
- **SC-006**: No increase in operation failure rate compared to direct operations (≤ baseline error rate)

## Assumptions

- Token savings are achievable primarily through response format optimization (removing redundant metadata, compacting structures)
- The MCP protocol allows for response transformation without losing semantic meaning
- Users will not notice functional differences between wrapped and direct operations
- Token measurement can be performed using standard tooling available in the development environment
- The 25-30% savings targets are reasonable based on observed redundancy in current MCP responses
