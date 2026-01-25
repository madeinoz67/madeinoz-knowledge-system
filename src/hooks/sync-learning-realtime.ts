#!/usr/bin/env bun
/**
 * Real-time Learning Sync Hook
 *
 * Syncs newly created learning files to the knowledge graph immediately
 * after they are created (runs after Stop hook).
 *
 * Updated for PAI Memory System v7.0 (2026-01-12):
 * - Reads from ~/.claude/MEMORY/LEARNING/ instead of ~/.config/pai/history/learnings/
 * - Handles both ALGORITHM and SYSTEM subdirectories
 * - Supports new frontmatter schema
 *
 * Features:
 * - Syncs only the most recent learning file
 * - Excludes sessions containing knowledge tool operations (prevents feedback loop)
 * - Uses content hashing to prevent duplicates
 * - Non-blocking execution
 *
 * Usage:
 * - As Stop hook: Runs automatically after stop-hook.ts
 * - Manual: bun run sync-learning-realtime.ts [--verbose]
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
} from './lib/sync-state';
import { checkHealth, addEpisode, type AddEpisodeParams } from './lib/knowledge-client';

// Tools that indicate knowledge system operations (prevent feedback loop)
const KNOWLEDGE_TOOL_PATTERNS = [
  'mcp__madeinoz-knowledge__',
  'search_memory',
  'add_memory',
  'get_episodes',
  'knowledge graph',
  'what do i know',
  'what do you know',
];

interface SyncOptions {
  verbose: boolean;
  dryRun: boolean;
}

/**
 * Check if content contains knowledge tool operations
 */
function containsKnowledgeOperations(content: string): boolean {
  const lowerContent = content.toLowerCase();
  return KNOWLEDGE_TOOL_PATTERNS.some((pattern) => lowerContent.includes(pattern.toLowerCase()));
}

/**
 * Generate SHA-256 hash of content
 */
function hashContent(content: string): string {
  return createHash('sha256').update(content).digest('hex');
}

/**
 * Get the Memory System directory
 */
function getMemoryDir(): string {
  return join(homedir(), '.claude', 'MEMORY');
}

/**
 * Find the most recently created learning file
 * Checks both LEARNING/ALGORITHM and LEARNING/SYSTEM directories
 */
function findLatestLearning(): string | null {
  const memoryDir = getMemoryDir();
  const learningDirs = [
    join(memoryDir, 'LEARNING', 'ALGORITHM'),
    join(memoryDir, 'LEARNING', 'SYSTEM'),
  ];

  const allFiles: { path: string; mtime: number }[] = [];

  for (const learningDir of learningDirs) {
    if (!existsSync(learningDir)) {
      continue;
    }

    // Get year-month subdirectories
    const subdirs = readdirSync(learningDir).filter((d) => {
      const fullPath = join(learningDir, d);
      return statSync(fullPath).isDirectory() && /^\d{4}-\d{2}$/.test(d);
    });

    if (subdirs.length === 0) {
      continue;
    }

    // Sort to get most recent month
    subdirs.sort().reverse();
    const latestMonth = subdirs[0];
    const monthDir = join(learningDir, latestMonth);

    // Get all markdown files in the latest month
    const files = readdirSync(monthDir)
      .filter((f) => f.endsWith('.md'))
      .map((f) => ({
        path: join(monthDir, f),
        mtime: statSync(join(monthDir, f)).mtime.getTime(),
      }));

    allFiles.push(...files);
  }

  if (allFiles.length === 0) {
    return null;
  }

  // Sort by modification time (newest first) and return the latest
  allFiles.sort((a, b) => b.mtime - a.mtime);
  return allFiles[0].path;
}

/**
 * Sync a single learning file to knowledge
 */
async function syncLearning(
  filepath: string,
  options: SyncOptions
): Promise<{ success: boolean; reason?: string }> {
  try {
    const content = readFileSync(filepath, 'utf-8');
    const filename = basename(filepath);
    const parsed = parseMarkdownFile(content, filename);
    const cleanedBody = cleanBody(parsed.body);

    // Check for knowledge operations (prevent feedback loop)
    if (containsKnowledgeOperations(content)) {
      return {
        success: false,
        reason: 'Contains knowledge operations (feedback loop prevention)',
      };
    }

    // Check content hash for duplicates
    const contentHash = hashContent(cleanedBody);
    const syncState = loadSyncState();
    const syncedHashes = getContentHashes(syncState);

    if (syncedHashes.has(contentHash)) {
      return { success: false, reason: 'Duplicate content (already synced)' };
    }

    // Check if filepath already synced
    const syncedPaths = getSyncedPaths(syncState);
    if (syncedPaths.has(filepath)) {
      return { success: false, reason: 'File already synced' };
    }

    // Build source description
    const sourceDescParts: string[] = [];
    if (parsed.frontmatter.source) {
      sourceDescParts.push(`Source: ${parsed.frontmatter.source}`);
    }
    if (parsed.frontmatter.session_id) {
      sourceDescParts.push(`Session: ${parsed.frontmatter.session_id.slice(0, 8)}`);
    }
    if (parsed.frontmatter.rating) {
      sourceDescParts.push(`Rating: ${parsed.frontmatter.rating}/10`);
    }
    sourceDescParts.push('Realtime sync');

    // Prepare episode parameters
    const captureType = parsed.frontmatter.capture_type || 'LEARNING';
    const params: AddEpisodeParams = {
      name: `${captureType}: ${parsed.title}`.slice(0, 200),
      episode_body: cleanedBody.slice(0, 5000),
      source: 'text',
      source_description: sourceDescParts.join(' | '),
      group_id: captureType.toLowerCase(),
    };

    if (options.verbose) {
      console.error(`[RealtimeSync] Syncing: ${params.name}`);
    }

    if (options.dryRun) {
      console.error(`[DryRun] Would sync: ${params.name}`);
      return { success: true };
    }

    // Sync to knowledge
    const result = await addEpisode(params);

    if (result.success) {
      // Mark as synced
      markAsSynced(syncState, filepath, captureType, undefined, contentHash);
      saveSyncState(syncState);

      if (options.verbose) {
        console.error(`[RealtimeSync] ✓ Synced: ${params.name}`);
      }
      return { success: true };
    }
    return { success: false, reason: result.error };
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return { success: false, reason: message };
  }
}

/**
 * Main entry point
 */
async function main() {
  const args = process.argv.slice(2);
  const options: SyncOptions = {
    verbose: args.includes('--verbose') || args.includes('-v'),
    dryRun: args.includes('--dry-run') || args.includes('-n'),
  };

  // Check if running as hook (stdin available)
  const isHook = !process.stdin.isTTY;

  if (isHook) {
    // Consume stdin (hook payload)
    await Bun.stdin.text().catch(() => '');
  }

  // Check MCP health
  if (!options.dryRun) {
    const healthy = await checkHealth();
    if (!healthy) {
      if (options.verbose) {
        console.error('[RealtimeSync] MCP server offline - skipping');
      }
      process.exit(0);
    }
  }

  // Find latest learning
  const latestLearning = findLatestLearning();

  if (!latestLearning) {
    if (options.verbose) {
      console.error('[RealtimeSync] No learning files found');
    }
    process.exit(0);
  }

  if (options.verbose) {
    console.error(`[RealtimeSync] Latest learning: ${latestLearning}`);
  }

  // Sync it
  const result = await syncLearning(latestLearning, options);

  if (result.success) {
    console.error('[RealtimeSync] ✓ Learning synced to knowledge graph');
  } else if (options.verbose) {
    console.error(`[RealtimeSync] Skipped: ${result.reason}`);
  }

  process.exit(0);
}

main();
