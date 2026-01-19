/**
 * Output Formatter for token-efficient MCP responses
 * @module output-formatter
 */

import { logTransformationFailure, logTransformationSuccess } from './transformation-log';

// ============================================================================
// Types
// ============================================================================

export interface FormatOptions {
  maxLines?: number;
  maxLineLength?: number;
  collectMetrics?: boolean;
  timeoutMs?: number;
  query?: string;
}

export interface FormatResult {
  output: string;
  usedFallback: boolean;
  error?: string;
  metrics?: {
    rawBytes: number;
    compactBytes: number;
    savingsPercent: number;
    processingTimeMs: number;
  };
}

export const DEFAULT_OPTIONS: FormatOptions = {
  maxLines: 20,
  maxLineLength: 120,
  collectMetrics: false,
  timeoutMs: 100,
};

export type OperationFormatter = (data: unknown, options: FormatOptions) => string;

// ============================================================================
// Formatter Registry
// ============================================================================

const formatterRegistry = new Map<string, OperationFormatter>();

export function registerFormatter(operation: string, formatter: OperationFormatter): void {
  formatterRegistry.set(operation, formatter);
}

// ============================================================================
// Utility Functions (T007)
// ============================================================================

/**
 * Convert ISO timestamp to human-readable relative time.
 * Examples: "2h ago", "1d ago", "1mo ago", "1y ago"
 */
export function relativeTime(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();

  const seconds = Math.floor(diffMs / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  const months = Math.floor(days / 30);
  const years = Math.floor(days / 365);

  if (years > 0) return `${years}y ago`;
  if (months > 0) return `${months}mo ago`;
  if (days > 0) return `${days}d ago`;
  if (hours > 0) return `${hours}h ago`;
  if (minutes > 0) return `${minutes}m ago`;
  return 'just now';
}

/**
 * Truncate UUID to last 8 characters with ellipsis prefix.
 * Example: "550e8400-e29b-41d4-a716-446655440000" -> "...55440000"
 */
export function truncateUuid(uuid: string): string {
  if (!uuid || uuid.length < 8) return uuid || '';
  return `...${uuid.slice(-8)}`;
}

/**
 * Truncate text at word boundary with ellipsis.
 * The result including ellipsis will not exceed maxLength.
 * Example: "This is a long text that needs truncation" (maxLength=25) -> "This is a long text..."
 */
export function truncateText(text: string, maxLength: number): string {
  if (!text || text.length <= maxLength) return text || '';

  // Account for ellipsis (3 chars) in max length
  const effectiveMax = maxLength - 3;
  if (effectiveMax <= 0) {
    return text.slice(0, maxLength) + '...';
  }

  // Find last space before effective max
  const truncated = text.slice(0, effectiveMax);
  const lastSpace = truncated.lastIndexOf(' ');

  // If no space found or space is at the beginning, just cut at effectiveMax
  if (lastSpace <= 0) {
    return truncated.trim() + '...';
  }

  return truncated.slice(0, lastSpace).trim() + '...';
}

// ============================================================================
// MCP Response Type Guards
// ============================================================================

interface SearchNodesResponse {
  nodes: Array<{
    uuid?: string;
    name: string;
    labels?: string[]; // Actual MCP response uses labels array
    entity_type?: string; // Legacy field
    summary?: string;
    created_at?: string;
    group_id?: string;
  }>;
}

interface SearchFactsResponse {
  facts: Array<{
    uuid?: string;
    name: string; // Relation type (e.g., "ABOUT", "RELATES_TO")
    fact: string; // Human-readable fact description
    source_node_uuid?: string;
    target_node_uuid?: string;
    created_at?: string;
    valid_at?: string;
    // Legacy fields (older response format)
    source?: { name: string };
    target?: { name: string };
    relation?: string;
    confidence?: number;
  }>;
}

interface GetEpisodesResponse {
  episodes: Array<{
    uuid?: string;
    name: string;
    content?: string;
    created_at: string;
    source_description?: string;
  }>;
}

interface AddMemoryResponse {
  message: string;
  // Legacy fields (may not be present in newer server versions)
  uuid?: string;
  name?: string;
  entities_extracted?: number;
  facts_extracted?: number;
}

interface GetStatusResponse {
  status: string;
  message: string;
  // Legacy fields (may not be present in newer server versions)
  entity_count?: number;
  episode_count?: number;
  last_updated?: string;
}

interface DeleteResponse {
  success: boolean;
  uuid?: string;
  message?: string;
}

interface ClearGraphResponse {
  success: boolean;
  deleted_entities?: number;
  deleted_episodes?: number;
}

function isSearchNodesResponse(data: unknown): data is SearchNodesResponse {
  return (
    typeof data === 'object' &&
    data !== null &&
    'nodes' in data &&
    Array.isArray((data as SearchNodesResponse).nodes)
  );
}

function isSearchFactsResponse(data: unknown): data is SearchFactsResponse {
  if (typeof data !== 'object' || data === null) return false;
  if (!('facts' in data)) return false;
  const facts = (data as SearchFactsResponse).facts;
  if (!Array.isArray(facts)) return false;
  // Validate at least first fact has expected fields (name+fact or source+target+relation)
  if (facts.length > 0) {
    const first = facts[0];
    const hasNewFormat = 'name' in first && 'fact' in first;
    const hasLegacyFormat = 'source' in first && 'target' in first && 'relation' in first;
    return hasNewFormat || hasLegacyFormat;
  }
  return true; // Empty array is valid
}

function isGetEpisodesResponse(data: unknown): data is GetEpisodesResponse {
  return (
    typeof data === 'object' &&
    data !== null &&
    'episodes' in data &&
    Array.isArray((data as GetEpisodesResponse).episodes)
  );
}

function isAddMemoryResponse(data: unknown): data is AddMemoryResponse {
  return (
    typeof data === 'object' &&
    data !== null &&
    'message' in data &&
    typeof (data as AddMemoryResponse).message === 'string'
  );
}

function isGetStatusResponse(data: unknown): data is GetStatusResponse {
  return (
    typeof data === 'object' &&
    data !== null &&
    'status' in data &&
    'message' in data
  );
}

function isDeleteResponse(data: unknown): data is DeleteResponse {
  return (
    typeof data === 'object' &&
    data !== null &&
    'success' in data &&
    typeof (data as DeleteResponse).success === 'boolean'
  );
}

function isClearGraphResponse(data: unknown): data is ClearGraphResponse {
  return (
    typeof data === 'object' &&
    data !== null &&
    'success' in data &&
    typeof (data as ClearGraphResponse).success === 'boolean'
  );
}

// ============================================================================
// Individual Formatters (T014-T020)
// ============================================================================

/**
 * Format search_nodes / search_memory_nodes response
 * Output: Found N entities for "query":
 *         1. Name [Type] - Summary (truncated to 80 chars)
 */
export function formatSearchNodes(data: unknown, options: FormatOptions): string {
  if (!isSearchNodesResponse(data)) {
    throw new Error('Invalid data format for search_nodes');
  }

  const { nodes } = data;
  const query = options.query || 'query';
  const maxLines = options.maxLines ?? DEFAULT_OPTIONS.maxLines ?? 20;

  if (nodes.length === 0) {
    return `No entities found for "${query}"`;
  }

  const lines: string[] = [`Found ${nodes.length} entities for "${query}":`];

  const displayNodes = nodes.slice(0, maxLines);
  displayNodes.forEach((node, index) => {
    const summary = truncateText(node.summary || '', 120);
    // Use labels array (new format) or entity_type (legacy)
    const entityType = node.labels?.[0] || node.entity_type || 'Entity';
    lines.push(`${index + 1}. ${node.name} [${entityType}] - ${summary}`);
  });

  if (nodes.length > maxLines) {
    lines.push(`... and ${nodes.length - maxLines} more`);
  }

  return lines.join('\n');
}

/**
 * Format search_facts / search_memory_facts response
 * Output: Found N facts for "query":
 *         1. [RELATION] Fact description (truncated)
 */
export function formatSearchFacts(data: unknown, options: FormatOptions): string {
  if (!isSearchFactsResponse(data)) {
    throw new Error('Invalid data format for search_facts');
  }

  const { facts } = data;
  const query = options.query || 'query';
  const maxLines = options.maxLines ?? DEFAULT_OPTIONS.maxLines ?? 20;

  if (facts.length === 0) {
    return `No facts found for "${query}"`;
  }

  const lines: string[] = [`Found ${facts.length} facts for "${query}":`];

  const displayFacts = facts.slice(0, maxLines);
  displayFacts.forEach((fact, index) => {
    // New format: name is relation type, fact is description
    if (fact.name && fact.fact) {
      const relation = fact.name.toUpperCase();
      // Use full fact text - no truncation to preserve complete knowledge
      lines.push(`${index + 1}. [${relation}] ${fact.fact}`);
    }
    // Legacy format: source/target/relation objects
    else if (fact.source && fact.target && fact.relation) {
      const relation = fact.relation.toLowerCase().replace(/_/g, '-');
      let line = `${index + 1}. ${fact.source.name} --${relation}--> ${fact.target.name}`;
      if (fact.confidence !== undefined && fact.confidence > 0) {
        line += ` (${(fact.confidence * 100).toFixed(0)}%)`;
      }
      lines.push(line);
    }
  });

  if (facts.length > maxLines) {
    lines.push(`... and ${facts.length - maxLines} more`);
  }

  return lines.join('\n');
}

/**
 * Format get_episodes response
 * Output: Recent episodes (N):
 *         - [2h ago] Name - Content preview...
 */
export function formatGetEpisodes(data: unknown, options: FormatOptions): string {
  if (!isGetEpisodesResponse(data)) {
    throw new Error('Invalid data format for get_episodes');
  }

  const { episodes } = data;
  const maxLines = options.maxLines ?? DEFAULT_OPTIONS.maxLines ?? 20;

  if (episodes.length === 0) {
    return 'No episodes found';
  }

  const lines: string[] = [`Recent episodes (${episodes.length}):`];

  const displayEpisodes = episodes.slice(0, maxLines);
  displayEpisodes.forEach((episode) => {
    const time = relativeTime(episode.created_at);
    // Use full content - no truncation to preserve complete knowledge
    const content = episode.content || '';
    lines.push(`- [${time}] ${episode.name} - ${content}`);
  });

  if (episodes.length > maxLines) {
    lines.push(`... and ${episodes.length - maxLines} more`);
  }

  return lines.join('\n');
}

/**
 * Format add_memory response
 * Output: ✓ Episode queued: "Episode 'Name' queued for processing in group 'main'"
 * Legacy: ✓ Episode added: "Name" (id: ...uuid8)
 *           Extracted: N entities, M facts
 */
export function formatAddMemory(data: unknown, options: FormatOptions): string {
  if (!isAddMemoryResponse(data)) {
    throw new Error('Invalid data format for add_memory');
  }

  // New format: server returns a message string
  const lines: string[] = [`✓ ${data.message}`];

  // Legacy format: include uuid and extraction stats if available
  if (data.uuid) {
    const uuid = truncateUuid(data.uuid);
    const name = data.name || 'Unnamed episode';
    lines[0] = `✓ Episode added: "${name}" (id: ${uuid})`;
  }

  if (
    data.entities_extracted !== undefined ||
    data.facts_extracted !== undefined
  ) {
    const entities = data.entities_extracted ?? 0;
    const facts = data.facts_extracted ?? 0;
    lines.push(`  Extracted: ${entities} entities, ${facts} facts`);
  }

  return lines.join('\n');
}

/**
 * Format get_status response
 * Output: Knowledge Graph Status: OK
 *         Connected to neo4j database
 */
export function formatGetStatus(data: unknown, options: FormatOptions): string {
  if (!isGetStatusResponse(data)) {
    throw new Error('Invalid data format for get_status');
  }

  const status = data.status.toUpperCase();
  const lines: string[] = [`Knowledge Graph Status: ${status}`];
  lines.push(data.message);

  // Include legacy stats if available
  if (data.entity_count !== undefined && data.episode_count !== undefined) {
    let statsLine = `Entities: ${data.entity_count} | Episodes: ${data.episode_count}`;
    if (data.last_updated) {
      statsLine += ` | Last update: ${relativeTime(data.last_updated)}`;
    }
    lines.push(statsLine);
  }

  return lines.join('\n');
}

/**
 * Format delete_episode / delete_entity_edge response
 * Output: ✓ Deleted: ...uuid8
 *     or: ✗ Delete failed: message
 */
export function formatDelete(data: unknown, options: FormatOptions): string {
  if (!isDeleteResponse(data)) {
    throw new Error('Invalid data format for delete');
  }

  if (data.success) {
    const uuid = data.uuid ? truncateUuid(data.uuid) : 'unknown';
    return `✓ Deleted: ${uuid}`;
  } else {
    const message = data.message || 'Unknown error';
    return `✗ Delete failed: ${message}`;
  }
}

/**
 * Format clear_graph response
 * Output: ✓ Knowledge graph cleared
 *           Removed: N entities, M episodes
 */
export function formatClearGraph(data: unknown, options: FormatOptions): string {
  if (!isClearGraphResponse(data)) {
    throw new Error('Invalid data format for clear_graph');
  }

  if (!data.success) {
    return '✗ Clear graph failed';
  }

  const lines: string[] = ['✓ Knowledge graph cleared'];

  if (
    data.deleted_entities !== undefined ||
    data.deleted_episodes !== undefined
  ) {
    const entities = data.deleted_entities ?? 0;
    const episodes = data.deleted_episodes ?? 0;
    lines.push(`  Removed: ${entities} entities, ${episodes} episodes`);
  }

  return lines.join('\n');
}

// ============================================================================
// Main Entry Point (T021)
// ============================================================================

// Register all built-in formatters
registerFormatter('search_nodes', formatSearchNodes);
registerFormatter('search_memory_nodes', formatSearchNodes);
registerFormatter('search_facts', formatSearchFacts);
registerFormatter('search_memory_facts', formatSearchFacts);
registerFormatter('get_episodes', formatGetEpisodes);
registerFormatter('add_memory', formatAddMemory);
registerFormatter('add_episode', formatAddMemory);
registerFormatter('get_status', formatGetStatus);
registerFormatter('delete_episode', formatDelete);
registerFormatter('delete_entity_edge', formatDelete);
registerFormatter('clear_graph', formatClearGraph);

/**
 * Main entry point for formatting MCP responses.
 * Routes to the appropriate formatter based on operation name.
 * Falls back to JSON on unknown operations or errors.
 */
export function formatOutput(
  operation: string,
  data: unknown,
  options?: FormatOptions
): FormatResult {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  const startTime = performance.now();

  // Calculate raw size
  const rawJson = JSON.stringify(data, null, 2);
  const rawBytes = new TextEncoder().encode(rawJson).length;

  // Try to find and execute formatter
  const formatter = formatterRegistry.get(operation);

  if (!formatter) {
    // Unknown operation - fallback to JSON
    return {
      output: rawJson,
      usedFallback: true,
      error: `No formatter registered for operation: ${operation}`,
      metrics: opts.collectMetrics
        ? {
            rawBytes,
            compactBytes: rawBytes,
            savingsPercent: 0,
            processingTimeMs: performance.now() - startTime,
          }
        : undefined,
    };
  }

  try {
    const output = formatter(data, opts);
    const compactBytes = new TextEncoder().encode(output).length;
    const processingTimeMs = performance.now() - startTime;
    const savingsPercent =
      rawBytes > 0 ? ((rawBytes - compactBytes) / rawBytes) * 100 : 0;

    // Log slow transformations
    if (processingTimeMs >= 50) {
      logTransformationSuccess(operation, rawBytes, processingTimeMs).catch(() => {});
    }

    return {
      output,
      usedFallback: false,
      metrics: opts.collectMetrics
        ? {
            rawBytes,
            compactBytes,
            savingsPercent,
            processingTimeMs,
          }
        : undefined,
    };
  } catch (error) {
    const processingTimeMs = performance.now() - startTime;
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';

    // Log transformation failure
    logTransformationFailure(operation, rawBytes, errorMessage, processingTimeMs).catch(
      () => {}
    );

    return {
      output: rawJson,
      usedFallback: true,
      error: errorMessage,
      metrics: opts.collectMetrics
        ? {
            rawBytes,
            compactBytes: rawBytes,
            savingsPercent: 0,
            processingTimeMs,
          }
        : undefined,
    };
  }
}
