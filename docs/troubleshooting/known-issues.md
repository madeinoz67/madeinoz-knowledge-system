---
title: Known Issues
description: Documented known issues with the Madeinoz Knowledge System and their workarounds
---

# Known Issues

This page documents known issues with the Madeinoz Knowledge System, including their root causes and implemented workarounds. These are issues we're aware of that have solutions in place but may affect your usage or require understanding.

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

The Docker container includes a patched factory module applied at image build time that automatically selects the appropriate client based on the endpoint type.

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
