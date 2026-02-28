"""
Multi-Query Variants for LKAP (Feature 023 Enhancement)
RedTeam Gap #GAP-006: Add multi-query variant generation.

RAG Book Reference:
"Generate 3 different ways to ask this question, combine results"

Multi-query improves retrieval by:
1. Generating multiple query variants/rephrasings
2. Retrieving results for each variant
3. Merging results using Reciprocal Rank Fusion (RRF)

When to use:
- Complex queries with multiple interpretations
- Queries that might match different terminology
- When single query retrieval yields poor results

When to skip:
- Simple, well-defined queries
- Exact match queries (keywords, IDs)
- When latency is critical

Environment Variables:
    MADEINOZ_KNOWLEDGE_MULTI_QUERY_ENABLED: Enable multi-query (default: true)
    MADEINOZ_KNOWLEDGE_MULTI_QUERY_MIN_LENGTH: Min query length to trigger (default: 10)
    MADEINOZ_KNOWLEDGE_MULTI_QUERY_NUM_VARIANTS: Number of variants to generate (default: 3)
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Configuration with defaults
MULTI_QUERY_ENABLED = os.getenv("MADEINOZ_KNOWLEDGE_MULTI_QUERY_ENABLED", "true").lower() == "true"
MULTI_QUERY_MIN_LENGTH = int(os.getenv("MADEINOZ_KNOWLEDGE_MULTI_QUERY_MIN_LENGTH", "10"))
MULTI_QUERY_NUM_VARIANTS = int(os.getenv("MADEINOZ_KNOWLEDGE_MULTI_QUERY_NUM_VARIANTS", "3"))


@dataclass
class QueryVariant:
    """A single query variant."""
    original: str
    variant: str
    variant_type: str  # "synonym", "rephrase", "expansion", "decomposition"


@dataclass
class MultiQueryResult:
    """Result of multi-query retrieval."""
    original_query: str
    variants: List[QueryVariant]
    merged_results: List[Dict[str, Any]]
    per_variant_results: Dict[str, List[Dict[str, Any]]]
    total_candidates: int
    deduplication_count: int


class QueryVariantGenerator:
    """
    Generates query variants using rule-based and LLM methods.

    Rule-based variants:
    - Synonym replacement
    - Query expansion
    - Query decomposition

    LLM variants (when available):
    - Rephrasing
    - Perspective changes
    """

    # Synonym mappings for common terms
    SYNONYMS = {
        "error": ["issue", "problem", "failure", "exception"],
        "config": ["configuration", "setting", "setup"],
        "setup": ["install", "configure", "initialize"],
        "fail": ["error", "fail", "not working", "broken"],
        "fix": ["resolve", "solve", "repair", "troubleshoot"],
        "start": ["begin", "launch", "run", "execute"],
        "stop": ["halt", "terminate", "end", "shutdown"],
        "create": ["make", "generate", "build", "produce"],
        "delete": ["remove", "erase", "clear", "drop"],
        "update": ["modify", "change", "edit", "alter"],
        "get": ["retrieve", "fetch", "obtain", "acquire"],
        "show": ["display", "list", "view", "see"],
        "how": ["in what way", "by what means", "what steps"],
        "why": ["for what reason", "what causes", "what is the cause"],
        "what": ["which", "what kind of"],
    }

    # Expansion terms for common query patterns
    EXPANSIONS = {
        "api": ["API endpoint", "REST API", "API call"],
        "auth": ["authentication", "login", "authorization", "OAuth"],
        "db": ["database", "SQL", "data storage"],
        "ui": ["user interface", "frontend", "UI component"],
        "perf": ["performance", "latency", "throughput", "optimization"],
    }

    def __init__(self, llm_client: Optional[Any] = None):
        """
        Initialize variant generator.

        Args:
            llm_client: Optional LLM client for rephrasing
        """
        self.llm_client = llm_client

    def generate_variants(
        self,
        query: str,
        num_variants: int = MULTI_QUERY_NUM_VARIANTS,
        use_llm: bool = False,
    ) -> List[QueryVariant]:
        """
        Generate query variants.

        Args:
            query: Original query
            num_variants: Maximum number of variants to generate
            use_llm: Whether to use LLM for rephrasing

        Returns:
            List of QueryVariant objects
        """
        variants = []

        # 1. Synonym replacement
        synonym_variant = self._synonym_replacement(query)
        if synonym_variant and synonym_variant.lower() != query.lower():
            variants.append(QueryVariant(
                original=query,
                variant=synonym_variant,
                variant_type="synonym",
            ))

        # 2. Query expansion
        expanded = self._expand_query(query)
        if expanded and expanded.lower() != query.lower():
            variants.append(QueryVariant(
                original=query,
                variant=expanded,
                variant_type="expansion",
            ))

        # 3. Query decomposition (if complex query)
        decomposed = self._decompose_query(query)
        for dec in decomposed:
            if len(variants) >= num_variants:
                break
            variants.append(QueryVariant(
                original=query,
                variant=dec,
                variant_type="decomposition",
            ))

        # 4. LLM rephrasing (if available and requested)
        if use_llm and self.llm_client and len(variants) < num_variants:
            llm_variants = self._llm_rephrase(query, num_variants - len(variants))
            for llm_var in llm_variants:
                variants.append(QueryVariant(
                    original=query,
                    variant=llm_var,
                    variant_type="rephrase",
                ))

        # Limit to requested number
        return variants[:num_variants]

    def _synonym_replacement(self, query: str) -> Optional[str]:
        """Replace words with synonyms."""
        words = query.lower().split()
        replaced = False

        for i, word in enumerate(words):
            if word in self.SYNONYMS:
                synonyms = self.SYNONYMS[word]
                # Pick first synonym that's different
                for syn in synonyms:
                    if syn != word:
                        words[i] = syn
                        replaced = True
                        break
                if replaced:
                    break

        if replaced:
            return " ".join(words)
        return None

    def _expand_query(self, query: str) -> Optional[str]:
        """Expand abbreviations and add context."""
        words = query.lower().split()
        expanded = False

        for i, word in enumerate(words):
            if word in self.EXPANSIONS:
                # Replace with first expansion
                expansion = self.EXPANSIONS[word][0]
                words[i] = expansion
                expanded = True
                break

        if expanded:
            return " ".join(words)
        return None

    def _decompose_query(self, query: str) -> List[str]:
        """Decompose complex queries into sub-queries."""
        decomposed = []

        # Check for conjunction patterns
        conjunctions = [" and ", " vs ", " versus ", " or ", " compared to "]

        for conj in conjunctions:
            if conj in query.lower():
                parts = query.lower().split(conj)
                if len(parts) == 2:
                    # Create sub-queries
                    decomposed.append(parts[0].strip())
                    decomposed.append(parts[1].strip())
                break

        return decomposed[:2]  # Max 2 decomposed parts

    def _llm_rephrase(self, query: str, num: int) -> List[str]:
        """Use LLM to rephrase query."""
        if not self.llm_client:
            return []

        prompt = f"""Generate {num} different ways to ask this question.
Each variant should use different words but ask the same thing.
Return only the variants, one per line, numbered.

Question: {query}

Variants:"""

        try:
            response = self._call_llm(prompt)
            variants = []

            for line in response.strip().split("\n"):
                # Remove numbering
                line = line.strip()
                if line and line[0].isdigit():
                    line = ".".join(line.split(".")[1:]).strip()
                if line and len(line) > 5:
                    variants.append(line)

            return variants[:num]

        except Exception as e:
            logger.warning(f"LLM rephrasing failed: {e}")
            return []

    def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt."""
        if hasattr(self.llm_client, "generate"):
            return self.llm_client.generate(prompt)
        elif hasattr(self.llm_client, "chat"):
            response = self.llm_client.chat([{"role": "user", "content": prompt}])
            if isinstance(response, dict):
                return response.get("content", response.get("message", str(response)))
            return str(response)
        else:
            raise ValueError("Unsupported LLM client")


class MultiQueryRetriever:
    """
    Retrieves using multiple query variants and merges results.

    Usage:
        retriever = MultiQueryRetriever(qdrant_client)
        result = await retriever.retrieve("How do I fix auth errors?")
    """

    def __init__(
        self,
        qdrant_client: Any,
        variant_generator: Optional[QueryVariantGenerator] = None,
        enabled: bool = MULTI_QUERY_ENABLED,
        min_length: int = MULTI_QUERY_MIN_LENGTH,
        num_variants: int = MULTI_QUERY_NUM_VARIANTS,
    ):
        """
        Initialize multi-query retriever.

        Args:
            qdrant_client: QdrantClient instance
            variant_generator: Optional QueryVariantGenerator
            enabled: Whether multi-query is enabled
            min_length: Minimum query length to trigger multi-query
            num_variants: Number of variants to generate
        """
        self.qdrant_client = qdrant_client
        self.variant_generator = variant_generator or QueryVariantGenerator()
        self.enabled = enabled
        self.min_length = min_length
        self.num_variants = num_variants

        # Stats
        self._queries_processed = 0
        self._multi_queries_executed = 0

    def should_use_multi_query(self, query: str) -> bool:
        """
        Determine if query should use multi-query retrieval.

        Args:
            query: User query

        Returns:
            True if multi-query should be used
        """
        if not self.enabled:
            return False

        # Check minimum length
        if len(query.split()) < self.min_length:
            return False

        # Check for complex query patterns
        complex_patterns = [
            " and ",
            " vs ",
            " versus ",
            " or ",
            " compared to ",
            " difference between ",
            " how to ",
            " what are ",
        ]

        query_lower = query.lower()
        for pattern in complex_patterns:
            if pattern in query_lower:
                return True

        # Default: use multi-query for longer queries
        return len(query.split()) >= self.min_length

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        use_llm: bool = False,
    ) -> MultiQueryResult:
        """
        Retrieve using multi-query strategy.

        Args:
            query: User query
            top_k: Number of results to return
            filters: Optional metadata filters
            use_llm: Whether to use LLM for variants

        Returns:
            MultiQueryResult with merged results
        """
        self._queries_processed += 1

        if not self.should_use_multi_query(query):
            # Fall back to single query
            results = await self.qdrant_client.semantic_search(
                query=query,
                top_k=top_k,
                filters=filters,
            )
            return MultiQueryResult(
                original_query=query,
                variants=[],
                merged_results=results,
                per_variant_results={"original": results},
                total_candidates=len(results),
                deduplication_count=0,
            )

        self._multi_queries_executed += 1

        # Generate variants
        variants = self.variant_generator.generate_variants(
            query=query,
            num_variants=self.num_variants,
            use_llm=use_llm,
        )

        # Retrieve for each variant
        all_queries = [query] + [v.variant for v in variants]
        per_variant_results: Dict[str, List[Dict[str, Any]]] = {}

        for q in all_queries:
            try:
                results = await self.qdrant_client.semantic_search(
                    query=q,
                    top_k=top_k,
                    filters=filters,
                )
                per_variant_results[q] = results
            except Exception as e:
                logger.warning(f"Multi-query failed for '{q[:30]}...': {e}")
                per_variant_results[q] = []

        # Merge results using RRF
        merged = self._merge_results(per_variant_results, top_k)

        logger.info(
            f"Multi-query: '{query[:50]}...' -> {len(variants)} variants, "
            f"{len(merged)} merged results"
        )

        # Calculate deduplication
        total_candidates = sum(len(r) for r in per_variant_results.values())
        dedup_count = total_candidates - len(merged)

        return MultiQueryResult(
            original_query=query,
            variants=variants,
            merged_results=merged,
            per_variant_results=per_variant_results,
            total_candidates=total_candidates,
            deduplication_count=dedup_count,
        )

    def _merge_results(
        self,
        per_variant_results: Dict[str, List[Dict[str, Any]]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """
        Merge results from multiple queries using RRF.

        Args:
            per_variant_results: Results keyed by query
            top_k: Number of results to return

        Returns:
            Merged and deduplicated results
        """
        from patches.hybrid_search import reciprocal_rank_fusion

        # Collect all results with their ranks
        all_chunks: Dict[str, Dict[str, Any]] = {}
        rank_lists: List[List[Tuple[str, float, Dict[str, Any]]]] = []

        for query, results in per_variant_results.items():
            formatted = []
            for i, result in enumerate(results):
                chunk_id = result.get("chunk_id", f"unknown_{i}")
                score = result.get("confidence", result.get("score", 0.5))
                metadata = result.copy()

                all_chunks[chunk_id] = metadata
                formatted.append((chunk_id, score, metadata))

            rank_lists.append(formatted)

        if not rank_lists:
            return []

        # Apply RRF iteratively
        if len(rank_lists) == 1:
            # Just one query, return as-is
            return list(all_chunks.values())[:top_k]

        # Start with first list
        fused = rank_lists[0]

        # Merge each subsequent list
        for lst in rank_lists[1:]:
            fused = self._rrf_merge(fused, lst, k=60)

        # Sort by score and deduplicate
        seen = set()
        merged = []
        for chunk_id, score, *rest in sorted(fused, key=lambda x: x[1], reverse=True):
            if chunk_id not in seen:
                seen.add(chunk_id)
                result = all_chunks.get(chunk_id, {})
                result["multi_query_score"] = score
                merged.append(result)
                if len(merged) >= top_k:
                    break

        return merged

    def _rrf_merge(
        self,
        list1: List[Tuple[str, float, Dict[str, Any]]],
        list2: List[Tuple[str, float, Dict[str, Any]]],
        k: int = 60,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Simple RRF merge of two lists."""
        scores: Dict[str, float] = {}

        for i, (chunk_id, _, _) in enumerate(list1):
            scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + i + 1)

        for i, (chunk_id, _, _) in enumerate(list2):
            scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + i + 1)

        # Get metadata
        all_chunks = {c[0]: c[2] for c in list1}
        all_chunks.update({c[0]: c[2] for c in list2})

        # Sort by RRF score
        result = [(cid, score, all_chunks.get(cid, {})) for cid, score in scores.items()]
        result.sort(key=lambda x: x[1], reverse=True)

        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get multi-query statistics."""
        return {
            "enabled": self.enabled,
            "queries_processed": self._queries_processed,
            "multi_queries_executed": self._multi_queries_executed,
            "multi_query_rate": (
                self._multi_queries_executed / self._queries_processed
                if self._queries_processed > 0
                else 0
            ),
        }


# Convenience function
async def retrieve_with_variants(
    query: str,
    qdrant_client: Any,
    top_k: int = 10,
) -> MultiQueryResult:
    """
    Quick multi-query retrieval.

    Args:
        query: User query
        qdrant_client: QdrantClient instance
        top_k: Number of results

    Returns:
        MultiQueryResult
    """
    retriever = MultiQueryRetriever(qdrant_client)
    return await retriever.retrieve(query, top_k=top_k)
