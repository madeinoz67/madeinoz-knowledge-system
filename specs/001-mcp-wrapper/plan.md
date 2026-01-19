# Implementation Plan: MCP Wrapper for Token Savings

**Branch**: `001-mcp-wrapper` | **Date**: 2026-01-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-mcp-wrapper/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Create a CLI wrapper around the Graphiti MCP tools that produces compact, token-efficient output formats. The wrapper intercepts MCP tool responses, transforms verbose JSON into minimal human-readable summaries, and provides fallback to direct MCP operations when transformation fails. The goal is 25-30% token reduction while maintaining full functionality.

## Technical Context

**Language/Version**: TypeScript (ES modules, strict mode), Bun runtime
**Primary Dependencies**: @modelcontextprotocol/sdk (existing), mcp-client.ts library (existing)
**Storage**: Neo4j (default) or FalkorDB via Graphiti MCP server (existing infrastructure)
**Testing**: bun test (existing), integration tests require running containers
**Target Platform**: CLI (macOS/Linux), Claude Code MCP integration
**Project Type**: Single project - extends existing `src/server/` structure
**Performance Goals**: ≤100ms wrapper processing overhead per operation
**Constraints**: Response transformation must preserve semantic meaning, wrapper must work with both database backends
**Scale/Scope**: ~8 MCP tool operations to wrap, token savings validated against baseline measurements

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Container-First Architecture ✅ PASS
- **Assessment**: Wrapper operates entirely client-side; no container changes required
- **Impact**: None - MCP server container unchanged

### Principle II: Graph-Centric Design ✅ PASS
- **Assessment**: Wrapper transforms MCP output format only; all operations still use Graphiti knowledge graph API
- **Impact**: None - semantic meaning preserved, only presentation changes

### Principle III: Zero-Friction Knowledge Capture ✅ PASS
- **Assessment**: Wrapper is transparent to users; same natural language triggers continue to work
- **Impact**: None - user interface unchanged

### Principle IV: Query Resilience ✅ PASS
- **Assessment**: Wrapper fallback mechanism logs failures and retries via direct MCP
- **Impact**: Positive - adds resilience layer with logging for analysis

### Principle V: Graceful Degradation ✅ PASS
- **Assessment**: Wrapper failures fall back to direct MCP operations, never block functionality
- **Impact**: Positive - enhances graceful degradation with fallback pattern

**Gate Status**: ✅ ALL PRINCIPLES PASS - Proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/001-mcp-wrapper/
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
├── server/
│   ├── mcp-wrapper.ts           # EXISTING - CLI wrapper (to be enhanced)
│   ├── lib/
│   │   ├── mcp-client.ts        # EXISTING - HTTP client for MCP
│   │   ├── output-formatter.ts  # NEW - Token-efficient output formatting
│   │   ├── token-metrics.ts     # NEW - Response size measurement
│   │   └── wrapper-config.ts    # NEW - Wrapper configuration
│   └── run.ts                   # EXISTING - Server orchestration (unchanged)
├── skills/
│   ├── SKILL.md                 # EXISTING - Update to prefer wrapper
│   └── workflows/               # EXISTING - Update to use wrapper operations
│       ├── CaptureEpisode.md    # Update with wrapper instructions
│       ├── SearchKnowledge.md   # Update with wrapper instructions
│       └── ...                  # Other workflows
└── hooks/                       # EXISTING - Unchanged

tests/
├── unit/
│   ├── output-formatter.test.ts # NEW - Format transformation tests
│   └── token-metrics.test.ts    # NEW - Measurement accuracy tests
└── integration/
    └── wrapper-benchmark.test.ts # NEW - Token savings validation
```

**Structure Decision**: Extends existing `src/server/` structure with new library modules for formatting and metrics. No new top-level directories.

## Complexity Tracking

> **No Constitution violations requiring justification.**

| Component | Complexity | Justification |
|-----------|------------|---------------|
| output-formatter.ts | Low | Single-responsibility module for JSON→compact transformation |
| token-metrics.ts | Low | Measurement utility using bytes + chars/4 formula |
| wrapper-config.ts | Low | Configuration for output format preferences |
