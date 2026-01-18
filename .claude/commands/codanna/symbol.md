---
description: Looks up a symbol by name. Returns its location, signature, line range, documentation, calls, callers, implementations, and definitions.
argument-hint: <symbol-name> "<question>"
---

## Context

Symbol to analyze: **$1**

User's question: **$2**

## Your task

Use the Bash tool to fetch symbol information, then answer the user's question.

**Workflow:**
1. Execute: `node .claude/scripts/codanna/context-provider.js symbol $1`
2. Analyze the symbol details returned (includes `[symbol_id:123]` for all symbols)
3. For deeper exploration, the script supports: `describe`, `callers`, `calls` subcommands
4. Trust the script output. If it's not enough, ask the user.
5. Answer the question: "$2"

> The meta-principle is: "When given a workflow, follow it. Uncertainty is a signal to verify, not improvise."

When answering:
- Reference actual code locations (file:line_range)
- Explain relationships (calls, called_by, implements, defines)
- Use the signature and documentation from the symbol
- Be specific about how the symbol is used in the codebase

**Following relationships:**
- Use `<symbol_name|symbol_id:ID>` for follow-up queries
- Commands: `calls`, `callers`, `describe` accept either format

Focus on what the code actually shows, not general programming principles.

## Graph Visualization

When the symbol has rich relationships, suggest:
> "This symbol has N callers/calls. Would you like a graph visualization?"

If the user explicitly asks for a graph, or accepts the suggestion:
1. Execute: `node .claude/scripts/codanna/visualize-graph.js <symbol_id:ID> [depth]`
2. Default depth is 2 (shows immediate + one level of transitive relationships)
3. The script generates an HTML file and outputs the path
4. Tell the user the file location so they can open it in their browser

**When to suggest graphs:**
- Many relationships where text output is hard to follow
- User asks "how is this connected" or "show me the relationships"
- User wants to understand call flow or dependency topology

**Do NOT suggest graphs for:**
- Simple symbols with 0-2 relationships
- When user is asking about implementation details, not relationships
