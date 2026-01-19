---
title: Known Issues
description: Documented known issues with the Madeinoz Knowledge System and their workarounds
---

# Known Issues

This page documents known issues with the Madeinoz Knowledge System, including their root causes and implemented workarounds. These are issues we're aware of that have solutions in place but may affect your usage or require understanding.

---

## Lucene Query Sanitization

The knowledge system includes automatic query sanitization to handle special characters in search terms. This is particularly important for CTI/OSINT data with hyphenated identifiers.

### The Problem

FalkorDB uses RediSearch, which implements Lucene query syntax. In Lucene, certain characters have special meaning:

| Character | Lucene Meaning |
|-----------|----------------|
| `-` (hyphen) | Negation operator (NOT) |
| `"` (quotes) | Phrase query delimiters |
| `*`, `?` | Wildcards for pattern matching |
| `+` | Required term operator |
| `&&`, `\|\|` | Boolean operators |

!!! warning "Query Interpretation Issue"
    When searching for hyphenated group_ids like `madeinoz-threat-intel`, Lucene interprets this as:

    ```
    madeinoz AND NOT threat AND NOT intel
    ```

    This causes query syntax errors because the negation operators are incomplete.

### The Solution

A centralized sanitization module automatically escapes special characters before queries reach FalkorDB.

**Location:** `src/server/lib/lucene.ts`

### Sanitization Functions

| Function | Purpose | Example Input | Example Output |
|----------|---------|---------------|----------------|
| `luceneSanitize(value)` | Escape a value by wrapping in quotes and escaping special characters | `madeinoz-threat-intel` | `"madeinoz-threat-intel"` |
| `sanitizeGroupId(groupId)` | Convenience function for sanitizing group_ids | `madeinoz-threat-intel` | `"madeinoz-threat-intel"` |
| `sanitizeGroupIds(groupIds)` | Sanitize an array of group_ids | `["group-1", "group-2"]` | `["group-1", "group-2"]` |
| `sanitizeSearchQuery(query)` | Escape special characters while preserving multi-word searches | `apt-28 threat` | `apt\-28 threat` |

### Characters That Get Escaped

The following Lucene special characters are automatically escaped:

```
+ - && || ! ( ) { } [ ] ^ " ~ * ? : \ /
```

### Root Cause Analysis

=== "Unsanitized Query"

    ```
    Query: group_id:madeinoz-threat-intel
    Lucene interprets: group_id:madeinoz AND NOT threat AND NOT intel
    Result: Syntax error (incomplete negation)
    ```

=== "Sanitized Query"

    ```
    Query: group_id:"madeinoz-threat-intel"
    Lucene interprets: group_id equals literal string "madeinoz-threat-intel"
    Result: Successful search
    ```

### Impact on Users

!!! success "Automatic Handling"
    This sanitization happens automatically in all server operations and hooks. You don't need to manually escape your queries - the system handles it for you.

If you're experiencing unexpected search behavior with hyphenated terms or special characters, the sanitization should already be handling it. If issues persist, please check:

1. You're using the latest version of the knowledge system
2. The `lucene.ts` module is present in `src/server/lib/`
3. Your queries aren't double-escaping characters

!!! tip "Recommendation: Use Neo4j Backend"
    The Neo4j database backend does **not** have this Lucene query syntax issue. Neo4j uses Cypher queries which handle special characters natively without requiring sanitization. If you frequently work with hyphenated identifiers (CTI/OSINT data, kebab-case naming), consider using the Neo4j backend instead of FalkorDB.

    To switch backends, update your configuration:
    ```bash
    MADEINOZ_KNOWLEDGE_BACKEND=neo4j
    ```

    See the [Configuration Reference](../reference/configuration.md) for details.

!!! info "Upstream Tracking"
    This sanitization is a local workaround for FalkorDB users. For upstream improvements to Graphiti's query handling, see the [Graphiti GitHub Issues](https://github.com/getzep/graphiti/issues) page. Relevant issues include query escaping, special character handling, and FalkorDB/RediSearch compatibility.

---

## Pydantic Validation Errors with OpenAI-Compatible APIs

When using OpenAI-compatible API providers (OpenRouter, Together AI, Fireworks, etc.), users may encounter intermittent Pydantic validation errors during entity extraction and relationship mapping.

### The Problem

Graphiti uses structured output (JSON schema validation) to ensure LLM responses conform to expected data types. Different LLM clients have different levels of structured output support:

| Client Type | Structured Output Method | Reliability |
|-------------|--------------------------|-------------|
| `OpenAIClient` | Parse API with strict schema enforcement | High |
| `OpenAIGenericClient` | Basic `json_object` mode | Variable |

!!! warning "EdgeDuplicate Validation Errors"
    When using the wrong client type for cloud providers, you may see errors like:

    ```
    pydantic.ValidationError: EdgeDuplicate validation failed
    ```

    These occur because the basic `json_object` mode doesn't enforce the strict schema that Graphiti expects, leading to malformed responses that fail Pydantic validation.

### The Solution

A patched factory module automatically selects the appropriate client based on the endpoint type.

**Location:** `src/server/patches/factories.py`

### Client Selection Logic

| Endpoint Type | Client Used | Reason |
|---------------|-------------|--------|
| OpenAI Direct (`api.openai.com`) | `OpenAIClient` | Native support |
| Cloud Providers (OpenRouter, Together, etc.) | `OpenAIClient` | Parse API support via proxy |
| Local Endpoints (Ollama, localhost) | `OpenAIGenericClient` | No parse API available |

### Root Cause Analysis

=== "Before Patch"

    ```
    All custom endpoints → OpenAIGenericClient
    Cloud providers like OpenRouter use basic json_object mode
    Result: Intermittent Pydantic validation failures
    ```

=== "After Patch (v3)"

    ```
    Cloud providers → OpenAIClient (strict schema via parse API)
    Local endpoints → OpenAIGenericClient (json_object mode)
    Result: Reliable structured output for cloud providers
    ```

### Impact on Users

!!! success "Automatic Handling"
    This client selection happens automatically in the patched factory module. If you're using OpenRouter, Together AI, or other cloud providers, the system automatically uses the appropriate client with strict schema enforcement.

If you're experiencing validation errors:

1. Ensure you're using the patched `factories.py` from this knowledge system
2. Check that your endpoint URL is correctly classified (cloud vs local)
3. For local LLMs (Ollama), validation errors may still occur as they don't support the parse API

!!! tip "Recommended Cloud Providers"
    The following providers have been tested and work reliably with the patched client selection:

    - **OpenRouter** (`openrouter.ai`) - Excellent structured output support
    - **Together AI** (`api.together.xyz`) - Good structured output support
    - **Fireworks AI** (`api.fireworks.ai`) - Good structured output support

!!! info "Upstream Tracking"
    This issue is tracked in the Graphiti repository:

    - [Issue #912](https://github.com/getzep/graphiti/issues/912) - EdgeDuplicate Pydantic validation errors
    - [Issue #1116](https://github.com/getzep/graphiti/issues/1116) - MCP server ignores api_base/base_url configuration

---

## Reporting New Issues

If you encounter an issue not documented here, please:

1. Check the [Common Issues](common-issues.md) page for troubleshooting steps
2. Search existing [GitHub Issues](https://github.com/madeinoz67/madeinoz-knowledge-system/issues)
3. If it's a new issue, open a GitHub issue with:
    - Steps to reproduce
    - Expected vs actual behavior
    - System information (OS, container runtime, versions)
