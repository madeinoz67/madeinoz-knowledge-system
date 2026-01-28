# Research: Knowledge CLI Remote Host Support

**Feature**: 008-remote-host | **Date**: 2026-01-28

## Overview

This document captures research findings for adding remote host capabilities to the knowledge-cli tool. The current implementation hardcodes localhost connections; this feature enables users to connect to Knowledge MCP servers running on remote machines.

---

## Research Questions & Findings

### 1. HTTP/HTTPS Connection Handling for MCP Clients

**Question**: How should TypeScript MCP clients handle HTTP vs HTTPS connections with configurable TLS validation?

**Findings**:
- MCP SDK (@modelcontextprotocol/sdk) uses SSE (Server-Sent Events) transport over HTTP/HTTPS
- The SDK supports custom transports through configuration
- Node.js `fetch` API (via `undici`) supports HTTPS with custom certificate validation
- Bun's native `fetch` also supports HTTPS with configurable options

**Decision**: Use Bun's native `fetch` with configurable `rejectUnauthorized` option for TLS validation control.

**Rationale**:
- Bun is already the runtime for this project (Constitution Principle VII)
- Native `fetch` provides built-in HTTPS support with certificate validation options
- No additional dependencies required
- Consistent with existing codebase patterns

**Alternatives Considered**:
- `node-fetch` with `https-agent`: Rejected (adds dependency, Bun has native support)
- Custom transport implementation: Rejected (unnecessary complexity for MVP)

**Implementation Notes**:
```typescript
// Example fetch configuration
const response = await fetch(url, {
  headers: { 'Content-Type': 'application/json' },
  signal: AbortSignal.timeout(10000),  // 10 second timeout
  // For HTTPS with custom validation
  // @ts-ignore - Bun supports this option
  rejectUnauthorized: !insecureFlag
});
```

---

### 2. CLI Flag Parsing Patterns in TypeScript/Bun

**Question**: What is the standard pattern for parsing CLI flags with environment variable fallbacks in TypeScript/Bun projects?

**Findings**:
- Common libraries: `commander`, `yargs`, `clite`
- This project already uses a custom CLI pattern (src/server/lib/cli.ts)
- Environment variable access via `process.env`
- Priority: CLI flags > environment variables > defaults

**Decision**: Extend existing `lib/cli.ts` pattern with new flag definitions.

**Rationale**:
- Consistency with existing codebase
- No additional dependencies
- Simpler than learning a new CLI framework for a small feature

**Alternatives Considered**:
- `commander` package: Rejected (adds 80KB dependency, existing pattern sufficient)
- `yargs` package: Rejected (overkill for 4 new flags)

**Implementation Pattern**:
```typescript
// Extended pattern for remote host configuration
const flags = {
  host: {
    flag: args['--host'],
    env: process.env['MADEINOZ_KNOWLEDGE_HOST'],
    default: 'localhost'
  },
  port: {
    flag: args['--port'],
    env: process.env['MADEINOZ_KNOWLEDGE_PORT'],
    default: '8000',
    validate: (v: string) => parseInt(v) >= 1 && parseInt(v) <= 65535
  },
  insecure: {
    flag: args['--insecure'],
    env: false,  // CLI-only for security
    default: false
  },
  verbose: {
    flag: args['--verbose'],
    env: process.env['MADEINOZ_KNOWLEDGE_VERBOSE'] === 'true',
    default: false
  }
};

const getConfig = (key: string) => flags[key].flag ?? flags[key].env ?? flags[key].default;
```

---

### 3. MCP Client Connection Timeout Best Practices

**Question**: What is the appropriate timeout value for MCP client connections, and how should timeout errors be presented?

**Findings**:
- HTTP connection timeouts typically range from 5-30 seconds
- SSE connections are long-lived; initial connection timeout is critical
- 10 seconds is a common default for HTTP APIs (balances responsiveness vs remote latency)
- Timeout errors should distinguish between: DNS failure, connection refused, connection timeout

**Decision**: 10-second timeout with specific error messages for each failure type (from spec clarification).

**Rationale**:
- Matches user clarification (Question 1)
- Industry standard for HTTP clients
- Fast enough for interactive use, long enough for remote networks
- Clear error messaging reduces user frustration (Constitution Principle V: Graceful Degradation)

**Error Message Format**:
```
Error: Connection to remote-host:9000 failed
- Details: Connection timeout (10s)
- Troubleshooting: Verify network connectivity and server is running
- Command: Use --verbose for detailed diagnostics
```

---

### 4. Environment Variable Naming Conventions

**Question**: What environment variable names should be used for remote host configuration?

**Findings**:
- Existing pattern: `MADEINOZ_KNOWLEDGE_*` prefix (from config/.env.example)
- Current env vars: `MADEINOZ_KNOWLEDGE_SYNC_*`, `MADEINOZ_KNOWLEDGE_LLM_*`
- Convention: `{PREFIX}_{CATEGORY}_{SETTING}`

**Decision**:
- `MADEINOZ_KNOWLEDGE_HOST` for remote hostname
- `MADEINOZ_KNOWLEDGE_PORT` for remote port
- `MADEINOZ_KNOWLEDGE_VERBOSE` for verbosity level

**Rationale**:
- Follows existing project conventions
- Clear and discoverable
- Matches pattern from clarifications

---

### 5. TypeScript Path Aliases and Module Resolution

**Question**: How should the new remote host configuration module integrate with existing path aliases?

**Findings**:
- Existing aliases from tsconfig.json: `@server/*`, `@lib/*`, `@tools/*`
- Configuration utilities live in `src/server/lib/config.ts`
- CLI utilities live in `src/server/lib/cli.ts`

**Decision**: Extend `src/server/lib/config.ts` with remote host configuration functions.

**Rationale**:
- Centralized configuration management
- Reusable across server and CLI tools
- Consistent with existing patterns

---

## Technical Decisions Summary

| Area | Decision | Rationale |
|------|----------|-----------|
| HTTP/HTTPS | Bun native `fetch` with `rejectUnauthorized` option | No dependencies, consistent runtime |
| CLI Parsing | Extend existing `lib/cli.ts` pattern | Consistency, no new dependencies |
| Timeout | 10 seconds with specific error types | User clarification, industry standard |
| Environment Variables | `MADEINOZ_KNOWLEDGE_HOST`, `_PORT`, `_VERBOSE` | Existing naming pattern |
| Module Location | Extend `src/server/lib/config.ts` | Centralized config, existing pattern |

---

## Dependencies

No new npm dependencies required. All functionality achievable with:
- Bun runtime (native `fetch`, `AbortSignal.timeout`)
- Existing `@modelcontextprotocol/sdk`
- Standard TypeScript patterns

---

## Open Questions (Resolved)

All technical questions resolved. Ready for Phase 1 design.
