"""
Hybrid Search for LKAP (Feature 023 Enhancement)
RedTeam Gap #GAP-003: Add hybrid search (BM25 + dense) for +20% recall.

RAG Book Reference:
"Hybrid search combines vector similarity with traditional keyword matching (BM25).
When hybrid helps:
- Acronyms and proper nouns ('GPT-4' vs 'GPT' and '4')
- Exact phrase matching ('machine learning' as phrase, not separate concepts)
- Rare terms not well-represented in embedding space
- Mixed query types (some semantic, some keyword-focused)"

Architecture:
- Dense retrieval: Existing vector search via Qdrant
- Sparse retrieval: BM25-style keyword matching via Qdrant text index
- Fusion: Reciprocal Rank Fusion (RRF) - robust, no score normalization needed

RRF Formula:
    score(d) = sum(1 / (k + rank)) for each result list
    k = 60 (typical default that dampens rank impact)

Environment Variables:
    MADEINOZ_KNOWLEDGE_HYBRID_ENABLED: Enable hybrid search (default: true)
    MADEINOZ_KNOWLEDGE_HYBRID_ALPHA: Weight for dense vs sparse (default: 0.7)
    MADEINOZ_KNOWLEDGE_HYBRID_RRF_K: RRF constant k (default: 60)
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import asyncio

logger = logging.getLogger(__name__)

# Configuration with defaults
HYBRID_ENABLED = os.getenv("MADEINOZ_KNOWLEDGE_HYBRID_ENABLED", "true").lower() == "true"
HYBRID_ALPHA = float(os.getenv("MADEINOZ_KNOWLEDGE_HYBRID_ALPHA", "0.7"))  # 0.7 = favor dense
HYBRID_RRF_K = int(os.getenv("MADEINOZ_KNOWLEDGE_HYBRID_RRF_K", "60"))


@dataclass
class HybridResult:
    """A search result from hybrid search with both dense and sparse scores."""
    chunk_id: str
    document_id: str
    text: str
    dense_score: float
    sparse_score: float
    final_score: float
    dense_rank: int
    sparse_rank: int
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "text": self.text,
            "dense_score": self.dense_score,
            "sparse_score": self.sparse_score,
            "final_score": self.final_score,
            "dense_rank": self.dense_rank,
            "sparse_rank": self.sparse_rank,
            "metadata": self.metadata,
        }


def reciprocal_rank_fusion(
    dense_results: List[Tuple[str, float, Dict[str, Any]]],
    sparse_results: List[Tuple[str, float, Dict[str, Any]]],
    k: int = HYBRID_RRF_K,
) -> List[Tuple[str, float, float, int, int, Dict[str, Any]]]:
    """
    Combine dense and sparse results using Reciprocal Rank Fusion.

    RRF is robust and doesn't require score normalization since it uses ranks only.
    This is preferred over weighted score fusion when dense/sparse scores are on
    different scales.

    Args:
        dense_results: List of (chunk_id, score, metadata) from dense search
        sparse_results: List of (chunk_id, score, metadata) from sparse/BM25 search
        k: RRF constant (default: 60) - dampens the impact of rank

    Returns:
        List of (chunk_id, final_score, sparse_score, dense_rank, sparse_rank, metadata)
        sorted by final_score descending
    """
    # Track scores and ranks for each document
    rrf_scores = defaultdict(float)
    dense_ranks = {}  # chunk_id -> rank
    sparse_ranks = {}  # chunk_id -> rank
    sparse_scores = {}  # chunk_id -> sparse_score
    metadata_map = {}  # chunk_id -> metadata (prefer dense metadata)

    # Process dense results
    for rank, (chunk_id, score, metadata) in enumerate(dense_results):
        rrf_scores[chunk_id] += 1.0 / (k + rank)
        dense_ranks[chunk_id] = rank
        metadata_map[chunk_id] = metadata

    # Process sparse results
    for rank, (chunk_id, score, metadata) in enumerate(sparse_results):
        rrf_scores[chunk_id] += 1.0 / (k + rank)
        sparse_ranks[chunk_id] = rank
        sparse_scores[chunk_id] = score
        if chunk_id not in metadata_map:
            metadata_map[chunk_id] = metadata

    # Build final results
    results = []
    for chunk_id, final_score in rrf_scores.items():
        dense_rank = dense_ranks.get(chunk_id, 9999)
        sparse_rank = sparse_ranks.get(chunk_id, 9999)
        sparse_score = sparse_scores.get(chunk_id, 0.0)
        results.append((
            chunk_id,
            final_score,
            sparse_score,
            dense_rank,
            sparse_rank,
            metadata_map.get(chunk_id, {}),
        ))

    # Sort by final score descending
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def weighted_score_fusion(
    dense_results: List[Tuple[str, float, Dict[str, Any]]],
    sparse_results: List[Tuple[str, float, Dict[str, Any]]],
    alpha: float = HYBRID_ALPHA,
) -> List[Tuple[str, float, float, Dict[str, Any]]]:
    """
    Combine dense and sparse results using weighted score fusion.

    Note: This requires normalizing scores to 0-1 range, which can be tricky.
    RRF is generally preferred for this reason.

    Args:
        dense_results: List of (chunk_id, score, metadata) from dense search
        sparse_results: List of (chunk_id, score, metadata) from sparse search
        alpha: Weight for dense scores (0 = all sparse, 1 = all dense)

    Returns:
        List of (chunk_id, final_score, sparse_score, metadata)
    """
    # Normalize dense scores to 0-1
    if dense_results:
        max_dense = max(r[1] for r in dense_results)
        min_dense = min(r[1] for r in dense_results)
        range_dense = max_dense - min_dense
        if range_dense == 0:
            # All scores are equal, normalize to 1.0 for all
            dense_normalized = {r[0]: 1.0 for r in dense_results}
        else:
            dense_normalized = {
                r[0]: (r[1] - min_dense) / range_dense
                for r in dense_results
            }
    else:
        dense_normalized = {}

    # Normalize sparse scores to 0-1
    if sparse_results:
        max_sparse = max(r[1] for r in sparse_results)
        min_sparse = min(r[1] for r in sparse_results)
        range_sparse = max_sparse - min_sparse
        if range_sparse == 0:
            # All scores are equal, normalize to 1.0 for all
            sparse_normalized = {r[0]: 1.0 for r in sparse_results}
        else:
            sparse_normalized = {
                r[0]: (r[1] - min_sparse) / range_sparse
                for r in sparse_results
            }
    else:
        sparse_normalized = {}

    # Combine scores
    all_chunk_ids = set(dense_normalized.keys()) | set(sparse_normalized.keys())
    metadata_map = {r[0]: r[2] for r in dense_results}
    metadata_map.update({r[0]: r[2] for r in sparse_results if r[0] not in metadata_map})

    combined = []
    for chunk_id in all_chunk_ids:
        d_score = dense_normalized.get(chunk_id, 0)
        s_score = sparse_normalized.get(chunk_id, 0)
        final = alpha * d_score + (1 - alpha) * s_score
        combined.append((chunk_id, final, s_score, metadata_map.get(chunk_id, {})))

    combined.sort(key=lambda x: x[1], reverse=True)
    return combined


class HybridSearchService:
    """
    Hybrid search service combining dense (vector) and sparse (BM25) retrieval.

    Usage:
        service = HybridSearchService(qdrant_client)
        results = await service.search("authentication API", top_k=10)
    """

    def __init__(
        self,
        qdrant_client,
        enabled: bool = HYBRID_ENABLED,
        alpha: float = HYBRID_ALPHA,
        rrf_k: int = HYBRID_RRF_K,
    ):
        """
        Initialize hybrid search service.

        Args:
            qdrant_client: QdrantClient instance for vector/text search
            enabled: Whether to use hybrid search (default: from env)
            alpha: Weight for dense vs sparse (default: 0.7 from env)
            rrf_k: RRF constant k (default: 60 from env)
        """
        self.qdrant_client = qdrant_client
        self.enabled = enabled
        self.alpha = alpha
        self.rrf_k = rrf_k

    async def search(
        self,
        query: str,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        confidence_threshold: float = 0.5,
    ) -> List[HybridResult]:
        """
        Perform hybrid search combining dense and sparse retrieval.

        Args:
            query: Original text query (for sparse/BM25 search)
            query_vector: Query embedding vector (for dense search)
            top_k: Number of results to return
            filters: Optional metadata filters
            confidence_threshold: Minimum score threshold

        Returns:
            List of HybridResult sorted by final_score descending
        """
        if not self.enabled:
            # Fallback to dense-only search
            return await self._dense_only_search(
                query_vector, top_k, filters, confidence_threshold
            )

        # Run both searches in parallel
        dense_task = self._dense_search(query_vector, top_k * 2, filters, confidence_threshold)
        sparse_task = self._sparse_search(query, top_k * 2, filters)

        dense_results, sparse_results = await asyncio.gather(dense_task, sparse_task)

        # Log search stats
        logger.info(f"Hybrid search: dense={len(dense_results)}, sparse={len(sparse_results)}")

        # Fuse results using RRF
        fused = reciprocal_rank_fusion(dense_results, sparse_results, k=self.rrf_k)

        # Build HybridResult objects
        results = []
        for chunk_id, final_score, sparse_score, dense_rank, sparse_rank, metadata in fused[:top_k]:
            # Get dense score from dense_results
            dense_score = 0.0
            for cid, score, _ in dense_results:
                if cid == chunk_id:
                    dense_score = score
                    break

            results.append(HybridResult(
                chunk_id=chunk_id,
                document_id=metadata.get("document_id", metadata.get("doc_id", "")),
                text=metadata.get("text", ""),
                dense_score=dense_score,
                sparse_score=sparse_score,
                final_score=final_score,
                dense_rank=dense_rank,
                sparse_rank=sparse_rank,
                metadata=metadata,
            ))

        return results

    async def _dense_search(
        self,
        query_vector: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]],
        score_threshold: float,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Perform dense (vector) search via Qdrant.

        Returns:
            List of (chunk_id, score, metadata) tuples
        """
        try:
            results = await self.qdrant_client.search(
                query_vector=query_vector,
                top_k=top_k,
                filters=filters,
                score_threshold=score_threshold,
            )
            return [
                (r.chunk_id, r.score, r.metadata or {})
                for r in results
            ]
        except Exception as e:
            logger.error(f"Dense search failed: {e}")
            return []

    async def _sparse_search(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]],
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Perform sparse (BM25-like) search via Qdrant text index.

        Qdrant supports text filtering but not full BM25 scoring.
        For better sparse search, consider using SPLADE embeddings.

        This implementation uses Qdrant's text matching as a proxy for BM25.
        Results are scored based on match quality.

        Returns:
            List of (chunk_id, score, metadata) tuples
        """
        try:
            # Use Qdrant's scroll with text filter for keyword matching
            # Note: This is a simplified BM25 proxy; true BM25 requires SPLADE
            client = await self.qdrant_client._get_client()

            # Build filter for text matching
            # Split query into keywords for matching
            keywords = [kw.strip().lower() for kw in query.split() if len(kw.strip()) > 2]

            if not keywords:
                return []

            # Build Qdrant filter
            must_conditions = []
            for kw in keywords[:5]:  # Limit to top 5 keywords
                must_conditions.append({
                    "key": "text",
                    "match": {"text": kw}
                })

            # Use 'should' (OR) for matching any keyword
            search_filter = {"should": must_conditions}

            # Add metadata filters if provided
            if filters:
                for key, value in filters.items():
                    if value and key in ["domain", "project", "component", "type", "doc_id"]:
                        search_filter.setdefault("must", []).append({
                            "key": key,
                            "match": {"value": value}
                        })

            # Use scroll API with filter for text search
            # Note: Qdrant text search doesn't provide scores, so we estimate
            response = await client.post(
                f"{self.qdrant_client.url}/collections/{self.qdrant_client.collection_name}/points/scroll",
                json={
                    "limit": top_k,
                    "with_payload": True,
                    "filter": search_filter,
                }
            )

            if response.status_code != 200:
                logger.warning(f"Sparse search returned {response.status_code}")
                return []

            data = response.json()
            results = []

            # Qdrant scroll API returns {"result": {"points": [...], "next_page_offset": null}}
            result_data = data.get("result", {})
            if isinstance(result_data, dict):
                points = result_data.get("points", [])
            else:
                # Fallback if result is directly a list (older API version)
                points = result_data if isinstance(result_data, list) else []

            # Score based on keyword match count (simple proxy for BM25)
            for point in points:
                if not isinstance(point, dict):
                    continue  # Skip if point is not a dict
                payload = point.get("payload", {})
                text = payload.get("text", "").lower()
                chunk_id = point.get("id", "")

                # Count keyword matches as a simple relevance score
                match_count = sum(1 for kw in keywords if kw in text)
                score = match_count / max(len(keywords), 1)  # Normalize to 0-1

                if match_count > 0:
                    results.append((chunk_id, score, payload))

            # Sort by score descending
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]

        except Exception as e:
            logger.error(f"Sparse search failed: {e}")
            return []

    async def _dense_only_search(
        self,
        query_vector: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]],
        confidence_threshold: float,
    ) -> List[HybridResult]:
        """Fallback to dense-only search when hybrid is disabled."""
        results = await self.qdrant_client.search(
            query_vector=query_vector,
            top_k=top_k,
            filters=filters,
            score_threshold=confidence_threshold,
        )

        hybrid_results = []
        for rank, r in enumerate(results):
            hybrid_results.append(HybridResult(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                text=r.text,
                dense_score=r.score,
                sparse_score=0.0,
                final_score=r.score,
                dense_rank=rank,
                sparse_rank=9999,
                metadata=r.metadata or {},
            ))

        return hybrid_results


# Convenience function
async def hybrid_search(
    qdrant_client,
    query: str,
    query_vector: List[float],
    top_k: int = 10,
    filters: Optional[Dict[str, Any]] = None,
) -> List[HybridResult]:
    """
    Perform hybrid search combining dense and sparse retrieval.

    Args:
        qdrant_client: QdrantClient instance
        query: Original text query
        query_vector: Query embedding vector
        top_k: Number of results to return
        filters: Optional metadata filters

    Returns:
        List of HybridResult sorted by final_score
    """
    service = HybridSearchService(qdrant_client)
    return await service.search(query, query_vector, top_k, filters)
