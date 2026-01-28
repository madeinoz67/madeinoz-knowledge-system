# Implementation Plan: Knowledge CLI Remote Host Support

**Branch**: `008-remote-host` | **Date**: 2026-01-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-remote-host/spec.md`

## Summary

Add remote host support to the knowledge-cli tool, allowing users to connect to Knowledge MCP servers running on remote machines via `--host` and `--port` CLI flags or `MADEINOZ_KNOWLEDGE_HOST`/`MADEINOZ_KNOWLEDGE_PORT` environment variables. Currently, the CLI is hardcoded to `localhost:8000`. This feature enables distributed knowledge graph deployments while maintaining 100% backward compatibility.

## Technical Context

**Language/Version**: TypeScript (ES modules, strict mode) with Bun runtime
**Primary Dependencies**: @modelcontextprotocol/sdk (existing), mcp-client.ts library (existing)
**Storage**: N/A (configuration only - connects to remote Neo4j/FalkorDB)
**Testing**: bun test (existing test infrastructure)
**Target Platform**: macOS, Linux (CLI tool)
**Project Type**: Single project (existing structure)
**Performance Goals**: Connection timeout ≤10 seconds (per spec FR-009)
**Constraints**: Backward compatible - existing localhost workflows must work unchanged
**Scale/Scope**: Single CLI tool modification, 2-3 files affected

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies? | Status | Notes |
|-----------|----------|--------|-------|
| I. Container-First Architecture | No | ✅ N/A | No container changes - this is CLI code only |
| II. Graph-Centric Design | No | ✅ N/A | No data model changes |
| III. Zero-Friction Knowledge Capture | No | ✅ N/A | No capture workflow changes |
| IV. Query Resilience | No | ✅ N/A | No query changes |
| V. Graceful Degradation | **Yes** | ✅ COMPLIANT | Must fail gracefully when remote host unreachable - spec requires clear error messages with hostname/port |
| VI. Codanna-First Development | **Yes** | ✅ COMPLIANT | Used Codanna CLI for codebase exploration (see Phase 0) |
| VII. Language Separation | **Yes** | ✅ COMPLIANT | All changes in `src/` TypeScript directory |
| VIII. Dual-Audience Documentation | **Yes** | ✅ REQUIRED | FR-017: Update docs/index.md, docs/getting-started/, CLI help text with AI-friendly summaries and tables |

**Gate Status**: ✅ PASSED - No principle violations

## Project Structure

### Documentation (this feature)

```text
specs/008-remote-host/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (configuration types)
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── cli-options.md   # CLI option contract
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── skills/
│   ├── tools/
│   │   └── knowledge-cli.ts     # PRIMARY: Add --host, --port, --insecure, --verbose flags
│   └── lib/
│       ├── mcp-client.ts        # MODIFY: Add insecure TLS option, configurable timeout
│       └── cli.ts               # REUSE: Existing CLI utilities
└── hooks/
    └── lib/
        └── knowledge-client.ts  # OPTIONAL: Align env var naming if needed
```

**Structure Decision**: Single project structure - this feature modifies existing CLI tool in `src/skills/tools/`

## Complexity Tracking

> No Constitution violations requiring justification

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | - | - |

---

## Phase 0: Research

### Research Questions

| Question | Context | Research Task |
|----------|---------|---------------|
| RQ-1: Current URL construction | Need to understand how `createMCPClient()` is called | ✅ RESOLVED: See codebase analysis |
| RQ-2: TLS certificate handling | How does Bun/fetch handle HTTPS with self-signed certs? | Research Bun fetch TLS options |
| RQ-3: Connection timeout configuration | Spec requires 10s timeout, current code has 30s | ✅ RESOLVED: `DEFAULT_TIMEOUT = 30000` in mcp-client.ts |
| RQ-4: Env var precedence pattern | Ensure consistent behavior across tools | ✅ RESOLVED: CLI > env > default pattern standard |

### Codebase Analysis (Codanna Results)

**Primary File: `src/skills/tools/knowledge-cli.ts`**
- Uses `createMCPClient()` from `../lib/mcp-client` (line 19)
- Has existing flag parsing infrastructure (`parseFlags` function, lines 49-81)
- Has existing env var support pattern (lines 340-347)
- No host/port configuration currently

**MCP Client: `src/skills/lib/mcp-client.ts`**
- Hardcoded: `const DEFAULT_BASE_URL = 'http://localhost:8000/mcp'` (line 156)
- Hardcoded: `const DEFAULT_TIMEOUT = 30000` (line 157)
- Constructor accepts `config.baseURL` (line 235): `this.baseURL = config.baseURL || DEFAULT_BASE_URL`
- Already supports custom configuration via `MCPClientConfig` interface

**Hooks Client: `src/hooks/lib/knowledge-client.ts`**
- Already has env var support: `baseURL: process.env.MADEINOZ_KNOWLEDGE_MCP_URL || 'http://localhost:8000'` (line 39)
- Uses different env var naming (`MADEINOZ_KNOWLEDGE_MCP_URL` vs proposed `MADEINOZ_KNOWLEDGE_HOST`)

### Decisions

| Decision | Rationale | Alternatives Rejected |
|----------|-----------|----------------------|
| D-1: Add flags to knowledge-cli.ts only | This is the user-facing CLI; hooks client already has env var support | Modifying hooks client would be scope creep |
| D-2: Use `https://` prefix in host for HTTPS | Consistent with curl/wget behavior; no separate `--https` flag needed | Separate `--https` flag adds complexity |
| D-3: Connection timeout stays at 30s for operations, 10s is for connection establishment | Spec says "within 10 seconds" for error messages, not total operation time | Lowering to 10s might break legitimate slow queries |
| D-4: Align env vars: HOST, PORT separated | Matches spec FR-005/FR-006; more flexible than single URL | Single `_URL` env var is less flexible for scripts |

---

## Phase 1: Design

### Data Model

**New Types in knowledge-cli.ts:**

```typescript
interface ConnectionConfig {
  host: string;      // Default: 'localhost'
  port: number;      // Default: 8000
  insecure: boolean; // Default: false (validate TLS)
  verbose: boolean;  // Default: false
}
```

**Modified CLIFlags interface:**

```typescript
interface CLIFlags {
  raw: boolean;
  metrics: boolean;
  metricsFile?: string;
  help: boolean;
  since?: string;
  until?: string;
  // NEW: Remote host configuration
  host?: string;
  port?: number;
  insecure: boolean;
  verbose: boolean;
}
```

### URL Construction Logic

```
Priority Order:
1. CLI flags (--host, --port) - highest priority
2. Environment variables (MADEINOZ_KNOWLEDGE_HOST, MADEINOZ_KNOWLEDGE_PORT)
3. Defaults (localhost, 8000) - lowest priority

URL Construction:
- If host starts with 'https://': strip prefix, use HTTPS, extract host
- If host starts with 'http://': strip prefix, use HTTP, extract host
- Otherwise: use HTTP by default
- Final URL: {protocol}://{host}:{port}/mcp
```

### Modified Components

**1. knowledge-cli.ts - parseFlags()**
```
Add parsing for:
- --host <hostname>     (string, optional)
- --port <number>       (number, optional, validate 1-65535)
- --insecure            (boolean, default false)
- --verbose             (boolean, default false)
```

**2. knowledge-cli.ts - getConnectionConfig()**
```
New function:
- Read CLI flags first
- Fall back to env vars: MADEINOZ_KNOWLEDGE_HOST, MADEINOZ_KNOWLEDGE_PORT
- Fall back to defaults
- Validate port range
- Construct full URL
- Return { url, insecure, verbose }
```

**3. knowledge-cli.ts - createMCPClient() calls**
```
Change from:
  const client = createMCPClient();
To:
  const client = createMCPClient({
    baseURL: connectionConfig.url,
    timeout: connectionConfig.verbose ? 30000 : 10000
  });
```

**4. knowledge-cli.ts - health command output**
```
Update to show:
  "Connected to: {host}:{port}"
  "Protocol: HTTP/HTTPS"
  "TLS Validation: enabled/disabled"
```

**5. knowledge-cli.ts - error handling**
```
Wrap all client calls to catch connection errors and display:
  "Failed to connect to {host}:{port}: {error}"
If verbose, add:
  - DNS resolution status
  - Connection timing
  - TLS certificate details (for HTTPS)
```

**6. mcp-client.ts - Optional TLS handling**
```
If insecure flag is passed, use fetch with:
  {
    // Note: Bun's fetch uses NODE_TLS_REJECT_UNAUTHORIZED env var
    // or we can use agent configuration
  }
```

### Contracts

See `contracts/cli-options.md` for detailed CLI option contract.

### Help Text Updates

```
Connection Options:
  --host <hostname>   Knowledge MCP server hostname or IP (default: localhost)
  --port <number>     Knowledge MCP server port (default: 8000)
  --insecure          Skip TLS certificate validation for self-signed certs
  --verbose           Enable detailed connection diagnostics

Environment Variables:
  MADEINOZ_KNOWLEDGE_HOST    Remote server hostname (overridden by --host)
  MADEINOZ_KNOWLEDGE_PORT    Remote server port (overridden by --port)

Examples:
  # Connect to remote server
  bun run src/skills/tools/knowledge-cli.ts --host example.com --port 9000 get_status

  # Connect to HTTPS server
  bun run src/skills/tools/knowledge-cli.ts --host https://example.com --port 443 get_status

  # Connect with self-signed cert
  bun run src/skills/tools/knowledge-cli.ts --host https://internal.local --insecure get_status

  # Use environment variables
  export MADEINOZ_KNOWLEDGE_HOST=example.com
  export MADEINOZ_KNOWLEDGE_PORT=9000
  bun run src/skills/tools/knowledge-cli.ts get_status
```

---

## Post-Design Constitution Re-Check

| Principle | Status | Evidence |
|-----------|--------|----------|
| V. Graceful Degradation | ✅ COMPLIANT | Error handling shows hostname/port, connection timeout, clear messages |
| VI. Codanna-First Development | ✅ COMPLIANT | Used Codanna CLI for all codebase exploration |
| VII. Language Separation | ✅ COMPLIANT | All changes in TypeScript `src/` directory |
| VIII. Dual-Audience Documentation | ✅ COMPLIANT | Help text includes structured examples, env var table |

**Gate Status**: ✅ PASSED - Ready for Phase 2 task generation

---

## Implementation Summary

### Files to Modify

| File | Changes | Lines Est. |
|------|---------|------------|
| `src/skills/tools/knowledge-cli.ts` | Add flags, URL construction, error handling, help text | +150 |
| `src/skills/lib/mcp-client.ts` | Add insecure TLS option (optional) | +20 |
| `docs/index.md` | Add AI-friendly summary, update quick reference card with new options | +30 |
| `docs/getting-started/overview.md` | Add remote connection examples | +20 |
| `docs/reference/configuration.md` | Add environment variables table | +15 |

### Test Cases Required

| Test | Description |
|------|-------------|
| TC-1 | Default behavior unchanged (localhost:8000) |
| TC-2 | --host flag overrides localhost |
| TC-3 | --port flag overrides 8000 |
| TC-4 | Environment variables work when no flags |
| TC-5 | CLI flags take precedence over env vars |
| TC-6 | Invalid port (0, 65536, -1) rejected |
| TC-7 | HTTPS prefix detected and used |
| TC-8 | Connection failure shows hostname/port |
| TC-9 | Health command shows connection info |
| TC-10 | --insecure flag skips TLS validation |

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing localhost workflows | Low | High | Extensive default behavior testing |
| TLS handling complexity in Bun | Medium | Medium | Use NODE_TLS_REJECT_UNAUTHORIZED as fallback |
| Timeout too short for slow networks | Low | Low | Keep 30s for operations, 10s for connect only |
