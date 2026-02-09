"""
Chunking Service for LKAP (Feature 022)
Heading-aware chunking using Docling's HybridChunker.

Research Update: Docling does NOT have ChunkingParams.respect_headings.
Heading awareness is built-in via HybridChunker which automatically tracks
document hierarchy (H1 → H2 → H3) and includes heading context in chunks.

Chunk size: 512-768 tokens
Overlap: Handled by HybridChunker merge_peers behavior
Respects: Heading boundaries (automatic via Docling design)
"""

import logging
from typing import List, Dict, Any

from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from transformers import AutoTokenizer

from .lkap_logging import get_logger

logger = get_logger("lkap.chunking")

# Chunking configuration
CHUNK_SIZE_MIN = 512
CHUNK_SIZE_MAX = 768
# Overlap is implicit in HybridChunker's merge_peers behavior

# Tokenizer for chunk size estimation
# Using sentence-transformers model (same embedding model dimensionality)
_TOKENIZER_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _get_tokenizer() -> HuggingFaceTokenizer:
    """Get or create cached tokenizer for chunk size estimation."""
    if not hasattr(_get_tokenizer, "_cached"):
        _get_tokenizer._cached = HuggingFaceTokenizer(
            tokenizer=AutoTokenizer.from_pretrained(_TOKENIZER_MODEL),
            max_tokens=CHUNK_SIZE_MAX,
        )
    return _get_tokenizer._cached


def create_hybrid_chunker() -> HybridChunker:
    """
    Create Docling HybridChunker for token-aware, heading-aware chunking.

    HybridChunker provides:
    - Token-aware chunking (respects max_tokens limit)
    - Automatic heading hierarchy tracking (H1 → H2 → H3)
    - Merge behavior for undersized chunks with same heading context
    - Chunk metadata includes parent headings via chunk.meta.headings

    Returns:
        Configured HybridChunker instance
    """
    tokenizer = _get_tokenizer()

    return HybridChunker(
        tokenizer=tokenizer,
        merge_peers=True,  # Merge undersized chunks with same headings
    )


def chunk_document(
    docling_doc,
    text_content: str = None,
) -> List[Dict[str, Any]]:
    """
    Chunk a document using Docling's heading-aware HybridChunker.

    Args:
        docling_doc: Docling parsed document (or file path to convert)
        text_content: Optional text content (if doc is already converted)

    Returns:
        List of chunk dictionaries with text, position, token_count, headings

    Heading Awareness:
        - Docling automatically tracks document hierarchy during traversal
        - Each chunk includes chunk.meta.headings list with parent headings
        - Chunks under same heading can be merged (merge_peers=True)
        - Heading hierarchy: H1 (level 0) → H2 (level 1) → H3 (level 2)

    Research Decision RT-002: Heading-aware chunking maintains semantic coherence.
    """
    chunker = create_hybrid_chunker()

    # Convert document if file path provided
    if isinstance(docling_doc, str):
        converter = DocumentConverter()
        result = converter.convert(docling_doc)
        doc = result.document
    elif text_content:
        # If text_content provided but doc is not converted, we need to handle this
        # For now, assume doc is already a DLDocument
        doc = docling_doc
    else:
        doc = docling_doc

    # Chunk using HybridChunker
    chunks = []
    for i, chunk in enumerate(chunker.chunk(dl_doc=doc)):
        # Extract heading context from metadata
        headings = chunk.meta.headings if hasattr(chunk.meta, "headings") else []

        # Token count estimation (actual count depends on tokenizer)
        token_count = len(chunk.text.split())  # Simple approximation

        chunks.append({
            "text": chunk.text,
            "position": i,
            "token_count": token_count,
            "headings": headings,  # List of parent headings for provenance
        })

    logger.info(f"Document chunked into {len(chunks)} chunks with heading context")
    return chunks


def contextualize_chunk(chunk: Dict[str, Any]) -> str:
    """
    Contextualize chunk text with heading prefixes for embedding.

    This prepends heading hierarchy to chunk text so embeddings capture
    the section context. Useful for semantic search.

    Args:
        chunk: Chunk dictionary with text and headings

    Returns:
        Contextualized text with heading prefixes

    Example:
        Input chunk text: "The GPIO port supports..."
        Headings: ["Embedded Systems", "GPIO Configuration"]
        Output: "Embedded Systems > GPIO Configuration: The GPIO port supports..."
    """
    if not chunk.get("headings"):
        return chunk["text"]

    # Join headings with " > " separator
    heading_prefix = " > ".join(chunk["headings"])
    return f"{heading_prefix}: {chunk['text']}"
