# Output Formatter API Contract

**Feature Branch**: `001-mcp-wrapper`
**Date**: 2026-01-18
**Status**: Complete

## Overview

The `output-formatter.ts` module provides operation-specific formatters that transform MCP responses into compact, token-efficient output.

---

## Module API

### formatOutput

Main entry point for formatting MCP responses.

```typescript
function formatOutput(
  operation: string,
  data: unknown,
  options?: FormatOptions
): FormatResult;
```

**Parameters**:
- `operation`: MCP operation name (e.g., "search_nodes", "add_memory")
- `data`: Raw MCP response data
- `options`: Optional formatting configuration

**Returns**: `FormatResult` containing formatted output and metrics

**Example**:
```typescript
import { formatOutput } from './lib/output-formatter.js';

const result = formatOutput('search_nodes', {
  nodes: [
    { name: 'Graphiti', entity_type: 'Framework', summary: 'Knowledge graph framework' }
  ]
});

console.log(result.output);
// Found 1 entity for query:
// 1. Graphiti [Framework] - Knowledge graph framework
```

---

### FormatOptions

Configuration for formatting behavior.

```typescript
interface FormatOptions {
  /** Maximum output lines before truncation */
  maxLines?: number;

  /** Maximum characters per line */
  maxLineLength?: number;

  /** Include metrics in result */
  collectMetrics?: boolean;

  /** Transformation timeout (ms) */
  timeoutMs?: number;

  /** Original query for context (used in output) */
  query?: string;
}
```

**Default Values**:
```typescript
const DEFAULT_OPTIONS: FormatOptions = {
  maxLines: 20,
  maxLineLength: 120,
  collectMetrics: false,
  timeoutMs: 100,
};
```

---

### FormatResult

Result of a formatting operation.

```typescript
interface FormatResult {
  /** Formatted output string */
  output: string;

  /** Whether fallback to raw JSON was used */
  usedFallback: boolean;

  /** Error message if fallback was triggered */
  error?: string;

  /** Token metrics (if collectMetrics: true) */
  metrics?: {
    rawBytes: number;
    compactBytes: number;
    savingsPercent: number;
    processingTimeMs: number;
  };
}
```

---

### registerFormatter

Register a custom formatter for an operation.

```typescript
function registerFormatter(
  operation: string,
  formatter: OperationFormatter
): void;
```

**Parameters**:
- `operation`: MCP operation name to handle
- `formatter`: Formatter function

**Example**:
```typescript
import { registerFormatter } from './lib/output-formatter.js';

registerFormatter('custom_operation', (data, options) => {
  // Transform data to compact string
  return `Custom: ${data.name}`;
});
```

---

### OperationFormatter

Type definition for formatter functions.

```typescript
type OperationFormatter = (
  data: unknown,
  options: FormatOptions
) => string;
```

---

## Built-in Formatters

### formatSearchNodes

Formats `search_nodes` / `search_memory_nodes` responses.

**Input Shape**:
```typescript
{
  nodes: Array<{
    name: string;
    entity_type: string;
    summary: string;
    uuid?: string;
    created_at?: string;
  }>;
}
```

**Output Format**:
```
Found {count} entities for "{query}":
1. {name} [{entity_type}] - {summary}
2. {name} [{entity_type}] - {summary}
...
```

**Truncation Rules**:
- Summary truncated to 80 chars at word boundary
- Maximum 20 results shown (configurable via `maxLines`)

---

### formatSearchFacts

Formats `search_facts` / `search_memory_facts` responses.

**Input Shape**:
```typescript
{
  facts: Array<{
    source: { name: string };
    target: { name: string };
    relation: string;
    confidence?: number;
  }>;
}
```

**Output Format**:
```
Found {count} relationships for "{query}":
1. {source.name} --{relation}--> {target.name} (confidence: {confidence})
2. {source.name} --{relation}--> {target.name}
...
```

**Notes**:
- Confidence shown only if present and > 0
- Relation is normalized to lowercase with hyphens

---

### formatGetEpisodes

Formats `get_episodes` responses.

**Input Shape**:
```typescript
{
  episodes: Array<{
    name: string;
    content?: string;
    created_at: string;
    source_description?: string;
  }>;
}
```

**Output Format**:
```
Recent episodes ({count}):
- [{relative_time}] {name} - {truncated_content}
- [{relative_time}] {name} - {truncated_content}
...
```

**Truncation Rules**:
- Content truncated to 60 chars
- Relative time calculated from `created_at`

---

### formatGetStatus

Formats `get_status` responses.

**Input Shape**:
```typescript
{
  status?: string;
  entity_count: number;
  episode_count: number;
  last_updated?: string;
}
```

**Output Format**:
```
Knowledge Graph Status: {status|HEALTHY}
Entities: {entity_count} | Episodes: {episode_count} | Last update: {relative_time}
```

---

### formatAddMemory

Formats `add_memory` responses.

**Input Shape**:
```typescript
{
  uuid: string;
  name?: string;
  entities_extracted?: number;
  facts_extracted?: number;
}
```

**Output Format**:
```
✓ Episode added: "{name}" (id: ...{uuid_last8})
  Extracted: {entities_extracted} entities, {facts_extracted} facts
```

**Notes**:
- If extraction counts not provided, second line omitted
- UUID truncated to last 8 characters

---

### formatDelete

Formats `delete_episode`, `delete_entity_edge` responses.

**Input Shape**:
```typescript
{
  success: boolean;
  uuid?: string;
  message?: string;
}
```

**Output Format (success)**:
```
✓ Deleted: ...{uuid_last8}
```

**Output Format (failure)**:
```
✗ Delete failed: {message}
```

---

### formatClearGraph

Formats `clear_graph` responses.

**Input Shape**:
```typescript
{
  success: boolean;
  deleted_entities?: number;
  deleted_episodes?: number;
}
```

**Output Format**:
```
✓ Knowledge graph cleared
  Removed: {deleted_entities} entities, {deleted_episodes} episodes
```

---

## Utility Functions

### relativeTime

Convert ISO timestamp to human-readable relative time.

```typescript
function relativeTime(isoString: string): string;
```

**Examples**:
```typescript
relativeTime('2026-01-18T12:00:00Z'); // "2h ago" (if now is 14:00)
relativeTime('2026-01-17T12:00:00Z'); // "1d ago"
relativeTime('2025-12-18T12:00:00Z'); // "1mo ago"
```

---

### truncateUuid

Truncate UUID to last 8 characters with ellipsis prefix.

```typescript
function truncateUuid(uuid: string): string;
```

**Example**:
```typescript
truncateUuid('550e8400-e29b-41d4-a716-446655440000');
// Returns: "...55440000"
```

---

### truncateText

Truncate text at word boundary with ellipsis.

```typescript
function truncateText(text: string, maxLength: number): string;
```

**Example**:
```typescript
truncateText('This is a long text that needs truncation', 25);
// Returns: "This is a long text..."
```

---

## Error Handling

All formatters are wrapped with error handling. If a formatter throws:

1. Error is logged to transformation log
2. `usedFallback` is set to `true` in result
3. Raw JSON is returned as output

```typescript
const result = formatOutput('search_nodes', invalidData);
if (result.usedFallback) {
  console.warn(`Formatter failed: ${result.error}`);
  // result.output contains JSON.stringify(invalidData, null, 2)
}
```
