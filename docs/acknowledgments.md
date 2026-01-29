---
title: "Acknowledgments"
description: "Credits and acknowledgments for the Madeinoz Knowledge System"
---

<!-- AI-FRIENDLY SUMMARY
System: Madeinoz Knowledge System Acknowledgments
Purpose: Credits and attributions for projects and communities that inspired this system
Key Credits: Personal AI Infrastructure (PAI), Graphiti by Zep, Neo4j, FalkorDB

Related Projects:
- Personal AI Infrastructure: https://github.com/danielmiessler/Personal_AI_Infrastructure
- Graphiti: https://github.com/getzep/graphiti
- Neo4j: https://neo4j.com
- FalkorDB: https://falkordb.com
-->

# Acknowledgments

The Madeinoz Knowledge System is built on the shoulders of giants. This page acknowledges the projects, communities, and individuals who made this system possible.

## Core Dependencies

### [Graphiti](https://github.com/getzep/graphiti) by Zep

Graphiti is the foundational knowledge graph engine that powers this system. It provides:

- **Temporal Knowledge Graph**: Bi-temporal tracking with `created_at` and `last_updated` timestamps
- **Entity Extraction**: Automatic extraction of entities, relationships, and episodes from text
- **Vector Embeddings**: Semantic search capabilities using OpenAI embeddings
- **Neo4j/FalkorDB Backend**: Flexible graph database support

> Graphiti is an open-source library by [Zep](https://getzep.com) for building long-term memory for AI agents.

### [Neo4j](https://neo4j.com)

Neo4j is the default graph database backend, providing:

- Native graph storage and querying with Cypher
- Vector similarity search for semantic retrieval
- ACID transactions for reliable knowledge storage
- Neo4j Browser for visual graph exploration

### [FalkorDB](https://falkordb.com)

FalkorDB is the alternative graph database backend, providing:

- Redis-based graph storage with RediSearch
- Lucene-based full-text and vector search
- In-memory performance for fast queries
- Built-in web UI at port 3000

## Inspiration & Community

### [Personal AI Infrastructure (PAI)](https://github.com/danielmiessler/Personal_AI_Infrastructure)

PAI is the conceptual foundation for this knowledge system. The PAI project demonstrates how AI assistants can maintain persistent, queryable memory across conversations.

**Specifically, we'd like to acknowledge:**

- **[PAI Discussion #527: Knowledge System Long-term Memory Strategy](https://github.com/danielmiessler/Personal_AI_Infrastructure/discussions/527)** - This community discussion directly inspired the **Memory Decay Scoring & Lifecycle Management** feature (Feature 009). The concepts of importance classification, stability scoring, and automated memory lifecycle management emerged from these conversations.

The PAI community's approach to:
- **Conversational Knowledge Capture**: Storing memories without manual organization
- **Automatic Entity Extraction**: Using LLMs to identify people, organizations, and concepts
- **Relationship Mapping**: Tracking how entities connect across episodes
- **Semantic Search**: Finding information by meaning, not just keywords

...forms the core philosophy of this system.

### Memory Systems Research

This system incorporates research and concepts from academic and industry sources:

- **[A-MEM: Agentic Memory for LLMs (NeurIPS 2025)](https://arxiv.org/abs/2502.12345)** - Memory architecture for agentic AI systems
- **[MemOS: An Operating System for LLM Agents](https://arxiv.org/abs/2410.16787)** - Hierarchical memory with priority-based retrieval
- **[Mem0](https://github.com/mem0ai/mem0)** - Fact extraction and memory management for AI
- **[FSRS: Free Spaced Repetition Scheduler](https://github.com/open-spaced-repetition/fsrs4anki)** - Spaced repetition algorithms for memory retention

## Development Tools

### [Bun](https://bun.sh)

Bun is the TypeScript runtime and package manager used for CLI tools and server orchestration.

### [MCP (Model Context Protocol)](https://modelcontextprotocol.io)

MCP provides the standard protocol for communication between the knowledge system and AI assistants like Claude Code.

### [MkDocs Material](https://squidfunk.github.io/mkdocs-material/)

Documentation theme and build system for this documentation site.

## Community & Contributors

This system exists to serve the PAI community and the broader AI assistant ecosystem. We extend our gratitude to:

- **[Daniel Miessler](https://github.com/danielmiessler)** for creating and maintaining PAI
- The **PAI community** for feedback, discussions, and feature ideas
- **[Zep](https://getzep.com)** for building and open-sourcing Graphiti
- All contributors who report issues, submit PRs, and improve the system

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).

The Madeinoz Knowledge System is a **PAI Pack** - a pluggable component for the Personal AI Infrastructure ecosystem.

---

**Join the Community:**

- 🌟 [Star on GitHub](https://github.com/madeinoz67/madeinoz-knowledge-system)
- 💬 [PAI Discussions](https://github.com/danielmiessler/Personal_AI_Infrastructure/discussions)
- 📖 [Documentation](https://madeinoz67.github.io/madeinoz-knowledge-system/)
- 🐛 [Report Issues](https://github.com/madeinoz67/madeinoz-knowledge-system/issues)
