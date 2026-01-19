/**
 * Transformation logging for MCP wrapper
 * Logs transformation failures and slow operations
 * @module transformation-log
 */

import { appendFile, mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';
import { homedir } from 'node:os';

export interface TransformationLog {
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

/** Default log file path */
export const DEFAULT_LOG_PATH = `${homedir()}/.madeinoz-knowledge/wrapper.log`;

/** Performance thresholds */
export const SLOW_THRESHOLD_MS = 50;
export const TIMEOUT_THRESHOLD_MS = 100;

/**
 * Generate a simple UUID v4
 */
function generateId(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Format a log entry for file output
 */
function formatLogEntry(log: TransformationLog): string {
  const timestamp = log.timestamp.toISOString();
  const level = log.level.toUpperCase().padEnd(5);
  const operation = log.operation.padEnd(15);
  const fallback = log.usedFallback ? '[FALLBACK]' : '';
  const time = log.processingTimeMs ? `${log.processingTimeMs}ms` : '';
  const error = log.error ? `: ${log.error}` : '';

  return `${timestamp} ${level} ${operation} ${fallback} ${time}${error}`.trim();
}

/**
 * Log a transformation event to file
 */
export async function logTransformation(
  log: Omit<TransformationLog, 'id' | 'timestamp'>
): Promise<void> {
  const entry: TransformationLog = {
    ...log,
    id: generateId(),
    timestamp: new Date(),
  };

  const logPath = process.env.MADEINOZ_WRAPPER_LOG_FILE || DEFAULT_LOG_PATH;

  try {
    // Ensure directory exists
    await mkdir(dirname(logPath), { recursive: true });

    // Append log entry
    const line = formatLogEntry(entry) + '\n';
    await appendFile(logPath, line, 'utf-8');
  } catch (error) {
    // Silently fail - logging should not break the wrapper
    console.error('[transformation-log] Failed to write log:', error);
  }
}

/**
 * Log a transformation failure (convenience function)
 */
export async function logTransformationFailure(
  operation: string,
  inputSize: number,
  error: string,
  processingTimeMs?: number
): Promise<void> {
  await logTransformation({
    level: 'error',
    operation,
    inputSize,
    error,
    processingTimeMs,
    usedFallback: true,
  });
}

/**
 * Log a slow transformation warning (convenience function)
 */
export async function logSlowTransformation(
  operation: string,
  inputSize: number,
  processingTimeMs: number
): Promise<void> {
  await logTransformation({
    level: 'warn',
    operation,
    inputSize,
    processingTimeMs,
    usedFallback: false,
  });
}

/**
 * Log successful transformation (info level, optional)
 */
export async function logTransformationSuccess(
  operation: string,
  inputSize: number,
  processingTimeMs: number
): Promise<void> {
  // Only log if processing was slow but within threshold
  if (processingTimeMs >= SLOW_THRESHOLD_MS) {
    await logSlowTransformation(operation, inputSize, processingTimeMs);
  }
}
