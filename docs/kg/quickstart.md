---
title: "Knowledge Memory Quickstart"
description: "Quick start guide for Knowledge Memory using Graphiti knowledge graph"
---

<!-- AI-FRIENDLY SUMMARY
System: Knowledge Memory (KG) - Graphiti Knowledge Graph
Purpose: Durable knowledge storage with entity extraction and relationships
Component: Part 2 of LKAP Two-Tier Memory Model

Core Workflow:
1. Add episodes via add_memory MCP tool
2. Search entities with search_memory_nodes
3. Find relationships with search_memory_facts
4. Promote facts from RAG evidence

MCP Tools:
- add_memory(name, body, group_id) - Store episode
- search_memory_nodes(query, group_id) - Entity search
- search_memory_facts(query, group_id) - Relationship search
- get_episodes(group_id, limit) - Recent episodes
- delete_episode(uuid) - Remove episode
- clear_graph(group_id) - Clear group

Configuration Prefix: MADEINOZ_KNOWLEDGE_*
-->

# Knowledge Memory Quickstart

**Knowledge Memory** - Durable, typed facts with provenance using Graphiti knowledge graph.

## Quick Reference Card

| Task | Command/Action |
|------|----------------|
| **Start Neo4j** | `bun run server-cli start` |
| **Add knowledge** | `add_memory(name="Topic", body="content")` |
| **Search entities** | `search_memory_nodes(query="topic")` |
| **Find relationships** | `search_memory_facts(query="X and Y")` |
| **Get recent episodes** | `get_episodes(limit=10)` |
| **Check status** | `bun run server-cli status` |

## Architecture

Knowledge Memory is **Tier 2** of the LKAP two-tier model:

| Aspect | Knowledge Memory |
|--------|-----------------|
| **Technology** | Graphiti/Neo4j |
| **Storage** | Entities + Relationships |
| **Volume** | Low (curated facts) |
| **Persistence** | Durable |
| **Query Type** | Graph traversal |

➡️ **[Knowledge Memory Concepts](concepts.md)** - Learn how knowledge graphs work

## Getting Started

### 1. Start Services

```bash
# Start Neo4j (and MCP server)
bun run server-cli start

# Verify services are running
bun run server-cli status
```

### 2. Add Knowledge

Use the MCP tools to add episodes:

```python
# Add a knowledge episode
add_memory(
    name="SPI Configuration",
    body="SPI1 on STM32F4 has a maximum clock frequency of 42MHz. "
         "This is derived from the APB2 clock (84MHz) divided by 2.",
    group_id="main"
)
```

After adding, the system:
- Extracts entities using LLM (GPT-4o-mini)
- Identifies relationships between entities
- Creates embeddings for semantic search
- Stores everything in Neo4j

### 3. Search Knowledge

```python
# Search for entities
search_memory_nodes(
    query="SPI clock frequency",
    group_id="main"
)

# Search for relationships
search_memory_facts(
    query="SPI and APB clock relationship",
    group_id="main"
)
```

### 4. Get Recent Episodes

```python
# Get recent knowledge captures
get_episodes(
    group_id="main",
    limit=10
)
```

## MCP Tools

### add_memory(name, body, group_id)

Store a knowledge episode.

```python
add_memory(
    name="GPIO Configuration",
    body="GPIO pins on STM32 can be configured as input, output, "
         "analog, or alternate function. Each pin has a 32-bit "
         "configuration register.",
    group_id="main"
)
```

**Returns**:
- Episode UUID
- Entity count extracted
- Relationship count

### search_memory_nodes(query, group_id)

Search for entities by meaning.

```python
search_memory_nodes(
    query="container tools",
    group_id="main"
)
```

**Returns**:
- Entity names and types
- Similarity scores
- Related facts

### search_memory_facts(query, group_id)

Search for relationships between entities.

```python
search_memory_facts(
    query="Podman Docker comparison",
    group_id="main"
)
```

**Returns**:
- Facts (relationships)
- Source episode references
- Temporal context

### get_episodes(group_id, limit)

Retrieve recent knowledge captures.

```python
get_episodes(
    group_id="main",
    limit=20
)
```

**Returns**:
- Episode UUIDs
- Names and timestamps
- Content summary

### delete_episode(uuid)

Remove an episode and its extracted knowledge.

```python
delete_episode(uuid="abc123-def456")
```

### clear_graph(group_id)

Clear all knowledge in a group.

```python
clear_graph(group_id="test")  # Use with caution!
```

## Promotion from RAG

Promote facts from Document Memory to Knowledge Memory:

### Promote from Evidence

```python
# Search RAG first
results = rag.search("maximum SPI frequency")

# Promote specific chunk
kg.promoteFromEvidence(
    evidence_id="chunk-abc123",
    fact_type="Constraint",
    value="SPI1 max frequency is 42MHz"
)
```

### Promote from Query

```python
# Search and promote in one step
kg.promoteFromQuery(
    query="GPIO configuration constraints",
    fact_type="Constraint"
)
```

➡️ **[Promotion Workflow](../lkap/promotion-workflow.md)** - Full promotion guide

## Fact Types

When promoting from RAG, facts are typed:

| Type | Description | Example |
|------|-------------|---------|
| `Constraint` | System limits | "max clock is 120MHz" |
| `Erratum` | Known issues | "FIFO corrupts at 80MHz" |
| `API` | Function signatures | `gpio_init(port, pin)` |
| `Workaround` | Solutions | "Use DMA instead" |
| `BuildFlag` | Compiler options | `-DUSE_FIFO=0` |

## CLI Reference

```bash
# Server management
bun run server-cli start      # Start containers
bun run server-cli stop       # Stop containers
bun run server-cli status     # Check status
bun run server-cli logs       # View logs

# Knowledge operations (via MCP tools)
# Use add_memory, search_memory_nodes, etc.
```

## Groups

Organize knowledge into separate namespaces:

| Group | Purpose |
|-------|---------|
| `main` | Default knowledge |
| `work` | Professional knowledge |
| `personal` | Life organization |
| `research` | Academic/exploratory |

Groups are isolated - no cross-group queries.

## Next Steps

- **[Knowledge Memory Concepts](concepts.md)** - Understand knowledge graphs
- **[KG Configuration](configuration.md)** - Configure Neo4j and LLM
- **[KG Troubleshooting](troubleshooting.md)** - Solve common issues
- **[Promotion Workflow](../lkap/promotion-workflow.md)** - Promote from RAG
- **[Document Memory (RAG)](../rag/quickstart.md)** - Document search
