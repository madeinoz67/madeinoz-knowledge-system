/**
 * Knowledge Client for Hooks
 *
 * Lightweight client for hook integration with the knowledge graph MCP.
 * Uses database-specific protocols: FalkorDB uses SSE (/sse), Neo4j uses HTTP POST (/mcp).
 * Designed for fail-safe operation with timeouts and graceful degradation.
 *
 * NOTE: Lucene sanitization is now handled server-side by the Python patch
 * (falkordb_lucene.py). The client passes group_ids directly without escaping.
 */

import { join } from 'node:path';
import { existsSync, readFileSync } from 'node:fs';

/**
 * Load environment variables from PAI .env file
 * Priority: $PAI_DIR/.env > ~/.claude/.env
 *
 * This must be called before accessing environment variables to ensure
 * the .env file is loaded into process.env
 */
async function loadEnvFile(): Promise<void> {
  // Check if already loaded (skip if we already have the MCP URL set)
  if (process.env.MADEINOZ_KNOWLEDGE_MCP_URL) {
    return;
  }

  // Determine env file path: $PAI_DIR/.env takes priority
  const paiDir = process.env.PAI_DIR;
  const homeDir = process.env.HOME || process.env.USERPROFILE || '';
  const envFile = paiDir ? join(paiDir, '.env') : join(homeDir, '.claude', '.env');

  // Check if .env file exists
  if (!existsSync(envFile)) {
    return;
  }

  // Read and parse .env file
  const content = readFileSync(envFile, 'utf-8');
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

      // Only set if not already in process.env (env vars take precedence)
      if (process.env[key] === undefined) {
        process.env[key] = unquoted;
      }
    }
  }
}

// Load .env file immediately on module import
let envLoadPromise: Promise<void> | null = null;

function ensureEnvLoaded(): Promise<void> {
  if (!envLoadPromise) {
    envLoadPromise = loadEnvFile();
  }
  return envLoadPromise;
}

export interface KnowledgeClientConfig {
  baseURL: string;
  timeout: number;
  retries: number;
}

export interface AddEpisodeParams {
  name: string;
  episode_body: string;
  source?: string;
  source_description?: string;
  reference_timestamp?: string;
  group_id?: string;
}

export interface AddEpisodeResult {
  success: boolean;
  uuid?: string;
  error?: string;
}

/**
 * Database type for protocol and sanitization selection
 */
type DatabaseType = 'neo4j' | 'falkorodb';

/**
 * Get default configuration (loads .env file first)
 */
function getDefaultConfig(): KnowledgeClientConfig {
  return {
    baseURL: process.env.MADEINOZ_KNOWLEDGE_MCP_URL || 'http://localhost:8000',
    timeout: Number.parseInt(process.env.MADEINOZ_KNOWLEDGE_TIMEOUT || '15000', 10),
    retries: Number.parseInt(process.env.MADEINOZ_KNOWLEDGE_RETRIES || '3', 10),
  };
}

const DEFAULT_CONFIG = getDefaultConfig();

/**
 * Get database type from environment variable with validation
 */
function getDatabaseType(): DatabaseType {
  const dbType = process.env.MADEINOZ_KNOWLEDGE_DB || 'neo4j';
  const validDbTypes: DatabaseType[] = ['neo4j', 'falkorodb'];

  if (!validDbTypes.includes(dbType as DatabaseType)) {
    throw new Error(
      `Invalid MADEINOZ_KNOWLEDGE_DB: ${dbType}. Must be one of: ${validDbTypes.join(', ')}`
    );
  }

  return dbType as DatabaseType;
}

/**
 * Check if database is FalkorDB (requires SSE protocol and sanitization)
 */
function isFalkorDB(): boolean {
  return getDatabaseType() === 'falkorodb';
}

/**
 * Parse SSE event data from response text (for FalkorDB SSE protocol)
 */
function parseSSEEvent(text: string): { event?: string; data?: string } {
  const lines = text.split('\n');
  let event: string | undefined;
  let data: string | undefined;

  for (const line of lines) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      data = line.slice(5).trim();
    }
  }

  return { event, data };
}

/**
 * Parse SSE response body to extract JSON-RPC result (for Neo4j HTTP POST protocol)
 * Response body contains lines like "data: {...}\n"
 */
function parseSSEResponse(text: string): unknown {
  const lines = text.split('\n');
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const jsonStr = line.substring(6);
      try {
        const parsed = JSON.parse(jsonStr);
        // Extract result from the MCP response format
        if (parsed.result) {
          // Handle tool call response format
          if (parsed.result.content && Array.isArray(parsed.result.content)) {
            // Check for structuredContent first (preferred)
            if (parsed.result.structuredContent) {
              const sc = parsed.result.structuredContent;
              // Unwrap Graphiti's result wrapper if present
              if (sc.result && typeof sc.result === 'object') {
                return sc.result;
              }
              return sc;
            }
            // Fall back to text content
            const textContent = parsed.result.content.find(
              (c: { type: string }) => c.type === 'text'
            );
            if (textContent?.text) {
              try {
                return JSON.parse(textContent.text);
              } catch {
                return textContent.text;
              }
            }
          }
          return parsed.result;
        }
        if (parsed.error) {
          throw new Error(parsed.error.message || 'Unknown error');
        }
        return parsed;
      } catch (e) {
        if (e instanceof SyntaxError) continue;
        throw e;
      }
    }
  }
  throw new Error('No valid SSE data found in response');
}

/**
 * MCP Client for Neo4j (HTTP POST + JSON-RPC 2.0)
 */
class Neo4jClient {
  private baseURL: string;
  private timeout: number;
  private headers: Record<string, string>;
  private requestId: number;
  private sessionId: string | null = null;
  private initializePromise: Promise<void> | null = null;

  constructor(config: KnowledgeClientConfig) {
    // Use /mcp/ endpoint for Neo4j
    this.baseURL = config.baseURL.endsWith('/mcp') ? config.baseURL : `${config.baseURL}/mcp`;
    this.timeout = config.timeout;
    this.headers = {
      'Content-Type': 'application/json',
      Accept: 'application/json, text/event-stream',
    };
    this.requestId = 1;
  }

  /**
   * Initialize MCP session and get session ID
   */
  private async initializeSession(): Promise<void> {
    if (this.sessionId) return;
    if (this.initializePromise) return this.initializePromise;

    this.initializePromise = (async () => {
      const request = {
        jsonrpc: '2.0',
        id: this.requestId++,
        method: 'initialize',
        params: {
          protocolVersion: '2024-11-05',
          capabilities: {},
          clientInfo: { name: 'madeinoz-knowledge-hook', version: '1.0.0' },
        },
      };

      const response = await fetch(this.baseURL, {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`Failed to initialize session: HTTP ${response.status}`);
      }

      // Get session ID from header
      const sessionId = response.headers.get('Mcp-Session-Id');
      if (!sessionId) {
        throw new Error('Server did not return session ID');
      }
      this.sessionId = sessionId;

      // Consume the SSE response body
      await response.text();

      // Send initialized notification (required by FastMCP HTTP transport)
      const notifyRequest = {
        jsonrpc: '2.0',
        method: 'notifications/initialized',
      };
      await fetch(this.baseURL, {
        method: 'POST',
        headers: {
          ...this.headers,
          'Mcp-Session-Id': this.sessionId,
        },
        body: JSON.stringify(notifyRequest),
      });
    })();

    await this.initializePromise;
  }

  /**
   * Call an MCP tool with JSON-RPC 2.0
   */
  async callTool(
    toolName: string,
    arguments_: Record<string, unknown>
  ): Promise<{
    success: boolean;
    result?: unknown;
    error?: string;
  }> {
    try {
      // Ensure session is initialized
      await this.initializeSession();

      const request = {
        jsonrpc: '2.0',
        id: this.requestId++,
        method: 'tools/call',
        params: {
          name: toolName,
          arguments: arguments_,
        },
      };

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);

      const response = await fetch(this.baseURL, {
        method: 'POST',
        headers: {
          ...this.headers,
          'Mcp-Session-Id': this.sessionId!,
        },
        body: JSON.stringify(request),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        return {
          success: false,
          error: `HTTP ${response.status}: ${response.statusText}`,
        };
      }

      // Parse SSE response
      const text = await response.text();
      const data = parseSSEResponse(text);

      return {
        success: true,
        result: data,
      };
    } catch (error: unknown) {
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          return {
            success: false,
            error: `Request timeout after ${this.timeout}ms`,
          };
        }
        return {
          success: false,
          error: error.message,
        };
      }
      return {
        success: false,
        error: 'Unknown error occurred',
      };
    }
  }

  /**
   * Check MCP server health via /health endpoint
   */
  async testConnection(): Promise<boolean> {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      // Use health endpoint on base URL without /mcp/
      const healthURL = `${this.baseURL.replace(/\/mcp\/?$/, '')}/health`;

      const response = await fetch(healthURL, {
        method: 'GET',
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      return response.ok;
    } catch {
      return false;
    }
  }
}

/**
 * SSE Session for FalkorDB protocol
 */
interface SSESession {
  sessionId: string;
  messagesUrl: string;
  initialized: boolean;
}

/**
 * MCP Client for FalkorDB (SSE GET protocol)
 */
class FalkorDBClient {
  private baseURL: string;
  private timeout: number;
  private headers: Record<string, string>;
  private requestId: number;

  constructor(config: KnowledgeClientConfig) {
    // Use base URL for SSE endpoint
    this.baseURL = config.baseURL;
    this.timeout = config.timeout;
    this.headers = {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    };
    this.requestId = 1;
  }

  /**
   * Get SSE session endpoint from the server
   */
  private async getSSESession(): Promise<SSESession | null> {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 5000);

      const sseUrl = `${this.baseURL}/sse`;
      const response = await fetch(sseUrl, {
        headers: { Accept: 'text/event-stream' },
        signal: controller.signal,
      });

      clearTimeout(timeout);

      if (!response.ok) {
        return null;
      }

      // Read just enough to get the endpoint event
      const reader = response.body?.getReader();
      if (!reader) {
        return null;
      }

      const decoder = new TextDecoder();
      let buffer = '';

      // Read chunks until we get the endpoint
      for (let i = 0; i < 10; i++) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Check if we have a complete event
        if (buffer.includes('\n\n') || buffer.includes('data:')) {
          const { event, data } = parseSSEEvent(buffer);

          if (event === 'endpoint' && data) {
            // Cancel the reader - we have what we need
            reader.cancel().catch(() => {});

            // Extract session ID from the messages URL
            const sessionMatch = data.match(/session_id=([a-f0-9]+)/);
            const sessionId = sessionMatch?.[1] || '';

            return {
              sessionId,
              messagesUrl: `${this.baseURL}${data}`,
              initialized: false,
            };
          }
        }
      }

      reader.cancel().catch(() => {});
      return null;
    } catch {
      return null;
    }
  }

  /**
   * Initialize MCP session with server capabilities
   */
  private async initializeSession(session: SSESession): Promise<boolean> {
    if (session.initialized) {
      return true;
    }

    const initRequest = {
      jsonrpc: '2.0',
      id: this.requestId++,
      method: 'initialize',
      params: {
        protocolVersion: '2024-11-05',
        capabilities: {},
        clientInfo: {
          name: 'madeinoz-knowledge-hook',
          version: '1.0.0',
        },
      },
    };

    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 5000);

      const response = await fetch(session.messagesUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(initRequest),
        signal: controller.signal,
      });

      clearTimeout(timeout);

      if (response.ok || response.status === 202) {
        // Send initialized notification
        const notifyRequest = {
          jsonrpc: '2.0',
          method: 'notifications/initialized',
        };

        await fetch(session.messagesUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(notifyRequest),
        }).catch(() => {});

        session.initialized = true;
        // Pause to let server process initialization
        await new Promise((r) => setTimeout(r, 800));
        return true;
      }

      return false;
    } catch {
      return false;
    }
  }

  /**
   * Send JSON-RPC request via SSE messages endpoint
   */
  private async sendRequest(
    session: SSESession,
    request: object
  ): Promise<{ success: boolean; result?: unknown; error?: string }> {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);

      const response = await fetch(session.messagesUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const text = await response.text().catch(() => 'Unknown error');
        return {
          success: false,
          error: `HTTP ${response.status}: ${text.slice(0, 100)}`,
        };
      }

      // For SSE transport, 202 Accepted means the request was queued
      if (response.status === 202) {
        return { success: true };
      }

      // Try to parse JSON response if available
      const contentType = response.headers.get('content-type');
      if (contentType?.includes('application/json')) {
        const data = await response.json();
        if (data.error) {
          return {
            success: false,
            error: data.error.message || 'Unknown MCP error',
          };
        }
        return { success: true, result: data.result };
      }

      return { success: true };
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      return { success: false, error: message };
    }
  }

  /**
   * Call an MCP tool using SSE protocol
   */
  async callTool(
    toolName: string,
    arguments_: Record<string, unknown>
  ): Promise<{
    success: boolean;
    result?: unknown;
    error?: string;
  }> {
    const session = await this.getSSESession();
    if (!session) {
      return {
        success: false,
        error: 'Failed to establish SSE session',
      };
    }

    const initialized = await this.initializeSession(session);
    if (!initialized) {
      return {
        success: false,
        error: 'Failed to initialize MCP session',
      };
    }

    const request = {
      jsonrpc: '2.0',
      id: this.requestId++,
      method: 'tools/call',
      params: {
        name: toolName,
        arguments: arguments_,
      },
    };

    return await this.sendRequest(session, request);
  }

  /**
   * Check MCP server health via SSE connection
   */
  async testConnection(): Promise<boolean> {
    const session = await this.getSSESession();
    return session !== null;
  }
}

/**
 * Check if MCP server is healthy
 */
export async function checkHealth(
  config: KnowledgeClientConfig = DEFAULT_CONFIG
): Promise<boolean> {
  // Ensure .env file is loaded before checking health
  await ensureEnvLoaded();
  // Re-read config in case env loading changed values
  const effectiveConfig = getDefaultConfig();

  if (isFalkorDB()) {
    const client = new FalkorDBClient(config);
    return await client.testConnection();
  }
  const client = new Neo4jClient(config);
  return await client.testConnection();
}

/**
 * Add an episode to the knowledge graph with retry logic
 */
export async function addEpisode(
  params: AddEpisodeParams,
  config: KnowledgeClientConfig = DEFAULT_CONFIG
): Promise<AddEpisodeResult> {
  // Ensure .env file is loaded before adding episode
  await ensureEnvLoaded();
  // Server-side sanitization handles Lucene escaping for FalkorDB
  const requestArgs = {
    name: params.name.slice(0, 200),
    episode_body: params.episode_body.slice(0, 5000),
    source: params.source || 'text',
    source_description: params.source_description || '',
    ...(params.group_id && { group_id: params.group_id }),
    ...(params.reference_timestamp && { reference_timestamp: params.reference_timestamp }),
  };

  // Retry loop with exponential backoff
  for (let attempt = 0; attempt < config.retries; attempt++) {
    try {
      let result: { success: boolean; result?: unknown; error?: string };

      if (isFalkorDB()) {
        // Use SSE protocol for FalkorDB
        const client = new FalkorDBClient(config);
        result = await client.callTool('add_memory', requestArgs);
      } else {
        // Use HTTP POST protocol for Neo4j
        const client = new Neo4jClient(config);
        result = await client.callTool('add_memory', requestArgs);
      }

      if (result.success) {
        // Extract UUID from result if available
        let uuid: string | undefined;
        if (typeof result.result === 'object' && result.result !== null) {
          const r = result.result as Record<string, unknown>;
          uuid = (r.uuid || r.episode_uuid || r.id) as string | undefined;
        }
        return { success: true, uuid };
      }

      // Check if retryable
      if (attempt < config.retries - 1) {
        const isRetryable =
          result.error?.includes('timeout') ||
          result.error?.includes('ECONNREFUSED') ||
          result.error?.includes('abort') ||
          result.error?.includes('ECONNRESET') ||
          result.error?.includes('ETIMEDOUT');

        if (isRetryable) {
          const backoff = 500 * 2 ** attempt;
          await new Promise((r) => setTimeout(r, backoff));
          continue;
        }
      }

      return { success: false, error: result.error };
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Unknown error';

      if (attempt < config.retries - 1) {
        const backoff = 500 * 2 ** attempt;
        await new Promise((r) => setTimeout(r, backoff));
        continue;
      }

      return { success: false, error: message };
    }
  }

  return { success: false, error: 'Max retries exceeded' };
}

/**
 * Get current configuration
 */
export function getConfig(): KnowledgeClientConfig {
  return { ...DEFAULT_CONFIG };
}
