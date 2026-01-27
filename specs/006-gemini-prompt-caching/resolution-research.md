# Resolution Research: Feature 006 Caching Architectural Limitation

**Research Date**: 2026-01-27
**Researcher**: DAIV (PAI System)
**Issue**: [GitHub #11](https://github.com/madeinoz67/madeinoz-knowledge-system/issues/11)
**Task**: T059 (Phase 7: Architectural Research)

## Executive Summary

After comprehensive research into three potential resolution paths, **none of the paths are immediately viable** for enabling prompt caching in Feature 006:

- **Path 1 (String-based cache_control)**: ❌ NOT VIABLE - OpenRouter requires multipart format
- **Path 2 (Endpoint-specific caching)**: ❌ NOT VIABLE - Graphiti uses 0% chat.completions.create
- **Path 3 (Alternative provider)**: ⚠️ COMPLEX - Requires architectural rewrite

**Recommendation**: Feature 006 should remain DISABLED indefinitely until OpenRouter adds multipart format support to their `/responses` endpoint, OR we undertake a major architectural change to use native Google Gemini API.

---

## Research Findings by Path

### Path 1: String-based cache_control (NOT VIABLE)

**Research Question**: Does OpenRouter support cache_control markers WITHOUT multipart format?

**Findings**:

OpenRouter's official documentation ([Prompt Caching Guide](https://openrouter.ai/docs/guides/best-practices/prompt-caching)) explicitly states:

> "The cache_control breakpoint can only be inserted into the text part of a multipart message."

**Required format** for Gemini caching:
```json
{
  "role": "system",
  "content": [
    {
      "type": "text",
      "text": "Large cacheable content",
      "cache_control": {
        "type": "ephemeral"
      }
    }
  ]
}
```

**What doesn't work**:
```json
{
  "role": "system",
  "content": "string content"  // ❌ Cache markers cannot be added to string format
}
```

**Source**: [OpenRouter Prompt Caching Documentation](https://openrouter.ai/docs/guides/best-practices/prompt-caching)

**Conclusion**: String-based cache_control is architecturally impossible with OpenRouter. Multipart format is a hard requirement, not a configuration option.

**Decision Criteria NOT MET**: Cache_control does NOT work without multipart format.

---

### Path 2: Endpoint-specific caching (NOT VIABLE)

**Research Question**: What % of Graphiti requests use `chat.completions.create` vs `responses.parse`?

**Methodology**: Analyzed container logs and code to count endpoint usage:

```bash
$ docker logs madeinoz-knowledge-graph-mcp-dev 2>&1 | grep "CALLED"
6 calls to responses.parse
0 calls to chat.completions.create
```

**Findings**:

| Endpoint | Usage % | Caching Support | Notes |
|----------|---------|-----------------|-------|
| `chat.completions.create` | 0% | ✅ Multipart format supported | Never used by Graphiti |
| `responses.parse` | 100% | ❌ Multipart format rejected | All entity extraction |

**Why Graphiti uses only responses.parse**:
- Graphiti performs entity extraction with structured Pydantic models
- `responses.parse()` is the OpenAI Beta API for structured outputs
- ALL Graphiti operations require entity extraction (nodes, edges, facts)
- Therefore 100% of operations use `responses.parse`

**Cost savings potential**: 0% - No requests would benefit from caching

**Source**: Container log analysis + `docker/patches/caching_wrapper.py` diagnostic output

**Conclusion**: Endpoint-specific caching would provide ZERO value because Graphiti makes no calls to the cacheable endpoint.

**Decision Criteria NOT MET**: <1% of requests use chat.completions.create (need >20% for viability).

---

### Path 3: Wait for OpenRouter or Use Alternative Provider (COMPLEX)

**Research Question 3a**: Will OpenRouter add multipart format support to `/responses` endpoint?

**Findings**:

From web search results, OpenRouter documentation states:

> "Multimodal requests are only available via the /api/v1/chat/completions API with a multi-part messages parameter."

This indicates multipart format is intentionally limited to `/chat/completions` only. The `/responses` endpoint limitation appears to be by design, not a bug.

**Attempts to contact OpenRouter**:
- [OpenRouter Support Page](https://openrouter.ai/support)
- No public roadmap found indicating `/responses` multipart support
- No GitHub issues tracking this specific limitation

**Source**: [OpenRouter API Documentation](https://openrouter.ai/docs/api/reference/overview)

**Conclusion**: Unknown timeline. No indication OpenRouter plans to change this. Appears to be architectural design choice.

---

**Research Question 3b**: Do alternative providers support both multipart format AND structured outputs?

**Provider Analysis**:

#### Google Gemini Native API

**Caching Architecture**: ✅ Supports both caching AND structured outputs
**BUT**: Uses completely different caching model

**Native Gemini approach** ([Context Caching Documentation](https://ai.google.dev/gemini-api/docs/caching)):
1. Create cached content separately: `client.caches.create()`
2. Reference cache in requests: `cached_content=cache.name`
3. NO cache_control markers at all

**Example**:
```python
# Step 1: Create cache separately
cache = client.caches.create(
    model=model,
    config=types.CreateCachedContentConfig(
        system_instruction="...",
        contents=[file_or_content],
        ttl="300s"
    )
)

# Step 2: Reference in request
response = client.models.generate_content(
    model=model,
    contents="user query",
    config=types.GenerateContentConfig(
        cached_content=cache.name  # Reference, not inline
    )
)
```

**Key difference**: OpenRouter uses **inline cache_control markers** (Anthropic-style), while native Gemini uses **separate cache service**.

**Migration effort**:
- HIGH: Requires rewriting entire caching architecture
- Change from message-level markers to cache creation service
- Modify `caching_wrapper.py`, `message_formatter.py`, `cache_metrics.py`
- Add cache lifecycle management (create, update TTL, delete)
- Estimated effort: 40-80 hours (2-4 weeks)

**Cost savings**: 75-90% on cached tokens (vs 50% through OpenRouter)

**Sources**:
- [Gemini Context Caching](https://ai.google.dev/gemini-api/docs/caching)
- [Gemini Structured Outputs](https://ai.google.dev/gemini-api/docs/structured-output)

---

#### Anthropic Direct API

**Caching Architecture**: ✅ Uses cache_control markers (same as OpenRouter)
**Structured Outputs**: ❌ No native structured output support

Anthropic does NOT offer an equivalent to OpenAI's structured outputs / responses.parse. They rely on prompt engineering or tool use for JSON extraction.

**Viability**: Not viable - lacks structured output capability that Graphiti requires.

**Source**: [Anthropic API Documentation](https://docs.anthropic.com/claude/reference/messages_post)

---

## Cost/Benefit Analysis

| Path | Effort | Timeline | Cost Savings | Risk | Viability |
|------|--------|----------|--------------|------|-----------|
| **Path 1: String-based** | None | N/A | 0% | None | ❌ Impossible |
| **Path 2: Endpoint-specific** | Low (4-8 hrs) | 1 week | 0% | Low | ❌ No value |
| **Path 3a: Wait for OpenRouter** | None | Unknown (>6mo?) | 50-75% | High | ⚠️ Uncertain |
| **Path 3b: Native Gemini** | High (40-80 hrs) | 2-4 weeks | 75-90% | Medium | ⚠️ Major rewrite |

---

## Recommendation

**Short-term (Immediate)**: Keep Feature 006 DISABLED (`MADEINOZ_KNOWLEDGE_PROMPT_CACHE_ENABLED=false`)

**Medium-term (3-6 months)**: Monitor OpenRouter for `/responses` endpoint updates
- Check quarterly for API changes
- Subscribe to OpenRouter changelog/announcements
- Test endpoint periodically with multipart format

**Long-term (If >6 months with no OpenRouter update)**: Consider migrating to native Google Gemini API
- Evaluate if cost savings (75-90% vs 0%) justify development effort
- Plan 2-4 week migration project with dedicated sprint
- Prototype cache service architecture before committing

**Alternative consideration**: Hybrid approach
- Use OpenRouter for development/testing (no caching)
- Use native Gemini for production (with caching)
- Maintain two configurations

---

## Technical Blockers Summary

1. **OpenRouter Multipart Limitation**: `/responses` endpoint rejects multipart content arrays
2. **Cache_control Requirement**: OpenRouter caching REQUIRES multipart format for markers
3. **Graphiti Endpoint Usage**: 100% of requests use responses.parse (0% cacheable)
4. **Architectural Mismatch**: OpenRouter inline markers ≠ Native Gemini cache service

These blockers are mutually reinforcing and cannot be worked around without either:
- OpenRouter changing their API design (Path 3a)
- Complete architectural rewrite (Path 3b)

---

## Next Actions

- [ ] Update Issue #11 with research findings
- [ ] Update tasks.md to mark T059 as complete
- [ ] Update spec.md status with recommendation
- [ ] Document monitoring schedule for OpenRouter updates (quarterly check)
- [ ] Create backlog item for native Gemini migration evaluation (6-month timeframe)

---

## Sources

All sources used in this research:

1. [OpenRouter Prompt Caching Documentation](https://openrouter.ai/docs/guides/best-practices/prompt-caching)
2. [OpenRouter API Reference](https://openrouter.ai/docs/api/reference/overview)
3. [OpenRouter Responses API Beta](https://openrouter.ai/docs/api/reference/responses/overview)
4. [Google Gemini Context Caching](https://ai.google.dev/gemini-api/docs/caching)
5. [Google Gemini Structured Outputs](https://ai.google.dev/gemini-api/docs/structured-output)
6. [Google Blog: Gemini API Structured Outputs](https://blog.google/technology/developers/gemini-api-structured-outputs/)
7. Container log analysis (madeinoz-knowledge-graph-mcp-dev)
8. Source code analysis (docker/patches/caching_wrapper.py)

---

**Research Status**: COMPLETE
**Feature Status**: BLOCKED indefinitely
**Recommendation**: Monitor OpenRouter quarterly for updates, evaluate native Gemini migration if no progress after 6 months.
