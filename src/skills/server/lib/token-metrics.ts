/**
 * Token Metrics for response size measurement
 * @module token-metrics
 */

import { appendFile, mkdir, readFile } from 'node:fs/promises';
import { dirname } from 'node:path';

// ============================================================================
// Types
// ============================================================================

export interface TokenMetrics {
  operation: string;
  timestamp: Date;
  rawBytes: number;
  compactBytes: number;
  savingsPercent: number;
  estimatedTokensBefore: number;
  estimatedTokensAfter: number;
  processingTimeMs: number;
}

export interface AggregateStats {
  count: number;
  avgSavingsPercent: number;
  medianSavingsPercent: number;
  minSavingsPercent: number;
  maxSavingsPercent: number;
  totalBytesBeforeTransform: number;
  totalBytesAfterTransform: number;
  avgProcessingTimeMs: number;
}

export interface BenchmarkReport {
  generatedAt: Date;
  totalMeasurements: number;
  overall: AggregateStats;
  byOperation: Map<string, AggregateStats>;
  underperformingOperations: Array<{
    operation: string;
    avgSavingsPercent: number;
    target: number;
  }>;
  verdict: 'PASS' | 'FAIL';
  summary: string;
}

// ============================================================================
// Constants (T045)
// ============================================================================

export const TOKEN_SAVINGS_TARGETS: Record<string, number> = {
  add_memory: 25,
  search_nodes: 30,
  search_memory_nodes: 30,
  search_facts: 30,
  search_memory_facts: 30,
  get_episodes: 25,
  get_status: 25,
  clear_graph: 25,
  health: 25,
  delete_episode: 25,
  delete_entity_edge: 25,
};

// Default target for unknown operations
const DEFAULT_TARGET = 25;

// ============================================================================
// Core Functions (T036-T037)
// ============================================================================

/**
 * Estimate token count from text using chars/4 formula.
 * This is an approximation; actual tokenization varies by model.
 * T037
 */
export function estimateTokens(text: string): number {
  if (!text) return 0;
  return Math.ceil(text.length / 4);
}

/**
 * Calculate token metrics for a transformation.
 * T036
 */
export function measureTokens(
  rawData: unknown,
  compactOutput: string,
  operation: string,
  processingTimeMs: number
): TokenMetrics {
  const rawJson = JSON.stringify(rawData, null, 2);
  const rawBytes = new TextEncoder().encode(rawJson).length;
  const compactBytes = new TextEncoder().encode(compactOutput).length;

  const savingsPercent = rawBytes > 0 ? ((rawBytes - compactBytes) / rawBytes) * 100 : 0;

  return {
    operation,
    timestamp: new Date(),
    rawBytes,
    compactBytes,
    savingsPercent,
    estimatedTokensBefore: estimateTokens(rawJson),
    estimatedTokensAfter: estimateTokens(compactOutput),
    processingTimeMs,
  };
}

// ============================================================================
// Formatting Functions (T038)
// ============================================================================

/**
 * Generate human-readable metrics summary.
 * T038
 */
export function formatMetricsReport(metrics: TokenMetrics): string {
  const tokensSaved = metrics.estimatedTokensBefore - metrics.estimatedTokensAfter;

  const lines = [
    '--- Token Metrics ---',
    `Operation: ${metrics.operation}`,
    `Raw size: ${metrics.rawBytes.toLocaleString()} bytes (${metrics.estimatedTokensBefore} est. tokens)`,
    `Compact size: ${metrics.compactBytes.toLocaleString()} bytes (${metrics.estimatedTokensAfter} est. tokens)`,
    `Savings: ${metrics.savingsPercent.toFixed(1)}% (${tokensSaved} tokens saved)`,
    `Processing time: ${metrics.processingTimeMs}ms`,
  ];

  return lines.join('\n');
}

// ============================================================================
// Persistence Functions (T039)
// ============================================================================

/**
 * Append metrics to JSONL file for later analysis.
 * T039
 */
export async function appendMetrics(metrics: TokenMetrics, filePath: string): Promise<void> {
  // Ensure directory exists
  await mkdir(dirname(filePath), { recursive: true });

  // Serialize metrics to JSON line
  const line = `${JSON.stringify({
    ...metrics,
    timestamp: metrics.timestamp.toISOString(),
  })}\n`;

  await appendFile(filePath, line, 'utf-8');
}

/**
 * Load metrics from JSONL file for analysis.
 * T039
 */
export async function loadMetrics(filePath: string): Promise<TokenMetrics[]> {
  try {
    const content = await readFile(filePath, 'utf-8');
    const lines = content.trim().split('\n').filter(Boolean);

    return lines
      .map((line) => {
        try {
          const parsed = JSON.parse(line);
          return {
            ...parsed,
            timestamp: new Date(parsed.timestamp),
          };
        } catch {
          return null;
        }
      })
      .filter((m): m is TokenMetrics => m !== null);
  } catch (_error) {
    // File doesn't exist or is unreadable
    return [];
  }
}

// ============================================================================
// Analysis Functions (T040-T041)
// ============================================================================

/**
 * Calculate aggregate statistics for a single group of metrics.
 */
function calculateStats(metrics: TokenMetrics[]): AggregateStats {
  if (metrics.length === 0) {
    return {
      count: 0,
      avgSavingsPercent: 0,
      medianSavingsPercent: 0,
      minSavingsPercent: 0,
      maxSavingsPercent: 0,
      totalBytesBeforeTransform: 0,
      totalBytesAfterTransform: 0,
      avgProcessingTimeMs: 0,
    };
  }

  const savingsValues = metrics.map((m) => m.savingsPercent).sort((a, b) => a - b);
  const processingTimes = metrics.map((m) => m.processingTimeMs);

  const count = metrics.length;
  const avgSavingsPercent = savingsValues.reduce((a, b) => a + b, 0) / count;
  const minSavingsPercent = savingsValues[0];
  const maxSavingsPercent = savingsValues[count - 1];

  // Calculate median
  const mid = Math.floor(count / 2);
  const medianSavingsPercent =
    count % 2 === 0 ? (savingsValues[mid - 1] + savingsValues[mid]) / 2 : savingsValues[mid];

  const totalBytesBeforeTransform = metrics.reduce((sum, m) => sum + m.rawBytes, 0);
  const totalBytesAfterTransform = metrics.reduce((sum, m) => sum + m.compactBytes, 0);
  const avgProcessingTimeMs = processingTimes.reduce((a, b) => a + b, 0) / count;

  return {
    count,
    avgSavingsPercent,
    medianSavingsPercent,
    minSavingsPercent,
    maxSavingsPercent,
    totalBytesBeforeTransform,
    totalBytesAfterTransform,
    avgProcessingTimeMs,
  };
}

/**
 * Calculate aggregate statistics from multiple measurements.
 * T040
 */
export function aggregateMetrics(
  metrics: TokenMetrics[],
  groupBy?: 'operation' | 'day'
): AggregateStats | Map<string, AggregateStats> {
  if (!groupBy) {
    return calculateStats(metrics);
  }

  const groups = new Map<string, TokenMetrics[]>();

  for (const metric of metrics) {
    let key: string;
    if (groupBy === 'operation') {
      key = metric.operation;
    } else {
      // Group by day
      key = metric.timestamp.toISOString().split('T')[0];
    }

    const existing = groups.get(key) || [];
    existing.push(metric);
    groups.set(key, existing);
  }

  const result = new Map<string, AggregateStats>();
  for (const [key, groupMetrics] of groups) {
    result.set(key, calculateStats(groupMetrics));
  }

  return result;
}

/**
 * Generate comprehensive benchmark report for validation.
 * T041
 */
export function generateBenchmarkReport(metrics: TokenMetrics[]): BenchmarkReport {
  const generatedAt = new Date();
  const totalMeasurements = metrics.length;
  const overall = calculateStats(metrics);
  const byOperation = aggregateMetrics(metrics, 'operation') as Map<string, AggregateStats>;

  // Find underperforming operations
  const underperformingOperations: BenchmarkReport['underperformingOperations'] = [];

  for (const [operation, stats] of byOperation) {
    const target = TOKEN_SAVINGS_TARGETS[operation] ?? DEFAULT_TARGET;
    if (stats.avgSavingsPercent < target) {
      underperformingOperations.push({
        operation,
        avgSavingsPercent: stats.avgSavingsPercent,
        target,
      });
    }
  }

  const verdict: 'PASS' | 'FAIL' = underperformingOperations.length === 0 ? 'PASS' : 'FAIL';

  // Generate summary
  const summaryLines = [
    'Token Savings Benchmark Report',
    '==============================',
    `Total measurements: ${totalMeasurements}`,
    `Overall average savings: ${overall.avgSavingsPercent.toFixed(1)}%`,
    '',
    'By Operation:',
  ];

  for (const [operation, stats] of byOperation) {
    const target = TOKEN_SAVINGS_TARGETS[operation] ?? DEFAULT_TARGET;
    const status = stats.avgSavingsPercent >= target ? '✅' : '❌';
    summaryLines.push(
      `  ${operation}: ${stats.avgSavingsPercent.toFixed(1)}% avg (target: ${target}%) ${status}`
    );
  }

  summaryLines.push('');
  if (verdict === 'PASS') {
    summaryLines.push('Verdict: PASS - All operations exceed target savings');
  } else {
    summaryLines.push(
      `Verdict: FAIL - ${underperformingOperations.length} operation(s) below target`
    );
    for (const { operation, avgSavingsPercent, target } of underperformingOperations) {
      summaryLines.push(`  - ${operation}: ${avgSavingsPercent.toFixed(1)}% (target: ${target}%)`);
    }
  }

  return {
    generatedAt,
    totalMeasurements,
    overall,
    byOperation,
    underperformingOperations,
    verdict,
    summary: summaryLines.join('\n'),
  };
}
