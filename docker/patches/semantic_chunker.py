"""
Semantic Chunker for LKAP (Feature 022, T008)
Local Knowledge Augmentation Platform

Provides intelligent text chunking with:
- Token-aware splitting using tiktoken
- Configurable overlap (default 15%) for context preservation
- Heading-aware chunking for document structure preservation
- Metadata tracking for provenance

Chunk Configuration:
- Min tokens: 512 (default)
- Max tokens: 768 (default)
- Overlap: 10-20% (default 15%)
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

import tiktoken

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """
    Represents a text chunk with metadata for RAG processing.

    Attributes:
        chunk_id: Unique identifier (UUID4)
        text: Chunk text content
        token_count: Number of tokens in chunk (using tiktoken)
        char_start: Character position in source text (inclusive)
        char_end: Character position in source text (exclusive)
        headings: Parent heading hierarchy (H1 > H2 > H3) for context
        metadata: Additional metadata for tracking (source, section info, etc.)
    """
    chunk_id: str
    text: str
    token_count: int
    char_start: int
    char_end: int
    headings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SemanticChunker:
    """
    Intelligent text chunking with token counting and overlap.

    Splits text into chunks of configurable token size with overlap
    to preserve context at boundaries. Supports heading-aware chunking
    to maintain document structure context.

    Token counting uses tiktoken with cl100k_base encoding (compatible
    with OpenAI embeddings).

    Args:
        min_tokens: Minimum tokens per chunk (default: 512)
        max_tokens: Maximum tokens per chunk (default: 768)
        overlap_percent: Overlap between chunks as decimal (default: 0.15 = 15%)

    Raises:
        ValueError: If min_tokens >= max_tokens or overlap_percent out of range [0, 0.5]
    """

    # tiktoken encoding name for OpenAI cl100k_base (used by text-embedding-3-large)
    ENCODING_NAME = "cl100k_base"

    def __init__(
        self,
        min_tokens: int = 512,
        max_tokens: int = 768,
        overlap_percent: float = 0.15,
    ):
        if min_tokens >= max_tokens:
            raise ValueError(f"min_tokens ({min_tokens}) must be less than max_tokens ({max_tokens})")
        if not 0 <= overlap_percent <= 0.5:
            raise ValueError(f"overlap_percent ({overlap_percent}) must be between 0 and 0.5")

        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.overlap_percent = overlap_percent

        # Initialize tiktoken encoder
        try:
            self._tokenizer = tiktoken.get_encodingering(self.ENCODING_NAME)
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize tiktoken encoder '{self.ENCODING_NAME}'. "
                f"Ensure tiktoken is installed and the encoding name is valid. "
                f"Original error: {e}"
            ) from e

        # Calculate overlap in tokens
        self.overlap_tokens = int(max_tokens * overlap_percent)

        logger.debug(
            f"SemanticChunker initialized: min_tokens={min_tokens}, "
            f"max_tokens={max_tokens}, overlap_percent={overlap_percent}, "
            f"overlap_tokens={self.overlap_tokens}"
        )

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        return len(self._tokenizer.encode(text))

    def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """
        Split text into overlapping chunks.

        Chunks are created by splitting at target token boundaries
        with overlap to maintain context. Each chunk includes character
        positions for provenance tracking.

        Args:
            text: Source text to chunk
            metadata: Optional metadata dictionary to attach to all chunks

        Returns:
            List of Chunk objects with text, token_count, positions, and metadata
        """
        if not text:
            return []

        if metadata is None:
            metadata = {}

        chunks: List[Chunk] = []
        char_position = 0
        text_length = len(text)
        chunk_index = 0

        # Target token count (midpoint between min and max)
        target_tokens = (self.min_tokens + self.max_tokens) // 2

        while char_position < text_length:
            # Calculate chunk end position
            chunk_end = self._find_chunk_end(text, char_position, target_tokens)

            # Extract chunk text
            chunk_text = text[char_position:chunk_end]

            # Validate token count
            token_count = self.count_tokens(chunk_text)
            if token_count < self.min_tokens and chunk_end < text_length:
                # Chunk too small and not at end - extend if possible
                chunk_end = self._find_chunk_end(text, char_position, self.max_tokens)
                chunk_text = text[char_position:chunk_end]
                token_count = self.count_tokens(chunk_text)

            # Create chunk
            chunk = Chunk(
                chunk_id=str(uuid.uuid4()),
                text=chunk_text,
                token_count=token_count,
                char_start=char_position,
                char_end=chunk_end,
                headings=[],
                metadata=metadata.copy(),
            )
            chunks.append(chunk)

            # Move position with overlap for context
            char_position = max(char_position + 1, chunk_end - self.overlap_tokens)
            chunk_index += 1

        logger.debug(f"Created {len(chunks)} chunks from {text_length} characters")
        return chunks

    def chunk_with_headings(
        self,
        text: str,
        headings: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        Split text into chunks while preserving heading context.

        Heading hierarchy is included in chunk metadata for provenance
        and context. Headings are prepended to chunk text for embedding
        contextualization (if desired by downstream processing).

        Args:
            text: Source text to chunk
            headings: List of heading strings representing hierarchy (e.g., ["H1", "H2"])
            metadata: Optional metadata dictionary to attach to all chunks

        Returns:
            List of Chunk objects with heading context in metadata
        """
        if metadata is None:
            metadata = {}

        # Create chunks with base method
        chunks = self.chunk(text, metadata)

        # Attach heading hierarchy to each chunk
        for chunk in chunks:
            chunk.headings = headings.copy()
            # Add headings to metadata for downstream access
            chunk.metadata["heading_hierarchy"] = " > ".join(headings)

        logger.debug(f"Added heading context to {len(chunks)} chunks")
        return chunks

    def _find_chunk_end(self, text: str, start: int, target_tokens: int) -> int:
        """
        Find character position for chunk end based on target token count.

        Uses binary search to find position closest to target token count
        without exceeding max_tokens. Prefers sentence/paragraph boundaries
        when possible.

        Args:
            text: Full source text
            start: Starting character position
            target_tokens: Desired token count for this chunk

        Returns:
            Character position for chunk end
        """
        text_length = len(text)
        low = start
        high = min(text_length, start + self.max_tokens * 4)  # Upper bound estimate

        # Binary search for target token count
        best_end = start
        while low <= high:
            mid = (low + high) // 2
            candidate = text[start:mid]
            tokens = self.count_tokens(candidate)

            if tokens <= target_tokens:
                best_end = mid
                low = mid + 1
            else:
                high = mid - 1

        # Try to find natural break point (sentence/paragraph)
        # Look for period, newline, or other delimiters near best_end
        search_start = max(start, best_end - 100)
        search_area = text[search_start:min(best_end + 100, text_length)]

        # Preferred break delimiters
        break_chars = [".", "!", "?", "\n\n", "\n"]

        for break_char in break_chars:
            # Search backwards from best_end
            for i in range(len(search_area) - 1, -1, -1):
                if search_area[i] == break_char:
                    # Found break point - use it if within acceptable range
                    actual_end = search_start + i + 1
                    if actual_end > start:
                        # Verify token count still within bounds
                        tokens = self.count_tokens(text[start:actual_end])
                        if self.min_tokens <= tokens <= self.max_tokens:
                            return actual_end
                    break  # Found first occurrence of this delimiter

        # No good break point found - use best_end
        return best_end

    def contextualize_chunk(self, chunk: Chunk) -> str:
        """
        Contextualize chunk text with heading hierarchy for embedding.

        Prepends heading path to chunk text so embeddings capture
        document structure context. Format: "H1 > H2 > H3: Chunk text"

        Args:
            chunk: Chunk object to contextualize

        Returns:
            Contextualized text string for embedding
        """
        if not chunk.headings:
            return chunk.text

        heading_prefix = " > ".join(chunk.headings) + ": "
        return heading_prefix + chunk.text
