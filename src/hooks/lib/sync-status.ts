/**
 * Sync Status Module
 *
 * Provides a unified view of sync configuration and recent activity.
 * Combines data from sync-config.ts and sync-state.ts.
 *
 * Feature: 007-configurable-memory-sync
 */

import {
  loadSyncConfig,
  getAllSourcesWithStatus,
  formatConfig,
  type SyncConfiguration,
  type SyncSource,
} from './sync-config';
import {
  loadSyncState,
  getSyncStats,
  getRecentlySynced,
  type SyncState,
  type SyncedFile,
} from './sync-state';

/**
 * Sync activity statistics.
 */
export interface SyncActivityStats {
  /** Total files synced (all time) */
  totalSynced: number;

  /** Files synced by capture type */
  byType: Record<string, number>;

  /** Last sync timestamp (ISO 8601) */
  lastSync: string;

  /** Files synced in the last 24 hours */
  recentCount: number;

  /** Recent synced files (last 24 hours) */
  recentFiles: SyncedFile[];
}

/**
 * Complete sync status.
 */
export interface SyncStatus {
  /** Current configuration */
  config: SyncConfiguration;

  /** All sources with their enabled status */
  sources: SyncSource[];

  /** Sync activity statistics */
  activity: SyncActivityStats;
}

/**
 * Get complete sync status.
 */
export function getSyncStatus(): SyncStatus {
  const config = loadSyncConfig();
  const sources = getAllSourcesWithStatus(config);
  const state = loadSyncState();
  const stats = getSyncStats(state);
  const recentFiles = getRecentlySynced(state, 24);

  return {
    config,
    sources,
    activity: {
      totalSynced: stats.totalSynced,
      byType: stats.byType,
      lastSync: stats.lastSync,
      recentCount: recentFiles.length,
      recentFiles,
    },
  };
}

/**
 * Format sync status for display.
 */
export function formatSyncStatus(status?: SyncStatus): string {
  const s = status || getSyncStatus();
  const lines: string[] = [];

  // Configuration section
  lines.push('=== Sync Configuration ===');
  lines.push('');
  lines.push('Sources:');
  for (const source of s.sources) {
    const status = source.enabled ? '\u2705 enabled' : '\u274c disabled';
    lines.push(`  ${source.path}: ${status}`);
  }
  lines.push('');
  lines.push(`Max files per sync: ${s.config.maxFilesPerSync}`);
  lines.push(`Verbose logging: ${s.config.verbose ? 'enabled' : 'disabled'}`);

  if (s.config.customExcludePatterns.length > 0) {
    lines.push(`Custom exclude patterns: ${s.config.customExcludePatterns.join(', ')}`);
  }

  // Activity section
  lines.push('');
  lines.push('=== Sync Activity ===');
  lines.push('');

  if (s.activity.lastSync) {
    const lastSyncDate = new Date(s.activity.lastSync);
    lines.push(`Last sync: ${lastSyncDate.toLocaleString()}`);
  } else {
    lines.push('Last sync: never');
  }

  lines.push(`Total files synced: ${s.activity.totalSynced}`);

  if (Object.keys(s.activity.byType).length > 0) {
    lines.push('By type:');
    for (const [type, count] of Object.entries(s.activity.byType)) {
      lines.push(`  ${type}: ${count}`);
    }
  }

  lines.push('');
  lines.push(`Recent (24h): ${s.activity.recentCount} files`);

  if (s.activity.recentFiles.length > 0 && s.activity.recentFiles.length <= 10) {
    lines.push('Recent files:');
    for (const file of s.activity.recentFiles.slice(0, 10)) {
      const syncTime = new Date(file.synced_at).toLocaleTimeString();
      lines.push(`  [${syncTime}] ${file.filepath}`);
    }
  }

  return lines.join('\n');
}

/**
 * Get sync status as JSON (for programmatic use).
 */
export function getSyncStatusJson(): string {
  const status = getSyncStatus();
  return JSON.stringify(status, null, 2);
}
