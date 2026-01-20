# Research: Fix Sync Hook Protocol Mismatch

**Feature**: 003-fix-issue-2
**Date**: 2026-01-20

## Overview

This document consolidates research findings from analyzing the reference implementation, existing broken code, and sanitization utilities. All unknowns from the plan have been resolved.

## MCP Protocol Details

### Decision: Use HTTP POST + JSON-RPC 2.0 with SSE Response Body

**Reference**: `src/server/lib/mcp-client.ts` (lines 216-439)

**Protocol Flow**:
1. **Session Initialization**: POST to `/mcp/` with JSON-RPC `initialize` method
2. **Session ID Extraction**: Read `Mcp-Session-Id` from response headers
3. **Tool Calls**: POST to `/mcp/` with `tools/call` method, including `Mcp-Session-Id` header
4. **Response Parsing**: Response body contains SSE format with `data:` lines containing JSON

**Rationale**: The Graphiti MCP server (zepai/knowledge-graph-mcp:standalone) uses this protocol. SSE is used for response format (in response body), not for transport.

**Key Implementation Details**:
```typescript
// Session initialization request
{
  jsonrpc: "2.0",
  id: 1,
  method: "initialize",
  params: {
    protocolVersion: "2024-11-05",
    capabilities: {},
    clientInfo: { name: "mcp-wrapper", version: "1.0.0" }
  }
}

// Tool call request
{
  jsonrpc: "2.0",
  id: 2,
  method: "tools/call",
  params: {
    name: "add_memory",
    arguments: { /* episode data */ }
  }
}

// Response parsing (extract data: lines from response body)
function parseSSEResponse(text: string): unknown {
  const lines = text.split("\n");
  for (const line of lines) {
    if (line.startsWith("data: ")) {
      const jsonStr = line.substring(6);
      return JSON.parse(jsonStr);
    }
  }
}
```

**Alternatives Considered**:
- SSE GET to `/sse` endpoint: **REJECTED** - endpoint does not exist, causes HTTP 404
- WebSocket transport: **REJECTED** - not supported by Graphiti MCP server
- Direct HTTP REST: **REJECTED** - server requires JSON-RPC 2.0 protocol

## Database Type Detection

### Decision: Read MADEINOZ_KNOWLEDGE_DB, Default to "neo4j"

**Reference**: Environment variable convention from `config/.env.example`

**Implementation**:
```typescript
const dbType = process.env.MADEINOZ_KNOWLEDGE_DB || 'neo4j';
const needsEscaping = dbType === 'falkorodb';
```

**Validation**:
```typescript
const validDbTypes = ['neo4j', 'falkorodb'];
if (dbType && !validDbTypes.includes(dbType)) {
  throw new Error(`Invalid MADEINOZ_KNOWLEDGE_DB: ${dbType}. Must be one of: ${validDbTypes.join(', ')}`);
}
```

**Rationale**: Neo4j is the default and most common backend. FalkorDB requires special query escaping. The environment variable allows users to switch backends without code changes.

**Alternatives Considered**:
- Auto-detect from server: **REJECTED** - adds unnecessary complexity, server may not expose this info
- Separate config file: **REJECTED** - environment variables are standard for this project
- Runtime query detection: **REJECTED** - inefficient, could cause query failures

## Query Sanitization

### Decision: Use Existing lucene.ts Utilities

**Reference**: `src/server/lib/lucene.ts`

**Special Characters to Escape** (FalkorDB only):
```
+ - && || ! ( ) { } [ ] ^ " ~ * ? : \ /
```

**Implementation**:
```typescript
import { sanitizeSearchQuery, sanitizeGroupId } from "../../server/lib/lucene.js";

// For search queries
const sanitizedQuery = sanitizeSearchQuery(params.query);

// For group_id values
const sanitizedGroupId = sanitizeGroupId(params.group_id);
```

**Neo4j Behavior**: No escaping needed - uses native Cypher queries which handle special characters naturally.

**Rationale**: The existing `lucene.ts` utilities are tested and handle all edge cases. Reusing them ensures consistency with the server-side MCP client.

**Alternatives Considered**:
- Custom escaping in hook: **REJECTED** - duplicates existing code, risks inconsistency
- No escaping: **REJECTED** - causes query failures for CTI identifiers like "apt-28"
- Regex replacement: **REJECTED** - existing implementation is more robust

## Session Management

### Decision: Lazy Initialization with Session Caching

**Reference**: `src/server/lib/mcp-client.ts` (lines 248-289)

**Implementation Pattern**:
```typescript
class MCPClient {
  private sessionId: string | null = null;
  private initializePromise: Promise<void> | null = null;

  private async initializeSession(): Promise<void> {
    if (this.sessionId) return; // Already initialized
    if (this.initializePromise) return this.initializePromise; // In progress

    this.initializePromise = (async () => {
      const response = await fetch(this.baseURL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: this.requestId++,
          method: "initialize",
          params: { /* init params */ }
        })
      });

      const sessionId = response.headers.get("Mcp-Session-Id");
      if (!sessionId) throw new Error("Server did not return session ID");

      this.sessionId = sessionId;
      await response.text(); // Consume SSE response body
    })();

    await this.initializePromise;
  }
}
```

**Session Lifecycle**:
1. Created on first `initialize()` call
2. Reused for subsequent requests via `Mcp-Session-Id` header
3. No explicit logout needed (server-side timeout)
4. Single session per client instance

**Rationale**: Lazy initialization avoids unnecessary requests. Session caching prevents redundant initialization. The reference implementation pattern is proven to work.

**Alternatives Considered**:
- Initialize on client construction: **REJECTED** - wasteful if client never used
- New session per request: **REJECTED** - inefficient, loses session context
- Explicit session lifecycle: **REJECTED** - adds complexity, server handles timeout

## Error Handling Patterns

### Decision: Retry with Exponential Backoff for Retryable Errors

**Reference**: Existing sync hook retry logic (`src/hooks/sync-memory-to-knowledge.ts`, lines 257-283)

**Retryable Errors**:
- `timeout` / `AbortError`
- `ECONNREFUSED` / `ECONNRESET` / `ETIMEDOUT`
- HTTP 429 (rate limit)
- HTTP 503 / 502 / 504 (server errors)

**Non-Retryable Errors**:
- HTTP 400 (bad request)
- HTTP 404 (not found)
- JSON-RPC error responses (application-level errors)

**Implementation Pattern**:
```typescript
for (let attempt = 0; attempt < config.retries; attempt++) {
  const result = await addEpisode(params);

  if (result.success) return { success: true };

  const isRetryable = result.error?.includes('timeout') ||
    result.error?.includes('ECONNREFUSED') ||
    result.error?.includes('abort');

  if (!isRetryable) break;

  const backoff = 500 * Math.pow(2, attempt); // Exponential backoff
  await new Promise(r => setTimeout(r, backoff));
}
```

**Rationale**: Exponential backoff is standard for transient failures. Distinguishing retryable from non-retryable errors prevents infinite loops on permanent failures.

**Alternatives Considered**:
- No retry: **REJECTED** - fragile for network issues
- Fixed delay: **REJECTED** - less efficient than exponential backoff
- Retry everything: **REJECTED** - wastes resources on permanent failures

## Integration Points

### Files to Modify

1. **`src/hooks/lib/knowledge-client.ts`** (REWRITE)
   - Replace SSE GET logic with HTTP POST + JSON-RPC 2.0
   - Add session management
   - Integrate database type detection
   - Import sanitization utilities from `src/server/lib/lucene.ts`

2. **`src/hooks/sync-memory-to-knowledge.ts`** (MINOR UPDATE)
   - Update health check to use HTTP POST instead of SSE GET
   - No other changes needed (uses knowledge-client.ts interface)

3. **`src/server/lib/lucene.ts`** (NO CHANGES)
   - Existing utilities reused as-is

### Files to Reference (Read-Only)

- **`src/server/lib/mcp-client.ts`**: Reference implementation for protocol and session management
- **`src/hooks/lib/sync-state.ts`**: State tracking (unchanged)
- **`src/hooks/lib/frontmatter-parser.ts`**: YAML parsing (unchanged)

## Summary

All research unknowns resolved:
- ✅ MCP Protocol: HTTP POST + JSON-RPC 2.0 with SSE response body
- ✅ Database Detection: MADEINOZ_KNOWLEDGE_DB env var, default neo4j
- ✅ Session Management: Lazy init with session caching
- ✅ Error Handling: Exponential backoff for retryable errors

The fix is straightforward: rewrite `knowledge-client.ts` following the reference implementation in `mcp-client.ts`, add database type detection for conditional sanitization, and update the health check method.
