# Feature Specification: Fix Environment File Loading

**Feature Branch**: `004-fix-env-file-loading`
**Created**: 2026-01-20
**Status**: Draft
**Input**: User description: "fix https://github.com/madeinoz67/madeinoz-knowledge-system/issues/4 and update relevant documentatation relating to the fix"

## Clarifications

### Session 2026-01-20

- Q: What is the root cause of env_file loading failure? → A: Path resolution works, but variables are not being mapped correctly to container environment variables (Docker Compose variable expansion syntax may not be resolving MADEINOZ_KNOWLEDGE_* prefixes correctly)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Docker Compose Loads Environment Variables (Priority: P1)

As a Knowledge System user, I want Docker Compose to automatically load my API keys and configuration from my PAI `.env` file using the `env_file` directive, so that I don't need to manually copy keys into docker-compose files or export environment variables before starting containers.

**Why this priority**: This is the core functionality issue. The `env_file` directive should work as documented but currently fails, blocking LLM and embedder functionality.

**Independent Test**: Can be fully tested by (1) configuring `~/.claude/.env` with API keys, (2) running `docker compose -f src/server/docker-compose-neo4j.yml up -d`, (3) checking container logs to confirm no "variable not set" warnings, and (4) verifying MCP server logs show configured LLM/embedder clients. Delivers value by enabling automatic configuration without manual intervention.

**Acceptance Scenarios**:

1. **Given** the `~/.claude/.env` file contains `MADEINOZ_KNOWLEDGE_OPENAI_API_KEY=sk-or-v1-...`, **When** Docker Compose starts the graphiti-mcp service with `env_file: ${PAI_DIR:-~/.claude}/.env`, **Then** the `OPENAI_API_KEY` environment variable is set inside the container with the correct value
2. **Given** the `.env` file contains `MADEINOZ_KNOWLEDGE_MODEL_NAME=google/gemini-2.0-flash-001`, **When** the container starts, **Then** the `MODEL_NAME` variable is set to `google/gemini-2.0-flash-001` inside the container
3. **Given** the `.env` file does not exist, **When** Docker Compose starts, **Then** the services should use default values from the docker-compose environment section (e.g., `MODEL_NAME=${MADEINOZ_KNOWLEDGE_MODEL_NAME:-google/gemini-2.0-flash-001}`)
4. **Given** both `PAI_DIR` environment variable is set and `.env` file exists at `$PAI_DIR/.env`, **When** Docker Compose starts, **Then** the `.env` file from `PAI_DIR` is loaded (takes precedence over `~/.claude/.env`)

---

### User Story 2 - Clear Documentation of Environment Configuration (Priority: P2)

As a Knowledge System user, I want clear documentation explaining how environment variables are loaded from `.env` files, so that I can troubleshoot configuration issues and understand where to place my API keys.

**Why this priority**: Good documentation prevents user confusion and reduces support burden. This is secondary to fixing the actual bug but important for long-term maintainability.

**Independent Test**: Can be fully tested by (1) reviewing documentation for clarity and completeness, (2) following documentation instructions to configure environment, and (3) verifying the documented behavior matches actual system behavior. Delivers value by enabling self-service troubleshooting.

**Acceptance Scenarios**:

1. **Given** a new user reads the installation documentation, **When** they reach the environment configuration section, **Then** they understand exactly where to place their `.env` file and what variables to configure
2. **Given** a user encounters "variable not set" warnings, **When** they check the troubleshooting documentation, **Then** they find clear steps to diagnose and fix the issue
3. **Given** the documentation mentions `env_file` directive, **When** a user reads it, **Then** they understand how variable expansion (`${PAI_DIR:-~/.claude}`) works
4. **Given** a user is using a specific container runtime (Docker vs Podman) or backend (Neo4j vs FalkorDB), **When** they read the documentation, **Then** they understand which compose file to use and that all compose files expect the same `.env` location

---

### User Story 3 - Validation and Error Messaging (Priority: P3)

As a Knowledge System user, I want clear error messages when environment configuration is invalid or missing, so that I can quickly identify and fix configuration issues without digging through container logs.

**Why this priority**: Error messaging improves user experience but is not critical to core functionality. Users can still check logs if error messages are unclear.

**Independent Test**: Can be fully tested by (1) intentionally misconfiguring the `.env` file (e.g., invalid format), (2) starting Docker Compose services, and (3) verifying that helpful error messages appear in logs or console output. Delivers value by reducing debugging time.

**Acceptance Scenarios**:

1. **Given** the `.env` file has malformed syntax (e.g., quotes around values), **When** Docker Compose attempts to load variables, **Then** a clear warning message indicates the syntax issue
2. **Given** required API keys are missing from `.env`, **When** the MCP server starts, **Then** a helpful error message indicates which keys are missing and how to configure them
3. **Given** the `.env` file path is incorrect, **When** Docker Compose starts, **Then** the error message indicates the expected file location

---

### Edge Cases

- What happens when `PAI_DIR` environment variable points to a non-existent directory?
- How does system handle `.env` file with Windows-style line endings (CRLF) on macOS/Linux?
- What occurs when `.env` file has incorrect permissions (not readable by Docker daemon)?
- How does system handle environment variables with spaces or special characters in values?
- What happens when different docker-compose files (Neo4j vs FalkorDB vs Podman) have inconsistent `env_file` configurations?
- What happens when a user needs Neo4j backend with Podman runtime (podman-compose-neo4j.yml missing)?
- What occurs when compose files are renamed (docker-compose.yml → docker-compose-falkordb.yml) and existing references break?
- How does system behave when `.env` file is empty (0 bytes)?
- What occurs when `.env` file contains Unicode characters or multi-byte values?
- How does system handle very long environment variable values (>4096 characters)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Docker Compose `env_file` directive MUST successfully load environment variables from the path specified by `${PAI_DIR:-~/.claude}/.env` variable expansion
- **FR-002**: Environment variables loaded from `.env` file MUST be accessible inside Docker containers using the variable names specified in docker-compose `environment` section
- **FR-003**: Variable expansion syntax `${PAI_DIR:-~/.claude}` MUST correctly resolve to `$PAI_DIR/.env` if `PAI_DIR` is set, or `~/.claude/.env` if `PAI_DIR` is not set
- **FR-004**: Docker Compose MUST parse `.env` file in standard KEY=VALUE format without requiring quotes around values
- **FR-005**: If `.env` file does not exist at the specified path, services MUST start using default values from docker-compose `environment` section (e.g., `${VAR:-default}`)
- **FR-006**: Docker Compose MUST correctly expand variable references like `${MADEINOZ_KNOWLEDGE_OPENAI_API_KEY}` when they appear in the `environment` section of docker-compose files
- **FR-007**: System MUST support loading environment variables for both Neo4j (`docker-compose-neo4j.yml`) and FalkorDB (`docker-compose.yml`) backends
- **FR-008**: Documentation MUST clearly explain where to place `.env` file and how `env_file` directive works
- **FR-009**: Documentation MUST include troubleshooting steps for "variable not set" warnings
- **FR-010**: Documentation MUST explain the difference between container environment variables and host environment variables
- **FR-011**: System MUST provide clear error messages when `.env` file has invalid format or permissions
- **FR-012**: Configuration validation MUST check that required API keys are present before starting services
- **FR-013**: System MUST handle both Unix (`\n`) and Windows (`\r\n`) line endings in `.env` file
- **FR-014**: All docker-compose files in the repository MUST be reviewed and updated for consistent `env_file` handling, including any Podman-specific, Neo4j, FalkorDB, or other backend-specific variants
- **FR-015**: All docker-compose files MUST use consistent variable expansion syntax and `env_file` path conventions to ensure configuration works across different container runtimes (Docker, Podman) and database backends
- **FR-016**: A `podman-compose-neo4j.yml` file MUST be created to provide Neo4j backend support for Podman users (parity with docker-compose-neo4j.yml for Docker users)
- **FR-017**: Compose file names MUST clearly indicate their database backend: existing `docker-compose.yml` and `podman-compose.yml` MUST be renamed to `docker-compose-falkordb.yml` and `podman-compose-falkordb.yml` respectively, matching the naming convention used by `docker-compose-neo4j.yml`

### Key Entities

- **Environment File**: Plain text configuration file at `~/.claude/.env` (or `$PAI_DIR/.env`) containing KEY=VALUE pairs
- **Docker Compose Service**: Container service definition with `env_file` directive and `environment` section
- **Environment Variable**: Configuration variable (e.g., `MADEINOZ_KNOWLEDGE_OPENAI_API_KEY`) loaded from `.env` and mapped to container variable name (e.g., `OPENAI_API_KEY`)
- **Default Value**: Fallback value specified in docker-compose using `${VAR:-default}` syntax

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can start Docker Compose services with their configured API keys loaded automatically from `.env` file 100% of the time when `.env` exists at expected path
- **SC-002**: No "variable not set. Defaulting to a blank string" warnings appear in container logs when `.env` file is properly configured
- **SC-003**: Users can successfully start containers within 30 seconds of running docker-compose up command (measures time to load env and start services)
- **SC-004**: Documentation troubleshooting guide resolves environment configuration issues for 90% of users without requiring additional support
- **SC-005**: Variable expansion (`${PAI_DIR:-~/.claude}`) correctly resolves to appropriate path in both scenarios (PAI_DIR set and unset)
- **SC-006**: System gracefully handles missing `.env` file by using defaults, preventing container startup failures

## Assumptions

1. User has Docker Compose v2.x or later installed
2. User is running macOS, Linux, or Windows with WSL2 (standard Docker environments)
3. `.env` file follows standard KEY=VALUE format (no quotes around values, one variable per line)
4. `PAI_DIR` environment variable, if set, points to a valid directory path
5. Docker daemon has read permissions for the user's home directory
6. User has API keys for at least one LLM provider (OpenAI, Anthropic, Google, Groq, or Ollama)
7. Services should not fail to start if `.env` file is missing (use defaults)
8. Variable expansion syntax is supported by Docker Compose version in use
9. `.env` file location at `~/.claude/.env` is standard PAI configuration location
10. Container environment variables take precedence over `.env` file values when both are specified
11. Docker Compose processes `env_file` directive before evaluating `environment` section variable expansion
12. Both docker-compose files use the same `.env` file location for consistency
13. All compose files (Docker, Podman, Neo4j, FalkorDB) will be reviewed for consistent `env_file` configuration as part of this fix
14. A new podman-compose-neo4j.yml file will be created to provide Neo4j + Podman support (currently missing)
15. Existing compose files will be renamed for clarity: docker-compose.yml → docker-compose-falkordb.yml, podman-compose.yml → podman-compose-falkordb.yml (breaking change requiring reference updates in code and documentation)
