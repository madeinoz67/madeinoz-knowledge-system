---
title: Madeinoz Knowledge System
description: Persistent personal knowledge management system powered by Graphiti knowledge graph with FalkorDB or Neo4j backend
---

# Madeinoz Knowledge System

<p align="center"><img src="assets/logo.png" alt="Madeinoz Knowledge System" width="200"></p>

> Persistent personal knowledge management system powered by Graphiti knowledge graph - automatically extracts entities, relationships, and temporal context from conversations, documents, and ideas.

## What It Does

The Madeinoz Knowledge System transforms your AI conversations into a permanent, searchable knowledge base:

- **Automatically Learns**: Extracts entities and relationships as you work
- **Connects Concepts**: Maps how ideas relate over time
- **Semantic Search**: Finds relevant knowledge using natural language
- **Builds Context**: Compounds knowledge across sessions
- **Never Forgets**: Persistent storage with temporal tracking

**Core principle**: Work normally, knowledge handles itself.

## Quick Start

New to the system? Follow this path:

1. **[Overview](getting-started/overview.md)** - What the system does and your first steps (5 min)
2. **[Installation Guide](installation/index.md)** - Step-by-step setup instructions (15 min)
3. **[Basic Usage](usage/basic-usage.md)** - How to capture and search knowledge (10 min)
4. **[Quick Reference](getting-started/quick-reference.md)** - Commands at a glance

**Total time to get started: 30 minutes**

## Documentation Sections

### Getting Started

Start here if you're new:

- **[Overview](getting-started/overview.md)** - What the system does and quick start
- **[Quick Reference](getting-started/quick-reference.md)** - Commands and natural language triggers

### Installation

Set up the system:

- **[Installation Guide](installation/index.md)** - Complete setup instructions
- **[Requirements](installation/requirements.md)** - Prerequisites and dependencies
- **[Verification](installation/verification.md)** - Confirm everything works

### Usage

Learn how to use the system:

- **[Basic Usage](usage/basic-usage.md)** - Capturing and searching knowledge
- **[Advanced Usage](usage/advanced.md)** - Bulk import, backup, multiple graphs

### Concepts

Understand how it works:

- **[Architecture](concepts/architecture.md)** - System design and components
- **[Knowledge Graph](concepts/knowledge-graph.md)** - Episodes, entities, facts explained

### Troubleshooting

Fix common issues:

- **[Common Issues](troubleshooting/common-issues.md)** - Solutions to frequent problems

### Reference

Detailed specifications:

- **[CLI Reference](reference/cli.md)** - Command-line interface
- **[Configuration](reference/configuration.md)** - Environment variables and settings
- **[Model Guide](reference/model-guide.md)** - Ollama and LLM configuration
- **[Benchmarks](reference/benchmarks.md)** - Model performance comparisons

## Natural Language Commands

The system responds to natural conversation:

| Say This | System Does |
|----------|-------------|
| "Remember that..." | Captures knowledge with entity extraction |
| "What do I know about X?" | Searches knowledge base semantically |
| "How are X and Y related?" | Finds relationships between concepts |
| "What did I learn today?" | **Temporal search** - filter by date |
| "What did I learn recently?" | Shows recent knowledge additions |
| "Knowledge status" | Displays system health and statistics |

## Database Backends

Two graph database options:

| Backend | Best For | Web UI |
|---------|----------|--------|
| **Neo4j** (default) | CTI/OSINT data, rich queries | [localhost:7474](http://localhost:7474) |
| **FalkorDB** | Simple setup, lower resources | [localhost:3000](http://localhost:3000) |

## Common Commands

### Server Management

```bash
# Check status
bun run status

# Start server
bun run start

# Stop server
bun run stop

# View logs
bun run logs
```

### Memory Sync

```bash
# Manual sync (from installed location)
bun run ~/.claude/hooks/sync-memory-to-knowledge.ts

# Dry run (see what would sync)
bun run ~/.claude/hooks/sync-memory-to-knowledge.ts --dry-run
```

## Need Help?

1. Check the [Troubleshooting Guide](troubleshooting/common-issues.md)
2. Review [Key Concepts](concepts/knowledge-graph.md)
3. Look for examples in the [Usage Guide](usage/basic-usage.md)

## Credits

- **Knowledge graph engine**: [Graphiti](https://github.com/getzep/graphiti) by Zep AI
- **Graph databases**: [Neo4j](https://neo4j.com/) and [FalkorDB](https://www.falkordb.com/)
- **Part of**: [Personal AI Infrastructure (PAI)](https://github.com/danielmiessler/PAI)
