# Token Metrics API Contract

**Feature Branch**: `001-mcp-wrapper`
**Date**: 2026-01-18
**Status**: Complete

## Overview

The `token-metrics.ts` module provides measurement utilities for tracking response size reduction and validating token savings.

---

## Module API

### measureTokens

Calculate token metrics for a transformation.

```typescript
function measureTokens(
  rawData: unknown,
  compactOutput: string,
  operation: string,
  processingTimeMs: number
): TokenMetrics;
```

**Parameters**:
- `rawData`: Original MCP response data
- `compactOutput`: Formatted output string
- `operation`: MCP operation name
- `processingTimeMs`: Time taken to transform

**Returns**: `TokenMetrics` with all measurements

**Example**:
```typescript
import { measureTokens } from './lib/token-metrics.js';

const metrics = measureTokens(
  { nodes: [...] },  // rawData
  'Found 3 entities...', // compactOutput
  'search_nodes',
  8
);

console.log(metrics.savingsPercent); // 76.1
```

---

### TokenMetrics

Complete metrics for a transformation.

```typescript
interface TokenMetrics {
  /** MCP operation name */
  operation: string;

  /** Measurement timestamp */
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

---

### estimateTokens

Estimate token count from text using chars/4 formula.

```typescript
function estimateTokens(text: string): number;
```

**Implementation**:
```typescript
function estimateTokens(text: string): number {
  return Math.ceil(text.length / 4);
}
```

**Notes**:
- This is an approximation; actual tokenization varies by model
- Conservative estimate (rounds up)
- Suitable for relative comparisons

---

### formatMetricsReport

Generate human-readable metrics summary.

```typescript
function formatMetricsReport(metrics: TokenMetrics): string;
```

**Output Format**:
```
--- Token Metrics ---
Operation: {operation}
Raw size: {rawBytes} bytes ({estimatedTokensBefore} est. tokens)
Compact size: {compactBytes} bytes ({estimatedTokensAfter} est. tokens)
Savings: {savingsPercent}% ({tokensSaved} tokens saved)
Processing time: {processingTimeMs}ms
```

**Example**:
```typescript
const report = formatMetricsReport(metrics);
console.log(report);
// --- Token Metrics ---
// Operation: search_nodes
// Raw size: 1,247 bytes (312 est. tokens)
// Compact size: 298 bytes (75 est. tokens)
// Savings: 76.1% (237 tokens saved)
// Processing time: 8ms
```

---

## Persistence API

### appendMetrics

Append metrics to JSONL file for later analysis.

```typescript
async function appendMetrics(
  metrics: TokenMetrics,
  filePath: string
): Promise<void>;
```

**File Format** (JSONL):
```json
{"operation":"search_nodes","timestamp":"2026-01-18T12:00:00Z","rawBytes":1247,"compactBytes":298,"savingsPercent":76.1,"estimatedTokensBefore":312,"estimatedTokensAfter":75,"processingTimeMs":8}
{"operation":"add_memory","timestamp":"2026-01-18T12:01:00Z","rawBytes":523,"compactBytes":89,"savingsPercent":83.0,"estimatedTokensBefore":131,"estimatedTokensAfter":22,"processingTimeMs":5}
```

---

### loadMetrics

Load metrics from JSONL file for analysis.

```typescript
async function loadMetrics(filePath: string): Promise<TokenMetrics[]>;
```

**Example**:
```typescript
const allMetrics = await loadMetrics('~/.madeinoz-knowledge/metrics.jsonl');
console.log(`Loaded ${allMetrics.length} measurements`);
```

---

## Analysis API

### aggregateMetrics

Calculate aggregate statistics from multiple measurements.

```typescript
function aggregateMetrics(
  metrics: TokenMetrics[],
  groupBy?: 'operation' | 'day'
): AggregateStats | Map<string, AggregateStats>;
```

**AggregateStats Type**:
```typescript
interface AggregateStats {
  count: number;
  avgSavingsPercent: number;
  medianSavingsPercent: number;
  minSavingsPercent: number;
  maxSavingsPercent: number;
  totalBytesBeforeTransform: number;
  totalBytesAfterTransform: number;
  avgProcessingTimeMs: number;
}
```

**Example**:
```typescript
const byOperation = aggregateMetrics(allMetrics, 'operation');
// Map {
//   'search_nodes' => { count: 47, avgSavingsPercent: 68.3, ... },
//   'get_episodes' => { count: 23, avgSavingsPercent: 54.1, ... },
//   ...
// }
```

---

### generateBenchmarkReport

Generate comprehensive benchmark report for validation.

```typescript
function generateBenchmarkReport(
  metrics: TokenMetrics[]
): BenchmarkReport;
```

**BenchmarkReport Type**:
```typescript
interface BenchmarkReport {
  /** Report generation timestamp */
  generatedAt: Date;

  /** Total measurements analyzed */
  totalMeasurements: number;

  /** Overall aggregate stats */
  overall: AggregateStats;

  /** Stats broken down by operation */
  byOperation: Map<string, AggregateStats>;

  /** Operations failing to meet targets */
  underperformingOperations: Array<{
    operation: string;
    avgSavingsPercent: number;
    target: number;
  }>;

  /** Summary verdict */
  verdict: 'PASS' | 'FAIL';

  /** Human-readable summary */
  summary: string;
}
```

**Example Output**:
```typescript
const report = generateBenchmarkReport(allMetrics);
console.log(report.summary);
// Token Savings Benchmark Report
// ==============================
// Total measurements: 142
// Overall average savings: 64.7%
//
// By Operation:
//   search_nodes: 68.3% avg (target: 30%) ✅
//   search_facts: 71.2% avg (target: 30%) ✅
//   get_episodes: 54.1% avg (target: 30%) ✅
//   add_memory: 62.8% avg (target: 25%) ✅
//   get_status: 45.2% avg (target: 25%) ✅
//
// Verdict: PASS - All operations exceed target savings
```

---

## Validation Rules

### Success Criteria (from spec)

| Operation Type | Target Savings |
|---------------|----------------|
| Knowledge capture | ≥ 25% |
| Search operations | ≥ 30% |

### Flagging Logic

Operations are flagged for review when:
- Average savings < target for operation type
- Savings variance > 20% (inconsistent results)
- Any single measurement shows 0% or negative savings

---

## Constants

```typescript
export const TOKEN_SAVINGS_TARGETS = {
  // Capture operations
  add_memory: 25,

  // Search operations
  search_nodes: 30,
  search_facts: 30,

  // Retrieval operations
  get_episodes: 25,

  // System operations
  get_status: 25,
  clear_graph: 25,
  health: 25,
} as const;
```
