/**
 * Qdrant HTTP API Wrapper for LKAP (Feature 023 - T046)
 * Local Knowledge Augmentation Platform
 *
 * TypeScript wrapper for Qdrant vector database operations:
 * - Semantic search with embedding generation
 * - Chunk retrieval by ID
 * - Document ingestion (via Python DoclingIngester)
 * - Health checks
 *
 * @see https://qdrant.github.io/qdrant/redoc/index.html
 */

import { $ } from "bun";
import { createMCPClient, MCPClient } from "../../lib/mcp-client.js";
import type { SearchFilters } from "./types.js";

// Configuration from environment
// Use CLI-specific URL for host-side operations (dev port mapping), fall back to standard URL
// Note: These are functions to allow env vars to be set after module import (e.g., by rag-cli.ts)
function getQdrantUrl(): string {
  return (
    process.env.MADEINOZ_KNOWLEDGE_QDRANT_URL_CLI ||
    process.env.MADEINOZ_KNOWLEDGE_QDRANT_URL ||
    "http://localhost:6334"  // Default to CLI dev port
  );
}
function getQdrantCollection(): string {
  return process.env.MADEINOZ_KNOWLEDGE_QDRANT_COLLECTION || "lkap_documents";
}

// Keep backward-compatible constants for existing code
const QDRANT_URL = getQdrantUrl();
const QDRANT_COLLECTION = getQdrantCollection();
// For CLI operations, use remote Ollama server (env var or default)
const OLLAMA_URL =
  process.env.MADEINOZ_KNOWLEDGE_QDRANT_OLLAMA_URL ||
  process.env.MADEINOZ_KNOWLEDGE_OLLAMA_BASE_URL ||
  "http://10.0.0.150:11434";  // Default to remote Ollama server
const EMBEDDING_MODEL =
  process.env.MADEINOZ_KNOWLEDGE_QDRANT_OLLAMA_MODEL ||
  process.env.MADEINOZ_KNOWLEDGE_OLLAMA_EMBEDDING_MODEL ||
  "bge-m3";  // Use bge-m3 as default
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
  // Use /api/embed endpoint (Ollama 0.1.26+) with batch format
  const response = await fetch(`${OLLAMA_URL}/api/embed`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: EMBEDDING_MODEL,
      input: [text],
      truncate: true,
    }),
    signal: AbortSignal.timeout(30000),
  });

  if (!response.ok) {
    throw new Error(`Ollama embedding failed: ${response.status}`);
  }

  const data = await response.json();
  // /api/embed returns {embeddings: [[...]]}
  return data.embeddings[0];
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
 * Semantic search in Qdrant via MCP server
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
  try {
    // Use MCPClient for proper session handling (runs inside container with Qdrant access)
    const client = createMCPClient();
    const response = await client.ragSearch({
      query,
      top_k: topK,
      domain: filters.domain,
      document_type: filters.type,
      component: filters.component,
      project: filters.project,
      version: filters.version,
    });

    if (!response.success) {
      throw new Error(response.error || "Search failed");
    }

    const result = response.data as any;

    // Check for ErrorResponse format (has 'error' field)
    if (result.error) {
      throw new Error(result.error);
    }

    // Transform MCP response to QdrantSearchResult format
    return (result.results || []).map((r: any) => ({
      chunk_id: r.chunk_id,
      text: r.text || "",
      source: r.source || "",
      page: r.page?.toString(),
      confidence: r.confidence,
      metadata: r.metadata || {},
    }));
  } catch (error) {
    throw new Error(`Search error: ${(error as Error).message}`);
  }
}

/**
 * Get a specific chunk by ID via MCP server
 *
 * @param chunkId - Unique chunk identifier
 * @returns Chunk data or null if not found
 */
export async function getChunk(chunkId: string): Promise<QdrantChunk | null> {
  try {
    // Use MCPClient for proper session handling (runs inside container with Qdrant access)
    const client = createMCPClient();
    const response = await client.ragGetChunk({ chunk_id: chunkId });

    if (!response.success) {
      if (response.error?.includes("not found")) {
        return null;
      }
      throw new Error(response.error || "Get chunk failed");
    }

    const result = response.data as any;

    // Check for ErrorResponse format (has 'error' field)
    if (result.error) {
      if (result.error.includes("not found")) {
        return null;
      }
      throw new Error(result.error);
    }

    // rag_get_chunk returns {success: true, chunk: {...}}
    const chunk = result.chunk;
    if (!chunk) {
      return null;
    }

    // Transform MCP response to QdrantChunk format
    return {
      id: chunk.id || chunk.chunk_id,
      payload: {
        chunk_id: chunk.id || chunk.chunk_id,
        doc_id: chunk.payload?.doc_id || chunk.document_id || "",
        text: chunk.payload?.text || chunk.text || "",
        source: chunk.payload?.source || chunk.source,
        page_section: chunk.payload?.page_section || chunk.page?.toString(),
        token_count: chunk.payload?.token_count || chunk.token_count,
        headings: chunk.payload?.headings || chunk.headings,
        domain: chunk.payload?.domain,
        project: chunk.payload?.project,
        component: chunk.payload?.component,
        type: chunk.payload?.type,
      },
    };
  } catch (error) {
    throw new Error(`Get chunk error: ${(error as Error).message}`);
  }
}

/**
 * Check Qdrant health via MCP server
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

  try {
    // Use MCPClient for proper session handling (runs inside container with Qdrant access)
    const client = createMCPClient();
    const response = await client.ragHealth();

    if (response.success) {
      const data = response.data as any;

      // Check for ErrorResponse format (has 'error' field)
      if (data.error) {
        return result;
      }

      // rag_health returns: connected, collection_exists, vector_count, collection_name
      result.connected = data.connected === true;
      result.collection_exists = data.collection_exists === true;
      result.vector_count = data.vector_count || 0;
    }
  } catch {
    // Connection failed
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
  // Use dynamic URL getter to pick up env vars set after module import
  const url = getQdrantUrl();
  const collection = getQdrantCollection();

  const response = await fetch(
    `${url}/collections/${collection}/points/scroll`,
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

/**
 * Ingest documents via MCP server rag_ingest tool
 *
 * Calls the MCP server's rag_ingest endpoint which runs inside the container
 * where Python dependencies (Docling, tiktoken) are installed.
 *
 * @param filePath - Path to file (relative to knowledge/inbox/ or absolute)
 * @param ingestAll - If true, ingest all documents in knowledge/inbox/
 * @returns Ingestion result with doc_id, chunk_count, status
 */
export async function ingest(
  filePath?: string,
  ingestAll: boolean = false
): Promise<IngestionResult | IngestionResult[]> {
  try {
    // Use MCPClient for proper session handling
    const client = createMCPClient();
    const response = await client.ragIngest({
      file_path: filePath || undefined,
      ingest_all: ingestAll,
    });

    if (!response.success) {
      throw new Error(response.error || "Ingestion failed");
    }

    const result = response.data as any;

    // Check for ErrorResponse format (has 'error' field)
    if (result.error) {
      throw new Error(result.error);
    }

    // Convert MCP response to IngestionResult format
    if (result.results && Array.isArray(result.results)) {
      // Batch ingestion
      return result.results.map((r: any) => ({
        success: r.status === "completed",
        doc_id: r.doc_id,
        filename: r.filename,
        chunk_count: r.chunk_count,
        status: r.status,
        error_message: r.error_message,
        processing_time_ms: r.processing_time_ms,
      }));
    } else {
      // Single file ingestion
      return {
        success: result.status === "completed" || result.success || false,
        doc_id: result.doc_id,
        filename: result.filename,
        chunk_count: result.chunk_count,
        status: result.status,
        error_message: result.error_message,
        processing_time_ms: result.processing_time_ms,
      };
    }
  } catch (error) {
    throw new Error(`Ingestion error: ${(error as Error).message}`);
  }
}

// ============================================================================
// Feature 024: Image Search Functions
// ============================================================================

/**
 * Image classification types
 */
export type ImageClassification =
  | "schematic"
  | "pinout"
  | "waveform"
  | "photo"
  | "table"
  | "graph"
  | "flowchart"
  | "unknown";

/**
 * Image search result from Qdrant
 */
export interface QdrantImageResult {
  image_id: string;
  doc_id: string;
  description: string;
  classification: ImageClassification;
  source_page?: number;
  source: string;
  confidence: number;
  image_data?: string; // Base64 encoded
  image_format?: string;
  headings?: string[];
}

/**
 * Search for images by description similarity via MCP server
 *
 * Feature 024: Image search with Vision LLM-enriched descriptions.
 *
 * @param query - Natural language search query (e.g., "GPIO pinout diagram")
 * @param classification - Optional filter by image type
 * @param topK - Maximum results to return (default: 10)
 * @returns Array of image results sorted by confidence
 */
export async function searchImages(
  query: string,
  classification?: ImageClassification,
  topK: number = 10
): Promise<QdrantImageResult[]> {
  try {
    // Use MCPClient for proper session handling (runs inside container with Qdrant access)
    const client = createMCPClient();
    const response = await client.ragSearchImages({
      query,
      top_k: topK,
      image_type: classification,
    });

    if (!response.success) {
      throw new Error(response.error || "Image search failed");
    }

    const result = response.data as any;

    // Check for ErrorResponse format (has 'error' field)
    if (result.error) {
      throw new Error(result.error);
    }

    // Transform MCP response to QdrantImageResult format
    return (result.results || []).map((r: any) => ({
      image_id: r.image_id || "",
      doc_id: r.doc_id || "",
      description: r.description || "",
      classification: r.image_type || "unknown",
      source_page: r.page,
      source: r.source || "",
      confidence: r.confidence,
      image_data: r.base64_data,
      image_format: r.image_format || "PNG",
      headings: r.headings || [],
    }));
  } catch (error) {
    throw new Error(`Image search error: ${(error as Error).message}`);
  }
}

/**
 * Get a specific image by ID via MCP server
 *
 * @param imageId - Unique image identifier
 * @returns Image data or null if not found
 */
export async function getImage(
  imageId: string
): Promise<QdrantImageResult | null> {
  try {
    // Use MCPClient for proper session handling (runs inside container with Qdrant access)
    const client = createMCPClient();
    const response = await client.ragGetImage({ image_id: imageId });

    if (!response.success) {
      if (response.error?.includes("not found")) {
        return null;
      }
      throw new Error(response.error || "Get image failed");
    }

    const result = response.data as any;

    // Check for ErrorResponse format (has 'error' field)
    if (result.error) {
      if (result.error.includes("not found")) {
        return null;
      }
      throw new Error(result.error);
    }

    return {
      image_id: result.image_id || "",
      doc_id: result.doc_id || "",
      description: result.description || "",
      classification: result.image_type || "unknown",
      source_page: result.page,
      source: result.source || "",
      confidence: 1.0,
      image_data: result.base64_data,
      image_format: result.image_format || "PNG",
      headings: result.headings || [],
    };
  } catch (error) {
    throw new Error(`Get image error: ${(error as Error).message}`);
  }
}

/**
 * List images with optional filters via MCP server
 *
 * @param docId - Optional filter by document ID (not supported by MCP, ignored)
 * @param classification - Optional filter by image type
 * @param limit - Maximum results (default: 50)
 * @returns Array of image results (without image_data for performance)
 */
export async function listImages(
  docId?: string,
  classification?: ImageClassification,
  limit: number = 50
): Promise<Omit<QdrantImageResult, "image_data">[]> {
  try {
    // Use MCPClient for proper session handling (runs inside container with Qdrant access)
    const client = createMCPClient();
    const response = await client.ragListImages({
      image_type: classification,
      limit,
    });

    if (!response.success) {
      throw new Error(response.error || "List images failed");
    }

    const result = response.data as any;

    // Check for ErrorResponse format (has 'error' field)
    if (result.error) {
      throw new Error(result.error);
    }

    // Transform MCP response, filter by docId if provided
    let images = (result.images || []).map((r: any) => ({
      image_id: r.image_id || "",
      doc_id: r.doc_id || "",
      description: (r.description || "").substring(0, 200), // Truncate for listing
      classification: r.image_type || "unknown",
      source_page: r.page,
      source: r.source || "",
      image_format: r.image_format || "PNG",
    }));

    // Filter by docId if provided (MCP doesn't support this filter)
    if (docId) {
      images = images.filter((img: any) => img.doc_id === docId);
    }

    return images;
  } catch (error) {
    throw new Error(`List images error: ${(error as Error).message}`);
  }
}
