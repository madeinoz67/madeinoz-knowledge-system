"""
RAG Evaluation Metrics for LKAP (Feature 023 Enhancement)
RedTeam Gap #GAP-011: Add evaluation metrics (MRR, NDCG, recall@k).

RAG Book Reference:
"You cannot improve what you cannot measure."

Evaluation requires knowing what "right" looks like:
- Human annotation (gold standard): Humans label which documents are relevant
- Synthetic generation: Use LLM to generate queries from documents
- User feedback: Thumbs up/down, "Was this helpful?" surveys

Retrieval Quality Targets:
- Precision@5 > 0.70 (70% of top 5 results relevant)
- Recall@10 > 0.80 (find 80% of relevant docs in top 10)
- MRR > 0.60 (first relevant result avg position)
- NDCG@10 > 0.70 (accounts for position of relevant docs)

Environment Variables:
    MADEINOZ_KNOWLEDGE_EVAL_ENABLED: Enable evaluation logging (default: true)
    MADEINOZ_KNOWLEDGE_EVAL_LOG_PATH: Path to evaluation log file (default: logs/evaluation.jsonl)
"""

import json
import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from math import log2
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Configuration with defaults
EVAL_ENABLED = os.getenv("MADEINOZ_KNOWLEDGE_EVAL_ENABLED", "true").lower() == "true"
EVAL_LOG_PATH = os.getenv("MADEINOZ_KNOWLEDGE_EVAL_LOG_PATH", "logs/evaluation.jsonl")


@dataclass
class RetrievalMetrics:
    """Container for retrieval evaluation metrics."""
    precision_at_1: float = 0.0
    precision_at_3: float = 0.0
    precision_at_5: float = 0.0
    precision_at_10: float = 0.0
    recall_at_5: float = 0.0
    recall_at_10: float = 0.0
    recall_at_20: float = 0.0
    mrr: float = 0.0  # Mean Reciprocal Rank
    ndcg_at_10: float = 0.0  # Normalized Discounted Cumulative Gain

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for JSON serialization."""
        return {
            "precision@1": self.precision_at_1,
            "precision@3": self.precision_at_3,
            "precision@5": self.precision_at_5,
            "precision@10": self.precision_at_10,
            "recall@5": self.recall_at_5,
            "recall@10": self.recall_at_10,
            "recall@20": self.recall_at_20,
            "mrr": self.mrr,
            "ndcg@10": self.ndcg_at_10,
        }

    def meets_targets(self) -> Dict[str, bool]:
        """Check if metrics meet RAG Book targets."""
        return {
            "precision@5 > 0.70": self.precision_at_5 > 0.70,
            "recall@10 > 0.80": self.recall_at_10 > 0.80,
            "mrr > 0.60": self.mrr > 0.60,
            "ndcg@10 > 0.70": self.ndcg_at_10 > 0.70,
        }


@dataclass
class EvaluationRecord:
    """A single evaluation record for logging."""
    query: str
    retrieved_ids: List[str]
    relevant_ids: Set[str]
    metrics: RetrievalMetrics
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Convert to JSON line for logging."""
        return json.dumps({
            "query": self.query,
            "retrieved_ids": self.retrieved_ids,
            "relevant_ids": list(self.relevant_ids),
            "metrics": self.metrics.to_dict(),
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        })


@dataclass
class UserFeedback:
    """User feedback on search results."""
    query: str
    chunk_id: str
    rating: int  # 1-5 or -1 (not relevant), 0 (neutral), 1 (relevant)
    helpful: Optional[bool] = None
    comment: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class RetrievalEvaluator:
    """
    Evaluates retrieval quality using standard IR metrics.

    Usage:
        evaluator = RetrievalEvaluator()
        metrics = evaluator.evaluate(
            retrieved_docs=[{"id": "doc1"}, {"id": "doc2"}],
            relevant_ids={"doc1", "doc3"}
        )
        print(metrics.mrr)  # 1.0 (first result was relevant)
    """

    def __init__(
        self,
        enabled: bool = EVAL_ENABLED,
        log_path: str = EVAL_LOG_PATH,
    ):
        """
        Initialize retrieval evaluator.

        Args:
            enabled: Whether evaluation logging is enabled
            log_path: Path to evaluation log file
        """
        self.enabled = enabled
        self.log_path = Path(log_path)

        # Ensure log directory exists
        if self.enabled:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # Aggregate metrics
        self._metrics_history: List[RetrievalMetrics] = []
        self._feedback_history: List[UserFeedback] = []

    def compute_precision_at_k(
        self,
        retrieved_ids: List[str],
        relevant_ids: Set[str],
        k: int,
    ) -> float:
        """
        Compute Precision@k.

        Precision@k = (# relevant in top k) / k

        Args:
            retrieved_ids: List of retrieved document IDs in rank order
            relevant_ids: Set of relevant document IDs (ground truth)
            k: Cutoff position

        Returns:
            Precision@k score (0.0 to 1.0)
        """
        if k <= 0:
            return 0.0

        retrieved_k = set(retrieved_ids[:k])
        relevant_in_k = len(retrieved_k & relevant_ids)

        return relevant_in_k / k

    def compute_recall_at_k(
        self,
        retrieved_ids: List[str],
        relevant_ids: Set[str],
        k: int,
    ) -> float:
        """
        Compute Recall@k.

        Recall@k = (# relevant in top k) / (total # relevant)

        Args:
            retrieved_ids: List of retrieved document IDs in rank order
            relevant_ids: Set of relevant document IDs (ground truth)
            k: Cutoff position

        Returns:
            Recall@k score (0.0 to 1.0)
        """
        if not relevant_ids:
            return 0.0

        retrieved_k = set(retrieved_ids[:k])
        relevant_in_k = len(retrieved_k & relevant_ids)

        return relevant_in_k / len(relevant_ids)

    def compute_mrr(
        self,
        retrieved_ids: List[str],
        relevant_ids: Set[str],
    ) -> float:
        """
        Compute Mean Reciprocal Rank.

        MRR = 1 / rank of first relevant result

        Args:
            retrieved_ids: List of retrieved document IDs in rank order
            relevant_ids: Set of relevant document IDs (ground truth)

        Returns:
            MRR score (0.0 to 1.0)
        """
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in relevant_ids:
                return 1.0 / (i + 1)

        return 0.0

    def compute_ndcg_at_k(
        self,
        retrieved_ids: List[str],
        relevant_ids: Set[str],
        k: int = 10,
    ) -> float:
        """
        Compute Normalized Discounted Cumulative Gain@k.

        NDCG accounts for the position of relevant documents in the ranking.
        DCG = sum(relevance / log2(rank + 1)) for top k
        NDCG = DCG / IDCG (where IDCG is ideal DCG with all relevant at top)

        Args:
            retrieved_ids: List of retrieved document IDs in rank order
            relevant_ids: Set of relevant document IDs (ground truth)
            k: Cutoff position

        Returns:
            NDCG@k score (0.0 to 1.0)
        """
        # Compute DCG
        dcg = 0.0
        for i, doc_id in enumerate(retrieved_ids[:k]):
            if doc_id in relevant_ids:
                # Binary relevance: 1 if relevant, 0 otherwise
                dcg += 1.0 / log2(i + 2)  # i+2 because log2(1) = 0

        # Compute IDCG (ideal: all relevant docs at top)
        idcg = sum(1.0 / log2(i + 2) for i in range(min(k, len(relevant_ids))))

        if idcg == 0:
            return 0.0

        return dcg / idcg

    def evaluate(
        self,
        retrieved_docs: List[Dict[str, Any]],
        relevant_ids: Set[str],
        query: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RetrievalMetrics:
        """
        Compute all retrieval metrics.

        Args:
            retrieved_docs: List of retrieved documents with 'id' or 'chunk_id' field
            relevant_ids: Set of relevant document IDs (ground truth)
            query: Optional query string for logging
            metadata: Optional metadata for logging

        Returns:
            RetrievalMetrics with all computed metrics
        """
        # Extract IDs from retrieved docs
        retrieved_ids = []
        for doc in retrieved_docs:
            doc_id = doc.get("id") or doc.get("chunk_id")
            if doc_id:
                retrieved_ids.append(doc_id)

        # Compute all metrics
        metrics = RetrievalMetrics(
            precision_at_1=self.compute_precision_at_k(retrieved_ids, relevant_ids, 1),
            precision_at_3=self.compute_precision_at_k(retrieved_ids, relevant_ids, 3),
            precision_at_5=self.compute_precision_at_k(retrieved_ids, relevant_ids, 5),
            precision_at_10=self.compute_precision_at_k(retrieved_ids, relevant_ids, 10),
            recall_at_5=self.compute_recall_at_k(retrieved_ids, relevant_ids, 5),
            recall_at_10=self.compute_recall_at_k(retrieved_ids, relevant_ids, 10),
            recall_at_20=self.compute_recall_at_k(retrieved_ids, relevant_ids, 20),
            mrr=self.compute_mrr(retrieved_ids, relevant_ids),
            ndcg_at_10=self.compute_ndcg_at_k(retrieved_ids, relevant_ids, 10),
        )

        # Log evaluation
        if self.enabled and query:
            record = EvaluationRecord(
                query=query,
                retrieved_ids=retrieved_ids,
                relevant_ids=relevant_ids,
                metrics=metrics,
                metadata=metadata or {},
            )
            self._log_evaluation(record)

        # Store in history
        self._metrics_history.append(metrics)

        return metrics

    def _log_evaluation(self, record: EvaluationRecord) -> None:
        """Log evaluation record to file."""
        try:
            with open(self.log_path, "a") as f:
                f.write(record.to_json() + "\n")
        except Exception as e:
            logger.warning(f"Failed to log evaluation: {e}")

    def record_feedback(self, feedback: UserFeedback) -> None:
        """
        Record user feedback on search results.

        Args:
            feedback: UserFeedback object
        """
        self._feedback_history.append(feedback)

        if self.enabled:
            try:
                feedback_path = self.log_path.parent / "feedback.jsonl"
                with open(feedback_path, "a") as f:
                    f.write(json.dumps({
                        "query": feedback.query,
                        "chunk_id": feedback.chunk_id,
                        "rating": feedback.rating,
                        "helpful": feedback.helpful,
                        "comment": feedback.comment,
                        "timestamp": feedback.timestamp,
                    }) + "\n")
            except Exception as e:
                logger.warning(f"Failed to log feedback: {e}")

    def get_aggregate_metrics(self) -> Dict[str, float]:
        """
        Compute aggregate metrics across all evaluations.

        Returns:
            Dictionary of mean metrics
        """
        if not self._metrics_history:
            return {}

        n = len(self._metrics_history)
        sums = defaultdict(float)

        for metrics in self._metrics_history:
            for key, value in metrics.to_dict().items():
                sums[key] += value

        return {key: value / n for key, value in sums.items()}

    def get_feedback_stats(self) -> Dict[str, Any]:
        """
        Compute statistics from user feedback.

        Returns:
            Dictionary of feedback statistics
        """
        if not self._feedback_history:
            return {"total_feedback": 0}

        ratings = [f.rating for f in self._feedback_history]
        helpful_count = sum(1 for f in self._feedback_history if f.helpful is True)

        return {
            "total_feedback": len(self._feedback_history),
            "avg_rating": sum(ratings) / len(ratings) if ratings else 0,
            "helpful_rate": helpful_count / len(self._feedback_history),
        }

    def clear_history(self) -> None:
        """Clear evaluation history."""
        self._metrics_history.clear()
        self._feedback_history.clear()


class EvaluationService:
    """
    Main evaluation service combining retrieval metrics and feedback.

    Usage:
        service = EvaluationService()
        metrics = service.evaluate_retrieval(
            query="how to configure GPIO",
            retrieved_docs=results,
            relevant_ids={"doc1", "doc2"}
        )

        # Record user feedback
        service.record_feedback(UserFeedback(
            query="how to configure GPIO",
            chunk_id="doc1",
            rating=5,
            helpful=True
        ))
    """

    def __init__(
        self,
        enabled: bool = EVAL_ENABLED,
        log_path: str = EVAL_LOG_PATH,
    ):
        """
        Initialize evaluation service.

        Args:
            enabled: Whether evaluation is enabled
            log_path: Path to evaluation log file
        """
        self.enabled = enabled
        self.retrieval_evaluator = RetrievalEvaluator(enabled=enabled, log_path=log_path)

    def evaluate_retrieval(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]],
        relevant_ids: Set[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RetrievalMetrics:
        """
        Evaluate retrieval quality.

        Args:
            query: Search query
            retrieved_docs: Retrieved documents
            relevant_ids: Ground truth relevant document IDs
            metadata: Optional metadata

        Returns:
            RetrievalMetrics
        """
        if not self.enabled:
            return RetrievalMetrics()

        return self.retrieval_evaluator.evaluate(
            retrieved_docs=retrieved_docs,
            relevant_ids=relevant_ids,
            query=query,
            metadata=metadata,
        )

    def record_feedback(
        self,
        query: str,
        chunk_id: str,
        rating: int,
        helpful: Optional[bool] = None,
        comment: Optional[str] = None,
    ) -> None:
        """
        Record user feedback.

        Args:
            query: Search query
            chunk_id: Chunk ID that was rated
            rating: Rating (1-5 or -1/0/1 for binary)
            helpful: Whether the result was helpful
            comment: Optional comment
        """
        if not self.enabled:
            return

        feedback = UserFeedback(
            query=query,
            chunk_id=chunk_id,
            rating=rating,
            helpful=helpful,
            comment=comment,
        )
        self.retrieval_evaluator.record_feedback(feedback)

    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Get data for evaluation dashboard.

        Returns:
            Dictionary with aggregate metrics and feedback stats
        """
        return {
            "aggregate_metrics": self.retrieval_evaluator.get_aggregate_metrics(),
            "feedback_stats": self.retrieval_evaluator.get_feedback_stats(),
            "evaluation_count": len(self.retrieval_evaluator._metrics_history),
        }


# Convenience functions
def evaluate_retrieval(
    retrieved_docs: List[Dict[str, Any]],
    relevant_ids: Set[str],
) -> RetrievalMetrics:
    """
    Quick evaluation of retrieval quality.

    Args:
        retrieved_docs: Retrieved documents
        relevant_ids: Ground truth relevant document IDs

    Returns:
        RetrievalMetrics
    """
    evaluator = RetrievalEvaluator()
    return evaluator.evaluate(retrieved_docs, relevant_ids)
