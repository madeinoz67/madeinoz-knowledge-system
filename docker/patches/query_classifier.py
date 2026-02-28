"""
Query Classification for LKAP (Feature 023 Enhancement)
RedTeam Gap #GAP-005: Add query classification for adaptive retrieval.

RAG Book Reference:
"Different queries need different retrieval strategies."

Query types with routing rules:
- factual_lookup: Fast exact match, keyword retriever
- conceptual: Semantic similarity, vector retriever
- procedural: Structured docs, hierarchical retriever
- comparison: Multi-document comparison
- temporal: Time-sensitive queries

Classification methods:
- Rule-based (fast, no LLM cost)
- LLM-based (more accurate, higher cost)
- Hybrid (rules first, LLM for ambiguous)

Environment Variables:
    MADEINOZ_KNOWLEDGE_QUERY_CLASSIFIER_ENABLED: Enable classification (default: true)
    MADEINOZ_KNOWLEDGE_QUERY_CLASSIFIER_USE_LLM: Use LLM for classification (default: false)
"""

import logging
import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Configuration with defaults
CLASSIFIER_ENABLED = os.getenv("MADEINOZ_KNOWLEDGE_QUERY_CLASSIFIER_ENABLED", "true").lower() == "true"
CLASSIFIER_USE_LLM = os.getenv("MADEINOZ_KNOWLEDGE_QUERY_CLASSIFIER_USE_LLM", "false").lower() == "true"


class QueryType(str, Enum):
    """Query type classification for adaptive retrieval."""
    FACTUAL = "factual"           # Specific facts, exact matches
    PROCEDURAL = "procedural"     # How-to, step-by-step instructions
    CONCEPTUAL = "conceptual"     # Explanations, understanding
    COMPARATIVE = "comparative"   # Comparing options, features
    TEMPORAL = "temporal"         # Time-sensitive queries
    AMBIGUOUS = "ambiguous"       # Needs clarification


# Retrieval strategy recommendations per query type
RETRIEVAL_STRATEGIES = {
    QueryType.FACTUAL: {
        "primary": "keyword",      # Fast exact match
        "top_k": 5,
        "rerank": True,
        "hybrid_weight": 0.7,     # Favor sparse (keyword)
    },
    QueryType.PROCEDURAL: {
        "primary": "hybrid",       # Both keyword and semantic
        "top_k": 10,
        "rerank": True,
        "hybrid_weight": 0.5,
    },
    QueryType.CONCEPTUAL: {
        "primary": "dense",        # Semantic similarity
        "top_k": 10,
        "rerank": True,
        "hybrid_weight": 0.3,     # Favor dense (semantic)
    },
    QueryType.COMPARATIVE: {
        "primary": "hybrid",
        "top_k": 15,               # Need more docs for comparison
        "rerank": True,
        "hybrid_weight": 0.5,
    },
    QueryType.TEMPORAL: {
        "primary": "keyword",      # Date filters work better with keyword
        "top_k": 10,
        "rerank": True,
        "hybrid_weight": 0.6,
        "time_filter": True,
    },
    QueryType.AMBIGUOUS: {
        "primary": "hybrid",
        "top_k": 10,
        "rerank": True,
        "hybrid_weight": 0.5,
    },
}


@dataclass
class ClassificationResult:
    """Result of query classification."""
    query_type: QueryType
    confidence: float
    strategy: Dict[str, Any]
    detected_patterns: List[str]
    suggested_refinements: Optional[List[str]] = None


# Rule-based classification patterns
FACTUAL_PATTERNS = [
    r"^(what|where|when|who|which)\s+(is|are|was|were|the)\b",
    r"^(how\s+many|how\s+much)\b",
    r"\b(rate\s+limit|api\s+key|version|config|setting)\b",
    r"\b(define|definition|value|number)\b",
    r"\?$",  # Short questions
]

PROCEDURAL_PATTERNS = [
    r"^(how\s+(do|can|to|should)\s+i)\b",
    r"^(steps?|guide|tutorial)\s+(to|for)\b",
    r"\b(setup|install|configure|deploy|run)\b",
    r"\b(step|first|then|finally|next)\b",
    r"\b(how\s+to)\b",
]

CONCEPTUAL_PATTERNS = [
    r"^(explain|describe|tell\s+me\s+about)\b",
    r"\b(how\s+does\s+.+\s+work)\b",
    r"\b(why|reason|cause|purpose)\b",
    r"\b(difference\s+between|vs\.?|versus)\b",
    r"\b(concept|principle|theory|architecture)\b",
]

COMPARATIVE_PATTERNS = [
    r"\b(compare|comparison|vs\.?|versus|versus)\b",
    r"\b(better|best|worse|worst)\b",
    r"\b(difference\s+between)\b",
    r"\b(which\s+(one|option|approach)\s+is)\b",
    r"\b(pros?\s+and\s+cons?)\b",
]

TEMPORAL_PATTERNS = [
    r"\b(latest|recent|newest|current)\b",
    r"\b(today|yesterday|this\s+week|this\s+month)\b",
    r"\b(202\d|last\s+year|in\s+\d{4})\b",
    r"\b(updated|changed|modified)\b",
    r"\b(history|timeline|evolution)\b",
]

AMBIGUOUS_PATTERNS = [
    r"^(it|this|that|they)\b",  # Pronoun without context
    r"^\w{1,3}$",  # Very short queries
    r"\b(the\s+thing|the\s+stuff|the\s+part)\b",  # Vague references
]


class RuleBasedClassifier:
    """
    Rule-based query classifier using pattern matching.

    Fast, no LLM cost, good for common patterns.
    """

    def __init__(self):
        """Initialize with compiled patterns."""
        self.patterns = {
            QueryType.FACTUAL: [re.compile(p, re.IGNORECASE) for p in FACTUAL_PATTERNS],
            QueryType.PROCEDURAL: [re.compile(p, re.IGNORECASE) for p in PROCEDURAL_PATTERNS],
            QueryType.CONCEPTUAL: [re.compile(p, re.IGNORECASE) for p in CONCEPTUAL_PATTERNS],
            QueryType.COMPARATIVE: [re.compile(p, re.IGNORECASE) for p in COMPARATIVE_PATTERNS],
            QueryType.TEMPORAL: [re.compile(p, re.IGNORECASE) for p in TEMPORAL_PATTERNS],
            QueryType.AMBIGUOUS: [re.compile(p, re.IGNORECASE) for p in AMBIGUOUS_PATTERNS],
        }

    def classify(self, query: str) -> Tuple[QueryType, float, List[str]]:
        """
        Classify query using pattern matching.

        Args:
            query: User query string

        Returns:
            Tuple of (QueryType, confidence, matched_patterns)
        """
        scores: Dict[QueryType, int] = {qt: 0 for qt in QueryType}
        matches: Dict[QueryType, List[str]] = {qt: [] for qt in QueryType}

        for query_type, patterns in self.patterns.items():
            for pattern in patterns:
                if pattern.search(query):
                    scores[query_type] += 1
                    matches[query_type].append(pattern.pattern)

        # Find best match
        max_score = max(scores.values())
        if max_score == 0:
            # No patterns matched - default to CONCEPTUAL
            return QueryType.CONCEPTUAL, 0.3, []

        # Get query types with max score
        best_types = [qt for qt, score in scores.items() if score == max_score]

        # If multiple types tie, prefer in order: FACTUAL > PROCEDURAL > CONCEPTUAL
        priority_order = [
            QueryType.FACTUAL,
            QueryType.PROCEDURAL,
            QueryType.TEMPORAL,
            QueryType.COMPARATIVE,
            QueryType.CONCEPTUAL,
            QueryType.AMBIGUOUS,
        ]

        for qt in priority_order:
            if qt in best_types:
                confidence = min(0.9, 0.5 + max_score * 0.15)
                return qt, confidence, matches[qt]

        return QueryType.CONCEPTUAL, 0.5, []

    def get_suggested_refinements(self, query: str, query_type: QueryType) -> List[str]:
        """
        Suggest query refinements for ambiguous queries.

        Args:
            query: Original query
            query_type: Detected query type

        Returns:
            List of suggested refinements
        """
        if query_type != QueryType.AMBIGUOUS:
            return []

        suggestions = []

        # Check for short queries
        if len(query.split()) <= 2:
            suggestions.append("Try adding more context to your question")
            suggestions.append("Example: 'How do I configure X' instead of just 'X'")

        # Check for pronouns
        if re.search(r"^(it|this|that|they)\b", query, re.IGNORECASE):
            suggestions.append("Try replacing pronouns with specific terms")

        return suggestions


class LLMClassifier:
    """
    LLM-based query classifier for higher accuracy.

    Uses LLM to classify queries that are ambiguous for rules.
    """

    def __init__(self, llm_client: Optional[Any] = None):
        """
        Initialize LLM classifier.

        Args:
            llm_client: LLM client for classification
        """
        self.llm_client = llm_client
        self.classification_prompt = """Classify this query into exactly one category:

Categories:
- factual: Asking for specific facts, numbers, definitions
- procedural: Asking how to do something, steps, instructions
- conceptual: Asking for explanations, understanding how something works
- comparative: Asking to compare options or features
- temporal: Asking about recent changes, history, or time-sensitive info
- ambiguous: Too vague to classify confidently

Query: "{query}"

Category (respond with just the category name):"""

    def classify(self, query: str) -> Tuple[QueryType, float]:
        """
        Classify query using LLM.

        Args:
            query: User query string

        Returns:
            Tuple of (QueryType, confidence)
        """
        if not self.llm_client:
            return QueryType.CONCEPTUAL, 0.3

        try:
            prompt = self.classification_prompt.format(query=query)
            # Call LLM (implementation depends on client type)
            response = self._call_llm(prompt)
            response_lower = response.strip().lower()

            # Map response to QueryType
            type_mapping = {
                "factual": QueryType.FACTUAL,
                "procedural": QueryType.PROCEDURAL,
                "conceptual": QueryType.CONCEPTUAL,
                "comparative": QueryType.COMPARATIVE,
                "temporal": QueryType.TEMPORAL,
                "ambiguous": QueryType.AMBIGUOUS,
            }

            for key, query_type in type_mapping.items():
                if key in response_lower:
                    return query_type, 0.85

            return QueryType.CONCEPTUAL, 0.5

        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")
            return QueryType.CONCEPTUAL, 0.3

    def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt (implementation varies by client)."""
        # Placeholder - actual implementation depends on LLM client
        if hasattr(self.llm_client, "generate"):
            return self.llm_client.generate(prompt)
        elif hasattr(self.llm_client, "chat"):
            return self.llm_client.chat([{"role": "user", "content": prompt}])
        else:
            raise ValueError("Unsupported LLM client")


class QueryClassifier:
    """
    Main query classifier combining rule-based and LLM classification.

    Usage:
        classifier = QueryClassifier()
        result = classifier.classify("How do I deploy the application?")
        print(result.query_type)  # QueryType.PROCEDURAL
        print(result.strategy)    # {"primary": "hybrid", "top_k": 10, ...}
    """

    def __init__(
        self,
        enabled: bool = CLASSIFIER_ENABLED,
        use_llm: bool = CLASSIFIER_USE_LLM,
        llm_client: Optional[Any] = None,
    ):
        """
        Initialize query classifier.

        Args:
            enabled: Whether classification is enabled
            use_llm: Whether to use LLM for ambiguous queries
            llm_client: Optional LLM client
        """
        self.enabled = enabled
        self.use_llm = use_llm
        self.rule_classifier = RuleBasedClassifier()
        self.llm_classifier = LLMClassifier(llm_client) if use_llm else None

        # Stats tracking
        self._classification_counts: Dict[QueryType, int] = {qt: 0 for qt in QueryType}

    def classify(self, query: str) -> ClassificationResult:
        """
        Classify query and return retrieval strategy.

        Args:
            query: User query string

        Returns:
            ClassificationResult with type, confidence, and strategy
        """
        if not self.enabled:
            return ClassificationResult(
                query_type=QueryType.CONCEPTUAL,
                confidence=0.5,
                strategy=RETRIEVAL_STRATEGIES[QueryType.CONCEPTUAL],
                detected_patterns=[],
            )

        # Start with rule-based classification
        query_type, confidence, patterns = self.rule_classifier.classify(query)

        # Use LLM for low-confidence or ambiguous results
        if self.llm_classifier and (confidence < 0.6 or query_type == QueryType.AMBIGUOUS):
            llm_type, llm_confidence = self.llm_classifier.classify(query)
            if llm_confidence > confidence:
                query_type = llm_type
                confidence = llm_confidence
                patterns = ["llm_classification"]

        # Get retrieval strategy
        strategy = RETRIEVAL_STRATEGIES.get(query_type, RETRIEVAL_STRATEGIES[QueryType.CONCEPTUAL])

        # Get refinements for ambiguous queries
        refinements = None
        if query_type == QueryType.AMBIGUOUS:
            refinements = self.rule_classifier.get_suggested_refinements(query, query_type)

        # Update stats
        self._classification_counts[query_type] += 1

        return ClassificationResult(
            query_type=query_type,
            confidence=confidence,
            strategy=strategy,
            detected_patterns=patterns,
            suggested_refinements=refinements,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get classification statistics."""
        total = sum(self._classification_counts.values())
        if total == 0:
            return {"total_classified": 0}

        return {
            "total_classified": total,
            "distribution": {
                qt.value: count / total
                for qt, count in self._classification_counts.items()
                if count > 0
            },
            "counts": {
                qt.value: count
                for qt, count in self._classification_counts.items()
            },
        }


class QueryRouter:
    """
    Routes queries to appropriate retrieval strategies.

    RAG Book Reference:
    "Route queries to different retrieval strategies based on query type."

    Usage:
        router = QueryRouter(qdrant_client)
        results = await router.retrieve("How do I deploy?", k=10)
    """

    def __init__(
        self,
        qdrant_client: Any,
        classifier: Optional[QueryClassifier] = None,
    ):
        """
        Initialize query router.

        Args:
            qdrant_client: QdrantClient instance
            classifier: Optional QueryClassifier (creates default if None)
        """
        self.qdrant_client = qdrant_client
        self.classifier = classifier or QueryClassifier()

    async def retrieve(
        self,
        query: str,
        k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], ClassificationResult]:
        """
        Route query and retrieve using appropriate strategy.

        Args:
            query: User query string
            k: Optional override for top_k
            filters: Optional metadata filters

        Returns:
            Tuple of (results, classification_result)
        """
        # Classify query
        classification = self.classifier.classify(query)
        strategy = classification.strategy

        # Get top_k from strategy or use override
        top_k = k if k is not None else strategy.get("top_k", 10)

        # Apply time filter for temporal queries
        if strategy.get("time_filter") and filters is None:
            filters = {}
        if strategy.get("time_filter"):
            # Add recency boost (implementation depends on metadata)
            pass  # Time filtering handled by qdrant_client

        # Retrieve using hybrid search with strategy-specific weights
        results = await self.qdrant_client.semantic_search(
            query=query,
            top_k=top_k,
            filters=filters,
            confidence_threshold=0.3,  # Lower threshold, let reranking filter
            rerank=strategy.get("rerank", True),
            hybrid=True,  # Always use hybrid, weight controls balance
        )

        logger.info(
            f"Routed query '{query[:50]}...' as {classification.query_type.value} "
            f"(confidence: {classification.confidence:.2f}, strategy: {strategy['primary']})"
        )

        return results, classification


# Convenience function
def classify_query(query: str) -> ClassificationResult:
    """
    Quick query classification.

    Args:
        query: User query string

    Returns:
        ClassificationResult
    """
    classifier = QueryClassifier()
    return classifier.classify(query)
