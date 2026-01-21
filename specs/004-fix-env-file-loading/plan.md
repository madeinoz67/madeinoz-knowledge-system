# Implementation Plan: Fix Environment File Loading

**Branch**: `004-fix-env-file-loading` | **Date**: 2026-01-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-fix-env-file-loading/spec.md`

## Summary

Fix critical bug where Docker Compose `env_file` directive with variable expansion `${PAI_DIR:-~/.claude}/.env` is not loading environment variables correctly into containers. Variables loaded from `.env` are not being mapped to container environment variables in the `environment` section, causing "variable not set" warnings and blocking LLM/embedder functionality.

**Technical Approach**: Review and fix all docker-compose files (docker-compose.yml, docker-compose-neo4j.yml, podman-compose.yml) to ensure consistent `env_file` path with fallback, and verify environment variable expansion syntax works correctly.

## Technical Context

**Language/Version**: YAML (Docker/Podman Compose v2.x)
**Primary Dependencies**: Docker Compose v2.x or Podman Compose
**Storage**: N/A (configuration files only)
**Testing**: Manual verification with container startup and log inspection
**Target Platform**: Linux, macOS, Windows with WSL2 (standard container environments)
**Project Type**: Configuration/infrastructure (docker-compose files)
**Performance Goals**: <30 second container startup time
**Constraints**: Must maintain backward compatibility with PAI .env file location convention
**Scale/Scope**: 4 compose files (docker-compose.yml, docker-compose-neo4j.yml, podman-compose.yml, and new podman-compose-neo4j.yml)

### Key Technical Issues Identified

1. **Missing compose file**:
   - `podman-compose-neo4j.yml` does not exist (Neo4j + Podman users have no compose file)
   - Must be created for parity with Docker variants

2. **Unclear compose file naming**:
   - `docker-compose.yml` and `podman-compose.yml` don't indicate backend (FalkorDB)
   - Should be renamed to `docker-compose-falkordb.yml` and `podman-compose-falkordb.yml`
   - This is a BREAKING CHANGE - all references in code and documentation must be updated

3. **Inconsistent `env_file` paths**:
   - `docker-compose.yml` and `docker-compose-neo4j.yml`: `${PAI_DIR:-~/.claude}/.env` (has fallback)
   - `podman-compose.yml`: `${PAI_DIR}/.env` (NO fallback - will fail if PAI_DIR unset)

4. **Variable expansion in `environment` section**:
   - Variables like `${MADEINOZ_KNOWLEDGE_OPENAI_API_KEY}` may not expand correctly
   - Docker Compose processes `env_file` before evaluating `environment` section
   - Need to verify cross-reference between loaded variables and environment mappings

5. **Documentation gaps**:
   - No clear explanation of how `env_file` directive works
   - Missing troubleshooting for "variable not set" warnings
   - No coverage of different compose files for different backends
   - No guidance on which compose file to use (Docker vs Podman, Neo4j vs FalkorDB)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Container-First Architecture

**Status**: ✅ PASS

**Analysis**:
- All compose files already use container orchestration (docker-compose/podman-compose)
- Network isolation via `madeinoz-knowledge-net` already configured
- Health checks already implemented
- Persistent volumes already configured

**Impact**: This fix maintains container-first architecture. No new containers or services added.

### II. Graph-Centric Design

**Status**: ✅ PASS

**Analysis**:
- No changes to knowledge graph storage or retrieval
- No changes to entity extraction or relationship mapping
- Fix only affects configuration loading

**Impact**: Graph-centric design preserved. No impact on graph operations.

### III. Zero-Friction Knowledge Capture

**Status**: ✅ PASS (Fix IMPROVES this principle)

**Analysis**:
- Current bug: Users must manually set environment variables or copy keys into compose files
- Fixed state: Automatic configuration from PAI `.env` file
- Reduces configuration friction

**Impact**: POSITIVE - This fix ENHANCES zero-friction knowledge capture by making configuration automatic.

### IV. Query Resilience

**Status**: ✅ PASS

**Analysis**:
- No changes to query handling or sanitization
- No changes to special character handling
- Fix only affects configuration loading

**Impact**: Query resilience preserved. No impact on query operations.

### V. Graceful Degradation

**Status**: ⚠️ NEEDS VERIFICATION

**Analysis**:
- Spec requirement FR-005: Services should start with defaults if `.env` missing
- Current compose files use `${VAR:-default}` syntax which provides fallback
- Need to verify graceful degradation works after fix

**Impact**: Must ensure fix doesn't break graceful degradation. Testing required.

### VI. Codanna-First Development

**Status**: ✅ PASS

**Analysis**:
- Codanna CLI already used for codebase exploration
- Document search used to find existing compose files
- No new code being written (configuration only)

**Impact**: Codanna-first development maintained.

**Overall Constitution Check**: ✅ PASS with one verification needed (Graceful Degradation)

## Project Structure

### Documentation (this feature)

```text
specs/004-fix-env-file-loading/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (N/A - no data model)
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (N/A - no API contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

**Affected Files**:

```text
src/server/
├── docker-compose-falkordb.yml     # FalkorDB backend (Docker) - RENAMED from docker-compose.yml
├── docker-compose-neo4j.yml        # Neo4j backend (Docker)
├── podman-compose-falkordb.yml     # FalkorDB backend (Podman) - RENAMED from podman-compose.yml
└── podman-compose-neo4j.yml        # Neo4j backend (Podman) - TO BE CREATED
```

**Documentation Files to Update**:

```text
docs/
├── getting-started/
│   ├── environment-configuration.md    # NEW - detailed env setup guide
│   └── troubleshooting/
│       └── env-file-issues.md          # NEW - env-specific troubleshooting
├── concepts/
│   └── container-configuration.md      # NEW - compose files explained
└── README.md                            # UPDATE - clarify compose file usage
```

**Structure Decision**: Single project structure (infrastructure configuration). No new source code directories. Only modification of existing docker-compose files and addition of documentation.

## Complexity Tracking

> **No Constitution violations to justify**

This fix REDUCES complexity by:
1. Standardizing `env_file` path across all 3 compose files
2. Providing clear documentation for configuration
3. Eliminating need for manual environment variable setup

**No additions to system complexity** - this is a bug fix that simplifies configuration.

## Phase 0: Research Tasks

### Unknowns to Resolve

1. **Docker Compose variable expansion behavior**
   - Question: Does Docker Compose expand `${MADEINOZ_KNOWLEDGE_OPENAI_API_KEY}` in `environment` section from variables loaded via `env_file`?
   - Research needed: Docker Compose v2.x documentation on variable expansion order

2. **Podman Compose compatibility**
   - Question: Does Podman Compose handle `env_file` and variable expansion the same way as Docker Compose?
   - Research needed: Podman Compose documentation on `env_file` directive

3. **Tilde expansion in compose files**
   - Question: Does `${PAI_DIR:-~/.claude}` correctly expand the tilde to user's home directory?
   - Research needed: Shell expansion behavior in docker-compose

4. **Optimal fix strategy**
   - Question: Should we use `env_file` only, or combine with `environment` section mappings?
   - Research needed: Docker Compose best practices for environment variable loading

### Research Agent Tasks

```text
Task 1: "Research Docker Compose v2.x variable expansion order and env_file directive behavior"
Task 2: "Research Podman Compose env_file compatibility and differences from Docker Compose"
Task 3: "Find best practices for Docker Compose environment variable configuration with .env files"
Task 4: "Research shell tilde expansion behavior in docker-compose variable syntax"
```

## Phase 1: Design Artifacts

### data-model.md

**N/A** - This feature has no data model. Configuration only.

### contracts/

**N/A** - This feature has no API contracts. Infrastructure only.

### quickstart.md

**Content to Generate**:
1. How to verify env_file is loading correctly
2. How to test with different compose files
3. Troubleshooting steps for "variable not set" warnings
4. Verification checklist

## Phase 2: Implementation Outline

**NOTE**: This is planning phase. Implementation tasks will be generated by `/speckit.tasks` command.

**High-Level Implementation Steps**:

1. **Rename existing compose files for clarity**:
   - Rename `docker-compose.yml` → `docker-compose-falkordb.yml`
   - Rename `podman-compose.yml` → `podman-compose-falkordb.yml`
   - Find and update all references in code (run.ts, install.ts, documentation, etc.)

2. **Create missing compose file**:
   - Create `podman-compose-neo4j.yml` based on `docker-compose-neo4j.yml` structure
   - Use consistent `${PAI_DIR:-$HOME/.claude}/.env` path with fallback (note: `$HOME` not `~`)

3. **Fix env_file paths** (apply tilde fix to all files):
   - Update all compose files to use `${PAI_DIR:-$HOME/.claude}/.env` (replace `~` with `$HOME`)
   - This is the ROOT CAUSE fix: Docker Compose doesn't expand tilde, treats it as literal character

4. **Find and update all references**:
   - Use Codanna or grep to find all references to old filenames
   - Update TypeScript source files (run.ts, install.ts, container.ts, etc.)
   - Update documentation (README.md, INSTALL.md, docs/)
   - Update package.json scripts if they reference compose files

5. **Add validation** (optional):
   - Add container startup validation to check if required variables are set
   - Provide clear error messages if `.env` file is missing or invalid

6. **Update documentation**:
   - Create environment configuration guide
   - Create troubleshooting guide for env_file issues
   - Update README with compose file usage clarification
   - Document breaking change: compose file renaming

7. **Test all compose files**:
   - Test `docker-compose-falkordb.yml` (FalkorDB + Docker)
   - Test `docker-compose-neo4j.yml` (Neo4j + Docker)
   - Test `podman-compose-falkordb.yml` (FalkorDB + Podman)
   - Test `podman-compose-neo4j.yml` (Neo4j + Podman)
