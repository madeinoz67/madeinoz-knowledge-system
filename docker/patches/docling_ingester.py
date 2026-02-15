"""
Docling Document Ingester (Feature 023)
Qdrant RAG Migration

Ingests PDF and markdown documents into Qdrant with:
- Docling for PDF parsing with table extraction
- Semantic chunking with heading awareness
- Ollama embeddings with bge-large-en-v1.5
- Idempotent ingestion via document hash

Feature 024: Multimodal image extraction with Vision LLM enrichment
"""

import base64
import hashlib
import io
import logging
import os
import shutil
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from docling.chunking import HybridChunker
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import PictureItem

from patches.lkap_models import (
    Document,
    DocumentChunk,
    DocumentType,
    Domain,
    ImageChunk,
    ImageType,
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
    batch_size: int = 8  # Reduced for Ollama stability
    confidence_threshold: float = 0.70
    extract_images: bool = True  # Feature 024: Enable image extraction
    enrich_images: bool = True   # Feature 024: Enable Vision LLM enrichment
    enable_ocr: bool = False     # OCR disabled by default for faster text-based PDF processing


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

    Feature 024: Multimodal image extraction with Vision LLM enrichment
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

        # Configure Docling pipeline options
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = self.config.enable_ocr  # Disable OCR by default for faster processing

        # Feature 024: Configure Docling for image extraction
        if self.config.extract_images:
            pipeline_options.generate_page_images = False
            pipeline_options.generate_picture_images = True  # Extract figures/images

        self.docling_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

        self.chunker = SemanticChunker(
            min_tokens=self.config.min_tokens,
            max_tokens=self.config.max_tokens,
            overlap_percent=self.config.overlap_percent,
        )
        self.embedder = get_ollama_embedder()

        # Feature 024: Lazy-load image enricher
        self._image_enricher = None

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

    def parse_pdf(self, file_path: Path) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Parse PDF document using Docling with table extraction and image extraction.

        T018: PDF parsing with Docling.
        Feature 024: Image extraction from PDFs.

        Args:
            file_path: Path to PDF file

        Returns:
            Tuple of (full_text, list of chunk dicts with metadata, list of image dicts)
        """
        logger.info(f"Parsing PDF: {file_path}")

        result = self.docling_converter.convert(str(file_path))

        # Export to markdown format for text
        markdown_text = result.document.export_to_markdown()

        # Get structured chunks from Docling's HybridChunker (preserves headings/structure)
        from docling.chunking import HybridChunker as DoclingHybridChunker
        docling_chunker = DoclingHybridChunker()
        docling_chunks = list(docling_chunker.chunk(result.document))
        logger.info(f"Docling produced {len(docling_chunks)} initial chunks")

        chunks = []
        rechunked_count = 0
        for i, chunk in enumerate(docling_chunks):
            headings = []
            if hasattr(chunk, "meta") and hasattr(chunk.meta, "headings"):
                # Handle case where headings might be None
                chunk_headings = chunk.meta.headings
                if chunk_headings is not None:
                    headings = list(chunk_headings)

            text = chunk.text
            if not text or not text.strip():
                continue  # Skip empty chunks

            token_count = self.chunker.count_tokens(text)
            logger.debug(f"Chunk {i}: {token_count} tokens, max={self.config.max_tokens}")

            # If chunk is too large for embedding model, re-chunk it
            if token_count > self.config.max_tokens:
                logger.info(f"Re-chunking large chunk {i} ({token_count} tokens > {self.config.max_tokens})")
                rechunked_count += 1
                sub_chunks = self.chunker.chunk(text)
                if sub_chunks is None:
                    logger.warning(f"Re-chunking returned None for chunk {i}, splitting by sentences")
                    # Fallback: split by sentences
                    import re
                    sentences = re.split(r'[.!?]+', text)
                    for j, sent in enumerate(sentences):
                        if sent.strip():
                            chunks.append({
                                "text": sent.strip(),
                                "position": len(chunks),
                                "headings": headings,
                                "page_section": getattr(chunk.meta, "page_no", None) if hasattr(chunk, "meta") else None,
                                "token_count": self.chunker.count_tokens(sent.strip()),
                            })
                else:
                    logger.info(f"Split into {len(sub_chunks)} sub-chunks")
                    for j, sub in enumerate(sub_chunks):
                        sub_text = sub.text if hasattr(sub, "text") else str(sub)
                        sub_tokens = getattr(sub, "token_count", None) or self.chunker.count_tokens(sub_text)
                        chunks.append({
                            "text": sub_text,
                            "position": len(chunks),
                            "headings": headings,
                            "page_section": getattr(chunk.meta, "page_no", None) if hasattr(chunk, "meta") else None,
                            "token_count": sub_tokens,
                        })
            else:
                chunks.append({
                    "text": text,
                    "position": i,
                    "headings": headings,
                    "page_section": getattr(chunk.meta, "page_no", None) if hasattr(chunk, "meta") else None,
                    "token_count": token_count,
                })

        logger.info(f"Final chunks: {len(chunks)} (re-chunked {rechunked_count} large chunks)")

        # Feature 024: Extract images from PDF
        images = []
        if self.config.extract_images:
            images = self._extract_images_from_docling(result.document)
            logger.info(f"Extracted {len(images)} images from PDF")

        logger.info(f"Parsed PDF into {len(chunks)} chunks and {len(images)} images")
        return markdown_text, chunks, images

    def _extract_images_from_docling(self, document) -> List[Dict[str, Any]]:
        """
        Extract images from Docling document using correct API.

        Feature 024: Image extraction from Docling using iterate_items().

        Uses document.iterate_items() to find PictureItem elements,
        then extracts actual image data via element.get_image(document).

        Args:
            document: Docling document object

        Returns:
            List of image dicts with base64 data and metadata
        """
        images = []
        picture_count = 0

        logger.info("=== Docling Image Extraction (iterate_items API) ===")
        logger.debug(f"Document type: {type(document)}")

        try:
            # Correct Docling API: iterate through document items
            # Each item is a tuple of (element, level_in_document_hierarchy)
            for element, level in document.iterate_items():
                if isinstance(element, PictureItem):
                    picture_count += 1
                    logger.debug(f"Found PictureItem at level {level}: {type(element)}")

                    # Get the actual image from the PictureItem
                    # get_image() returns a PIL Image or None
                    image = element.get_image(document)

                    if image is not None:
                        logger.debug(f"PictureItem has image: {image.size}, mode={image.mode}")

                        # Convert PIL Image to base64
                        buffer = io.BytesIO()
                        # Convert to RGB if necessary (handles RGBA, etc.)
                        if image.mode in ('RGBA', 'P'):
                            image = image.convert('RGB')
                        image.save(buffer, format="PNG")
                        image_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

                        # Extract metadata from PictureItem
                        prov = getattr(element, 'prov', [])
                        page_no = prov[0].page_no if prov else 0

                        images.append({
                            "image_id": str(uuid.uuid4()),
                            "image_data": image_data,
                            "source_page": page_no,
                            "position": picture_count,
                            "format": "PNG",
                            "size": image.size,
                            "mode": image.mode,
                        })
                        logger.info(f"Extracted image {picture_count}: page={page_no}, size={image.size}")
                    else:
                        logger.debug(f"PictureItem.get_image() returned None for item {picture_count}")

            logger.info(f"Image extraction complete: {picture_count} PictureItems found, {len(images)} images extracted")

        except Exception as e:
            logger.warning(f"Failed to extract images from document: {e}")
            logger.exception("Full image extraction error:")

        return images

    def _extract_picture_image(self, picture) -> Optional[str]:
        """
        Extract base64 image from Docling picture object.

        DEPRECATED: This method is kept for backwards compatibility.
        New code should use _extract_images_from_docling() which uses
        the correct iterate_items() API.

        Args:
            picture: Docling picture object

        Returns:
            Base64 encoded image string or None
        """
        try:
            if hasattr(picture, "image") and picture.image:
                buffer = io.BytesIO()
                picture.image.save(buffer, format="PNG")
                return base64.b64encode(buffer.getvalue()).decode("utf-8")
            elif hasattr(picture, "data"):
                # Some versions store raw data
                return base64.b64encode(picture.data).decode("utf-8")
        except Exception as e:
            logger.debug(f"Failed to extract picture image: {e}")
        return None

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

        # Use semantic chunker for markdown with empty headings list
        chunks = self.chunker.chunk_with_headings(text, headings=[])

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
        # Prepare chunks for QdrantClient.ingest_chunks format
        qdrant_chunks = []
        for i, chunk in enumerate(chunks):
            qdrant_chunks.append({
                "text": chunk["text"],
                "metadata": {
                    "chunk_id": f"{doc_id}_chunk_{i}",
                    "doc_id": doc_id,
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
                }
            })

        # Use QdrantClient.ingest_chunks
        result = await self.qdrant_client.ingest_chunks(
            chunks=qdrant_chunks,
            embeddings=embeddings,
            document_id=doc_id,
        )

        return result.get("chunks_ingested", 0)

    async def ingest(self, file_path: Path) -> IngestionResult:
        """
        Ingest a document: parse → chunk → embed → store.

        T021: Orchestrates the full ingestion pipeline.
        Feature 024: Also extracts and enriches images from PDFs.

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
            doc_id = str(uuid.uuid4())

            # T025: Progress logging
            logger.info(f"[1/5] Parsing document: {filename}")

            # Parse based on document type
            doc_type = self.detect_document_type(file_path)
            images = []  # Feature 024: Image list
            if doc_type == DocumentType.PDF:
                full_text, chunks, images = self.parse_pdf(file_path)
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
            logger.info(f"[2/5] Generating embeddings for {len(chunks)} chunks")

            # Generate embeddings in batches
            all_embeddings = []
            batch_texts = [c["text"] for c in chunks]

            for i in range(0, len(batch_texts), self.config.batch_size):
                batch = batch_texts[i:i + self.config.batch_size]
                embeddings = await self.embedder.embed_batch(batch)
                all_embeddings.extend(embeddings)
                logger.debug(f"Generated embeddings for batch {i//self.config.batch_size + 1}")

            # T025: Progress logging
            logger.info(f"[3/5] Classifying and storing chunks")

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

            # Feature 024: Process and store images
            image_count = 0
            if images and self.config.extract_images:
                logger.info(f"[4/5] Enriching and storing {len(images)} images")
                image_count = await self._process_images(doc_id, images, metadata)
            else:
                logger.info(f"[4/5] No images to process")

            # T025: Progress logging
            logger.info(f"[5/5] Moving document to processed/")

            # T023: Move from inbox to processed (optional - may fail on read-only filesystems)
            try:
                processed_path = Path(self.config.processed_path) / filename
                shutil.move(str(file_path), str(processed_path))
            except (OSError, PermissionError) as e:
                logger.warning(f"Could not move document to processed/ (read-only filesystem?): {e}")

            processing_time = int((time.time() - start_time) * 1000)

            logger.info(f"Ingestion complete: {filename} -> {stored_count} chunks, {image_count} images ({processing_time}ms)")

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

    async def _process_images(
        self,
        doc_id: str,
        images: List[Dict[str, Any]],
        metadata: Dict[str, Any],
    ) -> int:
        """
        Process images: enrich with Vision LLM and store in Qdrant.

        Feature 024: Image enrichment and storage pipeline.

        Args:
            doc_id: Document identifier
            images: List of image dicts from parse_pdf
            metadata: Document-level metadata

        Returns:
            Number of images stored
        """
        if not images:
            return 0

        # Lazy-load image enricher
        if self._image_enricher is None and self.config.enrich_images:
            from patches.image_enricher import get_image_enricher
            self._image_enricher = get_image_enricher()

        processed_images = []
        for img in images:
            try:
                # Enrich with Vision LLM if enabled
                if self.config.enrich_images and self._image_enricher:
                    enrichment = await self._image_enricher.classify_and_describe(img["image_data"])
                    classification = enrichment.classification
                    description = enrichment.description
                else:
                    classification = ImageType.UNKNOWN
                    description = f"Image from page {img.get('source_page', 'unknown')}"

                # Create ImageChunk
                image_chunk = {
                    "image_id": img["image_id"],
                    "doc_id": doc_id,
                    "image_data": img["image_data"],
                    "image_format": img.get("format", "PNG"),
                    "dimensions": img.get("dimensions", (0, 0)),
                    "source_page": img.get("source_page", 0),
                    "classification": classification.value,
                    "description": description,
                    "headings": [],
                    "content_type": "image",
                    "source": metadata.get("filename", ""),
                }

                # Generate text embedding from description
                if self._image_enricher:
                    embeddings = await self.embedder.embed_batch([description])
                    image_chunk["text_embedding"] = embeddings[0] if embeddings else None

                processed_images.append(image_chunk)

            except Exception as e:
                logger.warning(f"Failed to process image {img.get('image_id', 'unknown')}: {e}")
                continue

        # Store images in Qdrant
        if processed_images:
            stored = await self._store_image_chunks(doc_id, processed_images, metadata)
            return stored

        return 0

    async def _store_image_chunks(
        self,
        doc_id: str,
        images: List[Dict[str, Any]],
        metadata: Dict[str, Any],
    ) -> int:
        """
        Store image chunks in Qdrant.

        Feature 024: Image storage with embeddings.

        Args:
            doc_id: Document identifier
            images: List of processed image dicts
            metadata: Document-level metadata

        Returns:
            Number of images stored
        """
        # Prepare images as chunks for QdrantClient.ingest_chunks
        qdrant_chunks = []
        embeddings = []
        for img in images:
            image_id = img["image_id"]
            qdrant_chunks.append({
                "text": img.get("description", ""),  # Use description as text
                "metadata": {
                    "image_id": image_id,
                    "doc_id": doc_id,
                    "image_data": img["image_data"],
                    "image_format": img.get("image_format", "PNG"),
                    "classification": img.get("classification", "unknown"),
                    "description": img.get("description", ""),
                    "source_page": img.get("source_page", 0),
                    "headings": img.get("headings", []),
                    "domain": metadata.get("domain", "software"),
                    "source": metadata.get("filename", ""),
                    "content_type": "image",
                }
            })
            embeddings.append(img.get("text_embedding", [0.0] * 1024))

        # Use QdrantClient.ingest_chunks
        try:
            result = await self.qdrant_client.ingest_chunks(
                chunks=qdrant_chunks,
                embeddings=embeddings,
                document_id=doc_id,
            )
            return result.get("chunks_ingested", 0)
        except Exception as e:
            logger.error(f"Failed to store image chunks: {e}")
            return 0

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
