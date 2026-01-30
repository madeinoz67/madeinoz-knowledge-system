# Implementation Plan: Remote MCP Access for Knowledge CLI

**Branch**: `010-remote-mcp-access` | **Date**: 2026-01-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/010-remote-mcp-access/spec.md`

## Summary

Add remote MCP access capabilities to the knowledge-cli, enabling connections from different machines. The solution includes: (1) environment variable-based host/port configuration, (2) TLS/SSL support for secure connections, (3) connection profile management for multiple knowledge systems, and (4) Docker network configuration for external access.

## Technical Context

**Language/Version**: TypeScript (ES modules, strict mode) with Bun runtime for client; Python 3.11+ for MCP server
**Primary Dependencies**: @modelcontextprotocol/sdk (MCP client), node:https (TLS), js-yaml (profile parsing), uvicorn (Python server)
**Storage**: YAML configuration files for connection profiles; Neo4j or FalkorDB for graph data
**Testing**: bun test (TypeScript client), pytest (Python server integration)
**Target Platform**: Linux/macOS/Windows with Bun runtime, Docker/Podman for server
**Project Type**: single (CLI tool with containerized server)
**Performance Goals**: <2s query response on broadband, <5s connection establishment, 10+ concurrent connections
**Constraints**: Must maintain backward compatibility (localhost default), TLS verification by default with opt-out, no breaking changes to existing API
**Scale/Scope**: Single server with multiple clients, ~10 concurrent users typical, configuration via environment variables and YAML files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance | Notes |
|-----------|------------|-------|
| **I. Container-First Architecture** | ✅ PASS | MCP server runs in Docker/Podman; network configuration changes are additive (0.0.0.0 binding) |
| **II. Graph-Centric Design** | ✅ PASS | No changes to graph storage or operations; remote access is transport-layer only |
| **III. Zero-Friction Knowledge Capture** | ✅ PASS | CLI interface unchanged for users; remote configuration is transparent |
| **IV. Query Resilience** | ✅ PASS | No changes to query logic; special character handling preserved |
| **V. Graceful Degradation** | ✅ PASS | Connection failures produce clear error messages; localhost fallback available |
| **VI. Codanna-First Development** | ✅ PASS | Used Codanna CLI for codebase exploration; will continue for implementation |
| **VII. Language Separation** | ✅ PASS | Client changes in `src/` (TypeScript), server changes in `docker/` (Python) |
| **VIII. Dual-Audience Documentation** | ✅ PASS | Documentation will include AI-friendly summaries and configuration tables |

**Gate Result**: ✅ ALL PASS - No violations to justify. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/010-remote-mcp-access/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── skills/
│   ├── lib/
│   │   ├── mcp-client.ts           # MODIFIED: Add TLS options, connection profile support
│   │   └── connection-profile.ts   # NEW: Profile loading and validation
│   └── tools/
│       └── knowledge-cli.ts        # MODIFIED: Add profile selection, connection status
└── server/
    └── lib/
        └── config.ts               # MODIFIED: Add MADEINOZ_KNOWLEDGE_HOST/PORT/TLS mappings

docker/
├── patches/
│   └── graphiti_mcp_server.py      # MODIFIED: Add 0.0.0.0 host binding, TLS config
└── Dockerfile                      # MODIFIED: Add TLS certificate volume mounts

config/
└── knowledge-profiles.yaml         # NEW: Default connection profiles configuration

docs/
└── remote-access.md                # NEW: Remote access setup and troubleshooting guide
```

**Structure Decision**: Single project structure with TypeScript client (`src/`) and Python server (`docker/`) following Principle VII (Language Separation). Client changes focus on connection configuration; server changes focus on network binding and TLS support.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | No violations | N/A |

---

## Phase 0: Research & Technical Decisions

### Research Questions

1. **MCP Remote Connection Patterns**: How does the MCP protocol handle remote connections over HTTP/HTTPS?
2. **TLS Implementation in Bun/Node.js**: What is the standard pattern for HTTPS clients with certificate verification options?
3. **Docker External Access**: What are the security considerations for binding MCP server to 0.0.0.0?
4. **Configuration File Best Practices**: How should connection profiles be structured and validated?

### Research Findings

See [research.md](./research.md) for detailed findings.

---

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](./data-model.md) for entity definitions and relationships.

### API Contracts

See [contracts/](./contracts/) for interface definitions.

### Quickstart Guide

See [quickstart.md](./quickstart.md) for user-facing setup instructions.

---

## Constitution Re-Check (Post-Design)

*Re-evaluating gates after Phase 1 design completion.*

| Principle | Compliance | Notes |
|-----------|------------|-------|
| **I. Container-First Architecture** | ✅ PASS | 0.0.0.0 binding configured via environment variable; containers maintain isolation |
| **II. Graph-Centric Design** | ✅ PASS | No changes to graph operations; transport layer only |
| **III. Zero-Friction Knowledge Capture** | ✅ PASS | Profile selection via single env var; no user action required for default case |
| **IV. Query Resilience** | ✅ PASS | Query logic unchanged; special character handling preserved |
| **V. Graceful Degradation** | ✅ PASS | Connection errors are actionable; localhost default remains |
| **VI. Codanna-First Development** | ✅ PASS | Design informed by Codanna exploration of existing codebase |
| **VII. Language Separation** | ✅ PASS | TypeScript client config in `src/`; Python server config in `docker/` |
| **VIII. Dual-Audience Documentation** | ✅ PASS | Configuration uses tables; quickstart includes AI-friendly summary |

**Gate Result**: ✅ ALL PASS - Design validated. Ready for Phase 2 (task breakdown).

---

## Next Steps

1. ✅ Specification complete ([spec.md](./spec.md))
2. ✅ Requirements checklist complete ([checklists/requirements.md](./checklists/requirements.md))
3. ✅ Implementation plan complete (this file)
4. ✅ Phase 0 research complete ([research.md](./research.md))
5. ✅ Phase 1 design complete ([data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md))
6. ⏳ **Phase 2**: Run `/speckit.tasks` to generate task breakdown
