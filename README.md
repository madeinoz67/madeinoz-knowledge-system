---
# name: (24 words max) Human-readable pack name
name: Madeinoz Knowledge System

# pack-id: (format) {author}-{pack-name}-{variant}-v{version}
pack-id: madeinoz67-madeinoz-knowledge-system-core-v1.2.5

# version: (format) SemVer major.minor.patch
version: 1.2.5

# author: (1 word) GitHub username or organization
author: madeinoz67

# description: (128 words max) One-line description
description: Persistent personal knowledge management system powered by Graphiti knowledge graph with FalkorDB or Neo4j backend - automatic entity extraction, relationship mapping, and semantic search for AI conversations and documents

# type: (single) concept | skill | hook | plugin | agent | mcp | workflow | template | other
type: skill

# purpose-type: (multi) security | productivity | research | development | automation | integration | creativity | analysis | other
purpose-type: [productivity, automation, development]

# platform: (single) agnostic | claude-code | opencode | cursor | custom
platform: claude-code

# dependencies: (list) Required pack-ids, empty [] if none
dependencies: []

# keywords: (24 tags max) Searchable tags for discovery
keywords: [knowledge, graph, memory, semantic search, entity extraction, relationships, graphiti, falkordb, neo4j, mcp, persistent, ai, storage, retrieval, organizational, learning, documentation]
---

<p align="center"><img src="../icons/madeinoz-knowledge-system.png" alt="Madeinoz Knowledge System" width="256"></p>

# Knowledge

> Persistent personal knowledge management system powered by Graphiti knowledge graph - automatically extracts entities, relationships, and temporal context from conversations and documents.

[![Docker Build](https://github.com/madeinoz67/madeinoz-knowledge-system/actions/workflows/docker-build.yml/badge.svg)](https://github.com/madeinoz67/madeinoz-knowledge-system/actions/workflows/docker-build.yml)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/madeinoz67/madeinoz-knowledge-system)](https://github.com/madeinoz67/madeinoz-knowledge-system/releases/latest)
[![Docker Pulls](https://img.shields.io/docker/pulls/madeinoz-knowledge-system?label=Docker%20Hub)](https://hub.docker.com/r/madeinoz-knowledge-system)
[![GitHub Container Registry](https://img.shields.io/badge/ghcr.io-madeinoz--knowledge--system-blue?logo=docker)](https://ghcr.io/madeinoz67/madeinoz-knowledge-system)

## Documentation

**[View Full Documentation](https://madeinoz67.github.io/madeinoz-knowledge-system/)** - Complete guides, architecture, and reference.

| Topic | Description |
|-------|-------------|
| [Getting Started](https://madeinoz67.github.io/madeinoz-knowledge-system/getting-started/) | Installation and quick start guide |
| [Configuration](https://madeinoz67.github.io/madeinoz-knowledge-system/reference/configuration/) | Environment variables and settings |
| [Architecture](https://madeinoz67.github.io/madeinoz-knowledge-system/reference/architecture/) | System design and components |
| [Troubleshooting](https://madeinoz67.github.io/madeinoz-knowledge-system/troubleshooting/) | Common issues and solutions |
| [Developer Notes](https://madeinoz67.github.io/madeinoz-knowledge-system/reference/developer-notes/) | Contributing and development |

## Quick Start

### 1. Pull the Docker Image

```bash
# From GitHub Container Registry (recommended)
docker pull ghcr.io/madeinoz67/madeinoz-knowledge-system:latest

# Or from Docker Hub
docker pull madeinoz-knowledge-system:latest
```

### 2. Start the Server

```bash
# Neo4j backend (default)
bun run server-cli start

# FalkorDB backend
DATABASE_TYPE=falkordb bun run server-cli start
```

### 3. Verify Installation

```bash
bun run server-cli status
```

See [INSTALL.md](INSTALL.md) for complete installation instructions and [VERIFY.md](VERIFY.md) for verification checklist.

## Features

- **Automatic Entity Extraction** - LLM-powered extraction of people, organizations, concepts, and more
- **Relationship Mapping** - Automatically discovers connections between entities
- **Semantic Search** - Find knowledge using natural language, not just keywords
- **Temporal Tracking** - Know when knowledge was captured and how it evolves
- **Memory Sync** - Auto-syncs learnings from PAI Memory System
- **Query Sanitization** - Handles special characters in CTI/OSINT data

## Usage

The skill triggers automatically based on natural language:

| Say This | Action |
|----------|--------|
| "remember that X" | Capture knowledge with entity extraction |
| "what do I know about X" | Semantic search for related entities |
| "how are X and Y related" | Find relationships between concepts |
| "what did I learn today" | **Temporal search** - filter by date |
| "recent learnings" | Retrieve recent knowledge additions |
| "knowledge status" | Check system health |

### Temporal Search

Filter search results by date with `--since` and `--until`:

```bash
# Today's knowledge
bun run tools/knowledge-cli.ts search_nodes "topic" --since today

# Last 7 days
bun run tools/knowledge-cli.ts search_facts "decisions" --since 7d

# Date range
bun run tools/knowledge-cli.ts search_nodes "project" --since 2026-01-01 --until 2026-01-15
```

**Date formats:** `today`, `yesterday`, `7d`, `1w`, `1m`, or ISO dates (`2026-01-26`)

## What's Included

| Component | Purpose |
|-----------|---------|
| `SKILL.md` | PAI skill with intent-based routing |
| `src/skills/workflows/` | 8 workflows (Capture, Search, SearchByDate, Facts, Recent, Status, Clear, BulkImport) |
| `src/skills/tools/` | Server management scripts (start, stop, status, logs) |
| `src/hooks/` | Memory sync hook for automatic knowledge capture |
| `docker/` | Docker/Podman compose files for Neo4j and FalkorDB |

## Database Backends

| Backend | Web UI | Best For |
|---------|--------|----------|
| **Neo4j** (default) | http://localhost:7474 | Rich queries, special character handling |
| **FalkorDB** | http://localhost:3000 | Simple setup, lower resources |

## Configuration

All configuration uses `MADEINOZ_KNOWLEDGE_*` prefixed environment variables in `~/.claude/.env`:

```bash
# LLM Provider
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openai
MADEINOZ_KNOWLEDGE_MODEL_NAME=gpt-4o-mini
MADEINOZ_KNOWLEDGE_OPENAI_API_KEY=sk-your-key-here

# Database (neo4j or falkordb)
MADEINOZ_KNOWLEDGE_DATABASE_TYPE=neo4j
```

See [config/.env.example](config/.env.example) for complete configuration reference.

## Server Commands

```bash
bun run server-cli start    # Start containers
bun run server-cli stop     # Stop containers
bun run server-cli status   # Check status
bun run server-cli logs     # View logs
bun run server-cli --dev    # Development mode (isolated ports)
```

## For AI Agents

This is a **PAI Pack** - a complete, self-contained module for Personal AI Infrastructure:

1. Read the entire README to understand what you're installing
2. Follow [INSTALL.md](INSTALL.md) step-by-step
3. Complete ALL verification checks in [VERIFY.md](VERIFY.md)
4. If any step fails, STOP and troubleshoot before continuing

## Credits

- **Knowledge graph engine**: [Graphiti](https://github.com/getzep/graphiti) by Zep AI
- **Graph databases**: [Neo4j](https://neo4j.com/), [FalkorDB](https://www.falkordb.com/)
- **Built for**: [Personal AI Infrastructure (PAI)](https://github.com/danielmiessler/PAI)

## Related

- [PAI Memory System](https://github.com/danielmiessler/PAI) - Auto-syncs learnings to knowledge graph
- [PAI Research Skill](https://github.com/danielmiessler/PAI) - Capture research findings

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

**Latest: v1.2.5** - Consolidated server CLI, lib consolidation, Docker reorganization.

---

*For detailed documentation, visit the [full docs](https://madeinoz67.github.io/madeinoz-knowledge-system/).*
