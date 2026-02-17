"""
Quality Scoring for LKAP (Feature 023 Enhancement)
RedTeam Gap #GAP-009: Add quality scoring at ingestion.
RedTeam Gap #GAP-010: Add garbage detection for corrupted content.

RAG Book Reference:
"Documents below threshold get flagged for review or excluded."
"Placeholder text, 'lorem ipsum', corrupted exports"

Quality scoring considers:
- Freshness: How recent is the information?
- Completeness: Does the document have adequate content?
- Authority: Is the source trustworthy?
- Entropy: Does the content have meaningful information density?
- Language: Is it valid content or gibberish?

Environment Variables:
    MADEINOZ_KNOWLEDGE_QUALITY_SCORING_ENABLED: Enable quality scoring (default: true)
    MADEINOZ_KNOWLEDGE_QUALITY_MIN_SCORE: Minimum quality score to accept (default: 0.3)
    MADEINOZ_KNOWLEDGE_QUALITY_FRESHNESS_HALF_LIFE: Days for freshness decay (default: 365)
"""

import logging
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Configuration with defaults
QUALITY_SCORING_ENABLED = os.getenv("MADEINOZ_KNOWLEDGE_QUALITY_SCORING_ENABLED", "true").lower() == "true"
QUALITY_MIN_SCORE = float(os.getenv("MADEINOZ_KNOWLEDGE_QUALITY_MIN_SCORE", "0.3"))
QUALITY_FRESHNESS_HALF_LIFE = int(os.getenv("MADEINOZ_KNOWLEDGE_QUALITY_FRESHNESS_HALF_LIFE", "365"))


class QualityFactor(str, Enum):
    """Factors contributing to quality score."""
    FRESHNESS = "freshness"
    COMPLETENESS = "completeness"
    AUTHORITY = "authority"
    ENTROPY = "entropy"
    LANGUAGE = "language"


class QualityLevel(str, Enum):
    """Quality level classification."""
    EXCELLENT = "excellent"     # 0.9 - 1.0
    GOOD = "good"               # 0.7 - 0.9
    ACCEPTABLE = "acceptable"   # 0.5 - 0.7
    POOR = "poor"               # 0.3 - 0.5
    UNACCEPTABLE = "unacceptable"  # < 0.3


@dataclass
class QualityScoreResult:
    """Result of quality scoring."""
    score: float
    level: QualityLevel
    factors: Dict[str, float]
    flags: List[str]
    is_garbage: bool
    garbage_reason: Optional[str] = None


# Garbage detection patterns
GARBAGE_PATTERNS = [
    r"lorem\s+ipsum",
    r"dolor\s+sit\s+amet",
    r"placeholder\s+text",
    r"insert\s+text\s+here",
    r"\[?\s*tbd\s*\]?",  # To be determined
    r"\[?\s*todo\s*\]?",  # Todo
    r"coming\s+soon",
    r"under\s+construction",
    r"page\s+\d+\s+of\s+\d+",  # Just page numbers
]

# Low-entropy patterns (repeated characters)
LOW_ENTROPY_PATTERNS = [
    r"(.)\1{10,}",  # Same character repeated 10+ times
    r"(\S+\s+){10,}\1",  # Same word pattern repeated
]

# Minimum thresholds
MIN_CHUNK_LENGTH = 50  # Minimum characters for valid content
MIN_UNIQUE_WORDS = 10  # Minimum unique words
MIN_ENTROPY = 2.0  # Minimum Shannon entropy (bits/char)


class GarbageDetector:
    """
    Detects garbage, placeholder, and corrupted content.

    RAG Book Reference:
    "Placeholder text, 'lorem ipsum', corrupted exports"
    """

    def __init__(
        self,
        min_chunk_length: int = MIN_CHUNK_LENGTH,
        min_unique_words: int = MIN_UNIQUE_WORDS,
        min_entropy: float = MIN_ENTROPY,
    ):
        """
        Initialize garbage detector.

        Args:
            min_chunk_length: Minimum character length
            min_unique_words: Minimum unique words
            min_entropy: Minimum Shannon entropy
        """
        self.min_chunk_length = min_chunk_length
        self.min_unique_words = min_unique_words
        self.min_entropy = min_entropy

        # Compile patterns
        self.garbage_patterns = [re.compile(p, re.IGNORECASE) for p in GARBAGE_PATTERNS]
        self.low_entropy_patterns = [re.compile(p, re.IGNORECASE) for p in LOW_ENTROPY_PATTERNS]

    def detect(self, content: str) -> Tuple[bool, Optional[str]]:
        """
        Detect if content is garbage.

        Args:
            content: Content to analyze

        Returns:
            Tuple of (is_garbage, reason)
        """
        if not content or not content.strip():
            return True, "empty_content"

        # Check minimum length
        if len(content.strip()) < self.min_chunk_length:
            return True, f"too_short ({len(content.strip())} < {self.min_chunk_length})"

        # Check for garbage patterns
        for pattern in self.garbage_patterns:
            if pattern.search(content):
                return True, f"placeholder_detected ({pattern.pattern[:20]}...)"

        # Check for low-entropy patterns
        for pattern in self.low_entropy_patterns:
            if pattern.search(content):
                return True, f"low_entropy_pattern ({pattern.pattern[:20]}...)"

        # Calculate Shannon entropy
        entropy = self._calculate_entropy(content)
        if entropy < self.min_entropy:
            return True, f"low_entropy ({entropy:.2f} < {self.min_entropy})"

        # Check unique word count
        words = set(content.lower().split())
        if len(words) < self.min_unique_words:
            return True, f"few_unique_words ({len(words)} < {self.min_unique_words})"

        return False, None

    def _calculate_entropy(self, content: str) -> float:
        """
        Calculate Shannon entropy of content.

        Higher entropy = more information density.
        Lower entropy = more repetitive/predictable.
        """
        if not content:
            return 0.0

        # Count character frequencies
        freq = {}
        for char in content:
            freq[char] = freq.get(char, 0) + 1

        # Calculate entropy
        total = len(content)
        entropy = 0.0
        for count in freq.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)

        return entropy

    def get_entropy_score(self, content: str) -> float:
        """
        Get normalized entropy score (0-1).

        Good content typically has entropy > 3.0
        Garbage/patterns typically have entropy < 2.0
        """
        entropy = self._calculate_entropy(content)
        # Normalize: 3.0+ = 1.0, 0.0 = 0.0
        return min(1.0, entropy / 3.0)


class QualityScorer:
    """
    Computes quality score for documents.

    Quality = freshness * completeness * authority * entropy

    RAG Book Reference:
    "Documents below threshold get flagged for review or excluded"
    """

    def __init__(
        self,
        enabled: bool = QUALITY_SCORING_ENABLED,
        min_score: float = QUALITY_MIN_SCORE,
        freshness_half_life: int = QUALITY_FRESHNESS_HALF_LIFE,
        garbage_detector: Optional[GarbageDetector] = None,
    ):
        """
        Initialize quality scorer.

        Args:
            enabled: Whether quality scoring is enabled
            min_score: Minimum acceptable quality score
            freshness_half_life: Days for freshness to decay by half
            garbage_detector: Optional garbage detector instance
        """
        self.enabled = enabled
        self.min_score = min_score
        self.freshness_half_life = freshness_half_life
        self.garbage_detector = garbage_detector or GarbageDetector()

        # Stats tracking
        self._scored_count = 0
        self._rejected_count = 0
        self._garbage_count = 0

    def compute_score(
        self,
        content: str,
        source_date: Optional[datetime] = None,
        trust_score: float = 0.7,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> QualityScoreResult:
        """
        Compute quality score for content.

        Args:
            content: Content to score
            source_date: Date the content was created/modified
            trust_score: Trust score of the source (0-1)
            metadata: Optional additional metadata

        Returns:
            QualityScoreResult with score, level, and flags
        """
        if not self.enabled:
            return QualityScoreResult(
                score=0.7,
                level=QualityLevel.GOOD,
                factors={},
                flags=[],
                is_garbage=False,
            )

        flags = []
        factors = {}

        # 1. Check for garbage first
        is_garbage, garbage_reason = self.garbage_detector.detect(content)
        if is_garbage:
            self._garbage_count += 1
            return QualityScoreResult(
                score=0.0,
                level=QualityLevel.UNACCEPTABLE,
                factors={},
                flags=[f"garbage:{garbage_reason}"],
                is_garbage=True,
                garbage_reason=garbage_reason,
            )

        # 2. Freshness score (exponential decay)
        freshness = self._compute_freshness(source_date)
        factors[QualityFactor.FRESHNESS.value] = freshness
        if freshness < 0.5:
            flags.append("stale_content")

        # 3. Completeness score (length and structure)
        completeness = self._compute_completeness(content)
        factors[QualityFactor.COMPLETENESS.value] = completeness
        if completeness < 0.5:
            flags.append("incomplete_content")

        # 4. Authority score (from trust score)
        authority = trust_score
        factors[QualityFactor.AUTHORITY.value] = authority
        if authority < 0.5:
            flags.append("low_authority")

        # 5. Entropy score (information density)
        entropy = self.garbage_detector.get_entropy_score(content)
        factors[QualityFactor.ENTROPY.value] = entropy
        if entropy < 0.5:
            flags.append("low_entropy")

        # Compute weighted average
        # Weights: freshness=0.2, completeness=0.2, authority=0.3, entropy=0.3
        weights = {
            QualityFactor.FRESHNESS.value: 0.2,
            QualityFactor.COMPLETENESS.value: 0.2,
            QualityFactor.AUTHORITY.value: 0.3,
            QualityFactor.ENTROPY.value: 0.3,
        }

        total_score = sum(
            factors.get(factor, 0.5) * weight
            for factor, weight in weights.items()
        )

        # Determine quality level
        level = self._get_quality_level(total_score)

        # Track stats
        self._scored_count += 1
        if total_score < self.min_score:
            self._rejected_count += 1
            flags.append("below_threshold")

        return QualityScoreResult(
            score=total_score,
            level=level,
            factors=factors,
            flags=flags,
            is_garbage=False,
        )

    def _compute_freshness(self, source_date: Optional[datetime]) -> float:
        """Compute freshness score based on age."""
        if source_date is None:
            return 0.7  # Default for unknown date

        # Ensure timezone-aware
        if source_date.tzinfo is None:
            source_date = source_date.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        age_days = (now - source_date).total_seconds() / 86400

        # Exponential decay: score = 0.5^(age / half_life)
        decay_rate = math.log(0.5) / self.freshness_half_life
        freshness = math.exp(decay_rate * age_days)

        return max(0.1, min(1.0, freshness))

    def _compute_completeness(self, content: str) -> float:
        """Compute completeness score based on content structure."""
        if not content:
            return 0.0

        score = 0.0

        # Length factor (target: 500+ chars)
        length = len(content)
        if length >= 500:
            score += 0.3
        elif length >= 200:
            score += 0.2
        elif length >= 100:
            score += 0.1

        # Word count factor (target: 100+ words)
        words = content.split()
        if len(words) >= 100:
            score += 0.3
        elif len(words) >= 50:
            score += 0.2
        elif len(words) >= 20:
            score += 0.1

        # Sentence count factor (target: 5+ sentences)
        sentences = len(re.split(r"[.!?]+", content))
        if sentences >= 5:
            score += 0.2
        elif sentences >= 3:
            score += 0.1

        # Structure factor (headings, paragraphs)
        has_structure = bool(re.search(r"^#+\s+", content, re.MULTILINE))  # Markdown headings
        has_paragraphs = content.count("\n\n") >= 2
        if has_structure or has_paragraphs:
            score += 0.2

        return min(1.0, score)

    def _get_quality_level(self, score: float) -> QualityLevel:
        """Determine quality level from score."""
        if score >= 0.9:
            return QualityLevel.EXCELLENT
        elif score >= 0.7:
            return QualityLevel.GOOD
        elif score >= 0.5:
            return QualityLevel.ACCEPTABLE
        elif score >= 0.3:
            return QualityLevel.POOR
        else:
            return QualityLevel.UNACCEPTABLE

    def should_accept(self, result: QualityScoreResult) -> bool:
        """Check if content should be accepted based on quality."""
        if result.is_garbage:
            return False
        return result.score >= self.min_score

    def get_stats(self) -> Dict[str, Any]:
        """Get quality scoring statistics."""
        return {
            "enabled": self.enabled,
            "min_score": self.min_score,
            "scored_count": self._scored_count,
            "rejected_count": self._rejected_count,
            "garbage_count": self._garbage_count,
            "rejection_rate": (
                self._rejected_count / self._scored_count
                if self._scored_count > 0
                else 0
            ),
        }


class QualityFilter:
    """
    Filters documents based on quality score.

    Usage:
        filter = QualityFilter()
        filtered = filter.filter(documents)
    """

    def __init__(
        self,
        min_score: float = QUALITY_MIN_SCORE,
        reject_garbage: bool = True,
    ):
        """
        Initialize quality filter.

        Args:
            min_score: Minimum quality score to pass
            reject_garbage: Whether to reject garbage content
        """
        self.min_score = min_score
        self.reject_garbage = reject_garbage
        self.scorer = QualityScorer(min_score=min_score)

    def filter(
        self,
        documents: List[Dict[str, Any]],
        content_key: str = "content",
    ) -> List[Dict[str, Any]]:
        """
        Filter documents by quality.

        Args:
            documents: List of document dictionaries
            content_key: Key for content field

        Returns:
            Filtered list of documents
        """
        filtered = []

        for doc in documents:
            content = doc.get(content_key, "")
            source_date = doc.get("source_date") or doc.get("created_at")
            trust_score = doc.get("trust_score", 0.7)

            # Convert string dates
            if isinstance(source_date, str):
                try:
                    source_date = datetime.fromisoformat(source_date.replace("Z", "+00:00"))
                except ValueError:
                    source_date = None

            result = self.scorer.compute_score(
                content=content,
                source_date=source_date,
                trust_score=trust_score,
                metadata=doc,
            )

            # Skip garbage
            if result.is_garbage and self.reject_garbage:
                continue

            # Skip low quality
            if result.score < self.min_score:
                continue

            # Add quality metadata
            doc["quality_score"] = result.score
            doc["quality_level"] = result.level.value
            doc["quality_factors"] = result.factors
            if result.flags:
                doc["quality_flags"] = result.flags

            filtered.append(doc)

        return filtered


# Convenience functions
def compute_quality_score(
    content: str,
    source_date: Optional[datetime] = None,
    trust_score: float = 0.7,
) -> QualityScoreResult:
    """
    Quick quality score computation.

    Args:
        content: Content to score
        source_date: Date the content was created
        trust_score: Trust score of the source

    Returns:
        QualityScoreResult
    """
    scorer = QualityScorer()
    return scorer.compute_score(content, source_date, trust_score)


def is_garbage(content: str) -> Tuple[bool, Optional[str]]:
    """
    Quick garbage check.

    Args:
        content: Content to check

    Returns:
        Tuple of (is_garbage, reason)
    """
    detector = GarbageDetector()
    return detector.detect(content)
