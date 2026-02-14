"""
Docling Document Ingester (Feature 023)
Qdrant RAG Migration

Ingests PDF and markdown documents into Qdrant with:
- Docling for PDF parsing with table extraction
- Semantic chunking with heading awareness
- Ollama embeddings with bge-large-en-v1.5
- Idempotent ingestion via document hash
"""

import hashlib
import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from docling.chunking import HybridChunker
from docling.document_converter import DocumentConverter

from patches.lkap_models import (
    Document,
    DocumentChunk,
    DocumentType,
    Domain,
    IngestionResult,
    IngestionStatus,
    Sensitivity,
)
from patches.ollama_embedder import get_ollama_embedder
from patches.semantic_chunker import SemanticChunker

logger = logging.getLogger(__name__)


@dataclass
class IngestionConfig:
    """Configuration for document ingestion"""
    inbox_path: str = "knowledge/inbox"
    processed_path: str = "knowledge/processed"
    min_tokens: int = 512
    max_tokens: int = 768
    overlap_percent: float = 0.15
    batch_size: int = 32
    confidence_threshold: float = 0.70


class DoclingIngester:
    """
    Document ingester using Docling parser and Qdrant storage.

    T018-T025: Implements document ingestion pipeline:
    - T018: PDF parsing with table extraction
    - T019: Markdown parsing with heading awareness
    - T020: Plain text parsing
    - T021: Ingest orchestration (parse → chunk → embed → store)
    - T022: Idempotent ingestion via document hash
    - T023: Document move from inbox/ to processed/
    - T024: Error handling with rollback
    - T025: Progress logging
    """

    def __init__(
        self,
        qdrant_client: Any,
        config: Optional[IngestionConfig] = None,
    ):
        """
        Initialize DoclingIngester.

        Args:
            qdrant_client: QdrantClient instance for storage
            config: Optional ingestion configuration
        """
        self.qdrant_client = qdrant_client
        self.config = config or IngestionConfig()
        self.docling_converter = DocumentConverter()
        self.chunker = SemanticChunker(
            min_tokens=self.config.min_tokens,
            max_tokens=self.config.max_tokens,
            overlap_percent=self.config.overlap_percent,
        )
        self.embedder = get_ollama_embedder()

        # Ensure directories exist
        Path(self.config.inbox_path).mkdir(parents=True, exist_ok=True)
        Path(self.config.processed_path).mkdir(parents=True, exist_ok=True)

    def compute_document_hash(self, file_path: Path) -> str:
        """
        Compute SHA-256 hash of document for idempotency check.

        T022: Idempotent ingestion - skip already processed documents.

        Args:
            file_path: Path to the document file

        Returns:
            SHA-256 hash string
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    async def check_document_exists(self, doc_hash: str) -> bool:
        """
        Check if document already exists in Qdrant.

        T022: Idempotent check by document hash.

        Args:
            doc_hash: SHA-256 hash of document

        Returns:
            True if document already ingested
        """
        try:
            # Check Qdrant for existing document with this hash
            result = await self.qdrant_client.scroll(
                collection_name=self.qdrant_client.collection_name,
                scroll_filter={
                    "must": [
                        {"key": "doc_hash", "match": {"value": doc_hash}}
                    ]
                },
                limit=1,
            )
            return len(result.get("points", [])) > 0
        except Exception as e:
            logger.warning(f"Failed to check document existence: {e}")
            return False

    def parse_pdf(self, file_path: Path) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Parse PDF document using Docling with table extraction.

        T018: PDF parsing with Docling.

        Args:
            file_path: Path to PDF file

        Returns:
            Tuple of (full_text, list of chunk dicts with metadata)
        """
        logger.info(f"Parsing PDF: {file_path}")

        result = self.docling_converter.convert(str(file_path))

        # Export to markdown format for text
        markdown_text = result.document.export_to_markdown()

        # Get structured chunks from Docling
        chunker = HybridChunker()
        docling_chunks = list(chunker.chunk(result.document))

        chunks = []
        for i, chunk in enumerate(docling_chunks):
            headings = []
            if hasattr(chunk, "meta") and hasattr(chunk.meta, "headings"):
                headings = list(chunk.meta.headings)

            chunks.append({
                "text": chunk.text,
                "position": i,
                "headings": headings,
                "page_section": getattr(chunk.meta, "page_no", None) if hasattr(chunk, "meta") else None,
            })

        logger.info(f"Parsed PDF into {len(chunks)} chunks")
        return markdown_text, chunks

    def parse_markdown(self, file_path: Path) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Parse markdown document with heading awareness.

        T019: Markdown parsing with heading extraction.

        Args:
            file_path: Path to markdown file

        Returns:
            Tuple of (full_text, list of chunk dicts with metadata)
        """
        logger.info(f"Parsing markdown: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        # Use semantic chunker for markdown
        chunks = self.chunker.chunk_with_headings(text)

        chunk_dicts = []
        for i, chunk in enumerate(chunks):
            chunk_dicts.append({
                "text": chunk.text,
                "position": i,
                "headings": chunk.headings,
                "page_section": None,
                "token_count": chunk.token_count,
            })

        logger.info(f"Parsed markdown into {len(chunk_dicts)} chunks")
        return text, chunk_dicts

    def parse_text(self, file_path: Path) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Parse plain text document.

        T020: Plain text parsing.

        Args:
            file_path: Path to text file

        Returns:
            Tuple of (full_text, list of chunk dicts with metadata)
        """
        logger.info(f"Parsing text: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        # Use semantic chunker for plain text
        chunks = self.chunker.chunk(text)

        chunk_dicts = []
        for i, chunk in enumerate(chunks):
            chunk_dicts.append({
                "text": chunk.text,
                "position": i,
                "headings": [],
                "page_section": None,
                "token_count": chunk.token_count,
            })

        logger.info(f"Parsed text into {len(chunk_dicts)} chunks")
        return text, chunk_dicts

    def detect_document_type(self, file_path: Path) -> DocumentType:
        """Detect document type from file extension."""
        suffix = file_path.suffix.lower()
        type_map = {
            ".pdf": DocumentType.PDF,
            ".md": DocumentType.MARKDOWN,
            ".markdown": DocumentType.MARKDOWN,
            ".txt": DocumentType.TEXT,
            ".html": DocumentType.HTML,
            ".htm": DocumentType.HTML,
        }
        return type_map.get(suffix, DocumentType.TEXT)

    def classify_domain(self, filename: str, text_sample: str) -> Domain:
        """
        Classify document domain from filename and content.

        Uses heuristics for common patterns.
        """
        filename_lower = filename.lower()
        text_lower = text_sample.lower()[:2000]  # First 2000 chars

        # Embedded/STM32 patterns
        if any(kw in filename_lower for kw in ["stm32", "hal", "cube", "mcu", "gpio", "uart", "spi", "i2c"]):
            return Domain.EMBEDDED
        if any(kw in text_lower for kw in ["stm32", "gpio configuration", "register", "peripheral"]):
            return Domain.EMBEDDED

        # Security patterns
        if any(kw in filename_lower for kw in ["security", "cve", "vulnerability", "threat", "attack"]):
            return Domain.SECURITY
        if any(kw in text_lower for kw in ["vulnerability", "exploit", "attack vector", "cve-"]):
            return Domain.SECURITY

        # Cloud patterns
        if any(kw in filename_lower for kw in ["aws", "azure", "gcp", "cloud", "kubernetes", "k8s"]):
            return Domain.CLOUD
        if any(kw in text_lower for kw in ["aws::", "azure", "gcp", "kubernetes", "terraform"]):
            return Domain.CLOUD

        # Standards patterns
        if any(kw in filename_lower for kw in ["iso", "iec", "ieee", "standard", "specification"]):
            return Domain.STANDARDS
        if any(kw in text_lower for kw in ["iso/", "iec/", "ieee std"]):
            return Domain.STANDARDS

        return Domain.SOFTWARE

    async def store_chunks(
        self,
        doc_id: str,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        metadata: Dict[str, Any],
    ) -> int:
        """
        Store chunks with embeddings in Qdrant.

        Args:
            doc_id: Document identifier
            chunks: List of chunk dictionaries
            embeddings: List of embedding vectors
            metadata: Document-level metadata

        Returns:
            Number of chunks stored
        """
        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{doc_id}_chunk_{i}"
            point = {
                "id": chunk_id,
                "vector": embedding,
                "payload": {
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "text": chunk["text"],
                    "position": chunk["position"],
                    "token_count": chunk.get("token_count", 0),
                    "headings": chunk.get("headings", []),
                    "page_section": chunk.get("page_section"),
                    "domain": metadata.get("domain", "software"),
                    "project": metadata.get("project", ""),
                    "component": metadata.get("component", ""),
                    "type": metadata.get("type", "text"),
                    "source": metadata.get("filename", ""),
                    "doc_hash": metadata.get("doc_hash", ""),
                    "created_at": datetime.now().isoformat(),
                }
            }
            points.append(point)

        # Batch upsert to Qdrant
        await self.qdrant_client.upsert(
            collection_name=self.qdrant_client.collection_name,
            points=points,
        )

        return len(points)

    async def ingest(self, file_path: Path) -> IngestionResult:
        """
        Ingest a document: parse → chunk → embed → store.

        T021: Orchestrates the full ingestion pipeline.

        Args:
            file_path: Path to document file

        Returns:
            IngestionResult with status and metadata
        """
        start_time = time.time()
        filename = file_path.name

        logger.info(f"Starting ingestion: {filename}")

        try:
            # T022: Idempotency check
            doc_hash = self.compute_document_hash(file_path)
            if await self.check_document_exists(doc_hash):
                logger.info(f"Document already exists (hash: {doc_hash[:12]}...), skipping")
                return IngestionResult(
                    doc_id=doc_hash[:36],  # Use hash prefix as ID
                    chunk_count=0,
                    status=IngestionStatus.COMPLETED,
                    error_message=None,
                    filename=filename,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                )

            # Generate document ID
            import uuid
            doc_id = str(uuid.uuid4())

            # T025: Progress logging
            logger.info(f"[1/4] Parsing document: {filename}")

            # Parse based on document type
            doc_type = self.detect_document_type(file_path)
            if doc_type == DocumentType.PDF:
                full_text, chunks = self.parse_pdf(file_path)
            elif doc_type == DocumentType.MARKDOWN:
                full_text, chunks = self.parse_markdown(file_path)
            else:
                full_text, chunks = self.parse_text(file_path)

            if not chunks:
                logger.warning(f"No chunks extracted from {filename}")
                return IngestionResult(
                    doc_id=doc_id,
                    chunk_count=0,
                    status=IngestionStatus.FAILED,
                    error_message="No chunks extracted from document",
                    filename=filename,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                )

            # T025: Progress logging
            logger.info(f"[2/4] Generating embeddings for {len(chunks)} chunks")

            # Generate embeddings in batches
            all_embeddings = []
            batch_texts = [c["text"] for c in chunks]

            for i in range(0, len(batch_texts), self.config.batch_size):
                batch = batch_texts[i:i + self.config.batch_size]
                embeddings = await self.embedder.embed_batch(batch)
                all_embeddings.extend(embeddings)
                logger.debug(f"Generated embeddings for batch {i//self.config.batch_size + 1}")

            # T025: Progress logging
            logger.info(f"[3/4] Classifying and storing chunks")

            # Classify domain
            domain = self.classify_domain(filename, full_text)

            # Prepare metadata
            metadata = {
                "filename": filename,
                "doc_hash": doc_hash,
                "domain": domain.value,
                "type": doc_type.value,
                "project": "",
                "component": "",
            }

            # Store in Qdrant
            stored_count = await self.store_chunks(doc_id, chunks, all_embeddings, metadata)

            # T025: Progress logging
            logger.info(f"[4/4] Moving document to processed/")

            # T023: Move from inbox to processed
            processed_path = Path(self.config.processed_path) / filename
            shutil.move(str(file_path), str(processed_path))

            processing_time = int((time.time() - start_time) * 1000)

            logger.info(f"Ingestion complete: {filename} -> {stored_count} chunks ({processing_time}ms)")

            return IngestionResult(
                doc_id=doc_id,
                chunk_count=stored_count,
                status=IngestionStatus.COMPLETED,
                error_message=None,
                filename=filename,
                processing_time_ms=processing_time,
            )

        except Exception as e:
            # T024: Error handling
            logger.error(f"Ingestion failed for {filename}: {e}")

            # T024: Rollback - document stays in inbox for retry
            processing_time = int((time.time() - start_time) * 1000)

            return IngestionResult(
                doc_id="",
                chunk_count=0,
                status=IngestionStatus.FAILED,
                error_message=str(e),
                filename=filename,
                processing_time_ms=processing_time,
            )

    async def ingest_directory(self, directory: Optional[Path] = None) -> List[IngestionResult]:
        """
        Ingest all documents in a directory.

        Args:
            directory: Directory to scan (defaults to inbox path)

        Returns:
            List of IngestionResult for each document
        """
        dir_path = Path(directory or self.config.inbox_path)

        if not dir_path.exists():
            logger.warning(f"Directory does not exist: {dir_path}")
            return []

        # Find all supported documents
        supported_extensions = {".pdf", ".md", ".markdown", ".txt", ".html", ".htm"}
        files = [
            f for f in dir_path.iterdir()
            if f.is_file() and f.suffix.lower() in supported_extensions
        ]

        if not files:
            logger.info(f"No supported documents found in {dir_path}")
            return []

        logger.info(f"Found {len(files)} documents to ingest")

        results = []
        for file_path in files:
            result = await self.ingest(file_path)
            results.append(result)

        # Summary logging
        successful = sum(1 for r in results if r.status == IngestionStatus.COMPLETED)
        failed = sum(1 for r in results if r.status == IngestionStatus.FAILED)
        total_chunks = sum(r.chunk_count for r in results)

        logger.info(f"Batch ingestion complete: {successful} succeeded, {failed} failed, {total_chunks} total chunks")

        return results


# Factory function
_ingester: Optional[DoclingIngester] = None


def get_docling_ingester(qdrant_client: Any, config: Optional[IngestionConfig] = None) -> DoclingIngester:
    """Get or create DoclingIngester singleton."""
    global _ingester
    if _ingester is None:
        _ingester = DoclingIngester(qdrant_client, config)
    return _ingester
