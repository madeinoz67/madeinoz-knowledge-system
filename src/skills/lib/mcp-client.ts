/**
 * MCP Client Library
 *
 * HTTP client for communicating with the Graphiti MCP server.
 * Handles JSON-RPC 2.0 requests for all MCP tools.
 *
 * NOTE: Lucene sanitization is now handled server-side by the Python patch
 * (falkordb_lucene.py). The TypeScript client passes values directly to the server.
 */

// Import profile loading function for connection profiles
import { loadProfileWithOverrides } from './connection-profile.js';

/**
 * MCP tool names (Graphiti MCP server)
 *
 * Note: The Graphiti MCP server tools:
 * - add_memory: Add episodes to the knowledge graph
 * - search_nodes: Search for entities/nodes
 * - search_memory_facts: Search for relationships/facts
 * - get_episodes: Retrieve recent episodes
 * - delete_episode, delete_entity_edge: Deletion operations
 * - clear_graph: Clear all data
 * - get_status: Server health check
 *
 * TypeScript methods use Graphiti-native terminology (Episode, Node, Fact)
 * while calling the actual MCP tool names.
 */
export const MCP_TOOLS = {
  // Knowledge capture (adds an "episode" to memory)
  ADD_EPISODE: 'add_memory',
  // Entity search (searches "nodes")
  SEARCH_NODES: 'search_nodes',
  // Relationship search (searches "facts" in memory)
  SEARCH_FACTS: 'search_memory_facts',
  // Episode retrieval
  GET_EPISODES: 'get_episodes',
  // System operations
  GET_STATUS: 'get_status',
  CLEAR_GRAPH: 'clear_graph',
  DELETE_EPISODE: 'delete_episode',
  DELETE_ENTITY_EDGE: 'delete_entity_edge',
  GET_ENTITY_EDGE: 'get_entity_edge',
  // Feature 009: Memory decay scoring
  GET_KNOWLEDGE_HEALTH: 'get_knowledge_health',
  RUN_DECAY_MAINTENANCE: 'run_decay_maintenance',
  CLASSIFY_MEMORY: 'classify_memory',
  RECOVER_SOFT_DELETED: 'recover_soft_deleted',
} as const;

/**
 * MCP tool parameters
 */
export interface AddEpisodeParams {
  name: string;
  episode_body: string;
  source?: string;
  reference_timestamp?: string;
  source_description?: string;
}

export interface SearchNodesParams {
  query: string;
  /** Maximum number of nodes to return (maps to max_nodes on server) */
  limit?: number;
  group_ids?: string[];
  /** Filter by entity type names (e.g., ["Preference", "Procedure"]) */
  entity_types?: string[];
  /** Return nodes created after this date (ISO 8601 or relative: "today", "7d", "1 week ago") */
  since?: string;
  /** Return nodes created before this date (ISO 8601 or relative) */
  until?: string;
}

export interface SearchFactsParams {
  query: string;
  limit?: number;
  group_ids?: string[];
  max_facts?: number;
  /** Filter by entity type (e.g., "Preference", "Procedure", "Learning", "Research", "Decision") */
  entity?: string;
  /** Center the search on a specific entity UUID */
  center_node_uuid?: string;
  /** Return facts created after this date (ISO 8601 or relative: "today", "7d", "1 week ago") */
  since?: string;
  /** Return facts created before this date (ISO 8601 or relative) */
  until?: string;
}

export interface GetEpisodesParams {
  /** Maximum number of episodes to return (maps to max_episodes on server) */
  limit?: number;
  /** Single group ID (will be converted to group_ids array) */
  group_id?: string;
  /** Multiple group IDs */
  group_ids?: string[];
}

export type GetStatusParams = Record<string, never>;

export type ClearGraphParams = Record<string, never>;

export interface DeleteEpisodeParams {
  uuid: string;
}

export interface DeleteEntityEdgeParams {
  uuid: string;
}

export interface GetEntityEdgeParams {
  uuid: string;
}

// Feature 009: Memory decay scoring parameters
export interface GetKnowledgeHealthParams {
  group_id?: string;
}

export interface RunDecayMaintenanceParams {
  dry_run?: boolean;
}

export interface ClassifyMemoryParams {
  content: string;
  source_description?: string;
}

export interface RecoverSoftDeletedParams {
  uuid: string;
}

/**
 * JSON-RPC 2.0 request
 */
export interface JSONRPCRequest {
  jsonrpc: '2.0';
  id: number | string;
  method: string;
  params: {
    name: string;
    arguments: Record<string, unknown>;
  };
}

/**
 * JSON-RPC 2.0 response
 */
export interface JSONRPCResponse {
  jsonrpc: '2.0';
  id: number | string;
  result?: unknown;
  error?: {
    code: number;
    message: string;
    data?: unknown;
  };
}

/**
 * MCP client response
 */
export interface MCPClientResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  code?: number;
}

/**
 * TLS/SSL configuration for HTTPS connections
 */
export interface TLSConfig {
  /** Enable certificate verification (default: true) */
  verify?: boolean;
  /** Path to CA certificate file (PEM format) */
  ca?: string;
  /** Path to client certificate file (PEM format) */
  cert?: string;
  /** Path to client private key file (PEM format) */
  key?: string;
  /** Minimum TLS protocol version (default: TLSv1.2) */
  minVersion?: 'TLSv1.2' | 'TLSv1.3';
}

/**
 * MCP Client configuration
 */
export interface MCPClientConfig {
  /** Base URL for MCP server (deprecated: use protocol+host+port+basePath) */
  baseURL?: string;
  /** Protocol: http or https (default: http) */
  protocol?: 'http' | 'https';
  /** Hostname or IP address (default: localhost) */
  host?: string;
  /** TCP port (default: 8001) */
  port?: number;
  /** URL path prefix (default: /mcp) */
  basePath?: string;
  /** Request timeout in milliseconds (default: 30000) */
  timeout?: number;
  /** Custom headers */
  headers?: Record<string, string>;
  /** TLS configuration (required if protocol=https) */
  tls?: TLSConfig;
  /** Connection profile name (loads from file) */
  profile?: string;
}

/**
 * Default timeout for requests
 */
const DEFAULT_TIMEOUT = 30000; // 30 seconds

/**
 * Simple LRU Cache for search results
 */
interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

class LRUCache<T> {
  private cache: Map<string, CacheEntry<T>>;
  private maxSize: number;
  private ttlMs: number;

  constructor(maxSize = 100, ttlMs: number = 5 * 60 * 1000) {
    this.cache = new Map();
    this.maxSize = maxSize;
    this.ttlMs = ttlMs;
  }

  get(key: string): T | undefined {
    const entry = this.cache.get(key);
    if (!entry) return undefined;

    // Check TTL
    if (Date.now() - entry.timestamp > this.ttlMs) {
      this.cache.delete(key);
      return undefined;
    }

    // Move to end (most recently used)
    this.cache.delete(key);
    this.cache.set(key, entry);
    return entry.data;
  }

  set(key: string, data: T): void {
    // Evict oldest if at capacity
    if (this.cache.size >= this.maxSize) {
      const oldestKey = this.cache.keys().next().value;
      if (oldestKey) this.cache.delete(oldestKey);
    }

    this.cache.set(key, { data, timestamp: Date.now() });
  }

  clear(): void {
    this.cache.clear();
  }

  size(): number {
    return this.cache.size;
  }
}

/**
 * Extended MCP Client configuration with caching options
 */
export interface MCPClientConfigExtended extends MCPClientConfig {
  enableCache?: boolean;
  cacheMaxSize?: number;
  cacheTtlMs?: number;
}

/**
 * Create HTTPS agent with custom TLS options for Bun/Node.js fetch
 *
 * T021 [P] [US2]: Create HTTPS agent factory with custom TLS options
 * T022 [US2]: Implement TLS certificate verification logic
 */
function createHTTPSOptions(tls?: TLSConfig): RequestInit {
  const options: RequestInit = {};

  if (!tls) {
    return options;
  }

  // For Bun, we use a different approach with custom agent
  // Bun's fetch doesn't directly support https.Agent, but we can pass
  // TLS configuration through the request context

  // T022 [US2]: Implement TLS certificate verification logic
  // Default is to verify certificates (secure by default)
  const verify = tls.verify !== false;

  // For development/testing: allow self-signed certificates
  if (!verify) {
    // Bun doesn't have a direct way to disable verification in fetch
    // This is a known limitation - users should use valid certificates
    // or configure their system to trust the self-signed certificate
    console.warn('TLS certificate verification is DISABLED. This is not secure for production.');
  }

  // T024 [US2]: Add MADEINOZ_KNOWLEDGE_TLS_CA environment variable support
  // T023 [US2]: Add MADEINOZ_KNOWLEDGE_TLS_VERIFY environment variable support
  // Note: Bun's fetch API doesn't directly support custom CA certificates
  // Users need to configure system-level certificate trust or use a proxy
  if (tls.ca) {
    console.warn(`Custom CA certificate specified: ${tls.ca}`);
    console.warn('Bun fetch requires system-level certificate configuration. Use NODE_OPTIONS=--use-openssl-ca or configure certificate trust at OS level.');
  }

  // Client certificate authentication (mTLS)
  if (tls.cert && tls.key) {
    console.warn(`Client certificates specified: cert=${tls.cert}, key=${tls.key}`);
    console.warn('Bun fetch does not directly support client certificates. Consider using Node.js for mTLS support.');
  }

  return options;
}

/**
 * MCP Client class with session management and optional response caching
 */
export class MCPClient {
  private baseURL: string;
  private timeout: number;
  private headers: Record<string, string>;
  private requestId: number;
  private cache: LRUCache<unknown> | null;
  private sessionId: string | null = null;
  private initializePromise: Promise<void> | null = null;
  private tlsConfig: TLSConfig | undefined;

  constructor(config: MCPClientConfigExtended = {}) {
    // Construct baseURL from protocol+host+port+basePath if baseURL not provided
    if (config.baseURL) {
      // Backward compatibility: use explicit baseURL
      this.baseURL = config.baseURL;
    } else {
      // Construct from individual components
      const protocol = config.protocol || 'http';
      const host = config.host || 'localhost';
      const port = config.port || 8001;
      const basePath = config.basePath || '/mcp';
      this.baseURL = `${protocol}://${host}:${port}${basePath}`;
    }

    this.timeout = config.timeout || DEFAULT_TIMEOUT;
    this.headers = {
      'Content-Type': 'application/json',
      Accept: 'application/json, text/event-stream',
      ...config.headers,
    };
    this.requestId = 1;

    // Store TLS configuration for HTTPS connections
    this.tlsConfig = config.tls;

    // Log TLS configuration for HTTPS URLs
    if (this.baseURL.startsWith('https://')) {
      const verify = this.tlsConfig?.verify !== false;
      const ca = this.tlsConfig?.ca ? ` (CA: ${this.tlsConfig.ca})` : '';
      const cert = this.tlsConfig?.cert ? ` (cert: ${this.tlsConfig.cert})` : '';
      console.log(`[MCPClient] HTTPS mode enabled - verify: ${verify}${ca}${cert}`);
    }

    // Initialize cache if enabled (default: enabled for search operations)
    if (config.enableCache !== false) {
      this.cache = new LRUCache<unknown>(
        config.cacheMaxSize || 100,
        config.cacheTtlMs || 5 * 60 * 1000 // 5 minutes default
      );
    } else {
      this.cache = null;
    }
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
          clientInfo: { name: 'mcp-wrapper', version: '1.0.0' },
        },
      };

      // T021 [P] [US2]: Apply TLS configuration for HTTPS requests
      const tlsOptions = createHTTPSOptions(this.tlsConfig);

      const response = await fetch(this.baseURL, {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify(request),
        ...tlsOptions,
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
   * Parse SSE response to extract JSON-RPC result
   */
  private parseSSEResponse(text: string): unknown {
    // SSE format: "event: message\ndata: {...}\n\n"
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
                  const textParsed = JSON.parse(textContent.text);
                  // Unwrap Graphiti's result wrapper if present
                  if (textParsed.result && typeof textParsed.result === 'object') {
                    return textParsed.result;
                  }
                  return textParsed;
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
   * Generate cache key for a tool call
   */
  private getCacheKey(toolName: string, args: Record<string, unknown>): string {
    return `${toolName}:${JSON.stringify(args)}`;
  }

  /**
   * Clear the response cache
   */
  clearCache(): void {
    this.cache?.clear();
  }

  /**
   * Get cache statistics
   */
  getCacheStats(): { enabled: boolean; size: number } {
    return {
      enabled: this.cache !== null,
      size: this.cache?.size() || 0,
    };
  }

  /**
   * Call an MCP tool
   */
  async callTool<T = unknown>(
    toolName: string,
    arguments_: Record<string, unknown>
  ): Promise<MCPClientResponse<T>> {
    try {
      // Ensure session is initialized
      await this.initializeSession();

      const request: JSONRPCRequest = {
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

      // T021 [P] [US2]: Create HTTPS agent factory with custom TLS options
      // Apply TLS configuration for HTTPS requests
      const tlsOptions = createHTTPSOptions(this.tlsConfig);

      const response = await fetch(this.baseURL, {
        method: 'POST',
        headers: {
          ...this.headers,
          'Mcp-Session-Id': this.sessionId!,
        },
        body: JSON.stringify(request),
        signal: controller.signal,
        ...tlsOptions,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        return {
          success: false,
          error: `HTTP ${response.status}: ${response.statusText}`,
          code: response.status,
        };
      }

      // Parse SSE response
      const text = await response.text();
      const data = this.parseSSEResponse(text);

      return {
        success: true,
        data: data as T,
      };
    } catch (error: unknown) {
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          return {
            success: false,
            error: `Request timeout after ${this.timeout}ms`,
          };
        }

        // T026 [US2]: Add TLS certificate error handling with clear messages
        const errorMsg = error.message.toLowerCase();
        if (
          errorMsg.includes('certificate') ||
          errorMsg.includes('tls') ||
          errorMsg.includes('ssl') ||
          errorMsg.includes('handshake') ||
          errorMsg.includes('certificate verify failed')
        ) {
          const suggestions: string[] = [];
          if (this.tlsConfig?.ca) {
            suggestions.push(`Verify CA certificate path exists: ${this.tlsConfig.ca}`);
          }
          if (this.tlsConfig?.verify === false) {
            suggestions.push('TLS verification is disabled but certificate error still occurred');
          } else {
            suggestions.push('Try setting MADEINOZ_KNOWLEDGE_TLS_VERIFY=false for self-signed certificates (not recommended for production)');
            suggestions.push('Ensure the server certificate is valid and trusted');
          }
          return {
            success: false,
            error: `TLS Certificate Error: ${error.message}${suggestions.length > 0 ? '\nSuggestions:\n  - ' + suggestions.join('\n  - ') : ''}`,
          };
        }

        // Host unreachable errors
        if (
          errorMsg.includes('econnrefused') ||
          errorMsg.includes('connection refused') ||
          errorMsg.includes('econnreset')
        ) {
          return {
            success: false,
            error: `Connection Error: Unable to reach server at ${this.baseURL}\n  - Verify the server is running\n  - Check firewall settings\n  - Verify host and port are correct`,
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
   * Add an episode to the knowledge graph
   */
  async addEpisode(params: AddEpisodeParams): Promise<MCPClientResponse<{ uuid: string }>> {
    return await this.callTool<{ uuid: string }>(MCP_TOOLS.ADD_EPISODE, params as unknown as Record<string, unknown>);
  }

  /**
   * Search for nodes (entities) in the knowledge graph
   * Results are cached for repeated queries
   */
  async searchNodes(params: SearchNodesParams): Promise<MCPClientResponse<unknown[]>> {
    // Build server params with correct field names
    // Sanitization is handled server-side by falkordb_lucene.py patch
    const serverParams: Record<string, unknown> = {
      query: params.query,
    };
    if (params.limit !== undefined) {
      serverParams.max_nodes = params.limit;
    }
    if (params.group_ids) {
      serverParams.group_ids = params.group_ids;
    }
    if (params.entity_types) {
      serverParams.entity_types = params.entity_types;
    }
    // Temporal filters (Madeinoz Patch)
    if (params.since) {
      serverParams.created_after = params.since;
    }
    if (params.until) {
      serverParams.created_before = params.until;
    }

    // Check cache first
    if (this.cache) {
      const cacheKey = this.getCacheKey(MCP_TOOLS.SEARCH_NODES, serverParams);
      const cached = this.cache.get(cacheKey);
      if (cached) {
        return { success: true, data: cached as unknown[] };
      }

      // Fetch and cache
      const result = await this.callTool<unknown[]>(MCP_TOOLS.SEARCH_NODES, serverParams);
      if (result.success && result.data) {
        this.cache.set(cacheKey, result.data);
      }
      return result;
    }

    return await this.callTool<unknown[]>(MCP_TOOLS.SEARCH_NODES, serverParams);
  }

  /**
   * Search for facts (relationships) in the knowledge graph
   * Results are cached for repeated queries
   *
   * NOTE: Sanitization is handled server-side by falkordb_lucene.py patch
   */
  async searchFacts(params: SearchFactsParams): Promise<MCPClientResponse<unknown[]>> {
    // Server-side sanitization handles Lucene escaping
    const serverParams: Record<string, unknown> = {
      query: params.query,
    };
    if (params.max_facts !== undefined) {
      serverParams.max_facts = params.max_facts;
    }
    if (params.group_ids) {
      serverParams.group_ids = params.group_ids;
    }
    if (params.center_node_uuid) {
      serverParams.center_node_uuid = params.center_node_uuid;
    }
    // Temporal filters (Madeinoz Patch)
    if (params.since) {
      serverParams.created_after = params.since;
    }
    if (params.until) {
      serverParams.created_before = params.until;
    }

    // Check cache first
    if (this.cache) {
      const cacheKey = this.getCacheKey(MCP_TOOLS.SEARCH_FACTS, serverParams);
      const cached = this.cache.get(cacheKey);
      if (cached) {
        return { success: true, data: cached as unknown[] };
      }

      // Fetch and cache
      const result = await this.callTool<unknown[]>(MCP_TOOLS.SEARCH_FACTS, serverParams);
      if (result.success && result.data) {
        this.cache.set(cacheKey, result.data);
      }
      return result;
    }

    return await this.callTool<unknown[]>(MCP_TOOLS.SEARCH_FACTS, serverParams);
  }

  /**
   * Get recent episodes from the knowledge graph
   *
   * NOTE: Sanitization is handled server-side by falkordb_lucene.py patch
   */
  async getEpisodes(params: GetEpisodesParams = {}): Promise<MCPClientResponse<unknown[]>> {
    // Build server params with correct field names
    // Server-side sanitization handles Lucene escaping
    const serverParams: Record<string, unknown> = {};
    if (params.limit !== undefined) {
      serverParams.max_episodes = params.limit;
    }
    // Support both group_id (single) and group_ids (multiple)
    if (params.group_ids) {
      serverParams.group_ids = params.group_ids;
    } else if (params.group_id) {
      // Server-side sanitization handles Lucene escaping
      serverParams.group_ids = [params.group_id];
    }
    return await this.callTool<unknown[]>(MCP_TOOLS.GET_EPISODES, serverParams);
  }

  /**
   * Get the status of the knowledge graph
   */
  async getStatus(): Promise<
    MCPClientResponse<{
      entity_count: number;
      episode_count: number;
      last_updated: string;
    }>
  > {
    return await this.callTool<{
      entity_count: number;
      episode_count: number;
      last_updated: string;
    }>(MCP_TOOLS.GET_STATUS, {});
  }

  /**
   * Clear all data from the knowledge graph
   */
  async clearGraph(): Promise<MCPClientResponse<{ success: boolean }>> {
    return await this.callTool<{ success: boolean }>(MCP_TOOLS.CLEAR_GRAPH, {});
  }

  /**
   * Delete an episode from the knowledge graph
   */
  async deleteEpisode(
    params: DeleteEpisodeParams
  ): Promise<MCPClientResponse<{ success: boolean }>> {
    return await this.callTool<{ success: boolean }>(MCP_TOOLS.DELETE_EPISODE, params as unknown as Record<string, unknown>);
  }

  /**
   * Delete an entity edge from the knowledge graph
   */
  async deleteEntityEdge(
    params: DeleteEntityEdgeParams
  ): Promise<MCPClientResponse<{ success: boolean }>> {
    return await this.callTool<{ success: boolean }>(MCP_TOOLS.DELETE_ENTITY_EDGE, params as unknown as Record<string, unknown>);
  }

  /**
   * Get an entity edge from the knowledge graph
   */
  async getEntityEdge(params: GetEntityEdgeParams): Promise<MCPClientResponse<unknown>> {
    return await this.callTool<unknown>(MCP_TOOLS.GET_ENTITY_EDGE, params as unknown as Record<string, unknown>);
  }

  /**
   * Feature 009: Get knowledge graph health metrics
   */
  async getKnowledgeHealth(
    params: GetKnowledgeHealthParams = {}
  ): Promise<MCPClientResponse<unknown>> {
    const serverParams: Record<string, unknown> = {};
    if (params.group_id) {
      serverParams.group_id = params.group_id;
    }
    return await this.callTool<unknown>(MCP_TOOLS.GET_KNOWLEDGE_HEALTH, serverParams);
  }

  /**
   * Feature 009: Run decay maintenance cycle
   */
  async runDecayMaintenance(
    params: RunDecayMaintenanceParams = {}
  ): Promise<MCPClientResponse<unknown>> {
    const serverParams: Record<string, unknown> = {
      dry_run: params.dry_run ?? false,
    };
    return await this.callTool<unknown>(MCP_TOOLS.RUN_DECAY_MAINTENANCE, serverParams);
  }

  /**
   * Feature 009: Classify memory importance and stability
   */
  async classifyMemory(
    params: ClassifyMemoryParams
  ): Promise<MCPClientResponse<unknown>> {
    const serverParams: Record<string, unknown> = {
      content: params.content,
    };
    if (params.source_description) {
      serverParams.source_description = params.source_description;
    }
    return await this.callTool<unknown>(MCP_TOOLS.CLASSIFY_MEMORY, serverParams);
  }

  /**
   * Feature 009: Recover soft-deleted memory
   */
  async recoverSoftDeleted(
    params: RecoverSoftDeletedParams
  ): Promise<MCPClientResponse<unknown>> {
    return await this.callTool<unknown>(MCP_TOOLS.RECOVER_SOFT_DELETED, {
      uuid: params.uuid,
    });
  }

  /**
   * Test the connection to the MCP server
   */
  async testConnection(): Promise<MCPClientResponse<{ status: string }>> {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout for health check

      // T021 [P] [US2]: Apply TLS configuration for HTTPS requests
      const tlsOptions = createHTTPSOptions(this.tlsConfig);

      const response = await fetch(`${this.baseURL.replace(/\/mcp\/?$/, '')}/health`, {
        method: 'GET',
        signal: controller.signal,
        ...tlsOptions,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        return {
          success: false,
          error: `HTTP ${response.status}: ${response.statusText}`,
        };
      }

      const data = await response.json();
      return {
        success: true,
        data: data as { status: string },
      };
    } catch (error: unknown) {
      if (error instanceof Error) {
        // T018 [US1]: Implement connection error handling with actionable messages
        // T026 [US2]: Add TLS certificate error handling with clear messages
        const errorMsg = error.message.toLowerCase();
        const suggestions: string[] = [];

        // TLS/SSL certificate errors
        if (
          errorMsg.includes('certificate') ||
          errorMsg.includes('tls') ||
          errorMsg.includes('ssl') ||
          errorMsg.includes('handshake')
        ) {
          suggestions.push('Check that the server certificate is valid');
          suggestions.push('Try MADEINOZ_KNOWLEDGE_TLS_VERIFY=false for self-signed certificates (not recommended for production)');
          if (this.tlsConfig?.ca) {
            suggestions.push(`Verify CA certificate path exists: ${this.tlsConfig.ca}`);
          }
          return {
            success: false,
            error: `TLS Certificate Error: ${error.message}\nSuggestions:\n  - ${suggestions.join('\n  - ')}`,
          };
        }

        // Host unreachable / DNS resolution errors
        if (
          errorMsg.includes('econnrefused') ||
          errorMsg.includes('connection refused') ||
          errorMsg.includes('econnreset') ||
          errorMsg.includes('enotfound') ||
          errorMsg.includes('getaddrinfo')
        ) {
          suggestions.push('Verify the MCP server is running (bun run server status)');
          suggestions.push('Check firewall settings allow connections');
          suggestions.push('Verify the host and port are correct');
          if (this.baseURL.includes('localhost') || this.baseURL.includes('127.0.0.1')) {
            suggestions.push('If running in Docker, ensure ports are properly mapped');
          }
          return {
            success: false,
            error: `Connection Error: Unable to reach server at ${this.baseURL}\nSuggestions:\n  - ${suggestions.join('\n  - ')}`,
          };
        }

        // Network timeout errors
        if (
          errorMsg.includes('timeout') ||
          errorMsg.includes('timed out') ||
          error.name === 'AbortError'
        ) {
          suggestions.push('The request took too long to complete');
          suggestions.push('Check if the server is under heavy load');
          suggestions.push('Try increasing MADEINOZ_KNOWLEDGE_TIMEOUT (currently ${this.timeout}ms)');
          return {
            success: false,
            error: `Connection Timeout: ${error.message}\nSuggestions:\n  - ${suggestions.join('\n  - ')}`,
          };
        }

        // Invalid protocol errors
        if (errorMsg.includes('invalid protocol') || errorMsg.includes('unsupported protocol')) {
          suggestions.push('Check MADEINOZ_KNOWLEDGE_PROTOCOL is "http" or "https"');
          return {
            success: false,
            error: `Protocol Error: ${error.message}\nSuggestions:\n  - ${suggestions.join('\n  - ')}`,
          };
        }

        // Generic error with message
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
}

/**
 * Create an MCP client instance with configuration from environment variables or profiles
 *
 * T015 [US1]: Update createMCPClient() to accept extended config
 * T016 [US1]: Add environment variable parsing
 * T023 [US2]: Add MADEINOZ_KNOWLEDGE_TLS_VERIFY environment variable support
 * T024 [US2]: Add MADEINOZ_KNOWLEDGE_TLS_CA environment variable support
 *
 * Priority order (highest to lowest):
 * 1. Explicit config parameter
 * 2. Individual environment variables (MADEINOZ_KNOWLEDGE_HOST, etc.)
 * 3. Profile from MADEINOZ_KNOWLEDGE_PROFILE environment variable
 * 4. Default profile from YAML file
 * 5. Code defaults (localhost:8001, http)
 *
 * Environment variables (MADEINOZ_KNOWLEDGE_* prefix):
 *   - MADEINOZ_KNOWLEDGE_PROFILE: Profile name to load from YAML file
 *   - MADEINOZ_KNOWLEDGE_PROTOCOL: http or https (default: http)
 *   - MADEINOZ_KNOWLEDGE_HOST: hostname or IP address (default: localhost)
 *   - MADEINOZ_KNOWLEDGE_PORT: TCP port (default: 8001)
 *   - MADEINOZ_KNOWLEDGE_BASE_PATH: URL path prefix (default: /mcp)
 *   - MADEINOZ_KNOWLEDGE_TLS_VERIFY: true or false (default: true)
 *   - MADEINOZ_KNOWLEDGE_TLS_CA: Path to CA certificate file
 *   - MADEINOZ_KNOWLEDGE_TLS_CERT: Path to client certificate file
 *   - MADEINOZ_KNOWLEDGE_TLS_KEY: Path to client private key file
 */
export function createMCPClient(config?: MCPClientConfig): MCPClient {
  // If explicit config provided with all necessary fields, use it directly
  if (config && (config.baseURL || (config.host && config.port))) {
    return new MCPClient(config);
  }

  // Build extended config from environment variables
  const envConfig: MCPClientConfigExtended = {
    protocol: (process.env.MADEINOZ_KNOWLEDGE_PROTOCOL as 'http' | 'https') || undefined,
    host: process.env.MADEINOZ_KNOWLEDGE_HOST || undefined,
    port: process.env.MADEINOZ_KNOWLEDGE_PORT ? Number.parseInt(process.env.MADEINOZ_KNOWLEDGE_PORT, 10) : undefined,
    basePath: process.env.MADEINOZ_KNOWLEDGE_BASE_PATH || undefined,
    tls: {
      // T023 [US2]: Add MADEINOZ_KNOWLEDGE_TLS_VERIFY environment variable support
      verify: process.env.MADEINOZ_KNOWLEDGE_TLS_VERIFY ? process.env.MADEINOZ_KNOWLEDGE_TLS_VERIFY !== 'false' : undefined,
      // T024 [US2]: Add MADEINOZ_KNOWLEDGE_TLS_CA environment variable support
      ca: process.env.MADEINOZ_KNOWLEDGE_TLS_CA || undefined,
      cert: process.env.MADEINOZ_KNOWLEDGE_TLS_CERT || undefined,
      key: process.env.MADEINOZ_KNOWLEDGE_TLS_KEY || undefined,
    },
    ...config,
  };

  // Remove undefined TLS config to avoid overriding defaults
  if (!envConfig.tls?.ca && !envConfig.tls?.cert && !envConfig.tls?.key && envConfig.tls?.verify === undefined) {
    delete envConfig.tls;
  }

  // If no explicit config and no environment variables, try loading from profile
  if (!config && !process.env.MADEINOZ_KNOWLEDGE_HOST && !process.env.MADEINOZ_KNOWLEDGE_PORT) {
    try {
      // Load profile from config file (imported at top of file)
      const profileConfig = loadProfileWithOverrides();

      // Convert profile config to MCPClientConfig format
      const profileBasedConfig: MCPClientConfigExtended = {
        protocol: profileConfig.protocol as 'http' | 'https',
        host: profileConfig.host,
        port: profileConfig.port,
        basePath: profileConfig.basePath,
        timeout: profileConfig.timeout,
        tls: profileConfig.tls,
        profile: profileConfig.name,
      };

      // Profile settings as base, environment variables override (only defined values)
      // Note: envConfig must come first so undefined values don't override profile values
      const finalConfig = { ...envConfig, ...profileBasedConfig };
      return new MCPClient(finalConfig);
    } catch (_error) {
      // If profile loading fails, fall back to environment config or defaults
      // This ensures backward compatibility
    }
  }

  return new MCPClient(envConfig);
}

/**
 * Quick health check function
 */
export async function checkHealth(baseURL?: string): Promise<boolean> {
  const client = new MCPClient({ baseURL });
  const result = await client.testConnection();
  return result.success;
}
