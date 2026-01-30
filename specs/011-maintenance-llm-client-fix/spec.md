# Feature Specification: LLM Client for Maintenance Classification

**Feature Branch**: `011-maintenance-llm-client-fix`
**Created**: 2026-01-30
**Status**: Draft
**Input**: User description: "Fix Issue #21 - Maintenance service not receiving LLM client for importance/stability classification, causing all nodes to default to importance=3 instead of using configured LLM model"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Intelligent Memory Classification (Priority: P1)

When a knowledge episode is added to the system, the maintenance service should use the configured LLM model to intelligently classify the importance and stability of extracted entities. This enables the system to prioritize truly important memories and decay less critical ones over time.

**Why this priority**: This is the core value proposition of the memory decay system - without intelligent classification, all memories are treated equally, defeating the purpose of importance-based decay scoring.

**Independent Test**: Can be fully tested by adding a knowledge episode about a critical topic (e.g., "My SSH private key is stored at ~/.ssh/id_rsa"), running maintenance, and verifying that the extracted entity receives a high importance score (4 or 5) instead of the default 3.

**Acceptance Scenarios**:

1. **Given** a new knowledge episode is added about a critical topic, **When** maintenance runs classification, **Then** the extracted entities receive importance scores that reflect their actual importance (not default 3)
2. **Given** a new knowledge episode is added about a trivial topic, **When** maintenance runs classification, **Then** the extracted entities receive low importance scores (1 or 2)
3. **Given** the LLM client is unavailable or misconfigured, **When** maintenance runs classification, **Then** the system gracefully falls back to default values (3, 3) and logs a warning

---

### User Story 2 - Immediate Classification (Priority: P1)

When a knowledge episode is added, the system should immediately begin classifying extracted entities in the background, without waiting for the periodic maintenance cycle. This ensures entities have meaningful importance scores as soon as possible after creation.

**Why this priority**: Reduces classification delay from hours/days (maintenance interval) to seconds/minutes, improving user experience and system responsiveness.

**Independent Test**: Can be tested by adding a knowledge episode and immediately checking health metrics - entities should have non-default importance scores within 1-2 minutes instead of waiting for the next maintenance cycle.

**Acceptance Scenarios**:

1. **Given** a new knowledge episode is added, **When** the add_memory call returns, **Then** a background classification task is spawned immediately
2. **Given** the background classification task completes, **When** health metrics are checked, **Then** newly created entities have non-default importance scores
3. **Given** the immediate classification fails, **When** maintenance runs, **Then** entities are still classified (maintenance acts as backup)

---

### User Story 3 - Configurable LLM Provider (Priority: P2)

The system should use whichever LLM provider is configured (OpenAI, Anthropic, OpenRouter, etc.) for classification tasks, ensuring consistency across all LLM-dependent operations.

**Why this priority**: Ensures the system works with the user's preferred LLM provider and maintains consistency between entity extraction and classification.

**Independent Test**: Can be tested by configuring different LLM providers in the environment, adding episodes, running maintenance, and verifying that the configured provider is used for classification (evidenced by different classification results).

**Acceptance Scenarios**:

1. **Given** OpenAI is configured as the LLM provider, **When** maintenance runs classification, **Then** classifications use the OpenAI API
2. **Given** OpenRouter is configured as the LLM provider, **When** maintenance runs classification, **Then** classifications use the OpenRouter API

---

### Edge Cases

- What happens when the LLM client becomes unavailable during maintenance? (Should fall back to defaults and continue)
- What happens when the LLM returns invalid or out-of-range scores? (Should clamp to valid range 1-5)
- What happens when maintenance is interrupted mid-classification? (Should be idempotent and resume on next run)
- What happens when an entity was already classified manually? (Should respect existing classification and not reclassify)
- What happens when the configured LLM model doesn't support the classification prompt format? (Should handle gracefully and fall back to defaults)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST extract the LLM client from the Graphiti service instance
- **FR-002**: System MUST pass the LLM client to the maintenance service during initialization
- **FR-003**: System MUST use the LLM client for importance/stability classification during maintenance
- **FR-004**: System MUST trigger immediate background classification after queuing a new episode (Option D approach)
- **FR-005**: System MUST fall back to default values (3, 3) when LLM client is unavailable
- **FR-006**: System MUST log when using LLM-based classification vs default fallback
- **FR-007**: System MUST handle LLM API errors gracefully without failing maintenance
- **FR-008**: All 4 maintenance service initialization points MUST receive the LLM client parameter
- **FR-009**: Immediate classification task MUST use small batch size (100) for quick processing
- **FR-010**: Maintenance cycle MUST remain operational as backup safety net

### Key Entities

- **LLM Client**: The language model client configured for the knowledge graph (OpenAI, Anthropic, OpenRouter, etc.) - used for generating classifications
- **Maintenance Service**: Background service that processes unclassified nodes and applies decay scoring
- **Importance Score**: 1-5 rating of how critical a memory is (1=trivial, 5=core)
- **Stability Score**: 1-5 rating of how permanent a memory is (1=volatile, 5=permanent)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Maintenance classifications use LLM model (not defaults) in 100% of runs when LLM is configured and available
- **SC-002**: At least 80% of newly added entities receive non-default importance scores (not equal to 3)
- **SC-003**: Immediate background classification spawns within 1 second after add_memory returns
- **SC-004**: Background classification completes within 2 minutes for batches of up to 100 entities (immediate mode)
- **SC-005**: Classification completes within 30 seconds for batches of up to 500 entities (maintenance mode)
- **SC-006**: System recovers gracefully from LLM failures (maintenance completes successfully with logged fallback to defaults)

## Research References

This specification is informed by codebase research conducted on 2026-01-30:
- **Research Focus**: Real-time importance classification at episode add time
- **Tools Used**: Codanna code intelligence (semantic search, symbol analysis)
- **Key Findings**: Graphiti QueueService is external library with no hooks; Option D (immediate background task) is recommended approach
- **Related Issues**: #21 (Maintenance service LLM client bug), potential #22 (Real-time classification enhancement)

## Assumptions

- Graphiti service instance provides access to the configured LLM client via `client.llm_client` attribute
- LLM client is already configured and working for other operations (entity extraction, search)
- The classification prompt in `importance_classifier.py` is compatible with the configured LLM model
- Default values (3, 3) are appropriate fallback for unclassified entities
- Immediate classification will run in small batches (100) to avoid overwhelming the LLM API
- Background task creation via `asyncio.create_task()` is safe and won't cause resource issues
- Graphiti background processing will complete before classification task runs (race condition acceptable - maintenance catches misses)
- Existing maintenance schedule remains as secondary safety net

## Implementation Approach

### Architectural Research Findings

Research into the codebase revealed that implementing real-time classification requires understanding the current flow:

```
add_memory (returns immediately)
    ↓
queue_service.add_episode() (Graphiti QueueService - external library)
    ↓
[Background Processing by Graphiti]
    → Extracts entities from episode
    → Creates nodes WITHOUT importance attributes (NULL)
    → No hooks/callbacks available in external library
    ↓
Maintenance Service (periodic - could be hours/days)
    → Finds nodes where importance IS NULL
    → Classifies using LLM
```

### Recommended Approach: Immediate Background Classification (Option D)

Instead of waiting for the periodic maintenance cycle, trigger classification immediately after queuing the episode:

**Changes Required:**

1. **In `add_memory` function** (`docker/patches/graphiti_mcp_server.py:818`):
   - After `queue_service.add_episode()` returns
   - Spawn background task: `asyncio.create_task(classify_unclassified_nodes(...))`
   - Use small batch size (100) for immediate processing
   - Continue with maintenance as backup

2. **Import Required**:
   ```python
   from utils.importance_classifier import classify_unclassified_nodes
   ```

3. **Benefits**:
   - ✅ Classification runs immediately (not hours/days later)
   - ✅ Non-blocking (runs in background)
   - ✅ Minimal code changes
   - ✅ Maintenance remains as safety net

### Alternative Approaches Considered

| Approach | Pros | Cons | Decision |
|----------|------|-------|----------|
| A: Synchronous Processing | Immediate classification | Blocks user, slow response | Rejected |
| B: Extended QueueService | Clean architecture | Requires forking external library | Rejected |
| C: Post-Process Callback | Non-blocking | Complex episode tracking | Rejected |
| **D: Immediate Background** | Simple, non-blocking, immediate | Small delay before classification | **Selected** |
| E: Smart Defaults + Async LLM | Best UX | Requires modifying Graphiti core | Future enhancement |

## Out of Scope

- Modifying the classification prompt or logic
- Changing the importance/stability score ranges
- Modifying the maintenance schedule or batch processing
- Adding new LLM providers
- Implementing manual classification override UI
- Modifying the external Graphiti library (queue_service)
- Waiting for episode completion before classification (too complex for this fix)
