# Implementation Plan: Fix Sync Hook Protocol Mismatch

**Branch**: `003-fix-issue-2` | **Date**: 2026-01-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-fix-issue-2/spec.md`

## Summary

Fix CRITICAL bug blocking Knowledge sync functionality. The sync hook (`src/hooks/sync-memory-to-knowledge.ts`) currently uses SSE GET protocol to connect to `/sse` endpoint, but the Graphiti MCP server actually uses HTTP POST with JSON-RPC 2.0 to the `/mcp/` endpoint. A working reference implementation exists in `src/server/lib/mcp-client.ts`. This fix rewrites the knowledge client to use the correct protocol, adds database type detection for dynamic query sanitization (Neo4j vs FalkorDB), and ensures graceful degradation when MCP is unavailable.

## Technical Context

**Language/Version**: TypeScript (ES modules, strict mode), Bun runtime
**Primary Dependencies**: @modelcontextprotocol/sdk (existing), existing mcp-client.ts library
**Storage**: Neo4j (default) or FalkorDB backend via Docker/Podman containers
**Testing**: bun test (unit and integration tests with running containers)
**Target Platform**: CLI tool (hooks) running on macOS/Linux with Bun runtime
**Project Type**: Single project - TypeScript library with CLI tools
**Performance Goals**: 15 seconds for 20 file sync batch, 5 second health check
**Constraints**: HTTP POST only (no SSE GET), JSON-RPC 2.0 protocol, SSE response body parsing
**Scale/Scope**: Single sync hook, one knowledge client library, affects ~3 source files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Container-First Architecture
✅ **PASS** - MCP server and database containers already exist. Fix does not modify container configuration.

### Principle II: Graph-Centric Design
✅ **PASS** - All operations go through Graphiti MCP API. Entity extraction performed by LLM server-side.

### Principle III: Zero-Friction Knowledge Capture
✅ **PASS** - Sync is automatic via SessionStart hook. No manual user intervention required.

### Principle IV: Query Resilience
✅ **PASS** - FR-004 through FR-006 explicitly address database type detection and conditional sanitization. Lucene escaping for FalkorDB, passthrough for Neo4j.

### Principle V: Graceful Degradation
✅ **PASS** - FR-013 requires non-blocking execution when MCP unavailable. FR-007 implements retry with exponential backoff.

### Principle VI: Codanna-First Development
✅ **PASS** - Used Codanna CLI to explore codebase and identify reference implementation in `src/server/lib/mcp-client.ts`.

**GATE RESULT**: All principles satisfied. No violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/003-fix-issue-2/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── mcp-client.ts   # MCP client interface contract
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── hooks/
│   ├── sync-memory-to-knowledge.ts    # Main hook entry (MODIFY)
│   └── lib/
│       ├── knowledge-client.ts        # MCP client (REWRITE - use HTTP POST protocol)
│       ├── frontmatter-parser.ts      # YAML parsing (existing, unchanged)
│       └── sync-state.ts              # State tracking (existing, unchanged)
└── server/
    └── lib/
        ├── mcp-client.ts              # Reference implementation (existing, reference only)
        └── lucene.ts                  # Query sanitization (existing, reused)

tests/
├── unit/
│   └── hooks/
│       └── lib/
│           └── knowledge-client.test.ts  # Unit tests for MCP client
└── integration/
    └── hooks/
        └── sync-memory-to-knowledge.test.ts  # Integration tests with live MCP
```

**Structure Decision**: Single project structure applies. This is a bug fix affecting existing TypeScript code under `src/hooks/`. The reference implementation in `src/server/lib/mcp-client.ts` demonstrates the correct HTTP POST + JSON-RPC 2.0 protocol with SSE response parsing.

## Complexity Tracking

> No Constitution Check violations - this section not applicable

## Phase 0: Research

### Unknowns to Resolve

1. **MCP Protocol Details**: Confirm exact HTTP POST format, JSON-RPC 2.0 structure, and SSE response parsing from reference implementation
2. **Database Type Detection**: Determine how to read MADEINOZ_KNOWLEDGE_DB and implement conditional sanitization
3. **Session Management**: Understand Mcp-Session-Id header lifecycle and initialization flow
4. **Error Handling Patterns**: Identify retryable vs non-retryable errors for exponential backoff

### Research Tasks

1. **Analyze reference implementation** (`src/server/lib/mcp-client.ts`)
   - Extract HTTP POST request format
   - Document SSE response parsing logic
   - Understand session initialization flow

2. **Review query sanitization** (`src/server/lib/lucene.ts`)
   - Document special character escaping rules
   - Confirm Neo4j vs FalkorDB differences

3. **Examine existing hook code** (`src/hooks/sync-memory-to-knowledge.ts`)
   - Understand current SSE GET approach (broken)
   - Identify where to apply HTTP POST fix
   - Map integration points with sync-state.ts

## Phase 1: Design

### Data Model

See [data-model.md](./data-model.md) for entity definitions:
- Episode (knowledge entry)
- Sync State (file tracking)
- MCP Session (connection state)
- Memory File (input source)

### Contracts

See [contracts/mcp-client.ts](./contracts/mcp-client.ts) for:
- `MCPClient` class interface
- Session initialization (`initialize()`)
- Tool invocation (`callTool()`)
- Response parsing (`parseSSEResponse()`)

### Quickstart

See [quickstart.md](./quickstart.md) for:
- Manual testing with MCP server
- Environment variable setup
- Verification steps

### Agent Context Update

```bash
.specify/scripts/bash/update-agent-context.sh claude
```

## Constitution Re-Check (Post-Phase 1)

*Re-evaluating after design completion*

All principles remain satisfied:
- Protocol fix maintains container architecture
- Graph-centric operations preserved
- Zero-friction sync maintained
- Query resilience enhanced with database type detection
- Graceful degradation preserved with retry logic
- Codanna CLI used for codebase exploration

**FINAL GATE RESULT**: ✅ APPROVED for implementation

---

**Next Command**: `/speckit.tasks` to generate actionable implementation tasks
