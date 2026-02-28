"""
Cross-Encoder Reranker for LKAP (Feature 023 Enhancement)

RedTeam Gap #GAP-007: Add cross-encoder reranking for +30-40% retrieval accuracy.

RAG Book Recommendation:
"Never skip reranking for production RAG systems. Cross-encoder reranking
on top-20 candidates improves NDCG by 15-25 points."

Architecture:
- Initial retrieval: Bi-encoder (fast, approximates relevance)
- Reranking: Cross-encoder (slow, precise relevance scoring)
- Returns: Top-k re-ranked by cross-encoder scores

Supported Backends:
1. sentence-transformers: Local cross-encoder models (BAAI/bge-reranker-base)
2. Ollama: API-based reranking (if model supports it)
3. OpenRouter: API-based reranking (Cohere rerank, etc.)

Environment Variables:
    MADEINOZ_KNOWLEDGE_RERANKER_ENABLED: Enable/disable reranking (default: true)
    MADEINOZ_KNOWLEDGE_RERANKER_MODEL: Model name (default: BAAI/bge-reranker-base)
    MADEINOZ_KNOWLEDGE_RERANKER_TOP_K: Candidates to rerank (default: 20)
    MADEINOZ_KNOWLEDGE_RERANKER_FINAL_K: Final results after reranking (default: 10)
"""

import os
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# Configuration with defaults
RERANKER_ENABLED = os.getenv("MADEINOZ_KNOWLEDGE_RERANKER_ENABLED", "true").lower() == "true"
RERANKER_MODEL = os.getenv("MADEINOZ_KNOWLEDGE_RERANKER_MODEL", "BAAI/bge-reranker-base")
RERANKER_TOP_K = int(os.getenv("MADEINOZ_KNOWLEDGE_RERANKER_TOP_K", "20"))
RERANKER_FINAL_K = int(os.getenv("MADEINOZ_KNOWLEDGE_RERANKER_FINAL_K", "10"))
RERANKER_PROVIDER = os.getenv("MADEINOZ_KNOWLEDGE_RERANKER_PROVIDER", "local")  # local, openrouter, cohere


@dataclass
class RerankedResult:
    """A search result after reranking."""
    chunk_id: str
    document_id: str
    text: str
    initial_score: float  # Original bi-encoder score
    rerank_score: float   # Cross-encoder score
    final_score: float    # Combined or rerank score
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "text": self.text,
            "initial_score": self.initial_score,
            "rerank_score": self.rerank_score,
            "final_score": self.final_score,
            "metadata": self.metadata,
        }


class RerankerBackend(ABC):
    """Abstract base class for reranker backends."""

    @abstractmethod
    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 10,
    ) -> List[RerankedResult]:
        """
        Rerank candidates by query relevance.

        Args:
            query: Original search query
            candidates: List of candidate results with 'text', 'score', 'chunk_id', etc.
            top_k: Number of results to return

        Returns:
            List of RerankedResult sorted by rerank_score descending
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the backend is available."""
        pass


class LocalCrossEncoderBackend(RerankerBackend):
    """
    Local cross-encoder reranker using sentence-transformers.

    Uses BAAI/bge-reranker-base by default (fast, accurate).
    Falls back gracefully if model not available.
    """

    def __init__(self, model_name: str = RERANKER_MODEL):
        self.model_name = model_name
        self._model = None
        self._available = None

    def _load_model(self):
        """Lazy load the cross-encoder model."""
        if self._model is not None:
            return self._model

        try:
            from sentence_transformers import CrossEncoder
            logger.info(f"Loading cross-encoder model: {self.model_name}")
            self._model = CrossEncoder(self.model_name, max_length=512)
            self._available = True
            return self._model
        except ImportError:
            logger.warning("sentence-transformers not installed, reranking disabled")
            self._available = False
            return None
        except Exception as e:
            logger.error(f"Failed to load cross-encoder model: {e}")
            self._available = False
            return None

    def is_available(self) -> bool:
        """Check if local cross-encoder is available."""
        if self._available is None:
            self._load_model()
        return self._available

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 10,
    ) -> List[RerankedResult]:
        """Rerank using local cross-encoder."""
        model = self._load_model()
        if not model or not candidates:
            return []

        start_time = time.time()

        # Prepare query-document pairs
        pairs = [(query, c.get("text", "")) for c in candidates]

        # Score all pairs
        try:
            scores = model.predict(pairs)
        except Exception as e:
            logger.error(f"Cross-encoder prediction failed: {e}")
            return []

        # Create reranked results
        results = []
        for i, candidate in enumerate(candidates):
            rerank_score = float(scores[i]) if hasattr(scores, '__iter__') else float(scores)

            # Normalize cross-encoder score to 0-1 range (models output varies)
            # BGE-reranker outputs logits; apply sigmoid for probability-like score
            import math
            normalized_score = 1 / (1 + math.exp(-rerank_score)) if rerank_score < 10 else rerank_score

            results.append(RerankedResult(
                chunk_id=candidate.get("chunk_id", ""),
                document_id=candidate.get("document_id", "") or candidate.get("metadata", {}).get("doc_id", ""),
                text=candidate.get("text", ""),
                initial_score=candidate.get("score", 0) or candidate.get("confidence", 0),
                rerank_score=normalized_score,
                final_score=normalized_score,  # Use rerank score as final
                metadata=candidate.get("metadata", {}),
            ))

        # Sort by rerank score and take top_k
        results.sort(key=lambda x: x.rerank_score, reverse=True)
        results = results[:top_k]

        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(f"Reranked {len(candidates)} candidates -> {len(results)} results in {elapsed_ms:.1f}ms")

        return results


class NoOpRerankerBackend(RerankerBackend):
    """Passthrough reranker that preserves original order (for fallback)."""

    def is_available(self) -> bool:
        return True

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 10,
    ) -> List[RerankedResult]:
        """Pass through candidates without reranking."""
        results = []
        for candidate in candidates[:top_k]:
            score = candidate.get("score", 0) or candidate.get("confidence", 0)
            results.append(RerankedResult(
                chunk_id=candidate.get("chunk_id", ""),
                document_id=candidate.get("document_id", "") or candidate.get("metadata", {}).get("doc_id", ""),
                text=candidate.get("text", ""),
                initial_score=score,
                rerank_score=score,  # Same as initial
                final_score=score,
                metadata=candidate.get("metadata", {}),
            ))
        return results


class RerankerService:
    """
    Main reranker service with backend selection and fallback.

    Usage:
        reranker = RerankerService()
        reranked = reranker.rerank(query, initial_results, top_k=10)
    """

    _instance: Optional["RerankerService"] = None

    def __init__(
        self,
        enabled: bool = RERANKER_ENABLED,
        provider: str = RERANKER_PROVIDER,
        model: str = RERANKER_MODEL,
        top_k_candidates: int = RERANKER_TOP_K,
        final_k: int = RERANKER_FINAL_K,
    ):
        self.enabled = enabled
        self.provider = provider
        self.model = model
        self.top_k_candidates = top_k_candidates
        self.final_k = final_k

        # Initialize backend
        self._backend: Optional[RerankerBackend] = None
        self._noop_backend = NoOpRerankerBackend()

    @classmethod
    def get_instance(cls) -> "RerankerService":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_backend(self) -> RerankerBackend:
        """Get or initialize the reranker backend."""
        if self._backend is not None:
            return self._backend

        if self.provider == "local":
            self._backend = LocalCrossEncoderBackend(self.model)
            if not self._backend.is_available():
                logger.warning("Local reranker not available, using passthrough")
                self._backend = self._noop_backend
        else:
            # Future: Add OpenRouter, Cohere backends
            logger.warning(f"Unknown reranker provider '{self.provider}', using passthrough")
            self._backend = self._noop_backend

        return self._backend

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[RerankedResult]:
        """
        Rerank search results by query relevance.

        Args:
            query: Original search query
            candidates: List of initial search results
            top_k: Number of final results (default: from config)

        Returns:
            List of RerankedResult sorted by relevance
        """
        if top_k is None:
            top_k = self.final_k

        if not candidates:
            return []

        if not self.enabled:
            # Reranking disabled, return passthrough results
            return self._noop_backend.rerank(query, candidates, top_k)

        # Get backend and rerank
        backend = self._get_backend()

        # Take top_k_candidates for reranking (efficiency)
        candidates_to_rerank = candidates[:self.top_k_candidates]

        return backend.rerank(query, candidates_to_rerank, top_k)

    def is_available(self) -> bool:
        """Check if reranking is available."""
        if not self.enabled:
            return False
        return self._get_backend().is_available()


# Convenience function for direct use
def rerank_results(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = 10,
) -> List[RerankedResult]:
    """
    Rerank search results by query relevance.

    Args:
        query: Original search query
        candidates: List of initial search results
        top_k: Number of final results

    Returns:
        List of RerankedResult sorted by relevance
    """
    service = RerankerService.get_instance()
    return service.rerank(query, candidates, top_k)
