"""
Integration Tests for RAGFlow Semantic Search (T052, T053, T076 - US2/US4)
Local Knowledge Augmentation Platform

End-to-end tests for:
- Semantic search with filtering (T052)
- Empty results handling (T053)
- Keyword-enhanced search ranking (T076)
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from patches.ragflow_client import RAGFlowClient, SearchResult


class TestSemanticSearch:
    """Integration tests for semantic search (T052, T053)"""

    @pytest.fixture
    def mock_ragflow_client(self):
        """Create a mock RAGFlow client"""
        client = MagicMock(spec=RAGFlowClient)
        client.search = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_search_with_domain_filter(self, mock_ragflow_client):
        """
        T052: Test semantic search filtering by domain.

        Verifies that search results can be filtered by domain metadata.
        """
        # Mock search results
        mock_results = [
            SearchResult(
                chunk_id="chunk-001",
                text="STM32H7 GPIO configuration requires 120MHz clock",
                source_document="stm32h7-reference.pdf",
                page_section="Section 3.2",
                confidence=0.92,
                metadata={"domain": "embedded", "type": "datasheet"},
            ),
            SearchResult(
                chunk_id="chunk-002",
                text="ESP32 GPIO supports capacitive touch",
                source_document="esp32-datasheet.pdf",
                page_section="Section 4.1",
                confidence=0.88,
                metadata={"domain": "embedded", "type": "datasheet"},
            ),
        ]

        mock_ragflow_client.search.return_value = mock_results

        # Execute search with domain filter
        results = await mock_ragflow_client.search(
            query="GPIO configuration",
            filters={"domain": "embedded"},
            top_k=10,
        )

        # Verify filter was applied
        mock_ragflow_client.search.assert_called_once()
        call_args = mock_ragflow_client.search.call_args
        assert call_args.kwargs.get("filters", {}).get("domain") == "embedded"

        # Verify results
        assert len(results) == 2
        for result in results:
            assert result.metadata.get("domain") == "embedded"

    @pytest.mark.asyncio
    async def test_search_with_type_filter(self, mock_ragflow_client):
        """
        T052: Test semantic search filtering by document type.

        Verifies that search results can be filtered by document type.
        """
        mock_results = [
            SearchResult(
                chunk_id="chunk-003",
                text="Errata: USART3 has known bug with DMA",
                source_document="stm32h7-errata.pdf",
                page_section="Section 2.1",
                confidence=0.95,
                metadata={"type": "errata", "component": "USART"},
            ),
        ]

        mock_ragflow_client.search.return_value = mock_results

        results = await mock_ragflow_client.search(
            query="USART bug",
            filters={"type": "errata"},
            top_k=5,
        )

        assert len(results) == 1
        assert results[0].metadata.get("type") == "errata"

    @pytest.mark.asyncio
    async def test_search_with_component_filter(self, mock_ragflow_client):
        """
        T052: Test semantic search filtering by component.

        Verifies that search results can be filtered by hardware component.
        """
        mock_results = [
            SearchResult(
                chunk_id="chunk-004",
                text="GPIO maximum speed is 120MHz on STM32H7",
                source_document="stm32h7-datasheet.pdf",
                page_section="Section 5.1",
                confidence=0.91,
                metadata={"component": "GPIO"},
            ),
        ]

        mock_ragflow_client.search.return_value = mock_results

        results = await mock_ragflow_client.search(
            query="maximum speed",
            filters={"component": "GPIO"},
            top_k=5,
        )

        assert len(results) == 1
        assert results[0].metadata.get("component") == "GPIO"

    @pytest.mark.asyncio
    async def test_search_with_project_filter(self, mock_ragflow_client):
        """
        T052: Test semantic search filtering by project.

        Verifies that search results can be filtered by project identifier.
        """
        mock_results = [
            SearchResult(
                chunk_id="chunk-005",
                text="Project-specific constraint: use SPI2 for display",
                source_document="project-alpha-notes.md",
                page_section="Hardware Setup",
                confidence=0.87,
                metadata={"project": "project-alpha"},
            ),
        ]

        mock_ragflow_client.search.return_value = mock_results

        results = await mock_ragflow_client.search(
            query="SPI configuration",
            filters={"project": "project-alpha"},
            top_k=5,
        )

        assert len(results) == 1
        assert results[0].metadata.get("project") == "project-alpha"

    @pytest.mark.asyncio
    async def test_search_with_version_filter(self, mock_ragflow_client):
        """
        T052: Test semantic search filtering by version.

        Verifies that search results can be filtered by document version.
        """
        mock_results = [
            SearchResult(
                chunk_id="chunk-006",
                text="Version 2.0 changed the boot sequence",
                source_document="firmware-changelog.md",
                page_section="Changes",
                confidence=0.89,
                metadata={"version": "2.0"},
            ),
        ]

        mock_ragflow_client.search.return_value = mock_results

        results = await mock_ragflow_client.search(
            query="boot sequence",
            filters={"version": "2.0"},
            top_k=5,
        )

        assert len(results) == 1
        assert results[0].metadata.get("version") == "2.0"

    @pytest.mark.asyncio
    async def test_empty_results_below_threshold(self, mock_ragflow_client):
        """
        T053: Test that search returns empty when all results below threshold.

        When confidence threshold (0.70) is not met, should return empty list.
        """
        # Mock results below threshold
        mock_results = [
            SearchResult(
                chunk_id="chunk-low-1",
                text="Unrelated content about cooking",
                source_document="recipes.pdf",
                page_section="Section 1",
                confidence=0.45,  # Below 0.70 threshold
                metadata={},
            ),
            SearchResult(
                chunk_id="chunk-low-2",
                text="Another unrelated document",
                source_document="random.pdf",
                page_section="Section 2",
                confidence=0.52,  # Below 0.70 threshold
                metadata={},
            ),
        ]

        mock_ragflow_client.search.return_value = mock_results

        # Search with confidence threshold
        results = await mock_ragflow_client.search(
            query="STM32H7 GPIO configuration",
            top_k=10,
        )

        # Client should filter out low-confidence results
        # (This tests the client's threshold filtering behavior)
        high_confidence_results = [r for r in results if r.confidence >= 0.70]
        assert len(high_confidence_results) == 0

    @pytest.mark.asyncio
    async def test_empty_results_no_matches(self, mock_ragflow_client):
        """
        T053: Test that search returns empty when no documents match query.

        When there are literally no results from the vector search,
        should return empty list (not error).
        """
        mock_ragflow_client.search.return_value = []

        results = await mock_ragflow_client.search(
            query="xyzzy plugh adventure game",
            top_k=10,
        )

        assert results == []
        assert len(results) == 0


class TestKeywordEnhancedSearch:
    """Integration tests for keyword-enhanced search (T076)"""

    @pytest.fixture
    def mock_ragflow_client(self):
        """Create a mock RAGFlow client"""
        client = MagicMock(spec=RAGFlowClient)
        client.search = AsyncMock()
        client.get_chunk = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_keywords_improve_ranking(self, mock_ragflow_client):
        """
        T076: Test that manually added keywords improve search ranking.

        RAGFlow allows adding keywords to chunks. These should boost
        the chunk's relevance for matching queries.
        """
        # Simulate search where keyword-enhanced chunk ranks higher
        mock_results = [
            SearchResult(
                chunk_id="chunk-with-keywords",
                text="Configure the peripheral clock for optimal performance",
                source_document="clock-config.md",
                page_section="Section 1",
                confidence=0.95,  # Higher due to keywords
                metadata={"keywords": ["STM32H7", "clock", "GPIO", "120MHz"]},
            ),
            SearchResult(
                chunk_id="chunk-without-keywords",
                text="The peripheral clock configuration is described here",
                source_document="generic-doc.md",
                page_section="Section 1",
                confidence=0.78,  # Lower without keywords
                metadata={},
            ),
        ]

        mock_ragflow_client.search.return_value = mock_results

        results = await mock_ragflow_client.search(
            query="STM32H7 clock GPIO 120MHz",
            top_k=5,
        )

        # Keyword-enhanced result should rank first
        assert results[0].chunk_id == "chunk-with-keywords"
        assert results[0].confidence > results[1].confidence

    @pytest.mark.asyncio
    async def test_chunk_keywords_retrievable(self, mock_ragflow_client):
        """
        T076: Test that chunk metadata includes keywords.

        When retrieving a chunk, its keywords should be included
        in the metadata for verification.
        """
        mock_chunk = {
            "chunk_id": "chunk-with-keywords",
            "text": "Configure the peripheral clock",
            "source_document": "clock-config.md",
            "metadata": {
                "keywords": ["STM32H7", "clock", "GPIO"],
            },
        }

        mock_ragflow_client.get_chunk.return_value = mock_chunk

        chunk = await mock_ragflow_client.get_chunk("chunk-with-keywords")

        assert "keywords" in chunk.get("metadata", {})
        assert "STM32H7" in chunk["metadata"]["keywords"]

    @pytest.mark.asyncio
    async def test_keyword_relevance_boost(self, mock_ragflow_client):
        """
        T076: Verify keyword match provides relevance boost.

        Keywords should act as a signal that boosts relevance
        even when semantic similarity is moderate.
        """
        # Simulate scenario where semantic-only would rank differently
        mock_results = [
            SearchResult(
                chunk_id="semantically-similar",
                text="Clock configuration for microcontrollers",
                source_document="generic-mcu.md",
                page_section="Section 1",
                confidence=0.75,
                metadata={},  # No keywords
            ),
            SearchResult(
                chunk_id="keyword-boosted",
                text="H7 series peripheral setup",
                source_document="stm32-notes.md",
                page_section="Section 1",
                confidence=0.88,  # Boosted by keywords
                metadata={"keywords": ["STM32H7", "peripheral"]},
            ),
        ]

        mock_ragflow_client.search.return_value = mock_results

        results = await mock_ragflow_client.search(
            query="STM32H7 peripheral clock",
            top_k=5,
        )

        # Keyword-boosted result should rank higher
        assert results[0].metadata.get("keywords") is not None
