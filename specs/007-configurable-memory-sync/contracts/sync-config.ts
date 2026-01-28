/**
 * Sync Configuration Contract
 *
 * Defines the interfaces for configurable memory-to-knowledge sync.
 * These types should be implemented in src/hooks/lib/sync-config.ts
 *
 * Feature: 007-configurable-memory-sync
 * Date: 2026-01-28
 */

// ============================================================================
// Configuration Types
// ============================================================================

/**
 * Main sync configuration loaded from environment variables.
 * Controls which memory sources are synced and how.
 */
export interface SyncConfiguration {
  /** Enable sync for LEARNING/ALGORITHM directory */
  syncLearningAlgorithm: boolean;

  /** Enable sync for LEARNING/SYSTEM directory */
  syncLearningSystem: boolean;

  /** Enable sync for RESEARCH directory */
  syncResearch: boolean;

  /** Custom patterns to always exclude (in addition to built-in anti-loop) */
  customExcludePatterns: string[];

  /** Maximum files to process per sync run (1-1000) */
  maxFilesPerSync: number;

  /** Enable verbose logging */
  verbose: boolean;

  /** Dry run mode - log but don't actually sync */
  dryRun: boolean;
}

/**
 * Environment variable names for sync configuration.
 * All prefixed with MADEINOZ_KNOWLEDGE_ for PAI integration.
 */
export const SYNC_CONFIG_ENV_VARS = {
  SYNC_LEARNING_ALGORITHM: 'MADEINOZ_KNOWLEDGE_SYNC_LEARNING_ALGORITHM',
  SYNC_LEARNING_SYSTEM: 'MADEINOZ_KNOWLEDGE_SYNC_LEARNING_SYSTEM',
  SYNC_RESEARCH: 'MADEINOZ_KNOWLEDGE_SYNC_RESEARCH',
  SYNC_EXCLUDE_PATTERNS: 'MADEINOZ_KNOWLEDGE_SYNC_EXCLUDE_PATTERNS',
  SYNC_MAX_FILES: 'MADEINOZ_KNOWLEDGE_SYNC_MAX_FILES',
  SYNC_VERBOSE: 'MADEINOZ_KNOWLEDGE_SYNC_VERBOSE',
} as const;

/**
 * Default configuration values.
 */
export const DEFAULT_SYNC_CONFIG: SyncConfiguration = {
  syncLearningAlgorithm: true,
  syncLearningSystem: true,
  syncResearch: true,
  customExcludePatterns: [],
  maxFilesPerSync: 50,
  verbose: false,
  dryRun: false,
};

// ============================================================================
// Source Types
// ============================================================================

/**
 * A memory source directory that can be synced.
 */
export interface SyncSource {
  /** Relative path from MEMORY directory (e.g., 'LEARNING/ALGORITHM') */
  path: string;

  /** Default capture type for content from this source */
  type: 'LEARNING' | 'RESEARCH';

  /** Human-readable description */
  description: string;

  /** Whether this source is enabled for sync (from configuration) */
  enabled: boolean;
}

/**
 * External configuration file format for sync sources.
 * File location: config/sync-sources.json
 */
export interface SyncSourceConfigFile {
  /** Schema version for future compatibility */
  version: '1.0';

  /** Array of sync source definitions */
  sources: Array<{
    /** Unique identifier for this source (used in env var names) */
    id: string;

    /** Relative path from MEMORY directory */
    path: string;

    /** Content type for this source */
    type: 'LEARNING' | 'RESEARCH';

    /** Human-readable description */
    description: string;

    /** Default enabled state if no env var set */
    defaultEnabled: boolean;
  }>;
}

// ============================================================================
// Anti-Loop Types
// ============================================================================

/**
 * Pattern types for anti-loop detection.
 */
export type PatternMatchType = 'contains' | 'regex';

/**
 * Where to apply the pattern check.
 */
export type PatternScope = 'body' | 'title' | 'both';

/**
 * A pattern used to detect knowledge-derived content.
 */
export interface AntiLoopPattern {
  /** The pattern string to match */
  pattern: string;

  /** Human-readable description of what this catches */
  description: string;

  /** Match type: 'contains' (substring) or 'regex' (full regex) */
  matchType: PatternMatchType;

  /** Where to apply the check */
  scope: PatternScope;
}

/**
 * Built-in anti-loop patterns.
 * These cannot be disabled and are always applied.
 */
export const BUILTIN_ANTI_LOOP_PATTERNS: AntiLoopPattern[] = [
  // MCP tool patterns
  { pattern: 'mcp__madeinoz-knowledge__', matchType: 'contains', scope: 'both', description: 'MCP tool invocations' },
  { pattern: 'search_memory', matchType: 'contains', scope: 'both', description: 'Memory search operations' },
  { pattern: 'add_memory', matchType: 'contains', scope: 'both', description: 'Memory add operations' },
  { pattern: 'get_episodes', matchType: 'contains', scope: 'both', description: 'Episode retrieval' },
  { pattern: 'search_memory_nodes', matchType: 'contains', scope: 'both', description: 'Node search operation' },
  { pattern: 'search_memory_facts', matchType: 'contains', scope: 'both', description: 'Facts search operation' },

  // Natural language patterns
  { pattern: 'knowledge graph', matchType: 'contains', scope: 'both', description: 'Knowledge graph references' },
  { pattern: 'what do i know', matchType: 'contains', scope: 'both', description: 'Common query phrase' },
  { pattern: 'what do you know', matchType: 'contains', scope: 'both', description: 'Common query phrase' },

  // Output format patterns
  { pattern: 'LEARNING: Search', matchType: 'contains', scope: 'title', description: 'Search result learnings' },
  { pattern: 'Knowledge Found:', matchType: 'contains', scope: 'body', description: 'Formatted search output' },
  { pattern: 'Key Entities:', matchType: 'contains', scope: 'body', description: 'Knowledge query output' },
];

// ============================================================================
// Decision Types
// ============================================================================

/**
 * Possible outcomes of a sync decision.
 */
export type SyncDecisionOutcome = 'synced' | 'skipped' | 'failed';

/**
 * Reasons for skipping a file.
 */
export type SkipReason =
  | 'source_disabled'
  | 'path_already_synced'
  | 'content_already_synced'
  | 'anti_loop_detected'
  | 'custom_pattern_match';

/**
 * Reasons for sync failure.
 */
export type FailReason =
  | 'mcp_offline'
  | 'api_error'
  | 'parse_error'
  | 'timeout';

/**
 * A record of a sync decision for a single file.
 */
export interface SyncDecision {
  /** Absolute path to the memory file */
  filepath: string;

  /** Decision outcome */
  decision: SyncDecisionOutcome;

  /** Reason for the decision */
  reason: string;

  /** Structured reason code */
  reasonCode: SkipReason | FailReason | 'success';

  /** Timestamp of the decision (ISO 8601) */
  timestamp: string;

  /** Content hash (if computed) */
  contentHash?: string;

  /** Episode UUID (if synced successfully) */
  episodeUuid?: string;

  /** Source type of the file */
  sourceType?: 'LEARNING' | 'RESEARCH';
}

// ============================================================================
// Function Signatures
// ============================================================================

/**
 * Load sync configuration from environment variables.
 * Returns defaults for any missing or invalid values.
 */
export type LoadSyncConfig = () => SyncConfiguration;

/**
 * Check if content matches any anti-loop pattern.
 * @param title - The file title (from frontmatter or filename)
 * @param body - The file body content
 * @param customPatterns - Additional patterns from configuration
 * @returns Object with match result and matched pattern description
 */
export type CheckAntiLoop = (
  title: string,
  body: string,
  customPatterns?: string[]
) => { matches: boolean; matchedPattern?: string };

/**
 * Get enabled sync sources based on configuration.
 */
export type GetEnabledSources = (config: SyncConfiguration) => SyncSource[];

/**
 * Load sync source definitions from external configuration file.
 * Falls back to built-in defaults if file is missing or invalid.
 */
export type LoadSyncSources = () => SyncSourceConfigFile['sources'];

/**
 * Log a sync decision.
 */
export type LogSyncDecision = (decision: SyncDecision, verbose: boolean) => void;
