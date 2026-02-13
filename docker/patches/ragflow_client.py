"""
RAGFlow HTTP Client for LKAP (Feature 022)
Local Knowledge Augmentation Platform

HTTP REST API client for RAGFlow vector database operations.
Research Decision RT-001: Use HTTP REST API with Python requests library.

API Endpoints:
- POST /api/v1/documents - Upload and index document
- GET  /api/v1/search - Semantic search
- GET  /api/v1/documents/{id} - Retrieve document chunks
- DELETE /api/v1/documents/{id} - Delete document
"""

import os
import logging
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# RAGFlow configuration
RAGFLOW_API_URL = os.getenv("MADEINOZ_KNOWLEDGE_RAGFLOW_API_URL", "http://ragflow:9380")
RAGFLOW_API_KEY = os.getenv("MADEINOZ_KNOWLEDGE_RAGFLOW_API_KEY", "")
RAGFLOW_CONFIDENCE_THRESHOLD = float(os.getenv("MADEINOZ_KNOWLEDGE_RAGFLOW_CONFIDENCE_THRESHOLD", "0.7"))


@dataclass
class SearchResult:
    """Search result from RAGFlow"""
    chunk_id: str
    text: str
    source_document: str
    page_section: str
    confidence: float
    metadata: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict) -> "SearchResult":
        return cls(
            chunk_id=data["chunk_id"],
            text=data["text"],
            source_document=data["source_document"],
            page_section=data.get("page_section", ""),
            confidence=float(data["confidence"]),
            metadata=data.get("metadata", {}),
        )


class RAGFlowClient:
    """
    RAGFlow HTTP REST API client wrapper.

    Provides methods for document upload, semantic search, chunk retrieval,
    and document deletion with error handling and retry logic.
    """

    def __init__(
        self,
        api_url: str = RAGFLOW_API_URL,
        api_key: str = RAGFLOW_API_KEY,
        confidence_threshold: float = RAGFLOW_CONFIDENCE_THRESHOLD,
    ):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.confidence_threshold = confidence_threshold
        self.session = requests.Session()

        if self.api_key:
            self.session.headers.update({"X-API-Key": self.api_key})

    def _request(
        self, method: str, endpoint: str, max_retries: int = 3, **kwargs
    ) -> requests.Response:
        """
        Make HTTP request with retry logic and specific error handling.

        T047: Retry logic with exponential backoff.
        T058: Specific HTTP status error handling.

        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint path
            max_retries: Maximum number of retry attempts (default: 3)
            **kwargs: Additional arguments passed to requests

        Returns:
            requests.Response object

        Raises:
            RuntimeError: With specific error message based on HTTP status
        """
        url = f"{self.api_url}{endpoint}"
        last_exception = None

        for attempt in range(max_retries):
            try:
                response = self.session.request(method, url, **kwargs)

                # Handle specific HTTP status codes with actionable messages
                if response.status_code == 400:
                    raise RuntimeError(
                        f"RAGFlow API bad request (400): Invalid request parameters. "
                        f"Endpoint: {endpoint}. Check your request format and parameters."
                    )
                elif response.status_code == 401:
                    raise RuntimeError(
                        f"RAGFlow API authentication failed (401): Invalid or missing API key. "
                        f"Check MADEINOZ_KNOWLEDGE_RAGFLOW_API_KEY environment variable."
                    )
                elif response.status_code == 403:
                    raise RuntimeError(
                        f"RAGFlow API forbidden (403): Insufficient permissions. "
                        f"Your API key may not have access to this resource."
                    )
                elif response.status_code == 404:
                    raise RuntimeError(
                        f"RAGFlow API not found (404): Resource does not exist. "
                        f"Endpoint: {endpoint}. Verify the resource ID is correct."
                    )
                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    retry_after = int(response.headers.get("Retry-After", 5))
                    logger.warning(f"RAGFlow rate limited (429), waiting {retry_after}s")
                    time.sleep(retry_after)
                    last_exception = Exception("Rate limited")
                    continue
                elif response.status_code >= 500:
                    # Server error - retry with exponential backoff
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                        logger.warning(
                            f"RAGFlow server error ({response.status_code}), "
                            f"retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(wait_time)
                        last_exception = Exception(f"Server error {response.status_code}")
                        continue
                    else:
                        raise RuntimeError(
                            f"RAGFlow API server error ({response.status_code}): "
                            f"Service may be temporarily unavailable. "
                            f"Check RAGFlow service logs for details."
                        )

                # Success for other status codes
                response.raise_for_status()
                return response

            except requests.RequestException as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"RAGFlow request failed (attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"RAGFlow request failed after {max_retries} attempts: {e}")

        # All retries exhausted
        raise RuntimeError(
            f"RAGFlow API request failed after {max_retries} attempts. "
            f"Check that RAGFlow service is running and accessible at {self.api_url}. "
            f"Original error: {last_exception}"
        ) from last_exception

    def upload_document(
        self, file_path: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload and index a document to RAGFlow.

        Args:
            file_path: Path to the document file
            metadata: Optional document metadata for classification

        Returns:
            Dictionary with doc_id and status

        Raises:
            IOError: If file cannot be read
            requests.RequestException: If upload fails
        """
        try:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}

                data = {}
                if metadata:
                    data["metadata"] = metadata

                response = self._request("POST", "/api/v1/documents", files=files, data=data)
                return response.json()

        except FileNotFoundError as e:
            logger.error(f"File not found: {file_path}")
            raise IOError(
                f"File not found: {file_path}. Verify the file path is correct "
                f"and the file exists."
            ) from e

    def search(
        self,
        query: str,
        filters: Optional[Dict[str, str]] = None,
        top_k: int = 10,
    ) -> List[SearchResult]:
        """
        Semantic search in RAGFlow.

        Args:
            query: Natural language search query
            filters: Optional search filters (domain, type, component, etc.)
            top_k: Maximum number of results (1-100)

        Returns:
            List of search results filtered by confidence threshold

        Raises:
            requests.RequestException: If search fails
        """
        params = {"query": query, "top_k": min(top_k, 100)}

        if filters:
            params.update({k: v for k, v in filters.items() if v is not None})

        import time
        start_time = time.time()
        response = self._request("GET", "/api/v1/search", params=params)
        latency_ms = (time.time() - start_time) * 1000

        # Performance target: <500ms search latency (FR-036a)
        # Log warning if target exceeded for monitoring
        if latency_ms > 500:
            logger.warning(
                f"RAGFlow search latency: {latency_ms:.0f}ms "
                f"(target: <500ms - investigate RAGFlow performance)"
            )

        results_data = response.json()
        results = [SearchResult.from_dict(r) for r in results_data]

        # Filter by confidence threshold
        filtered = [r for r in results if r.confidence >= self.confidence_threshold]

        logger.info(f"Search returned {len(filtered)} results (filtered from {len(results)})")
        return filtered

    def get_chunk(self, chunk_id: str) -> Dict[str, Any]:
        """
        Get exact document chunk by ID.

        Args:
            chunk_id: Unique chunk identifier

        Returns:
            Chunk data as dictionary

        Raises:
            requests.RequestException: If retrieval fails
        """
        response = self._request("GET", f"/api/v1/documents/{chunk_id}")
        return response.json()

    def delete_document(self, doc_id: str) -> Dict[str, bool]:
        """
        Delete a document from RAGFlow.

        Args:
            doc_id: Document identifier to delete

        Returns:
            Success status

        Raises:
            requests.RequestException: If deletion fails
        """
        response = self._request("DELETE", f"/api/v1/documents/{doc_id}")
        return response.json()

    def list_documents(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List all ingested documents.

        Args:
            limit: Maximum number of documents to return

        Returns:
            List of document summaries

        Raises:
            requests.RequestException: If listing fails
        """
        response = self._request("GET", f"/api/v1/documents?limit={limit}")
        return response.json()

    def health_check(self) -> bool:
        """
        Check if RAGFlow service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            response = self._request("GET", "/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"RAGFlow health check failed: {e}")
            return False


# Singleton instance for module-level access
_client: Optional[RAGFlowClient] = None


def get_ragflow_client() -> RAGFlowClient:
    """Get or create singleton RAGFlow client instance"""
    global _client
    if _client is None:
        _client = RAGFlowClient()
    return _client
