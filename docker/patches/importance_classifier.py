"""
Importance and Stability Classifier

Feature: 009-memory-decay-scoring
See: specs/009-memory-decay-scoring/quickstart.md

This module classifies memories for importance (1-5) and stability (1-5)
using LLM inference. Falls back to neutral defaults when LLM unavailable.

Importance Levels:
    1 = Trivial (can forget immediately)
    2 = Low (useful but replaceable)
    3 = Moderate (general knowledge)
    4 = High (important to work/identity)
    5 = Core (fundamental, never forget)

Stability Levels:
    1 = Volatile (changes in hours/days)
    2 = Low (changes in days/weeks)
    3 = Moderate (changes in weeks/months)
    4 = High (changes in months/years)
    5 = Permanent (never changes)

Permanent Classification:
    Memories with importance >= 4 AND stability >= 4 are classified as PERMANENT
    and are exempt from decay (decay_score always 0.0, always ACTIVE state).
"""

import json
import logging
import os
import re
import time
from typing import Optional, Tuple, Any

from utils.decay_config import get_default_classification, get_permanent_thresholds
from utils.metrics_exporter import get_decay_metrics_exporter

logger = logging.getLogger(__name__)

# ==============================================================================
# Dedicated Classification LLM Client
# ==============================================================================

_classification_llm_client = None


def get_classification_llm_client():
    """
    Get or create the dedicated LLM client for memory classification.

    Uses a separate model (liquid/lfm-2.5-1.2b-thinking:free) for classification
    while using the same environment configuration as the main LLM.

    Returns:
        LLM client instance or None if configuration is invalid
    """
    global _classification_llm_client

    if _classification_llm_client is not None:
        return _classification_llm_client

    try:
        from services.factories import LLMClientFactory
        from config.schema import LLMConfig, LLMProvidersConfig, OpenAIProviderConfig

        # Use same env config as main LLM, just different model
        classification_model = "openai/gpt-4o-mini"
        api_key = os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL", os.environ.get("MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL", "https://openrouter.ai/api/v1"))

        if not api_key:
            logger.warning("No OPENAI_API_KEY found, classification will use defaults")
            return None

        # Create LLMConfig for classification (same env, different model)
        llm_config = LLMConfig(
            provider="openai",
            model=classification_model,
            temperature=0.0,  # Deterministic for classification
            max_tokens=100,  # Only need JSON response
            providers=LLMProvidersConfig(
                openai=OpenAIProviderConfig(
                    api_key=api_key,
                    api_url=base_url
                )
            )
        )

        # Create dedicated client for classification
        _classification_llm_client = LLMClientFactory.create(llm_config)

        logger.info(f"Created dedicated classification LLM client: {classification_model}")
        return _classification_llm_client

    except Exception as e:
        logger.warning(f"Failed to create classification LLM client: {e}")
        return None


# ==============================================================================
# Classification Prompt
# ==============================================================================

CLASSIFICATION_PROMPT = """Classify the following memory for long-term value and change frequency.

CRITICAL INSTRUCTION: AVOID NEUTRAL RATINGS. You MUST commit to a definite assessment.
- Rate 1 or 5 for extreme cases
- Rate 2 or 4 for clear cases
- Reserve 3 ONLY for genuine ambiguity - when truly uncertain, choose 2 or 4 instead

Memory: {content}

Importance (1–5) - Cost if forgotten:

Rate 5 (CORE) if: Critical identity, credentials, security, financial access, fundamental life facts
  Examples: SSN, passwords, API keys, private keys, account numbers, birth certificate, passport
  Test: Would losing this cause identity theft, financial loss, or lockout? → 5

Rate 4 (HIGH) if: Important to work/identity, frequently accessed, domain-specific knowledge
  Examples: Key project decisions, technical preferences, important relationships, career milestones, research findings
  Test: Is this referenced weekly or essential for work/identity? → 4

Rate 3 (MODERATE) ONLY if: Genuinely ambiguous - moderately useful but not critical
  Examples: General processes, explanations, reference information, non-critical insights, meeting notes
  Test: Is this useful context but easily recovered or not frequently needed? → 3

Rate 2 (LOW) if: Easily rediscovered, replaceable, generic public information
  Examples: Public facts (capital cities, common knowledge), general references, Wikipedia-style info, basic documentation
  Test: Could this be found with 30 seconds of googling? Is it common knowledge? → 2

Rate 1 (TRIVIAL) if: No lasting value, transient context, disposable thoughts, vagueness without specifics
  Examples: "remember to call back", "wonder about X", temporary notes, fleeting thoughts, throwaway context, vague musings, unfinished ideas, casual observations, weather comments, idle questions
  Test: Is this a temporary reminder, vague thought, question, or trivial observation that adds no lasting value? → 1

Stability (1–5) - Likelihood of change:

Rate 5 (PERMANENT) if: Never changes - historical facts, fixed identity, unchangeable past events
  Test: Will this still be true in 10 years? → 5

Rate 4 (HIGH) if: Changes in months/years - long-term plans, established practices, core beliefs
  Test: Will this likely be true 6 months from now? → 4

Rate 3 (MODERATE) ONLY if: Changes in weeks/months - ongoing projects, evolving processes
  Test: Might this change in the next 1-2 months? → 3

Rate 2 (LOW) if: Changes in days/weeks - drafts, evolving ideas, short-term plans, current status
  Test: Is this likely to change within the next week? → 2

Rate 1 (VOLATILE) if: Changes in hours/days - temporary states, breaking news, momentary thoughts, fleeting contexts
  Test: Is this relevant only right now or for the next few hours? → 1

DECISION FRAMEWORK:
1. First ask: Is this CRITICAL (5) or TRIVIAL (1)? Most content falls between.
2. Then ask: Is this IMPORTANT to maintain (4) or EASILY REPLACED (2)?
3. Only use 3 if genuinely uncertain after steps 1-2.

Remember: When in doubt, choose 2 or 4. Avoid 3 unless truly ambiguous.

Respond with JSON only:
{{"importance": N, "stability": N}}"""


# ==============================================================================
# Classification Functions
# ==============================================================================

def is_permanent(importance: int, stability: int) -> bool:
    """
    Check if memory qualifies as permanent (exempt from decay).

    Permanent memories:
    - Never accumulate decay score (always 0.0)
    - Never transition states (always ACTIVE)
    - Not subject to archival or deletion

    Args:
        importance: Importance score (1-5)
        stability: Stability score (1-5)

    Returns:
        True if memory is permanent (importance >= threshold AND stability >= threshold)
    """
    imp_threshold, stab_threshold = get_permanent_thresholds()
    return importance >= imp_threshold and stability >= stab_threshold


def validate_score(value: Any, name: str) -> int:
    """
    Validate and clamp a classification score to 1-5 range.

    Args:
        value: Raw value from LLM response
        name: Field name for logging

    Returns:
        Integer score clamped to 1-5
    """
    try:
        score = int(value)
        if score < 1:
            logger.warning(f"{name} score {score} below minimum, clamping to 1")
            return 1
        if score > 5:
            logger.warning(f"{name} score {score} above maximum, clamping to 5")
            return 5
        return score
    except (TypeError, ValueError):
        default_imp, default_stab = get_default_classification()
        default = default_imp if name == "importance" else default_stab
        logger.warning(f"Invalid {name} value '{value}', using default {default}")
        return default


def parse_classification_response(response: str) -> Tuple[int, int]:
    """
    Parse LLM response to extract importance and stability scores.

    Handles multiple response formats:
    - Clean JSON: {"importance": 3, "stability": 4}
    - JSON with text: "Based on analysis... {"importance": 3, "stability": 4}"
    - Markdown code blocks: ```json {"importance": 3} ```

    Args:
        response: Raw LLM response text

    Returns:
        Tuple of (importance, stability) scores

    Raises:
        ValueError: If response cannot be parsed
    """
    # Handle dict response from Graphiti's generate_response
    if isinstance(response, dict):
        importance = validate_score(response.get("importance"), "importance")
        stability = validate_score(response.get("stability"), "stability")
        return importance, stability

    # Handle string response
    # Strip whitespace
    response = response.strip()

    # Try to extract JSON from markdown code blocks
    code_block_match = re.search(r'```(?:json)?\s*(\{[^}]+\})\s*```', response, re.DOTALL)
    if code_block_match:
        response = code_block_match.group(1)

    # Try to find JSON object in response
    json_match = re.search(r'\{[^}]+\}', response)
    if json_match:
        try:
            data = json.loads(json_match.group())
            importance = validate_score(data.get("importance"), "importance")
            stability = validate_score(data.get("stability"), "stability")
            return importance, stability
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse classification from response: {response[:100]}")


async def classify_memory(
    content: str,
    llm_client: Any,
    source_description: Optional[str] = None
) -> Tuple[int, int]:
    """
    Classify a memory's importance and stability using LLM.

    Uses the provided llm_client with forced-choice prompts to overcome
    central tendency bias. Falls back to neutral defaults (3, 3) if:
    - LLM client is not available
    - LLM call fails
    - Response cannot be parsed

    Args:
        content: Memory content to classify
        llm_client: Graphiti LLM client instance for classification
        source_description: Optional source context for better classification

    Returns:
        Tuple of (importance, stability) scores (1-5 each)
    """
    # Get default values
    default_importance, default_stability = get_default_classification()
    decay_metrics = get_decay_metrics_exporter()

    # Use provided LLM client (forced-choice prompt addresses bias better than model switching)
    client_to_use = llm_client

    # If no LLM client available, return defaults
    if client_to_use is None:
        logger.debug("No LLM client available, using default classification")
        if decay_metrics:
            decay_metrics.record_classification(status="fallback", latency_seconds=0.0)
        return default_importance, default_stability

    start_time = time.time()
    try:
        # Build prompt with content
        prompt = CLASSIFICATION_PROMPT.format(content=content[:2000])  # Limit content length

        # Add source context if available
        if source_description:
            prompt = f"Source: {source_description}\n\n{prompt}"

        # Try to use Graphiti's Message format if available, otherwise use string
        # (for backward compatibility with tests and environments without graphiti_core)
        try:
            from graphiti_core.prompts.models import Message
            # Create message in format expected by Graphiti's generate_response
            messages = [Message(role="user", content=prompt)]
            response = await client_to_use.generate_response(messages)
        except (ImportError, ModuleNotFoundError):
            # Fallback: pass prompt as string (for tests and legacy code)
            response = await client_to_use.generate_response(prompt)

        latency = time.time() - start_time

        # Debug: log raw response type and content for troubleshooting
        logger.debug(f"Raw LLM response type: {type(response)}, content: {response}")

        # Parse response
        importance, stability = parse_classification_response(response)

        # Record success metrics
        if decay_metrics:
            decay_metrics.record_classification(status="success", latency_seconds=latency)

        logger.debug(
            f"Classified memory: importance={importance}, stability={stability}, "
            f"permanent={is_permanent(importance, stability)}, latency={latency:.3f}s"
        )

        return importance, stability

    except Exception as e:
        latency = time.time() - start_time
        import traceback
        logger.warning(f"Classification failed, using defaults: {e}\nTraceback: {traceback.format_exc()}")

        # Record failure metrics
        if decay_metrics:
            decay_metrics.record_classification(status="failure", latency_seconds=latency)

        return default_importance, default_stability


async def classify_memory_batch(
    contents: list[str],
    llm_client: Any,
    batch_size: int = 10
) -> list[Tuple[int, int]]:
    """
    Classify multiple memories in batch.

    For efficiency when classifying many memories at once.

    Args:
        contents: List of memory contents to classify
        llm_client: Graphiti LLM client instance (or None)
        batch_size: Number of concurrent classifications

    Returns:
        List of (importance, stability) tuples, one per input
    """
    import asyncio

    results = []

    # Process in batches to avoid overwhelming the LLM
    for i in range(0, len(contents), batch_size):
        batch = contents[i:i + batch_size]

        # Classify batch concurrently
        tasks = [classify_memory(content, llm_client) for content in batch]
        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)

    return results


# ==============================================================================
# Classification Source Tracking
# ==============================================================================

class ClassificationSource:
    """Track how a classification was determined."""
    LLM = "llm"           # Classified by LLM
    DEFAULT = "default"   # Used default values (LLM unavailable)
    MANUAL = "manual"     # Manually set by admin


def get_classification_with_source(
    importance: int,
    stability: int,
    source: str = ClassificationSource.LLM
) -> dict:
    """
    Create classification result with source tracking.

    Args:
        importance: Importance score (1-5)
        stability: Stability score (1-5)
        source: How classification was determined

    Returns:
        Dictionary with classification details
    """
    return {
        "importance": importance,
        "stability": stability,
        "is_permanent": is_permanent(importance, stability),
        "classification_source": source,
    }


# ==============================================================================
# T012/T013: Classify and Initialize New Nodes
# ==============================================================================

# Query to find unclassified nodes (nodes without importance attribute)
FIND_UNCLASSIFIED_NODES_QUERY = """
MATCH (n:Entity)
WHERE n.`attributes.importance` IS NULL
RETURN n.uuid AS uuid, n.name AS name, n.summary AS summary
LIMIT $limit
"""

# Query to set classification and initial decay attributes
SET_CLASSIFICATION_QUERY = """
MATCH (n:Entity {uuid: $uuid})
SET n.`attributes.importance` = $importance,
    n.`attributes.stability` = $stability,
    n.`attributes.decay_score` = 0.0,
    n.`attributes.lifecycle_state` = 'ACTIVE',
    n.`attributes.last_accessed_at` = toString(datetime()),
    n.`attributes.access_count` = 0,
    n.`attributes.soft_deleted_at` = null,
    n.`attributes.classification_source` = $source
RETURN n.uuid AS uuid
"""

# Query to count unclassified nodes
COUNT_UNCLASSIFIED_QUERY = """
MATCH (n:Entity)
WHERE n.`attributes.importance` IS NULL
RETURN count(n) AS count
"""


async def count_unclassified_nodes(driver) -> int:
    """
    Count nodes that haven't been classified yet.

    Args:
        driver: Neo4j driver instance

    Returns:
        Number of unclassified nodes
    """
    logger.info(f"count_unclassified_nodes: driver={driver}, running query: {COUNT_UNCLASSIFIED_QUERY.strip()}")
    async with driver.session() as session:
        result = await session.run(COUNT_UNCLASSIFIED_QUERY)
        record = await result.single()
        count = record["count"] if record else 0
        logger.info(f"count_unclassified_nodes: found {count} unclassified nodes (record={record})")
        return count


async def classify_and_initialize_node(
    driver,
    llm_client,
    uuid: str,
    name: str,
    summary: Optional[str] = None
) -> bool:
    """
    Classify a single node and set initial decay attributes.

    This is T012 + T013: classify importance/stability AND set initial
    lifecycle_state='ACTIVE', decay_score=0.0, etc.

    Args:
        driver: Neo4j driver instance
        llm_client: Graphiti LLM client for classification
        uuid: Node UUID
        name: Node name (entity name)
        summary: Optional node summary for better classification

    Returns:
        True if node was classified and updated
    """
    # Build content for classification from name and summary
    content = name
    if summary:
        content = f"{name}: {summary}"

    # Classify using LLM (falls back to defaults if unavailable)
    importance, stability = await classify_memory(content, llm_client)

    # Determine classification source
    source = ClassificationSource.LLM if llm_client else ClassificationSource.DEFAULT

    # Set classification and initial decay attributes
    async with driver.session() as session:
        result = await session.run(
            SET_CLASSIFICATION_QUERY,
            uuid=uuid,
            importance=importance,
            stability=stability,
            source=source,
        )
        record = await result.single()

        if record and record["uuid"]:
            logger.debug(
                f"Classified node {uuid}: importance={importance}, stability={stability}, "
                f"permanent={is_permanent(importance, stability)}"
            )
            return True

        return False


async def classify_unclassified_nodes(
    driver,
    llm_client,
    batch_size: int = 50,
    max_nodes: int = 500
) -> dict:
    """
    Find and classify nodes that haven't been classified yet.

    This implements T012/T013: for each unclassified node:
    1. Classify importance/stability using LLM (T012)
    2. Set initial decay attributes (T013):
       - lifecycle_state='ACTIVE'
       - decay_score=0.0
       - last_accessed_at=now
       - access_count=0

    Called as part of maintenance cycle or manually via MCP tool.

    Args:
        driver: Neo4j driver instance
        llm_client: Graphiti LLM client for classification (or None for defaults)
        batch_size: Number of nodes to fetch per batch
        max_nodes: Maximum nodes to classify in one run

    Returns:
        Dictionary with classification results:
        - found: Number of unclassified nodes found
        - classified: Number successfully classified
        - failed: Number that failed classification
        - using_llm: Whether LLM was used (vs defaults)
    """
    results = {
        "found": 0,
        "classified": 0,
        "failed": 0,
        "using_llm": llm_client is not None,
    }

    # First count total unclassified
    total_unclassified = await count_unclassified_nodes(driver)
    results["found"] = total_unclassified

    if total_unclassified == 0:
        logger.debug("No unclassified nodes found")
        return results

    logger.info(f"Found {total_unclassified} unclassified nodes, processing up to {max_nodes}")

    # Process in batches
    processed = 0
    limit = min(batch_size, max_nodes)

    while processed < max_nodes:
        # Fetch batch of unclassified nodes
        async with driver.session() as session:
            result = await session.run(FIND_UNCLASSIFIED_NODES_QUERY, limit=limit)
            nodes = [record async for record in result]

        if not nodes:
            break

        # Classify each node
        for node in nodes:
            try:
                success = await classify_and_initialize_node(
                    driver,
                    llm_client,
                    uuid=node["uuid"],
                    name=node["name"],
                    summary=node.get("summary"),
                )
                if success:
                    results["classified"] += 1
                else:
                    results["failed"] += 1
            except Exception as e:
                logger.warning(f"Failed to classify node {node['uuid']}: {e}")
                results["failed"] += 1

            processed += 1
            if processed >= max_nodes:
                break

    logger.info(
        f"Classification complete: {results['classified']} classified, "
        f"{results['failed']} failed, {total_unclassified - processed} remaining"
    )

    return results
