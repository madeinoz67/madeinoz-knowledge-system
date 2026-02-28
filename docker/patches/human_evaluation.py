"""
Human Evaluation Framework for LKAP (Feature 023 Enhancement)
RedTeam Gap #GAP-012: Add human evaluation feedback framework.

RAG Book Reference:
"Human evaluation samples essential for quality validation"

Components:
1. EvaluationSample: Queries sampled for human review
2. HumanReviewer: Evaluation with guidelines
3. InterRaterAgreement: Cohen's Kappa for consistency
4. ReviewQueue: Managing pending reviews

Environment Variables:
    MADEINOZ_KNOWLEDGE_HUMAN_EVAL_ENABLED: Enable human eval (default: true)
    MADEINOZ_KNOWLEDGE_HUMAN_EVAL_SAMPLE_RATE: % of queries to sample (default: 0.05)
    MADEINOZ_KNOWLEDGE_HUMAN_EVAL_MIN_REVIEWS: Min reviews per sample (default: 3)
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import random
import math

logger = logging.getLogger(__name__)

# Configuration with defaults
HUMAN_EVAL_ENABLED = os.getenv("MADEINOZ_KNOWLEDGE_HUMAN_EVAL_ENABLED", "true").lower() == "true"
HUMAN_EVAL_SAMPLE_RATE = float(os.getenv("MADEINOZ_KNOWLEDGE_HUMAN_EVAL_SAMPLE_RATE", "0.05"))
HUMAN_EVAL_MIN_REVIEWS = int(os.getenv("MADEINOZ_KNOWLEDGE_HUMAN_EVAL_MIN_REVIEWS", "3"))


class RelevanceGrade(str, Enum):
    """Relevance grades for evaluation."""
    PERFECT = "perfect"         # 4: Perfect answer
    HIGHLY_RELEVANT = "highly_relevant"  # 3: Highly relevant
    SOMEWHAT_RELEVANT = "somewhat_relevant"  # 2: Somewhat relevant
    MARGINAL = "marginal"       # 1: Marginally relevant
    NOT_RELEVANT = "not_relevant"  # 0: Not relevant


class EvaluationStatus(str, Enum):
    """Status of evaluation sample."""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    DISPUTED = "disputed"  # Reviewers disagree


@dataclass
class EvaluationGuideline:
    """Guidelines for human evaluators."""
    grade: RelevanceGrade
    description: str
    examples: List[str]


# Default evaluation guidelines based on RAG Book recommendations
DEFAULT_GUIDELINES = [
    EvaluationGuideline(
        grade=RelevanceGrade.PERFECT,
        description="Result directly answers the query with accurate, complete information.",
        examples=[
            "Query asks for API rate limit, result states exact limit with source",
            "Query asks for config file location, result gives exact path",
        ],
    ),
    EvaluationGuideline(
        grade=RelevanceGrade.HIGHLY_RELEVANT,
        description="Result contains most of the information needed, minor gaps.",
        examples=[
            "Query asks for all config options, result lists most with explanations",
            "Query asks how to fix X, result gives steps that work with minor modifications",
        ],
    ),
    EvaluationGuideline(
        grade=RelevanceGrade.SOMEWHAT_RELEVANT,
        description="Result is related but missing key information or has inaccuracies.",
        examples=[
            "Query asks about feature X, result discusses related feature Y",
            "Result contains partial answer that requires additional search",
        ],
    ),
    EvaluationGuideline(
        grade=RelevanceGrade.MARGINAL,
        description="Result is tangentially related but doesn't address the query.",
        examples=[
            "Query asks about Python, result is about general programming",
            "Result mentions keywords but doesn't answer the question",
        ],
    ),
    EvaluationGuideline(
        grade=RelevanceGrade.NOT_RELEVANT,
        description="Result is unrelated or completely wrong.",
        examples=[
            "Query asks about authentication, result is about deployment",
            "Result is spam, corrupted, or placeholder text",
        ],
    ),
]


@dataclass
class EvaluationSample:
    """A query and result sampled for human evaluation."""
    sample_id: str
    query: str
    result_chunk_id: str
    result_text: str
    confidence: float
    created_at: datetime
    status: EvaluationStatus = EvaluationStatus.PENDING
    reviews: List["HumanReview"] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "sample_id": self.sample_id,
            "query": self.query,
            "result_chunk_id": self.result_chunk_id,
            "result_text": self.result_text[:500],  # Truncate for storage
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "reviews": [r.to_dict() for r in self.reviews],
            "metadata": self.metadata,
        }


@dataclass
class HumanReview:
    """A single human review of a sample."""
    reviewer_id: str
    grade: RelevanceGrade
    comment: Optional[str] = None
    reviewed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    time_spent_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "reviewer_id": self.reviewer_id,
            "grade": self.grade.value,
            "comment": self.comment,
            "reviewed_at": self.reviewed_at.isoformat(),
            "time_spent_seconds": self.time_spent_seconds,
        }


@dataclass
class EvaluationStats:
    """Statistics from human evaluation."""
    total_samples: int
    completed_samples: int
    pending_samples: int
    disputed_samples: int
    avg_grade: float
    grade_distribution: Dict[str, int]
    inter_rater_agreement: Optional[float]  # Cohen's Kappa


class SampleSelector:
    """
    Selects queries for human evaluation.

    Strategies:
    - Random sampling
    - Low confidence sampling (queries with low retrieval confidence)
    - Stratified sampling (across query types)
    """

    def __init__(
        self,
        sample_rate: float = HUMAN_EVAL_SAMPLE_RATE,
        min_confidence_for_skip: float = 0.9,  # Skip very high confidence
        max_confidence_for_priority: float = 0.5,  # Priority for low confidence
    ):
        """
        Initialize sample selector.

        Args:
            sample_rate: Fraction of queries to sample (0.0-1.0)
            min_confidence_for_skip: Skip sampling for very high confidence
            max_confidence_for_priority: Always sample low confidence queries
        """
        self.sample_rate = sample_rate
        self.min_confidence_for_skip = min_confidence_for_skip
        self.max_confidence_for_priority = max_confidence_for_priority

    def should_sample(self, query: str, confidence: float) -> bool:
        """
        Determine if a query should be sampled for evaluation.

        Args:
            query: The query string
            confidence: Retrieval confidence score

        Returns:
            True if query should be sampled
        """
        # Always sample low confidence queries
        if confidence < self.max_confidence_for_priority:
            return True

        # Skip very high confidence queries (usually correct)
        if confidence > self.min_confidence_for_skip:
            return random.random() < (self.sample_rate / 5)  # Reduced rate

        # Standard random sampling
        return random.random() < self.sample_rate


class ReviewQueue:
    """
    Manages queue of samples pending human review.

    Supports:
    - Priority ordering (low confidence first)
    - Reviewer assignment
    - Queue statistics
    """

    def __init__(self, queue_path: Optional[Path] = None):
        """
        Initialize review queue.

        Args:
            queue_path: Path to persist queue state
        """
        self.queue_path = queue_path or Path.home() / ".lkap" / "review_queue.json"
        self.queue: List[EvaluationSample] = []

        # Load existing queue
        self._load_queue()

    def _load_queue(self) -> None:
        """Load queue from disk."""
        if self.queue_path.exists():
            try:
                with open(self.queue_path, "r") as f:
                    data = json.load(f)
                    self.queue = [self._deserialize_sample(s) for s in data]
            except Exception as e:
                logger.warning(f"Failed to load review queue: {e}")

    def _save_queue(self) -> None:
        """Persist queue to disk."""
        try:
            self.queue_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.queue_path, "w") as f:
                json.dump([s.to_dict() for s in self.queue], f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save review queue: {e}")

    def _deserialize_sample(self, data: Dict[str, Any]) -> EvaluationSample:
        """Deserialize sample from dict."""
        sample = EvaluationSample(
            sample_id=data["sample_id"],
            query=data["query"],
            result_chunk_id=data["result_chunk_id"],
            result_text=data["result_text"],
            confidence=data["confidence"],
            created_at=datetime.fromisoformat(data["created_at"]),
            status=EvaluationStatus(data["status"]),
            metadata=data.get("metadata", {}),
        )
        # Deserialize reviews
        for r in data.get("reviews", []):
            sample.reviews.append(HumanReview(
                reviewer_id=r["reviewer_id"],
                grade=RelevanceGrade(r["grade"]),
                comment=r.get("comment"),
                reviewed_at=datetime.fromisoformat(r["reviewed_at"]),
                time_spent_seconds=r.get("time_spent_seconds"),
            ))
        return sample

    def add_sample(self, sample: EvaluationSample) -> None:
        """Add sample to review queue."""
        self.queue.append(sample)
        self._save_queue()

    def get_next_sample(self, reviewer_id: Optional[str] = None) -> Optional[EvaluationSample]:
        """
        Get next sample for review.

        Priority: low confidence, then oldest first.

        Args:
            reviewer_id: Optional reviewer to assign

        Returns:
            Next sample or None if queue empty
        """
        pending = [s for s in self.queue if s.status == EvaluationStatus.PENDING]
        if not pending:
            return None

        # Sort by confidence (ascending), then by created_at
        pending.sort(key=lambda s: (s.confidence, s.created_at))
        sample = pending[0]
        sample.status = EvaluationStatus.IN_REVIEW
        self._save_queue()
        return sample

    def submit_review(self, sample_id: str, review: HumanReview) -> None:
        """Submit a review for a sample."""
        for sample in self.queue:
            if sample.sample_id == sample_id:
                sample.reviews.append(review)

                # Check if we have enough reviews
                if len(sample.reviews) >= HUMAN_EVAL_MIN_REVIEWS:
                    sample.status = EvaluationStatus.COMPLETED
                    # Check for disputes
                    grades = [r.grade for r in sample.reviews]
                    if self._has_disagreement(grades):
                        sample.status = EvaluationStatus.DISPUTED

                self._save_queue()
                return

        logger.warning(f"Sample {sample_id} not found in queue")

    def _has_disagreement(self, grades: List[RelevanceGrade]) -> bool:
        """Check if there's significant disagreement among reviewers."""
        if len(grades) < 2:
            return False

        # Map to numeric
        grade_values = {
            RelevanceGrade.PERFECT: 4,
            RelevanceGrade.HIGHLY_RELEVANT: 3,
            RelevanceGrade.SOMEWHAT_RELEVANT: 2,
            RelevanceGrade.MARGINAL: 1,
            RelevanceGrade.NOT_RELEVANT: 0,
        }

        values = [grade_values[g] for g in grades]
        variance = sum((v - sum(values) / len(values)) ** 2 for v in values) / len(values)

        # Variance > 1 indicates significant spread (e.g., some 4s and some 1s)
        return variance > 1.0

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            "total_samples": len(self.queue),
            "pending": sum(1 for s in self.queue if s.status == EvaluationStatus.PENDING),
            "in_review": sum(1 for s in self.queue if s.status == EvaluationStatus.IN_REVIEW),
            "completed": sum(1 for s in self.queue if s.status == EvaluationStatus.COMPLETED),
            "disputed": sum(1 for s in self.queue if s.status == EvaluationStatus.DISPUTED),
        }


class InterRaterAgreement:
    """
    Calculates inter-rater agreement using Cohen's Kappa.

    Kappa interpretation:
    - < 0: Disagreement
    - 0-0.2: Slight agreement
    - 0.2-0.4: Fair agreement
    - 0.4-0.6: Moderate agreement
    - 0.6-0.8: Substantial agreement
    - 0.8-1.0: Almost perfect agreement
    """

    @staticmethod
    def calculate_cohens_kappa(reviews: List[List[RelevanceGrade]]) -> float:
        """
        Calculate Cohen's Kappa for multiple samples with 2 raters.

        Args:
            reviews: List of [rater1_grade, rater2_grade] pairs

        Returns:
            Kappa coefficient (-1 to 1)
        """
        if len(reviews) < 2:
            return 0.0

        # Convert to numeric matrix
        grade_values = {
            RelevanceGrade.PERFECT: 4,
            RelevanceGrade.HIGHLY_RELEVANT: 3,
            RelevanceGrade.SOMEWHAT_RELEVANT: 2,
            RelevanceGrade.MARGINAL: 1,
            RelevanceGrade.NOT_RELEVANT: 0,
        }

        n = len(reviews)  # Number of samples
        k = 5  # Number of categories

        # Build confusion matrix
        matrix = [[0] * k for _ in range(k)]
        for sample_reviews in reviews:
            if len(sample_reviews) >= 2:
                r1 = grade_values[sample_reviews[0]]
                r2 = grade_values[sample_reviews[1]]
                matrix[r1][r2] += 1

        # Calculate observed agreement (Po)
        agreement_count = sum(matrix[i][i] for i in range(k))
        po = agreement_count / n if n > 0 else 0

        # Calculate expected agreement (Pe)
        row_sums = [sum(matrix[i]) for i in range(k)]
        col_sums = [sum(matrix[i][j] for i in range(k)) for j in range(k)]
        total = sum(row_sums)

        if total == 0:
            return 0.0

        pe = sum((row_sums[i] / total) * (col_sums[i] / total) for i in range(k))

        # Calculate Kappa
        if pe == 1.0:
            return 1.0 if po == 1.0 else 0.0

        kappa = (po - pe) / (1 - pe)
        return kappa

    @staticmethod
    def interpret_kappa(kappa: float) -> str:
        """Interpret kappa coefficient."""
        if kappa < 0:
            return "disagreement"
        elif kappa < 0.2:
            return "slight agreement"
        elif kappa < 0.4:
            return "fair agreement"
        elif kappa < 0.6:
            return "moderate agreement"
        elif kappa < 0.8:
            return "substantial agreement"
        else:
            return "almost perfect agreement"


class HumanEvaluationFramework:
    """
    Main framework for human evaluation.

    Usage:
        framework = HumanEvaluationFramework()
        framework.sample_query("What is the API rate limit?", result, 0.75)
        sample = framework.get_next_sample()
        framework.submit_review(sample.sample_id, review)
    """

    def __init__(
        self,
        enabled: bool = HUMAN_EVAL_ENABLED,
        sample_rate: float = HUMAN_EVAL_SAMPLE_RATE,
        min_reviews: int = HUMAN_EVAL_MIN_REVIEWS,
        queue_path: Optional[Path] = None,
    ):
        """
        Initialize human evaluation framework.

        Args:
            enabled: Whether human evaluation is enabled
            sample_rate: Fraction of queries to sample
            min_reviews: Minimum reviews per sample
            queue_path: Path for queue persistence
        """
        self.enabled = enabled
        self.min_reviews = min_reviews
        self.selector = SampleSelector(sample_rate=sample_rate)
        self.queue = ReviewQueue(queue_path=queue_path)
        self.guidelines = DEFAULT_GUIDELINES

        # Statistics
        self._sample_count = 0

    def sample_query(
        self,
        query: str,
        result: Dict[str, Any],
        confidence: float,
    ) -> Optional[EvaluationSample]:
        """
        Sample a query for potential human evaluation.

        Args:
            query: User query
            result: Search result dictionary
            confidence: Retrieval confidence

        Returns:
            EvaluationSample if sampled, None otherwise
        """
        if not self.enabled:
            return None

        if not self.selector.should_sample(query, confidence):
            return None

        sample = EvaluationSample(
            sample_id=f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self._sample_count}",
            query=query,
            result_chunk_id=result.get("chunk_id", "unknown"),
            result_text=result.get("text", ""),
            confidence=confidence,
            created_at=datetime.now(timezone.utc),
            metadata={
                "retrieval_confidence": confidence,
                "chunk_id": result.get("chunk_id"),
            },
        )

        self._sample_count += 1
        self.queue.add_sample(sample)

        logger.info(f"Sampled query for evaluation: {sample.sample_id}")
        return sample

    def get_next_sample(self) -> Optional[EvaluationSample]:
        """Get next sample for review."""
        return self.queue.get_next_sample()

    def submit_review(
        self,
        sample_id: str,
        reviewer_id: str,
        grade: RelevanceGrade,
        comment: Optional[str] = None,
        time_spent_seconds: Optional[float] = None,
    ) -> None:
        """
        Submit a human review.

        Args:
            sample_id: Sample to review
            reviewer_id: Reviewer identifier
            grade: Relevance grade
            comment: Optional comment
            time_spent_seconds: Time spent on review
        """
        review = HumanReview(
            reviewer_id=reviewer_id,
            grade=grade,
            comment=comment,
            time_spent_seconds=time_spent_seconds,
        )
        self.queue.submit_review(sample_id, review)

    def get_evaluation_stats(self) -> EvaluationStats:
        """Get evaluation statistics."""
        queue_stats = self.queue.get_stats()

        # Calculate grade distribution from completed samples
        grade_distribution = {g.value: 0 for g in RelevanceGrade}
        total_grades = 0
        grade_sum = 0

        grade_values = {
            RelevanceGrade.PERFECT: 4,
            RelevanceGrade.HIGHLY_RELEVANT: 3,
            RelevanceGrade.SOMEWHAT_RELEVANT: 2,
            RelevanceGrade.MARGINAL: 1,
            RelevanceGrade.NOT_RELEVANT: 0,
        }

        reviews_for_kappa = []

        for sample in self.queue.queue:
            for review in sample.reviews:
                grade_distribution[review.grade.value] += 1
                grade_sum += grade_values[review.grade]
                total_grades += 1

            # Collect for kappa calculation (need 2+ reviews)
            if len(sample.reviews) >= 2:
                reviews_for_kappa.append([r.grade for r in sample.reviews[:2]])

        # Calculate inter-rater agreement
        kappa = InterRaterAgreement.calculate_cohens_kappa(reviews_for_kappa)

        return EvaluationStats(
            total_samples=queue_stats["total_samples"],
            completed_samples=queue_stats["completed"],
            pending_samples=queue_stats["pending"],
            disputed_samples=queue_stats["disputed"],
            avg_grade=grade_sum / total_grades if total_grades > 0 else 0,
            grade_distribution=grade_distribution,
            inter_rater_agreement=kappa,
        )

    def get_guidelines(self) -> List[EvaluationGuideline]:
        """Get evaluation guidelines."""
        return self.guidelines

    def export_results(self, output_path: Path) -> None:
        """Export evaluation results for analysis."""
        stats = self.get_evaluation_stats()

        output = {
            "stats": {
                "total_samples": stats.total_samples,
                "completed_samples": stats.completed_samples,
                "pending_samples": stats.pending_samples,
                "disputed_samples": stats.disputed_samples,
                "avg_grade": stats.avg_grade,
                "grade_distribution": stats.grade_distribution,
                "inter_rater_agreement": stats.inter_rater_agreement,
                "agreement_interpretation": InterRaterAgreement.interpret_kappa(
                    stats.inter_rater_agreement
                ) if stats.inter_rater_agreement is not None else None,
            },
            "samples": [s.to_dict() for s in self.queue.queue],
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)


# Convenience functions
def create_sample(
    query: str,
    result: Dict[str, Any],
    confidence: float,
) -> Optional[EvaluationSample]:
    """Quick sample creation."""
    framework = HumanEvaluationFramework()
    return framework.sample_query(query, result, confidence)
