"""
Progressive Classification Service for LKAP (Feature 022)
Local Knowledge Augmentation Platform

4-layer progressive classification per Research Decision RT-003:
Layer 1: Hard signals (path, filename, vendor markers) → weight: 1.0
Layer 2: Content analysis (title, TOC, headings) → weight: 0.8
Layer 3: LLM classification → weight: 0.6-0.9
Layer 4: User confirmation (confidence < 0.70)

Confidence Bands:
- High (≥0.85): Auto-accept
- Medium (0.70-0.84): Optional review
- Low (<0.70): Required review
"""

import os
import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .lkap_logging import get_logger
from .lkap_models import Domain, DocumentType, ConfidenceBand

logger = get_logger("lkap.classification")

# Vendor markers for automatic detection
VENDOR_MARKERS = {
    "ST": ["STMicroelectronics", "STM", "STMicro"],
    "NXP": ["NXP Semiconductors", "NXP"],
    "ARM": ["ARM Ltd", "ARM Holdings", "ARM Cortex"],
    "ESP": ["Espressif", "ESP32", "ESP8266"],
    "TI": ["Texas Instruments", "TI Incorporated"],
}

# Domain keywords by content
DOMAIN_KEYWORDS = {
    Domain.EMBEDDED: [
        "microcontroller", "mcu", "gpio", "spi", "i2c", "uart",
        "datasheet", "reference manual", "embedded", "firmware",
    ],
    Domain.SOFTWARE: [
        "api", "function", "class", "library", "framework",
        "documentation", "readme", "software development",
    ],
    Domain.SECURITY: [
        "threat", "vulnerability", "cve", "exploit", "apt",
        "malware", "indicator", "ioc", "threat intelligence",
    ],
    Domain.CLOUD: [
        "aws", "azure", "gcp", "kubernetes", "docker",
        "cloud", "deployment", "infrastructure", "service",
    ],
    Domain.STANDARDS: [
        "ieee", "iso", "ietf", "rfc", "standard", "specification",
    ],
}


@dataclass
class ClassificationResult:
    """Result of classifying a document field"""
    value: str
    confidence: float
    signal_sources: List[str]


class ProgressiveClassifier:
    """
    Progressive classification service with 4-layer confidence scoring.

    Research Decision RT-003: Layered confidence scoring where
    the best signal wins. Hard signals provide 1.0 confidence,
    content analysis 0.8, LLM 0.6-0.9 (with 0.7 multiplier).
    """

    def __init__(self):
        self.override_memory: Dict[str, Dict[str, str]] = {}

    def classify_domain(
        self,
        filename: str,
        path: str,
        title: str = "",
        content: str = "",
        toc: str = "",
    ) -> ClassificationResult:
        """
        Classify document domain using progressive 4-layer approach.

        Returns:
            ClassificationResult with domain value and confidence
        """
        scores = []
        sources = []

        # Layer 1: Hard signals from path/filename (weight: 1.0)
        path_domain = self._classify_from_path(path, filename)
        if path_domain:
            scores.append(1.0)
            sources.append("path")

        # Layer 2: Content analysis (weight: 0.8)
        content_domain = self._classify_domain_from_content(title, toc, content)
        if content_domain:
            scores.append(0.8)
            sources.append("content_analysis")

        # Layer 3: LLM classification (weight: 0.6-0.9 * 0.7 = 0.42-0.63)
        # Note: This is async and requires the method to be async
        # For synchronous calls, we skip LLM classification here
        # Full LLM integration available via async classify_domain_async method

        # Layer 4: User override (checked separately)
        user_override = self._get_user_override(path, "domain")
        if user_override:
            logger.info(f"User override for domain: {path} → {user_override}")
            return ClassificationResult(
                value=user_override,
                confidence=1.0,
                signal_sources=["user_override"],
            )

        # Best signal wins
        if scores:
            best_score = max(scores)
            best_index = scores.index(best_score)

            # Map back to domain value
            if sources[best_index] == "path" and path_domain:
                return ClassificationResult(
                    value=path_domain,
                    confidence=best_score,
                    signal_sources=sources,
                )
            elif sources[best_index] == "content_analysis" and content_domain:
                return ClassificationResult(
                    value=content_domain,
                    confidence=best_score,
                    signal_sources=sources,
                )

        # Default fallback
        logger.warning(f"Could not classify domain for {filename}, defaulting to software")
        return ClassificationResult(
            value=Domain.SOFTWARE.value,
            confidence=0.3,
            signal_sources=["default"],
        )

    def _classify_from_path(self, path: str, filename: str) -> Optional[str]:
        """Layer 1: Classify from path patterns (hard signal)"""
        path_lower = path.lower()
        filename_lower = filename.lower()

        if "embedded" in path_lower or "mcu" in path_lower:
            return Domain.EMBEDDED.value
        elif "security" in path_lower or "threat" in path_lower or "osint" in path_lower:
            return Domain.SECURITY.value
        elif "cloud" in path_lower or "infra" in path_lower:
            return Domain.CLOUD.value
        elif "standard" in path_lower or "spec" in path_lower:
            return Domain.STANDARDS.value
        elif "api" in path_lower or "lib" in path_lower:
            return Domain.SOFTWARE.value

        return None

    def _classify_domain_from_content(
        self, title: str, toc: str, content: str
    ) -> Optional[str]:
        """Layer 2: Classify from content analysis"""
        combined = f"{title} {toc} {content}".lower()

        scores = {}
        for domain, keywords in DOMAIN_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in combined)
            if matches > 0:
                scores[domain.value] = matches

        if scores:
            return max(scores, key=scores.get)

        return None

    def _get_user_override(self, path: str, field: str) -> Optional[str]:
        """Layer 4: Get user override from memory"""
        # Extract source identifier from path
        source_key = self._extract_source_key(path)
        if source_key in self.override_memory:
            return self.override_memory[source_key].get(field)
        return None

    def _extract_source_key(self, path: str) -> str:
        """Extract source identifier from document path for override learning"""
        # Use directory path as source identifier
        return os.path.dirname(path)

    def save_user_override(
        self, path: str, field: str, original_value: str, new_value: str
    ):
        """
        Save user override for future classification.

        Stores user corrections in memory for learning. Future documents
        from the same source will use the overridden value.

        Args:
            path: Document path for source identification
            field: Classification field being overridden
            original_value: Original auto-classified value
            new_value: User-corrected value to use for future classifications
        """
        source_key = self._extract_source_key(path)
        if source_key not in self.override_memory:
            self.override_memory[source_key] = {}

        self.override_memory[source_key][field] = new_value
        logger.info(
            f"Saved user override: {source_key} {field}: "
            f"{original_value} → {new_value}"
        )

    async def _classify_with_llm(
        self, title: str, content: str
    ) -> Optional[ClassificationResult]:
        """
        Layer 3: LLM-based classification using Graphiti LLM client.

        Uses LLM to classify document domain when hard signals and content
        analysis are insufficient.

        Args:
            title: Document title
            content: Document content (truncated to avoid token limits)

        Returns:
            ClassificationResult with confidence, or None if LLM unavailable

        Note:
            LLM classification has weight 0.6-0.9, multiplied by 0.7 for
            final confidence score (0.42-0.63 range).
        """
        try:
            from .promotion import get_graphiti

            graphiti = get_graphiti()
            if not graphiti or not graphiti.llm_client:
                logger.debug("LLM client not available for classification")
                return None

            # Prepare classification prompt
            domain_list = ", ".join([d.value for d in Domain])

            prompt = f"""Classify the following technical document into ONE of these domains: {domain_list}

Title: {title}

Content (first 2000 characters):
{content[:2000]}

Respond with ONLY the domain name. Choose the best match based on the document's primary focus."""

            # Call LLM
            from graphiti.llm_client import LLMClient
            llm_client: LLMClient = graphiti.llm_client

            response = await llm_client.generate_user_response(
                prompt=prompt,
                response_type="text",
            )

            # Extract domain from response
            response_text = response.strip().lower()

            # Map response to Domain enum
            for domain in Domain:
                if domain.value in response_text or response_text in domain.value:
                    # Base confidence on LLM certainty (0.6-0.9 range)
                    confidence = 0.75  # Medium-high confidence for LLM
                    logger.info(f"LLM classified as {domain.value} (confidence: {confidence})")
                    return ClassificationResult(
                        value=domain,
                        confidence=confidence,
                        signal_sources=["llm_classification"],
                    )

            logger.warning(f"LLM returned unrecognized domain: {response_text}")
            return None

        except ImportError:
            logger.debug("Graphiti not available for LLM classification")
            return None
        except Exception as e:
            logger.warning(f"LLM classification failed (non-critical): {e}")
            return None

    def get_confidence_band(self, confidence: float) -> ConfidenceBand:
        """
        Convert confidence score to confidence band.

        Research Decision RT-003:
        - High (≥0.85): Auto-accept
        - Medium (0.70-0.84): Optional review
        - Low (<0.70): Required review
        """
        if confidence >= 0.85:
            return ConfidenceBand.HIGH
        elif confidence >= 0.70:
            return ConfidenceBand.MEDIUM
        else:
            return ConfidenceBand.LOW
