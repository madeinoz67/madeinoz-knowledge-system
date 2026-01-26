/**
 * Configuration Loader Library
 *
 * Handles loading and mapping environment variables for the Madeinoz Knowledge System.
 * Supports MADEINOZ_KNOWLEDGE_* prefixed variables and maps them to standard container env vars.
 *
 * PAI .env is the ONLY source of truth for all configuration:
 *   - Uses ${PAI_DIR}/.env if PAI_DIR environment variable is set
 *   - Falls back to ~/.claude/.env if PAI_DIR is not set
 *
 * Docker containers read directly from PAI .env via the env_file directive.
 */

import { join } from 'node:path';

/**
 * Configuration interface
 */
export interface KnowledgeConfig {
  // API Keys
  OPENAI_API_KEY?: string;
  ANTHROPIC_API_KEY?: string;
  GOOGLE_API_KEY?: string;
  GROQ_API_KEY?: string;
  VOYAGE_API_KEY?: string;

  // LLM Provider Configuration
  LLM_PROVIDER: string;
  EMBEDDER_PROVIDER: string;
  MODEL_NAME: string;

  // Custom Endpoint Configuration
  OPENAI_BASE_URL?: string; // For Ollama LLM: http://host.docker.internal:11434/v1
  EMBEDDER_PROVIDER_URL?: string; // For custom embedder endpoint (Ollama, etc.)
  EMBEDDER_MODEL?: string; // For Ollama: nomic-embed-text
  EMBEDDER_DIMENSIONS?: string; // For embedder: 1024 for mxbai, 1536 for OpenAI

  // Performance Configuration
  SEMAPHORE_LIMIT: string;

  // Knowledge Graph Configuration
  GROUP_ID: string;

  // Database Configuration
  DATABASE_TYPE: string;
  FALKORDB_HOST?: string;
  FALKORDB_PORT?: string;
  FALKORDB_PASSWORD?: string;

  // Neo4j Configuration (alternative)
  NEO4J_URI?: string;
  NEO4J_USER?: string;
  NEO4J_PASSWORD?: string;

  // Telemetry
  GRAPHITI_TELEMETRY_ENABLED: string;

  // Container Configuration
  NETWORK_NAME: string;
  FALKORDB_CONTAINER: string;
  MCP_CONTAINER: string;
  VOLUME_NAME: string;

  // Port Configuration
  MCP_SERVER_PORT: string;
  FALKORDB_UI_PORT: string;

  // Original MADEINOZ_KNOWLEDGE_* prefixed values (for reference)
  PAI_PREFIXES?: Record<string, string | undefined>;
}

/**
 * Default configuration values
 */
const DEFAULTS: Record<string, string> = {
  LLM_PROVIDER: 'ollama',
  EMBEDDER_PROVIDER: 'ollama',
  MODEL_NAME: 'llama3.2',
  OPENAI_BASE_URL: 'http://host.docker.internal:11434/v1', // Ollama LLM default (Docker)
  EMBEDDER_PROVIDER_URL: 'http://host.containers.internal:11434', // Embedder endpoint (Ollama, etc.)
  EMBEDDER_MODEL: 'nomic-embed-text', // Ollama embedding model
  EMBEDDER_DIMENSIONS: '512', // nomic-embed-text dimensions
  SEMAPHORE_LIMIT: '10',
  GROUP_ID: 'main',
  DATABASE_TYPE: 'neo4j',
  GRAPHITI_TELEMETRY_ENABLED: 'false',
  NETWORK_NAME: 'madeinoz-knowledge-net',
  FALKORDB_CONTAINER: 'madeinoz-knowledge-falkordb',
  MCP_CONTAINER: 'madeinoz-knowledge-graph-mcp',
  VOLUME_NAME: 'madeinoz-knowledge-falkordb-data',
  MCP_SERVER_PORT: '8000',
  FALKORDB_UI_PORT: '3000',
  FALKORDB_HOST: 'madeinoz-knowledge-falkordb',
  FALKORDB_PORT: '6379',
  NEO4J_URI: 'bolt://localhost:7687',
  NEO4J_USER: 'neo4j',
  NEO4J_PASSWORD: 'demodemo',
};

/**
 * Configuration Loader class
 *
 * PAI .env is the ONLY source of truth for all configuration.
 * Uses ${PAI_DIR}/.env if PAI_DIR is set, otherwise ~/.claude/.env
 */
export class ConfigLoader {
  private packRoot: string;
  private envFile: string;

  constructor(packRoot?: string) {
    // If packRoot not provided, navigate up from src/server/lib to pack root
    this.packRoot = packRoot || join(import.meta.dir, '../../../');

    // PAI .env is the ONLY source of truth
    // Priority: PAI_DIR/.env > ~/.claude/.env
    const homeDir = process.env.HOME || '';
    this.envFile = process.env.PAI_DIR
      ? join(process.env.PAI_DIR, '.env')
      : join(homeDir, '.claude', '.env');
  }

  /**
   * Get the pack root directory
   */
  getPackRoot(): string {
    return this.packRoot;
  }

  /**
   * Get the PAI .env file path
   */
  getEnvFile(): string {
    return this.envFile;
  }

  /**
   * Check if .env file exists
   */
  async envExists(): Promise<boolean> {
    const file = Bun.file(this.envFile);
    return file.exists();
  }

  /**
   * Load environment variables from PAI .env file using Bun
   * PAI .env (${PAI_DIR}/.env or ~/.claude/.env) is the ONLY source of truth
   */
  async loadEnv(): Promise<Record<string, string>> {
    const env: Record<string, string> = {};

    // Copy process.env (filtering out undefined values)
    for (const [key, value] of Object.entries(process.env)) {
      if (value !== undefined) {
        env[key] = value;
      }
    }

    // Load from PAI .env (the ONLY source of truth)
    if (await this.envExists()) {
      const file = Bun.file(this.envFile);
      const content = await file.text();
      this.parseEnvFile(content, env);
    }

    return env;
  }

  /**
   * Parse .env file content
   */
  private parseEnvFile(content: string, env: Record<string, string>): void {
    const lines = content.split('\n');

    for (const line of lines) {
      const trimmed = line.trim();

      // Skip empty lines and comments
      if (!trimmed || trimmed.startsWith('#')) {
        continue;
      }

      // Parse KEY=VALUE
      const eqIndex = trimmed.indexOf('=');
      if (eqIndex > 0) {
        const key = trimmed.substring(0, eqIndex).trim();
        const value = trimmed.substring(eqIndex + 1).trim();

        // Remove quotes if present
        const unquoted =
          (value.startsWith('"') && value.endsWith('"')) ||
          (value.startsWith("'") && value.endsWith("'"))
            ? value.slice(1, -1)
            : value;

        env[key] = unquoted;
      }
    }
  }

  /**
   * Map MADEINOZ_KNOWLEDGE_* prefixed variables to standard names
   * MADEINOZ_KNOWLEDGE_* variables take PRECEDENCE over unprefixed variables
   */
  private mapPrefixes(env: Record<string, string>): {
    mapped: Record<string, string>;
    originals: Record<string, string | undefined>;
  } {
    const mapped: Record<string, string> = { ...env };
    const originals: Record<string, string | undefined> = {};

    // Mapping of MADEINOZ_KNOWLEDGE_* -> standard variable
    const mappings: Record<string, string> = {
      // API Keys
      MADEINOZ_KNOWLEDGE_OPENAI_API_KEY: 'OPENAI_API_KEY',
      MADEINOZ_KNOWLEDGE_ANTHROPIC_API_KEY: 'ANTHROPIC_API_KEY',
      MADEINOZ_KNOWLEDGE_GOOGLE_API_KEY: 'GOOGLE_API_KEY',
      MADEINOZ_KNOWLEDGE_GROQ_API_KEY: 'GROQ_API_KEY',
      MADEINOZ_KNOWLEDGE_VOYAGE_API_KEY: 'VOYAGE_API_KEY',
      // LLM Configuration
      MADEINOZ_KNOWLEDGE_LLM_PROVIDER: 'LLM_PROVIDER',
      MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER: 'EMBEDDER_PROVIDER',
      MADEINOZ_KNOWLEDGE_MODEL_NAME: 'MODEL_NAME',
      // Custom Endpoint Configuration
      MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL: 'OPENAI_BASE_URL',
      MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER_URL: 'EMBEDDER_PROVIDER_URL',
      MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL: 'EMBEDDER_MODEL',
      MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS: 'EMBEDDER_DIMENSIONS',
      // Performance
      MADEINOZ_KNOWLEDGE_SEMAPHORE_LIMIT: 'SEMAPHORE_LIMIT',
      // Knowledge Graph
      MADEINOZ_KNOWLEDGE_GROUP_ID: 'GROUP_ID',
      MADEINOZ_KNOWLEDGE_DATABASE_TYPE: 'DATABASE_TYPE',
      MADEINOZ_KNOWLEDGE_GRAPHITI_TELEMETRY_ENABLED: 'GRAPHITI_TELEMETRY_ENABLED',
      // FalkorDB
      MADEINOZ_KNOWLEDGE_FALKORDB_HOST: 'FALKORDB_HOST',
      MADEINOZ_KNOWLEDGE_FALKORDB_PORT: 'FALKORDB_PORT',
      MADEINOZ_KNOWLEDGE_FALKORDB_PASSWORD: 'FALKORDB_PASSWORD',
      // Neo4j
      MADEINOZ_KNOWLEDGE_NEO4J_URI: 'NEO4J_URI',
      MADEINOZ_KNOWLEDGE_NEO4J_USER: 'NEO4J_USER',
      MADEINOZ_KNOWLEDGE_NEO4J_PASSWORD: 'NEO4J_PASSWORD',
      MADEINOZ_KNOWLEDGE_NEO4J_DATABASE: 'NEO4J_DATABASE',
    };

    // Apply mappings - MADEINOZ_KNOWLEDGE_* takes PRECEDENCE over unprefixed variables
    for (const [paiVar, standardVar] of Object.entries(mappings)) {
      const paiValue = env[paiVar];
      if (paiValue) {
        // Store original for reference
        originals[paiVar] = paiValue;

        // ALWAYS use MADEINOZ_KNOWLEDGE_* value, overriding any unprefixed variable
        // This ensures prefixed vars take precedence as the primary configuration
        mapped[standardVar] = paiValue;
      }
    }

    return { mapped, originals };
  }

  /**
   * Get configuration value with fallback to default
   */
  private getEnvValue(env: Record<string, string>, key: string, defaultValue?: string): string {
    const value = env[key];
    if (value) {
      return value;
    }
    if (defaultValue !== undefined) {
      return defaultValue;
    }
    // Return from defaults
    return DEFAULTS[key] || '';
  }

  /**
   * Load and validate configuration
   */
  async load(): Promise<KnowledgeConfig> {
    // Load .env file
    const env = await this.loadEnv();

    // Map MADEINOZ_KNOWLEDGE_* prefixes
    const { mapped, originals } = this.mapPrefixes(env);

    // Build configuration object
    const config: KnowledgeConfig = {
      // API Keys
      OPENAI_API_KEY: this.getEnvValue(mapped, 'OPENAI_API_KEY'),
      ANTHROPIC_API_KEY: this.getEnvValue(mapped, 'ANTHROPIC_API_KEY'),
      GOOGLE_API_KEY: this.getEnvValue(mapped, 'GOOGLE_API_KEY'),
      GROQ_API_KEY: this.getEnvValue(mapped, 'GROQ_API_KEY'),
      VOYAGE_API_KEY: this.getEnvValue(mapped, 'VOYAGE_API_KEY'),

      // LLM Provider Configuration
      LLM_PROVIDER: this.getEnvValue(mapped, 'LLM_PROVIDER', DEFAULTS.LLM_PROVIDER),
      EMBEDDER_PROVIDER: this.getEnvValue(mapped, 'EMBEDDER_PROVIDER', DEFAULTS.EMBEDDER_PROVIDER),
      MODEL_NAME: this.getEnvValue(mapped, 'MODEL_NAME', DEFAULTS.MODEL_NAME),

      // Custom Endpoint Configuration
      OPENAI_BASE_URL: this.getEnvValue(mapped, 'OPENAI_BASE_URL', ''),
      EMBEDDER_PROVIDER_URL: this.getEnvValue(mapped, 'EMBEDDER_PROVIDER_URL', ''),
      EMBEDDER_MODEL: this.getEnvValue(mapped, 'EMBEDDER_MODEL', ''),
      EMBEDDER_DIMENSIONS: this.getEnvValue(mapped, 'EMBEDDER_DIMENSIONS', ''),

      // Performance Configuration
      SEMAPHORE_LIMIT: this.getEnvValue(mapped, 'SEMAPHORE_LIMIT', DEFAULTS.SEMAPHORE_LIMIT),

      // Knowledge Graph Configuration
      GROUP_ID: this.getEnvValue(mapped, 'GROUP_ID', DEFAULTS.GROUP_ID),

      // Database Configuration
      DATABASE_TYPE: this.getEnvValue(mapped, 'DATABASE_TYPE', DEFAULTS.DATABASE_TYPE),
      FALKORDB_HOST: this.getEnvValue(mapped, 'FALKORDB_HOST', DEFAULTS.FALKORDB_HOST),
      FALKORDB_PORT: this.getEnvValue(mapped, 'FALKORDB_PORT', DEFAULTS.FALKORDB_PORT),
      FALKORDB_PASSWORD: this.getEnvValue(mapped, 'FALKORDB_PASSWORD', ''),

      // Neo4j Configuration
      NEO4J_URI: this.getEnvValue(mapped, 'NEO4J_URI', DEFAULTS.NEO4J_URI),
      NEO4J_USER: this.getEnvValue(mapped, 'NEO4J_USER', DEFAULTS.NEO4J_USER),
      NEO4J_PASSWORD: this.getEnvValue(mapped, 'NEO4J_PASSWORD', DEFAULTS.NEO4J_PASSWORD),

      // Telemetry
      GRAPHITI_TELEMETRY_ENABLED: this.getEnvValue(
        mapped,
        'GRAPHITI_TELEMETRY_ENABLED',
        DEFAULTS.GRAPHITI_TELEMETRY_ENABLED
      ),

      // Container Configuration
      NETWORK_NAME: this.getEnvValue(mapped, 'NETWORK_NAME', DEFAULTS.NETWORK_NAME),
      FALKORDB_CONTAINER: this.getEnvValue(
        mapped,
        'FALKORDB_CONTAINER',
        DEFAULTS.FALKORDB_CONTAINER
      ),
      MCP_CONTAINER: this.getEnvValue(mapped, 'MCP_CONTAINER', DEFAULTS.MCP_CONTAINER),
      VOLUME_NAME: this.getEnvValue(mapped, 'VOLUME_NAME', DEFAULTS.VOLUME_NAME),

      // Port Configuration
      MCP_SERVER_PORT: this.getEnvValue(mapped, 'MCP_SERVER_PORT', DEFAULTS.MCP_SERVER_PORT),
      FALKORDB_UI_PORT: this.getEnvValue(mapped, 'FALKORDB_UI_PORT', DEFAULTS.FALKORDB_UI_PORT),

      // Store original MADEINOZ_KNOWLEDGE_* values
      PAI_PREFIXES: originals,
    };

    return config;
  }

  /**
   * Validate that required configuration is present
   */
  validate(config: KnowledgeConfig): { valid: boolean; errors: string[] } {
    const errors: string[] = [];

    // Check that at least one API key is configured (not required for Ollama)
    const isOllama = config.LLM_PROVIDER === 'ollama';
    const hasAnyKey =
      !!config.OPENAI_API_KEY ||
      !!config.ANTHROPIC_API_KEY ||
      !!config.GOOGLE_API_KEY ||
      !!config.GROQ_API_KEY;

    if (!hasAnyKey && !isOllama) {
      errors.push('No LLM API key configured (need OPENAI_API_KEY or alternative, or use Ollama)');
    }

    // Validate LLM provider
    const validProviders = ['openai', 'anthropic', 'gemini', 'groq', 'ollama'];
    if (!validProviders.includes(config.LLM_PROVIDER)) {
      errors.push(`Invalid LLM_PROVIDER: ${config.LLM_PROVIDER}`);
    }

    // Validate Ollama configuration
    if (isOllama && !config.OPENAI_BASE_URL) {
      errors.push(
        'OPENAI_BASE_URL required for Ollama (e.g., http://host.docker.internal:11434/v1)'
      );
    }

    // Validate database type
    const validDatabases = ['falkordb', 'neo4j'];
    if (!validDatabases.includes(config.DATABASE_TYPE)) {
      errors.push(`Invalid DATABASE_TYPE: ${config.DATABASE_TYPE}`);
    }

    // Validate semaphore limit is a number
    const semaphoreLimit = Number.parseInt(config.SEMAPHORE_LIMIT, 10);
    if (Number.isNaN(semaphoreLimit) || semaphoreLimit < 1) {
      errors.push(`Invalid SEMAPHORE_LIMIT: ${config.SEMAPHORE_LIMIT}`);
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }

  /**
   * Get configuration for container environment variables
   * Maps config to container-friendly env var names
   */
  getContainerEnv(config: KnowledgeConfig): Record<string, string> {
    const env: Record<string, string> = {
      OPENAI_API_KEY: config.OPENAI_API_KEY || '',
      ANTHROPIC_API_KEY: config.ANTHROPIC_API_KEY || '',
      GOOGLE_API_KEY: config.GOOGLE_API_KEY || '',
      GROQ_API_KEY: config.GROQ_API_KEY || '',
      VOYAGE_API_KEY: config.VOYAGE_API_KEY || '',
      DATABASE_TYPE: config.DATABASE_TYPE,
      FALKORDB_HOST: config.FALKORDB_HOST || config.FALKORDB_CONTAINER,
      FALKORDB_PORT: config.FALKORDB_PORT || '6379',
      FALKORDB_PASSWORD: config.FALKORDB_PASSWORD || '',
      // For containers, use container hostname 'neo4j' not 'localhost'
      NEO4J_URI: config.NEO4J_URI || 'bolt://neo4j:7687',
      NEO4J_USER: config.NEO4J_USER || 'neo4j',
      NEO4J_PASSWORD: config.NEO4J_PASSWORD || 'demodemo',
      SEMAPHORE_LIMIT: config.SEMAPHORE_LIMIT,
      GRAPHITI_TELEMETRY_ENABLED: config.GRAPHITI_TELEMETRY_ENABLED,
      MODEL_NAME: config.MODEL_NAME,
      LLM_PROVIDER: config.LLM_PROVIDER,
      EMBEDDER_PROVIDER: config.EMBEDDER_PROVIDER,
      EMBEDDER_MODEL: config.EMBEDDER_MODEL || '',
      EMBEDDER_DIMENSIONS: config.EMBEDDER_DIMENSIONS || '',
      EMBEDDER_PROVIDER_URL: config.EMBEDDER_PROVIDER_URL || '',
      GROUP_ID: config.GROUP_ID,
    };

    // LLM provider configuration
    // For Ollama LLM: Use "openai" as provider with custom base URL (OpenAI-compatible API)
    const isOllamaLLM = config.LLM_PROVIDER === 'ollama';
    if (isOllamaLLM) {
      env.LLM_PROVIDER = 'openai';
      env.OPENAI_API_KEY = config.OPENAI_API_KEY || 'ollama'; // Ollama doesn't need a real key
      env.OPENAI_BASE_URL = config.OPENAI_BASE_URL || DEFAULTS.OPENAI_BASE_URL;
    } else if (config.OPENAI_BASE_URL) {
      // Custom OpenAI endpoint (e.g., Azure, local proxy)
      env.OPENAI_BASE_URL = config.OPENAI_BASE_URL;
    }

    // Embedder provider configuration (independent from LLM provider)
    const isOllamaEmbedder = config.EMBEDDER_PROVIDER === 'ollama';
    if (isOllamaEmbedder) {
      // Ollama embedder uses native 'ollama' provider in Graphiti
      env.EMBEDDER_PROVIDER = 'ollama';
      env.EMBEDDER_PROVIDER_URL = config.EMBEDDER_PROVIDER_URL || DEFAULTS.EMBEDDER_PROVIDER_URL;
      env.EMBEDDER_MODEL = config.EMBEDDER_MODEL || DEFAULTS.EMBEDDER_MODEL;
      env.EMBEDDER_DIMENSIONS = config.EMBEDDER_DIMENSIONS || DEFAULTS.EMBEDDER_DIMENSIONS;
    } else if (config.EMBEDDER_MODEL) {
      env.EMBEDDER_MODEL = config.EMBEDDER_MODEL;
    }

    return env;
  }

  /**
   * Save configuration to PAI .env file
   * Writes to ${PAI_DIR}/.env or ~/.claude/.env (the ONLY source of truth)
   */
  async save(config: Partial<KnowledgeConfig>): Promise<void> {
    // Build new content for PAI .env
    let newContent = '# Madeinoz Knowledge System Configuration\n';
    newContent += `# Location: ${this.envFile}\n`;
    newContent += `# Generated: ${new Date().toISOString()}\n`;
    newContent += '\n';

    // Add API Keys (all use MADEINOZ_KNOWLEDGE_* prefix)
    if (config.OPENAI_API_KEY) {
      newContent += `MADEINOZ_KNOWLEDGE_OPENAI_API_KEY=${config.OPENAI_API_KEY}\n`;
    }
    if (config.ANTHROPIC_API_KEY) {
      newContent += `MADEINOZ_KNOWLEDGE_ANTHROPIC_API_KEY=${config.ANTHROPIC_API_KEY}\n`;
    }
    if (config.GOOGLE_API_KEY) {
      newContent += `MADEINOZ_KNOWLEDGE_GOOGLE_API_KEY=${config.GOOGLE_API_KEY}\n`;
    }
    if (config.GROQ_API_KEY) {
      newContent += `MADEINOZ_KNOWLEDGE_GROQ_API_KEY=${config.GROQ_API_KEY}\n`;
    }
    if (config.VOYAGE_API_KEY) {
      newContent += `MADEINOZ_KNOWLEDGE_VOYAGE_API_KEY=${config.VOYAGE_API_KEY}\n`;
    }

    newContent += '\n';

    // Add LLM Configuration
    if (config.LLM_PROVIDER) {
      newContent += `MADEINOZ_KNOWLEDGE_LLM_PROVIDER=${config.LLM_PROVIDER}\n`;
    }
    if (config.EMBEDDER_PROVIDER) {
      newContent += `MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER=${config.EMBEDDER_PROVIDER}\n`;
    }
    if (config.MODEL_NAME) {
      newContent += `MADEINOZ_KNOWLEDGE_MODEL_NAME=${config.MODEL_NAME}\n`;
    }

    newContent += '\n';

    // Add Ollama/Custom Endpoint Configuration
    if (config.OPENAI_BASE_URL) {
      newContent += '# Ollama/Custom Endpoint (for OpenAI-compatible APIs)\n';
      newContent += `MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL=${config.OPENAI_BASE_URL}\n`;
    }
    if (config.EMBEDDER_MODEL) {
      newContent += `MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL=${config.EMBEDDER_MODEL}\n`;
    }

    newContent += '\n';

    // Add Performance Configuration
    if (config.SEMAPHORE_LIMIT) {
      newContent += `MADEINOZ_KNOWLEDGE_SEMAPHORE_LIMIT=${config.SEMAPHORE_LIMIT}\n`;
    }

    newContent += '\n';

    // Add Knowledge Graph Configuration
    if (config.GROUP_ID) {
      newContent += `MADEINOZ_KNOWLEDGE_GROUP_ID=${config.GROUP_ID}\n`;
    }

    if (config.DATABASE_TYPE) {
      newContent += `MADEINOZ_KNOWLEDGE_DATABASE_TYPE=${config.DATABASE_TYPE}\n`;
    }

    if (config.GRAPHITI_TELEMETRY_ENABLED) {
      newContent += `MADEINOZ_KNOWLEDGE_GRAPHITI_TELEMETRY_ENABLED=${config.GRAPHITI_TELEMETRY_ENABLED}\n`;
    }

    newContent += '\n';

    // Add Database Configuration (FalkorDB)
    if (config.FALKORDB_HOST) {
      newContent += `MADEINOZ_KNOWLEDGE_FALKORDB_HOST=${config.FALKORDB_HOST}\n`;
    }
    if (config.FALKORDB_PORT) {
      newContent += `MADEINOZ_KNOWLEDGE_FALKORDB_PORT=${config.FALKORDB_PORT}\n`;
    }
    if (config.FALKORDB_PASSWORD) {
      newContent += `MADEINOZ_KNOWLEDGE_FALKORDB_PASSWORD=${config.FALKORDB_PASSWORD}\n`;
    }

    newContent += '\n';

    // Add Database Configuration (Neo4j)
    if (config.NEO4J_URI) {
      newContent += `MADEINOZ_KNOWLEDGE_NEO4J_URI=${config.NEO4J_URI}\n`;
    }
    if (config.NEO4J_USER) {
      newContent += `MADEINOZ_KNOWLEDGE_NEO4J_USER=${config.NEO4J_USER}\n`;
    }
    if (config.NEO4J_PASSWORD) {
      newContent += `MADEINOZ_KNOWLEDGE_NEO4J_PASSWORD=${config.NEO4J_PASSWORD}\n`;
    }

    // Write to file
    await Bun.write(this.envFile, newContent);
  }
}

/**
 * Create a config loader instance
 */
export function createConfigLoader(packRoot?: string): ConfigLoader {
  return new ConfigLoader(packRoot);
}

/**
 * Load configuration (convenience function)
 */
export async function loadConfig(): Promise<KnowledgeConfig> {
  const loader = new ConfigLoader();
  return await loader.load();
}

/**
 * Validate configuration (convenience function)
 */
export function validateConfig(config: KnowledgeConfig): { valid: boolean; errors: string[] } {
  const loader = new ConfigLoader();
  return loader.validate(config);
}
