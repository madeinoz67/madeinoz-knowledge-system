#!/usr/bin/env bun
/**
 * Madeinoz Knowledge System Installation Script v2.1.0
 *
 * Interactive installer that guides users through:
 * - LLM provider selection
 * - API key configuration
 * - Model selection
 * - Performance tuning
 * - PAI .env integration
 * - Service startup
 * - PAI skill installation
 *
 * Usage:
 *   bun run src/server/install.ts                # Fresh install (interactive)
 *   bun run src/server/install.ts --update       # Update existing installation
 *   bun run src/server/install.ts --yes          # Non-interactive with defaults
 *   bun run src/server/install.ts --update --yes # Update non-interactively
 */

// =============================================================================
// CLI FLAGS
// =============================================================================

const isUpdateMode = process.argv.includes('--update') || process.argv.includes('-u');
const isNonInteractive = process.argv.includes('--yes') || process.argv.includes('-y');

import { createContainerManager } from '../lib/container';
import { createConfigLoader } from '../lib/config';
import { cli } from '../lib/cli';
import inquirer from 'inquirer';

/**
 * LLM Provider configuration
 */
interface LLMProvider {
  id: string;
  name: string;
  embedder: string;
  needsOpenAI: boolean;
  models?: ModelChoice[];
}

/**
 * Model choice for provider
 */
interface ModelChoice {
  name: string;
  value: string;
}

/**
 * API tier configuration
 */
interface APITier {
  name: string;
  semaphoreLimit: number;
}

/**
 * OpenAI-compatible provider configuration
 */
interface OpenAICompatibleProvider {
  id: string;
  name: string;
  baseUrl: string;
  keyName: string;
  keyUrl: string;
  models: ModelChoice[];
  embedderModels?: ModelChoice[];
  defaultEmbedderDimensions?: number;
}

/**
 * OpenAI-compatible cloud providers (use OpenAI API format)
 */
const OPENAI_COMPATIBLE_PROVIDERS: OpenAICompatibleProvider[] = [
  {
    id: 'openrouter',
    name: 'OpenRouter (access to 200+ models) - RECOMMENDED',
    baseUrl: 'https://openrouter.ai/api/v1',
    keyName: 'OpenRouter',
    keyUrl: 'https://openrouter.ai/keys',
    models: [
      // ✅ BENCHMARK TESTED - These models WORK with Graphiti MCP
      {
        name: 'google/gemini-2.0-flash-001 (BEST VALUE - $0.125/1K)',
        value: 'google/gemini-2.0-flash-001',
      },
      { name: 'openai/gpt-4o-mini (reliable - $0.129/1K)', value: 'openai/gpt-4o-mini' },
      { name: 'qwen/qwen-2.5-72b-instruct ($0.126/1K, slow)', value: 'qwen/qwen-2.5-72b-instruct' },
      { name: 'anthropic/claude-3.5-haiku ($0.816/1K)', value: 'anthropic/claude-3.5-haiku' },
      { name: 'openai/gpt-4o (FASTEST - $2.155/1K)', value: 'openai/gpt-4o' },
      { name: 'x-ai/grok-3 (xAI option - $2.163/1K)', value: 'x-ai/grok-3' },
      // ❌ BENCHMARK TESTED - These models FAIL Graphiti validation (kept for reference)
      // { name: "meta-llama/llama-3.1-70b-instruct (FAILS)", value: "meta-llama/llama-3.1-70b-instruct" },
      // { name: "deepseek/deepseek-chat (FAILS)", value: "deepseek/deepseek-chat" },
    ],
  },
  {
    id: 'together',
    name: 'Together AI (fast inference)',
    baseUrl: 'https://api.together.xyz/v1',
    keyName: 'Together AI',
    keyUrl: 'https://api.together.xyz/settings/api-keys',
    models: [
      {
        name: 'meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo (recommended)',
        value: 'meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo',
      },
      {
        name: 'meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo',
        value: 'meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo',
      },
      {
        name: 'mistralai/Mixtral-8x22B-Instruct-v0.1',
        value: 'mistralai/Mixtral-8x22B-Instruct-v0.1',
      },
      { name: 'Qwen/Qwen2.5-72B-Instruct-Turbo', value: 'Qwen/Qwen2.5-72B-Instruct-Turbo' },
    ],
    embedderModels: [
      { name: 'BAAI/bge-large-en-v1.5 (recommended)', value: 'BAAI/bge-large-en-v1.5' },
      {
        name: 'togethercomputer/m2-bert-80M-8k-retrieval',
        value: 'togethercomputer/m2-bert-80M-8k-retrieval',
      },
    ],
    defaultEmbedderDimensions: 1024,
  },
  {
    id: 'fireworks',
    name: 'Fireworks AI (low latency)',
    baseUrl: 'https://api.fireworks.ai/inference/v1',
    keyName: 'Fireworks AI',
    keyUrl: 'https://fireworks.ai/api-keys',
    models: [
      {
        name: 'accounts/fireworks/models/llama-v3p1-70b-instruct (recommended)',
        value: 'accounts/fireworks/models/llama-v3p1-70b-instruct',
      },
      {
        name: 'accounts/fireworks/models/mixtral-8x22b-instruct',
        value: 'accounts/fireworks/models/mixtral-8x22b-instruct',
      },
      {
        name: 'accounts/fireworks/models/qwen2p5-72b-instruct',
        value: 'accounts/fireworks/models/qwen2p5-72b-instruct',
      },
    ],
  },
  {
    id: 'deepinfra',
    name: 'DeepInfra (serverless GPUs)',
    baseUrl: 'https://api.deepinfra.com/v1/openai',
    keyName: 'DeepInfra',
    keyUrl: 'https://deepinfra.com/dash/api_keys',
    models: [
      {
        name: 'meta-llama/Meta-Llama-3.1-70B-Instruct (recommended)',
        value: 'meta-llama/Meta-Llama-3.1-70B-Instruct',
      },
      {
        name: 'mistralai/Mixtral-8x22B-Instruct-v0.1',
        value: 'mistralai/Mixtral-8x22B-Instruct-v0.1',
      },
      { name: 'Qwen/Qwen2.5-72B-Instruct', value: 'Qwen/Qwen2.5-72B-Instruct' },
    ],
    embedderModels: [
      { name: 'BAAI/bge-large-en-v1.5 (recommended)', value: 'BAAI/bge-large-en-v1.5' },
      {
        name: 'sentence-transformers/all-MiniLM-L6-v2',
        value: 'sentence-transformers/all-MiniLM-L6-v2',
      },
    ],
    defaultEmbedderDimensions: 1024,
  },
];

/**
 * Provider configurations
 */
const PROVIDERS: LLMProvider[] = [
  {
    id: 'openai',
    name: 'OpenAI (direct)',
    embedder: 'openai',
    needsOpenAI: true,
    models: [
      { name: 'gpt-4o-mini (recommended - fast & cost-effective)', value: 'gpt-4o-mini' },
      { name: 'gpt-4o (best quality)', value: 'gpt-4o' },
      { name: 'gpt-3.5-turbo (economy)', value: 'gpt-3.5-turbo' },
    ],
  },
  {
    id: 'openai-compatible',
    name: 'OpenAI-compatible (OpenRouter, Together, etc.)',
    embedder: 'openai-compatible',
    needsOpenAI: false,
  },
  {
    id: 'ollama',
    name: 'Ollama (local, free) - ⚠️ LLM FAILS, embeddings OK',
    embedder: 'ollama',
    needsOpenAI: false,
    models: [
      // ⚠️ WARNING: All Ollama LLM models FAIL Graphiti Pydantic validation
      // Use OpenRouter + Ollama (embeddings only) instead!
      { name: '⚠️ llama3.2 (FAILS Graphiti validation)', value: 'llama3.2' },
      { name: '⚠️ llama3.1:70b (FAILS Graphiti validation)', value: 'llama3.1:70b' },
      { name: '⚠️ mistral (FAILS Graphiti validation)', value: 'mistral' },
      { name: '⚠️ deepseek-r1:7b (FAILS Graphiti validation)', value: 'deepseek-r1:7b' },
      { name: '⚠️ qwen2.5:7b (FAILS Graphiti validation)', value: 'qwen2.5:7b' },
    ],
  },
  {
    id: 'hybrid',
    name: 'Hybrid (OpenAI LLM + Ollama embeddings - recommended)',
    embedder: 'ollama',
    needsOpenAI: true,
    models: [
      { name: 'gpt-4o-mini (recommended - fast & cost-effective)', value: 'gpt-4o-mini' },
      { name: 'gpt-4o (best quality)', value: 'gpt-4o' },
    ],
  },
  {
    id: 'anthropic',
    name: 'Anthropic Claude',
    embedder: 'openai',
    needsOpenAI: true,
  },
  {
    id: 'gemini',
    name: 'Google Gemini',
    embedder: 'gemini',
    needsOpenAI: false,
  },
  {
    id: 'groq',
    name: 'Groq (fast inference)',
    embedder: 'openai',
    needsOpenAI: true,
    models: [
      { name: 'llama-3.3-70b-versatile (recommended)', value: 'llama-3.3-70b-versatile' },
      { name: 'llama-3.1-70b-versatile', value: 'llama-3.1-70b-versatile' },
    ],
  },
];

/**
 * OpenAI API tiers
 */
const OPENAI_TIERS: APITier[] = [
  { name: 'Free tier', semaphoreLimit: 2 },
  { name: 'Tier 2 (60 requests/minute)', semaphoreLimit: 8 },
  { name: 'Tier 3 (500 requests/minute) - most common', semaphoreLimit: 10 },
  { name: 'Tier 4 (5000 requests/minute)', semaphoreLimit: 20 },
];

/**
 * Database backend choice
 */
interface DatabaseBackend {
  id: string;
  name: string;
  description: string;
}

/**
 * Database backends
 */
const DATABASE_BACKENDS: DatabaseBackend[] = [
  {
    id: 'neo4j',
    name: 'Neo4j (recommended)',
    description:
      'Native graph database with Cypher queries. Better special character handling, richer query language.',
  },
  {
    id: 'falkordb',
    name: 'FalkorDB',
    description: 'Redis-based graph database. Simpler setup, lower resource usage.',
  },
];

// =============================================================================
// NON-INTERACTIVE HELPERS
// =============================================================================

/**
 * Confirm wrapper that auto-accepts in non-interactive mode
 */
async function confirmWithDefault(message: string, defaultValue = true): Promise<boolean> {
  if (isNonInteractive) {
    cli.dim(`  Auto-${defaultValue ? 'accepting' : 'declining'}: ${message}`);
    return defaultValue;
  }
  const { result } = await inquirer.prompt([
    {
      type: 'confirm',
      name: 'result',
      message,
      default: defaultValue,
    },
  ]);
  return result;
}

/**
 * Press enter wrapper that skips in non-interactive mode
 */
async function pressEnterToContinue(message = 'Press Enter to continue...'): Promise<void> {
  if (isNonInteractive) {
    return;
  }
  await inquirer.prompt([
    {
      type: 'input',
      name: 'continue',
      message,
    },
  ]);
}

/**
 * Installation state
 */
interface InstallState {
  llmProvider: string;
  embedderProvider: string;
  modelName: string;
  semaphoreLimit: string;
  apiKeys: {
    OPENAI_API_KEY?: string;
    ANTHROPIC_API_KEY?: string;
    GOOGLE_API_KEY?: string;
    GROQ_API_KEY?: string;
    OPENAI_COMPATIBLE_KEY?: string;
  };
  paiConfig: {
    GROUP_ID?: string;
    DATABASE_TYPE?: string;
    GRAPHITI_TELEMETRY_ENABLED?: string;
  };
  // OpenAI-compatible provider configuration
  openaiCompatible?: {
    providerId: string;
    baseUrl: string;
    embedderBaseUrl?: string;
    embedderModel?: string;
    embedderDimensions?: number;
  };
}

/**
 * Installer class
 */
class Installer {
  private state: InstallState = {
    llmProvider: 'ollama',
    embedderProvider: 'ollama',
    modelName: 'llama3.2',
    semaphoreLimit: '10',
    apiKeys: {},
    paiConfig: {
      GROUP_ID: 'main',
      DATABASE_TYPE: 'neo4j',
      GRAPHITI_TELEMETRY_ENABLED: 'false',
    },
  };

  // Ollama configuration
  private ollamaBaseUrl = 'http://host.docker.internal:11434/v1';
  private embedderModel = 'mxbai-embed-large'; // Best Ollama embedder (77% quality, 156ms)

  private containerManager = createContainerManager();
  private configLoader = createConfigLoader();

  /**
   * Collect an API key with optional existing value
   */
  private async collectKey(
    keyName: string,
    keyUrl: string,
    existingValue?: string
  ): Promise<string | undefined> {
    cli.blank();
    cli.info(`You need a ${keyName} API key.`);
    cli.dim(`Get it from: ${keyUrl}`);
    cli.blank();

    // If we have an existing value, confirm it
    if (existingValue && existingValue.length > 0) {
      const masked = this.maskApiKey(existingValue);
      cli.info(`Found ${keyName} API key in PAI configuration.`);
      cli.dim(`Key: ${masked}`);
      cli.blank();

      // In non-interactive mode, always use existing key
      if (isNonInteractive) {
        cli.success(`Using existing ${keyName} API key`);
        return existingValue;
      }

      const { useKey } = await inquirer.prompt([
        {
          type: 'confirm',
          name: 'useKey',
          message: 'Use this key?',
          default: true,
        },
      ]);

      if (useKey) {
        cli.success(`Using existing ${keyName} API key`);
        return existingValue;
      }
    }

    // In non-interactive mode without existing key, check environment
    if (isNonInteractive) {
      // Try to get from environment variables
      // MADEINOZ_KNOWLEDGE_* prefixed variables take PRECEDENCE over unprefixed variables
      const envKey = keyName.includes('OpenAI')
        ? process.env.MADEINOZ_KNOWLEDGE_OPENAI_API_KEY || process.env.OPENAI_API_KEY
        : keyName.includes('Anthropic')
          ? process.env.MADEINOZ_KNOWLEDGE_ANTHROPIC_API_KEY || process.env.ANTHROPIC_API_KEY
          : keyName.includes('Google')
            ? process.env.MADEINOZ_KNOWLEDGE_GOOGLE_API_KEY || process.env.GOOGLE_API_KEY
            : keyName.includes('Groq')
              ? process.env.MADEINOZ_KNOWLEDGE_GROQ_API_KEY || process.env.GROQ_API_KEY
              : undefined;

      if (envKey) {
        cli.success(`Using ${keyName} API key from environment`);
        return envKey;
      }

      cli.warning(`No ${keyName} API key found - set via environment or run interactively`);
      return undefined;
    }

    // Prompt for new key
    const { apiKey } = await inquirer.prompt([
      {
        type: 'password',
        name: 'apiKey',
        message: `Enter your ${keyName} API key:`,
        validate: (input: string) => {
          if (!input || input.trim().length === 0) {
            return "No API key provided. You'll need to add it later.";
          }
          return true;
        },
      },
    ]);

    if (apiKey && apiKey.trim().length > 0) {
      cli.success(`${keyName} API key received`);
      return apiKey.trim();
    }
    cli.warning('No API key provided');
    return undefined;
  }

  /**
   * Mask API key for display
   */
  private maskApiKey(key: string): string {
    if (key.length <= 24) {
      return `${key.slice(0, 8)}...${key.slice(-4)}`;
    }
    return `${key.slice(0, 20)}...${key.slice(-4)}`;
  }

  /**
   * Read PAI configuration from PAI .env file
   * Path priority: PAI_DIR > ~/.claude > ~/.config/pai (legacy)
   */
  private async readPAIConfig(): Promise<void> {
    const possiblePaths = [
      process.env.PAI_DIR ? `${process.env.PAI_DIR}/.env` : '',
      `${process.env.HOME}/.claude/.env`,
      `${process.env.HOME}/.config/pai/.env`, // Legacy fallback
    ].filter(Boolean);

    let paiEnvPath: string | undefined;

    for (const path of possiblePaths) {
      try {
        const file = Bun.file(path);
        if (await file.exists()) {
          paiEnvPath = path;
          break;
        }
      } catch {
        // Continue
      }
    }

    if (!paiEnvPath) {
      return;
    }

    cli.blank();
    cli.info('Checking PAI configuration...');

    try {
      const file = Bun.file(paiEnvPath);
      const content = await file.text();
      const env: Record<string, string> = {};

      // Parse .env file
      for (const line of content.split('\n')) {
        const trimmed = line.trim();
        if (trimmed && !trimmed.startsWith('#')) {
          const eqIndex = trimmed.indexOf('=');
          if (eqIndex > 0) {
            const key = trimmed.slice(0, eqIndex).trim();
            const value = trimmed.slice(eqIndex + 1).trim();
            env[key] = value;
          }
        }
      }

      // Read MADEINOZ_KNOWLEDGE_* variables
      const paiPrefix = 'MADEINOZ_KNOWLEDGE_';
      let foundAny = false;

      for (const [key, value] of Object.entries(env)) {
        if (key.startsWith(paiPrefix)) {
          const configKey = key.slice(paiPrefix.length);
          const _standardKey = key.replace(paiPrefix, '');

          if (configKey === 'OPENAI_API_KEY') {
            this.state.apiKeys.OPENAI_API_KEY = value;
            foundAny = true;
          } else if (configKey === 'LLM_PROVIDER') {
            this.state.llmProvider = value;
            foundAny = true;
          } else if (configKey === 'EMBEDDER_PROVIDER') {
            this.state.embedderProvider = value;
          } else if (configKey === 'MODEL_NAME') {
            this.state.modelName = value;
            foundAny = true;
          } else if (configKey === 'SEMAPHORE_LIMIT') {
            this.state.semaphoreLimit = value;
          } else if (configKey === 'GROUP_ID') {
            this.state.paiConfig.GROUP_ID = value;
          } else if (configKey === 'DATABASE_TYPE') {
            this.state.paiConfig.DATABASE_TYPE = value;
          } else if (configKey === 'GRAPHITI_TELEMETRY_ENABLED') {
            this.state.paiConfig.GRAPHITI_TELEMETRY_ENABLED = value;
          }
        }
      }

      if (foundAny) {
        cli.success('Found Madeinoz Knowledge System configuration in PAI .env');
        if (this.state.llmProvider) {
          cli.success(`LLM Provider from config: ${this.state.llmProvider}`);
        }
        if (this.state.modelName) {
          cli.success(`Model from config: ${this.state.modelName}`);
        }
      }
    } catch {
      // Ignore errors reading PAI config
    }
  }

  /**
   * Step 1: Verify prerequisites
   */
  private async verifyPrerequisites(): Promise<void> {
    cli.blank();
    cli.header('Step 1: Verify Prerequisites');

    if (!this.containerManager.isRuntimeAvailable()) {
      cli.error('Podman is not installed!');
      cli.blank();
      cli.info('Please install Podman first:');
      cli.dim('  macOS: brew install podman');
      cli.dim('  Linux: sudo apt install podman');
      cli.blank();
      cli.dim('Visit: https://podman.io/getting-started/installation');
      process.exit(1);
    }

    const versionResult = await this.containerManager.exec(['--version'], { silent: true });
    if (versionResult.success) {
      cli.success(`Podman is installed: ${versionResult.stdout.trim()}`);
    }
  }

  /**
   * Step 2: Installation directory (skip in TS version - we know where we are)
   */
  private async confirmDirectory(): Promise<void> {
    cli.blank();
    cli.header('Step 2: Installation Directory');
    cli.info('Using current pack directory');
    cli.blank();
    cli.dim('(In TypeScript version, we always use the current pack directory)');
    await pressEnterToContinue();
  }

  /**
   * Step 3: Database Backend Selection
   */
  private async selectDatabaseBackend(): Promise<void> {
    cli.blank();
    cli.header('Step 3: Database Backend Selection');

    cli.blank();
    cli.info('Choose your graph database backend:');
    cli.blank();

    for (const backend of DATABASE_BACKENDS) {
      cli.dim(`  ${backend.name}`);
      cli.dim(`    ${backend.description}`);
      cli.blank();
    }

    let backend: string;

    if (isNonInteractive) {
      // Use existing backend from state (loaded from config) or default to neo4j
      backend = this.state.paiConfig.DATABASE_TYPE || 'neo4j';
      cli.dim(`  Using database backend: ${backend}`);
    } else {
      const result = await inquirer.prompt([
        {
          type: 'list',
          name: 'backend',
          message: 'Select database backend:',
          choices: DATABASE_BACKENDS.map((b) => ({ name: b.name, value: b.id })),
          default: this.state.paiConfig.DATABASE_TYPE || 'neo4j',
        },
      ]);
      backend = result.backend;
    }

    const selected = DATABASE_BACKENDS.find((b) => b.id === backend);
    if (!selected) {
      cli.error('Invalid backend selection');
      process.exit(1);
    }

    this.state.paiConfig.DATABASE_TYPE = selected.id;
    cli.success(`Selected: ${selected.name}`);

    // Show backend-specific information
    if (selected.id === 'neo4j') {
      cli.blank();
      cli.info('Neo4j provides:');
      cli.dim('  - Native Cypher query language');
      cli.dim('  - Neo4j Browser UI at http://localhost:7474');
      cli.dim('  - Bolt protocol at port 7687');
    } else {
      cli.blank();
      cli.info('FalkorDB provides:');
      cli.dim('  - Redis-based graph database');
      cli.dim('  - FalkorDB UI at http://localhost:3000');
      cli.dim('  - Lower memory footprint');
    }
  }

  /**
   * Step 4: LLM Provider Selection
   */
  private async selectProvider(): Promise<void> {
    cli.blank();
    cli.header('Step 4: LLM Provider Selection');

    let provider: string;

    if (isNonInteractive) {
      // Use existing provider from state (loaded from config) or default to openai
      provider = this.state.llmProvider || 'openai';
      cli.dim(`  Using provider: ${provider}`);
    } else {
      const result = await inquirer.prompt([
        {
          type: 'list',
          name: 'provider',
          message: 'Select your LLM provider:',
          choices: PROVIDERS.map((p) => ({ name: p.name, value: p.id })),
          default: this.state.llmProvider || 'openai',
        },
      ]);
      provider = result.provider;
    }

    const selected = PROVIDERS.find((p) => p.id === provider);
    if (!selected) {
      cli.error('Invalid provider selection');
      process.exit(1);
    }

    // Handle OpenAI-compatible provider sub-selection
    if (provider === 'openai-compatible') {
      await this.selectOpenAICompatibleProvider();
      return;
    }

    this.state.llmProvider = selected.id;
    this.state.embedderProvider = selected.embedder;

    if (selected.embedder !== selected.id) {
      cli.warning(`Selected: ${selected.name} (requires OpenAI for embeddings)`);
    } else {
      cli.success(`Selected: ${selected.name}`);
    }
  }

  /**
   * Sub-selection for OpenAI-compatible providers (OpenRouter, Together, etc.)
   */
  private async selectOpenAICompatibleProvider(): Promise<void> {
    cli.blank();
    cli.info('OpenAI-compatible providers use the same API format as OpenAI');
    cli.info('but with different base URLs and API keys.');
    cli.blank();

    let selectedProviderId: string;

    if (isNonInteractive) {
      // Use existing or default to openrouter
      selectedProviderId = this.state.openaiCompatible?.providerId || 'openrouter';
      cli.dim(`  Using OpenAI-compatible provider: ${selectedProviderId}`);
    } else {
      const result = await inquirer.prompt([
        {
          type: 'list',
          name: 'provider',
          message: 'Select OpenAI-compatible provider:',
          choices: OPENAI_COMPATIBLE_PROVIDERS.map((p) => ({ name: p.name, value: p.id })),
          default: this.state.openaiCompatible?.providerId || 'openrouter',
        },
      ]);
      selectedProviderId = result.provider;
    }

    const compatibleProvider = OPENAI_COMPATIBLE_PROVIDERS.find((p) => p.id === selectedProviderId);
    if (!compatibleProvider) {
      cli.error('Invalid OpenAI-compatible provider selection');
      process.exit(1);
    }

    // Store the OpenAI-compatible provider configuration
    this.state.llmProvider = 'openai'; // Use openai provider type (works with OpenAI-compatible API)
    this.state.openaiCompatible = {
      providerId: compatibleProvider.id,
      baseUrl: compatibleProvider.baseUrl,
    };

    // Handle embeddings - if provider has embeddings, use them; otherwise default to Ollama
    if (compatibleProvider.embedderModels && compatibleProvider.embedderModels.length > 0) {
      this.state.embedderProvider = 'openai'; // OpenAI-compatible for embeddings too
      this.state.openaiCompatible.embedderBaseUrl = compatibleProvider.baseUrl;
      this.state.openaiCompatible.embedderModel = compatibleProvider.embedderModels[0].value;
      this.state.openaiCompatible.embedderDimensions = compatibleProvider.defaultEmbedderDimensions;
      cli.success(`Selected: ${compatibleProvider.name} (LLM + embeddings)`);
    } else {
      // Provider doesn't have embeddings, offer Ollama or OpenAI
      cli.blank();
      cli.warning(`${compatibleProvider.name} doesn't provide embeddings.`);
      cli.info('You need a separate embedder. Options:');
      cli.dim('  1. Ollama (free, local) - recommended');
      cli.dim('  2. OpenAI (paid, cloud)');
      cli.blank();

      if (isNonInteractive) {
        this.state.embedderProvider = 'ollama';
        cli.dim('  Using Ollama for embeddings (free, local)');
      } else {
        const { embedder } = await inquirer.prompt([
          {
            type: 'list',
            name: 'embedder',
            message: 'Select embedder:',
            choices: [
              { name: 'Ollama (free, local) - recommended', value: 'ollama' },
              { name: 'OpenAI (paid, cloud)', value: 'openai' },
            ],
            default: 'ollama',
          },
        ]);
        this.state.embedderProvider = embedder;
      }

      cli.success(
        `Selected: ${compatibleProvider.name} (LLM) + ${this.state.embedderProvider === 'ollama' ? 'Ollama' : 'OpenAI'} (embeddings)`
      );
    }
  }

  /**
   * Step 5: API Key Collection
   */
  private async collectAPIKeys(): Promise<void> {
    cli.blank();
    cli.header('Step 5: API Key Configuration');

    // Read existing PAI config first
    await this.readPAIConfig();

    const provider = PROVIDERS.find((p) => p.id === this.state.llmProvider);

    if (!provider) {
      cli.error('Invalid provider');
      process.exit(1);
    }

    // Ollama doesn't need API keys
    if (this.state.llmProvider === 'ollama') {
      cli.blank();
      cli.success('Ollama selected - no API key required!');
      cli.blank();
      cli.info('Ollama Prerequisites:');
      cli.dim('  1. Install Ollama: https://ollama.com/download');
      cli.dim('  2. Pull required models:');
      cli.dim(`     ollama pull ${this.state.modelName}`);
      cli.dim(`     ollama pull ${this.embedderModel}`);
      cli.dim('  3. Ensure Ollama is running: ollama serve');
      cli.blank();

      // Configure Ollama base URL
      if (!isNonInteractive) {
        const { baseUrl } = await inquirer.prompt([
          {
            type: 'input',
            name: 'baseUrl',
            message: 'Ollama API URL (for Docker containers):',
            default: this.ollamaBaseUrl,
          },
        ]);
        this.ollamaBaseUrl = baseUrl;
      }

      cli.success(`Ollama endpoint: ${this.ollamaBaseUrl}`);
      return;
    }

    // Handle OpenAI-compatible provider (OpenRouter, Together, etc.)
    if (this.state.openaiCompatible) {
      const compatibleProvider = OPENAI_COMPATIBLE_PROVIDERS.find(
        (p) => p.id === this.state.openaiCompatible?.providerId
      );

      if (compatibleProvider) {
        this.state.apiKeys.OPENAI_COMPATIBLE_KEY = await this.collectKey(
          compatibleProvider.keyName,
          compatibleProvider.keyUrl,
          this.state.apiKeys.OPENAI_COMPATIBLE_KEY
        );

        // If embedder is Ollama, configure its base URL
        if (this.state.embedderProvider === 'ollama') {
          cli.blank();
          cli.info('Configuring Ollama for embeddings...');
          cli.dim('  Ollama Prerequisites:');
          cli.dim('  1. Install Ollama: https://ollama.com/download');
          cli.dim(`  2. Pull embedding model: ollama pull ${this.embedderModel}`);
          cli.dim('  3. Ensure Ollama is running: ollama serve');
          cli.blank();

          if (!isNonInteractive) {
            const { baseUrl } = await inquirer.prompt([
              {
                type: 'input',
                name: 'baseUrl',
                message: 'Ollama API URL (for Docker containers):',
                default: this.ollamaBaseUrl,
              },
            ]);
            this.ollamaBaseUrl = baseUrl;
          }
          cli.success(`Ollama endpoint for embeddings: ${this.ollamaBaseUrl}`);
        }

        // If embedder is OpenAI (not Ollama), need OpenAI key for embeddings
        if (
          this.state.embedderProvider === 'openai' &&
          !this.state.openaiCompatible.embedderBaseUrl
        ) {
          cli.blank();
          cli.info('You need an OpenAI API key for embeddings.');
          this.state.apiKeys.OPENAI_API_KEY = await this.collectKey(
            'OpenAI (for embeddings)',
            'https://platform.openai.com/api-keys',
            this.state.apiKeys.OPENAI_API_KEY
          );
        }

        return;
      }
    }

    // Collect OpenAI key if needed
    if (provider.needsOpenAI) {
      this.state.apiKeys.OPENAI_API_KEY = await this.collectKey(
        'Madeinoz Knowledge System OpenAI',
        'https://platform.openai.com/api-keys',
        this.state.apiKeys.OPENAI_API_KEY
      );
    }

    // Collect Anthropic key
    if (this.state.llmProvider === 'anthropic') {
      this.state.apiKeys.ANTHROPIC_API_KEY = await this.collectKey(
        'Anthropic',
        'https://console.anthropic.com/',
        this.state.apiKeys.ANTHROPIC_API_KEY
      );
    }

    // Collect Google key
    if (this.state.llmProvider === 'gemini' || this.state.embedderProvider === 'gemini') {
      this.state.apiKeys.GOOGLE_API_KEY = await this.collectKey(
        'Google',
        'https://aistudio.google.com/app/apikey',
        this.state.apiKeys.GOOGLE_API_KEY
      );
    }

    // Collect Groq key
    if (this.state.llmProvider === 'groq') {
      this.state.apiKeys.GROQ_API_KEY = await this.collectKey(
        'Groq',
        'https://console.groq.com/',
        this.state.apiKeys.GROQ_API_KEY
      );
    }
  }

  /**
   * Step 6: Model Selection
   */
  private async selectModel(): Promise<void> {
    cli.blank();
    cli.header('Step 6: Model Configuration');

    // Handle OpenAI-compatible provider models
    if (this.state.openaiCompatible) {
      const compatibleProvider = OPENAI_COMPATIBLE_PROVIDERS.find(
        (p) => p.id === this.state.openaiCompatible?.providerId
      );

      if (compatibleProvider && compatibleProvider.models.length > 0) {
        if (isNonInteractive) {
          // Use existing model or first available
          const existingModel = compatibleProvider.models.find(
            (m) => m.value === this.state.modelName
          );
          this.state.modelName = existingModel?.value || compatibleProvider.models[0].value;
          cli.dim(`  Using model: ${this.state.modelName}`);
        } else {
          const { model } = await inquirer.prompt([
            {
              type: 'list',
              name: 'model',
              message: `Select ${compatibleProvider.name} model:`,
              choices: compatibleProvider.models,
              default: this.state.modelName || compatibleProvider.models[0].value,
            },
          ]);
          this.state.modelName = model;
        }

        cli.success(`Selected model: ${this.state.modelName}`);

        // If provider has embedder models and we're using them, select embedder model too
        if (
          this.state.openaiCompatible.embedderBaseUrl &&
          compatibleProvider.embedderModels &&
          compatibleProvider.embedderModels.length > 0
        ) {
          cli.blank();
          cli.info('Configuring embeddings model...');

          if (isNonInteractive) {
            this.state.openaiCompatible.embedderModel = compatibleProvider.embedderModels[0].value;
            cli.dim(`  Using embedder: ${this.state.openaiCompatible.embedderModel}`);
          } else {
            const { embedderModel } = await inquirer.prompt([
              {
                type: 'list',
                name: 'embedderModel',
                message: `Select ${compatibleProvider.name} embeddings model:`,
                choices: compatibleProvider.embedderModels,
                default: compatibleProvider.embedderModels[0].value,
              },
            ]);
            this.state.openaiCompatible.embedderModel = embedderModel;
          }

          cli.success(`Selected embedder: ${this.state.openaiCompatible.embedderModel}`);
        }

        return;
      }
    }

    const provider = PROVIDERS.find((p) => p.id === this.state.llmProvider);

    if (!provider) {
      cli.error('Invalid provider');
      process.exit(1);
    }

    // If provider has specific models, prompt for selection
    if (provider.models && provider.models.length > 0) {
      if (isNonInteractive) {
        // Use existing model from state or first available
        const existingModel = provider.models.find((m) => m.value === this.state.modelName);
        this.state.modelName = existingModel?.value || provider.models[0].value;
        cli.dim(`  Using model: ${this.state.modelName}`);
      } else {
        const { model } = await inquirer.prompt([
          {
            type: 'list',
            name: 'model',
            message: `Select ${provider.name} model:`,
            choices: provider.models,
            default: this.state.modelName || provider.models[0].value,
          },
        ]);
        this.state.modelName = model;
      }
    } else {
      // Use default model for provider
      switch (this.state.llmProvider) {
        case 'anthropic':
          this.state.modelName = 'claude-sonnet-4-20250514';
          cli.info('Using Claude Sonnet 4');
          break;
        case 'gemini':
          this.state.modelName = 'gemini-2.0-flash-exp';
          cli.info('Using Gemini 2.0 Flash');
          break;
        default:
          this.state.modelName = 'gpt-4o-mini';
      }
    }

    cli.success(`Selected model: ${this.state.modelName}`);
  }

  /**
   * Step 7: Concurrency Configuration
   */
  private async configureConcurrency(): Promise<void> {
    cli.blank();
    cli.header('Step 7: Performance Configuration');

    if (this.state.llmProvider === 'openai') {
      if (isNonInteractive) {
        // Use existing or default to Tier 3 (most common)
        const existingLimit = Number.parseInt(this.state.semaphoreLimit, 10);
        if (!existingLimit || existingLimit < 1) {
          this.state.semaphoreLimit = '10';
        }
        cli.dim(`  Using concurrency limit: ${this.state.semaphoreLimit}`);
      } else {
        const { tier } = await inquirer.prompt([
          {
            type: 'list',
            name: 'tier',
            message: 'What is your OpenAI API tier?',
            choices: OPENAI_TIERS.map((t) => ({ name: t.name, value: t.semaphoreLimit })),
            default: Number.parseInt(this.state.semaphoreLimit, 10) || 10,
          },
        ]);
        this.state.semaphoreLimit = String(tier);
      }
    } else {
      this.state.semaphoreLimit = '5';
      cli.success('Using conservative concurrency: 5');
    }

    cli.success(`Concurrency limit: ${this.state.semaphoreLimit}`);
  }

  /**
   * Step 8: Create Configuration
   */
  private async createConfiguration(): Promise<void> {
    cli.blank();
    cli.header('Step 8: Saving to PAI .env');

    // PAI .env is the ONLY source of truth
    // Location: ${PAI_DIR}/.env or ~/.claude/.env
    cli.info(`Target: ${this.configLoader.getEnvFile()}`);
    cli.blank();

    // Backup existing PAI .env
    if (await this.configLoader.envExists()) {
      cli.warning(`Found existing PAI .env: ${this.configLoader.getEnvFile()}`);

      const shouldBackup = await confirmWithDefault('Backup and replace?', true);

      if (shouldBackup) {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
        const backupPath = `${this.configLoader.getEnvFile()}.backup.${timestamp}`;
        const originalFile = Bun.file(this.configLoader.getEnvFile());
        const content = await originalFile.text();
        await Bun.write(backupPath, content);
        cli.success(`Backed up to ${backupPath}`);
      } else {
        cli.error('Installation cancelled');
        process.exit(1);
      }
    }

    // Build configuration object
    const config: Record<string, string | undefined> = {
      OPENAI_API_KEY: this.state.apiKeys.OPENAI_API_KEY,
      ANTHROPIC_API_KEY: this.state.apiKeys.ANTHROPIC_API_KEY,
      GOOGLE_API_KEY: this.state.apiKeys.GOOGLE_API_KEY,
      GROQ_API_KEY: this.state.apiKeys.GROQ_API_KEY,
      LLM_PROVIDER: this.state.llmProvider,
      EMBEDDER_PROVIDER: this.state.embedderProvider,
      MODEL_NAME: this.state.modelName,
      SEMAPHORE_LIMIT: this.state.semaphoreLimit,
      GROUP_ID: this.state.paiConfig.GROUP_ID || 'main',
      DATABASE_TYPE: this.state.paiConfig.DATABASE_TYPE || 'neo4j',
      GRAPHITI_TELEMETRY_ENABLED: this.state.paiConfig.GRAPHITI_TELEMETRY_ENABLED || 'false',
    };

    // Add Ollama-specific configuration
    if (this.state.llmProvider === 'ollama') {
      config.OPENAI_BASE_URL = this.ollamaBaseUrl;
      config.EMBEDDER_MODEL = this.embedderModel;
    }

    // Add OpenAI-compatible provider configuration
    if (this.state.openaiCompatible) {
      // Use the provider's API key as OPENAI_API_KEY (works with OpenAI-compatible clients)
      config.OPENAI_API_KEY = this.state.apiKeys.OPENAI_COMPATIBLE_KEY;
      config.OPENAI_BASE_URL = this.state.openaiCompatible.baseUrl;

      // Note which provider we're using (for reference)
      config.OPENAI_COMPATIBLE_PROVIDER = this.state.openaiCompatible.providerId;

      // Configure embedder based on what's selected
      if (this.state.openaiCompatible.embedderBaseUrl) {
        // Using the same OpenAI-compatible provider for embeddings
        config.EMBEDDER_BASE_URL = this.state.openaiCompatible.embedderBaseUrl;
        config.EMBEDDER_MODEL = this.state.openaiCompatible.embedderModel;
        if (this.state.openaiCompatible.embedderDimensions) {
          config.EMBEDDER_DIMENSIONS = String(this.state.openaiCompatible.embedderDimensions);
        }
      } else if (this.state.embedderProvider === 'ollama') {
        // Using Ollama for embeddings
        config.EMBEDDER_BASE_URL = this.ollamaBaseUrl;
        config.EMBEDDER_MODEL = this.embedderModel;
        config.EMBEDDER_DIMENSIONS = '1024'; // mxbai-embed-large dimensions
      }
      // If embedderProvider is "openai" without embedderBaseUrl, we use standard OpenAI embeddings
      // In that case, OPENAI_API_KEY should be set separately for embeddings
    }

    // Add Hybrid configuration (OpenAI LLM + Ollama embeddings)
    if (
      this.state.llmProvider === 'hybrid' ||
      (this.state.llmProvider === 'openai' &&
        this.state.embedderProvider === 'ollama' &&
        !this.state.openaiCompatible)
    ) {
      config.EMBEDDER_BASE_URL = this.ollamaBaseUrl;
      config.EMBEDDER_MODEL = this.embedderModel;
      config.EMBEDDER_DIMENSIONS = '1024'; // mxbai-embed-large dimensions
    }

    // Save configuration
    await this.configLoader.save(config);

    cli.success(`Configuration saved to PAI .env: ${this.configLoader.getEnvFile()}`);
  }

  /**
   * Step 9: Start Services
   */
  private async startServices(): Promise<void> {
    cli.blank();
    cli.header('Step 9: Starting Services');

    cli.info('Starting Graphiti MCP server...');
    cli.blank();

    // Import and run the run.ts script
    const _startTime = Date.now();

    // Use spawn to run run.ts from the pack directory
    const packDir = import.meta.dir.replace(/\/src\/server$/, '');
    const proc = Bun.spawn(['bun', 'run', 'src/server/run.ts'], {
      stdout: 'inherit',
      stderr: 'inherit',
      cwd: packDir,
    });

    const exitCode = await proc.exited;

    if (exitCode !== 0) {
      cli.error('Failed to start services');
      process.exit(1);
    }

    cli.blank();
    cli.info('Waiting for server to start...');

    // Wait for server to be ready
    await new Promise((resolve) => setTimeout(resolve, 15000));

    // Check server health
    cli.blank();
    cli.info('Verifying server health...');

    try {
      const response = await fetch('http://localhost:8000/health', {
        signal: AbortSignal.timeout(5000),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.status === 'healthy' || data.status === 'ok') {
          cli.success('Server is running!');
        } else {
          cli.warning('Server health check inconclusive');
        }
      } else {
        cli.warning('Server health check inconclusive');
      }
    } catch {
      cli.warning('Server health check inconclusive');
      cli.dim('Check logs with: bun run server-cli logs');
    }
  }

  /**
   * Step 10: Install PAI Skill
   * Path priority: PAI_DIR > ~/.claude (PAI v2.1.0 standard)
   */
  private async installPAISkill(): Promise<void> {
    cli.blank();
    cli.header('Step 10: Installing PAI Skill');

    // Determine PAI directory - prefer PAI_DIR, then ~/.claude
    const possiblePaths = [
      process.env.PAI_DIR ? `${process.env.PAI_DIR}/skills` : '',
      `${process.env.HOME}/.claude/skills`,
    ].filter(Boolean);

    let paiSkillsDir: string | undefined;

    for (const path of possiblePaths) {
      try {
        const dir = Bun.file(path);
        if (await dir.exists()) {
          paiSkillsDir = path;
          break;
        }
      } catch {
        // Continue
      }
    }

    if (!paiSkillsDir) {
      cli.blank();
      cli.warning('PAI skills directory not found.');
      cli.info('Common locations:');
      cli.dim('  - ~/.claude/skills');
      cli.dim('  - $PAI_DIR/skills');
      cli.blank();

      if (isNonInteractive) {
        // Create default skills directory in non-interactive mode
        paiSkillsDir = `${process.env.HOME}/.claude/skills`;
        cli.dim(`  Creating default: ${paiSkillsDir}`);
        const { mkdirSync } = await import('node:fs');
        mkdirSync(paiSkillsDir, { recursive: true });
      } else {
        const { customDir } = await inquirer.prompt([
          {
            type: 'input',
            name: 'customDir',
            message: 'Enter PAI skills directory (or press Enter to skip):',
          },
        ]);

        if (customDir && customDir.trim().length > 0) {
          paiSkillsDir = customDir.trim();
        }
      }
    }

    if (paiSkillsDir) {
      cli.blank();
      cli.info(`Installing to: ${paiSkillsDir}/madeinoz-knowledge-system`);

      // Remove existing installation
      const existingPath = `${paiSkillsDir}/madeinoz-knowledge-system`;
      try {
        const existing = Bun.file(existingPath);
        if (await existing.exists()) {
          cli.warning('Removing existing installation');
          await this.containerManager.exec(['rm', '-rf', existingPath], { silent: true });
        }
      } catch {
        // Continue
      }

      // Copy skill directory
      const packDir = `${import.meta.dir}/../../../`;
      const skillSource = `${packDir}/Knowledge`;

      try {
        await this.containerManager.exec(
          ['cp', '-r', skillSource, `${paiSkillsDir}/madeinoz-knowledge-system`],
          {
            silent: false,
          }
        );
        cli.success('Madeinoz Knowledge System skill installed');
      } catch (error) {
        cli.error(`Failed to install PAI skill: ${String(error)}`);
      }
    } else {
      cli.warning('Skipping PAI skill installation. You can install it manually later.');
    }
  }

  /**
   * Step 11: Install Memory Sync Hook
   * Hooks install to ~/.claude/hooks/ where Claude Code reads them (PAI v2.1.0)
   * Updated for Memory System v7.0 (2026-01-12)
   */
  private async installMemorySyncHook(): Promise<void> {
    cli.blank();
    cli.header('Step 11: Installing Memory Sync Hook');

    cli.blank();
    cli.info('The Memory Sync Hook automatically syncs learnings and research');
    cli.info('from the PAI Memory System to your knowledge graph.');
    cli.blank();

    const installHook = await confirmWithDefault('Install the Memory Sync Hook?', true);

    if (!installHook) {
      cli.warning('Skipping hook installation. You can install it manually later.');
      return;
    }

    // Determine PAI hooks directory - ~/.claude is where Claude Code reads hooks
    const paiDir = process.env.PAI_DIR || `${process.env.HOME}/.claude`;
    const hooksDir = `${paiDir}/hooks`;
    const settingsPath = `${paiDir}/settings.json`;

    cli.blank();
    cli.info(`Installing hooks to: ${hooksDir}`);

    try {
      // Create hooks directory
      const { mkdirSync, existsSync, copyFileSync, readFileSync, writeFileSync } = await import(
        'node:fs'
      );
      const { join, dirname } = await import('node:path');

      if (!existsSync(hooksDir)) {
        mkdirSync(hooksDir, { recursive: true });
      }

      // Create lib subdirectory
      const libDir = join(hooksDir, 'lib');
      if (!existsSync(libDir)) {
        mkdirSync(libDir, { recursive: true });
      }

      // Copy hook files from pack
      const packDir = dirname(dirname(dirname(import.meta.dir)));
      const sourceHooksDir = join(packDir, 'src', 'hooks');

      const filesToCopy = [
        { src: 'sync-memory-to-knowledge.ts', dest: 'sync-memory-to-knowledge.ts' },
        { src: 'lib/frontmatter-parser.ts', dest: 'lib/frontmatter-parser.ts' },
        { src: 'lib/sync-state.ts', dest: 'lib/sync-state.ts' },
        { src: 'lib/knowledge-client.ts', dest: 'lib/knowledge-client.ts' },
        { src: 'lib/sync-config.ts', dest: 'lib/sync-config.ts' },
        { src: 'lib/anti-loop-patterns.ts', dest: 'lib/anti-loop-patterns.ts' },
      ];

      for (const file of filesToCopy) {
        const srcPath = join(sourceHooksDir, file.src);
        const destPath = join(hooksDir, file.dest);

        if (existsSync(srcPath)) {
          copyFileSync(srcPath, destPath);
          cli.success(`Installed: ${file.dest}`);
        } else {
          cli.warning(`Source not found: ${file.src}`);
        }
      }

      // Copy config file to ~/.claude/config/
      const configDir = join(paiDir, 'config');
      if (!existsSync(configDir)) {
        mkdirSync(configDir, { recursive: true });
      }

      const sourceConfigPath = join(packDir, 'config', 'sync-sources.json');
      const destConfigPath = join(configDir, 'sync-sources.json');

      if (existsSync(sourceConfigPath)) {
        // Only copy if destination doesn't exist (preserve user customizations)
        if (!existsSync(destConfigPath)) {
          copyFileSync(sourceConfigPath, destConfigPath);
          cli.success(`Installed: config/sync-sources.json`);
        } else {
          cli.dim('Config file exists, preserving user customizations');
        }
      }

      // Update settings.json to register the hook
      cli.blank();
      cli.info('Registering hook in settings.json...');

      let settings: any = {};
      if (existsSync(settingsPath)) {
        try {
          const content = readFileSync(settingsPath, 'utf-8');
          settings = JSON.parse(content);
        } catch {
          cli.warning('Could not parse existing settings.json, creating new');
        }
      }

      // Ensure hooks structure exists
      if (!settings.hooks) {
        settings.hooks = {};
      }

      // Add SessionStart hook if not already present
      const hookCommand = `bun run ${hooksDir}/sync-memory-to-knowledge.ts`;

      if (!settings.hooks.SessionStart) {
        settings.hooks.SessionStart = [];
      }

      // Check if hook already registered (check for both old and new names)
      const hookExists = settings.hooks.SessionStart.some((h: any) =>
        h.hooks?.some(
          (inner: any) =>
            inner.command?.includes('sync-memory-to-knowledge') ||
            inner.command?.includes('sync-history-to-knowledge')
        )
      );

      if (!hookExists) {
        settings.hooks.SessionStart.push({
          matcher: '*',
          hooks: [
            {
              type: 'command',
              command: hookCommand,
              timeout: 30000,
            },
          ],
        });

        writeFileSync(settingsPath, JSON.stringify(settings, null, 2));
        cli.success('Hook registered in settings.json');
      } else {
        cli.info('Hook already registered in settings.json');
      }

      cli.blank();
      cli.success('Memory Sync Hook installed!');
      cli.blank();
      cli.dim('The hook will:');
      cli.dim('  - Run on SessionStart');
      cli.dim('  - Sync LEARNING/ALGORITHM/, LEARNING/SYSTEM/, and RESEARCH/ to knowledge graph');
      cli.dim('  - Skip already-synced files');
      cli.dim('  - Gracefully handle MCP server being offline');
    } catch (error) {
      cli.error(`Failed to install hook: ${String(error)}`);
      cli.dim('You can install the hook manually later.');
    }
  }

  /**
   * Step 12: Installation Summary
   */
  private printSummary(): void {
    cli.blank();
    cli.header('Installation Complete!');

    cli.blank();
    cli.info('📦 Configuration Summary:');
    cli.blank();
    cli.dim(`Database Backend: ${this.state.paiConfig.DATABASE_TYPE}`);
    cli.dim(`LLM Provider: ${this.state.llmProvider}`);
    cli.dim(`Model: ${this.state.modelName}`);
    cli.dim(`Concurrency: ${this.state.semaphoreLimit}`);
    cli.blank();

    cli.info('Services:');
    cli.url('  MCP Server', 'http://localhost:8000/mcp/');
    if (this.state.paiConfig.DATABASE_TYPE === 'neo4j') {
      cli.url('  Neo4j Browser', 'http://localhost:7474');
      cli.dim('  Bolt URI: bolt://localhost:7687');
    } else {
      cli.url('  FalkorDB UI', 'http://localhost:3000');
    }
    cli.url('  Health Check', 'http://localhost:8000/health');
    cli.blank();

    cli.info('🎉 Next Steps:');
    cli.blank();
    cli.dim('1. Test the installation:');
    cli.dim("   Remember that I'm testing the Madeinoz Knowledge System.");
    cli.blank();
    cli.dim('2. Search your knowledge:');
    cli.dim('   What do I know about PAI?');
    cli.blank();
    cli.dim('3. Check system status:');
    cli.dim('   Show the knowledge graph status');
    cli.blank();
    cli.dim('4. Memory sync (automatic):');
    cli.dim('   Learnings and research from PAI Memory System');
    cli.dim('   are automatically synced on session start.');
    cli.blank();

    cli.info('Management Commands:');
    cli.dim('  View logs:    bun run server-cli logs');
    cli.dim('  Restart:      bun run server-cli restart');
    cli.dim('  Stop:         bun run server-cli stop');
    cli.dim('  Start:        bun run server-cli start');
    cli.dim('  Status:       bun run server-cli status');
    cli.blank();

    cli.success('Installation complete!');
  }

  /**
   * Run the full installation
   */
  async run(): Promise<void> {
    cli.clear();

    const modeLabel = isUpdateMode ? 'UPDATE' : isNonInteractive ? 'NON-INTERACTIVE' : 'v2.1.0';
    cli.header(`Madeinoz Knowledge System Installation (${modeLabel})`);
    cli.blank();

    // In non-interactive mode, always read existing config first
    if (isNonInteractive) {
      cli.info('Non-interactive mode: Using defaults and existing configuration.');
      cli.blank();
      await this.readPAIConfig();

      if (this.state.llmProvider) cli.dim(`  LLM Provider: ${this.state.llmProvider}`);
      if (this.state.modelName) cli.dim(`  Model: ${this.state.modelName}`);
      if (this.state.apiKeys.OPENAI_API_KEY)
        cli.dim(`  OpenAI API key: ****${this.state.apiKeys.OPENAI_API_KEY.slice(-4)}`);
      cli.blank();
    }

    if (isUpdateMode) {
      cli.info('Update mode: Preserving existing configuration where possible.');
      cli.blank();
      cli.dim('  - Will use existing API keys as defaults');
      cli.dim('  - Will preserve LLM provider settings');
      cli.dim('  - Only updates infrastructure files');
      cli.blank();

      // Check for existing installation
      if (!this.configLoader.envExists()) {
        cli.error('Update mode requires an existing installation.');
        cli.dim('Run without --update for a fresh install.');
        process.exit(1);
      }

      // Read existing config first (if not already read in non-interactive mode)
      if (!isNonInteractive) {
        await this.readPAIConfig();

        cli.info('Found existing configuration:');
        if (this.state.llmProvider) cli.dim(`  LLM Provider: ${this.state.llmProvider}`);
        if (this.state.modelName) cli.dim(`  Model: ${this.state.modelName}`);
        if (this.state.apiKeys.OPENAI_API_KEY)
          cli.dim(`  OpenAI API key: ****${this.state.apiKeys.OPENAI_API_KEY.slice(-4)}`);
        cli.blank();
      }

      const proceed = await confirmWithDefault('Proceed with update?', true);

      if (!proceed) {
        cli.info('Update cancelled.');
        process.exit(0);
      }
    } else if (!isNonInteractive) {
      cli.info('This script will install and configure the Madeinoz Knowledge System.');
      cli.blank();
      cli.info('Prerequisites:');
      cli.dim('  - Podman (must be installed)');
      cli.dim('  - At least one LLM provider API key');
      cli.blank();

      await pressEnterToContinue();
    }

    await this.verifyPrerequisites();

    if (!isUpdateMode && !isNonInteractive) {
      await this.confirmDirectory();
    }

    await this.selectDatabaseBackend();
    await this.selectProvider();
    await this.collectAPIKeys();
    await this.selectModel();
    await this.configureConcurrency();
    await this.createConfiguration();
    await this.startServices();
    await this.installPAISkill();
    await this.installMemorySyncHook();
    this.printSummary();
  }
}

/**
 * Main function
 */
async function main() {
  const installer = new Installer();
  await installer.run();
}

// Run main function
main().catch((error) => {
  cli.error('Unexpected error:');
  console.error(error);
  process.exit(1);
});
