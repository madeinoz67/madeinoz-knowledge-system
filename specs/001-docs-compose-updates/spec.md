# Feature Specification: Documentation and Docker Compose Updates

**Feature Branch**: `001-docs-compose-updates`
**Created**: 2026-01-26
**Status**: Draft
**Input**: User description: "document review to remove the lucene sections and improve benchmark sections, also minor fixes for docker compose files to point to ghcr.io/madeinoz67/madeinoz-knowledge-system:latest"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Documentation Cleanup (Priority: P1)

As a developer reading the documentation, I need accurate and relevant information without obsolete backend-specific implementation details so that I can understand and use the system effectively.

**Why this priority**: Documentation is the first touchpoint for users. Removing confusing or obsolete Lucene-specific content improves comprehension and reduces support burden.

**Independent Test**: Can be fully tested by reviewing all documentation files for Lucene references and verifying they are removed or updated with accurate backend-agnostic information.

**Acceptance Scenarios**:

1. **Given** documentation contains Lucene-specific query syntax examples, **When** developer reads the docs, **Then** only backend-agnostic query examples are present
2. **Given** CLAUDE.md or README contains Lucene escaping details, **When** developer reviews configuration guidance, **Then** only relevant backend information is documented
3. **Given** code comments reference Lucene sanitization, **When** developer reads inline documentation, **Then** comments accurately reflect current implementation without obsolete details

---

### User Story 2 - Improved Benchmark Documentation (Priority: P2)

As a developer or operator evaluating system performance, I need clear and comprehensive benchmark information so that I can understand performance characteristics and make informed decisions.

**Why this priority**: Benchmarks help users set realistic expectations and troubleshoot performance issues. Improved clarity increases confidence in the system.

**Independent Test**: Can be tested by reviewing benchmark sections for completeness, measurable metrics, test conditions, and reproducibility instructions.

**Acceptance Scenarios**:

1. **Given** benchmark section exists in documentation, **When** user reads performance information, **Then** clear metrics with units (operations/sec, latency percentiles) are provided with real benchmarks prominently at top
2. **Given** benchmark results are documented, **When** user wants to reproduce tests, **Then** test conditions (data size, query types, hardware specs) are clearly documented
3. **Given** multiple backend options exist, **When** user compares performance, **Then** benchmarks for both Neo4j and FalkorDB backends are included
4. **Given** user evaluating LLM model options, **When** reading benchmark documentation, **Then** clear recommendations for best models (price/performance) and models to avoid are provided

---

### User Story 3 - Docker Compose Image Updates (Priority: P1)

As a developer deploying the system using Docker Compose, I need the compose files to reference the correct container image location so that I can successfully deploy the system without manual configuration changes.

**Why this priority**: Incorrect image references cause deployment failures immediately. This is a critical blocker for new users.

**Independent Test**: Can be tested by running docker-compose up with each compose file and verifying the correct image is pulled from ghcr.io.

**Acceptance Scenarios**:

1. **Given** docker-compose-neo4j.yml file, **When** user runs docker-compose up, **Then** system pulls image from ghcr.io/madeinoz67/madeinoz-knowledge-system:latest
2. **Given** docker-compose-falkordb.yml file, **When** user runs docker-compose up, **Then** system pulls image from ghcr.io/madeinoz67/madeinoz-knowledge-system:latest
3. **Given** podman-compose files exist, **When** user runs podman-compose up, **Then** system pulls correct image from ghcr.io

---

### Edge Cases

- **Lucene explanatory references**: Remove ALL Lucene references without exception, including technical explanations about FalkorDB internals. Prioritize documentation simplicity.
- **Benchmark documentation structure**: Reorganize existing benchmark information for clarity - place real performance benchmarks at top of page, testing results at bottom. Include clear guidance on best LLM models for price/performance and models to avoid.
- **Image reference scope**: Update ALL image references in compose files, scripts, and documentation - comprehensive consistency check required.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Documentation MUST NOT contain ANY Lucene references, including query syntax examples and technical explanations
- **FR-002**: Documentation MUST NOT reference lucene.ts or Lucene sanitization as a general feature
- **FR-003**: Benchmark sections MUST include measurable performance metrics with units (queries/sec, milliseconds, etc.)
- **FR-004**: Benchmark sections MUST document test conditions (data volume, query complexity, hardware specifications) AND provide clear guidance on best LLM models for price/performance with explicit recommendations for models to avoid
- **FR-005**: All Docker Compose files, scripts, and documentation MUST reference ghcr.io/madeinoz67/madeinoz-knowledge-system:latest for ALL container image references
- **FR-006**: Updated documentation MUST maintain accuracy about backend-specific differences where relevant
- **FR-007**: Benchmark documentation MUST include comparison between Neo4j and FalkorDB backends if both are supported
- **FR-008**: Benchmark sections MUST be reorganized with real performance benchmarks at top of page and testing results at bottom
- **FR-009**: Documentation MUST include explicit LLM model recommendations section identifying best models for price/performance ratio AND models to avoid with clear reasoning for each

### Key Entities

- **Documentation Files**: README.md, CLAUDE.md, docs/ directory, inline code comments
- **Docker Compose Files**: docker-compose-neo4j.yml, docker-compose-falkordb.yml, podman-compose-neo4j.yml, podman-compose-falkordb.yml
- **Scripts**: Shell scripts, CI/CD workflows, automation tools that reference container images
- **Benchmark Data**: Performance metrics, test conditions, hardware specifications, backend comparisons, LLM model recommendations (best for price/performance, models to avoid)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero references to Lucene in ANY documentation sections (complete removal without exception)
- **SC-002**: Benchmark sections include at least 3 measurable metrics (e.g., throughput, latency p50/p95/p99, concurrent operations) with real benchmarks prominently placed at top
- **SC-002a**: Documentation clearly identifies best LLM models for price/performance and explicitly lists models to avoid with reasoning
- **SC-003**: All Docker Compose files, scripts, and documentation consistently reference ghcr.io/madeinoz67/madeinoz-knowledge-system:latest
- **SC-004**: Documentation review by developer unfamiliar with project requires zero clarification questions about Lucene or benchmarks
- **SC-005**: Docker Compose deployment succeeds on first attempt without image reference errors

## Scope *(mandatory)*

### In Scope

- Removal or updating of Lucene-specific content in documentation
- Reorganization of benchmark sections (real performance benchmarks top, testing results bottom)
- Addition of LLM model recommendations (best for price/performance, models to avoid with reasoning)
- Update of image references in all Docker Compose files, Podman Compose files, scripts, and documentation
- Comprehensive review of all container image references across the codebase
- Verification of documentation accuracy after changes

### Out of Scope

- Running new benchmark tests (only improving existing benchmark documentation)
- Code changes to lucene.ts or backend query handling
- Changes to MCP server implementation or query execution
- Documentation restructuring beyond the specified sections
- Translation of documentation to other languages

## Assumptions *(mandatory)*

1. ALL Lucene content will be removed from documentation without exception, prioritizing simplicity over technical accuracy
2. Benchmark improvements focus on reorganizing existing information for clarity (real performance benchmarks top, testing results bottom) and adding LLM model recommendations (best models, models to avoid), not generating new benchmark data
3. Container image ghcr.io/madeinoz67/madeinoz-knowledge-system:latest exists and is accessible
4. Docker Compose file structure and service definitions remain unchanged except for image references
5. Standard documentation formats (Markdown) are maintained

## Dependencies

- Access to GitHub Container Registry for image verification
- Existing benchmark data or agreement that "benchmarks pending" is acceptable
- Understanding of which Lucene references are obsolete vs. technically accurate

## Clarifications

### Session 2026-01-26

- Q: How should technically accurate explanatory references to Lucene be handled in documentation? → A: Remove ALL Lucene references including explanatory context - prioritize simplicity over technical accuracy
- Q: How should benchmark documentation be handled when actual performance data doesn't exist yet? → A: Reorganize existing information for clarity (real benchmarks bottom, testing results top)
- Q: Should Docker Compose files be checked for image references beyond the main madeinoz-knowledge-system service? → A: Update all image references in all compose files, scripts and documentation
- Q: What level of detail and completeness is required for test condition documentation in the reorganized benchmark sections? → A: Provide real benchmarks at top and testing results at bottom, make clear the best models on price and performance, and what models not to use

## Open Questions

None - all requirements are clear and testable with reasonable defaults applied.
