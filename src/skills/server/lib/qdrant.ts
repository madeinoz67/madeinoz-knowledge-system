/**
 * Qdrant HTTP API Wrapper for LKAP (Feature 023 - T046)
 * Local Knowledge Augmentation Platform
 *
 * TypeScript wrapper for Qdrant vector database operations:
 * - Semantic search with embedding generation
 * - Chunk retrieval by ID
 * - Document ingestion
 * - Health checks
 *
 * @see https://qdrant.github.io/qdrant/redoc/index.html
 */

import type { SearchFilters } from "./types.js";

// Configuration from environment
const QDRANT_URL =
  process.env.MADEINOZ_KNOWLEDGE_QDRANT_URL || "http://localhost:6333";
const QDRANT_COLLECTION =
  process.env.MADEINOZ_KNOWLEDGE_QDRANT_COLLECTION || "lkap_documents";
const OLLAMA_URL =
  process.env.MADEINOZ_KNOWLEDGE_QDRANT_OLLAMA_URL ||
  process.env.MADEINOZ_KNOWLEDGE_OLLAMA_BASE_URL ||
  "http://localhost:11434";
const EMBEDDING_MODEL =
  process.env.MADEINOZ_KNOWLEDGE_QDRANT_OLLAMA_MODEL ||
  "bge-large-en-v1.5";
const CONFIDENCE_THRESHOLD = parseFloat(
  process.env.MADEINOZ_KNOWLEDGE_QDRANT_CONFIDENCE_THRESHOLD || "0.70"
);

/**
 * Search result from Qdrant
 */
export interface QdrantSearchResult {
  chunk_id: string;
  text: string;
  source: string;
  page?: string;
  confidence: number;
  metadata: {
    domain?: string;
    project?: string;
    component?: string;
    type?: string;
    headings?: string[];
    doc_id?: string;
  };
}

/**
 * Chunk data from Qdrant
 */
export interface QdrantChunk {
  id: string;
  vector?: number[];
  payload: {
    chunk_id: string;
    doc_id: string;
    text: string;
    source?: string;
    page_section?: string;
    position?: number;
    token_count?: number;
    headings?: string[];
    domain?: string;
    project?: string;
    component?: string;
    type?: string;
    created_at?: string;
  };
}

/**
 * Health check result
 */
export interface QdrantHealth {
  connected: boolean;
  collection_exists: boolean;
  vector_count: number;
  collection_name: string;
}

/**
 * Ingestion result
 */
export interface IngestionResult {
  success: boolean;
  doc_id: string;
  filename: string;
  chunk_count: number;
  status: string;
  error_message?: string;
  processing_time_ms?: number;
}

/**
 * Generate embedding via Ollama
 */
async function generateEmbedding(text: string): Promise<number[]> {
  const response = await fetch(`${OLLAMA_URL}/api/embeddings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: EMBEDDING_MODEL,
      prompt: text,
    }),
    signal: AbortSignal.timeout(30000),
  });

  if (!response.ok) {
    throw new Error(`Ollama embedding failed: ${response.status}`);
  }

  const data = await response.json();
  return data.embedding;
}

/**
 * Build Qdrant filter from search filters
 */
function buildFilter(filters: SearchFilters): object | undefined {
  const conditions: object[] = [];

  if (filters.domain) {
    conditions.push({
      key: "domain",
      match: { value: filters.domain },
    });
  }
  if (filters.type) {
    conditions.push({
      key: "type",
      match: { value: filters.type },
    });
  }
  if (filters.component) {
    conditions.push({
      key: "component",
      match: { value: filters.component },
    });
  }
  if (filters.project) {
    conditions.push({
      key: "project",
      match: { value: filters.project },
    });
  }
  if (filters.version) {
    conditions.push({
      key: "version",
      match: { value: filters.version },
    });
  }

  return conditions.length > 0 ? { must: conditions } : undefined;
}

/**
 * Semantic search in Qdrant
 *
 * @param query - Natural language search query
 * @param filters - Optional metadata filters
 * @param topK - Maximum results to return (default: 10)
 * @returns Array of search results sorted by confidence
 */
export async function search(
  query: string,
  filters: SearchFilters = {},
  topK: number = 10
): Promise<QdrantSearchResult[]> {
  // Generate query embedding
  const queryVector = await generateEmbedding(query);

  // Build search request
  const searchRequest: any = {
    vector: queryVector,
    limit: topK,
    with_payload: true,
    score_threshold: CONFIDENCE_THRESHOLD,
  };

  const qdrantFilter = buildFilter(filters);
  if (qdrantFilter) {
    searchRequest.filter = qdrantFilter;
  }

  // Search Qdrant
  const response = await fetch(
    `${QDRANT_URL}/collections/${QDRANT_COLLECTION}/points/search`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(searchRequest),
      signal: AbortSignal.timeout(30000),
    }
  );

  if (!response.ok) {
    if (response.status === 404) {
      return []; // Collection doesn't exist yet
    }
    throw new Error(`Qdrant search failed: ${response.status}`);
  }

  const data = await response.json();

  // Transform results
  return (data.result || []).map((point: any) => ({
    chunk_id: point.id,
    text: point.payload?.text || "",
    source: point.payload?.source || "",
    page: point.payload?.page_section,
    confidence: point.score,
    metadata: {
      domain: point.payload?.domain,
      project: point.payload?.project,
      component: point.payload?.component,
      type: point.payload?.type,
      headings: point.payload?.headings,
      doc_id: point.payload?.doc_id,
    },
  }));
}

/**
 * Get a specific chunk by ID
 *
 * @param chunkId - Unique chunk identifier
 * @returns Chunk data or null if not found
 */
export async function getChunk(chunkId: string): Promise<QdrantChunk | null> {
  const response = await fetch(
    `${QDRANT_URL}/collections/${QDRANT_COLLECTION}/points/${chunkId}`,
    {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      signal: AbortSignal.timeout(10000),
    }
  );

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(`Qdrant get chunk failed: ${response.status}`);
  }

  const data = await response.json();
  return data.result;
}

/**
 * Check Qdrant health
 *
 * @returns Health status
 */
export async function healthCheck(): Promise<QdrantHealth> {
  const result: QdrantHealth = {
    connected: false,
    collection_exists: false,
    vector_count: 0,
    collection_name: QDRANT_COLLECTION,
  };

  // Check server connectivity
  try {
    const healthResponse = await fetch(`${QDRANT_URL}/health`, {
      signal: AbortSignal.timeout(5000),
    });
    result.connected = healthResponse.ok;
  } catch {
    return result;
  }

  // Check collection exists
  try {
    const collectionResponse = await fetch(
      `${QDRANT_URL}/collections/${QDRANT_COLLECTION}`,
      { signal: AbortSignal.timeout(5000) }
    );

    if (collectionResponse.ok) {
      const data = await collectionResponse.json();
      result.collection_exists = true;
      result.vector_count = data.result?.points_count || 0;
    }
  } catch {
    // Collection doesn't exist
  }

  return result;
}

/**
 * List all documents (by counting unique doc_ids in collection)
 *
 * Note: This is a simplified implementation that scrolls through points
 * to find unique documents. For large collections, consider a proper index.
 *
 * @param limit - Maximum documents to return
 * @returns Array of unique document identifiers
 */
export async function listDocuments(
  limit: number = 100
): Promise<{ doc_id: string; source: string; count: number }[]> {
  const response = await fetch(
    `${QDRANT_URL}/collections/${QDRANT_COLLECTION}/points/scroll`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        limit: 1000, // Scroll through points to find unique docs
        with_payload: ["doc_id", "source"],
      }),
      signal: AbortSignal.timeout(30000),
    }
  );

  if (!response.ok) {
    if (response.status === 404) {
      return [];
    }
    throw new Error(`Qdrant scroll failed: ${response.status}`);
  }

  const data = await response.json();
  const points = data.result?.points || [];

  // Group by doc_id to get unique documents
  const docMap = new Map<string, { source: string; count: number }>();

  for (const point of points) {
    const docId = point.payload?.doc_id;
    const source = point.payload?.source || "unknown";

    if (docId) {
      if (docMap.has(docId)) {
        docMap.get(docId)!.count++;
      } else {
        docMap.set(docId, { source, count: 1 });
      }
    }
  }

  // Convert to array and sort
  return Array.from(docMap.entries())
    .map(([doc_id, data]) => ({
      doc_id,
      source: data.source,
      count: data.count,
    }))
    .slice(0, limit);
}
