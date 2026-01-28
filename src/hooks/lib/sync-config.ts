/**
 * Sync Configuration Loader
 *
 * Loads and validates sync configuration from environment variables and config files.
 * Controls which memory sources are synced to the knowledge graph.
 *
 * Feature: 007-configurable-memory-sync
 *
 * External Configuration (config/sync-sources.json):
 * - sources: Array of sync source definitions (path, type, defaultEnabled)
 * - customExcludePatterns: Array of patterns to exclude from sync (substring or /regex/)
 *
 * Environment Variables (override config file):
 * - MADEINOZ_KNOWLEDGE_SYNC_LEARNING_ALGORITHM: Enable LEARNING/ALGORITHM sync (default: true)
 * - MADEINOZ_KNOWLEDGE_SYNC_LEARNING_SYSTEM: Enable LEARNING/SYSTEM sync (default: true)
 * - MADEINOZ_KNOWLEDGE_SYNC_RESEARCH: Enable RESEARCH sync (default: true)
 * - MADEINOZ_KNOWLEDGE_SYNC_EXCLUDE_PATTERNS: Comma-separated custom exclude patterns (overrides config file)
 * - MADEINOZ_KNOWLEDGE_SYNC_MAX_FILES: Max files per sync run (default: 50)
 * - MADEINOZ_KNOWLEDGE_SYNC_VERBOSE: Enable verbose logging (default: false)
 */

import { existsSync, readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

/**
 * Main sync configuration.
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
 */
export interface SyncSourceConfigFile {
  version: '1.0';
  sources: Array<{
    id: string;
    path: string;
    type: 'LEARNING' | 'RESEARCH';
    description: string;
    defaultEnabled: boolean;
  }>;
  /** Custom patterns to exclude (in addition to built-in anti-loop patterns) */
  customExcludePatterns?: string[];
}

/**
 * Built-in default sync sources (used when config file is missing).
 */
const DEFAULT_SYNC_SOURCES: SyncSourceConfigFile['sources'] = [
  { id: 'LEARNING_ALGORITHM', path: 'LEARNING/ALGORITHM', type: 'LEARNING', description: 'Task execution learnings', defaultEnabled: true },
  { id: 'LEARNING_SYSTEM', path: 'LEARNING/SYSTEM', type: 'LEARNING', description: 'PAI/tooling learnings', defaultEnabled: true },
  { id: 'RESEARCH', path: 'RESEARCH', type: 'RESEARCH', description: 'Agent research outputs', defaultEnabled: true },
];

/**
 * Cached sync sources (loaded once per process).
 */
let cachedSyncSources: SyncSourceConfigFile['sources'] | null = null;

/**
 * Cached custom exclude patterns (loaded once per process).
 */
let cachedCustomExcludePatterns: string[] | null = null;

/**
 * Get the config directory path.
 * When installed: ~/.claude/config/
 * When running from source: {projectRoot}/config/
 */
function getConfigDir(): string {
  const __filename = fileURLToPath(import.meta.url);
  const __dirname = dirname(__filename);

  // Check if we're running from installed location (~/.claude/hooks/lib/)
  const homeDir = process.env.HOME || process.env.USERPROFILE || '';
  const installedPath = join(homeDir, '.claude', 'hooks', 'lib');

  if (__dirname === installedPath || __dirname.startsWith(installedPath)) {
    // Installed: config lives at ~/.claude/config/
    return join(homeDir, '.claude', 'config');
  }

  // Development: src/hooks/lib -> project root (3 levels up) -> config/
  return join(__dirname, '..', '..', '..', 'config');
}

/**
 * Load sync sources from external configuration file.
 * Falls back to built-in defaults if file is missing or invalid.
 */
export function loadSyncSources(): SyncSourceConfigFile['sources'] {
  if (cachedSyncSources !== null) {
    return cachedSyncSources;
  }

  const configPath = join(getConfigDir(), 'sync-sources.json');

  if (!existsSync(configPath)) {
    cachedSyncSources = DEFAULT_SYNC_SOURCES;
    return cachedSyncSources;
  }

  try {
    const content = readFileSync(configPath, 'utf-8');
    const config: SyncSourceConfigFile = JSON.parse(content);

    // Validate version
    if (config.version !== '1.0') {
      console.error(`[SyncConfig] Warning: Unknown config version ${config.version}, using defaults`);
      cachedSyncSources = DEFAULT_SYNC_SOURCES;
      return cachedSyncSources;
    }

    // Validate sources array
    if (!Array.isArray(config.sources) || config.sources.length === 0) {
      console.error('[SyncConfig] Warning: Invalid or empty sources array, using defaults');
      cachedSyncSources = DEFAULT_SYNC_SOURCES;
      return cachedSyncSources;
    }

    // Validate each source
    const validSources: SyncSourceConfigFile['sources'] = [];
    for (const source of config.sources) {
      if (!source.id || !source.path || !source.type || !source.description) {
        console.error(`[SyncConfig] Warning: Invalid source entry (missing fields), skipping: ${JSON.stringify(source)}`);
        continue;
      }
      if (source.type !== 'LEARNING' && source.type !== 'RESEARCH') {
        console.error(`[SyncConfig] Warning: Invalid source type "${source.type}" for ${source.id}, skipping`);
        continue;
      }
      validSources.push(source);
    }

    if (validSources.length === 0) {
      console.error('[SyncConfig] Warning: No valid sources found, using defaults');
      cachedSyncSources = DEFAULT_SYNC_SOURCES;
      return cachedSyncSources;
    }

    cachedSyncSources = validSources;
    return cachedSyncSources;
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    console.error(`[SyncConfig] Warning: Failed to load sync-sources.json: ${message}, using defaults`);
    cachedSyncSources = DEFAULT_SYNC_SOURCES;
    return cachedSyncSources;
  }
}

/**
 * Clear the cached sync sources and patterns (for testing).
 */
export function clearSyncSourcesCache(): void {
  cachedSyncSources = null;
  cachedCustomExcludePatterns = null;
}

/**
 * Load custom exclude patterns from external configuration file.
 * Falls back to empty array if file is missing or patterns not defined.
 * Environment variable MADEINOZ_KNOWLEDGE_SYNC_EXCLUDE_PATTERNS overrides config file.
 */
export function loadCustomExcludePatterns(): string[] {
  // Env var takes precedence for backwards compatibility
  const envPatterns = process.env[SYNC_CONFIG_ENV_VARS.SYNC_EXCLUDE_PATTERNS];
  if (envPatterns !== undefined && envPatterns !== '') {
    return envPatterns
      .split(',')
      .map((p) => p.trim())
      .filter((p) => p.length > 0);
  }

  // Use cached config file patterns
  if (cachedCustomExcludePatterns !== null) {
    return cachedCustomExcludePatterns;
  }

  const configPath = join(getConfigDir(), 'sync-sources.json');

  if (!existsSync(configPath)) {
    cachedCustomExcludePatterns = [];
    return cachedCustomExcludePatterns;
  }

  try {
    const content = readFileSync(configPath, 'utf-8');
    const config: SyncSourceConfigFile = JSON.parse(content);

    if (Array.isArray(config.customExcludePatterns)) {
      // Validate each pattern is a non-empty string
      cachedCustomExcludePatterns = config.customExcludePatterns
        .filter((p): p is string => typeof p === 'string' && p.trim().length > 0)
        .map((p) => p.trim());
    } else {
      cachedCustomExcludePatterns = [];
    }

    return cachedCustomExcludePatterns;
  } catch {
    cachedCustomExcludePatterns = [];
    return cachedCustomExcludePatterns;
  }
}

/**
 * Parse a boolean environment variable value.
 * Accepts: true, false, 1, 0, yes, no (case-insensitive)
 * Returns undefined for invalid values.
 */
function parseEnvBoolean(value: string | undefined): boolean | undefined {
  if (value === undefined || value === '') {
    return undefined;
  }

  const normalized = value.toLowerCase().trim();

  if (['true', '1', 'yes'].includes(normalized)) {
    return true;
  }

  if (['false', '0', 'no'].includes(normalized)) {
    return false;
  }

  return undefined;
}

/**
 * Parse a numeric environment variable value.
 * Returns undefined for invalid values.
 */
function parseEnvNumber(value: string | undefined, min: number, max: number): number | undefined {
  if (value === undefined || value === '') {
    return undefined;
  }

  const parsed = parseInt(value, 10);

  if (isNaN(parsed) || parsed < min || parsed > max) {
    return undefined;
  }

  return parsed;
}

/**
 * Parse comma-separated patterns from environment variable.
 */
function parseEnvPatterns(value: string | undefined): string[] {
  if (value === undefined || value === '') {
    return [];
  }

  return value
    .split(',')
    .map((p) => p.trim())
    .filter((p) => p.length > 0);
}

/**
 * Load sync configuration from environment variables.
 * Returns defaults for any missing or invalid values.
 * Logs warnings for invalid values.
 */
export function loadSyncConfig(): SyncConfiguration {
  const config: SyncConfiguration = { ...DEFAULT_SYNC_CONFIG };

  // Parse SYNC_LEARNING_ALGORITHM
  const learningAlgorithm = parseEnvBoolean(process.env[SYNC_CONFIG_ENV_VARS.SYNC_LEARNING_ALGORITHM]);
  if (learningAlgorithm !== undefined) {
    config.syncLearningAlgorithm = learningAlgorithm;
  } else if (process.env[SYNC_CONFIG_ENV_VARS.SYNC_LEARNING_ALGORITHM] !== undefined) {
    console.error(
      `[SyncConfig] Warning: Invalid value for ${SYNC_CONFIG_ENV_VARS.SYNC_LEARNING_ALGORITHM}, using default (true)`
    );
  }

  // Parse SYNC_LEARNING_SYSTEM
  const learningSystem = parseEnvBoolean(process.env[SYNC_CONFIG_ENV_VARS.SYNC_LEARNING_SYSTEM]);
  if (learningSystem !== undefined) {
    config.syncLearningSystem = learningSystem;
  } else if (process.env[SYNC_CONFIG_ENV_VARS.SYNC_LEARNING_SYSTEM] !== undefined) {
    console.error(
      `[SyncConfig] Warning: Invalid value for ${SYNC_CONFIG_ENV_VARS.SYNC_LEARNING_SYSTEM}, using default (true)`
    );
  }

  // Parse SYNC_RESEARCH
  const research = parseEnvBoolean(process.env[SYNC_CONFIG_ENV_VARS.SYNC_RESEARCH]);
  if (research !== undefined) {
    config.syncResearch = research;
  } else if (process.env[SYNC_CONFIG_ENV_VARS.SYNC_RESEARCH] !== undefined) {
    console.error(
      `[SyncConfig] Warning: Invalid value for ${SYNC_CONFIG_ENV_VARS.SYNC_RESEARCH}, using default (true)`
    );
  }

  // Load custom exclude patterns (config file preferred, env var fallback)
  config.customExcludePatterns = loadCustomExcludePatterns();

  // Parse SYNC_MAX_FILES (1-1000)
  const maxFiles = parseEnvNumber(process.env[SYNC_CONFIG_ENV_VARS.SYNC_MAX_FILES], 1, 1000);
  if (maxFiles !== undefined) {
    config.maxFilesPerSync = maxFiles;
  } else if (process.env[SYNC_CONFIG_ENV_VARS.SYNC_MAX_FILES] !== undefined) {
    console.error(
      `[SyncConfig] Warning: Invalid value for ${SYNC_CONFIG_ENV_VARS.SYNC_MAX_FILES}, using default (50)`
    );
  }

  // Parse SYNC_VERBOSE
  const verbose = parseEnvBoolean(process.env[SYNC_CONFIG_ENV_VARS.SYNC_VERBOSE]);
  if (verbose !== undefined) {
    config.verbose = verbose;
  }

  return config;
}

/**
 * Get the environment variable name for a sync source.
 */
function getEnvVarName(sourceId: string): string {
  return `MADEINOZ_KNOWLEDGE_SYNC_${sourceId}`;
}

/**
 * Get enabled sync sources based on configuration.
 * Uses dynamically loaded sources from config file.
 * Returns only sources where the corresponding env var or default is true.
 */
export function getEnabledSources(config: SyncConfiguration): SyncSource[] {
  const syncSources = loadSyncSources();
  const sources: SyncSource[] = [];

  for (const source of syncSources) {
    // Check env var for this source (e.g., MADEINOZ_KNOWLEDGE_SYNC_LEARNING_ALGORITHM)
    const envVarName = getEnvVarName(source.id);
    const envValue = parseEnvBoolean(process.env[envVarName]);

    // Use env var value if set, otherwise use defaultEnabled from config
    let enabled: boolean;
    if (envValue !== undefined) {
      enabled = envValue;
    } else if (process.env[envVarName] !== undefined) {
      // Invalid value in env var, warn and use default
      console.error(
        `[SyncConfig] Warning: Invalid value for ${envVarName}, using default (${source.defaultEnabled})`
      );
      enabled = source.defaultEnabled;
    } else {
      enabled = source.defaultEnabled;
    }

    // Also check the legacy config flags for backwards compatibility
    if (source.id === 'LEARNING_ALGORITHM' && config.syncLearningAlgorithm !== undefined) {
      enabled = config.syncLearningAlgorithm;
    } else if (source.id === 'LEARNING_SYSTEM' && config.syncLearningSystem !== undefined) {
      enabled = config.syncLearningSystem;
    } else if (source.id === 'RESEARCH' && config.syncResearch !== undefined) {
      enabled = config.syncResearch;
    }

    if (enabled) {
      sources.push({
        path: source.path,
        type: source.type,
        description: source.description,
        enabled,
      });
    }
  }

  return sources;
}

/**
 * Get all sync sources with their enabled status.
 * Useful for status display.
 */
export function getAllSourcesWithStatus(config: SyncConfiguration): SyncSource[] {
  const syncSources = loadSyncSources();

  return syncSources.map((source) => {
    // Check env var for this source
    const envVarName = getEnvVarName(source.id);
    const envValue = parseEnvBoolean(process.env[envVarName]);

    let enabled: boolean;
    if (envValue !== undefined) {
      enabled = envValue;
    } else {
      enabled = source.defaultEnabled;
    }

    // Also check the legacy config flags for backwards compatibility
    if (source.id === 'LEARNING_ALGORITHM' && config.syncLearningAlgorithm !== undefined) {
      enabled = config.syncLearningAlgorithm;
    } else if (source.id === 'LEARNING_SYSTEM' && config.syncLearningSystem !== undefined) {
      enabled = config.syncLearningSystem;
    } else if (source.id === 'RESEARCH' && config.syncResearch !== undefined) {
      enabled = config.syncResearch;
    }

    return {
      path: source.path,
      type: source.type,
      description: source.description,
      enabled,
    };
  });
}

/**
 * Format configuration for display.
 */
export function formatConfig(config: SyncConfiguration): string {
  const syncSources = loadSyncSources();
  const lines = ['Sync Configuration:'];

  // Show each source with its status
  for (const source of syncSources) {
    const envVarName = getEnvVarName(source.id);
    const envValue = parseEnvBoolean(process.env[envVarName]);

    let enabled: boolean;
    if (envValue !== undefined) {
      enabled = envValue;
    } else {
      enabled = source.defaultEnabled;
    }

    // Check legacy config flags
    if (source.id === 'LEARNING_ALGORITHM' && config.syncLearningAlgorithm !== undefined) {
      enabled = config.syncLearningAlgorithm;
    } else if (source.id === 'LEARNING_SYSTEM' && config.syncLearningSystem !== undefined) {
      enabled = config.syncLearningSystem;
    } else if (source.id === 'RESEARCH' && config.syncResearch !== undefined) {
      enabled = config.syncResearch;
    }

    lines.push(`  ${source.path}: ${enabled ? 'enabled' : 'disabled'}`);
  }

  lines.push(`  Max files per sync: ${config.maxFilesPerSync}`);
  lines.push(`  Verbose: ${config.verbose}`);
  lines.push(`  Dry run: ${config.dryRun}`);

  if (config.customExcludePatterns.length > 0) {
    lines.push(`  Custom exclude patterns: ${config.customExcludePatterns.join(', ')}`);
  }

  return lines.join('\n');
}
