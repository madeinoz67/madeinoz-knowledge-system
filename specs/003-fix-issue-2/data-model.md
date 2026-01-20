# Data Model: Fix Sync Hook Protocol Mismatch

**Feature**: 003-fix-issue-2
**Date**: 2026-01-20

## Overview

This feature fixes the sync hook protocol but does not introduce new data structures. The existing entities remain unchanged.

## Entities

### Episode

A knowledge entry representing a single document/memory synced to the knowledge graph.

**Fields**:
- `uuid` (string, readonly): Unique identifier assigned by server after sync
- `name` (string, required, max 200): Episode title with capture type prefix
- `episode_body` (string, required, max 5000): Content body (truncated if needed)
- `source` (string, optional): Source type (e.g., "text", "message")
- `source_description` (string, optional): Metadata string with session, rating, file info
- `reference_timestamp` (string, optional): ISO timestamp from frontmatter
- `group_id` (string, optional): Knowledge domain (e.g., "learning", "research")

**Relationships**:
- Belongs to: Sync State (via file path)

**Validation Rules**:
- Name: Required, max 200 characters, format: `{capture_type}: {title}`
- Body: Required, max 5000 characters (server constraint)
- Group ID: Optional, used for organizing knowledge by type

### Sync State

Persistent tracking of previously synced files to avoid duplicates.

**Fields**:
- `syncedFiles` (Map<string, SyncedFileEntry>): File path -> sync metadata
- `contentHashes` (Map<string, string>): SHA-256 hash -> file path (for deduplication)

**Nested Type: SyncedFileEntry**
- `path` (string): Absolute file path
- `captureType` (string): Knowledge capture type (learning, research)
- `syncedAt` (string): ISO timestamp of last sync
- `contentHash` (string): SHA-256 hash of cleaned body content

**Storage**: JSON file at `~/.claude/MEMORY/.sync-state.json`

**Relationships**:
- Tracks: Memory Files (by file path)
- References: Episodes (by content hash)

### MCP Session

Server-side session for JSON-RPC 2.0 communication.

**Fields**:
- `sessionId` (string, readonly): Session identifier from response header
- `baseURL` (string): MCP server endpoint (default: `http://localhost:8000/mcp`)
- `initialized` (boolean): Whether session has been initialized
- `requestId` (number): Incrementing JSON-RPC request ID counter

**Lifecycle**:
1. Created on first `initialize()` call
2. Reused for subsequent requests via `Mcp-Session-Id` header
3. No explicit logout needed (server manages timeout)

**Relationships**:
- Manages: Episodes (via tool calls)

### Memory File

Input source file from PAI Memory System.

**Fields**:
- `path` (string): Absolute file path
- `filename` (string): Base filename
- `content` (string): Raw markdown content
- `frontmatter` (object): Parsed YAML metadata
  - `rating` (number, optional): 1-10 score
  - `source` (string, optional): Source identifier
  - `session_id` (string, optional): PAI session UUID
  - `capture_type` (string, optional): Knowledge capture type
  - `timestamp` (string, optional): ISO timestamp
  - `tags` (array<string>, optional): User-defined tags
- `body` (string): Markdown content without frontmatter
- `cleanedBody` (string): Body with special characters sanitized (if needed)
- `contentHash` (string): SHA-256 hash of cleaned body

**Locations**:
- `~/.claude/MEMORY/LEARNING/ALGORITHM/*.md`
- `~/.claude/MEMORY/LEARNING/SYSTEM/*.md`
- `~/.claude/MEMORY/RESEARCH/*.md`

**Relationships**:
- Source for: Episodes (after sync)
- Tracked by: Sync State

## State Transitions

### Memory File Sync Lifecycle

```
[New File]
    |
    v
[Hash Computed] --> [Exists in Sync State?] --Yes--> [Skip]
    |                                          |
    No                                         No
    |                                          |
    v                                          v
[Sync to MCP] --> [Success?] --Yes--> [Update Sync State] --> [Done]
    |               |
    No              No
    |               |
    v               v
[Retry Logic] <-[Exhausted Retries?]--Yes--> [Log Error] --> [Skip File]
    |
    v
[Success on Retry] --> [Update Sync State] --> [Done]
```

### MCP Session Lifecycle

```
[Client Created]
    |
    v
[First Tool Call]
    |
    v
[Initialize Session] --> [Get Mcp-Session-Id] --> [Cache Session ID]
    |                                                     |
    v                                                     v
[Send Tool Call with Session Header] --> [Parse SSE Response] --> [Return Result]
    |
    v
[Subsequent Calls]
    |
    v
[Reuse Cached Session ID] --> [Send with Header] --> [Parse Response]
```

## Configuration

### Environment Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MADEINOZ_KNOWLEDGE_MCP_URL` | string | `http://localhost:8000` | MCP server base URL |
| `MADEINOZ_KNOWLEDGE_DB` | string | `neo4j` | Database backend type (neo4j or falkorodb) |
| `MADEINOZ_KNOWLEDGE_TIMEOUT` | number | `15000` | Request timeout in milliseconds |
| `MADEINOZ_KNOWLEDGE_RETRIES` | number | `3` | Max retry attempts for transient failures |

### Database Type Behavior

| Database Type | Query Sanitization | Character Escaping |
|---------------|-------------------|-------------------|
| `neo4j` | None (native Cypher) | Not needed |
| `falkorodb` | Lucene/RediSearch | Escape: `+ - && || ! ( ) { } [ ] ^ " ~ * ? : \ /` |

## Validation Summary

- **Episode length**: Body max 5000 chars, name max 200 chars (server constraints)
- **Content hash**: SHA-256 for deduplication across files
- **Database type**: Validated against allowed values (neo4j, falkorodb)
- **Retry logic**: Exponential backoff, max 3 attempts, retryable errors only
