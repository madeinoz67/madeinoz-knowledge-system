# Research: MCP Wrapper for Token Savings

**Feature Branch**: `001-mcp-wrapper`
**Date**: 2026-01-18
**Status**: Complete

## Research Questions

### R1: Optimal Output Format for Token Savings

**Question**: What output format provides the best token savings while preserving semantic meaning?

**Research Findings**:

1. **Current State Analysis**: The existing MCP wrapper (`src/server/mcp-wrapper.ts`) outputs full JSON responses via `JSON.stringify(result.data, null, 2)`. This includes:
   - Verbose field names (e.g., `source_description`, `reference_timestamp`)
   - Deeply nested structures for entity relationships
   - Redundant metadata (UUIDs, timestamps, internal identifiers)

2. **Format Comparison** (estimated token counts based on chars/4):

   | Format | Example Search Result | Est. Tokens | Savings vs JSON |
   |--------|----------------------|-------------|-----------------|
   | Pretty JSON | Full response with indentation | ~800 | Baseline |
   | Compact JSON | Minified, no whitespace | ~600 | 25% |
   | Markdown Table | Entity/summary format | ~400 | 50% |
   | Line-based | One entity per line | ~350 | 56% |

3. **Semantic Preservation Requirements**:
   - Entity names and summaries MUST be preserved
   - Relationship types MUST be preserved
   - UUIDs can be truncated to last 8 chars for reference
   - Timestamps can use relative format ("2h ago") vs ISO
   - Metadata like `created_at`, `valid_at` can be omitted

**Decision**: Use line-based compact format as primary output with optional Markdown table for structured data.

**Rationale**: Line-based format provides maximum token savings (56%+) while maintaining readability. Human readers and LLMs can parse effectively. Markdown tables add structure when multiple entities have common fields.

**Alternatives Rejected**:
- Compact JSON: Still verbose, field names consume tokens
- XML: More verbose than JSON
- CSV: Poor for nested relationships

---

### R2: Fallback Strategy for Transformation Failures

**Question**: When should the wrapper fall back to direct MCP operations and how should failures be logged?

**Research Findings**:

1. **Failure Scenarios Identified**:
   - Unexpected response structure from MCP server
   - Missing required fields in response
   - Transformation timeout (>100ms)
   - Memory pressure during large result sets

2. **Existing Patterns**: The mcp-client.ts already has error handling:
   ```typescript
   if (!result.success) {
     cli.error(`Error: ${result.error}`);
     return 1;
   }
   ```

3. **Logging Requirements** (from spec clarifications):
   - Log transformation failures for analysis
   - Include: operation name, input size, error message, timestamp
   - Log file location: `$HOME/.madeinoz-knowledge/wrapper.log`

**Decision**: Implement try/catch around transformation with structured logging and automatic fallback to raw JSON output.

**Rationale**: Never block functionality - if transformation fails, show raw output and log for later analysis. This aligns with Constitution Principle V (Graceful Degradation).

**Implementation Pattern**:
```typescript
try {
  const compact = formatCompact(result.data, operation);
  return compact;
} catch (error) {
  logTransformationFailure(operation, result.data, error);
  return JSON.stringify(result.data, null, 2); // Fallback
}
```

---

### R3: Token Measurement Methodology

**Question**: How to accurately measure token savings for validation?

**Research Findings**:

1. **Spec Clarification**: Hybrid approach confirmed:
   - Primary: Response size in bytes
   - Secondary: Estimated tokens via chars/4 formula

2. **Measurement Points**:
   - Before transformation: `Buffer.byteLength(JSON.stringify(data))`
   - After transformation: `Buffer.byteLength(compactOutput)`
   - Percentage: `100 - (after / before * 100)`

3. **Benchmark Design**:
   ```typescript
   interface TokenMetrics {
     operation: string;
     rawBytes: number;
     compactBytes: number;
     savingsPercent: number;
     estimatedTokensBefore: number;
     estimatedTokensAfter: number;
   }
   ```

4. **Statistical Validity**:
   - Run each operation 10x with varied inputs
   - Report mean, median, and std deviation
   - Flag operations with <25% savings for review

**Decision**: Implement `token-metrics.ts` module with dual measurement (bytes + estimated tokens) and statistical aggregation.

**Rationale**: Bytes are precise and measurable; estimated tokens provide context for API cost discussions. Both metrics together validate the feature's value proposition.

---

### R4: Output Format Per Operation Type

**Question**: Should different MCP operations use different compact formats?

**Research Findings**:

1. **Operation Categories**:

   | Category | Operations | Optimal Format |
   |----------|-----------|----------------|
   | Search Results | search_nodes, search_facts | Numbered list with summaries |
   | Single Item | get_status, get_entity_edge | Key-value pairs |
   | Collections | get_episodes | Date-grouped list |
   | Mutations | add_memory, delete_* | Success/failure with ID |
   | System | clear_graph | Confirmation message |

2. **Format Specifications**:

   **Search Results (Nodes)**:
   ```
   Found 3 entities for "Graphiti":
   1. Graphiti [Framework] - Knowledge graph framework with temporal context
   2. FalkorDB [Database] - Graph database backend for Graphiti
   3. MCP Server [Service] - Model Context Protocol server for Graphiti
   ```

   **Search Results (Facts)**:
   ```
   Found 2 relationships for "Graphiti FalkorDB":
   1. Graphiti --uses--> FalkorDB (confidence: 0.95)
   2. FalkorDB --stores--> Knowledge Graph (confidence: 0.88)
   ```

   **Episodes**:
   ```
   Recent episodes (3):
   - [2h ago] Podman Volume Syntax - volume mounting best practices
   - [1d ago] Architecture Decision - Graphiti selection rationale
   - [3d ago] VS Code Preferences - development environment setup
   ```

   **Status**:
   ```
   Knowledge Graph Status: HEALTHY
   Entities: 142 | Episodes: 47 | Last update: 5m ago
   ```

   **Mutations**:
   ```
   ✓ Episode added: "New Learning" (id: ...a1b2c3d4)
   ```

**Decision**: Implement operation-specific formatters in `output-formatter.ts` with a registry pattern.

**Rationale**: Each operation type has different data shapes. Tailored formats maximize token savings while preserving readability.

---

### R5: Workflow Integration Strategy

**Question**: How should skill workflows prefer the wrapper over direct MCP calls?

**Research Findings**:

1. **Current Workflow Pattern** (from SearchKnowledge.md):
   ```typescript
   search_nodes({
     query: searchQuery,
     limit: 10
   })
   ```
   Workflows currently reference raw MCP tools.

2. **Integration Options**:

   | Option | Pros | Cons |
   |--------|------|------|
   | A: Update workflow docs | Simple, non-breaking | Manual, may drift |
   | B: CLI wrapper only | Centralized, testable | Requires CLI invocation |
   | C: Both A+B | Maximum coverage | More maintenance |

3. **PAI Skill Pattern**: Skills already use workflow notification scripts and tool scripts. The wrapper CLI fits naturally as a tool.

**Decision**: Option B - CLI wrapper becomes the preferred interface. Workflow documentation updated to show CLI wrapper commands instead of raw MCP calls.

**Rationale**:
- CLI wrapper is testable and measurable
- Single point of transformation logic
- Workflows remain declarative (what to do, not how)
- Aligns with PAI's tool-based architecture

**Workflow Example (Updated)**:
```bash
# Before (direct MCP)
# search_nodes({ query: "Graphiti", limit: 10 })

# After (wrapper CLI)
bun run src/server/mcp-wrapper.ts search_nodes "Graphiti" 10
```

---

### R6: Performance Overhead Budget

**Question**: How to ensure wrapper processing stays under 100ms?

**Research Findings**:

1. **Performance Analysis**:
   - JSON.stringify: ~1ms for typical responses
   - String manipulation (transformation): ~5-10ms
   - Logging (async): ~0ms blocking
   - Total expected: ~10-15ms

2. **Mitigation Strategies**:
   - Pre-compile formatters (avoid runtime regex creation)
   - Stream large results instead of buffering
   - Use Map for O(1) operation type lookup

3. **Monitoring**:
   ```typescript
   const start = performance.now();
   const result = formatCompact(data, operation);
   const elapsed = performance.now() - start;
   if (elapsed > 50) {
     logSlowTransformation(operation, elapsed);
   }
   ```

**Decision**: Implement performance monitoring with 50ms warning threshold (half the budget) to catch regressions early.

**Rationale**: 100ms budget is generous; real processing should be <20ms. Early warning at 50ms allows investigation before user impact.

---

## Summary of Decisions

| Area | Decision | Confidence |
|------|----------|------------|
| Output Format | Line-based compact with operation-specific templates | High |
| Fallback Strategy | Try/catch with automatic raw JSON fallback + logging | High |
| Token Measurement | Dual metrics (bytes + chars/4) with statistical reporting | High |
| Per-Operation Formats | Registry of tailored formatters per operation type | High |
| Workflow Integration | CLI wrapper as primary interface, update workflow docs | High |
| Performance Monitoring | 50ms warning threshold, log slow transformations | High |

## Open Questions

None - all NEEDS CLARIFICATION items resolved.
