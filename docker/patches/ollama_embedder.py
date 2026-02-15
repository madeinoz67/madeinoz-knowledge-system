"""
Ollama Embedder for LKAP (Feature 022 - T007)
Local Knowledge Augmentation Platform

Async embedding client using Ollama local models.
Uses bge-large-en-v1.5 model with 1024 dimensions.

Environment Variables:
    OLLAMA_BASE_URL: Ollama API endpoint (default: http://ollama:11434)
    OLLAMA_EMBEDDING_MODEL: Model name (default: bge-large-en-v1.5)
"""

import asyncio
import json
import logging
import time
from typing import List, Optional

import aiohttp

import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Environment configuration - Qdrant RAG embedding (MADEINOZ_KNOWLEDGE_QDRANT_* prefix)
OLLAMA_URL = os.getenv("MADEINOZ_KNOWLEDGE_QDRANT_OLLAMA_URL", os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"))
OLLAMA_MODEL = os.getenv("MADEINOZ_KNOWLEDGE_QDRANT_EMBEDDING_MODEL", os.getenv("OLLAMA_EMBEDDING_MODEL", "bge-m3"))
EMBEDDING_DIMENSION = 1024  # bge-large-en-v1.5 produces 1024-dim vectors


class OllamaEmbedder:
    """
    Async embedding client for Ollama local models.

    Uses aiohttp for async HTTP calls to Ollama API.
    Handles connection errors gracefully and logs embedding latency.
    """

    def __init__(
        self,
        base_url: str,
        model: str = "bge-large-en-v1.5",
    ):
        """
        Initialize Ollama embedder.

        Args:
            base_url: Ollama API endpoint (e.g., "http://ollama:11434")
            model: Model name (default: "bge-large-en-v1.5")
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._session: Optional[aiohttp.ClientSession] = None

        logger.info(
            f"OllamaEmbedder initialized: url={self.base_url}, model={self.model}"
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=120.0)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text string to embed

        Returns:
            Embedding vector as list of floats (1024 dimensions)

        Raises:
            RuntimeError: If embedding generation fails
        """
        embeddings = await self.embed_batch([text])
        return embeddings[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (each is 1024 floats)

        Raises:
            RuntimeError: If embedding generation fails
        """
        session = await self._get_session()
        # Use /api/embed endpoint for batch embeddings (Ollama 0.1.26+)
        url = f"{self.base_url}/api/embed"

        payload = {
            "model": self.model,
            "input": texts,
            "truncate": True,  # Truncate long texts to model's context length
        }

        start_time = time.time()

        try:
            async with session.post(url, json=payload) as response:
                # Capture response body for error debugging
                response_text = await response.text()

                if response.status != 200:
                    logger.error(f"Ollama API error {response.status}: {response_text[:500]}")
                    response.raise_for_status()

                data = json.loads(response_text)

                latency_ms = (time.time() - start_time) * 1000
                logger.debug(
                    f"Embedding: {len(texts)} texts in {latency_ms:.0f}ms "
                    f"({latency_ms/len(texts):.0f}ms per text)"
                )

                embeddings = data.get("embeddings", [])
                if not embeddings:
                    raise RuntimeError("No embeddings returned from Ollama")

                # Validate dimension
                if len(embeddings[0]) != EMBEDDING_DIMENSION:
                    logger.warning(
                        f"Embedding dimension mismatch: expected {EMBEDDING_DIMENSION}, "
                        f"got {len(embeddings[0])}"
                    )

                return embeddings

        except aiohttp.ClientError as e:
            logger.error(f"Ollama connection error: {e}")
            raise RuntimeError(
                f"Ollama connection failed. Ensure Ollama is running at "
                f"{self.base_url} and model '{self.model}' is available. "
                f"Run 'ollama pull {self.model}' if needed. Error: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Ollama embedding failed: {e}")
            raise RuntimeError(f"Ollama embedding failed: {e}") from e

    def get_dimension(self) -> int:
        """
        Return embedding dimension.

        Returns:
            Dimension of embedding vectors (1024 for bge-large-en-v1.5)
        """
        return EMBEDDING_DIMENSION

    async def health_check(self) -> bool:
        """
        Check if Ollama service is healthy.

        Returns:
            True if service is accessible, False otherwise
        """
        try:
            session = await self._get_session()
            url = f"{self.base_url}/api/tags"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5.0)) as response:
                return response.status == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False


# Singleton instance for module-level access
_embedder: Optional[OllamaEmbedder] = None


def get_ollama_embedder(
    base_url: str = OLLAMA_URL,
    model: str = OLLAMA_MODEL,
) -> OllamaEmbedder:
    """
    Get or create singleton Ollama embedder instance.

    Args:
        base_url: Ollama API endpoint
        model: Model name

    Returns:
            OllamaEmbedder instance
    """
    global _embedder
    if _embedder is None:
        _embedder = OllamaEmbedder(base_url=base_url, model=model)
    return _embedder
