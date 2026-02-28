"""
HyDE Query Expansion for LKAP (Feature 023 Enhancement)
RedTeam Gap #GAP-004: Add HyDE query expansion for short/ambiguous queries.

RAG Book Reference:
"Hypothetical Document Embeddings (HyDE). Generate a hypothetical answer,
retrieve docs similar to it."

Why HyDE helps:
- The hypothetical document contains relevant terms in the "language" of your corpus
- A query "why is my login failing?" becomes a hypothetical doc mentioning
  "authentication errors, invalid credentials, password reset"

When HyDE works best:
- Short, ambiguous queries ("login issues")
- Queries with little domain terminology
- When documents are more verbose than typical queries

When to skip HyDE:
- Long, specific queries (already contain good keywords)
- When latency is critical (requires LLM call)
- When LLM might hallucinate domain-specific terminology

Cost reality:
- Adds LLM call per query (~$0.002 per query at 200 tokens)
- For 10K queries/day: ~$600/month

Environment Variables:
    MADEINOZ_KNOWLEDGE_HYDE_ENABLED: Enable HyDE expansion (default: true)
    MADEINOZ_KNOWLEDGE_HYDE_MIN_QUERY_TOKENS: Min tokens to trigger HyDE (default: 10)
    MADEINOZ_KNOWLEDGE_HYDE_MAX_HYPOTHETICAL_TOKENS: Max tokens in hypothetical (default: 200)
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Configuration with defaults
HYDE_ENABLED = os.getenv("MADEINOZ_KNOWLEDGE_HYDE_ENABLED", "true").lower() == "true"
HYDE_MIN_QUERY_TOKENS = int(os.getenv("MADEINOZ_KNOWLEDGE_HYDE_MIN_QUERY_TOKENS", "10"))
HYDE_MAX_HYPOTHETICAL_TOKENS = int(os.getenv("MADEINOZ_KNOWLEDGE_HYDE_MAX_HYPOTHETICAL_TOKENS", "200"))


@dataclass
class HyDEResult:
    """Result of HyDE expansion."""
    original_query: str
    hypothetical_document: Optional[str]
    should_expand: bool
    reason: str
    llm_latency_ms: Optional[float] = None


class HyDEExpander:
    """
    HyDE (Hypothetical Document Embeddings) query expansion.

    Generates hypothetical documents that would answer the query,
    then retrieves documents similar to those hypothetical documents.

    Usage:
        expander = HyDEExpander(llm_client)
        result = expander.expand("login issues")

        if result.should_expand:
            # Use hypothetical_document for retrieval
            embedding = embedder.encode(result.hypothetical_document)
    """

    # Prompt template for hypothetical document generation
    HYPOTHETICAL_PROMPT = """Write a brief, factual passage that would answer this question.
Use terminology and language typical of technical documentation.
Be specific and concrete, avoiding speculation.

Question: {query}

Passage:"""

    def __init__(
        self,
        enabled: bool = HYDE_ENABLED,
        min_query_tokens: int = HYDE_MIN_QUERY_TOKENS,
        max_hypothetical_tokens: int = HYDE_MAX_HYPOTHETICAL_TOKENS,
        llm_client: Optional[Any] = None,
    ):
        """
        Initialize HyDE expander.

        Args:
            enabled: Whether HyDE expansion is enabled
            min_query_tokens: Minimum query tokens to skip expansion
            max_hypothetical_tokens: Maximum tokens in hypothetical document
            llm_client: Optional LLM client for generation
        """
        self.enabled = enabled
        self.min_query_tokens = min_query_tokens
        self.max_hypothetical_tokens = max_hypothetical_tokens
        self.llm_client = llm_client

        # Stats tracking
        self._expansion_count = 0
        self._skip_count = 0
        self._total_latency_ms = 0.0

    def should_expand(self, query: str) -> Tuple[bool, str]:
        """
        Determine if query should be expanded using HyDE.

        Args:
            query: User query string

        Returns:
            Tuple of (should_expand, reason)
        """
        if not self.enabled:
            return False, "hyde_disabled"

        # Count tokens (rough approximation)
        token_count = len(query.split())

        if token_count >= self.min_query_tokens:
            return False, f"query_too_long ({token_count} >= {self.min_query_tokens})"

        # Check for specific query patterns that benefit from HyDE
        ambiguous_patterns = [
            "issues",
            "problems",
            "errors",
            "help",
            "not working",
            "broken",
            "config",
            "setup",
        ]

        query_lower = query.lower()
        for pattern in ambiguous_patterns:
            if pattern in query_lower and token_count < self.min_query_tokens:
                return True, f"ambiguous_pattern ({pattern})"

        # Default: expand short queries
        if token_count < self.min_query_tokens:
            return True, f"short_query ({token_count} tokens)"

        return False, "no_expansion_needed"

    def generate_hypothetical(self, query: str) -> Tuple[Optional[str], Optional[float]]:
        """
        Generate hypothetical document that would answer the query.

        Args:
            query: User query string

        Returns:
            Tuple of (hypothetical_document, latency_ms)
        """
        if not self.llm_client:
            logger.warning("No LLM client configured for HyDE")
            return None, None

        import time
        start_time = time.time()

        try:
            prompt = self.HYPOTHETICAL_PROMPT.format(query=query)
            hypothetical = self._call_llm(prompt)
            latency_ms = (time.time() - start_time) * 1000

            if hypothetical:
                # Truncate if too long
                words = hypothetical.split()
                if len(words) > self.max_hypothetical_tokens:
                    hypothetical = " ".join(words[:self.max_hypothetical_tokens])

            return hypothetical, latency_ms

        except Exception as e:
            logger.error(f"HyDE generation failed: {e}")
            return None, None

    def _call_llm(self, prompt: str) -> Optional[str]:
        """Call LLM with prompt (implementation varies by client)."""
        if hasattr(self.llm_client, "generate"):
            return self.llm_client.generate(prompt)
        elif hasattr(self.llm_client, "chat"):
            response = self.llm_client.chat([{"role": "user", "content": prompt}])
            if isinstance(response, dict):
                return response.get("content", response.get("message", str(response)))
            return str(response)
        else:
            raise ValueError("Unsupported LLM client")

    def expand(self, query: str) -> HyDEResult:
        """
        Expand query using HyDE if appropriate.

        Args:
            query: User query string

        Returns:
            HyDEResult with expansion details
        """
        should_expand, reason = self.should_expand(query)

        if not should_expand:
            self._skip_count += 1
            return HyDEResult(
                original_query=query,
                hypothetical_document=None,
                should_expand=False,
                reason=reason,
            )

        hypothetical, latency = self.generate_hypothetical(query)

        if hypothetical:
            self._expansion_count += 1
            if latency:
                self._total_latency_ms += latency

        return HyDEResult(
            original_query=query,
            hypothetical_document=hypothetical,
            should_expand=hypothetical is not None,
            reason=reason if hypothetical else "llm_failed",
            llm_latency_ms=latency,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get HyDE expansion statistics."""
        total = self._expansion_count + self._skip_count
        return {
            "enabled": self.enabled,
            "expansion_count": self._expansion_count,
            "skip_count": self._skip_count,
            "total_queries": total,
            "expansion_rate": self._expansion_count / total if total > 0 else 0,
            "avg_latency_ms": (
                self._total_latency_ms / self._expansion_count
                if self._expansion_count > 0
                else 0
            ),
        }


class HyDERetrievalAugmenter:
    """
    Augments retrieval with HyDE expansion.

    Combines original query and hypothetical document for better retrieval.

    Usage:
        augmenter = HyDERetrievalAugmenter(qdrant_client, expander)
        results = await augmenter.retrieve_with_hyde(
            query="login issues",
            top_k=10
        )
    """

    def __init__(
        self,
        qdrant_client: Any,
        expander: Optional[HyDEExpander] = None,
        embedder: Optional[Any] = None,
    ):
        """
        Initialize HyDE retrieval augmenter.

        Args:
            qdrant_client: QdrantClient instance
            expander: Optional HyDEExpander (creates default if None)
            embedder: Embedding service for hypothetical documents
        """
        self.qdrant_client = qdrant_client
        self.expander = expander or HyDEExpander()
        self.embedder = embedder

    async def retrieve_with_hyde(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        combine_mode: str = "hyde_only",  # "hyde_only", "original_only", "combine"
    ) -> Tuple[List[Dict[str, Any]], HyDEResult]:
        """
        Retrieve documents with optional HyDE expansion.

        Args:
            query: User query string
            top_k: Number of results to return
            filters: Optional metadata filters
            combine_mode: How to combine results:
                - "hyde_only": Use only hypothetical document for retrieval
                - "original_only": Use only original query
                - "combine": Combine results from both

        Returns:
            Tuple of (results, hyde_result)
        """
        hyde_result = self.expander.expand(query)

        if not hyde_result.should_expand or not hyde_result.hypothetical_document:
            # Fall back to normal retrieval
            results = await self.qdrant_client.semantic_search(
                query=query,
                top_k=top_k,
                filters=filters,
            )
            return results, hyde_result

        # Use hypothetical document for retrieval
        logger.info(
            f"HyDE expansion for '{query[:50]}...': "
            f"'{hyde_result.hypothetical_document[:50]}...' "
            f"(latency: {hyde_result.llm_latency_ms:.1f}ms)"
        )

        if combine_mode == "hyde_only":
            # Retrieve using hypothetical document
            results = await self.qdrant_client.semantic_search(
                query=hyde_result.hypothetical_document,
                top_k=top_k,
                filters=filters,
            )
        elif combine_mode == "combine":
            # Get results from both and merge
            hyde_results = await self.qdrant_client.semantic_search(
                query=hyde_result.hypothetical_document,
                top_k=top_k,
                filters=filters,
            )
            original_results = await self.qdrant_client.semantic_search(
                query=query,
                top_k=top_k,
                filters=filters,
            )
            results = self._merge_results(hyde_results, original_results, top_k)
        else:
            # original_only
            results = await self.qdrant_client.semantic_search(
                query=query,
                top_k=top_k,
                filters=filters,
            )

        return results, hyde_result

    def _merge_results(
        self,
        hyde_results: List[Dict[str, Any]],
        original_results: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """
        Merge results from HyDE and original query.

        Uses reciprocal rank fusion for combining.
        """
        from patches.hybrid_search import reciprocal_rank_fusion

        # Convert to format expected by RRF
        hyde_formatted = [
            (r.get("chunk_id", str(i)), r.get("confidence", r.get("score", 0.5)), r)
            for i, r in enumerate(hyde_results)
        ]
        original_formatted = [
            (r.get("chunk_id", str(i)), r.get("confidence", r.get("score", 0.5)), r)
            for i, r in enumerate(original_results)
        ]

        # Fuse results
        fused = reciprocal_rank_fusion(hyde_formatted, original_formatted, k=60)

        # Format results
        # RRF returns: (chunk_id, rrf_score, original_score, dense_rank, sparse_rank, metadata)
        results = []
        seen_ids = set()
        for chunk_id, rrf_score, orig_score, dense_rank, sparse_rank, metadata in fused[:top_k]:
            if chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                results.append({
                    "chunk_id": chunk_id,
                    "confidence": rrf_score,
                    "hyde_rank": dense_rank,
                    "original_rank": sparse_rank,
                    **metadata,
                })

        return results


# Convenience function
def expand_query(query: str, llm_client: Optional[Any] = None) -> HyDEResult:
    """
    Quick HyDE expansion.

    Args:
        query: User query string
        llm_client: Optional LLM client

    Returns:
        HyDEResult
    """
    expander = HyDEExpander(llm_client=llm_client)
    return expander.expand(query)
