#!/usr/bin/env bun
/**
 * Sync Memory to Knowledge Hook
 *
 * Syncs high-value memory files (learnings, research) to the
 * knowledge graph. Designed to run on SessionStart to catch up from
 * previous sessions.
 *
 * Updated for PAI Memory System v7.0 (2026-01-12):
 * - Reads from ~/.claude/MEMORY/ instead of ~/.config/pai/history/
 * - Handles LEARNING/ALGORITHM/, LEARNING/SYSTEM/, and RESEARCH/
 * - Supports new frontmatter schema (rating, source, tags)
 * - Handles files without frontmatter
 *
 * Features:
 * - Parses YAML frontmatter for metadata (optional)
 * - Maps memory format to knowledge API
 * - Tracks synced files to avoid duplicates
 * - Graceful degradation when MCP is unavailable
 * - Non-blocking execution (fire and forget)
 *
 * Usage:
 * - As SessionStart hook: Syncs recent files automatically
 * - Manual: bun run sync-memory-to-knowledge.ts [--all] [--dry-run]
 */

import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs';
import { join, basename } from 'node:path';
import { homedir } from 'node:os';
import { createHash } from 'node:crypto';
import { parseMarkdownFile, cleanBody } from './lib/frontmatter-parser';
import {
  loadSyncState,
  saveSyncState,
  getSyncedPaths,
  getContentHashes,
  markAsSynced,
  getSyncStats,
} from './lib/sync-state';
import { checkHealth, addEpisode, type AddEpisodeParams } from './lib/knowledge-client';
import {
  loadSyncConfig,
  getEnabledSources,
} from './lib/sync-config';
import { checkAntiLoop } from './lib/anti-loop-patterns';
import { getSyncStatus, formatSyncStatus } from './lib/sync-status';

/**
 * Generate SHA-256 hash of content for deduplication
 */
function hashContent(content: string): string {
  return createHash('sha256').update(content).digest('hex');
}

/**
 * Memory System source directories to sync
 * Now loaded dynamically from configuration via getEnabledSources()
 * See sync-config.ts for available sources and environment variable controls
 */

// Skip these directories (low entity value or specialized formats)
const _SKIP_PATTERNS = [
  'LEARNING/SIGNALS', // JSONL format, not markdown
  'LEARNING/SYNTHESIS', // Aggregated reports, separate sync if needed
  'WORK', // Work tracking, different structure
  'SECURITY', // Security events, JSONL format
  'STATE', // Runtime state, not knowledge
];

interface SyncOptions {
  dryRun: boolean;
  syncAll: boolean;
  maxFiles: number;
  verbose: boolean;
  showStatus: boolean;
}

const DEFAULT_OPTIONS: SyncOptions = {
  dryRun: false,
  syncAll: false,
  maxFiles: 50, // Limit per run to avoid overwhelming the API
  verbose: false,
  showStatus: false,
};

/**
 * Retry configuration for error recovery
 */
interface RetryConfig {
  maxRetries: number;
  baseDelayMs: number;
  maxDelayMs: number;
}

const RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  baseDelayMs: 1000,
  maxDelayMs: 10000,
};

/**
 * Calculate exponential backoff delay
 */
function getBackoffDelay(attempt: number, config: RetryConfig): number {
  const delay = config.baseDelayMs * 2 ** attempt;
  return Math.min(delay, config.maxDelayMs);
}

/**
 * Wait for MCP server with exponential backoff
 */
async function waitForMcpServer(verbose: boolean): Promise<boolean> {
  for (let attempt = 0; attempt < RETRY_CONFIG.maxRetries; attempt++) {
    const healthy = await checkHealth();
    if (healthy) {
      if (verbose && attempt > 0) {
        console.error(`[Sync] MCP server available after ${attempt + 1} attempts`);
      }
      return true;
    }

    if (attempt < RETRY_CONFIG.maxRetries - 1) {
      const delay = getBackoffDelay(attempt, RETRY_CONFIG);
      if (verbose) {
        console.error(
          `[Sync] MCP server offline, retrying in ${delay}ms (attempt ${attempt + 1}/${RETRY_CONFIG.maxRetries})`
        );
      }
      await new Promise((r) => setTimeout(r, delay));
    }
  }

  return false;
}

/**
 * Get the Memory System directory
 */
function getMemoryDir(): string {
  return join(homedir(), '.claude', 'MEMORY');
}

/**
 * Find all markdown files in a source directory
 * Handles both flat structure and YYYY-MM subdirectories
 */
function findMarkdownFiles(sourceDir: string): string[] {
  if (!existsSync(sourceDir)) {
    return [];
  }

  const files: string[] = [];

  // Check for YYYY-MM subdirectories first
  const subdirs = readdirSync(sourceDir).filter((d) => {
    const fullPath = join(sourceDir, d);
    return statSync(fullPath).isDirectory() && /^\d{4}-\d{2}$/.test(d);
  });

  if (subdirs.length > 0) {
    // Has year-month subdirectories
    for (const subdir of subdirs) {
      const subdirPath = join(sourceDir, subdir);
      const mdFiles = readdirSync(subdirPath)
        .filter((f) => f.endsWith('.md'))
        .map((f) => join(subdirPath, f));

      files.push(...mdFiles);
    }
  } else {
    // Flat directory structure
    const mdFiles = readdirSync(sourceDir)
      .filter((f) => f.endsWith('.md'))
      .map((f) => join(sourceDir, f));

    files.push(...mdFiles);
  }

  // Sort by modification time (newest first)
  files.sort((a, b) => {
    const statA = statSync(a);
    const statB = statSync(b);
    return statB.mtime.getTime() - statA.mtime.getTime();
  });

  return files;
}

/**
 * Map parsed memory file to knowledge API parameters
 */
function mapToKnowledgeParams(
  parsed: ReturnType<typeof parseMarkdownFile>,
  filepath: string,
  sourceType: string
): AddEpisodeParams {
  const { frontmatter, title, body } = parsed;
  const cleanedBody = cleanBody(body);
  const filename = basename(filepath);

  // Build source description from available metadata
  const sourceDescParts: (string | null)[] = [];

  if (frontmatter.source) {
    sourceDescParts.push(`Source: ${frontmatter.source}`);
  }
  if (frontmatter.session_id) {
    sourceDescParts.push(`Session: ${frontmatter.session_id.slice(0, 8)}`);
  }
  if (frontmatter.rating) {
    sourceDescParts.push(`Rating: ${frontmatter.rating}/10`);
  }
  sourceDescParts.push(`File: ${filename}`);

  const captureType = frontmatter.capture_type || sourceType;

  return {
    name: `${captureType}: ${title}`.slice(0, 200),
    episode_body: cleanedBody.slice(0, 5000),
    source: 'text',
    source_description: sourceDescParts.filter(Boolean).join(' | '),
    reference_timestamp: frontmatter.timestamp,
    group_id: captureType.toLowerCase(),
  };
}

/**
 * Check if an error is retryable
 */
function isRetryableError(error: string | undefined): boolean {
  if (!error) return false;
  const retryablePatterns = [
    'timeout',
    'ECONNREFUSED',
    'ECONNRESET',
    'ETIMEDOUT',
    'abort',
    '429',
    '503',
    '502',
    '504',
    'rate limit',
  ];
  const lowerError = error.toLowerCase();
  return retryablePatterns.some((pattern) => lowerError.includes(pattern.toLowerCase()));
}

/**
 * Sync a single file to knowledge graph with retry logic
 */
async function syncFile(
  filepath: string,
  sourceType: string,
  options: SyncOptions
): Promise<{ success: boolean; error?: string }> {
  try {
    const content = readFileSync(filepath, 'utf-8');
    const filename = basename(filepath);
    const parsed = parseMarkdownFile(content, filename);
    const params = mapToKnowledgeParams(parsed, filepath, sourceType);

    if (options.verbose) {
      console.error(`[Sync] Processing: ${params.name}`);
    }

    if (options.dryRun) {
      console.error(`[DryRun] Would sync: ${params.name}`);
      return { success: true };
    }

    // Retry loop for transient failures
    let lastError: string | undefined;
    for (let attempt = 0; attempt < RETRY_CONFIG.maxRetries; attempt++) {
      const result = await addEpisode(params);

      if (result.success) {
        if (options.verbose) {
          console.error(
            `[Sync] ✓ Synced: ${params.name}${attempt > 0 ? ` (attempt ${attempt + 1})` : ''}`
          );
        }
        return { success: true };
      }

      lastError = result.error;

      // Only retry on retryable errors
      if (!isRetryableError(lastError)) {
        break;
      }

      if (attempt < RETRY_CONFIG.maxRetries - 1) {
        const delay = getBackoffDelay(attempt, RETRY_CONFIG);
        if (options.verbose) {
          console.error(`[Sync] Retrying ${params.name} in ${delay}ms (attempt ${attempt + 1})`);
        }
        await new Promise((r) => setTimeout(r, delay));
      }
    }

    console.error(`[Sync] ✗ Failed: ${params.name} - ${lastError}`);
    return { success: false, error: lastError };
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    console.error(`[Sync] ✗ Error processing ${filepath}: ${message}`);
    return { success: false, error: message };
  }
}

/**
 * Main sync function
 */
async function syncMemoryToKnowledge(options: SyncOptions = DEFAULT_OPTIONS): Promise<{
  synced: number;
  failed: number;
  skipped: number;
}> {
  const memoryDir = getMemoryDir();

  const stats = { synced: 0, failed: 0, skipped: 0 };

  // Load sync configuration from environment variables
  const syncConfig = loadSyncConfig();

  // Merge config into options (config takes precedence for env-controlled settings)
  const effectiveOptions: SyncOptions = {
    ...options,
    verbose: options.verbose || syncConfig.verbose,
    maxFiles: syncConfig.maxFilesPerSync,
  };

  // Check if memory directory exists
  if (!existsSync(memoryDir)) {
    console.error(`[Sync] Memory directory not found: ${memoryDir}`);
    return stats;
  }

  // Get enabled sources based on configuration
  const enabledSources = getEnabledSources(syncConfig);

  if (enabledSources.length === 0) {
    if (effectiveOptions.verbose) {
      console.error('[Sync] No sync sources enabled in configuration');
    }
    return stats;
  }

  if (effectiveOptions.verbose) {
    console.error(`[Sync] Enabled sources: ${enabledSources.map((s) => s.path).join(', ')}`);
    if (syncConfig.customExcludePatterns.length > 0) {
      console.error(`[Sync] Custom exclude patterns: ${syncConfig.customExcludePatterns.join(', ')}`);
    }
  }

  // Check if MCP is healthy with retry logic
  if (!effectiveOptions.dryRun) {
    const healthy = await waitForMcpServer(effectiveOptions.verbose);
    if (!healthy) {
      console.error('[Sync] MCP server offline after retries - skipping sync');
      return stats;
    }
  }

  // Load sync state
  const syncState = loadSyncState();
  const syncedPaths = getSyncedPaths(syncState);
  const syncedHashes = getContentHashes(syncState);

  if (effectiveOptions.verbose) {
    const stateStats = getSyncStats(syncState);
    console.error(
      `[Sync] Previously synced: ${stateStats.totalSynced} files, ${syncedHashes.size} unique hashes`
    );
  }

  // Collect files to sync from enabled sources
  const filesToSync: { filepath: string; sourceType: string }[] = [];

  for (const source of enabledSources) {
    const sourceDir = join(memoryDir, source.path);
    const files = findMarkdownFiles(sourceDir);

    if (effectiveOptions.verbose && files.length > 0) {
      console.error(`[Sync] Found ${files.length} files in ${source.path}`);
    }

    for (const file of files) {
      if (!effectiveOptions.syncAll && syncedPaths.has(file)) {
        stats.skipped++;
        continue;
      }

      filesToSync.push({ filepath: file, sourceType: source.type });

      if (filesToSync.length >= effectiveOptions.maxFiles) {
        break;
      }
    }

    if (filesToSync.length >= effectiveOptions.maxFiles) {
      break;
    }
  }

  if (effectiveOptions.verbose) {
    console.error(`[Sync] Found ${filesToSync.length} files to sync`);
  }

  if (filesToSync.length === 0) {
    console.error('[Sync] No new files to sync');
    return stats;
  }

  // Sync files
  for (const { filepath, sourceType } of filesToSync) {
    // Pre-check content hash for deduplication and anti-loop detection
    let contentHash: string | undefined;
    let captureType = sourceType;
    let fileTitle = '';
    let fileBody = '';

    try {
      const content = readFileSync(filepath, 'utf-8');
      const filename = basename(filepath);
      const parsed = parseMarkdownFile(content, filename);
      const cleanedBody = cleanBody(parsed.body);
      contentHash = hashContent(cleanedBody);
      captureType = parsed.frontmatter.capture_type || sourceType;
      fileTitle = parsed.title;
      fileBody = cleanedBody;

      // Anti-loop detection: Skip files containing knowledge operations
      const antiLoopResult = checkAntiLoop(fileTitle, fileBody, syncConfig.customExcludePatterns);
      if (antiLoopResult.matches) {
        if (effectiveOptions.verbose) {
          console.error(
            `[Sync] Skipping (anti-loop: ${antiLoopResult.matchedPattern}): ${filepath}`
          );
        }
        stats.skipped++;
        // Mark as synced to avoid re-checking
        if (!effectiveOptions.dryRun) {
          markAsSynced(syncState, filepath, captureType, undefined, contentHash);
        }
        continue;
      }

      // Skip if content already synced (even from a different file)
      if (syncedHashes.has(contentHash)) {
        if (effectiveOptions.verbose) {
          console.error(`[Sync] Skipping duplicate content: ${filepath}`);
        }
        stats.skipped++;
        // Mark filepath as synced to avoid re-checking (only if not dry run)
        if (!effectiveOptions.dryRun) {
          markAsSynced(syncState, filepath, captureType, undefined, contentHash);
        }
        continue;
      }
    } catch {
      // Continue with sync attempt if pre-check fails
    }

    const result = await syncFile(filepath, sourceType, effectiveOptions);

    if (result.success) {
      stats.synced++;

      if (!effectiveOptions.dryRun) {
        try {
          const content = readFileSync(filepath, 'utf-8');
          const filename = basename(filepath);
          const parsed = parseMarkdownFile(content, filename);
          markAsSynced(
            syncState,
            filepath,
            parsed.frontmatter.capture_type || sourceType,
            undefined,
            contentHash
          );
          // Add hash to in-memory set for this run
          if (contentHash) syncedHashes.add(contentHash);
        } catch {
          // Continue even if marking fails
        }
      }
    } else {
      stats.failed++;
    }

    // Brief pause between API calls
    if (!effectiveOptions.dryRun && stats.synced % 5 === 0) {
      await new Promise((r) => setTimeout(r, 100));
    }
  }

  // Save sync state (also save if we skipped duplicates, as we marked them)
  if (!effectiveOptions.dryRun && (stats.synced > 0 || stats.skipped > 0)) {
    saveSyncState(syncState);
  }

  console.error(
    `[Sync] Complete: ${stats.synced} synced, ${stats.failed} failed, ${stats.skipped} skipped`
  );

  return stats;
}

/**
 * Parse command line arguments
 */
function parseArgs(args: string[]): SyncOptions {
  const options = { ...DEFAULT_OPTIONS };

  for (const arg of args) {
    switch (arg) {
      case '--dry-run':
      case '-n':
        options.dryRun = true;
        break;
      case '--all':
      case '-a':
        options.syncAll = true;
        break;
      case '--verbose':
      case '-v':
        options.verbose = true;
        break;
      case '--status':
      case '-s':
        options.showStatus = true;
        break;
      default:
        if (arg.startsWith('--max=')) {
          options.maxFiles = Number.parseInt(arg.slice(6), 10) || 50;
        }
    }
  }

  return options;
}

/**
 * Main entry point
 */
async function main() {
  // Check if running as hook (stdin available) or CLI
  const isHook = !process.stdin.isTTY;

  if (isHook) {
    // Running as hook - quick sync, non-blocking
    try {
      // Read and discard stdin (hook payload)
      await Bun.stdin.text().catch(() => '');

      // Run sync with defaults (limited files, not verbose)
      await syncMemoryToKnowledge({
        ...DEFAULT_OPTIONS,
        maxFiles: 20, // Limit for hook execution
      });
    } catch (error) {
      console.error('[Sync Hook] Error:', error);
    }
  } else {
    // Running as CLI - parse args
    const args = process.argv.slice(2);
    const options = parseArgs(args);

    // Handle --status option
    if (options.showStatus) {
      const status = getSyncStatus();
      console.log(formatSyncStatus(status));
      process.exit(0);
    }

    if (options.verbose) {
      console.error('[Sync] Running in CLI mode');
      console.error(`[Sync] Options: ${JSON.stringify(options)}`);
      console.error(`[Sync] Memory directory: ${getMemoryDir()}`);
    }

    await syncMemoryToKnowledge(options);
  }

  process.exit(0);
}

main();
