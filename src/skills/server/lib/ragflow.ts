/**
 * RAGFlow HTTP Client Wrapper for LKAP (Feature 022)
 * Local Knowledge Augmentation Platform
 *
 * Provides TypeScript wrapper functions for RAGFlow API interactions.
 * RAGFlow uses HTTP REST API (no official Python SDK available).
 *
 * API Endpoints:
 * - POST /api/documents - Upload and index document
 * - GET  /api/search - Semantic search
 * - GET  /api/documents/{id} - Retrieve document chunks
 * - DELETE /api/documents/{id} - Delete document
 */

import type {
  Chunk,
  DocumentMetadata,
  SearchResult,
  SearchFilters,
} from "./types.ts";

// RAGFlow configuration from environment variables
const RAGFLOW_API_URL =
  process.env.MADEINOZ_KNOWLEDGE_RAGFLOW_API_URL || "http://localhost:9380";
const RAGFLOW_API_KEY = process.env.MADEINOZ_KNOWLEDGE_RAGFLOW_API_KEY;
const RAGFLOW_CONFIDENCE_THRESHOLD =
  parseFloat(process.env.MADEINOZ_KNOWLEDGE_RAGFLOW_CONFIDENCE_THRESHOLD || "0.7");

/**
 * Upload and index a document to RAGFlow
 *
 * @param filePath - Path to the document file
 * @param metadata - Optional document metadata for classification
 * @returns Document ID and status
 */
export async function uploadDocument(
  filePath: string,
  metadata?: DocumentMetadata
): Promise<{ doc_id: string; status: string }> {
  const formData = new FormData();
  formData.append("file", Bun.file(Bun.file(filePath).blob(), filePath));

  if (metadata) {
    formData.append("metadata", JSON.stringify(metadata));
  }

  const response = await fetch(`${RAGFLOW_API_URL}/api/documents`, {
    method: "POST",
    headers: {
      ...(RAGFLOW_API_KEY && { "X-API-Key": RAGFLOW_API_KEY }),
    },
    body: formData,
  });

  if (!response.ok) {
    throw new Error(
      `RAGFlow upload failed: ${response.status} ${response.statusText}`
    );
  }

  return await response.json();
}

/**
 * Semantic search in RAGFlow
 *
 * @param query - Natural language search query
 * @param filters - Optional search filters (domain, type, component, etc.)
 * @param topK - Maximum number of results (default: 10, max: 100)
 * @returns Array of search results with confidence scores
 */
export async function search(
  query: string,
  filters?: SearchFilters,
  topK = 10
): Promise<SearchResult[]> {
  const params = new URLSearchParams({
    query,
    top_k: Math.min(topK, 100).toString(),
  });

  if (filters) {
    if (filters.domain) params.append("domain", filters.domain);
    if (filters.type) params.append("type", filters.type);
    if (filters.component) params.append("component", filters.component);
    if (filters.project) params.append("project", filters.project);
    if (filters.version) params.append("version", filters.version);
  }

  const startTime = Date.now();
  const response = await fetch(
    `${RAGFLOW_API_URL}/api/search?${params.toString()}`,
    {
      method: "GET",
      headers: {
        ...(RAGFLOW_API_KEY && { "X-API-Key": RAGFLOW_API_KEY }),
      },
    }
  );

  if (!response.ok) {
    throw new Error(
      `RAGFlow search failed: ${response.status} ${response.statusText}`
    );
  }

  const results: SearchResult[] = await response.json();
  const latency = Date.now() - startTime;

  // Filter by confidence threshold and add latency tracking
  const filtered = results.filter((r) => r.confidence >= RAGFLOW_CONFIDENCE_THRESHOLD);

  // Log retrieval latency (FR-036a: basic logging, <500ms target)
  if (latency > 500) {
    console.warn(`RAGFlow search latency high: ${latency}ms (target: <500ms)`);
  }

  return filtered;
}

/**
 * Get exact document chunk by ID
 *
 * @param chunkId - Unique chunk identifier
 * @returns Chunk with text, metadata, and provenance
 */
export async function getChunk(chunkId: string): Promise<Chunk> {
  const response = await fetch(`${RAGFLOW_API_URL}/api/documents/${chunkId}`, {
    method: "GET",
    headers: {
      ...(RAGFLOW_API_KEY && { "X-API-Key": RAGFLOW_API_KEY }),
    },
  });

  if (!response.ok) {
    throw new Error(
      `RAGFlow getChunk failed: ${response.status} ${response.statusText}`
    );
  }

  return await response.json();
}

/**
 * Delete a document from RAGFlow
 *
 * @param docId - Document identifier to delete
 * @returns Success status
 */
export async function deleteDocument(docId: string): Promise<{ success: boolean }> {
  const response = await fetch(`${RAGFLOW_API_URL}/api/documents/${docId}`, {
    method: "DELETE",
    headers: {
      ...(RAGFLOW_API_KEY && { "X-API-Key": RAGFLOW_API_KEY }),
    },
  });

  if (!response.ok) {
    throw new Error(
      `RAGFlow delete failed: ${response.status} ${response.statusText}`
    );
  }

  return await response.json();
}

/**
 * List all ingested documents
 *
 * @param limit - Maximum number of documents to return (default: 100)
 * @returns Array of document summaries
 */
export async function listDocuments(limit = 100): Promise<
  Array<{
    doc_id: string;
    filename: string;
    upload_date: string;
    status: string;
  }>
> {
  const response = await fetch(
    `${RAGFLOW_API_URL}/api/documents?limit=${limit}`,
    {
      method: "GET",
      headers: {
        ...(RAGFLOW_API_KEY && { "X-API-Key": RAGFLOW_API_KEY }),
      },
    }
  );

  if (!response.ok) {
    throw new Error(
      `RAGFlow listDocuments failed: ${response.status} ${response.statusText}`
    );
  }

  return await response.json();
}
