# Research: AsyncSession Compatibility Fix

**Feature**: 021-fix-async-session
**Date**: 2026-02-05
**Status**: Complete

## Research Task 1: Neo4j AsyncSession Patterns

### Question
What is the correct async syntax for Neo4j Python driver's AsyncSession?

### Findings
From analysis of existing MCP server code (`docker/patches/graphiti_mcp_server.py`):

**Correct async pattern** (line 1647):
```python
async with client.driver.session() as session:
    result = await session.run('MATCH (n) RETURN count(n) as count')
    if result:
        _ = [record async for record in result]
```

**Key elements**:
1. Use `async with` (not `with`) to enter AsyncSession context
2. Use `await session.run()` for queries (not `session.run()`)
3. Use async comprehension: `[record async for record in result]`

**Decision**: ✅ Adopt `async with driver.session() as session:` pattern

### Alternatives Considered
- **Synchronous wrapper**: Run sync code in thread pool executor
  - Rejected: Adds complexity, defeats async architecture purpose
- **Callback-based pattern**: Use Neo4j's callback API
  - Rejected: Less readable, not compatible with async/await ecosystem

---

## Research Task 2: Graphiti Async Architecture

### Question
How does Graphiti's async client work with Neo4j driver?

### Findings
From `docker/patches/graphiti_mcp_server.py`:

**Graphiti client access** (line 1707):
```python
client = await graphiti_service.get_client()
```

**Driver access pattern**:
- `client.driver` is the Neo4j async driver instance
- Already configured for async in graphiti_service initialization
- All MCP tools follow this pattern consistently

**Decision**: ✅ Use `client.driver` directly from Graphiti client

### Implementation Pattern
The MCP server's `investigate_entity` function (line 1667) is async and should await the traversal:

**Current (broken)**:
```python
traversal_result = traversal.traverse(...)  # Sync call fails
```

**Required (fixed)**:
```python
traversal_result = await traversal.traverse(...)  # Async call
```

This requires `GraphTraversal.traverse()` to become an async method.

---

## Research Task 3: Backward Compatibility Strategy

### Question
Should we support both sync and async, or async-only?

### Findings
**Current state analysis**:
- Neo4j backend: Requires async (MCP server uses async driver)
- FalkorDB backend: Currently synchronous (line 470: `self.driver.graph().query()`)
- MCP server: Only uses Neo4j async driver

**Decision**: ✅ Dual implementation strategy

**Rationale**:
1. FalkorDB doesn't have async client in current implementation
2. Spec states FalkorDB async support is "Out of Scope"
3. Dual implementation allows FalkorDB to continue working with sync code
4. Neo4j gets async path for compatibility

**Implementation approach**:
```python
class GraphTraversal:
    def __init__(self, driver, database_type, logger):
        self.driver = driver
        self.database_type = database_type.lower()

    async def traverse(self, ...):
        if self.database_type == "neo4j":
            return await self._traverse_neo4j_async(...)
        else:  # falkordb
            return self._traverse_falkordb_sync(...)

    async def _traverse_neo4j_async(self, ...):
        async with self.driver.session() as session:
            # async implementation

    def _traverse_falkordb_sync(self, ...):
        # existing synchronous implementation
```

**API compatibility**:
- `traverse()` becomes async (returns coroutine)
- FalkorDB path runs sync code but wrapped in async function
- Caller must await: `result = await traversal.traverse(...)`

---

## Dependency Analysis

### Neo4j Python Driver Version
**Status**: ✅ Confirmed in base image
- Base image: `zepai/knowledge-graph-mcp:standalone`
- AsyncSession context manager is available
- Used extensively in existing MCP server code

### FalkorDB Async Support
**Status**: ⏸️ Deferred (Out of Scope per spec)
- Current: Synchronous redis client
- Future: May require redis-py async client
- Not blocking for this fix

---

## Integration Points

### MCP Server → GraphTraversal

**Current code** (`graphiti_mcp_server.py:1750-1761`):
```python
traversal = GraphTraversal(
    driver=client.driver,
    database_type=config.database.provider,
    logger=logger
)

traversal_result = traversal.traverse(
    start_entity_uuid=start_uuid,
    max_depth=max_depth,
    relationship_types=relationship_types,
    group_ids=effective_group_ids
)
```

**Required changes**:
1. Add `await` to traverse call: `traversal_result = await traversal.traverse(...)`
2. GraphTraversal.traverse() becomes async method
3. FalkorDB sync implementation wrapped to return awaitable coroutine

### Return Value Compatibility

**Current**: `TraversalResult` dataclass with attributes
- `connections: List[Dict]`
- `depth_explored: int`
- `total_connections_explored: int`
- etc.

**Status**: ✅ No changes needed
- Return structure remains the same
- Only internal implementation changes to async

---

## Summary of Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Async syntax | `async with driver.session()` | Matches existing MCP server patterns |
| Driver access | Use `client.driver` directly | Already async from graphiti_service |
| Compatibility | Dual (async Neo4j, sync FalkorDB) | FalkorDB async deferred, maintains functionality |
| API change | `traverse()` becomes async | Minimal change, caller adds `await` |

**Next Phase**: Generate data-model.md, contracts/, and quickstart.md
