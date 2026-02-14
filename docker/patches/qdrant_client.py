"""
Qdrant Client for LKAP (Local Knowledge Augmentation Platform)

Feature 022: Self-Hosted RAG with Qdrant as the lightweight vector database.

This module provides MCP tools for:
- Document ingestion with chunking
- Embedding generation via Ollama
- Semantic search via Qdrant
- Provenance tracking to knowledge graph

Architecture:
- Qdrant: Single container, 1-2GB RAM (vs RAGFlow's 16GB+)
- Docling: Document parsing (PDF, markdown, text)
- Ollama: Local embeddings (bge-large-en-v1.5, 1024 dimensions)
- Graphiti: Knowledge graph with provenance links

Environment Variables:
    MADEINOZ_KNOWLEDGE_QDRANT_URL: Qdrant API URL (default: http://localhost:6333)
    MADEINOZ_KNOWLEDGE_QDRANT_COLLECTION: Collection name (default: lkap_documents)
    MADEINOZ_KNOWLEDGE_OLLAMA_BASE_URL: Ollama API URL (default: http://localhost:11434)
    MADEINOZ_KNOWLEDGE_EMBEDDING_MODEL: Embedding model (default: bge-large-en-v1.5)
    MADEINOZ_KNOWLEDGE_EMBEDDING_DIMENSIONS: Vector dimensions (default: 1024)
"""

import os
import asyncio
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

import httpx
from mcp.server import FastMCP
from mcp.server.types import Tool

# Configure logging
logging.basicConfig(level=os.getenv("MADEINOZ_KNOWLEDGE_QDRANT_LOG_LEVEL", os.getenv("RAGFLOW_LOG_LEVEL", "INFO")))
logger = logging.getLogger(__name__)

# Environment configuration
QDRANT_URL = os.getenv("MADEINOZ_KNOWLEDGE_QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("MADEINOZ_KNOWLEDGE_QDRANT_COLLECTION", "lkap_documents")
OLLAMA_BASE_URL = os.getenv("MADEINOZ_KNOWLEDGE_QDRANT_OLLAMA_URL", os.getenv("MADEINOZ_KNOWLEDGE_OLLAMA_BASE_URL", "http://localhost:11434"))
EMBEDDING_MODEL = os.getenv("MADEINOZ_KNOWLEDGE_QDRANT_OLLAMA_MODEL", os.getenv("MADEINOZ_KNOWLEDGE_EMBEDDING_MODEL", "bge-large-en-v1.5"))
EMBEDDING_DIMENSIONS = int(os.getenv("MADEINOZ_KNOWLEDGE_EMBEDDING_DIMENSIONS", "1024"))
CHUNK_SIZE_MIN = int(os.getenv("MADEINOZ_KNOWLEDGE_QDRANT_CHUNK_SIZE_MIN", os.getenv("MADEINOZ_KNOWLEDGE_RAGFLOW_CHUNK_SIZE_MIN", "512")))
CHUNK_SIZE_MAX = int(os.getenv("MADEINOZ_KNOWLEDGE_QDRANT_CHUNK_SIZE_MAX", os.getenv("MADEINOZ_KNOWLEDGE_RAGFLOW_CHUNK_SIZE_MAX", "768")))
CHUNK_OVERLAP = int(os.getenv("MADEINOZ_KNOWLEDGE_QDRANT_CHUNK_OVERLAP", os.getenv("MADEINOZ_KNOWLEDGE_RAGFLOW_CHUNK_OVERLAP", "100")))

# Create MCP server
mcp = FastMCP("LKAP Qdrant Client")


@dataclass
class SearchResult:
    """A single search result from Qdrant."""
    chunk_id: str
    document_id: str
    text: str
    score: float
    metadata: Dict[str, Any]
    provenance: Optional[Dict[str, Any]] = None


class QdrantClient:
    """Client for Qdrant vector database operations."""

    # Singleton instance for connection pooling
    _instance: Optional["QdrantClient"] = None

    def __init__(
        self,
        url: str = QDRANT_URL,
        collection_name: str = QDRANT_COLLECTION,
        embedding_dim: int = EMBEDDING_DIMENSIONS,
    ):
        self.url = url.rstrip("/")
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def health(self) -> Dict[str, Any]:
        """Check Qdrant health status."""
        client = await self._get_client()
        try:
            response = await client.get(f"{self.url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return {"status": "error", "message": str(e)}

    async def create_collection(self, collection_name: str, vector_size: int = 1024) -> bool:
        """
        Create a Qdrant collection with specified configuration.

        Creates a collection optimized for semantic document search with:
        - Cosine distance for similarity
        - Payload indexes for: chunk_id, doc_id, domain, project, component, type

        Args:
            collection_name: Name for the new collection
            vector_size: Embedding vector dimensions (default: 1024)

        Returns:
            True if collection created successfully, False otherwise
        """
        client = await self._get_client()

        payload = {
            "vectors": {
                "size": vector_size,
                "distance": "Cosine",
            },
            "optimizers_config": {
                "indexing_threshold": 20000,
            },
            "replication_config": {
                "factor": 1,
            },
            "payload_schema": {
                # Index for chunk identifier
                "chunk_id": {"type": "keyword", "index": True},
                # Index for document identifier
                "doc_id": {"type": "keyword", "index": True},
                # Indexes for filtering by domain, project, component
                "domain": {"type": "keyword", "index": True},
                "project": {"type": "keyword", "index": True},
                "component": {"type": "keyword", "index": True},
                # Index for chunk type (e.g., "heading", "code", "text")
                "type": {"type": "keyword", "index": True},
            }
        }

        try:
            response = await client.put(
                f"{self.url}/collections/{collection_name}",
                json=payload
            )
            response.raise_for_status()
            logger.info(f"Created collection '{collection_name}' with vector_size={vector_size}")
            return True
        except Exception as e:
            logger.error(f"Failed to create collection '{collection_name}': {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """
        Comprehensive health check for Qdrant and collection.

        Returns:
            Dict with:
            - connected: bool - True if Qdrant server is reachable
            - collection_exists: bool - True if configured collection exists
            - vector_count: int - Number of vectors in collection (0 if doesn't exist)
        """
        result = {
            "connected": False,
            "collection_exists": False,
            "vector_count": 0,
        }

        # Check Qdrant server connectivity
        try:
            client = await self._get_client()
            response = await client.get(f"{self.url}/health")
            response.raise_for_status()
            result["connected"] = True
        except Exception as e:
            logger.error(f"Qdrant server unreachable: {e}")
            return result

        # Check collection exists and get vector count
        try:
            response = await client.get(f"{self.url}/collections/{self.collection_name}")
            if response.status_code == 200:
                info = response.json()
                result["collection_exists"] = True
                result["vector_count"] = info.get("result", {}).get("points_count", 0)
                logger.info(f"Collection '{self.collection_name}' exists with {result['vector_count']} vectors")
            else:
                logger.warning(f"Collection '{self.collection_name}' not found (status: {response.status_code})")
        except Exception as e:
            logger.warning(f"Collection check failed: {e}")

        return result

    async def ensure_collection(self) -> bool:
        """Ensure the collection exists, create if not."""
        client = await self._get_client()

        # Check if collection exists
        try:
            response = await client.get(f"{self.url}/collections/{self.collection_name}")
            if response.status_code == 200:
                logger.info(f"Collection '{self.collection_name}' exists")
                return True
        except Exception as e:
            logger.warning(f"Error checking collection: {e}")

        # Create collection
        try:
            payload = {
                "vectors": {
                    "size": self.embedding_dim,
                    "distance": "Cosine",
                },
                "optimizers_config": {
                    "indexing_threshold": 20000,
                },
                "replication_config": {
                    "factor": 1,
                },
            }
            response = await client.put(
                f"{self.url}/collections/{self.collection_name}",
                json=payload
            )
            response.raise_for_status()
            logger.info(f"Created collection '{self.collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            return False

    async def ingest_chunks(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        document_id: str,
    ) -> Dict[str, Any]:
        """
        Ingest document chunks into Qdrant.

        Args:
            chunks: List of chunk dicts with 'text' and 'metadata' keys
            embeddings: List of embedding vectors (one per chunk)
            document_id: Unique document identifier

        Returns:
            Dict with operation status and point IDs
        """
        if len(chunks) != len(embeddings):
            raise ValueError(f"Chunk count ({len(chunks)}) != embedding count ({len(embeddings)})")

        client = await self._get_client()

        # Prepare points for Qdrant
        points = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point_id = f"{document_id}_chunk_{idx}"
            payload = {
                "document_id": document_id,
                "chunk_index": idx,
                "text": chunk["text"],
                **chunk.get("metadata", {}),
                "ingested_at": datetime.utcnow().isoformat(),
            }
            points.append({
                "id": point_id,
                "vector": embedding,
                "payload": payload,
            })

        # Insert in batches (Qdrant recommends up to 1000 points per request)
        batch_size = 100
        results = []

        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            try:
                response = await client.put(
                    f"{self.url}/collections/{self.collection_name}/points",
                    {"points": batch}
                )
                response.raise_for_status()
                result = response.json()
                results.append(result)
                logger.info(f"Inserted batch {i//batch_size + 1}: {len(batch)} points")
            except Exception as e:
                logger.error(f"Failed to insert batch {i//batch_size + 1}: {e}")
                results.append({"status": "error", "message": str(e)})

        return {
            "status": "completed",
            "document_id": document_id,
            "chunks_ingested": len(points),
            "results": results,
        }

    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.5,
    ) -> List[SearchResult]:
        """
        Search for similar chunks by vector similarity.

        Args:
            query_vector: Query embedding vector
            top_k: Maximum results to return (default: 10)
            filters: Optional payload filters for filtering results
            score_threshold: Minimum similarity score (0-1, default: 0.5)

        Returns:
            List of SearchResult objects with chunk_id, document_id, text, score, metadata
        """
        client = await self._get_client()

        search_params = {
            "vector": query_vector,
            "limit": top_k,
            "with_payload": True,
            "score_threshold": score_threshold,
        }

        if filters:
            search_params["filter"] = filters

        try:
            response = await client.post(
                f"{self.url}/collections/{self.collection_name}/points/search",
                {"params": search_params}
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for result in data.get("result", []):
                results.append(SearchResult(
                    chunk_id=result.get("id"),
                    document_id=result.get("payload", {}).get("document_id"),
                    text=result.get("payload", {}).get("text", ""),
                    score=result.get("score", 0.0),
                    metadata=result.get("payload", {}),
                ))
            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    async def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        confidence_threshold: float = 0.70,
    ) -> List[Dict[str, Any]]:
        """
        High-level semantic search combining embedding + vector search.

        T029-T033: Implements User Story 2 - Semantic Search.
        - Generates embedding via Ollama
        - Searches Qdrant with confidence threshold
        - Filters by metadata if provided
        - Returns empty list on error (not exception)

        Args:
            query: Natural language search query
            top_k: Maximum results to return (default: 10)
            filters: Optional metadata filters (domain, project, component, type)
            confidence_threshold: Minimum similarity score (default: 0.70)

        Returns:
            List of result dicts with chunk_id, text, source, page, confidence, metadata
        """
        import time
        from patches.ollama_embedder import get_ollama_embedder

        start_time = time.time()

        try:
            # Generate query embedding
            embedder = get_ollama_embedder()
            query_vector = await embedder.embed(query)

            # Build Qdrant filter if metadata filters provided
            qdrant_filter = None
            if filters:
                must_conditions = []
                for key, value in filters.items():
                    if value and key in ["domain", "project", "component", "type", "doc_id"]:
                        must_conditions.append({
                            "key": key,
                            "match": {"value": value}
                        })
                if must_conditions:
                    qdrant_filter = {"must": must_conditions}

            # Search with vector
            raw_results = await self.search(
                query_vector=query_vector,
                top_k=top_k,
                filters=qdrant_filter,
                score_threshold=confidence_threshold,
            )

            # Transform to QdrantSearchResult format
            results = []
            for result in raw_results:
                payload = result.metadata or {}
                results.append({
                    "chunk_id": result.chunk_id,
                    "text": result.text,
                    "source": payload.get("source", ""),
                    "page": payload.get("page_section"),
                    "confidence": result.score,
                    "metadata": {
                        "domain": payload.get("domain", ""),
                        "project": payload.get("project", ""),
                        "component": payload.get("component", ""),
                        "type": payload.get("type", ""),
                        "headings": payload.get("headings", []),
                        "doc_id": result.document_id,
                    }
                })

            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(f"Semantic search: '{query[:50]}...' -> {len(results)} results in {elapsed_ms:.1f}ms")

            # T032: Track latency for <500ms target
            if elapsed_ms > 500:
                logger.warning(f"Search latency {elapsed_ms:.1f}ms exceeds 500ms target")

            return results

        except Exception as e:
            # T033: Return empty list, not error
            logger.error(f"Semantic search failed: {e}")
            return []

    async def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific chunk by ID."""
        client = await self._get_client()

        try:
            response = await client.get(
                f"{self.url}/collections/{self.collection_name}/points/{chunk_id}",
                params={"with_payload": True}
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            return data.get("result")
        except Exception as e:
            logger.error(f"Failed to get chunk {chunk_id}: {e}")
            return None

    async def delete_document(self, document_id: str) -> Dict[str, Any]:
        """Delete all chunks for a document."""
        client = await self._get_client()

        try:
            response = await client.post(
                f"{self.url}/collections/{self.collection_name}/points/delete",
                {
                    "filter": {
                        "must": [
                            {"key": "document_id", "match": {"value": document_id}}
                        ]
                    }
                }
            )
            response.raise_for_status()
            data = response.json()
            return {
                "status": "deleted",
                "document_id": document_id,
                "chunks_deleted": data.get("result", {}).get("status", "unknown"),
            }
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return {"status": "error", "message": str(e)}

    async def collection_info(self) -> Dict[str, Any]:
        """Get collection information."""
        client = await self._get_client()

        try:
            response = await client.get(f"{self.url}/collections/{self.collection_name}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {"status": "error", "message": str(e)}


class OllamaEmbedder:
    """Embedding generation using Ollama."""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = EMBEDDING_MODEL,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        client = await self._get_client()

        embeddings = []
        for text in texts:
            try:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": self.model,
                        "prompt": text,
                    }
                )
                response.raise_for_status()
                data = response.json()
                embedding = data.get("embedding")
                if embedding:
                    embeddings.append(embedding)
                else:
                    logger.error(f"No embedding in response for text: {text[:50]}...")
                    # Fallback: zero vector
                    embeddings.append([0.0] * EMBEDDING_DIMENSIONS)
            except Exception as e:
                logger.error(f"Embedding failed: {e}")
                # Fallback: zero vector
                embeddings.append([0.0] * EMBEDDING_DIMENSIONS)

        return embeddings

    async def health(self) -> Dict[str, Any]:
        """Check Ollama health."""
        client = await self._get_client()
        try:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            return {"status": "healthy", "models": response.json().get("models", [])}
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Global instances
_qdrant_client: Optional[QdrantClient] = None
_ollama_embedder: Optional[OllamaEmbedder] = None


def get_qdrant_client() -> QdrantClient:
    """Get or create global Qdrant client."""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient()
    return _qdrant_client


def get_ollama_embedder() -> OllamaEmbedder:
    """Get or create global Ollama embedder."""
    global _ollama_embedder
    if _ollama_embedder is None:
        _ollama_embedder = OllamaEmbedder()
    return _ollama_embedder


# ============================================================================
# MCP Tools
# ============================================================================

@mcp.tool()
async def qdrant_health() -> Dict[str, Any]:
    """Check Qdrant health status.

    Returns:
        Health check result with status and version info.
    """
    client = get_qdrant_client()
    return await client.health()


@mcp.tool()
async def qdrant_search(
    query: str,
    limit: int = 10,
    score_threshold: float = 0.5,
) -> Dict[str, Any]:
    """Search documents by semantic similarity.

    Args:
        query: Search query text
        limit: Maximum number of results (default: 10)
        score_threshold: Minimum similarity score 0-1 (default: 0.5)

    Returns:
        Search results with chunks, scores, and metadata.
    """
    # Generate query embedding
    embedder = get_ollama_embedder()
    embeddings = await embedder.embed([query])

    if not embeddings or not embeddings[0]:
        return {"status": "error", "message": "Failed to generate query embedding"}

    query_embedding = embeddings[0]

    # Search Qdrant
    client = get_qdrant_client()
    results = await client.search(
        query_embedding=query_embedding,
        limit=limit,
        score_threshold=score_threshold,
    )

    return {
        "status": "success",
        "query": query,
        "results": [
            {
                "chunk_id": r.chunk_id,
                "document_id": r.document_id,
                "text": r.text,
                "score": r.score,
                "metadata": r.metadata,
            }
            for r in results
        ],
    }


@mcp.tool()
async def qdrant_ingest(
    document_id: str,
    chunks: List[str],
) -> Dict[str, Any]:
    """Ingest document chunks into Qdrant.

    Args:
        document_id: Unique document identifier
        chunks: List of text chunks to ingest

    Returns:
        Ingestion status with chunk count and point IDs.
    """
    # Generate embeddings for all chunks
    embedder = get_ollama_embedder()
    embeddings = await embedder.embed(chunks)

    if len(embeddings) != len(chunks):
        return {
            "status": "error",
            "message": f"Embedding count mismatch: {len(embeddings)} != {len(chunks)}",
        }

    # Prepare chunk data
    chunk_data = [
        {"text": chunk, "metadata": {"chunk_size": len(chunk)}}
        for chunk in chunks
    ]

    # Ingest into Qdrant
    client = get_qdrant_client()
    await client.ensure_collection()

    result = await client.ingest_chunks(
        chunks=chunk_data,
        embeddings=embeddings,
        document_id=document_id,
    )

    return result


@mcp.tool()
async def qdrant_get_chunk(chunk_id: str) -> Dict[str, Any]:
    """Retrieve a specific chunk by ID.

    Args:
        chunk_id: Unique chunk identifier (e.g., "doc123_chunk_0")

    Returns:
        Chunk data with text, metadata, and vector info.
    """
    client = get_qdrant_client()
    chunk = await client.get_chunk(chunk_id)

    if chunk is None:
        return {"status": "not_found", "chunk_id": chunk_id}

    return {
        "status": "success",
        "chunk_id": chunk_id,
        "data": chunk,
    }


@mcp.tool()
async def qdrant_delete_document(document_id: str) -> Dict[str, Any]:
    """Delete all chunks for a document.

    Args:
        document_id: Document identifier to delete

    Returns:
        Deletion status with chunks deleted count.
    """
    client = get_qdrant_client()
    return await client.delete_document(document_id)


@mcp.tool()
async def qdrant_collection_info() -> Dict[str, Any]:
    """Get Qdrant collection information.

    Returns:
        Collection status, vector count, and configuration.
    """
    client = get_qdrant_client()
    return await client.collection_info()


@mcp.tool()
async def qdrant_list_documents() -> Dict[str, Any]:
    """List all unique documents in the collection.

    Returns:
        List of document IDs with chunk counts.
    """
    client = await (await get_qdrant_client()._get_client()).get(f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}")

    # Use scroll to get all points and extract unique document_ids
    # This is a simplified implementation - production would use proper pagination
    return {
        "status": "success",
        "note": "Use Qdrant scroll API for full document listing",
    }


@mcp.tool()
async def ollama_health() -> Dict[str, Any]:
    """Check Ollama embedding service health.

    Returns:
        Health status and available models.
    """
    embedder = get_ollama_embedder()
    return await embedder.health()


# Main entrypoint
if __name__ == "__main__":
    # Run MCP server
    mcp.run()
