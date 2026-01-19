# Data Model: MCP Wrapper for Token Savings

**Feature Branch**: `001-mcp-wrapper`
**Date**: 2026-01-18
**Status**: Complete

## Overview

The MCP wrapper introduces new data structures for output formatting, token measurement, and wrapper configuration. These models are internal to the wrapper module and do not modify the existing Graphiti MCP schema.

---

## Entities

### OutputFormat

The format specification for transforming MCP responses to compact output.

```typescript
interface OutputFormat {
  /** Unique identifier for the format type */
  formatId: string;

  /** Display template with placeholders */
  template: string;

  /** Fields to extract from response */
  extractFields: string[];

  /** Optional field transformations */
  transforms?: Record<string, (value: unknown) => string>;

  /** Maximum output length (chars) before truncation */
  maxLength?: number;
}
```

**Validation Rules**:
- `formatId` must be alphanumeric with underscores
- `template` must contain at least one placeholder
- `extractFields` must have at least one entry

**Relationships**:
- One OutputFormat per MCP operation type

---

### TokenMetrics

Measurement data for comparing raw vs compact response sizes.

```typescript
interface TokenMetrics {
  /** MCP operation name (e.g., "search_nodes") */
  operation: string;

  /** Timestamp of measurement */
  timestamp: Date;

  /** Raw response size in bytes */
  rawBytes: number;

  /** Compact output size in bytes */
  compactBytes: number;

  /** Percentage savings (0-100) */
  savingsPercent: number;

  /** Estimated tokens before (chars/4) */
  estimatedTokensBefore: number;

  /** Estimated tokens after (chars/4) */
  estimatedTokensAfter: number;

  /** Processing time in milliseconds */
  processingTimeMs: number;
}
```

**Validation Rules**:
- `rawBytes` and `compactBytes` must be positive integers
- `savingsPercent` must be between 0 and 100
- `processingTimeMs` must be non-negative

**State Transitions**:
- Created when transformation completes
- Immutable after creation

---

### TransformationLog

Log entry for transformation failures and slow operations.

```typescript
interface TransformationLog {
  /** Log entry ID */
  id: string;

  /** Timestamp */
  timestamp: Date;

  /** Severity level */
  level: 'info' | 'warn' | 'error';

  /** MCP operation name */
  operation: string;

  /** Input data size in bytes */
  inputSize: number;

  /** Error message if failure */
  error?: string;

  /** Processing time (for slow warnings) */
  processingTimeMs?: number;

  /** Whether fallback was used */
  usedFallback: boolean;
}
```

**Validation Rules**:
- `id` must be UUID format
- `level` must be valid enum value
- `error` required when `level` is 'error'

---

### WrapperConfig

Runtime configuration for the wrapper behavior.

```typescript
interface WrapperConfig {
  /** Enable compact output (default: true) */
  compactOutput: boolean;

  /** Enable metrics collection (default: false) */
  collectMetrics: boolean;

  /** Metrics output file path */
  metricsFile?: string;

  /** Transformation log file path */
  logFile?: string;

  /** Processing time warning threshold (ms) */
  slowThresholdMs: number;

  /** Maximum transformation time before timeout (ms) */
  timeoutMs: number;

  /** Output format override per operation */
  formatOverrides?: Record<string, OutputFormat>;
}
```

**Validation Rules**:
- `slowThresholdMs` must be < `timeoutMs`
- File paths must be absolute or relative to cwd
- `timeoutMs` must be ≤ 100 (per spec requirement)

**Default Values**:
```typescript
const DEFAULT_CONFIG: WrapperConfig = {
  compactOutput: true,
  collectMetrics: false,
  slowThresholdMs: 50,
  timeoutMs: 100,
};
```

---

## MCP Response Schemas

### SearchNodesResponse

Raw response structure from `search_memory_nodes` MCP tool.

```typescript
interface SearchNodesResponse {
  nodes: Array<{
    uuid: string;
    name: string;
    entity_type: string;
    summary: string;
    created_at: string;
    labels?: string[];
    properties?: Record<string, unknown>;
  }>;
}
```

**Compact Format**:
```
Found {count} entities for "{query}":
1. {name} [{entity_type}] - {summary}
2. {name} [{entity_type}] - {summary}
...
```

---

### SearchFactsResponse

Raw response structure from `search_memory_facts` MCP tool.

```typescript
interface SearchFactsResponse {
  facts: Array<{
    uuid: string;
    source: { name: string; uuid: string };
    target: { name: string; uuid: string };
    relation: string;
    confidence?: number;
    valid_at?: string;
    invalid_at?: string;
  }>;
}
```

**Compact Format**:
```
Found {count} relationships for "{query}":
1. {source.name} --{relation}--> {target.name} (confidence: {confidence})
2. {source.name} --{relation}--> {target.name} (confidence: {confidence})
...
```

---

### GetEpisodesResponse

Raw response structure from `get_episodes` MCP tool.

```typescript
interface GetEpisodesResponse {
  episodes: Array<{
    uuid: string;
    name: string;
    content: string;
    source_description?: string;
    created_at: string;
    valid_at?: string;
  }>;
}
```

**Compact Format**:
```
Recent episodes ({count}):
- [{relative_time}] {name} - {truncated_content}
- [{relative_time}] {name} - {truncated_content}
...
```

---

### GetStatusResponse

Raw response structure from `get_status` MCP tool.

```typescript
interface GetStatusResponse {
  status: string;
  entity_count: number;
  episode_count: number;
  last_updated?: string;
  database?: string;
  version?: string;
}
```

**Compact Format**:
```
Knowledge Graph Status: {status}
Entities: {entity_count} | Episodes: {episode_count} | Last update: {relative_time}
```

---

### AddMemoryResponse

Raw response structure from `add_memory` MCP tool.

```typescript
interface AddMemoryResponse {
  uuid: string;
  name: string;
  entities_extracted?: number;
  facts_extracted?: number;
}
```

**Compact Format**:
```
✓ Episode added: "{name}" (id: ...{uuid_last8})
  Extracted: {entities_extracted} entities, {facts_extracted} facts
```

---

### DeleteResponse

Raw response structure from `delete_episode`, `delete_entity_edge` MCP tools.

```typescript
interface DeleteResponse {
  success: boolean;
  uuid: string;
  message?: string;
}
```

**Compact Format**:
```
✓ Deleted: ...{uuid_last8}
```
or
```
✗ Delete failed: {message}
```

---

### ClearGraphResponse

Raw response structure from `clear_graph` MCP tool.

```typescript
interface ClearGraphResponse {
  success: boolean;
  deleted_entities: number;
  deleted_episodes: number;
}
```

**Compact Format**:
```
✓ Knowledge graph cleared
  Removed: {deleted_entities} entities, {deleted_episodes} episodes
```

---

## Transformation Functions

### relativeTime

Convert ISO timestamp to human-readable relative time.

```typescript
function relativeTime(isoString: string): string;
// "2026-01-18T12:00:00Z" -> "2h ago"
// "2026-01-17T12:00:00Z" -> "1d ago"
// "2025-12-18T12:00:00Z" -> "1mo ago"
```

### truncateUuid

Truncate UUID to last 8 characters for display.

```typescript
function truncateUuid(uuid: string): string;
// "550e8400-e29b-41d4-a716-446655440000" -> "...55440000"
```

### truncateText

Truncate text with ellipsis at word boundary.

```typescript
function truncateText(text: string, maxLength: number): string;
// "This is a long text that needs truncation" -> "This is a long text..."
```

---

## File Locations

| Entity | Storage | Path |
|--------|---------|------|
| WrapperConfig | Runtime | Environment or CLI flags |
| TokenMetrics | Optional file | `$HOME/.madeinoz-knowledge/metrics.jsonl` |
| TransformationLog | File | `$HOME/.madeinoz-knowledge/wrapper.log` |
| OutputFormat | Compiled in | `src/server/lib/output-formatter.ts` |

---

## Diagram: Data Flow

```
┌─────────────────┐     ┌──────────────┐     ┌───────────────────┐
│   MCP Server    │────▶│  MCP Client  │────▶│   Output          │
│   (Graphiti)    │     │  (existing)  │     │   Formatter       │
└─────────────────┘     └──────────────┘     │   (new module)    │
                                             └─────────┬─────────┘
                                                       │
                              ┌─────────────────────────┼─────────────────────────┐
                              │                         │                         │
                              ▼                         ▼                         ▼
                        ┌───────────┐           ┌─────────────┐           ┌───────────┐
                        │  Compact  │           │   Token     │           │   Log     │
                        │  Output   │           │   Metrics   │           │   Entry   │
                        │  (stdout) │           │  (optional) │           │  (errors) │
                        └───────────┘           └─────────────┘           └───────────┘
```
