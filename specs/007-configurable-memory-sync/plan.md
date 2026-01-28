# Implementation Plan: Configurable Memory Sync

**Branch**: `007-configurable-memory-sync` | **Date**: 2026-01-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-configurable-memory-sync/spec.md`

## Summary

Enhance the memory-to-knowledge sync system with configurable source filtering, robust anti-loop detection, and production-ready Docker Compose for remote Neo4j deployment. Deprecate the realtime sync hook in favor of a single consolidated SessionStart sync.

## Technical Context

**Language/Version**: TypeScript (ES modules, strict mode) with Bun runtime
**Primary Dependencies**: @modelcontextprotocol/sdk, node:fs, node:crypto
**Storage**: Neo4j graph database via Graphiti MCP server
**Testing**: bun test (TypeScript)
**Target Platform**: Linux/macOS servers, PAI infrastructure
**Project Type**: single (src/ with hooks/)
**Performance Goals**: Sync completion within session start timeout (~30s)
**Constraints**: Non-blocking hook execution, graceful degradation when MCP offline
**Scale/Scope**: Hundreds of memory files per sync, single PAI user per deployment

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Container-First Architecture | PASS | Production compose provides containerized Neo4j deployment |
| II. Graph-Centric Design | PASS | Uses Graphiti knowledge graph API, preserves entity relationships |
| III. Zero-Friction Knowledge Capture | PASS | Automatic sync with no manual organization required |
| IV. Query Resilience | PASS | Neo4j backend - no Lucene escaping needed |
| V. Graceful Degradation | PASS | Hook exits gracefully when MCP unavailable (existing pattern) |
| VI. Codanna-First Development | PASS | Used Codanna for codebase exploration during research |
| VII. Language Separation | PASS | All changes in TypeScript (src/hooks/), no Python mixing |
| VIII. Dual-Audience Documentation | PASS | Remote deployment docs will include AI-friendly summary |

**Gate Status**: PASS - All principles satisfied, no violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/007-configurable-memory-sync/
├── plan.md              # This file
├── research.md          # Clarification decisions (Phase 0)
├── data-model.md        # Entity definitions (Phase 1)
├── quickstart.md        # Remote deployment guide (Phase 1)
├── contracts/           # API contracts (Phase 1)
│   └── sync-config.ts   # Configuration interface
└── tasks.md             # Task breakdown (Phase 2 - /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── hooks/
│   ├── sync-memory-to-knowledge.ts  # MODIFY: Add anti-loop detection, configurable sources
│   ├── sync-learning-realtime.ts    # DELETE: Deprecate this hook
│   └── lib/
│       ├── sync-state.ts            # EXISTING: Dual deduplication (path + hash)
│       ├── sync-config.ts           # NEW: Configuration loader
│       └── anti-loop-patterns.ts    # NEW: Knowledge operation detection patterns
└── server/
    └── docker-compose-production.yml  # NEW: Production compose for remote servers

docs/
└── remote-deployment.md              # NEW: User documentation for remote setup
```

**Structure Decision**: Single project structure. All hook code in src/hooks/, production compose in src/server/, documentation in docs/. Follows existing codebase patterns.

## Complexity Tracking

> No violations requiring justification. Design follows existing patterns.

| Addition | Justification | Simpler Alternative Considered |
|----------|---------------|-------------------------------|
| Anti-loop patterns module | Centralizes detection logic, reusable across sync functions | Inline patterns in sync function - harder to maintain |
| Config module | Environment variable parsing with validation | Direct env access - no validation, error-prone |
