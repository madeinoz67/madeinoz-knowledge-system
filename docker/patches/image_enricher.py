"""
Image Enricher for LKAP (Feature 024)
Multimodal Image Extraction

Enriches extracted images using Vision LLM with multi-provider fallback:
1. OpenRouter (cloud, fastest) - Various vision models
2. Z.AI Direct (cloud) - Z.AI native API
3. Ollama LLaVA (local) - Fully local vision model

Environment Variables:
    MADEINOZ_KNOWLEDGE_VISION_PROVIDER: Preferred provider (openrouter, zai, ollama)
    MADEINOZ_KNOWLEDGE_OPENROUTER_API_KEY: OpenRouter API key
    MADEINOZ_KNOWLEDGE_ZAI_API_KEY: Z.AI API key
    MADEINOZ_KNOWLEDGE_OLLAMA_BASE_URL: Ollama API URL
    MADEINOZ_KNOWLEDGE_VISION_MODEL: Vision model name
"""

import base64
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

import httpx

from patches.lkap_models import ImageType

logger = logging.getLogger(__name__)

# Environment configuration
VISION_PROVIDER = os.getenv("MADEINOZ_KNOWLEDGE_VISION_PROVIDER", os.getenv("VISION_LLM_PROVIDER", "ollama"))
OPENROUTER_API_KEY = os.getenv("MADEINOZ_KNOWLEDGE_OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
ZAI_API_KEY = os.getenv("MADEINOZ_KNOWLEDGE_ZAI_API_KEY", "")
ZAI_BASE_URL = os.getenv("MADEINOZ_KNOWLEDGE_ZAI_BASE_URL", "https://api.z.ai/v1")
# Ollama URL: check MADEINOZ_KNOWLEDGE_OLLAMA_BASE_URL first, then OLLAMA_BASE_URL (from container)
OLLAMA_BASE_URL = os.getenv("MADEINOZ_KNOWLEDGE_OLLAMA_BASE_URL", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
# Vision model: check MADEINOZ_KNOWLEDGE_VISION_MODEL first, then VISION_LLM_MODEL (from container)
VISION_MODEL = os.getenv(
    "MADEINOZ_KNOWLEDGE_VISION_MODEL",
    os.getenv("VISION_LLM_MODEL", "llama3.2-vision")  # Default to Ollama vision model
)

# Classification prompt for technical documents
CLASSIFICATION_PROMPT = """Analyze this technical document image and provide:
1. Classification: One of [schematic, pinout, waveform, photo, table, graph, flowchart, unknown]
2. Description: A detailed description suitable for search indexing (2-3 sentences)

Classification guidelines:
- schematic: Circuit diagrams, block diagrams, architecture diagrams
- pinout: Pin configuration diagrams, connector layouts
- waveform: Timing diagrams, signal plots, oscilloscope traces
- photo: Product photos, hardware images
- table: Tables extracted as images
- graph: Charts, bar graphs, line graphs, data visualizations
- flowchart: Process diagrams, flowcharts, state machines
- unknown: Cannot classify or unclear

Format your response EXACTLY as:
CLASSIFICATION: <type>
DESCRIPTION: <detailed description>"""


@dataclass
class EnrichmentResult:
    """Result of image enrichment."""
    classification: ImageType
    description: str
    ocr_text: Optional[str] = None
    model_used: Optional[str] = None
    provider: Optional[str] = None


class VisionLLMError(Exception):
    """Base exception for Vision LLM errors."""
    pass


class ImageEnricher:
    """
    Enrich images using Vision LLM with multi-provider fallback.

    Provider Priority:
    1. OpenRouter (cloud, fastest) - Gemini 2.0 Flash, GPT-4 Vision
    2. Z.AI Direct (cloud) - Z.AI native vision
    3. Ollama LLaVA (local) - Fully local, requires GPU
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize ImageEnricher.

        Args:
            provider: Override provider from env (openrouter, zai, ollama)
            model: Override model from env
        """
        self.provider = provider or VISION_PROVIDER
        self.model = model or VISION_MODEL
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120.0)  # Longer timeout for vision
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _parse_response(self, response_text: str) -> tuple[ImageType, str]:
        """
        Parse LLM response into classification and description.

        Args:
            response_text: Raw LLM response

        Returns:
            Tuple of (ImageType, description)
        """
        lines = response_text.strip().split("\n")
        classification = ImageType.UNKNOWN
        description = ""

        for line in lines:
            line = line.strip()
            if line.upper().startswith("CLASSIFICATION:"):
                type_str = line.split(":", 1)[1].strip().lower()
                try:
                    classification = ImageType(type_str)
                except ValueError:
                    logger.warning(f"Unknown classification type: {type_str}")
                    classification = ImageType.UNKNOWN
            elif line.upper().startswith("DESCRIPTION:"):
                description = line.split(":", 1)[1].strip()
            elif description and line:  # Continuation of description
                description += " " + line

        if not description:
            description = response_text  # Fallback to raw response

        return classification, description

    async def _call_openrouter(self, image_base64: str) -> str:
        """Call OpenRouter Vision API."""
        if not OPENROUTER_API_KEY:
            raise VisionLLMError("OPENROUTER_API_KEY not configured")

        client = await self._get_client()

        # Determine if image is already base64 or needs data URL prefix
        if not image_base64.startswith("data:"):
            image_url = f"data:image/png;base64,{image_base64}"
        else:
            image_url = image_base64

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": CLASSIFICATION_PROMPT},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ],
            "max_tokens": 500,
        }

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/madeinoz/madeinoz-knowledge-system",
        }

        response = await client.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def _call_zai(self, image_base64: str) -> str:
        """Call Z.AI Direct Vision API."""
        if not ZAI_API_KEY:
            raise VisionLLMError("ZAI_API_KEY not configured")

        client = await self._get_client()

        # Z.AI uses similar format to OpenAI
        if not image_base64.startswith("data:"):
            image_url = f"data:image/png;base64,{image_base64}"
        else:
            image_url = image_base64

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": CLASSIFICATION_PROMPT},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ],
            "max_tokens": 500,
        }

        headers = {
            "Authorization": f"Bearer {ZAI_API_KEY}",
            "Content-Type": "application/json",
        }

        response = await client.post(
            f"{ZAI_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def _call_ollama(self, image_base64: str) -> str:
        """Call Ollama LLaVA Vision API."""
        client = await self._get_client()

        # Ollama doesn't need data URL prefix
        if image_base64.startswith("data:"):
            # Extract just the base64 part
            image_base64 = image_base64.split(",", 1)[1]

        payload = {
            "model": self.model.replace("llava", "llava:latest") if "llava" in self.model.lower() else self.model,
            "prompt": CLASSIFICATION_PROMPT,
            "images": [image_base64],
            "stream": False,
        }

        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
        )
        response.raise_for_status()

        data = response.json()
        return data.get("response", "")

    async def classify_and_describe(
        self,
        image_base64: str,
        provider_override: Optional[str] = None,
    ) -> EnrichmentResult:
        """
        Classify image type and generate description using Vision LLM.

        Attempts providers in order: OpenRouter → Z.AI → Ollama

        Args:
            image_base64: Base64 encoded image (with or without data URL prefix)
            provider_override: Override provider for this call only

        Returns:
            EnrichmentResult with classification, description, and metadata

        Raises:
            VisionLLMError: If all providers fail
        """
        provider = provider_override or self.provider
        errors = []

        # Provider fallback chain
        providers_to_try = []
        if provider == "openrouter":
            providers_to_try = ["openrouter", "zai", "ollama"]
        elif provider == "zai":
            providers_to_try = ["zai", "openrouter", "ollama"]
        else:
            providers_to_try = ["ollama", "openrouter", "zai"]

        for prov in providers_to_try:
            try:
                logger.info(f"Trying vision provider: {prov}")

                if prov == "openrouter":
                    response = await self._call_openrouter(image_base64)
                elif prov == "zai":
                    response = await self._call_zai(image_base64)
                elif prov == "ollama":
                    response = await self._call_ollama(image_base64)
                else:
                    continue

                classification, description = self._parse_response(response)

                logger.info(f"Image enriched via {prov}: {classification.value}")

                return EnrichmentResult(
                    classification=classification,
                    description=description,
                    model_used=self.model,
                    provider=prov,
                )

            except Exception as e:
                error_msg = f"{prov} failed: {e}"
                logger.warning(error_msg)
                errors.append(error_msg)
                continue

        # All providers failed
        error_summary = "; ".join(errors)
        logger.error(f"All vision providers failed: {error_summary}")

        # Return fallback result instead of raising
        return EnrichmentResult(
            classification=ImageType.UNKNOWN,
            description="Image enrichment failed - vision LLM unavailable",
            provider="none",
        )

    async def classify_batch(
        self,
        images: list[tuple[str, str]],  # List of (image_id, base64_data)
    ) -> list[tuple[str, EnrichmentResult]]:
        """
        Classify multiple images in batch.

        Args:
            images: List of (image_id, base64_data) tuples

        Returns:
            List of (image_id, EnrichmentResult) tuples
        """
        results = []
        for image_id, image_data in images:
            try:
                result = await self.classify_and_describe(image_data)
                results.append((image_id, result))
            except Exception as e:
                logger.error(f"Failed to enrich image {image_id}: {e}")
                results.append((image_id, EnrichmentResult(
                    classification=ImageType.UNKNOWN,
                    description=f"Enrichment failed: {e}",
                    provider="none",
                )))
        return results


# Singleton instance
_enricher: Optional[ImageEnricher] = None


def get_image_enricher(
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> ImageEnricher:
    """Get or create ImageEnricher singleton."""
    global _enricher
    if _enricher is None:
        _enricher = ImageEnricher(provider, model)
    return _enricher
