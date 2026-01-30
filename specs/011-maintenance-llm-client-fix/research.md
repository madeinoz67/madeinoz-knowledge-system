# Research: LLM Client for Maintenance Classification

**Feature**: 011-maintenance-llm-client-fix
**Date**: 2026-01-30
**Research Method**: Codanna code intelligence (semantic search, symbol analysis)

## Overview

This research documents the technical investigation into Issue #21: "Maintenance service not receiving LLM client for importance/stability classification." The root cause has been identified and the fix path is clear.

## Root Cause Analysis

### The Bug

`get_maintenance_service()` is being called at 4 locations in `graphiti_mcp_server.py` without passing the `llm_client` parameter:

| Line | Context | Current Call |
|------|---------|--------------|
| 788 | `GraphitiService.initialize()` | `get_maintenance_service(self.client.driver)` |
| 1475 | `get_knowledge_health()` | `get_maintenance_service(client.driver)` |
| 1532 | `run_decay_maintenance()` | `get_maintenance_service(client.driver)` |
| 1566 | `get_knowledge_health()` | `get_maintenance_service(client.driver)` |

Since `llm_client` defaults to `None`, all classifications fall back to default values (3, 3).

### The Fix Pattern

The codebase already has the correct pattern for accessing the LLM client:

```python
# From graphiti_mcp_server.py (existing pattern)
client = await graphiti_service.get_client()
llm_client = client.llm_client if hasattr(client, 'llm_client') else None
```

All 4 calls need to be updated to:
```python
maintenance = get_maintenance_service(client.driver, llm_client=client.llm_client)
```

## Research Decisions

### Decision 1: LLM Client Access Pattern

**Decision**: Access LLM client via `graphiti_client.llm_client` attribute

**Rationale**:
- The Graphiti library stores the LLM client as an instance attribute
- Existing code in `graphiti_mcp_server.py` already uses this pattern
- The `classify_memory()` function in `importance_classifier.py` demonstrates this works

**Alternatives Considered**:
- Storing llm_client separately: Rejected - would duplicate state
- Passing through GraphitiService: Rejected - unnecessary indirection

### Decision 2: Immediate Background Classification

**Decision**: Use `asyncio.create_task()` to spawn classification after `add_memory()`

**Rationale**:
- Non-blocking: returns immediately to user
- Simple: single line addition to existing function
- Safe: maintenance cycle acts as backup if background task misses entities

**Code Location**: `docker/patches/graphiti_mcp_server.py:858` (after `queue_service.add_episode()`)

**Implementation**:
```python
# After queue_service.add_episode(...) returns:
client = await graphiti_service.get_client()
asyncio.create_task(
    classify_unclassified_nodes(
        driver=client.driver,
        llm_client=client.llm_client,
        batch_size=100,  # Small batch for immediate processing
        max_nodes=100,
    )
)
```

**Alternatives Considered** (from spec.md):
- Synchronous Processing: Rejected - blocks user response
- Extended QueueService: Rejected - requires forking external library
- Post-Process Callback: Rejected - complex episode tracking

### Decision 3: Error Handling

**Decision**: Background task fires-and-forgets; errors logged but not propagated

**Rationale**:
- `add_memory()` must return immediately (non-blocking)
- Classification failures are non-critical (maintenance cycle retries)
- `classify_unclassified_nodes()` already has internal error handling

**Logging Requirement**: Add `logger.info()` when spawning background task

### Decision 4: Test Strategy

**Decision**: Integration test + manual verification

**Rationale**:
- Unit test would mock too much (LLM client, Neo4j driver)
- Integration test with running Neo4j can verify actual classification
- Manual verification via health metrics shows real-world behavior

**Test Cases**:
1. Add episode about critical topic → verify importance 4-5
2. Add episode about trivial topic → verify importance 1-2
3. Run with LLM unavailable → verify fallback to defaults (3, 3)

## Technical Findings

### File: `docker/patches/maintenance_service.py`

- `MaintenanceService.__init__()` already accepts `llm_client` parameter (line 252-258)
- `get_maintenance_service()` factory accepts and passes `llm_client` (line 644-650)
- `run_maintenance()` calls `classify_unclassified_nodes()` with `self._llm_client` (line 318)
- **No changes needed** - this file is already correct

### File: `docker/patches/importance_classifier.py`

- `classify_unclassified_nodes()` accepts `llm_client` parameter (line 401-406)
- Falls back to defaults when `llm_client is None` (line 437)
- **No changes needed** - this file is already correct

### File: `docker/patches/graphiti_mcp_server.py`

**Changes Required**:

1. **Line 788** (in `GraphitiService.initialize()`):
   ```python
   # Before:
   maintenance = get_maintenance_service(self.client.driver)
   # After:
   maintenance = get_maintenance_service(self.client.driver, llm_client=self.client.llm_client)
   ```

2. **Line 1475** (in `get_knowledge_health()`):
   ```python
   # Before:
   maintenance = get_maintenance_service(client.driver)
   # After:
   maintenance = get_maintenance_service(client.driver, llm_client=client.llm_client)
   ```

3. **Line 1532** (in `run_decay_maintenance()`):
   ```python
   # Before:
   maintenance = get_maintenance_service(client.driver)
   # After:
   maintenance = get_maintenance_service(client.driver, llm_client=client.llm_client)
   ```

4. **Line 1566** (in `get_knowledge_health()`):
   ```python
   # Before:
   maintenance = get_maintenance_service(client.driver)
   # After:
   maintenance = get_maintenance_service(client.driver, llm_client=client.llm_client)
   ```

5. **After line 866** (in `add_memory()`):
   ```python
   # Add after queue_service.add_episode() returns:
   try:
       client = await graphiti_service.get_client()
       asyncio.create_task(
           classify_unclassified_nodes(
               driver=client.driver,
               llm_client=client.llm_client,
               batch_size=100,
               max_nodes=100,
           )
       )
       logger.info(f"Spawned immediate background classification for episode '{name}'")
   except Exception as e:
       logger.warning(f"Failed to spawn background classification: {e}")
   ```

## Dependencies

### External Dependencies
- `graphiti-core`: Graphiti client library (external, no changes)
- Neo4j driver: Already in use
- LLM providers (OpenAI, Anthropic, etc.): Already configured

### Internal Dependencies
- `utils.importance_classifier.classify_unclassified_nodes`: Already exists
- `utils.maintenance_service.get_maintenance_service`: Already exists
- `graphiti_service.client.llm_client`: Already available

## Open Questions

**Q1**: Should immediate classification use the same batch size as maintenance?

**A1**: No - use smaller batch (100 vs 500) for faster response. Maintenance cycle will catch any misses.

**Q2**: What if `client.llm_client` is `None`?

**A2**: `classify_unclassified_nodes()` already handles `None` by falling back to defaults (3, 3). No additional code needed.

**Q3**: Should we wait for immediate classification to complete before returning?

**A3**: No - defeats the purpose of background processing. User gets immediate response; classification runs asynchronously.

## References

- **Codanna Commands Used**:
  - `codanna mcp semantic_search_with_context query:"maintenance service initialization"`
  - `codanna mcp find_symbol classify_unclassified_nodes`
  - `codanna mcp find_symbol MaintenanceService`
  - `codanna mcp find_callers get_maintenance_service`
  - `rg "get_maintenance_service" docker/patches/graphiti_mcp_server.py`

- **Key Files Analyzed**:
  - `docker/patches/maintenance_service.py` (lines 240-340, 644-650)
  - `docker/patches/importance_classifier.py` (lines 400-440)
  - `docker/patches/graphiti_mcp_server.py` (lines 601-680, 818-875, 1470-1570)

## Conclusion

The root cause is clear: 4 locations are calling `get_maintenance_service()` without the `llm_client` parameter. The fix is straightforward - pass `client.llm_client` at each call site. Additionally, immediate background classification can be added to `add_memory()` for better UX. No changes are needed to `maintenance_service.py` or `importance_classifier.py` as they already handle the LLM client correctly.
