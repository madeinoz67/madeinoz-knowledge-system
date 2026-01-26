/**
 * MCP Client Library
 *
 * HTTP client for communicating with the Graphiti MCP server.
 * Handles JSON-RPC 2.0 requests for all MCP tools.
 *
 * NOTE: Lucene sanitization is now handled server-side by the Python patch
 * (falkordb_lucene.py). The TypeScript client passes values directly to the server.
 */

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
 * MCP Client configuration
 */
export interface MCPClientConfig {
  baseURL?: string;
  timeout?: number;
  headers?: Record<string, string>;
}

/**
 * Default MCP server URL
 */
const DEFAULT_BASE_URL = 'http://localhost:8000/mcp';
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

  constructor(config: MCPClientConfigExtended = {}) {
    this.baseURL = config.baseURL || DEFAULT_BASE_URL;
    this.timeout = config.timeout || DEFAULT_TIMEOUT;
    this.headers = {
      'Content-Type': 'application/json',
      Accept: 'application/json, text/event-stream',
      ...config.headers,
    };
    this.requestId = 1;

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
   * Test the connection to the MCP server
   */
  async testConnection(): Promise<MCPClientResponse<{ status: string }>> {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout for health check

      const response = await fetch(`${this.baseURL.replace(/\/mcp\/?$/, '')}/health`, {
        method: 'GET',
        signal: controller.signal,
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
 * Create an MCP client instance
 */
export function createMCPClient(config?: MCPClientConfig): MCPClient {
  return new MCPClient(config);
}

/**
 * Quick health check function
 */
export async function checkHealth(baseURL?: string): Promise<boolean> {
  const client = new MCPClient({ baseURL });
  const result = await client.testConnection();
  return result.success;
}
