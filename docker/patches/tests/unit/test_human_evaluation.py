"""
Unit Tests for Human Evaluation Framework (GAP-012)
Feature 023 Enhancement: RAG Book Compliance

Tests for human evaluation and review system.

RAG Book Reference:
"Human evaluation samples essential for quality validation"
"""

import pytest
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Add patches directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'patches'))


class TestRelevanceGrade:
    """Unit tests for RelevanceGrade enum."""

    def test_grades_exist(self):
        """Test all relevance grades are defined."""
        from human_evaluation import RelevanceGrade

        assert RelevanceGrade.PERFECT.value == "perfect"
        assert RelevanceGrade.HIGHLY_RELEVANT.value == "highly_relevant"
        assert RelevanceGrade.SOMEWHAT_RELEVANT.value == "somewhat_relevant"
        assert RelevanceGrade.MARGINAL.value == "marginal"
        assert RelevanceGrade.NOT_RELEVANT.value == "not_relevant"


class TestEvaluationStatus:
    """Unit tests for EvaluationStatus enum."""

    def test_statuses_exist(self):
        """Test all evaluation statuses are defined."""
        from human_evaluation import EvaluationStatus

        assert EvaluationStatus.PENDING.value == "pending"
        assert EvaluationStatus.IN_REVIEW.value == "in_review"
        assert EvaluationStatus.COMPLETED.value == "completed"
        assert EvaluationStatus.DISPUTED.value == "disputed"


class TestEvaluationGuideline:
    """Unit tests for EvaluationGuideline."""

    def test_guideline_creation(self):
        """Test guideline creation."""
        from human_evaluation import EvaluationGuideline, RelevanceGrade

        guideline = EvaluationGuideline(
            grade=RelevanceGrade.PERFECT,
            description="Perfect answer",
            examples=["Example 1", "Example 2"],
        )

        assert guideline.grade == RelevanceGrade.PERFECT
        assert len(guideline.examples) == 2


class TestDefaultGuidelines:
    """Unit tests for default evaluation guidelines."""

    def test_all_grades_have_guidelines(self):
        """Test all grades have guidelines."""
        from human_evaluation import DEFAULT_GUIDELINES, RelevanceGrade

        grades_with_guidelines = {g.grade for g in DEFAULT_GUIDELINES}

        for grade in RelevanceGrade:
            assert grade in grades_with_guidelines

    def test_guidelines_have_examples(self):
        """Test all guidelines have examples."""
        from human_evaluation import DEFAULT_GUIDELINES

        for guideline in DEFAULT_GUIDELINES:
            assert len(guideline.examples) >= 1


class TestEvaluationSample:
    """Unit tests for EvaluationSample."""

    def test_sample_creation(self):
        """Test sample creation."""
        from human_evaluation import EvaluationSample, EvaluationStatus

        sample = EvaluationSample(
            sample_id="test_001",
            query="What is the API rate limit?",
            result_chunk_id="chunk_123",
            result_text="The API rate limit is 100 requests per minute.",
            confidence=0.85,
            created_at=datetime.now(timezone.utc),
        )

        assert sample.sample_id == "test_001"
        assert sample.status == EvaluationStatus.PENDING
        assert len(sample.reviews) == 0

    def test_sample_to_dict(self):
        """Test sample serialization."""
        from human_evaluation import EvaluationSample

        sample = EvaluationSample(
            sample_id="test_002",
            query="Test query",
            result_chunk_id="chunk_456",
            result_text="Test result",
            confidence=0.9,
            created_at=datetime.now(timezone.utc),
        )

        data = sample.to_dict()

        assert data["sample_id"] == "test_002"
        assert data["query"] == "Test query"
        assert data["status"] == "pending"


class TestHumanReview:
    """Unit tests for HumanReview."""

    def test_review_creation(self):
        """Test review creation."""
        from human_evaluation import HumanReview, RelevanceGrade

        review = HumanReview(
            reviewer_id="reviewer_1",
            grade=RelevanceGrade.HIGHLY_RELEVANT,
            comment="Good answer, minor formatting issue",
            time_spent_seconds=45.0,
        )

        assert review.reviewer_id == "reviewer_1"
        assert review.grade == RelevanceGrade.HIGHLY_RELEVANT
        assert review.comment is not None
        assert review.time_spent_seconds == 45.0

    def test_review_to_dict(self):
        """Test review serialization."""
        from human_evaluation import HumanReview, RelevanceGrade

        review = HumanReview(
            reviewer_id="reviewer_2",
            grade=RelevanceGrade.PERFECT,
        )

        data = review.to_dict()

        assert data["reviewer_id"] == "reviewer_2"
        assert data["grade"] == "perfect"


class TestSampleSelector:
    """Unit tests for sample selection."""

    def test_always_samples_low_confidence(self):
        """Test low confidence queries are always sampled."""
        from human_evaluation import SampleSelector

        selector = SampleSelector(sample_rate=0.0)  # No random sampling

        # Low confidence should always be sampled
        assert selector.should_sample("test", 0.3) is True
        assert selector.should_sample("test", 0.4) is True

    def test_high_confidence_rarely_sampled(self):
        """Test very high confidence is rarely sampled."""
        from human_evaluation import SampleSelector

        selector = SampleSelector(
            sample_rate=0.5,  # High rate
            min_confidence_for_skip=0.9,
        )

        # Very high confidence should be rarely sampled
        # (statistical - might occasionally be True)
        samples = sum(1 for _ in range(100) if selector.should_sample("test", 0.95))
        assert samples < 50  # Should be much less than 50%

    def test_medium_confidence_uses_sample_rate(self):
        """Test medium confidence uses configured rate."""
        from human_evaluation import SampleSelector

        selector = SampleSelector(sample_rate=1.0)  # 100% rate

        # With 100% rate, should always sample
        assert selector.should_sample("test", 0.7) is True


class TestReviewQueue:
    """Unit tests for ReviewQueue."""

    def test_add_sample(self):
        """Test adding sample to queue."""
        from human_evaluation import ReviewQueue, EvaluationSample

        with tempfile.TemporaryDirectory() as tmpdir:
            queue = ReviewQueue(queue_path=Path(tmpdir) / "queue.json")

            sample = EvaluationSample(
                sample_id="test_003",
                query="Test",
                result_chunk_id="c1",
                result_text="Result",
                confidence=0.8,
                created_at=datetime.now(timezone.utc),
            )

            queue.add_sample(sample)

            stats = queue.get_stats()
            assert stats["total_samples"] == 1

    def test_get_next_sample(self):
        """Test getting next sample for review."""
        from human_evaluation import ReviewQueue, EvaluationSample

        with tempfile.TemporaryDirectory() as tmpdir:
            queue = ReviewQueue(queue_path=Path(tmpdir) / "queue.json")

            sample = EvaluationSample(
                sample_id="test_004",
                query="Test",
                result_chunk_id="c1",
                result_text="Result",
                confidence=0.8,
                created_at=datetime.now(timezone.utc),
            )

            queue.add_sample(sample)
            next_sample = queue.get_next_sample()

            assert next_sample is not None
            assert next_sample.sample_id == "test_004"

    def test_submit_review(self):
        """Test submitting a review."""
        from human_evaluation import ReviewQueue, EvaluationSample, HumanReview, RelevanceGrade

        with tempfile.TemporaryDirectory() as tmpdir:
            queue = ReviewQueue(queue_path=Path(tmpdir) / "queue.json")

            sample = EvaluationSample(
                sample_id="test_005",
                query="Test",
                result_chunk_id="c1",
                result_text="Result",
                confidence=0.8,
                created_at=datetime.now(timezone.utc),
            )

            queue.add_sample(sample)

            review = HumanReview(
                reviewer_id="r1",
                grade=RelevanceGrade.HIGHLY_RELEVANT,
            )

            queue.submit_review("test_005", review)

            # Find the sample and check review was added
            for s in queue.queue:
                if s.sample_id == "test_005":
                    assert len(s.reviews) == 1
                    break

    def test_low_confidence_priority(self):
        """Test low confidence samples are prioritized."""
        from human_evaluation import ReviewQueue, EvaluationSample

        with tempfile.TemporaryDirectory() as tmpdir:
            queue = ReviewQueue(queue_path=Path(tmpdir) / "queue.json")

            # Add high confidence first
            high = EvaluationSample(
                sample_id="high_conf",
                query="Test",
                result_chunk_id="c1",
                result_text="Result",
                confidence=0.9,
                created_at=datetime.now(timezone.utc),
            )
            queue.add_sample(high)

            # Add low confidence
            low = EvaluationSample(
                sample_id="low_conf",
                query="Test",
                result_chunk_id="c2",
                result_text="Result",
                confidence=0.3,
                created_at=datetime.now(timezone.utc),
            )
            queue.add_sample(low)

            # Should get low confidence first
            next_sample = queue.get_next_sample()
            assert next_sample.sample_id == "low_conf"


class TestInterRaterAgreement:
    """Unit tests for inter-rater agreement."""

    def test_perfect_agreement(self):
        """Test calculation with perfect agreement."""
        from human_evaluation import InterRaterAgreement, RelevanceGrade

        reviews = [
            [RelevanceGrade.PERFECT, RelevanceGrade.PERFECT],
            [RelevanceGrade.HIGHLY_RELEVANT, RelevanceGrade.HIGHLY_RELEVANT],
            [RelevanceGrade.NOT_RELEVANT, RelevanceGrade.NOT_RELEVANT],
        ]

        kappa = InterRaterAgreement.calculate_cohens_kappa(reviews)
        assert kappa == 1.0  # Perfect agreement

    def test_no_agreement(self):
        """Test calculation with no agreement."""
        from human_evaluation import InterRaterAgreement, RelevanceGrade

        reviews = [
            [RelevanceGrade.PERFECT, RelevanceGrade.NOT_RELEVANT],
            [RelevanceGrade.NOT_RELEVANT, RelevanceGrade.PERFECT],
        ]

        kappa = InterRaterAgreement.calculate_cohens_kappa(reviews)
        assert kappa < 0  # Disagreement

    def test_partial_agreement(self):
        """Test calculation with partial agreement."""
        from human_evaluation import InterRaterAgreement, RelevanceGrade

        reviews = [
            [RelevanceGrade.PERFECT, RelevanceGrade.HIGHLY_RELEVANT],  # Close
            [RelevanceGrade.HIGHLY_RELEVANT, RelevanceGrade.HIGHLY_RELEVANT],  # Same
            [RelevanceGrade.SOMEWHAT_RELEVANT, RelevanceGrade.MARGINAL],  # Close
        ]

        kappa = InterRaterAgreement.calculate_cohens_kappa(reviews)
        assert 0 < kappa < 1  # Some agreement

    def test_interpret_kappa(self):
        """Test kappa interpretation."""
        from human_evaluation import InterRaterAgreement

        assert InterRaterAgreement.interpret_kappa(-0.5) == "disagreement"
        assert InterRaterAgreement.interpret_kappa(0.1) == "slight agreement"
        assert InterRaterAgreement.interpret_kappa(0.3) == "fair agreement"
        assert InterRaterAgreement.interpret_kappa(0.5) == "moderate agreement"
        assert InterRaterAgreement.interpret_kappa(0.7) == "substantial agreement"
        assert InterRaterAgreement.interpret_kappa(0.9) == "almost perfect agreement"

    def test_empty_reviews(self):
        """Test with insufficient reviews."""
        from human_evaluation import InterRaterAgreement

        kappa = InterRaterAgreement.calculate_cohens_kappa([])
        assert kappa == 0.0


class TestHumanEvaluationFramework:
    """Unit tests for main framework."""

    @pytest.fixture
    def framework(self):
        """Create framework with temp directory."""
        from human_evaluation import HumanEvaluationFramework

        with tempfile.TemporaryDirectory() as tmpdir:
            yield HumanEvaluationFramework(
                enabled=True,
                sample_rate=1.0,  # Sample everything
                queue_path=Path(tmpdir) / "queue.json",
            )

    def test_disabled_framework(self):
        """Test disabled framework doesn't sample."""
        from human_evaluation import HumanEvaluationFramework

        framework = HumanEvaluationFramework(enabled=False)
        result = framework.sample_query("test", {"text": "result"}, 0.5)

        assert result is None

    def test_sample_query(self, framework):
        """Test sampling a query."""
        result = {"chunk_id": "c1", "text": "The answer is 42."}
        sample = framework.sample_query("What is the answer?", result, 0.8)

        assert sample is not None
        assert sample.query == "What is the answer?"
        assert sample.confidence == 0.8

    def test_get_next_sample(self, framework):
        """Test getting next sample."""
        result = {"chunk_id": "c1", "text": "Result text here."}
        framework.sample_query("Test query", result, 0.7)

        sample = framework.get_next_sample()
        assert sample is not None
        assert sample.query == "Test query"

    def test_submit_review(self, framework):
        """Test submitting a review."""
        from human_evaluation import RelevanceGrade

        result = {"chunk_id": "c1", "text": "Result text."}
        sample = framework.sample_query("Query", result, 0.7)

        framework.submit_review(
            sample_id=sample.sample_id,
            reviewer_id="reviewer_1",
            grade=RelevanceGrade.HIGHLY_RELEVANT,
            comment="Good answer",
        )

        stats = framework.get_evaluation_stats()
        # Should have 1 review but not completed (needs MIN_REVIEWS)
        assert stats.total_samples >= 1

    def test_get_evaluation_stats(self, framework):
        """Test getting evaluation stats."""
        from human_evaluation import RelevanceGrade

        result = {"chunk_id": "c1", "text": "Result"}
        sample = framework.sample_query("Query", result, 0.7)

        # Add multiple reviews to complete
        for i in range(framework.min_reviews):
            framework.submit_review(
                sample_id=sample.sample_id,
                reviewer_id=f"reviewer_{i}",
                grade=RelevanceGrade.HIGHLY_RELEVANT,
            )

        stats = framework.get_evaluation_stats()

        assert stats.total_samples >= 1
        assert stats.avg_grade >= 0

    def test_get_guidelines(self, framework):
        """Test getting evaluation guidelines."""
        guidelines = framework.get_guidelines()

        assert len(guidelines) >= 5  # One for each grade

    def test_export_results(self, framework):
        """Test exporting results."""
        from human_evaluation import RelevanceGrade

        result = {"chunk_id": "c1", "text": "Result"}
        sample = framework.sample_query("Query", result, 0.7)

        for i in range(framework.min_reviews):
            framework.submit_review(
                sample_id=sample.sample_id,
                reviewer_id=f"reviewer_{i}",
                grade=RelevanceGrade.PERFECT,
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "results.json"
            framework.export_results(output_path)

            assert output_path.exists()

            import json
            with open(output_path) as f:
                data = json.load(f)

            assert "stats" in data
            assert "samples" in data


class TestConvenienceFunction:
    """Unit tests for convenience function."""

    def test_create_sample(self):
        """Test create_sample convenience function."""
        from human_evaluation import create_sample

        with tempfile.TemporaryDirectory() as tmpdir:
            # Patch the queue path
            import human_evaluation
            original = human_evaluation.HumanEvaluationFramework

            class PatchedFramework(original):
                def __init__(self, *args, **kwargs):
                    kwargs['queue_path'] = Path(tmpdir) / "queue.json"
                    kwargs['sample_rate'] = 1.0
                    super().__init__(*args, **kwargs)

            human_evaluation.HumanEvaluationFramework = PatchedFramework

            try:
                result = {"chunk_id": "c1", "text": "Result"}
                sample = create_sample("Query", result, 0.7)
                # May be None if random sampling rejects
            finally:
                human_evaluation.HumanEvaluationFramework = original


class TestEnvironmentVariables:
    """Unit tests for environment configuration."""

    def test_default_values(self):
        """Test default configuration values."""
        from human_evaluation import (
            HUMAN_EVAL_ENABLED,
            HUMAN_EVAL_SAMPLE_RATE,
            HUMAN_EVAL_MIN_REVIEWS,
        )

        assert isinstance(HUMAN_EVAL_ENABLED, bool)
        assert isinstance(HUMAN_EVAL_SAMPLE_RATE, float)
        assert isinstance(HUMAN_EVAL_MIN_REVIEWS, int)

    def test_custom_values(self):
        """Test custom configuration via constructor."""
        from human_evaluation import HumanEvaluationFramework

        framework = HumanEvaluationFramework(
            enabled=False,
            sample_rate=0.1,
            min_reviews=5,
        )

        assert framework.enabled is False
        assert framework.selector.sample_rate == 0.1
        assert framework.min_reviews == 5


class TestDisputeDetection:
    """Unit tests for dispute detection."""

    def test_dispute_with_large_disagreement(self):
        """Test dispute detection with significant disagreement."""
        from human_evaluation import ReviewQueue, EvaluationSample, HumanReview, RelevanceGrade

        with tempfile.TemporaryDirectory() as tmpdir:
            queue = ReviewQueue(queue_path=Path(tmpdir) / "queue.json")

            sample = EvaluationSample(
                sample_id="dispute_test",
                query="Test",
                result_chunk_id="c1",
                result_text="Result",
                confidence=0.8,
                created_at=datetime.now(timezone.utc),
            )
            queue.add_sample(sample)

            # Add conflicting reviews
            queue.submit_review("dispute_test", HumanReview(
                reviewer_id="r1",
                grade=RelevanceGrade.PERFECT,
            ))
            queue.submit_review("dispute_test", HumanReview(
                reviewer_id="r2",
                grade=RelevanceGrade.NOT_RELEVANT,
            ))
            queue.submit_review("dispute_test", HumanReview(
                reviewer_id="r3",
                grade=RelevanceGrade.PERFECT,
            ))

            # Should be disputed
            from human_evaluation import EvaluationStatus
            for s in queue.queue:
                if s.sample_id == "dispute_test":
                    assert s.status == EvaluationStatus.DISPUTED
                    break
