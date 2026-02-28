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

# Environment configuration - use container env vars (populated by config.ts from MADEINOZ_KNOWLEDGE_QDRANT_*)
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "bge-m3")
EMBEDDING_DIMENSION = 1024  # bge-large-en-v1.5 produces 1024-dim vectors

# #GAP-002: E5 model prefix configuration
# E5 models (intfloat/e5-*) require "query: " and "passage: " prefixes for optimal performance.
# BGE models do NOT require prefixes.
# Models matching these patterns will have prefixes automatically added.
E5_MODEL_PATTERNS = {"e5-", "multilingual-e5-", "intfloat/e5"}


class OllamaEmbedder:
    """
    Async embedding client for Ollama local models.

    Uses aiohttp for async HTTP calls to Ollama API.
    Handles connection errors gracefully and logs embedding latency.

    #GAP-002: Automatically adds query/passage prefixes for E5 models.
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

        # #GAP-002: Detect if this model needs E5 prefixes
        self._needs_e5_prefix = self._detect_e5_model(model)

        logger.info(
            f"OllamaEmbedder initialized: url={self.base_url}, model={self.model}, "
            f"e5_prefixes={self._needs_e5_prefix}"
        )

    def _detect_e5_model(self, model: str) -> bool:
        """Detect if model requires E5-style query/passage prefixes."""
        model_lower = model.lower()
        return any(pattern in model_lower for pattern in E5_MODEL_PATTERNS)

    def _add_e5_prefix(self, text: str, is_query: bool = True) -> str:
        """Add E5 prefix to text if model requires it."""
        if not self._needs_e5_prefix:
            return text
        prefix = "query: " if is_query else "passage: "
        return prefix + text

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

    async def embed(self, text: str, is_query: bool = True) -> List[float]:
        """
        Generate embedding for a single text.

        #GAP-002: Adds E5 prefixes for models that require them.
        - is_query=True: Use "query: " prefix for search queries
        - is_query=False: Use "passage: " prefix for documents/chunks

        Args:
            text: Text string to embed
            is_query: If True, use "query: " prefix for E5 models (default: True)

        Returns:
            Embedding vector as list of floats (1024 dimensions)

        Raises:
            RuntimeError: If embedding generation fails
        """
        embeddings = await self.embed_batch([text], is_query=is_query)
        return embeddings[0]

    async def embed_batch(self, texts: List[str], is_query: bool = False) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        #GAP-002: Adds E5 prefixes for models that require them.
        - is_query=True: Use "query: " prefix for search queries
        - is_query=False: Use "passage: " prefix for documents/chunks

        Args:
            texts: List of text strings to embed
            is_query: If True, use "query: " prefix for E5 models (default: False for batch/documents)

        Returns:
            List of embedding vectors (each is 1024 floats)

        Raises:
            RuntimeError: If embedding generation fails
        """
        # #GAP-002: Add E5 prefixes if needed
        prefixed_texts = [self._add_e5_prefix(text, is_query=is_query) for text in texts]

        session = await self._get_session()
        # Use /api/embed endpoint for batch embeddings (Ollama 0.1.26+)
        url = f"{self.base_url}/api/embed"

        payload = {
            "model": self.model,
            "input": prefixed_texts,  # #GAP-002: Use prefixed texts for E5 support
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
                    f"Embedding: {len(prefixed_texts)} texts in {latency_ms:.0f}ms "
                    f"({latency_ms/len(prefixed_texts):.0f}ms per text)"
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
