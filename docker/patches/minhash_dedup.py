"""
MinHash Near-Duplicate Detection for LKAP (Feature 023 Enhancement)
RedTeam Gap #GAP-008b: Add MinHash near-duplicate detection.

RAG Book Reference:
"Five copies of the same doc crowding out diverse sources"
"Near-duplicates pollute retrieval, create false consensus"

MinHash with Locality-Sensitive Hashing (LSH) detects chunks that are
semantically similar but not exact duplicates. Uses Jaccard similarity
on character n-grams (shingles).

When to use:
- After hash-based dedup catches exact duplicates
- When corpus may have rephrased/slightly modified content
- When dedup threshold needs tuning (0.85-0.95 typical)

Environment Variables:
    MADEINOZ_KNOWLEDGE_MINHASH_ENABLED: Enable MinHash dedup (default: true)
    MADEINOZ_KNOWLEDGE_MINHASH_THRESHOLD: Jaccard similarity threshold (default: 0.85)
    MADEINOZ_KNOWLEDGE_MINHASH_NUM_PERM: Number of permutations (default: 128)
"""

import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Configuration with defaults
MINHASH_ENABLED = os.getenv("MADEINOZ_KNOWLEDGE_MINHASH_ENABLED", "true").lower() == "true"
MINHASH_THRESHOLD = float(os.getenv("MADEINOZ_KNOWLEDGE_MINHASH_THRESHOLD", "0.85"))
MINHASH_NUM_PERM = int(os.getenv("MADEINOZ_KNOWLEDGE_MINHASH_NUM_PERM", "128"))

# Default shingle size (character n-grams)
DEFAULT_SHINGLE_SIZE = 3


@dataclass
class NearDuplicate:
    """Represents a near-duplicate pair."""
    chunk_id_1: str
    chunk_id_2: str
    similarity: float
    text_preview_1: str
    text_preview_2: str


class ShingleGenerator:
    """
    Generates character n-grams (shingles) from text.

    Shingles are more robust than word tokens for near-duplicate detection
    because they capture character-level patterns.
    """

    def __init__(self, k: int = DEFAULT_SHINGLE_SIZE):
        """
        Initialize shingle generator.

        Args:
            k: Size of character n-grams
        """
        self.k = k

    def generate(self, text: str) -> Set[str]:
        """
        Generate set of shingles from text.

        Args:
            text: Input text

        Returns:
            Set of k-character shingles
        """
        # Normalize text: lowercase, remove extra whitespace
        text = re.sub(r"\s+", " ", text.lower().strip())

        if len(text) < self.k:
            return {text} if text else set()

        shingles = set()
        for i in range(len(text) - self.k + 1):
            shingles.add(text[i:i + self.k])

        return shingles


class MinHash:
    """
    MinHash signature generator.

    MinHash creates a compact signature that approximates Jaccard similarity.
    The signature is created by computing minimum hash values across multiple
    hash functions.
    """

    # Large prime for hash functions
    MAX_HASH = (1 << 32) - 1
    PRIME = 4294967311  # Prime larger than MAX_HASH

    def __init__(self, num_perm: int = MINHASH_NUM_PERM, seed: int = 42):
        """
        Initialize MinHash.

        Args:
            num_perm: Number of permutations (hash functions)
            seed: Random seed for reproducibility
        """
        self.num_perm = num_perm
        self.seed = seed

        # Generate hash function coefficients
        # Each hash function: h(x) = (a * x + b) mod p mod MAX_HASH
        import random
        random.seed(seed)
        self.a = [random.randint(1, self.PRIME - 1) for _ in range(num_perm)]
        self.b = [random.randint(0, self.PRIME - 1) for _ in range(num_perm)]

    def create_signature(self, shingles: Set[str]) -> List[int]:
        """
        Create MinHash signature from shingles.

        Args:
            shingles: Set of shingles

        Returns:
            List of minimum hash values (signature)
        """
        if not shingles:
            return [self.MAX_HASH] * self.num_perm

        # Initialize signature with max values
        signature = [self.MAX_HASH] * self.num_perm

        # For each shingle, compute hashes and track minimums
        for shingle in shingles:
            # Hash the shingle to an integer
            shingle_hash = hash(shingle) & self.MAX_HASH

            # Apply each hash function
            for i in range(self.num_perm):
                h = (self.a[i] * shingle_hash + self.b[i]) % self.PRIME % self.MAX_HASH
                if h < signature[i]:
                    signature[i] = h

        return signature

    def jaccard_similarity(self, sig1: List[int], sig2: List[int]) -> float:
        """
        Estimate Jaccard similarity from MinHash signatures.

        Args:
            sig1: First signature
            sig2: Second signature

        Returns:
            Estimated Jaccard similarity (0-1)
        """
        if len(sig1) != len(sig2):
            raise ValueError("Signatures must have same length")

        if not sig1:
            return 0.0

        matches = sum(1 for a, b in zip(sig1, sig2) if a == b)
        return matches / len(sig1)


class MinHashLSH:
    """
    Locality-Sensitive Hashing for MinHash.

    LSH enables efficient approximate nearest neighbor search by dividing
    the signature into bands and hashing each band.
    """

    def __init__(
        self,
        num_perm: int = MINHASH_NUM_PERM,
        num_bands: int = 16,
        rows_per_band: int = 8,
    ):
        """
        Initialize LSH index.

        Args:
            num_perm: Number of permutations in MinHash
            num_bands: Number of bands to divide signature into
            rows_per_band: Rows per band (num_perm should equal num_bands * rows_per_band)
        """
        self.num_perm = num_perm
        self.num_bands = num_bands
        self.rows_per_band = rows_per_band

        # Verify dimensions match
        if num_perm != num_bands * rows_per_band:
            # Adjust rows_per_band
            self.rows_per_band = num_perm // num_bands
            logger.info(f"Adjusted rows_per_band to {self.rows_per_band}")

        # Index: band_hash -> set of chunk_ids
        self.index: Dict[int, Set[str]] = {}

        # Store signatures for similarity computation
        self.signatures: Dict[str, List[int]] = {}

    def _hash_band(self, band: List[int]) -> int:
        """Hash a band of the signature."""
        return hash(tuple(band))

    def add(self, chunk_id: str, signature: List[int]) -> None:
        """
        Add a signature to the LSH index.

        Args:
            chunk_id: Unique identifier for the chunk
            signature: MinHash signature
        """
        self.signatures[chunk_id] = signature

        # Add to each band
        for i in range(self.num_bands):
            start = i * self.rows_per_band
            end = start + self.rows_per_band
            band = tuple(signature[start:end])
            band_hash = self._hash_band(list(band))

            if band_hash not in self.index:
                self.index[band_hash] = set()
            self.index[band_hash].add(chunk_id)

    def query(self, signature: List[int]) -> Set[str]:
        """
        Find candidate duplicates for a signature.

        Args:
            signature: MinHash signature to query

        Returns:
            Set of candidate chunk_ids that might be similar
        """
        candidates = set()

        for i in range(self.num_bands):
            start = i * self.rows_per_band
            end = start + self.rows_per_band
            band = tuple(signature[start:end])
            band_hash = self._hash_band(list(band))

            if band_hash in self.index:
                candidates.update(self.index[band_hash])

        return candidates


class MinHashDeduplicator:
    """
    Main class for MinHash-based near-duplicate detection.

    Usage:
        dedup = MinHashDeduplicator(threshold=0.85)
        dedup.add_chunk("chunk_1", "This is some text content")
        dedup.add_chunk("chunk_2", "This is some text contents")  # Near-duplicate

        duplicates = dedup.find_duplicates()
    """

    def __init__(
        self,
        enabled: bool = MINHASH_ENABLED,
        threshold: float = MINHASH_THRESHOLD,
        num_perm: int = MINHASH_NUM_PERM,
        shingle_size: int = DEFAULT_SHINGLE_SIZE,
    ):
        """
        Initialize MinHash deduplicator.

        Args:
            enabled: Whether MinHash dedup is enabled
            threshold: Jaccard similarity threshold for duplicates
            num_perm: Number of MinHash permutations
            shingle_size: Character n-gram size
        """
        self.enabled = enabled
        self.threshold = threshold
        self.num_perm = num_perm

        self.shingler = ShingleGenerator(k=shingle_size)
        self.minhash = MinHash(num_perm=num_perm)
        self.lsh = MinHashLSH(num_perm=num_perm)

        # Store chunk texts for preview
        self.chunk_texts: Dict[str, str] = {}

        # Stats
        self._chunks_processed = 0
        self._duplicates_found = 0

    def add_chunk(self, chunk_id: str, text: str) -> None:
        """
        Add a chunk to the deduplication index.

        Args:
            chunk_id: Unique identifier
            text: Chunk text content
        """
        if not self.enabled:
            return

        shingles = self.shingler.generate(text)
        signature = self.minhash.create_signature(shingles)

        self.lsh.add(chunk_id, signature)
        self.chunk_texts[chunk_id] = text
        self._chunks_processed += 1

    def find_duplicates(self, chunk_id: str) -> List[NearDuplicate]:
        """
        Find near-duplicates for a specific chunk.

        Args:
            chunk_id: Chunk to check for duplicates

        Returns:
            List of NearDuplicate objects
        """
        if not self.enabled:
            return []

        if chunk_id not in self.lsh.signatures:
            return []

        signature = self.lsh.signatures[chunk_id]
        text = self.chunk_texts.get(chunk_id, "")

        # Get candidates from LSH
        candidates = self.lsh.query(signature)

        duplicates = []
        for candidate_id in candidates:
            if candidate_id == chunk_id:
                continue

            # Compute exact similarity
            candidate_sig = self.lsh.signatures.get(candidate_id)
            if candidate_sig is None:
                continue

            similarity = self.minhash.jaccard_similarity(signature, candidate_sig)

            if similarity >= self.threshold:
                candidate_text = self.chunk_texts.get(candidate_id, "")
                duplicate = NearDuplicate(
                    chunk_id_1=chunk_id,
                    chunk_id_2=candidate_id,
                    similarity=similarity,
                    text_preview_1=text[:100] + "..." if len(text) > 100 else text,
                    text_preview_2=candidate_text[:100] + "..." if len(candidate_text) > 100 else candidate_text,
                )
                duplicates.append(duplicate)
                self._duplicates_found += 1

        # Sort by similarity descending
        duplicates.sort(key=lambda x: x.similarity, reverse=True)
        return duplicates

    def find_all_duplicates(self) -> List[NearDuplicate]:
        """
        Find all near-duplicate pairs in the index.

        Returns:
            List of all NearDuplicate pairs
        """
        if not self.enabled:
            return []

        all_duplicates = []
        seen_pairs: Set[Tuple[str, str]] = set()

        for chunk_id in list(self.lsh.signatures.keys()):
            duplicates = self.find_duplicates(chunk_id)

            for dup in duplicates:
                # Create ordered pair to avoid duplicates
                pair = tuple(sorted([dup.chunk_id_1, dup.chunk_id_2]))
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    all_duplicates.append(dup)

        return all_duplicates

    def filter_duplicates(
        self,
        chunks: List[Dict[str, Any]],
        text_key: str = "text",
        id_key: str = "chunk_id",
    ) -> List[Dict[str, Any]]:
        """
        Filter out near-duplicate chunks.

        Args:
            chunks: List of chunk dictionaries
            text_key: Key for text content
            id_key: Key for chunk ID

        Returns:
            Filtered list with duplicates removed
        """
        if not self.enabled:
            return chunks

        # Build index
        for chunk in chunks:
            chunk_id = chunk.get(id_key, str(hash(chunk.get(text_key, ""))))
            text = chunk.get(text_key, "")
            self.add_chunk(chunk_id, text)

        # Find all duplicates
        all_dups = self.find_all_duplicates()

        # Determine which chunks to remove (keep the first one in each pair)
        to_remove: Set[str] = set()
        for dup in all_dups:
            # Keep chunk_id_1, remove chunk_id_2
            to_remove.add(dup.chunk_id_2)

        # Filter chunks
        filtered = []
        for chunk in chunks:
            chunk_id = chunk.get(id_key, str(hash(chunk.get(text_key, ""))))
            if chunk_id not in to_remove:
                chunk["_minhash_checked"] = True
                chunk["_near_duplicate"] = False
                filtered.append(chunk)

        logger.info(
            f"MinHash dedup: {len(chunks)} chunks -> {len(filtered)} "
            f"({len(to_remove)} near-duplicates removed)"
        )

        return filtered

    def get_stats(self) -> Dict[str, Any]:
        """Get deduplication statistics."""
        return {
            "enabled": self.enabled,
            "threshold": self.threshold,
            "num_permutations": self.num_perm,
            "chunks_processed": self._chunks_processed,
            "duplicates_found": self._duplicates_found,
            "index_size": len(self.lsh.signatures),
        }


# Convenience functions
def check_near_duplicate(
    text1: str,
    text2: str,
    threshold: float = MINHASH_THRESHOLD,
) -> Tuple[bool, float]:
    """
    Quick check if two texts are near-duplicates.

    Args:
        text1: First text
        text2: Second text
        threshold: Similarity threshold

    Returns:
        Tuple of (is_duplicate, similarity_score)
    """
    shingler = ShingleGenerator()
    minhash = MinHash()

    sig1 = minhash.create_signature(shingler.generate(text1))
    sig2 = minhash.create_signature(shingler.generate(text2))

    similarity = minhash.jaccard_similarity(sig1, sig2)
    return similarity >= threshold, similarity


def compute_jaccard(text1: str, text2: str) -> float:
    """
    Compute exact Jaccard similarity between two texts.

    Args:
        text1: First text
        text2: Second text

    Returns:
        Jaccard similarity (0-1)
    """
    shingler = ShingleGenerator()
    s1 = shingler.generate(text1)
    s2 = shingler.generate(text2)

    if not s1 or not s2:
        return 0.0

    intersection = len(s1 & s2)
    union = len(s1 | s2)

    return intersection / union if union > 0 else 0.0
