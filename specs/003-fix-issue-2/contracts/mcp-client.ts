/**
 * MCP Client Contract
 *
 * Interface specification for the Graphiti MCP client used by sync hooks.
 * This contract defines the required behavior for the HTTP POST + JSON-RPC 2.0
 * protocol implementation.
 *
 * Reference Implementation: src/server/lib/mcp-client.ts
 */

/**
 * Database backend types supported by the knowledge graph
 */
export type DatabaseType = 'neo4j' | 'falkorodb';

/**
 * Episode parameters for add_memory tool
 */
export interface AddEpisodeParams {
  /** Episode name with capture type prefix (max 200 chars) */
  name: string;
  /** Episode body content (max 5000 chars) */
  episode_body: string;
  /** Source type (e.g., "text", "message") */
  source?: string;
  /** Metadata description string */
  source_description?: string;
  /** ISO timestamp for episode reference */
  reference_timestamp?: string;
  /** Knowledge domain for organization (e.g., "learning", "research") */
  group_id?: string;
}

/**
 * Result from addEpisode operation
 */
export interface AddEpisodeResult {
  /** Whether the operation succeeded */
  success: boolean;
  /** UUID assigned by server (present if successful) */
  uuid?: string;
  /** Error message (present if failed) */
  error?: string;
}

/**
 * Configuration for MCP client
 */
export interface MCPClientConfig {
  /** Base URL for MCP server (default: http://localhost:8000) */
  baseURL?: string;
  /** Request timeout in milliseconds (default: 15000) */
  timeout?: number;
  /** Maximum retry attempts (default: 3) */
  retries?: number;
  /** Enable response caching (default: true) */
  enableCache?: boolean;
  /** Cache max size (default: 100 entries) */
  cacheMaxSize?: number;
  /** Cache TTL in milliseconds (default: 5 minutes) */
  cacheTtlMs?: number;
}

/**
 * Health check result
 */
export interface HealthCheckResult {
  /** Whether server is healthy and reachable */
  healthy: boolean;
  /** Error message if unhealthy */
  error?: string;
}

/**
 * Sync statistics for logging
 */
export interface SyncStats {
  /** Number of files successfully synced */
  synced: number;
  /** Number of files that failed to sync */
  failed: number;
  /** Number of files skipped (duplicates or errors) */
  skipped: number;
}

/**
 * MCP Client Interface
 *
 * This interface defines the contract for the MCP client implementation.
 * The client handles:
 * - Session initialization with JSON-RPC 2.0
 * - HTTP POST requests to /mcp/ endpoint
 * - SSE response body parsing
 * - Database type detection for query sanitization
 * - Retry logic with exponential backoff
 */
export interface IMCPClient {
  /**
   * Initialize MCP session
   *
   * Sends JSON-RPC 2.0 initialize request to establish session.
   * Extracts Mcp-Session-Id from response headers for subsequent requests.
   *
   * @throws Error if server does not return session ID
   */
  initialize(): Promise<void>;

  /**
   * Check MCP server health
   *
   * Sends GET request to /health endpoint.
   *
   * @returns Health check result with status
   */
  checkHealth(): Promise<HealthCheckResult>;

  /**
   * Add an episode to the knowledge graph
   *
   * Sends tools/call request with add_memory parameters.
   * Retries on transient failures with exponential backoff.
   *
   * @param params - Episode data
   * @param config - Optional client configuration override
   * @returns AddEpisodeResult with UUID if successful
   */
  addEpisode(
    params: AddEpisodeParams,
    config?: MCPClientConfig
  ): Promise<AddEpisodeResult>;

  /**
   * Clear the response cache (if caching is enabled)
   */
  clearCache(): void;

  /**
   * Get cache statistics
   *
   * @returns Object with enabled flag and current cache size
   */
  getCacheStats(): { enabled: boolean; size: number };
}

/**
 * Knowledge Client Interface
 *
 * Simplified interface specifically for sync hook operations.
 * Wraps IMCPClient with sync-specific defaults and error handling.
 */
export interface IKnowledgeClient {
  /**
   * Check if MCP server is healthy
   *
   * @returns true if server is reachable and healthy
   */
  checkHealth(): Promise<boolean>;

  /**
   * Add an episode to the knowledge graph
   *
   * Implements retry logic with exponential backoff.
   * Sanitizes group_id parameter based on database type.
   *
   * @param params - Episode data
   * @returns AddEpisodeResult with success status
   */
  addEpisode(params: AddEpisodeParams): Promise<AddEpisodeResult>;

  /**
   * Get current client configuration
   *
   * @returns Current configuration defaults
   */
  getConfig(): MCPClientConfig;
}

/**
 * Exported tool names from Graphiti MCP server
 */
export const MCP_TOOLS = {
  /** Add an episode to memory */
  ADD_EPISODE: "add_memory",
  /** Search for nodes/entities */
  SEARCH_NODES: "search_nodes",
  /** Search for facts/relationships */
  SEARCH_FACTS: "search_memory_facts",
  /** Get recent episodes */
  GET_EPISODES: "get_episodes",
  /** Get server status */
  GET_STATUS: "get_status",
  /** Clear all graph data */
  CLEAR_GRAPH: "clear_graph",
  /** Delete an episode */
  DELETE_EPISODE: "delete_episode",
  /** Delete an entity edge */
  DELETE_ENTITY_EDGE: "delete_entity_edge",
  /** Get an entity edge */
  GET_ENTITY_EDGE: "get_entity_edge",
} as const;

/**
 * Special characters that require escaping for FalkorDB/Lucene queries
 */
export const LUCENE_SPECIAL_CHARS = [
  '+', '-', '&', '&', '|', '|', '!', '(', ')', '{', '}',
  '[', ']', '^', '"', '~', '*', '?', ':', '\\', '/'
];
