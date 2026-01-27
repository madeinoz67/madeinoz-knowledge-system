# Feature Specification: Gemini Prompt Caching with Cost Reporting

**Feature Branch**: `006-gemini-prompt-caching`
**Created**: 2026-01-27
**Status**: Ready for Testing (Solution Implemented)
**Input**: User description: "I want to use the recent research on prompt caching to implement in the Docker image for gemini, as well as reporting, OpenAI includes costs and cache savings in their response"

**RESOLUTION (2026-01-27)**: Implemented client routing solution. Gemini models on OpenRouter now use `OpenAIGenericClient` which routes requests through `/chat/completions` endpoint instead of `/responses`. The `/chat/completions` endpoint supports both multipart format (for `cache_control` markers) AND `json_schema` response format (for structured outputs). This enables full prompt caching functionality for Gemini models.

**Implementation Details**:
- Modified `factories.py` to detect Gemini models on OpenRouter
- Route Gemini → `OpenAIGenericClient` (uses `/chat/completions`)
- Route other models → `OpenAIClient` (uses `/responses`)
- Caching disabled by default (`MADEINOZ_KNOWLEDGE_PROMPT_CACHE_ENABLED=false`)
- Enable with `MADEINOZ_KNOWLEDGE_PROMPT_CACHE_ENABLED=true`

**Previous Status**: Blocked due to OpenRouter `/responses` endpoint incompatibility with multipart format. See `resolution-research.md` for the investigation that led to this solution.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Prompt Caching (Priority: P1)

Users running Graphiti with Gemini models benefit from automatic prompt caching without any configuration changes. The system intelligently caches common prompt prefixes (system prompts, context, few-shot examples) to reduce API costs and improve response times.

**Why this priority**: Core functionality that delivers immediate cost savings. This is the foundation that enables all other caching benefits.

**Independent Test**: Can be fully tested by making repeated requests with the same system prompt and measuring token usage reduction and delivers verifiable cost savings through API billing.

**Acceptance Scenarios**:

1. **Given** a fresh Graphiti instance with Gemini configured, **When** the same knowledge query is executed twice, **Then** the second request uses cached prompt tokens and costs less
2. **Given** multiple knowledge operations with identical system prompts, **When** operations are executed sequentially, **Then** cache hits occur and total token usage decreases
3. **Given** a cached prompt that has expired (TTL exceeded), **When** a new request is made, **Then** the cache is refreshed and new cache TTL starts

---

### User Story 2 - Cost and Cache Metrics Reporting (Priority: P2)

Users receive detailed caching metrics in every API response, showing cache hit rates, tokens saved, and cost reductions. This transparency allows users to understand and optimize their caching effectiveness.

**Why this priority**: Enables users to see the value they're getting from caching and make informed decisions about usage patterns. Similar to OpenAI's current reporting.

**Independent Test**: Can be tested by inspecting response metadata after any Gemini API call and delivers visible cost transparency.

**Acceptance Scenarios**:

1. **Given** a knowledge search operation with cache hit, **When** the response is returned, **Then** metadata includes cache_hit=true, tokens_saved, cost_saved, and cache_hit_rate
2. **Given** a knowledge operation with cache miss, **When** the response is returned, **Then** metadata includes cache_hit=false and total_cost
3. **Given** multiple operations in a session, **When** viewing cumulative metrics, **Then** session-level statistics show total savings and overall hit rate

---

### User Story 3 - Cache Performance Monitoring (Priority: P3)

System administrators can monitor cache effectiveness through Prometheus/OpenTelemetry metrics and logs, enabling optimization of cache configuration and identification of caching inefficiencies using standard observability tooling.

**Why this priority**: Valuable for optimization but not required for basic functionality. Most users will benefit from P1 and P2 first. Prometheus metrics enable integration with existing monitoring infrastructure.

**Independent Test**: Can be tested by scraping the Prometheus metrics endpoint and examining logs. Delivers actionable insights for cache tuning via standard observability tools.

**Acceptance Scenarios**:

1. **Given** the MCP server is running, **When** the /metrics endpoint is scraped, **Then** cache statistics (hit rate, tokens saved, cost saved) are exposed in Prometheus format
2. **Given** cache configuration changes, **When** monitoring metrics over time via Grafana or similar, **Then** impact on hit rates and costs is visible as time-series data
3. **Given** a cache eviction occurs, **When** reviewing logs, **Then** eviction reason and affected prompts are logged

---

### Edge Cases

- What happens when cache storage is full and new prompts arrive? (LRU eviction with logged warnings)
- How does the system handle prompts that exceed maximum cacheable size? (Fall back to uncached operation, log oversized prompts)
- What occurs if Gemini API changes caching behavior or pricing? (Graceful degradation, metric reporting continues with updated calculations)
- How does caching interact with concurrent requests using identical prompts? (Deduplicate requests, share cache entries)
- What happens when network issues prevent cache metadata retrieval? (Continue with operation, omit cache metrics from response, log error)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support Gemini's context caching API for eligible models (Gemini 1.5 Pro, Gemini 1.5 Flash)
- **FR-002**: System MUST automatically identify cacheable prompt components (system prompts, context, few-shot examples)
- **FR-003**: System MUST track cache hits and misses for each API request
- **FR-004**: System MUST calculate token savings as (total_tokens - cached_tokens)
- **FR-005**: System MUST calculate cost savings based on Gemini's caching pricing model (cached tokens cost less than input tokens)
- **FR-006**: System MUST include cache metrics in response metadata with fields: cache_hit (boolean), cached_tokens (integer), prompt_tokens (integer), tokens_saved (integer), cost_saved (float), total_cost (float)
- **FR-007**: System MUST respect Gemini's cache TTL limits (minimum 60 seconds, maximum 3600 seconds)
- **FR-008**: System MUST expose cache statistics via Prometheus metrics endpoint (/metrics)
- **FR-009**: System MUST log cache performance metrics for monitoring and debugging
- **FR-010**: System MUST handle cache misses gracefully without impacting response quality
- **FR-011**: System MUST support configurable cache TTL via environment variables
- **FR-012**: System MUST implement cache size limits to prevent unbounded memory growth
- **FR-013**: System MUST use LRU (Least Recently Used) eviction when cache is full
- **FR-014**: Docker image MUST include necessary dependencies for Gemini caching SDK
- **FR-015**: System MUST validate Gemini API responses for caching support before enabling feature

### Key Entities

- **CacheMetrics**: Represents caching performance data including cache_hit (boolean), cached_tokens (count of tokens served from cache), prompt_tokens (total input tokens), completion_tokens (output tokens), tokens_saved (cached_tokens count), cost_saved (monetary savings from caching), total_cost (final API cost), cache_hit_rate (percentage, session-level)

- **CacheConfiguration**: Represents cache behavior settings including ttl_seconds (cache entry lifetime), max_cache_size_mb (memory limit), eviction_policy (LRU), enabled_models (list of Gemini models with caching support), min_prompt_tokens (minimum token count for cacheable prompts)

- **CacheEntry**: Represents a cached prompt component including prompt_hash (unique identifier), cached_content (prompt prefix), created_at (timestamp), last_accessed (timestamp), access_count (usage frequency), token_count (size in tokens)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Knowledge operations with repeated system prompts show 40%+ token cost reduction on cache hits
- **SC-002**: Cache hit rate reaches 60%+ within 100 operations for typical usage patterns
- **SC-003**: Response metadata includes complete caching metrics (8 fields) in 100% of Gemini API responses
- **SC-004**: Average response time for cached requests is 25%+ faster than uncached requests
- **SC-005**: Cache overhead adds less than 50ms latency to uncached requests
- **SC-006**: Prometheus metrics endpoint exposes cache statistics for standard scraping
- **SC-007**: Users can verify cost savings by comparing total_cost with and without caching enabled
- **SC-008**: System handles 1000+ cached entries without memory exhaustion or degraded performance

## Assumptions

- Gemini API continues to support context caching as documented in current SDK
- Prompt caching pricing remains stable (cached tokens cost less than standard input tokens)
- System prompts and knowledge graph context represent majority of cacheable content
- Users prefer automatic caching over manual configuration
- Cache TTL of 300-600 seconds balances freshness and hit rate for typical workflows
- Docker image size increase (5-10MB for SDK dependencies) is acceptable
- Memory allocation for cache (default 100MB) fits within container resource limits
- Standard Gemini pricing model: input tokens > cached tokens > output tokens in cost per token

## Scope

### In Scope

- Gemini 1.5 Pro and Gemini 1.5 Flash model support
- Automatic prompt caching for system prompts and context
- Response metadata with cache metrics
- Health endpoint cache statistics
- Environment-based cache configuration
- Docker image updates with caching dependencies
- Cache eviction policies (LRU)
- Cost calculation logic for Gemini pricing
- Cache TTL management

### Out of Scope

- Caching for non-Gemini LLM providers (OpenAI, Anthropic, etc.) - future enhancement
- User-controlled cache invalidation API - not needed for MVP
- Persistent cache storage across container restarts - in-memory is sufficient
- Fine-grained cache key customization - automatic detection is sufficient
- Cache warming/pre-loading - reactive caching is adequate
- Multi-node cache synchronization - single instance only
- Gemini models without caching support (earlier versions)

## Dependencies

- Gemini SDK with context caching support (google-generativeai >= 0.3.0 or equivalent)
- Docker base image with Python 3.10+
- Graphiti's existing LLM provider abstraction layer
- Environment variable configuration system
- OpenTelemetry SDK with Prometheus exporter (opentelemetry-api, opentelemetry-sdk, opentelemetry-exporter-prometheus)

## Risks and Mitigations

**Risk**: Gemini API changes caching behavior or pricing structure
**Mitigation**: Version-lock SDK, implement feature flags to disable caching if needed, monitor API changelog

**Risk**: Cache causes stale responses when context should update
**Mitigation**: Conservative TTL defaults (5-10 minutes), clear cache on critical operations

**Risk**: Memory exhaustion from unbounded cache growth
**Mitigation**: Implement strict size limits, LRU eviction, monitoring alerts on cache size

**Risk**: Caching metrics add response payload bloat
**Mitigation**: Keep metrics minimal (8 fields), make detailed stats opt-in via query parameter

**Risk**: Cache implementation complexity delays feature delivery
**Mitigation**: Use Gemini SDK's built-in caching rather than custom implementation, start with simple automatic mode
