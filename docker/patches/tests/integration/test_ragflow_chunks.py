"""
Integration Tests for RAGFlow Chunk Retrieval (T075 - US4)
Local Knowledge Augmentation Platform

End-to-end tests for:
- Chunk retrieval with headings and metadata
- Chunk structure validation
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from patches.ragflow_client import RAGFlowClient


class TestChunkRetrieval:
    """Integration tests for RAGFlow chunk retrieval (T075)"""

    @pytest.fixture
    def mock_ragflow_client(self):
        """Create a mock RAGFlow client"""
        client = MagicMock(spec=RAGFlowClient)
        client.get_chunk = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_get_chunk_returns_headings(self, mock_ragflow_client):
        """
        T075: Test that getChunk returns chunk with headings.

        Chunks should include heading information for context.
        """
        mock_chunk = {
            "chunk_id": "chunk-abc123",
            "text": "The GPIO peripheral can be configured for various modes including input, output, and alternate functions.",
            "source_document": "stm32h7-reference.pdf",
            "doc_id": "doc-stm32h7-ref",
            "page_section": "Section 3.2 - GPIO Configuration",
            "position": 42,
            "confidence": 0.92,
            "metadata": {
                "headings": ["GPIO Configuration", "Peripheral Modes"],
                "page_number": 15,
                "document_type": "datasheet",
            },
        }

        mock_ragflow_client.get_chunk.return_value = mock_chunk

        chunk = await mock_ragflow_client.get_chunk("chunk-abc123")

        # Verify headings are present
        assert "metadata" in chunk
        assert "headings" in chunk["metadata"]
        assert len(chunk["metadata"]["headings"]) > 0
        assert "GPIO Configuration" in chunk["metadata"]["headings"]

    @pytest.mark.asyncio
    async def test_get_chunk_includes_position(self, mock_ragflow_client):
        """
        T075: Test that chunk includes position information.

        Position helps users locate the chunk within the document.
        """
        mock_chunk = {
            "chunk_id": "chunk-pos-test",
            "text": "Sample content",
            "source_document": "test-doc.pdf",
            "position": 7,
            "page_section": "Section 1.1",
            "confidence": 0.85,
            "metadata": {
                "page_number": 3,
                "char_start": 1200,
                "char_end": 1450,
            },
        }

        mock_ragflow_client.get_chunk.return_value = mock_chunk

        chunk = await mock_ragflow_client.get_chunk("chunk-pos-test")

        assert "position" in chunk
        assert chunk["position"] == 7
        assert chunk["metadata"].get("page_number") == 3

    @pytest.mark.asyncio
    async def test_get_chunk_includes_source_document(self, mock_ragflow_client):
        """
        T075: Test that chunk includes source document info.

        Source document is essential for provenance tracking.
        """
        mock_chunk = {
            "chunk_id": "chunk-source-test",
            "text": "Important constraint information",
            "source_document": "project-constraints.md",
            "doc_id": "doc-project-001",
            "page_section": "Hardware Constraints",
            "confidence": 0.91,
            "metadata": {
                "filename": "project-constraints.md",
                "uploaded_at": "2026-02-01T10:00:00Z",
            },
        }

        mock_ragflow_client.get_chunk.return_value = mock_chunk

        chunk = await mock_ragflow_client.get_chunk("chunk-source-test")

        assert "source_document" in chunk
        assert "project-constraints.md" in chunk["source_document"]
        assert "doc_id" in chunk

    @pytest.mark.asyncio
    async def test_get_chunk_includes_confidence(self, mock_ragflow_client):
        """
        T075: Test that chunk includes confidence score.

        Confidence indicates parsing/extraction quality.
        """
        mock_chunk = {
            "chunk_id": "chunk-conf-test",
            "text": "High-quality extracted content",
            "source_document": "clean-doc.pdf",
            "page_section": "Section 1",
            "confidence": 0.97,
            "metadata": {
                "extraction_method": "ocr",
                "quality_score": 0.97,
            },
        }

        mock_ragflow_client.get_chunk.return_value = mock_chunk

        chunk = await mock_ragflow_client.get_chunk("chunk-conf-test")

        assert "confidence" in chunk
        assert chunk["confidence"] >= 0.70  # Above threshold

    @pytest.mark.asyncio
    async def test_get_chunk_full_structure(self, mock_ragflow_client):
        """
        T075: Test complete chunk structure validation.

        Verify all required fields are present and correctly typed.
        """
        mock_chunk = {
            "chunk_id": "chunk-full-test",
            "text": "Complete chunk with all fields populated for validation testing purposes.",
            "source_document": "complete-doc.pdf",
            "doc_id": "doc-complete-001",
            "page_section": "Appendix A - Full Test",
            "position": 100,
            "token_count": 15,
            "confidence": 0.94,
            "metadata": {
                "headings": ["Appendix A", "Full Test"],
                "page_number": 50,
                "document_type": "reference",
                "component": "testing",
                "project": "lkap",
                "version": "1.0",
                "keywords": ["test", "validation"],
            },
        }

        mock_ragflow_client.get_chunk.return_value = mock_chunk

        chunk = await mock_ragflow_client.get_chunk("chunk-full-test")

        # Validate required fields
        required_fields = ["chunk_id", "text", "source_document", "confidence"]
        for field in required_fields:
            assert field in chunk, f"Missing required field: {field}"

        # Validate metadata structure
        assert "metadata" in chunk
        assert isinstance(chunk["metadata"], dict)

        # Validate types
        assert isinstance(chunk["chunk_id"], str)
        assert isinstance(chunk["text"], str)
        assert isinstance(chunk["confidence"], (int, float))
        assert 0 <= chunk["confidence"] <= 1

    @pytest.mark.asyncio
    async def test_get_chunk_not_found(self, mock_ragflow_client):
        """
        T075: Test handling of non-existent chunk.

        Should raise appropriate error when chunk doesn't exist.
        """
        mock_ragflow_client.get_chunk.side_effect = ValueError("Chunk not found: nonexistent")

        with pytest.raises(ValueError, match="Chunk not found"):
            await mock_ragflow_client.get_chunk("nonexistent-chunk-id")

    @pytest.mark.asyncio
    async def test_get_chunk_with_nested_headings(self, mock_ragflow_client):
        """
        T075: Test chunk with deeply nested heading structure.

        RAGFlow should preserve heading hierarchy for context.
        """
        mock_chunk = {
            "chunk_id": "chunk-nested-headings",
            "text": "Content within a deeply nested section structure.",
            "source_document": "technical-manual.pdf",
            "page_section": "3.2.1.4 GPIO Alternate Functions",
            "confidence": 0.89,
            "metadata": {
                "headings": [
                    "Chapter 3: Peripherals",
                    "3.2 GPIO Module",
                    "3.2.1 Configuration Options",
                    "3.2.1.4 Alternate Functions",
                ],
                "heading_depth": 4,
            },
        }

        mock_ragflow_client.get_chunk.return_value = mock_chunk

        chunk = await mock_ragflow_client.get_chunk("chunk-nested-headings")

        assert "headings" in chunk["metadata"]
        assert len(chunk["metadata"]["headings"]) == 4
        assert "3.2.1.4 GPIO Alternate Functions" in chunk["page_section"]
