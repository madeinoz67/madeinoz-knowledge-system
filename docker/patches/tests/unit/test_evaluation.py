"""
Unit Tests for RAG Evaluation Metrics (GAP-011)
Feature 023 Enhancement: RAG Book Compliance

Tests for retrieval evaluation metrics.

RAG Book Reference:
"You cannot improve what you cannot measure."

Retrieval Quality Targets:
- Precision@5 > 0.70 (70% of top 5 results relevant)
- Recall@10 > 0.80 (find 80% of relevant docs in top 10)
- MRR > 0.60 (first relevant result avg position)
"""

import pytest
import os
import sys
import tempfile
import json
from pathlib import Path

# Add patches directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'patches'))


class TestPrecisionAtK:
    """Unit tests for Precision@k metric."""

    def test_precision_at_5_all_relevant(self):
        """Test precision when all top 5 are relevant."""
        from evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator()

        retrieved = [{"id": f"doc{i}"} for i in range(10)]
        relevant = {f"doc{i}" for i in range(5)}

        precision = evaluator.compute_precision_at_k(
            [d["id"] for d in retrieved],
            relevant,
            k=5
        )

        assert precision == 1.0

    def test_precision_at_5_half_relevant(self):
        """Test precision when half are relevant."""
        from evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator()

        retrieved = [{"id": f"doc{i}"} for i in range(10)]
        relevant = {"doc0", "doc2", "doc5", "doc7", "doc9"}  # 2 in top 5

        precision = evaluator.compute_precision_at_k(
            [d["id"] for d in retrieved],
            relevant,
            k=5
        )

        assert precision == 0.4  # 2/5

    def test_precision_at_5_none_relevant(self):
        """Test precision when none are relevant."""
        from evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator()

        retrieved = [{"id": f"doc{i}"} for i in range(10)]
        relevant = {"doc20", "doc21"}  # Not in retrieved

        precision = evaluator.compute_precision_at_k(
            [d["id"] for d in retrieved],
            relevant,
            k=5
        )

        assert precision == 0.0

    def test_precision_at_1(self):
        """Test precision at k=1."""
        from evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator()

        # First result relevant
        precision = evaluator.compute_precision_at_k(
            ["doc0", "doc1", "doc2"],
            {"doc0"},
            k=1
        )
        assert precision == 1.0

        # First result not relevant
        precision = evaluator.compute_precision_at_k(
            ["doc0", "doc1", "doc2"],
            {"doc1"},
            k=1
        )
        assert precision == 0.0

    def test_precision_at_k_zero_k(self):
        """Test precision at k=0 returns 0."""
        from evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator()

        precision = evaluator.compute_precision_at_k(
            ["doc0", "doc1"],
            {"doc0"},
            k=0
        )

        assert precision == 0.0


class TestRecallAtK:
    """Unit tests for Recall@k metric."""

    def test_recall_all_found(self):
        """Test recall when all relevant docs are found."""
        from evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator()

        retrieved = [{"id": f"doc{i}"} for i in range(10)]
        relevant = {"doc0", "doc1", "doc2"}  # All in top 10

        recall = evaluator.compute_recall_at_k(
            [d["id"] for d in retrieved],
            relevant,
            k=10
        )

        assert recall == 1.0

    def test_recall_half_found(self):
        """Test recall when half of relevant docs are found."""
        from evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator()

        retrieved = [{"id": f"doc{i}"} for i in range(5)]
        relevant = {"doc0", "doc1", "doc5", "doc6"}  # 2 found, 2 not found

        recall = evaluator.compute_recall_at_k(
            [d["id"] for d in retrieved],
            relevant,
            k=5
        )

        assert recall == 0.5  # 2/4

    def test_recall_none_found(self):
        """Test recall when none are found."""
        from evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator()

        retrieved = [{"id": f"doc{i}"} for i in range(5)]
        relevant = {"doc10", "doc11"}  # Not in retrieved

        recall = evaluator.compute_recall_at_k(
            [d["id"] for d in retrieved],
            relevant,
            k=5
        )

        assert recall == 0.0

    def test_recall_empty_relevant(self):
        """Test recall with empty relevant set."""
        from evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator()

        recall = evaluator.compute_recall_at_k(
            ["doc0", "doc1"],
            set(),
            k=5
        )

        assert recall == 0.0


class TestMRR:
    """Unit tests for Mean Reciprocal Rank."""

    def test_mrr_first_relevant(self):
        """Test MRR when first result is relevant."""
        from evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator()

        mrr = evaluator.compute_mrr(
            ["doc0", "doc1", "doc2"],
            {"doc0"}
        )

        assert mrr == 1.0

    def test_mrr_second_relevant(self):
        """Test MRR when second result is relevant."""
        from evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator()

        mrr = evaluator.compute_mrr(
            ["doc0", "doc1", "doc2"],
            {"doc1"}
        )

        assert mrr == 0.5  # 1/2

    def test_mrr_third_relevant(self):
        """Test MRR when third result is relevant."""
        from evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator()

        mrr = evaluator.compute_mrr(
            ["doc0", "doc1", "doc2"],
            {"doc2"}
        )

        assert pytest.approx(mrr, 0.01) == 1/3

    def test_mrr_none_relevant(self):
        """Test MRR when no results are relevant."""
        from evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator()

        mrr = evaluator.compute_mrr(
            ["doc0", "doc1", "doc2"],
            {"doc5"}
        )

        assert mrr == 0.0

    def test_mrr_multiple_relevant(self):
        """Test MRR with multiple relevant docs (uses first)."""
        from evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator()

        mrr = evaluator.compute_mrr(
            ["doc0", "doc1", "doc2", "doc3"],
            {"doc1", "doc3"}  # doc1 at position 2
        )

        assert mrr == 0.5  # 1/2, not 1/4


class TestNDCG:
    """Unit tests for Normalized Discounted Cumulative Gain."""

    def test_ndcg_perfect_ranking(self):
        """Test NDCG with perfect ranking."""
        from evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator()

        # All relevant docs at top
        ndcg = evaluator.compute_ndcg_at_k(
            ["doc0", "doc1", "doc2", "doc3"],
            {"doc0", "doc1", "doc2"},
            k=3
        )

        assert ndcg == 1.0

    def test_ndcg_imperfect_ranking(self):
        """Test NDCG with imperfect ranking."""
        from evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator()

        # Relevant docs spread out
        ndcg = evaluator.compute_ndcg_at_k(
            ["doc0", "doc1", "doc2", "doc3", "doc4"],
            {"doc1", "doc3"},  # At positions 2 and 4
            k=5
        )

        # Should be less than 1.0
        assert 0.5 < ndcg < 1.0

    def test_ndcg_none_relevant(self):
        """Test NDCG when no results are relevant."""
        from evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator()

        ndcg = evaluator.compute_ndcg_at_k(
            ["doc0", "doc1", "doc2"],
            {"doc5"},
            k=3
        )

        assert ndcg == 0.0

    def test_ndcg_empty_relevant(self):
        """Test NDCG with empty relevant set."""
        from evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator()

        ndcg = evaluator.compute_ndcg_at_k(
            ["doc0", "doc1", "doc2"],
            set(),
            k=3
        )

        assert ndcg == 0.0


class TestRetrievalMetrics:
    """Unit tests for RetrievalMetrics container."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        from evaluation import RetrievalMetrics

        metrics = RetrievalMetrics(
            precision_at_5=0.8,
            recall_at_10=0.9,
            mrr=0.7,
            ndcg_at_10=0.75
        )

        d = metrics.to_dict()

        assert d["precision@5"] == 0.8
        assert d["recall@10"] == 0.9
        assert d["mrr"] == 0.7
        assert d["ndcg@10"] == 0.75

    def test_meets_targets(self):
        """Test target checking."""
        from evaluation import RetrievalMetrics

        # All targets met
        metrics = RetrievalMetrics(
            precision_at_5=0.75,
            recall_at_10=0.85,
            mrr=0.65,
            ndcg_at_10=0.75
        )
        targets = metrics.meets_targets()
        assert all(targets.values())

        # Some targets not met
        metrics = RetrievalMetrics(
            precision_at_5=0.65,  # Below 0.70
            recall_at_10=0.85,
            mrr=0.55,  # Below 0.60
            ndcg_at_10=0.75
        )
        targets = metrics.meets_targets()
        assert not targets["precision@5 > 0.70"]
        assert not targets["mrr > 0.60"]


class TestRetrievalEvaluator:
    """Unit tests for RetrievalEvaluator."""

    def test_evaluate_all_metrics(self):
        """Test full evaluation computes all metrics."""
        from evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator(enabled=False)

        retrieved = [
            {"id": "doc0"},
            {"id": "doc1"},
            {"id": "doc2"},
            {"id": "doc3"},
            {"id": "doc4"},
        ]
        relevant = {"doc0", "doc2", "doc4"}

        metrics = evaluator.evaluate(retrieved, relevant)

        assert metrics.precision_at_5 == 0.6  # 3/5
        assert metrics.recall_at_5 == 1.0  # 3/3
        assert metrics.mrr == 1.0  # First is relevant
        assert metrics.ndcg_at_10 > 0.5

    def test_evaluate_with_chunk_id(self):
        """Test evaluation with chunk_id instead of id."""
        from evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator(enabled=False)

        retrieved = [
            {"chunk_id": "chunk0"},
            {"chunk_id": "chunk1"},
        ]
        relevant = {"chunk0"}

        metrics = evaluator.evaluate(retrieved, relevant)

        assert metrics.precision_at_1 == 1.0
        assert metrics.mrr == 1.0

    def test_evaluation_logging(self):
        """Test evaluation logging to file."""
        from evaluation import RetrievalEvaluator

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "eval.jsonl"
            evaluator = RetrievalEvaluator(enabled=True, log_path=str(log_path))

            retrieved = [{"id": "doc0"}, {"id": "doc1"}]
            relevant = {"doc0"}

            evaluator.evaluate(retrieved, relevant, query="test query")

            # Check log file was created
            assert log_path.exists()

            # Check log content
            with open(log_path) as f:
                line = f.readline()
                record = json.loads(line)
                assert record["query"] == "test query"
                assert "metrics" in record

    def test_aggregate_metrics(self):
        """Test aggregate metrics computation."""
        from evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator(enabled=False)

        # Add two evaluations
        evaluator.evaluate([{"id": "doc0"}], {"doc0"})  # Perfect
        evaluator.evaluate([{"id": "doc1"}], {"doc0"})  # Miss

        aggregates = evaluator.get_aggregate_metrics()

        # Average MRR should be 0.5 (1.0 + 0.0) / 2
        assert aggregates["mrr"] == 0.5

    def test_clear_history(self):
        """Test clearing history."""
        from evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator(enabled=False)

        evaluator.evaluate([{"id": "doc0"}], {"doc0"})
        assert len(evaluator._metrics_history) == 1

        evaluator.clear_history()
        assert len(evaluator._metrics_history) == 0


class TestUserFeedback:
    """Unit tests for user feedback."""

    def test_record_feedback(self):
        """Test recording user feedback."""
        from evaluation import RetrievalEvaluator, UserFeedback

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "eval.jsonl"
            evaluator = RetrievalEvaluator(enabled=True, log_path=str(log_path))

            feedback = UserFeedback(
                query="test query",
                chunk_id="chunk0",
                rating=5,
                helpful=True
            )
            evaluator.record_feedback(feedback)

            assert len(evaluator._feedback_history) == 1

    def test_feedback_stats(self):
        """Test feedback statistics."""
        from evaluation import RetrievalEvaluator, UserFeedback

        evaluator = RetrievalEvaluator(enabled=False)

        evaluator.record_feedback(UserFeedback(
            query="q1", chunk_id="c1", rating=5, helpful=True
        ))
        evaluator.record_feedback(UserFeedback(
            query="q2", chunk_id="c2", rating=3, helpful=False
        ))
        evaluator.record_feedback(UserFeedback(
            query="q3", chunk_id="c3", rating=4, helpful=True
        ))

        stats = evaluator.get_feedback_stats()

        assert stats["total_feedback"] == 3
        assert stats["avg_rating"] == 4.0  # (5+3+4)/3
        assert stats["helpful_rate"] == pytest.approx(2/3, 0.01)


class TestEvaluationService:
    """Unit tests for EvaluationService."""

    def test_service_evaluate_retrieval(self):
        """Test service evaluate_retrieval method."""
        from evaluation import EvaluationService

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "eval.jsonl"
            service = EvaluationService(enabled=True, log_path=str(log_path))

            metrics = service.evaluate_retrieval(
                query="test",
                retrieved_docs=[{"id": "doc0"}, {"id": "doc1"}],
                relevant_ids={"doc0"}
            )

            assert metrics.mrr == 1.0

    def test_service_record_feedback(self):
        """Test service record_feedback method."""
        from evaluation import EvaluationService

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "eval.jsonl"
            service = EvaluationService(enabled=True, log_path=str(log_path))

            service.record_feedback(
                query="test",
                chunk_id="chunk0",
                rating=5,
                helpful=True
            )

            stats = service.get_dashboard_data()["feedback_stats"]
            assert stats["total_feedback"] == 1

    def test_service_dashboard_data(self):
        """Test dashboard data generation."""
        from evaluation import EvaluationService

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "eval.jsonl"
            service = EvaluationService(enabled=True, log_path=str(log_path))

            # Add evaluation
            service.evaluate_retrieval(
                query="test",
                retrieved_docs=[{"id": "doc0"}],
                relevant_ids={"doc0"}
            )

            data = service.get_dashboard_data()

            assert "aggregate_metrics" in data
            assert "feedback_stats" in data
            assert data["evaluation_count"] == 1

    def test_service_disabled(self):
        """Test disabled service returns empty metrics."""
        from evaluation import EvaluationService

        service = EvaluationService(enabled=False)

        metrics = service.evaluate_retrieval(
            query="test",
            retrieved_docs=[{"id": "doc0"}],
            relevant_ids={"doc0"}
        )

        # All zeros when disabled
        assert metrics.precision_at_5 == 0.0
        assert metrics.mrr == 0.0


class TestConvenienceFunctions:
    """Unit tests for convenience functions."""

    def test_evaluate_retrieval_quick(self):
        """Test quick evaluation function."""
        from evaluation import evaluate_retrieval

        metrics = evaluate_retrieval(
            retrieved_docs=[{"id": "doc0"}, {"id": "doc1"}],
            relevant_ids={"doc0"}
        )

        assert metrics.mrr == 1.0


class TestRAGBookTargets:
    """Tests verifying RAG Book target scenarios."""

    def test_meets_all_targets_scenario(self):
        """Test scenario where all RAG Book targets are met."""
        from evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator(enabled=False)

        # Simulate good retrieval: 5 relevant docs, all in top 10
        retrieved = [{"id": f"doc{i}"} for i in range(20)]
        relevant = {f"doc{i}" for i in [0, 1, 2, 3, 7]}  # 4 in top 5, 5 in top 10

        metrics = evaluator.evaluate(retrieved, relevant)
        targets = metrics.meets_targets()

        # Should meet all targets
        assert targets["precision@5 > 0.70"]  # 4/5 = 0.8
        assert targets["recall@10 > 0.80"]  # 5/5 = 1.0
        assert targets["mrr > 0.60"]  # First is relevant = 1.0

    def test_fails_precision_target(self):
        """Test scenario failing precision target."""
        from evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator(enabled=False)

        # Only 1 relevant in top 5
        retrieved = [{"id": f"doc{i}"} for i in range(20)]
        relevant = {"doc4", "doc10", "doc15"}  # Only 1 in top 5

        metrics = evaluator.evaluate(retrieved, relevant)

        assert metrics.precision_at_5 < 0.70  # 1/5 = 0.2

    def test_fails_mrr_target(self):
        """Test scenario failing MRR target."""
        from evaluation import RetrievalEvaluator

        evaluator = RetrievalEvaluator(enabled=False)

        # First relevant at position 3
        retrieved = [{"id": f"doc{i}"} for i in range(10)]
        relevant = {"doc2"}  # At position 3 (index 2)

        metrics = evaluator.evaluate(retrieved, relevant)

        assert metrics.mrr < 0.60  # 1/3 ≈ 0.33
