"""
Content Deduplication for LKAP (Feature 023 Enhancement)
RedTeam Gap #GAP-008: Add hash-based deduplication at ingestion.

RAG Book Reference:
"Hash-based deduplication using MD5 or SHA-256 catches exact duplicates at
ingestion time. Store the hash alongside documents; if a new document matches
an existing hash, skip it or create a reference.

For near-duplicates, MinHash with LSH is the industry standard for million-document
collections. For collections under 10,000 documents, brute-force pairwise comparison
is fine."

Architecture:
- Exact duplicate detection: SHA-256 hash of content
- Chunk-level deduplication: Skip chunks with identical text
- Near-duplicate detection: Optional MinHash for fuzzy matching (future)

Environment Variables:
    MADEINOZ_KNOWLEDGE_DEDUP_ENABLED: Enable deduplication (default: true)
    MADEINOZ_KNOWLEDGE_DEDUP_CHUNK_LEVEL: Enable chunk-level dedup (default: true)
    MADEINOZ_KNOWLEDGE_DEDUP_MINHASH_ENABLED: Enable MinHash near-dup (default: false)
    MADEINOZ_KNOWLEDGE_DEDUP_MINHASH_THRESHOLD: Similarity threshold (default: 0.8)
"""

import os
import logging
import hashlib
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Configuration with defaults
DEDUP_ENABLED = os.getenv("MADEINOZ_KNOWLEDGE_DEDUP_ENABLED", "true").lower() == "true"
DEDUP_CHUNK_LEVEL = os.getenv("MADEINOZ_KNOWLEDGE_DEDUP_CHUNK_LEVEL", "true").lower() == "true"
DEDUP_MINHASH_ENABLED = os.getenv("MADEINOZ_KNOWLEDGE_DEDUP_MINHASH_ENABLED", "false").lower() == "true"
DEDUP_MINHASH_THRESHOLD = float(os.getenv("MADEINOZ_KNOWLEDGE_DEDUP_MINHASH_THRESHOLD", "0.8"))


@dataclass
class DeduplicationResult:
    """Result of deduplication check."""
    is_duplicate: bool
    content_hash: str
    duplicate_of: Optional[str] = None  # ID of document/chunk this duplicates
    similarity_score: float = 0.0  # For near-duplicates


def compute_content_hash(text: str) -> str:
    """
    Compute SHA-256 hash of text content.

    Args:
        text: Text content to hash

    Returns:
        Hexadecimal SHA-256 hash string
    """
    # Normalize text: strip whitespace, lowercase for consistent hashing
    normalized = text.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def compute_file_hash(file_path: str, chunk_size: int = 8192) -> str:
    """
    Compute SHA-256 hash of a file.

    Args:
        file_path: Path to file
        chunk_size: Size of chunks to read at a time

    Returns:
        Hexadecimal SHA-256 hash string
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


class ChunkDeduplicator:
    """
    Deduplicates chunks within and across documents.

    Usage:
        dedup = ChunkDeduplicator()
        unique_chunks = dedup.filter_duplicates(chunks)
    """

    def __init__(
        self,
        enabled: bool = DEDUP_CHUNK_LEVEL,
        min_chunk_chars: int = 50,  # Skip very short chunks (noise)
    ):
        """
        Initialize chunk deduplicator.

        Args:
            enabled: Whether deduplication is enabled
            min_chunk_chars: Minimum characters for a chunk to be considered
        """
        self.enabled = enabled
        self.min_chunk_chars = min_chunk_chars
        self._seen_hashes: Set[str] = set()
        self._stats = {
            "total_chunks": 0,
            "duplicates_skipped": 0,
            "unique_kept": 0,
        }

    def reset(self):
        """Reset state for a new ingestion session."""
        self._seen_hashes.clear()
        self._stats = {
            "total_chunks": 0,
            "duplicates_skipped": 0,
            "unique_kept": 0,
        }

    def filter_duplicates(
        self,
        chunks: List[Dict[str, Any]],
        add_hash_metadata: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Filter out duplicate chunks.

        Args:
            chunks: List of chunk dicts with 'text' key
            add_hash_metadata: Whether to add 'content_hash' to metadata

        Returns:
            List of unique chunks with duplicates removed
        """
        if not self.enabled:
            return chunks

        unique_chunks = []

        for chunk in chunks:
            self._stats["total_chunks"] += 1

            text = chunk.get("text", "")

            # Skip very short chunks (likely noise)
            if len(text) < self.min_chunk_chars:
                logger.debug(f"Skipping short chunk ({len(text)} chars)")
                continue

            # Compute content hash
            content_hash = compute_content_hash(text)

            # Check if we've seen this content
            if content_hash in self._seen_hashes:
                self._stats["duplicates_skipped"] += 1
                logger.debug(f"Skipping duplicate chunk (hash: {content_hash[:12]}...)")
                continue

            # Mark as seen
            self._seen_hashes.add(content_hash)
            self._stats["unique_kept"] += 1

            # Add hash to chunk metadata
            if add_hash_metadata:
                chunk["content_hash"] = content_hash

            unique_chunks.append(chunk)

        return unique_chunks

    def get_stats(self) -> Dict[str, int]:
        """Get deduplication statistics."""
        return self._stats.copy()

    def get_seen_hashes(self) -> Set[str]:
        """Get set of seen content hashes."""
        return self._seen_hashes.copy()


class NearDuplicateDetector:
    """
    Near-duplicate detection using MinHash/LSH.

    For collections under 10K documents, simpler approaches work fine.
    This is for larger collections where O(n²) comparison is too slow.

    Future: Implement if DEDUP_MINHASH_ENABLED is true.
    """

    def __init__(
        self,
        enabled: bool = DEDUP_MINHASH_ENABLED,
        threshold: float = DEDUP_MINHASH_THRESHOLD,
    ):
        self.enabled = enabled
        self.threshold = threshold

        if enabled:
            try:
                from datasketch import MinHash, MinHashLSH
                self._minhash_cls = MinHash
                self._lsh = MinHashLSH(threshold=threshold, num_perm=128)
                self._document_hashes = {}  # doc_id -> MinHash
            except ImportError:
                logger.warning("datasketch not installed, MinHash dedup disabled")
                self.enabled = False

    def compute_minhash(self, text: str) -> Any:
        """
        Compute MinHash signature for text.

        Args:
            text: Text to hash

        Returns:
            MinHash object
        """
        if not self.enabled:
            return None

        # Create shingles (3-character n-grams)
        shingles = set()
        for i in range(len(text) - 2):
            shingles.add(text[i:i+3])

        # Create MinHash
        mh = self._minhash_cls(num_perm=128)
        for shingle in shingles:
            mh.update(shingle.encode("utf-8"))

        return mh

    def check_near_duplicate(self, doc_id: str, text: str) -> Tuple[bool, Optional[str]]:
        """
        Check if document is a near-duplicate of existing documents.

        Args:
            doc_id: Document ID
            text: Document text

        Returns:
            Tuple of (is_duplicate, duplicate_of_id)
        """
        if not self.enabled:
            return False, None

        mh = self.compute_minhash(text)

        # Query LSH for similar documents
        similar = self._lsh.query(mh)

        if similar:
            # Return first match (most similar)
            return True, similar[0]

        # Add to index
        self._lsh.insert(doc_id, mh)
        self._document_hashes[doc_id] = mh

        return False, None


class DeduplicationService:
    """
    Main deduplication service combining exact and near-duplicate detection.

    Usage:
        service = DeduplicationService()
        result = await service.check_duplicate(content)
        unique_chunks = service.dedup_chunks(chunks)
    """

    def __init__(
        self,
        enabled: bool = DEDUP_ENABLED,
        chunk_level: bool = DEDUP_CHUNK_LEVEL,
        minhash_enabled: bool = DEDUP_MINHASH_ENABLED,
    ):
        """
        Initialize deduplication service.

        Args:
            enabled: Master enable/disable
            chunk_level: Enable chunk-level deduplication
            minhash_enabled: Enable MinHash near-duplicate detection
        """
        self.enabled = enabled
        self.chunk_dedup = ChunkDeduplicator(enabled=enabled and chunk_level)
        self.near_dup_detector = NearDuplicateDetector(enabled=minhash_enabled)

    def dedup_chunks(
        self,
        chunks: List[Dict[str, Any]],
        reset_session: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Deduplicate chunks within a document.

        Args:
            chunks: List of chunk dicts
            reset_session: Whether to reset dedup state before processing

        Returns:
            List of unique chunks
        """
        if not self.enabled:
            return chunks

        if reset_session:
            self.chunk_dedup.reset()

        return self.chunk_dedup.filter_duplicates(chunks)

    async def check_near_duplicate(self, doc_id: str, text: str) -> DeduplicationResult:
        """
        Check if document is a near-duplicate.

        Args:
            doc_id: Document ID
            text: Document text

        Returns:
            DeduplicationResult with match info
        """
        content_hash = compute_content_hash(text)

        if not self.near_dup_detector.enabled:
            return DeduplicationResult(
                is_duplicate=False,
                content_hash=content_hash,
            )

        is_dup, dup_of = self.near_dup_detector.check_near_duplicate(doc_id, text)

        return DeduplicationResult(
            is_duplicate=is_dup,
            content_hash=content_hash,
            duplicate_of=dup_of,
            similarity_score=0.8 if is_dup else 0.0,  # Approximate
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get deduplication statistics."""
        return {
            "enabled": self.enabled,
            "chunk_stats": self.chunk_dedup.get_stats(),
            "seen_hashes_count": len(self.chunk_dedup.get_seen_hashes()),
        }


# Convenience functions
def dedup_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Quick deduplication of chunks.

    Args:
        chunks: List of chunk dicts with 'text' key

    Returns:
        List of unique chunks
    """
    service = DeduplicationService()
    return service.dedup_chunks(chunks)
