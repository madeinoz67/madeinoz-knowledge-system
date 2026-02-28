"""
Source Trust Scoring for LKAP (Feature 023 Enhancement)
RedTeam Gap #GAP-013: Add source trust scoring to prevent knowledge poisoning.

RAG Book Reference:
"The Stack Overflow attack succeeded because we treated all sources equally.
Every document gets a trust score based on:
- Source authority: Official docs > Verified KB > Employee posts > Community wiki > Unverified forums
- Age: Recent documents weighted higher (information decays)
- Verification status: Has someone vouched for this?
- Author reputation: Known contributors vs. first-time posters"

Security Architecture:
- Trust levels with configurable scores
- Source classification heuristics (URL patterns, file paths, metadata)
- Age-based decay for information freshness
- Integration into ingestion and retrieval pipelines

Environment Variables:
    MADEINOZ_KNOWLEDGE_TRUST_ENABLED: Enable trust scoring (default: true)
    MADEINOZ_KNOWLEDGE_TRUST_MIN_THRESHOLD: Minimum trust score to include in results (default: 0.3)
    MADEINOZ_KNOWLEDGE_TRUST_DECAY_HALF_LIFE: Half-life in days for age decay (default: 365)
"""

import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Configuration with defaults
TRUST_ENABLED = os.getenv("MADEINOZ_KNOWLEDGE_TRUST_ENABLED", "true").lower() == "true"
TRUST_MIN_THRESHOLD = float(os.getenv("MADEINOZ_KNOWLEDGE_TRUST_MIN_THRESHOLD", "0.3"))
TRUST_DECAY_HALF_LIFE = float(os.getenv("MADEINOZ_KNOWLEDGE_TRUST_DECAY_HALF_LIFE", "365"))


class TrustLevel(str, Enum):
    """Trust level categories based on RAG Book guidance."""
    OFFICIAL = "official"           # 1.0 - Official documentation, verified sources
    VERIFIED = "verified"           # 0.9 - Verified knowledge base
    TRUSTED = "trusted"             # 0.7 - Personal notes, trusted authors
    COMMUNITY = "community"         # 0.4 - Community sources, forums
    UNVERIFIED = "unverified"       # 0.2 - Unverified sources


# Default trust scores from RAG Book
TRUST_SCORES: Dict[TrustLevel, float] = {
    TrustLevel.OFFICIAL: 1.0,
    TrustLevel.VERIFIED: 0.9,
    TrustLevel.TRUSTED: 0.7,
    TrustLevel.COMMUNITY: 0.4,
    TrustLevel.UNVERIFIED: 0.2,
}

# Source classification patterns
OFFICIAL_PATTERNS = [
    r".*\.github\.io/.*",              # GitHub Pages official docs
    r".*docs\..*\.(com|org|io|dev)/.*",  # docs.company.com, docs.python.org, docs.site.io
    r".*documentation\..*\.(com|org|io)/.*",  # documentation.company.com
    r".*/docs/official/.*",            # /docs/official/ path
    r".*official-.*\.pdf",             # official-*.pdf files
    r"https?://docs\.[^/]+\.(org|com|io|dev)/.*",  # Explicit docs.* TLDs
]

VERIFIED_PATTERNS = [
    r".*\.edu/.*",                     # Educational institutions
    r".*\.gov/.*",                     # Government sources
    r".*wikipedia\.org/.*",            # Wikipedia
    r".*readthedocs\.io/.*",           # ReadTheDocs
    r".*/docs/verified/.*",            # /docs/verified/ path
]

TRUSTED_PATTERNS = [
    r".*medium\.com/@.*/.*",           # Medium posts by known authors
    r".*dev\.to/.*",                   # Dev.to posts
    r".*blog\..*\.com/.*",             # Company blogs
    r".*/knowledge/.*",                # Personal knowledge folder
    r".*/notes/.*",                    # Personal notes folder
]

COMMUNITY_PATTERNS = [
    r".*stackoverflow\.com/.*",        # Stack Overflow
    r".*reddit\.com/r/.*",             # Reddit
    r".*stackexchange\.com/.*",        # Stack Exchange
    r".*quora\.com/.*",                # Quora
    r".*discourse\.org/.*",            # Discourse forums
]

UNVERIFIED_PATTERNS = [
    r".*pastebin\.com/.*",             # Pastebin
    r".*gist\.github\.com/.*",         # Anonymous gists
    r".*/temp/.*",                     # Temporary folders
    r".*/inbox/.*",                    # Inbox (unprocessed)
    r".*/drafts/.*",                   # Drafts
]


@dataclass
class TrustScoreResult:
    """Result of trust score computation."""
    trust_level: TrustLevel
    base_score: float
    age_adjusted_score: float
    final_score: float
    age_days: float
    classification_source: str  # What pattern/metadata determined the level


class TrustScoringService:
    """
    Service for computing and managing source trust scores.

    Usage:
        service = TrustScoringService()
        result = service.compute_trust_score(
            source_path="https://docs.python.org/3/library/asyncio.html",
            created_at=datetime.now()
        )
        trust_score = result.final_score
    """

    def __init__(
        self,
        enabled: bool = TRUST_ENABLED,
        min_threshold: float = TRUST_MIN_THRESHOLD,
        decay_half_life_days: float = TRUST_DECAY_HALF_LIFE,
    ):
        """
        Initialize trust scoring service.

        Args:
            enabled: Whether trust scoring is enabled
            min_threshold: Minimum trust score to include in results
            decay_half_life_days: Half-life for age-based decay
        """
        self.enabled = enabled
        self.min_threshold = min_threshold
        self.decay_half_life_days = decay_half_life_days

        # Compile patterns for performance
        self._compiled_patterns = {
            TrustLevel.OFFICIAL: [re.compile(p, re.IGNORECASE) for p in OFFICIAL_PATTERNS],
            TrustLevel.VERIFIED: [re.compile(p, re.IGNORECASE) for p in VERIFIED_PATTERNS],
            TrustLevel.TRUSTED: [re.compile(p, re.IGNORECASE) for p in TRUSTED_PATTERNS],
            TrustLevel.COMMUNITY: [re.compile(p, re.IGNORECASE) for p in COMMUNITY_PATTERNS],
            TrustLevel.UNVERIFIED: [re.compile(p, re.IGNORECASE) for p in UNVERIFIED_PATTERNS],
        }

    def classify_source(self, source_path: str) -> Tuple[TrustLevel, str]:
        """
        Classify source into trust level based on path/URL patterns.

        Args:
            source_path: File path or URL of the source

        Returns:
            Tuple of (TrustLevel, pattern that matched)
        """
        # Normalize path for matching
        normalized_path = source_path.replace("\\", "/")

        # Check patterns in order of trust level (highest to lowest)
        for level in [
            TrustLevel.OFFICIAL,
            TrustLevel.VERIFIED,
            TrustLevel.TRUSTED,
            TrustLevel.COMMUNITY,
            TrustLevel.UNVERIFIED,
        ]:
            for pattern in self._compiled_patterns[level]:
                if pattern.match(normalized_path):
                    return level, pattern.pattern

        # Default to TRUSTED for local files (personal knowledge)
        if not source_path.startswith(("http://", "https://")):
            return TrustLevel.TRUSTED, "local_file_default"

        # Default to UNVERIFIED for unknown external sources
        return TrustLevel.UNVERIFIED, "unknown_external_default"

    def compute_age_decay(self, age_days: float) -> float:
        """
        Compute age-based decay factor using exponential decay.

        Uses half-life formula: decay = 2^(-age/half_life)
        - At age=0: decay=1.0 (no penalty)
        - At age=half_life: decay=0.5 (50% penalty)
        - At age=2*half_life: decay=0.25 (75% penalty)

        Args:
            age_days: Age of document in days

        Returns:
            Decay factor (0.0 to 1.0)
        """
        if age_days <= 0:
            return 1.0

        # Exponential decay: 2^(-age/half_life)
        import math
        decay = math.pow(2, -age_days / self.decay_half_life_days)

        # Clamp to reasonable range
        return max(0.1, min(1.0, decay))

    def compute_trust_score(
        self,
        source_path: str,
        created_at: Optional[datetime] = None,
        override_level: Optional[TrustLevel] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TrustScoreResult:
        """
        Compute final trust score for a document.

        Args:
            source_path: File path or URL of the source
            created_at: Document creation/modification date
            override_level: Override automatic classification
            metadata: Additional metadata (author, verification status, etc.)

        Returns:
            TrustScoreResult with score breakdown
        """
        if not self.enabled:
            return TrustScoreResult(
                trust_level=TrustLevel.TRUSTED,
                base_score=0.7,
                age_adjusted_score=0.7,
                final_score=0.7,
                age_days=0,
                classification_source="disabled",
            )

        # Determine trust level
        if override_level:
            trust_level = override_level
            classification_source = "override"
        else:
            trust_level, classification_source = self.classify_source(source_path)

        # Check metadata for verification status
        if metadata:
            verified = metadata.get("verified", False)
            author_trust = metadata.get("author_trust_score", 0)

            # Boost to VERIFIED if explicitly verified
            if verified and trust_level not in [TrustLevel.OFFICIAL, TrustLevel.VERIFIED]:
                trust_level = TrustLevel.VERIFIED
                classification_source = "verified_metadata"

            # Use author trust if higher than current level's score
            if author_trust > TRUST_SCORES[trust_level]:
                # Find matching level for author trust
                for level, score in sorted(TRUST_SCORES.items(), key=lambda x: -x[1]):
                    if author_trust >= score:
                        trust_level = level
                        classification_source = "author_trust_metadata"
                        break

        # Get base score for level
        base_score = TRUST_SCORES[trust_level]

        # Compute age factor
        age_days = 0.0
        if created_at:
            age_delta = datetime.now() - created_at
            age_days = age_delta.total_seconds() / 86400  # Convert to days

        age_decay = self.compute_age_decay(age_days)

        # Apply age decay
        age_adjusted_score = base_score * age_decay

        # Final score (can be further adjusted)
        final_score = age_adjusted_score

        return TrustScoreResult(
            trust_level=trust_level,
            base_score=base_score,
            age_adjusted_score=age_adjusted_score,
            final_score=final_score,
            age_days=age_days,
            classification_source=classification_source,
        )

    def filter_by_trust(
        self,
        results: List[Dict[str, Any]],
        min_score: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Filter search results by minimum trust score.

        Args:
            results: List of search results with 'trust_score' field
            min_score: Minimum trust score (uses default if not provided)

        Returns:
            Filtered list of results
        """
        if not self.enabled:
            return results

        threshold = min_score if min_score is not None else self.min_threshold

        filtered = []
        for result in results:
            score = result.get("trust_score", 0.5)  # Default to 0.5 if not set
            if score >= threshold:
                filtered.append(result)
            else:
                logger.debug(
                    f"Filtering low-trust result: score={score:.2f}, "
                    f"source={result.get('source', 'unknown')}"
                )

        return filtered

    def boost_by_trust(
        self,
        results: List[Dict[str, Any]],
        boost_factor: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Boost search result scores based on trust level.

        Higher trust = higher boost. Used in hybrid fusion to
        prioritize trusted sources.

        Args:
            results: List of search results with 'score' and 'trust_score' fields
            boost_factor: How much trust affects final score (0.0 to 1.0)

        Returns:
            Results with adjusted scores
        """
        if not self.enabled:
            return results

        for result in results:
            base_score = result.get("score", 0.5)
            trust_score = result.get("trust_score", 0.5)

            # Weighted combination
            boosted_score = base_score * (1 - boost_factor) + trust_score * boost_factor
            result["boosted_score"] = boosted_score
            result["original_score"] = base_score

        # Sort by boosted score
        results.sort(key=lambda x: x.get("boosted_score", 0), reverse=True)

        return results


def compute_trust_score(
    source_path: str,
    created_at: Optional[datetime] = None,
    **kwargs,
) -> float:
    """
    Quick trust score computation.

    Args:
        source_path: File path or URL of the source
        created_at: Document creation date
        **kwargs: Additional arguments for TrustScoringService

    Returns:
        Final trust score (0.0 to 1.0)
    """
    service = TrustScoringService()
    result = service.compute_trust_score(source_path, created_at, **kwargs)
    return result.final_score
