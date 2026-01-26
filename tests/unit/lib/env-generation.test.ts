/**
 * Unit Tests for Environment Variable Generation
 *
 * Tests the .env file generation logic from start.sh
 * This verifies that MADEINOZ_KNOWLEDGE_* prefixed variables are correctly
 * mapped to unprefixed container variables.
 */

import { describe, it, expect, beforeEach } from 'bun:test';

/**
 * Simulates the environment variable generation from start.sh
 */
function generateContainerEnv(sourceEnv: Record<string, string>): string {
  const lines: string[] = [];

  // LLM Provider Configuration
  lines.push('# LLM Provider Configuration');
  lines.push(`LLM_PROVIDER=${sourceEnv.MADEINOZ_KNOWLEDGE_LLM_PROVIDER || 'openai'}`);
  lines.push(`MODEL_NAME=${sourceEnv.MADEINOZ_KNOWLEDGE_MODEL_NAME || 'openai/gpt-4o-mini'}`);
  lines.push(`TEMPERATURE=${sourceEnv.MADEINOZ_KNOWLEDGE_TEMPERATURE || ''}`);
  lines.push(`MAX_TOKENS=${sourceEnv.MADEINOZ_KNOWLEDGE_MAX_TOKENS || ''}`);
  lines.push('');

  // OpenAI/OpenRouter API Configuration
  lines.push('# OpenAI/OpenRouter API Configuration');
  lines.push(`OPENAI_API_KEY=${sourceEnv.MADEINOZ_KNOWLEDGE_OPENAI_API_KEY || ''}`);
  lines.push(`OPENAI_BASE_URL=${sourceEnv.MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL || 'https://openrouter.ai/api/v1'}`);
  lines.push(`OPENAI_ORGANIZATION_ID=${sourceEnv.MADEINOZ_KNOWLEDGE_OPENAI_ORGANIZATION_ID || ''}`);
  lines.push('');

  // Anthropic API Configuration
  lines.push('# Anthropic API Configuration');
  lines.push(`ANTHROPIC_API_KEY=${sourceEnv.MADEINOZ_KNOWLEDGE_ANTHROPIC_API_KEY || ''}`);
  lines.push(`ANTHROPIC_API_URL=${sourceEnv.MADEINOZ_KNOWLEDGE_ANTHROPIC_API_URL || ''}`);
  lines.push('');

  // Google Gemini API Configuration
  lines.push('# Google Gemini API Configuration');
  lines.push(`GOOGLE_API_KEY=${sourceEnv.MADEINOZ_KNOWLEDGE_GOOGLE_API_KEY || ''}`);
  lines.push(`GOOGLE_PROJECT_ID=${sourceEnv.MADEINOZ_KNOWLEDGE_GOOGLE_PROJECT_ID || ''}`);
  lines.push(`GOOGLE_LOCATION=${sourceEnv.MADEINOZ_KNOWLEDGE_GOOGLE_LOCATION || ''}`);
  lines.push('');

  // Groq API Configuration
  lines.push('# Groq API Configuration');
  lines.push(`GROQ_API_KEY=${sourceEnv.MADEINOZ_KNOWLEDGE_GROQ_API_KEY || ''}`);
  lines.push(`GROQ_API_URL=${sourceEnv.MADEINOZ_KNOWLEDGE_GROQ_API_URL || ''}`);
  lines.push('');

  // Azure OpenAI Configuration
  lines.push('# Azure OpenAI Configuration');
  lines.push(`AZURE_OPENAI_API_KEY=${sourceEnv.MADEINOZ_KNOWLEDGE_AZURE_OPENAI_API_KEY || ''}`);
  lines.push(`AZURE_OPENAI_ENDPOINT=${sourceEnv.MADEINOZ_KNOWLEDGE_AZURE_OPENAI_ENDPOINT || ''}`);
  lines.push(`AZURE_OPENAI_API_VERSION=${sourceEnv.MADEINOZ_KNOWLEDGE_AZURE_OPENAI_API_VERSION || ''}`);
  lines.push(`AZURE_OPENAI_DEPLOYMENT=${sourceEnv.MADEINOZ_KNOWLEDGE_AZURE_OPENAI_DEPLOYMENT || ''}`);
  lines.push(`USE_AZURE_AD=${sourceEnv.MADEINOZ_KNOWLEDGE_USE_AZURE_AD || ''}`);
  lines.push('');

  // Embedder Configuration
  lines.push('# Embedder Configuration');
  lines.push(`EMBEDDER_PROVIDER=${sourceEnv.MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER || 'ollama'}`);
  lines.push(`EMBEDDER_MODEL=${sourceEnv.MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL || 'mxbai-embed-large'}`);
  lines.push(`EMBEDDER_DIMENSIONS=${sourceEnv.MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS || '1024'}`);
  lines.push(`EMBEDDER_BASE_URL=${sourceEnv.MADEINOZ_KNOWLEDGE_EMBEDDER_BASE_URL || ''}`);
  lines.push('');

  // Ollama Configuration
  lines.push('# Ollama Configuration');
  lines.push(`OLLAMA_BASE_URL=${sourceEnv.MADEINOZ_KNOWLEDGE_OLLAMA_BASE_URL || 'http://host.containers.internal:11434'}`);
  lines.push('');

  // Azure OpenAI Embeddings Configuration
  lines.push('# Azure OpenAI Embeddings Configuration');
  lines.push(`AZURE_OPENAI_EMBEDDINGS_ENDPOINT=${sourceEnv.MADEINOZ_KNOWLEDGE_AZURE_OPENAI_EMBEDDINGS_ENDPOINT || ''}`);
  lines.push(`AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT=${sourceEnv.MADEINOZ_KNOWLEDGE_AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT || ''}`);
  lines.push('');

  // Voyage AI Configuration
  lines.push('# Voyage AI Configuration');
  lines.push(`VOYAGE_API_KEY=${sourceEnv.MADEINOZ_KNOWLEDGE_VOYAGE_API_KEY || ''}`);
  lines.push(`VOYAGE_API_URL=${sourceEnv.MADEINOZ_KNOWLEDGE_VOYAGE_API_URL || ''}`);
  lines.push('');

  // Graphiti Configuration
  lines.push('# Graphiti Configuration');
  lines.push(`GRAPHITI_GROUP_ID=${sourceEnv.MADEINOZ_KNOWLEDGE_GROUP_ID || 'main'}`);
  lines.push(`EPISODE_ID_PREFIX=${sourceEnv.MADEINOZ_KNOWLEDGE_EPISODE_ID_PREFIX || ''}`);
  lines.push(`USER_ID=${sourceEnv.MADEINOZ_KNOWLEDGE_USER_ID || ''}`);
  lines.push(`SEMAPHORE_LIMIT=${sourceEnv.MADEINOZ_KNOWLEDGE_SEMAPHORE_LIMIT || '10'}`);
  lines.push(`GRAPHITI_TELEMETRY_ENABLED=${sourceEnv.MADEINOZ_KNOWLEDGE_GRAPHITI_TELEMETRY_ENABLED || 'false'}`);
  lines.push(`GRAPHITI_SEARCH_ALL_GROUPS=${sourceEnv.GRAPHITI_SEARCH_ALL_GROUPS || 'false'}`);
  lines.push(`DATABASE_TYPE=${sourceEnv.MADEINOZ_KNOWLEDGE_DATABASE_TYPE || 'neo4j'}`);
  lines.push('');

  // Neo4j Configuration (pass through unprefixed)
  lines.push('# Neo4j Configuration (pass through unprefixed - shared infrastructure)');
  lines.push(`NEO4J_URI=${sourceEnv.NEO4J_URI || 'bolt://neo4j:7687'}`);
  lines.push(`NEO4J_USER=${sourceEnv.NEO4J_USER || 'neo4j'}`);
  lines.push(`NEO4J_PASSWORD=${sourceEnv.NEO4J_PASSWORD || 'madeinozknowledge'}`);
  lines.push(`NEO4J_DATABASE=${sourceEnv.NEO4J_DATABASE || 'neo4j'}`);
  lines.push(`USE_PARALLEL_RUNTIME=${sourceEnv.USE_PARALLEL_RUNTIME || ''}`);
  lines.push('');

  // FalkorDB Configuration
  lines.push('# FalkorDB Configuration');
  lines.push(`FALKORDB_HOST=${sourceEnv.MADEINOZ_KNOWLEDGE_FALKORDB_HOST || 'falkordb'}`);
  lines.push(`FALKORDB_PORT=${sourceEnv.MADEINOZ_KNOWLEDGE_FALKORDB_PORT || '6379'}`);
  lines.push(`FALKORDB_PASSWORD=${sourceEnv.MADEINOZ_KNOWLEDGE_FALKORDB_PASSWORD || ''}`);
  lines.push(`FALKORDB_URI=${sourceEnv.FALKORDB_URI || ''}`);

  return lines.join('\n');
}

/**
 * Parse generated .env file into key-value pairs
 */
function parseEnvFile(content: string): Record<string, string> {
  const env: Record<string, string> = {};
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
  return env;
}

describe('Environment Variable Generation', () => {
  describe('LLM Provider Configuration', () => {
    it('should map MADEINOZ_KNOWLEDGE_LLM_PROVIDER to LLM_PROVIDER', () => {
      const source = {
        MADEINOZ_KNOWLEDGE_LLM_PROVIDER: 'anthropic',
      };
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.LLM_PROVIDER).toBe('anthropic');
    });

    it('should map MADEINOZ_KNOWLEDGE_MODEL_NAME to MODEL_NAME', () => {
      const source = {
        MADEINOZ_KNOWLEDGE_MODEL_NAME: 'google/gemini-2.0-flash-001',
      };
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.MODEL_NAME).toBe('google/gemini-2.0-flash-001');
    });

    it('should use default LLM provider when not specified', () => {
      const source = {};
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.LLM_PROVIDER).toBe('openai');
    });

    it('should use default model name when not specified', () => {
      const source = {};
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.MODEL_NAME).toBe('openai/gpt-4o-mini');
    });
  });

  describe('API Key Configuration', () => {
    it('should map MADEINOZ_KNOWLEDGE_OPENAI_API_KEY to OPENAI_API_KEY', () => {
      const source = {
        MADEINOZ_KNOWLEDGE_OPENAI_API_KEY: 'sk-test-key-12345',
      };
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.OPENAI_API_KEY).toBe('sk-test-key-12345');
    });

    it('should map MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL to OPENAI_BASE_URL', () => {
      const source = {
        MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL: 'https://openrouter.ai/api/v1',
      };
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.OPENAI_BASE_URL).toBe('https://openrouter.ai/api/v1');
    });

    it('should use default base URL when not specified', () => {
      const source = {};
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.OPENAI_BASE_URL).toBe('https://openrouter.ai/api/v1');
    });

    it('should map Anthropic API key', () => {
      const source = {
        MADEINOZ_KNOWLEDGE_ANTHROPIC_API_KEY: 'sk-ant-test-key',
      };
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.ANTHROPIC_API_KEY).toBe('sk-ant-test-key');
    });

    it('should map Google API key', () => {
      const source = {
        MADEINOZ_KNOWLEDGE_GOOGLE_API_KEY: 'google-test-key',
      };
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.GOOGLE_API_KEY).toBe('google-test-key');
    });
  });

  describe('Embedder Configuration', () => {
    it('should map MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER to EMBEDDER_PROVIDER', () => {
      const source = {
        MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER: 'openai',
      };
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.EMBEDDER_PROVIDER).toBe('openai');
    });

    it('should map MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL to EMBEDDER_MODEL', () => {
      const source = {
        MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL: 'text-embedding-3-small',
      };
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.EMBEDDER_MODEL).toBe('text-embedding-3-small');
    });

    it('should map MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS to EMBEDDER_DIMENSIONS', () => {
      const source = {
        MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS: '1536',
      };
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.EMBEDDER_DIMENSIONS).toBe('1536');
    });

    it('should use default embedder provider when not specified', () => {
      const source = {};
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.EMBEDDER_PROVIDER).toBe('ollama');
    });

    it('should map MADEINOZ_KNOWLEDGE_OLLAMA_BASE_URL to OLLAMA_BASE_URL', () => {
      const source = {
        MADEINOZ_KNOWLEDGE_OLLAMA_BASE_URL: 'http://host.containers.internal:11434',
      };
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.OLLAMA_BASE_URL).toBe('http://host.containers.internal:11434');
    });
  });

  describe('Graphiti Configuration', () => {
    it('should map MADEINOZ_KNOWLEDGE_GROUP_ID to GRAPHITI_GROUP_ID', () => {
      const source = {
        MADEINOZ_KNOWLEDGE_GROUP_ID: 'test-group',
      };
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.GRAPHITI_GROUP_ID).toBe('test-group');
    });

    it('should map MADEINOZ_KNOWLEDGE_SEMAPHORE_LIMIT to SEMAPHORE_LIMIT', () => {
      const source = {
        MADEINOZ_KNOWLEDGE_SEMAPHORE_LIMIT: '20',
      };
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.SEMAPHORE_LIMIT).toBe('20');
    });

    it('should use default group ID when not specified', () => {
      const source = {};
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.GRAPHITI_GROUP_ID).toBe('main');
    });

    it('should use default semaphore limit when not specified', () => {
      const source = {};
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.SEMAPHORE_LIMIT).toBe('10');
    });

    it('should map MADEINOZ_KNOWLEDGE_GRAPHITI_TELEMETRY_ENABLED to GRAPHITI_TELEMETRY_ENABLED', () => {
      const source = {
        MADEINOZ_KNOWLEDGE_GRAPHITI_TELEMETRY_ENABLED: 'true',
      };
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.GRAPHITI_TELEMETRY_ENABLED).toBe('true');
    });
  });

  describe('GRAPHITI_SEARCH_ALL_GROUPS Variable (Renamed)', () => {
    it('should use new GRAPHITI_SEARCH_ALL_GROUPS variable name', () => {
      const source = {
        GRAPHITI_SEARCH_ALL_GROUPS: 'true',
      };
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.GRAPHITI_SEARCH_ALL_GROUPS).toBe('true');
    });

    it('should use default value for GRAPHITI_SEARCH_ALL_GROUPS when not specified', () => {
      const source = {};
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.GRAPHITI_SEARCH_ALL_GROUPS).toBe('false');
    });

    it('should not contain old MADEINOZ_KNOWLEDGE_SEARCH_ALL_GROUPS in generated env', () => {
      const source = {
        GRAPHITI_SEARCH_ALL_GROUPS: 'true',
      };
      const content = generateContainerEnv(source);
      expect(content).not.toContain('MADEINOZ_KNOWLEDGE_SEARCH_ALL_GROUPS');
    });
  });

  describe('Database Configuration', () => {
    it('should map MADEINOZ_KNOWLEDGE_DATABASE_TYPE to DATABASE_TYPE', () => {
      const source = {
        MADEINOZ_KNOWLEDGE_DATABASE_TYPE: 'falkordb',
      };
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.DATABASE_TYPE).toBe('falkordb');
    });

    it('should use default database type when not specified', () => {
      const source = {};
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.DATABASE_TYPE).toBe('neo4j');
    });

    it('should pass through NEO4J_URI unprefixed', () => {
      const source = {
        NEO4J_URI: 'bolt://custom-neo4j:7687',
      };
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.NEO4J_URI).toBe('bolt://custom-neo4j:7687');
    });

    it('should use default NEO4J_URI when not specified', () => {
      const source = {};
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.NEO4J_URI).toBe('bolt://neo4j:7687');
    });

    it('should map MADEINOZ_KNOWLEDGE_FALKORDB_HOST to FALKORDB_HOST', () => {
      const source = {
        MADEINOZ_KNOWLEDGE_FALKORDB_HOST: 'custom-falkordb',
      };
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.FALKORDB_HOST).toBe('custom-falkordb');
    });

    it('should use default FALKORDB_HOST when not specified', () => {
      const source = {};
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.FALKORDB_HOST).toBe('falkordb');
    });
  });

  describe('Azure OpenAI Configuration', () => {
    it('should map all Azure OpenAI variables', () => {
      const source = {
        MADEINOZ_KNOWLEDGE_AZURE_OPENAI_API_KEY: 'azure-key',
        MADEINOZ_KNOWLEDGE_AZURE_OPENAI_ENDPOINT: 'https://openai.azure.com/',
        MADEINOZ_KNOWLEDGE_AZURE_OPENAI_API_VERSION: '2024-01-01',
        MADEINOZ_KNOWLEDGE_AZURE_OPENAI_DEPLOYMENT: 'gpt-4',
        MADEINOZ_KNOWLEDGE_USE_AZURE_AD: 'true',
      };
      const result = parseEnvFile(generateContainerEnv(source));
      expect(result.AZURE_OPENAI_API_KEY).toBe('azure-key');
      expect(result.AZURE_OPENAI_ENDPOINT).toBe('https://openai.azure.com/');
      expect(result.AZURE_OPENAI_API_VERSION).toBe('2024-01-01');
      expect(result.AZURE_OPENAI_DEPLOYMENT).toBe('gpt-4');
      expect(result.USE_AZURE_AD).toBe('true');
    });
  });

  describe('Complete Configuration', () => {
    it('should generate complete .env file with all variables', () => {
      const source = {
        MADEINOZ_KNOWLEDGE_LLM_PROVIDER: 'openai',
        MADEINOZ_KNOWLEDGE_MODEL_NAME: 'google/gemini-2.0-flash-001',
        MADEINOZ_KNOWLEDGE_OPENAI_API_KEY: 'sk-test-key',
        MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL: 'https://openrouter.ai/api/v1',
        MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER: 'ollama',
        MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL: 'mxbai-embed-large',
        MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS: '1024',
        MADEINOZ_KNOWLEDGE_OLLAMA_BASE_URL: 'http://host.containers.internal:11434',
        MADEINOZ_KNOWLEDGE_GROUP_ID: 'test-group',
        MADEINOZ_KNOWLEDGE_SEMAPHORE_LIMIT: '15',
        MADEINOZ_KNOWLEDGE_GRAPHITI_TELEMETRY_ENABLED: 'false',
        GRAPHITI_SEARCH_ALL_GROUPS: 'true',
        MADEINOZ_KNOWLEDGE_DATABASE_TYPE: 'neo4j',
      };

      const content = generateContainerEnv(source);
      const result = parseEnvFile(content);

      // Verify all key mappings
      expect(result.LLM_PROVIDER).toBe('openai');
      expect(result.MODEL_NAME).toBe('google/gemini-2.0-flash-001');
      expect(result.OPENAI_API_KEY).toBe('sk-test-key');
      expect(result.OPENAI_BASE_URL).toBe('https://openrouter.ai/api/v1');
      expect(result.EMBEDDER_PROVIDER).toBe('ollama');
      expect(result.EMBEDDER_MODEL).toBe('mxbai-embed-large');
      expect(result.EMBEDDER_DIMENSIONS).toBe('1024');
      expect(result.OLLAMA_BASE_URL).toBe('http://host.containers.internal:11434');
      expect(result.GRAPHITI_GROUP_ID).toBe('test-group');
      expect(result.SEMAPHORE_LIMIT).toBe('15');
      expect(result.GRAPHITI_TELEMETRY_ENABLED).toBe('false');
      expect(result.GRAPHITI_SEARCH_ALL_GROUPS).toBe('true');
      expect(result.DATABASE_TYPE).toBe('neo4j');

      // Verify no prefixed variables in output
      expect(content).not.toContain('MADEINOZ_KNOWLEDGE_');
    });

    it('should include comments in generated .env file', () => {
      const source = {};
      const content = generateContainerEnv(source);

      expect(content).toContain('# LLM Provider Configuration');
      expect(content).toContain('# OpenAI/OpenRouter API Configuration');
      expect(content).toContain('# Embedder Configuration');
      expect(content).toContain('# Graphiti Configuration');
      expect(content).toContain('# Neo4j Configuration');
      expect(content).toContain('# FalkorDB Configuration');
    });
  });

  describe('Empty and Optional Values', () => {
    it('should handle empty string values correctly', () => {
      const source = {
        MADEINOZ_KNOWLEDGE_TEMPERATURE: '',
        MADEINOZ_KNOWLEDGE_MAX_TOKENS: '',
        MADEINOZ_KNOWLEDGE_OPENAI_API_KEY: '',
      };
      const result = parseEnvFile(generateContainerEnv(source));

      expect(result.TEMPERATURE).toBe('');
      expect(result.MAX_TOKENS).toBe('');
      expect(result.OPENAI_API_KEY).toBe('');
    });

    it('should handle undefined values correctly', () => {
      const source = {};
      const result = parseEnvFile(generateContainerEnv(source));

      // These should have defaults
      expect(result.LLM_PROVIDER).toBeDefined();
      expect(result.MODEL_NAME).toBeDefined();
      expect(result.EMBEDDER_PROVIDER).toBeDefined();

      // These should be empty when not specified
      expect(result.OPENAI_API_KEY).toBe('');
      expect(result.TEMPERATURE).toBe('');
    });
  });
});
