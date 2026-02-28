---
title: "Getting Started Overview"
description: "Introduction to the Madeinoz Knowledge System and how to use your personal AI memory"
---

# Knowledge System - User Guide

Welcome to the Madeinoz Knowledge System! This guide will help you understand and use your personal knowledge management system with LKAP two-tier memory.

!!! info "PAI Pack"
    This is a **[PAI (Personal AI Infrastructure)](https://github.com/danielmiessler/PAI)** Pack - a modular component that adds persistent memory capabilities to your AI infrastructure. PAI Packs are self-contained modules that can be installed into any PAI-compatible system.

## LKAP Two-Tier Memory

The system uses a two-tier memory model:

| Tier | Technology | Best For |
|------|------------|----------|
| **Document Memory (RAG)** | Qdrant | Search documents, find citations, explore content |
| **Knowledge Memory (Graph)** | Graphiti/Neo4j | Verified facts, relationships, provenance |

**Key principle**: Documents are evidence. Knowledge is curated truth.

## What is the Knowledge System?

Think of the Knowledge System as your AI's memory with two complementary capabilities:

**Document Memory (RAG)** - Drop documents and search them semantically:
- Drop PDFs, markdown, text files in `knowledge/inbox/`
- Search across all documents using natural language
- Get citations showing exactly where information came from

**Knowledge Memory (Graph)** - Store and connect curated facts:
- Automatically organizes information as you add it
- Finds connections between different topics
- Lets you search using everyday language
- Keeps track of when you learned things

## What Can You Do With It?

### Document Memory (RAG)

**Search documents semantically using the CLI:**

```bash
# Drop a document in the inbox
cp datasheet.pdf knowledge/inbox/

# Ingest it (CLI method)
bun run src/skills/server/lib/rag-cli.ts ingest --all

# Search
bun run src/skills/server/lib/rag-cli.ts search "GPIO configuration"
```

**Or use MCP tools from Claude:**
```
You: "Search my documents for SPI clock settings"
[Claude calls rag_search tool automatically]
```

**Get citations with results:**
- Each result shows the source document
- Page/section references included
- Confidence scores for relevance

### Knowledge Memory (Graph)

### Store Information

Just say "remember this" and the system captures what you're talking about:

```
You: "Remember that I prefer using gpt-4o-mini for everyday tasks because it's faster and cheaper."
```

The system will automatically:

- Extract key concepts (gpt-4o-mini, preferences, cost optimization)
- Note relationships (preference, reason: speed and cost)
- Store it with today's date

### Find Information

Ask questions in plain English:

```
You: "What do I know about Podman?"
```

The system searches your knowledge and shows you:

- Everything you've stored about Podman
- Related topics (Docker, containers, etc.)
- When you learned each piece of information

### Discover Connections

See how different topics relate:

```
You: "How are Graphiti and FalkorDB connected?"
```

The system traces the relationships in your knowledge graph and explains how these concepts link together.

## Using the Knowledge Skill

The Knowledge skill provides natural language triggers that route to specific workflows. Just say what you want to do:

### Natural Language Triggers

| Intent | Example Phrases | What Happens |
|--------|----------------|--------------|
| **Capture** | "remember this", "store this", "add to knowledge", "save this" | Captures episode with entity extraction |
| **Search** | "what do I know about", "search my knowledge", "find in knowledge base" | Searches entities semantically |
| **Relationships** | "how are X and Y connected", "what's the relationship", "show connections" | Traverses graph edges |
| **Recent** | "what did I learn", "recent knowledge", "latest additions" | Gets recent episodes |
| **Status** | "knowledge status", "system health", "graph stats" | Returns system health |
| **Documents** | "search documents", "find in PDFs", "RAG search" | Searches Qdrant vector DB |
| **Promote** | "promote to knowledge", "add to graph" | Promotes RAG evidence to KG |

### Workflow Routing

When you use a trigger phrase, the skill routes your request to the appropriate workflow:

```
"Remember that Podman uses daemonless architecture"
       ↓
CaptureEpisode workflow
       ↓
CLI: bun run knowledge-cli.ts add_episode "Podman Architecture" "..."
       ↓
Entity extraction → Graph storage
       ↓
Response: "✓ Captured: Podman uses daemonless architecture"
```

### CLI vs Natural Language

You can interact with the system two ways:

**Natural Language (Recommended):**
```
You: "What do I know about container orchestration?"
[Claude handles the workflow automatically]
```

**Direct CLI (For scripting/automation):**
```bash
bun run knowledge-cli.ts search_nodes "container orchestration" 10
bun run rag-cli.ts search "SPI configuration" --top-k=5
```

## Quick Start

### Before You Begin

You'll need:

1. The Madeinoz Knowledge System installed (see [installation guide](../installation/index.md))
2. The MCP server running in the background
3. An OpenAI API key (or similar service)

### Your First Knowledge Capture

Try this simple example:

```
You: "Remember that bun is faster than npm for installing packages."
```

The system responds with something like:

```
Knowledge Captured

Stored episode: Bun Performance Comparison

Entities extracted:
- Bun (Tool)
- npm (Tool)
- package installation (Procedure)

Relationships identified:
- Bun -> faster than -> npm
- Bun -> used for -> package installation
```

### Your First Search

Now try finding what you just stored:

```
You: "What do I know about bun?"
```

The system shows you:

```
Knowledge Found: Bun

Based on your knowledge graph:

Key Entities:
1. Bun (Tool)
   - Fast JavaScript runtime and package manager
   - Alternative to npm and Node.js
   - Known for faster package installation

Relationships:
- Bun -> faster than -> npm
- Bun -> used for -> package installation

Episodes:
- "Bun Performance Comparison" (today)
```

## Common Use Cases

### For Developers

**Capture technical decisions:**

```
"Remember that we chose PostgreSQL over MongoDB because we need strong consistency and complex relationships."
```

**Store configuration snippets:**

```
"Save this: my preferred VS Code settings are 2-space tabs, auto-save on focus change, and Dracula theme."
```

**Document solutions to problems:**

```
"Remember: when Podman containers can't reach the network, check if the firewall is blocking the CNI plugins."
```

### For Learning

**Capture research findings:**

```
"Store this research: Graphiti uses LLMs to automatically extract entities from text, unlike traditional knowledge graphs that require manual annotation."
```

**Track concept connections:**

```
"Remember that FalkorDB is a Redis module that adds graph database capabilities, which is why Graphiti can use it as a backend."
```

### For Personal Organization

**Save preferences:**

```
"Remember that I prefer morning meetings between 9-11 AM and need at least 30 minutes between back-to-back calls."
```

**Track decisions:**

```
"Store this decision: I'm going to use weekly reviews instead of daily standups for my solo projects."
```

## Key Concepts

### Episodes

Every time you add knowledge, the system creates an "episode." Think of episodes as diary entries - each one captures:

- What you said
- When you said it
- What entities and relationships were found

### Entities

These are the "things" in your knowledge - people, places, tools, concepts, preferences, procedures, etc. The system automatically identifies these as you add information.

Common entity types:

- **People**: Names of individuals
- **Organizations**: Companies, teams, groups
- **Locations**: Places, servers, repositories
- **Concepts**: Ideas, technologies, methodologies
- **Procedures**: How-to guides, workflows
- **Preferences**: Your choices and opinions
- **Requirements**: Features, needs, specifications

### Relationships

Relationships show how entities connect. For example:

- "Bun is faster than npm" creates a relationship
- "PostgreSQL requires strong consistency" creates another
- "I prefer morning meetings" connects you to a preference

### Groups

You can organize knowledge into separate groups (like different notebooks). By default, everything goes into the "main" group, but you can create separate groups for work, personal, research, etc.

## How It Works Behind the Scenes

When you say "remember this," here's what happens:

1. **Your words go to the system** - The PAI skill recognizes you want to store knowledge

2. **Content is sent to the MCP server** - This is the brain that processes your information

3. **An LLM extracts entities** - Using AI (like GPT-4), the system identifies important concepts in what you said

4. **Relationships are mapped** - The system figures out how these concepts relate to each other

5. **Embeddings are created** - Your knowledge is converted into vector form so it can be searched semantically (by meaning, not just keywords)

6. **Everything is stored in FalkorDB** - A graph database saves all the entities, relationships, and the original text

When you search, the system uses vector similarity to find relevant knowledge, even if you use different words than you originally used.

## Next Steps

Ready to dive deeper? Check out:

- [Installation Guide](../installation/index.md) - Set up the system step by step
- [Usage Guide](../usage/basic-usage.md) - Detailed examples and commands
- [Concepts Guide](../kg/concepts.md) - Deep dive into how the system works
- [Troubleshooting](../troubleshooting/common-issues.md) - Fix common issues

## Getting Help

If something isn't working:

1. Check if the MCP server is running: `bun run server-cli status`
2. Look at the logs: `bun run server-cli logs`
3. Read the [troubleshooting guide](../troubleshooting/common-issues.md)
4. Review the [Architecture](../concepts/architecture.md) for technical details

## Tips for Success

1. **Be specific**: Instead of "remember Docker," say "remember that Docker requires a daemon process, unlike Podman which is daemonless"

2. **Add context**: The more detail you provide, the better the entity extraction works

3. **Use it regularly**: The more knowledge you add, the more useful the system becomes

4. **Review recent additions**: Periodically check what you've stored with "show me recent knowledge"

5. **Don't worry about organization**: The system automatically organizes information - you just focus on capturing it
