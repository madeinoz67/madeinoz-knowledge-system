"""
Embedding Service for LKAP (Feature 022)
Local Knowledge Augmentation Platform

Provides embeddings using OpenRouter (text-embedding-3-large, 3072 dim)
as primary and Ollama (bge-large-en-v1.5, 1024 dim) as fallback.

Research Decision RT-004:
- Primary: OpenAI text-embedding-3-large (3072 dim) via OpenRouter
- Fallback: BAAI bge-large-en-v1.5 (1024 dim) via Ollama

Performance targets:
- Batch size: 100 texts per request (OpenRouter), 50 for Ollama
- Latency: <500ms for single embedding, <5s for 100 embeddings
"""

import os
import logging
import hashlib
from typing import List, Optional, Dict, Tuple
import requests
from dotenv import load_dotenv
from functools import lru_cache

load_dotenv()

logger = logging.getLogger(__name__)

# T046: Embedding cache configuration
# Cache size: 1000 most recent embeddings (adjust based on memory constraints)
# Cache key: hash(text + model) to ensure different models don't share cache
EMBEDDING_CACHE_SIZE = 1000

_embedding_cache: Dict[str, List[float]] = {}
_cache_hits = 0
_cache_misses = 0


def _cache_key(text: str, model: str) -> str:
    """Generate cache key from text and model name"""
    content = f"{model}:{text}"
    return hashlib.sha256(content.encode()).hexdigest()


def _get_cached_embedding(text: str, model: str) -> Optional[List[float]]:
    """Get embedding from cache if available"""
    global _cache_hits
    key = _cache_key(text, model)
    if key in _embedding_cache:
        _cache_hits += 1
        return _embedding_cache[key]
    _cache_misses += 1
    return None


def _set_cached_embedding(text: str, model: str, embedding: List[float]) -> None:
    """Store embedding in cache with LRU eviction"""
    key = _cache_key(text, model)

    # Simple LRU: remove oldest if cache is full
    if len(_embedding_cache) >= EMBEDDING_CACHE_SIZE:
        # Remove first (oldest) entry
        oldest_key = next(iter(_embedding_cache))
        del _embedding_cache[oldest_key]

    _embedding_cache[key] = embedding


def get_cache_stats() -> Dict[str, int]:
    """Get embedding cache statistics"""
    total = _cache_hits + _cache_misses
    hit_rate = _cache_hits / total if total > 0 else 0
    return {
        "cache_size": len(_embedding_cache),
        "cache_hits": _cache_hits,
        "cache_misses": _cache_misses,
        "hit_rate": round(hit_rate * 100, 1),
    }


# Configuration (reuses existing Graphiti variables per Constitution Principle X)
EMBEDDING_PROVIDER = os.getenv("MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER", "ollama")
EMBEDDING_MODEL = os.getenv("MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL", "mxbai-embed-large")
EMBEDDING_DIMENSION = int(os.getenv("MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS", "1024"))
EMBEDDING_PROVIDER_URL = os.getenv("MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER_URL", "http://host.containers.internal:11434")
OPENROUTER_API_KEY = os.getenv("MADEINOZ_KNOWLEDGE_OPENROUTER_API_KEY", "")

# Batch size configuration for optimal throughput
# OpenRouter supports up to 2048 inputs per request
# Ollama performance degrades beyond ~50 texts per batch
EMBEDDING_BATCH_SIZE_OPENROUTER = 100
EMBEDDING_BATCH_SIZE_OLLAMA = 50


class EmbeddingService:
    """
    Embedding service supporting multiple providers.

    OpenRouter (text-embedding-3-large): 3072 dimensions, high quality
    Ollama (bge-large-en-v1.5): 1024 dimensions, offline capability
    """

    def __init__(
        self,
        provider: str = EMBEDDING_PROVIDER,
        model: str = EMBEDDING_MODEL,
        dimension: int = EMBEDDING_DIMENSION,
        provider_url: str = EMBEDDING_PROVIDER_URL,
    ):
        self.provider = provider
        self.model = model
        self.dimension = dimension
        self.provider_url = provider_url
        self.session = requests.Session()

        # Configure based on provider
        if provider == "openai" or provider == "openrouter":
            self.api_url = "https://openrouter.ai/api/v1"
            self.batch_size = EMBEDDING_BATCH_SIZE_OPENROUTER
        else:  # ollama or other local providers
            self.api_url = provider_url
            self.batch_size = EMBEDDING_BATCH_SIZE_OLLAMA

        logger.info(f"Embedding service initialized: provider={self.provider}, "
                   f"model={self.model}, dimension={self.dimension}, "
                   f"batch_size={self.batch_size}")

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        T046: Checks cache before generating embeddings to avoid redundant API calls.

        Automatically batches requests for optimal throughput. Large lists
        are split into batches based on provider-specific batch sizes.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (each is a list of floats)

        Raises:
            RuntimeError: If embedding generation fails
        """
        # Check cache for each text, collect misses
        cached_embeddings: Dict[int, List[float]] = {}
        uncached_texts: List[Tuple[int, str]] = []  # (original_index, text)

        for i, text in enumerate(texts):
            cached = _get_cached_embedding(text, self.model)
            if cached is not None:
                cached_embeddings[i] = cached
            else:
                uncached_texts.append((i, text))

        # If all cached, return immediately
        if not uncached_texts:
            logger.debug(f"Cache hit: all {len(texts)} embeddings retrieved from cache")
            return [cached_embeddings[i] for i in range(len(texts))]

        # Generate embeddings for uncached texts
        uncached_text_list = [text for _, text in uncached_texts]

        # Process in batches for optimal throughput
        new_embeddings: List[List[float]] = []
        if len(uncached_text_list) <= self.batch_size:
            if self.provider == "openrouter":
                new_embeddings = self._embed_openrouter(uncached_text_list)
            else:
                new_embeddings = self._embed_ollama(uncached_text_list)
        else:
            # Split into batches and process
            for i in range(0, len(uncached_text_list), self.batch_size):
                batch = uncached_text_list[i:i + self.batch_size]
                if self.provider == "openrouter":
                    batch_embeddings = self._embed_openrouter(batch)
                else:
                    batch_embeddings = self._embed_ollama(batch)
                new_embeddings.extend(batch_embeddings)

        # Cache new embeddings
        for (_, text), embedding in zip(uncached_texts, new_embeddings):
            _set_cached_embedding(text, self.model, embedding)

        # Combine cached and new embeddings in original order
        all_embeddings = []
        for i in range(len(texts)):
            if i in cached_embeddings:
                all_embeddings.append(cached_embeddings[i])
            else:
                # Find corresponding new embedding
                for j, (orig_idx, _) in enumerate(uncached_texts):
                    if orig_idx == i:
                        all_embeddings.append(new_embeddings[j])
                        break

        cache_stats = get_cache_stats()
        if uncached_texts:
            logger.debug(
                f"Embedding cache: {cache_stats['cache_hits']} hits, "
                f"{cache_stats['cache_misses']} misses, "
                f"{cache_stats['hit_rate']}% hit rate"
            )

        return all_embeddings

    def _embed_openrouter(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenRouter API (text-embedding-3-large)"""
        if not OPENROUTER_API_KEY:
            raise RuntimeError("OPENROUTER_API_KEY required for OpenRouter embeddings")

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }

        data = {
            "model": self.model,
            "input": texts,
        }

        try:
            response = self.session.post(
                f"{self.api_url}/embeddings",
                headers=headers,
                json=data,
                timeout=30,
            )
            response.raise_for_status()

            result = response.json()
            embeddings = [item["embedding"] for item in result["data"]]
            return embeddings

        except requests.RequestException as e:
            logger.error(f"OpenRouter embedding failed: {e}")
            raise RuntimeError(
                f"OpenRouter embedding API failed. Check your API key is valid and "
                f"you have available credits. Verify network connectivity to OpenRouter. "
                f"Original error: {e}"
            ) from e

    def _embed_ollama(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Ollama API (bge-large-en-v1.5)"""
        # Ollama embedding API endpoint
        url = f"{self.api_url}/api/embed"
        data = {
            "model": self.model,
            "input": texts,
        }

        try:
            response = self.session.post(url, json=data, timeout=60)
            response.raise_for_status()

            result = response.json()
            embeddings = result.get("embeddings", [])

            if not embeddings:
                raise RuntimeError("No embeddings returned from Ollama")

            return embeddings

        except requests.RequestException as e:
            logger.error(f"Ollama embedding failed: {e}")
            raise RuntimeError(
                f"Ollama embedding service failed. Ensure Ollama is running at "
                f"{self.api_url} and the model '{self.model}' is available. "
                f"Run 'ollama pull {self.model}' if needed. Original error: {e}"
            ) from e

    def get_dimension(self) -> int:
        """Return the embedding dimension"""
        return self.dimension

    def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[List[float]]:
        """
        Generate embeddings for chunks with heading contextualization.

        T048: Contextualize chunks with heading prefixes before embedding.
        This prepends document hierarchy to chunk text so embeddings capture
        section context for better semantic retrieval.

        Args:
            chunks: List of chunk dictionaries with 'text' and optional 'headings' keys

        Returns:
            List of embedding vectors

        Note:
            If chunks have 'headings' metadata, prepends them to text.
            Example: "Embedded Systems > GPIO: The GPIO port supports..."
        """
        from .chunking_service import contextualize_chunk

        # Contextualize chunks before embedding
        contextualized_texts = []
        for chunk in chunks:
            if isinstance(chunk, dict):
                contextualized = contextualize_chunk(chunk)
                contextualized_texts.append(contextualized)
            else:
                # Plain string, use as-is
                contextualized_texts.append(chunk)

        return self.embed(contextualized_texts)

    def health_check(self) -> bool:
        """
        Check if the embedding service is healthy.

        Returns:
            True if service is accessible, False otherwise
        """
        try:
            if self.provider == "ollama":
                # Check Ollama is running
                response = self.session.get(f"{self.api_url}/api/tags", timeout=5)
                return response.status_code == 200
            else:
                # Check OpenRouter API key is valid
                return bool(OPENROUTER_API_KEY)
        except Exception as e:
            logger.warning(f"Embedding service health check failed: {e}")
            return False


# Singleton instance
_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create singleton embedding service instance"""
    global _service
    if _service is None:
        _service = EmbeddingService()
    return _service


def embed_text(text: str) -> List[float]:
    """
    Convenience function to embed a single text string.

    Args:
        text: Text to embed

    Returns:
        Embedding vector as list of floats
    """
    service = get_embedding_service()
    embeddings = service.embed([text])
    return embeddings[0]


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Convenience function to embed multiple text strings.

    Args:
        texts: List of texts to embed

    Returns:
        List of embedding vectors
    """
    service = get_embedding_service()
    return service.embed(texts)
