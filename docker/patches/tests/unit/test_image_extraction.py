"""
Unit tests for Feature 024: Multimodal Image Extraction

Tests for:
- ImageType enum
- ImageChunk model
- ImageEnricher (Vision LLM client)
- Image extraction from DoclingIngester
"""

import base64
import pytest
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

# Test imports - these will work once the code is deployed to the container
import sys
from pathlib import Path

# Add patches directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "patches"))


class TestImageTypeEnum:
    """Tests for ImageType enum."""

    def test_image_type_values(self):
        """Test that ImageType has all expected values."""
        from lkap_models import ImageType

        assert ImageType.SCHEMATIC.value == "schematic"
        assert ImageType.PINOUT.value == "pinout"
        assert ImageType.WAVEFORM.value == "waveform"
        assert ImageType.PHOTO.value == "photo"
        assert ImageType.TABLE.value == "table"
        assert ImageType.GRAPH.value == "graph"
        assert ImageType.FLOWCHART.value == "flowchart"
        assert ImageType.UNKNOWN.value == "unknown"

    def test_image_type_from_string(self):
        """Test creating ImageType from string value."""
        from lkap_models import ImageType

        assert ImageType("schematic") == ImageType.SCHEMATIC
        assert ImageType("pinout") == ImageType.PINOUT
        assert ImageType("unknown") == ImageType.UNKNOWN

    def test_invalid_image_type(self):
        """Test that invalid ImageType raises ValueError."""
        from lkap_models import ImageType

        with pytest.raises(ValueError):
            ImageType("invalid_type")


class TestImageChunkModel:
    """Tests for ImageChunk model."""

    def test_image_chunk_creation(self):
        """Test creating an ImageChunk with required fields."""
        from lkap_models import ImageChunk, ImageType

        chunk = ImageChunk(
            image_id="test-image-123",
            doc_id="doc-456",
            dimensions=(800, 600),
            source_page=5,
            description="Test image description",
        )

        assert chunk.image_id == "test-image-123"
        assert chunk.doc_id == "doc-456"
        assert chunk.dimensions == (800, 600)
        assert chunk.source_page == 5
        assert chunk.description == "Test image description"
        assert chunk.classification == ImageType.UNKNOWN
        assert chunk.content_type == "image"

    def test_image_chunk_with_base64_data(self):
        """Test ImageChunk with base64 image data."""
        from lkap_models import ImageChunk

        # Create a simple 1x1 PNG image
        buffer = BytesIO()
        from PIL import Image
        img = Image.new('RGB', (1, 1), color='red')
        img.save(buffer, format='PNG')
        image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

        chunk = ImageChunk(
            image_id="test-123",
            doc_id="doc-456",
            image_data=image_data,
            dimensions=(1, 1),
            source_page=1,
            description="Red pixel",
        )

        assert chunk.image_data == image_data
        assert chunk.image_format == "PNG"

    def test_image_chunk_with_optional_fields(self):
        """Test ImageChunk with optional fields."""
        from lkap_models import ImageChunk, ImageType

        chunk = ImageChunk(
            image_id="test-123",
            doc_id="doc-456",
            image_data="base64data",
            dimensions=(800, 600),
            source_page=5,
            classification=ImageType.SCHEMATIC,
            description="Circuit diagram showing power supply",
            ocr_text="VCC=3.3V\nGND",
            related_chunk_ids=["chunk-1", "chunk-2"],
            headings=["Power Supply", "Schematic"],
            source_position={"x": 100, "y": 200, "width": 300, "height": 400},
        )

        assert chunk.classification == ImageType.SCHEMATIC
        assert chunk.ocr_text == "VCC=3.3V\nGND"
        assert len(chunk.related_chunk_ids) == 2
        assert len(chunk.headings) == 2


class TestImageEnricher:
    """Tests for ImageEnricher Vision LLM client."""

    def create_test_image_base64(self) -> str:
        """Create a simple test image as base64."""
        buffer = BytesIO()
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='blue')
        img.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    def test_enricher_initialization(self):
        """Test ImageEnricher initialization."""
        from image_enricher import ImageEnricher

        enricher = ImageEnricher()
        assert enricher.provider == "openrouter"  # default
        assert enricher.model is not None

    def test_enricher_custom_provider(self):
        """Test ImageEnricher with custom provider."""
        from image_enricher import ImageEnricher

        enricher = ImageEnricher(provider="ollama", model="llava:latest")
        assert enricher.provider == "ollama"
        assert enricher.model == "llava:latest"

    def test_parse_response_classification(self):
        """Test parsing LLM response for classification."""
        from image_enricher import ImageEnricher
        from lkap_models import ImageType

        enricher = ImageEnricher()

        # Test valid response
        response = """CLASSIFICATION: schematic
DESCRIPTION: This is a circuit diagram showing the power supply section with voltage regulators."""
        classification, description = enricher._parse_response(response)

        assert classification == ImageType.SCHEMATIC
        assert "circuit diagram" in description

    def test_parse_response_multiline_description(self):
        """Test parsing LLM response with multiline description."""
        from image_enricher import ImageEnricher
        from lkap_models import ImageType

        enricher = ImageEnricher()

        response = """CLASSIFICATION: pinout
DESCRIPTION: GPIO pin configuration for STM32H7 series microcontroller.
Shows 64-pin package layout with power, ground, and I/O pins."""
        classification, description = enricher._parse_response(response)

        assert classification == ImageType.PINOUT
        assert "GPIO" in description
        assert "STM32H7" in description

    def test_parse_response_unknown_classification(self):
        """Test parsing response with unknown classification."""
        from image_enricher import ImageEnricher
        from lkap_models import ImageType

        enricher = ImageEnricher()

        response = """CLASSIFICATION: something_weird
DESCRIPTION: Unknown image type."""
        classification, _ = enricher._parse_response(response)

        assert classification == ImageType.UNKNOWN

    @pytest.mark.asyncio
    async def test_classify_and_describe_fallback(self):
        """Test that classify_and_describe returns fallback on all providers failing."""
        from image_enricher import ImageEnricher, VisionLLMError
        from lkap_models import ImageType

        enricher = ImageEnricher()

        # Create test image
        test_image = self.create_test_image_base64()

        # Mock all providers to fail
        with patch.object(enricher, '_call_openrouter', side_effect=VisionLLMError("No API key")):
            with patch.object(enricher, '_call_zai', side_effect=VisionLLMError("No API key")):
                with patch.object(enricher, '_call_ollama', side_effect=Exception("Ollama not running")):
                    result = await enricher.classify_and_describe(test_image)

        # Should return fallback result, not raise
        assert result.classification == ImageType.UNKNOWN
        assert "failed" in result.description.lower() or "unavailable" in result.description.lower()


class TestEnrichmentResult:
    """Tests for EnrichmentResult dataclass."""

    def test_enrichment_result_creation(self):
        """Test creating EnrichmentResult."""
        from image_enricher import EnrichmentResult
        from lkap_models import ImageType

        result = EnrichmentResult(
            classification=ImageType.SCHEMATIC,
            description="Power supply schematic",
            ocr_text="VCC=5V",
            model_used="gemini-2.0-flash",
            provider="openrouter",
        )

        assert result.classification == ImageType.SCHEMATIC
        assert result.description == "Power supply schematic"
        assert result.ocr_text == "VCC=5V"
        assert result.provider == "openrouter"


class TestIngestionConfigImageSettings:
    """Tests for IngestionConfig image-related settings."""

    def test_default_image_settings(self):
        """Test default image extraction settings."""
        from docling_ingester import IngestionConfig

        config = IngestionConfig()

        assert config.extract_images is True
        assert config.enrich_images is True

    def test_disabled_image_enrichment(self):
        """Test disabling image enrichment."""
        from docling_ingester import IngestionConfig

        config = IngestionConfig(extract_images=True, enrich_images=False)

        assert config.extract_images is True
        assert config.enrich_images is False


# Integration-style test (requires actual Docling)
class TestImageExtractionFromPDF:
    """Tests for image extraction from PDF documents."""

    @pytest.mark.skip(reason="Requires sample PDF with images")
    def test_extract_images_from_pdf(self):
        """Test extracting images from a PDF document."""
        # This would require a sample PDF with images
        # and a running Docling installation
        pass

    def test_extract_picture_image_helper(self):
        """Test the _extract_picture_image helper method."""
        from docling_ingester import DoclingIngester
        from docling_ingester import IngestionConfig

        # Create mock Qdrant client
        mock_client = MagicMock()
        mock_client.collection_name = "test_collection"

        config = IngestionConfig(extract_images=True)
        ingester = DoclingIngester(mock_client, config)

        # Test with None image
        result = ingester._extract_picture_image(MagicMock(image=None, data=None))
        assert result is None


class TestQdrantImageSearch:
    """Tests for Qdrant image search methods."""

    @pytest.mark.asyncio
    async def test_search_images_method_exists(self):
        """Test that search_images method exists on QdrantClient."""
        from qdrant_client import QdrantClient

        # Check method exists
        assert hasattr(QdrantClient, 'search_images')
        assert hasattr(QdrantClient, 'get_image')
        assert hasattr(QdrantClient, 'list_images')

    @pytest.mark.asyncio
    async def test_list_images_with_filters(self):
        """Test list_images with classification filter."""
        from qdrant_client import QdrantClient
        from unittest.mock import AsyncMock

        client = QdrantClient()
        client._client = AsyncMock()

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "points": [
                    {
                        "payload": {
                            "image_id": "img-1",
                            "doc_id": "doc-1",
                            "classification": "schematic",
                            "description": "Test schematic",
                            "source_page": 1,
                        }
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()
        client._client.post = AsyncMock(return_value=mock_response)

        # Call list_images
        results = await client.list_images(classification="schematic", limit=10)

        assert len(results) == 1
        assert results[0]["classification"] == "schematic"


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
