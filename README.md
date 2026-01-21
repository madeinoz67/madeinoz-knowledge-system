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

> Persistent personal knowledge management system powered by Graphiti knowledge graph with FalkorDB or Neo4j backend - automatically extracts entities, relationships, and temporal context from conversations, documents, and ideas

[![Docker Build](https://github.com/madeinoz67/madeinoz-knowledge-system/actions/workflows/docker-build.yml/badge.svg)](https://github.com/madeinoz67/madeinoz-knowledge-system/actions/workflows/docker-build.yml)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/madeinoz67/madeinoz-knowledge-system)](https://github.com/madeinoz67/madeinoz-knowledge-system/releases/latest)
[![Docker Pulls](https://img.shields.io/docker/pulls/madeinoz-knowledge-system?label=Docker%20Hub)](https://hub.docker.com/r/madeinoz-knowledge-system)
[![GitHub Container Registry](https://img.shields.io/badge/ghcr.io-madeinoz--knowledge--system-blue?logo=docker)](https://ghcr.io/madeinoz67/madeinoz-knowledge-system)

📚 **[View Full Documentation](https://madeinoz67.github.io/madeinoz-knowledge-system/)** - Browse the complete docs online

## Quick Start with Docker

**Pull the custom image (with all patches):**
```bash
# From GitHub Container Registry (recommended)
docker pull ghcr.io/madeinoz67/madeinoz-knowledge-system:latest

# Or from Docker Hub
docker pull madeinoz-knowledge-system:latest
```

**Run with Docker Compose:**
```bash
# Neo4j backend (default)
docker compose -f src/server/docker-compose-neo4j.yml up -d

# FalkorDB backend
docker compose -f src/server/docker-compose-falkordb.yml up -d
```

**Why a custom image?** We apply critical upstream patches while waiting for official merges. See [Developer Notes](https://madeinoz67.github.io/madeinoz-knowledge-system/reference/developer-notes/) for details.

> **FOR AI AGENTS:** This is a PAI Pack - a complete, self-contained module for the PAI (Personal AI Infrastructure) system. When installing this pack:
> 1. Read the entire README first to understand what you're installing
> 2. Follow INSTALL.md step-by-step - do NOT skip or simplify steps
> 3. Complete ALL verification checks in VERIFY.md - ALL must pass
> 4. Each step has specific commands and expected outputs - verify them
> 5. If any step fails, STOP and troubleshoot before continuing

## Installation Prompt

You are receiving a PAI Pack - a modular upgrade for AI agent systems.

**What is PAI?** PAI (Personal AI Infrastructure) is a framework for building composable, modular AI systems with skills, hooks, and tools.

**What is a Pack?** A PAI Pack is a complete, end-to-end solution that can be installed into your PAI infrastructure. Each pack contains everything needed - from source code to configuration - with no missing components or "figure it out yourself" steps.

This pack adds persistent memory to your AI infrastructure. The Madeinoz Knowledge System is not just a note-taking tool - it's a comprehensive knowledge graph that:

- **Automatically Learns**: Extracts entities and relationships as you work
- **Connects Concepts**: Maps how ideas relate over time
- **Semantic Search**: Finds relevant knowledge using natural language
- **Builds Context**: Compounds knowledge across sessions
- **Never Forgets**: Persistent storage with temporal tracking
- **Query Sanitization**: Handles hyphenated identifiers and special characters in CTI/OSINT data

**Core principle**: Work normally, knowledge handles itself.

No more lost insights. No more forgotten context. Your AI builds a knowledge graph that grows with you.

Please follow the installation instructions below to integrate this pack into your infrastructure.

---

## What's Included

| Component | File | Purpose |
|-----------|------|---------|
| PAI Skill Definition | `SKILL.md` | Main skill file with intent-based routing and workflow table |
| Capture Workflow | `src/skills/workflows/CaptureEpisode.md` | Add knowledge to graph with entity extraction |
| Search Workflow | `src/skills/workflows/SearchKnowledge.md` | Find entities and summaries using semantic search |
| Facts Workflow | `src/skills/workflows/SearchFacts.md` | Find relationships between entities |
| Recent Workflow | `src/skills/workflows/GetRecent.md` | Retrieve recent knowledge additions |
| Status Workflow | `src/skills/workflows/GetStatus.md` | Check system health and statistics |
| Clear Workflow | `src/skills/workflows/ClearGraph.md` | Delete all knowledge and reset graph |
| Bulk Import Workflow | `src/skills/workflows/BulkImport.md` | Import multiple documents at once |
| Install Tool | `src/skills/tools/Install.md` | Complete installation workflow |
| **Memory Sync Hook** | `src/hooks/sync-memory-to-knowledge.ts` | Auto-sync learnings/research from PAI Memory System |
| Hook Libraries | `src/hooks/lib/*.ts` | Frontmatter parser, sync state, knowledge client, Lucene sanitization |
| MCP Server Launcher | `src/server/run.ts` | Graphiti server launcher with container orchestration |
| Server Management | `src/skills/tools/{start,stop,status,logs}.ts` | Container management scripts |
| Configuration Template | `config/.env.example` | API keys and model settings template (reference only) |
| Docker Compose (FalkorDB) | `src/server/docker-compose-falkordb.yml` | Docker Compose for FalkorDB backend |
| Docker Compose (Neo4j) | `src/server/docker-compose-neo4j.yml` | Docker Compose for Neo4j backend |
| Podman Compose (FalkorDB) | `src/server/podman-compose-falkordb.yml` | Podman Compose for FalkorDB backend |
| Podman Compose (Neo4j) | `src/server/podman-compose-neo4j.yml` | Podman Compose for Neo4j backend |
| Neo4j Config | `src/server/config-neo4j.yaml` | Graphiti MCP config for Neo4j backend |

**Summary:**
- **Files created:** 3 (README.md, INSTALL.md, VERIFY.md)
- **Workflows included:** 7
- **Tools included:** 1
- **Hooks included:** 2 (Memory Sync, Realtime Learning Sync)
- **Server scripts:** 5 (run, start, stop, status, logs)
- **Database backends:** Neo4j (default) or FalkorDB
- **External dependencies:** Podman/Docker, Graph database image
- **Dependencies:** Podman (container runtime), OpenAI API key (or compatible LLM provider)

---

## The Concept and/or Problem

AI agents are brilliant but amnesiac. Every conversation starts fresh with no memory of:

- What you learned last week about a technology
- Why you made certain architectural decisions
- What bugs you've already fixed (and might reintroduce)
- Lessons learned from debugging sessions
- Research you've already conducted
- Connections between seemingly unrelated concepts

This creates cascading problems across your entire AI workflow:

**For Development Work:**
- You research the same topics repeatedly because findings aren't captured
- Architectural decisions lack rationale when revisited months later
- Code reviews miss context because the "why" is lost
- Debugging sessions don't preserve solutions for future reference

**For Knowledge Management:**
- Notes are scattered across files, chats, and documents
- No way to see how concepts connect across domains
- Search is keyword-based, missing semantic relationships
- Temporal context is lost - when did you learn this?

**For Continuous Learning:**
- Insights get lost in conversation history
- No way to build on previous discoveries
- Mistakes repeat because there's no institutional memory
- Can't track how your understanding evolves over time

**The Fundamental Problem:**

Traditional AI systems treat knowledge as ephemeral. But real learning is cumulative. Today's debugging session informs tomorrow's architecture decision. Last month's research prevents this week's repeated mistake. Research findings should connect to project decisions. Bug fixes should link to related concepts.

Without a knowledge system, your AI is powerful but forgetful. Every conversation is day one. Every insight is fleeting. Every connection must be manually rediscovered.

---

## The Solution

The Madeinoz Knowledge System solves this through **automatic knowledge graph construction**. Instead of requiring manual note-taking, it extracts and structures knowledge as a natural byproduct of conversation.

**Core Architecture:**

```
User Conversation/Document
         │
         ▼
┌─────────────────────────────────┐
│   Madeinoz Knowledge System Skill    │
│  ┌───────────────────────────┐  │
│  │   Intent Routing          │  │
│  │   - "remember this"       │  │
│  │   - "what do I know"      │  │
│  │   - "how are X and Y...   │  │
│  └───────────┬───────────────┘  │
└───────────────┼──────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│   Graphiti MCP Server           │
│  ┌───────────────────────────┐  │
│  │   LLM-Based Extraction    │  │
│  │   - Entities (People,     │  │
│  │     Organizations,        │  │
│  │     Concepts, Places)     │  │
│  │   - Relationships         │  │
│  │   - Temporal Context      │  │
│  └───────────┬───────────────┘  │
│             │                    │
│  ┌──────────▼───────────────┐  │
│  │   Vector Embeddings      │  │
│  │   - OpenAI embeddings    │  │
│  │   - Semantic similarity  │  │
│  └──────────┬───────────────┘  │
└─────────────┼──────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│   Graph Database Backend        │
│  ┌───────────────────────────┐  │
│  │  Neo4j (default)          │  │
│  │   - Native graph DB       │  │
│  │   - Cypher queries        │  │
│  │   - Browser :7474         │  │
│  ├───────────────────────────┤  │
│  │  FalkorDB (alternative)   │  │
│  │   - Redis-based           │  │
│  │   - RediSearch queries    │  │
│  │   - Web UI :3000          │  │
│  └───────────────────────────┘  │
│  Nodes, Edges, Episodes, Indices│
└─────────────────────────────────┘
```

**How It Works:**

1. **Natural Capture**: Say "remember that Podman volumes use host:container syntax" and the system:
   - Extracts entities: "Podman", "volume mounting"
   - Identifies relationship: "uses", "syntax rule"
   - Creates episode with full context
   - Stores in graph with timestamp

2. **Semantic Search**: Ask "what do I know about container orchestration?" and the system:
   - Searches vector embeddings for related concepts
   - Returns entities: "Podman", "Kubernetes", "Docker Compose"
   - Shows relationships: "alternatives to", "similar tools"
   - Displays episodes with full context

3. **Relationship Discovery**: Ask "how are FalkorDB and Graphiti connected?" and the system:
   - Traverses graph edges between entities
   - Returns: "FalkorDB is the graph database backend for Graphiti"
   - Shows temporal context: "learned on 2025-01-03"
   - Displays related entities and connections

**Design Principles:**

1. **Zero Friction**: Capture knowledge through natural conversation
2. **Automatic Extraction**: LLM-powered entity and relationship detection
3. **Semantic Understanding**: Vector embeddings enable concept-based search
4. **Temporal Tracking**: Know when knowledge was added and how it evolves
5. **Graph-Based**: Explicit relationships show how concepts connect
6. **Complete**: Every component included - MCP server, PAI skill, workflows

**The Key Insight:**

Knowledge capture should be conversational, not administrative. By making the process frictionless and automatic, you build a knowledge graph that compounds over time without requiring manual maintenance or organization.

---

## What Makes This Different

The Madeinoz Knowledge System solves the problem through **multi-layered semantic architecture** that goes far beyond simple keyword search or flat note storage.

**Core Architecture:**

```
┌─────────────────────────────────────────────────────────────┐
│                    User Intent Layer                        │
│  Natural language triggers: "remember this", "what do I     │
│  know about X", "how are X and Y related"                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  PAI Skill Routing Layer                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  SKILL.md Frontmatter → Intent Detection             │  │
│  │  - USE WHEN clauses trigger based on user phrases    │  │
│  │  - Routes to appropriate workflow                    │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Workflow Execution Layer                   │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │  CaptureEpisode  │  │  SearchKnowledge │               │
│  │  - Adds episode  │  │  - Vector search │               │
│  │  - Extracts      │  │  - Returns       │               │
│  │    entities      │  │    entities +    │               │
│  │  - Creates       │  │    summaries     │               │
│  │    relationships │  │                  │               │
│  └──────────────────┘  └──────────────────┘               │
│                                                         │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │  SearchFacts     │  │  GetRecent       │               │
│  │  - Traverses     │  │  - Temporal      │               │
│  │    graph edges   │  │    queries       │               │
│  │  - Returns       │  │  - Shows         │               │
│  │    connections   │  │    progression   │               │
│  └──────────────────┘  └──────────────────┘               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              MCP Server Integration Layer                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  SSE Endpoint: localhost:8000/sse                    │  │
│  │  - add_memory: Store knowledge                       │  │
│  │  - search_memory_nodes: Semantic entity search       │  │
│  │  - search_memory_facts: Relationship traversal       │  │
│  │  - get_episodes: Temporal retrieval                  │  │
│  │  - delete_episode/clear_graph: Management            │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Graphiti Knowledge Graph Layer                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  LLM Processing (OpenAI/compatible)                  │  │
│  │  ┌────────────────────────────────────────────────┐ │  │
│  │  │  Entity Extraction                             │ │  │
│  │  │  - People, Organizations, Locations            │ │  │
│  │  │  - Concepts, Preferences, Requirements         │ │  │
│  │  │  - Procedures, Events, Documents               │ │  │
│  │  └────────────────────────────────────────────────┘ │  │
│  │                     │                               │  │
│  │  ┌──────────────────▼─────────────────────────────┐ │  │
│  │  │  Relationship Mapping                          │ │  │
│  │  │  - Causal: X caused Y                          │ │  │
│  │  │  - Dependency: X requires Y                    │ │  │
│  │  │  - Temporal: X happened before Y               │ │  │
│  │  │  - Semantic: X is related to Y                 │ │  │
│  │  └────────────────────────────────────────────────┘ │  │
│  │                     │                               │  │
│  │  ┌──────────────────▼─────────────────────────────┐ │  │
│  │  │  Vector Embeddings                             │ │  │
│  │  │  - OpenAI text-embedding-3-small               │ │  │
│  │  │  - Semantic similarity search                  │ │  │
│  │  │  - Hybrid: vector + keyword                    │ │  │
│  │  └────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│           FalkorDB Graph Database (Redis-based)             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Nodes: Entities with embeddings and metadata        │  │
│  │  Edges: Typed relationships with timestamps          │  │
│  │  Episodes: Full conversation context                │  │
│  │  Indices: Vector search, entity lookup, time        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Why This Architecture Matters:**

**1. Separation of Concerns**
Each layer has a single responsibility:
- **Intent Layer**: Natural language understanding
- **Routing Layer**: Direct user intent to workflow
- **Workflow Layer**: Operational procedures
- **Server Layer**: API abstraction
- **Graph Layer**: Knowledge operations
- **Database Layer**: Persistent storage

This is FUNDAMENTALLY DIFFERENT from "just storing notes" because:
- Progressive abstraction (not everything in one layer)
- Explicit intent routing (not fuzzy keyword matching)
- Separation of operations (capture, search, retrieve distinct)
- Deterministic execution (workflows map intent to MCP calls)

**2. Bidirectional Knowledge Flow**

```
User → "Remember X" → Capture Episode → Extract Entities → Create Relationships → Store in Graph
                                                                              ↓
User ← "What about X" ← Search Results ← Vector Search ← Semantic Similarity ← Graph Query
```

Every knowledge addition improves future retrieval. Every search result can trigger new knowledge capture.

**3. Multi-Dimensional Retrieval**

Traditional search: Keyword matching in flat text
Knowledge graph: Three retrieval dimensions

| Dimension | Mechanism | Example Query | Result Type |
|-----------|-----------|---------------|-------------|
| **Semantic** | Vector embeddings | "container orchestration" | Podman, Kubernetes, Docker |
| **Relational** | Graph traversal | "how are X and Y related" | "X uses Y as backend" |
| **Temporal** | Episode timestamps | "what did I learn about X" | Chronological episodes |

**4. Automatic Entity Extraction**

LLM-powered extraction identifies:
- **Named Entities**: People, organizations, locations
- **Abstract Concepts**: Technologies, methodologies, patterns
- **Procedural Knowledge**: Workflows, SOPs, how-to guides
- **Preferences**: Choices, configurations, opinions
- **Requirements**: Features, needs, specifications

This happens AUTOMATICALLY - no manual tagging required.

**5. Temporal Context Tracking**

Every episode includes:
- Timestamp: When knowledge was added
- Source: Conversation or document
- Entity State: How understanding evolved
- Relationship Creation: When connections were made

Example: "FalkorDB backend for Graphiti (learned 2025-01-03, updated 2025-01-05)"

**6. Lucene Query Sanitization**

The knowledge system includes automatic query sanitization to handle special characters in search terms, particularly important for CTI/OSINT data with hyphenated identifiers.

**The Problem:**
FalkorDB uses RediSearch, which implements Lucene query syntax. In Lucene, certain characters have special meaning:
- Hyphens (`-`) are interpreted as negation operators (NOT)
- Quotes (`"`) define phrase queries
- Wildcards (`*`, `?`) enable pattern matching

When searching for hyphenated group_ids like `madeinoz-threat-intel`, Lucene interprets this as "pai AND NOT threat AND NOT intel", causing query syntax errors.

**The Solution:**
A centralized sanitization module automatically escapes special characters:

**`src/server/lib/lucene.ts`** - Canonical sanitization module for all operations (server and hooks)

**Sanitization Functions:**

| Function | Purpose | Example |
|----------|---------|---------|
| `luceneSanitize(value)` | Escape a value by wrapping in quotes and escaping special characters | `"madeinoz-threat-intel"` |
| `sanitizeGroupId(groupId)` | Convenience function for sanitizing group_ids | `"madeinoz-threat-intel"` |
| `sanitizeGroupIds(groupIds)` | Sanitize an array of group_ids | `["group-1", "group-2"]` |
| `sanitizeSearchQuery(query)` | Escape special characters in search queries while preserving multi-word searches | `pai\\-threat\\-intel` |

**What Gets Escaped:**
Special Lucene characters: `+ - && || ! ( ) { } [ ] ^ " ~ * ? : \ /`

**Root Cause Analysis:**
```
Unsanitized query: group_id:madeinoz-threat-intel
Lucene interpretation: group_id:pai AND NOT threat AND NOT intel
Result: Syntax error (incomplete negation)

Sanitized query: group_id:"madeinoz-threat-intel"
Lucene interpretation: group_id equals literal string "madeinoz-threat-intel"
Result: Successful search
```

**7. End-to-End Completeness**

Every component is included:
- ✅ MCP Server: `run.ts` starts Graphiti + Neo4j/FalkorDB
- ✅ PAI Skill: `SKILL.md` with intent routing
- ✅ Workflows: 7 complete operational procedures
- ✅ Installation: Step-by-step in `tools/Install.md`
- ✅ Configuration: All settings in PAI config (`$PAI_DIR/.env`)
- ✅ Documentation: README, INSTALL, VERIFY
- ✅ Query Sanitization: Handles special characters automatically

NOT: "You need to set up your own vector database" - FalkorDB is included
NOT: "Implement your own entity extraction" - Graphiti handles it
NOT: "Configure your own embeddings" - OpenAI integration built-in
NOT: "Handle special characters manually" - Lucene sanitization built-in

**What Problems This Architecture Prevents:**

| Problem | Traditional Approach | Knowledge Graph Approach |
|---------|---------------------|-------------------------|
| **Keyword limits** | Must know exact terms | Semantic similarity finds related concepts |
| **Siloed information** | Notes in separate files | Graph connects everything |
| **Lost context** | No temporal tracking | Every episode has timestamp |
| **No relationships** | Flat documents | Explicit edges between entities |
| **Manual organization** | Tag and categorize yourself | Automatic entity extraction |
| **Scattered knowledge** | Multiple tools | Single unified graph |
| **Hyphenated identifiers** | Query syntax errors | Automatic sanitization |

**The Architectural Innovation:**

The key insight is that **knowledge is relational, not transactional**. Traditional note-taking treats each piece of information as an isolated transaction. The Madeinoz Knowledge System treats knowledge as a graph of interconnected entities with temporal context.

This isn't just "better search" - it's a fundamentally different paradigm:
- **Transaction**: "Note about Podman volumes" (isolated, static)
- **Relational**: "Podman → uses → volume mounting → syntax → host:container" (connected, queryable, temporal)

The graph structure allows queries impossible with flat notes:
- "Show me all technologies related to container orchestration I learned about in the past month"
- "What debugging solutions led to architectural decisions?"
- "How do my preferences for dev tools relate to past troubleshooting sessions?"
- "Find all CTI indicators from group 'apt-28'"

This architecture makes your AI infrastructure genuinely intelligent, not just a better filing cabinet.

---

## Why This Is Different

This sounds similar to Obsidian which also does knowledge management through linked notes. What makes this approach different?

The Madeinoz Knowledge System uses LLM-powered automatic entity extraction and semantic vector embeddings, requiring zero manual effort to organize. Unlike manual note-linking systems that demand you create and maintain connections yourself, this pack automatically identifies entities, relationships, and temporal context as you converse - no tagging, categorizing, or linking required.

- Automatic extraction eliminates all manual tagging overhead completely
- Semantic vector search enables concept-based knowledge queries
- Temporal tracking shows how your knowledge evolves
- Conversational interface integrates seamlessly into AI workflows
- Query sanitization handles CTI/OSINT data with special characters

---

## Installation

### AI-Assisted Installation (Recommended)

Give this pack directory to your AI agent and say:

> "Install this pack"

The AI will read [INSTALL.md](INSTALL.md) and execute each step, handling configuration, starting services, and verifying the installation. This is the standard PAI pack installation method.

### Interactive Installer (Alternative)

For humans who prefer an interactive CLI experience without AI assistance:

```bash
cd /path/to/madeinoz-knowledge-system
bun run src/server/install.ts
```

This guides you through database backend selection, LLM provider selection, API key configuration, and service startup.

**Database Backends:**
- **Neo4j** (default) - Native graph DB, better special character handling, richer query language
- **FalkorDB** - Redis-based, simpler setup, lower resources

**Flags:**
- `--yes` or `-y`: Non-interactive mode with defaults
- `--update` or `-u`: Update existing installation

### Manual Installation

See [INSTALL.md](INSTALL.md) for complete step-by-step instructions that can be followed manually or by an AI agent.

---

## Invocation Scenarios

The Madeinoz Knowledge System triggers automatically based on natural language intent:

| Trigger | Workflow | Action | Output |
|---------|----------|--------|--------|
| "remember that X", "store this", "add to knowledge" | CaptureEpisode | Extract entities and relationships from input | Episode stored in graph with timestamp |
| "what do I know about X", "search my knowledge" | SearchKnowledge | Vector search for related entities | List of entities with summaries and facts |
| "how are X and Y related", "what's the connection" | SearchFacts | Graph traversal between entities | Relationships with temporal context |
| "what did I learn", "recent additions" | GetRecent | Temporal episode query | Chronological list of recent knowledge |
| "knowledge status", "graph health" | GetStatus | Server and database statistics | Entity count, episode count, last update |
| "clear knowledge", "reset graph" | ClearGraph | Delete all data | Confirmation and graph reset |
| "import these documents" | BulkImport | Multi-document processing | Episodes created from each document |

**Edge Cases Handled:**

| Scenario | Behavior |
|----------|----------|
| Server not running | Workflow returns error with troubleshooting steps |
| No entities extracted | Suggests adding more context and detail |
| Empty search results | Recommends broader queries or different terms |
| API rate limits | Automatically retries with exponential backoff |
| Duplicate knowledge | Detects and updates existing entities instead of creating duplicates |
| Hyphenated group_ids | Automatic sanitization handles CTI/OSINT identifiers |

---

## Example Usage

### Example 1: Capturing Technical Knowledge

**User Input:**
```
Remember that when using PAI skills, the SKILL.md file must have a description
with a USE WHEN clause for intent-based routing. Workflows go in the workflows/
subdirectory with TitleCase names.
```

**System Behavior:**
1. Invokes CaptureEpisode workflow
2. Sends to MCP server: `add_episode`
3. Graphiti LLM extracts:
   - Entity: "PAI skills" (Concept)
   - Entity: "SKILL.md" (Document)
   - Entity: "USE WHEN clause" (Procedure)
   - Entity: "workflows/" (Location)
   - Relationship: "requires" → SKILL.md → PAI skills
   - Relationship: "contains" → workflows/ → PAI skills
4. Creates episode with full context

**Output to User:**
```
✓ Captured: PAI skills structure
- Entities extracted: 4
- Relationships created: 2
- Episode ID: abc-123-def
```

### Example 2: Searching Your Knowledge

**User Input:**
```
What do I know about Graphiti knowledge graphs?
```

**System Behavior:**
1. Invokes SearchKnowledge workflow
2. Sends to MCP server: `search_nodes` with query "Graphiti knowledge graphs"
3. Performs vector similarity search
4. Returns related entities with summaries and facts

**Output to User:**
```
Based on your knowledge graph:

**Entities:**
- Graphiti (Knowledge Graph Framework)
- FalkorDB (Graph Database)
- Entity Extraction (LLM Process)
- Vector Embeddings (Semantic Search)

**Key Facts:**
- Graphiti is a knowledge graph framework by Zep AI
- FalkorDB serves as the graph database backend (learned 2025-01-03)
- Uses OpenAI embeddings for semantic search
- Extracts entities: People, Organizations, Locations, Concepts, Procedures
- Maps relationships: causal, dependency, temporal, semantic

**Related Episodes:**
1. "Madeinoz Knowledge System setup" - 2025-01-03
2. "Entity extraction quality" - 2025-01-04
3. "Vector search tuning" - 2025-01-05
```

### Example 3: Finding Relationships

**User Input:**
```
How are Podman and Docker related?
```

**System Behavior:**
1. Invokes SearchFacts workflow
2. Sends to MCP server: `search_facts` for "Podman" and "Docker"
3. Traverses graph edges between entities
4. Returns relationships with temporal context

**Output to User:**
```
Relationships between Podman and Docker:

**Direct Relationships:**
- Podman → alternative to → Docker (learned 2025-01-02)
- Docker → similar tool → Podman (learned 2025-01-02)

**Related Entities:**
- Containerization (both implement this)
- Kubernetes (orchestration layer)
- Docker Compose (composition tool)

**Context from Episodes:**
"Podman is a daemonless container engine that's CLI-compatible with Docker
but doesn't require a root daemon" (captured 2025-01-02)
```

### Example 4: Reviewing Recent Learning

**User Input:**
```
What did I learn this week about knowledge management?
```

**System Behavior:**
1. Invokes GetRecent workflow
2. Sends to MCP server: `get_episodes` with filter "knowledge management"
3. Retrieves episodes from past 7 days
4. Returns chronological list

**Output to User:**
```
Recent knowledge about "knowledge management" (past 7 days):

**2025-01-05 - Graphiti vs Traditional Notes**
- Graphiti uses automatic entity extraction vs manual tagging
- Vector embeddings enable semantic search beyond keywords
- Temporal tracking shows knowledge evolution

**2025-01-04 - FalkorDB Configuration**
- FalkorDB runs as Redis module for graph operations
- Default port: 6379
- Web UI available at localhost:3000

**2025-01-03 - Madeinoz Knowledge System Setup**
- Installed Graphiti MCP server with FalkorDB backend
- Configured OpenAI API key for LLM operations
- Installed PAI skill to ~/.claude/skills/

Total: 3 episodes, 12 entities extracted, 8 relationships created
```

### Example 5: Clearing and Resetting

**User Input:**
```
Clear my knowledge graph and start fresh
```

**System Behavior:**
1. Invokes ClearGraph workflow
2. Confirms destructive action
3. Sends to MCP server: `clear_graph`
4. Server deletes all entities and relationships
5. Rebuilds indices

**Output to User:**
```
⚠️  WARNING: This will delete all knowledge from your graph.
Entities: 156
Relationships: 342
Episodes: 89

Type 'confirm' to proceed or 'cancel' to abort: confirm

✓ Knowledge graph cleared.
- All entities deleted
- All relationships removed
- Indices rebuilt

Ready for fresh knowledge capture.
```

### Example 6: Troubleshooting - Server Not Running

**User Input:**
```
Remember that I prefer gpt-4o for complex reasoning tasks
```

**System Behavior:**
1. Invokes CaptureEpisode workflow
2. Attempts to connect to MCP server at localhost:8000
3. Connection fails - server not running
4. Workflow returns error with troubleshooting steps

**Output to User:**
```
❌ Unable to connect to Graphiti MCP server at localhost:8000

**Troubleshooting Steps:**

1. Check if server is running:
   podman ps | grep madeinoz-knowledge-graph-mcp

2. If not running, start the server:
   bun run src/server/run.ts

3. Check server logs:
   bun run src/skills/tools/logs.ts

4. Verify health endpoint:
   curl http://localhost:8000/health

5. Check if port is already in use:
   lsof -i :8000

Once the server is running, try capturing knowledge again.
```

---

## Configuration

### Environment Variables

#### Configuration File Location

**All environment variables must be configured in** `~/.claude/.env`

This is the PAI configuration file, located in your home directory. **Do not** create a `.env` file in the project directory - it will not be used.

The `config/.env.example` file in this pack is a reference template only, showing available variables and their defaults.

#### Variable Prefix Pattern

All configuration variables use the `MADEINOZ_KNOWLEDGE_` prefix. This naming convention prevents conflicts with other PAI packs that may use similar variable names.

| Prefixed Variable | Unprefixed Container Variable |
|-------------------|-------------------------------|
| `MADEINOZ_KNOWLEDGE_LLM_PROVIDER` | `LLM_PROVIDER` |
| `MADEINOZ_KNOWLEDGE_MODEL_NAME` | `MODEL_NAME` |
| `MADEINOZ_KNOWLEDGE_OPENAI_API_KEY` | `OPENAI_API_KEY` |
| `MADEINOZ_KNOWLEDGE_OLLAMA_BASE_URL` | `OLLAMA_BASE_URL` |

#### entrypoint.sh Mapping

The `entrypoint.sh` script automatically maps prefixed variables to their unprefixed equivalents at container startup. You only need to set the `MADEINOZ_KNOWLEDGE_*` prefixed variables in `~/.claude/.env` - the script handles the translation internally.

**Benefits of this approach:**
- Clear ownership: Each variable is pack-specific
- No conflicts: Different packs can use different settings for the same underlying variable
- Separate billing: Track costs per pack
- Clean configuration: Only prefixed variables needed, no duplication

#### Key Environment Variables

```bash
# In ~/.claude/.env

# LLM Provider (openai, anthropic, gemini, groq)
MADEINOZ_KNOWLEDGE_LLM_PROVIDER=openai

# Model Name (e.g., gpt-4o-mini, gpt-4o)
MADEINOZ_KNOWLEDGE_MODEL_NAME=gpt-4o-mini

# API Key (required for OpenAI provider)
MADEINOZ_KNOWLEDGE_OPENAI_API_KEY=sk-your-key-here

# Embedder Provider (ollama recommended for free local embeddings)
MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER=ollama

# Ollama Base URL (when using Ollama for embeddings)
MADEINOZ_KNOWLEDGE_OLLAMA_BASE_URL=http://host.containers.internal:11434

# OpenRouter Base URL (optional - for accessing multiple LLM providers)
MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL=https://openrouter.ai/api/v1

# Concurrency Limit (adjust based on API tier)
MADEINOZ_KNOWLEDGE_SEMAPHORE_LIMIT=10

# Knowledge Graph Group ID (creates isolated graphs)
MADEINOZ_KNOWLEDGE_GROUP_ID=main
```

**For a complete list of all available variables**, see `config/.env.example` in this pack.

### Model Selection

| Model | Use Case | Cost | Quality | Recommended |
|-------|----------|------|---------|-------------|
| **gpt-4o-mini** | Daily use, high volume | Low | Good | ✅ Yes |
| **gpt-4o** | Complex reasoning, important knowledge | Medium | Excellent | For critical content |
| **gpt-3.5-turbo** | Economy option | Very Low | Fair | Not recommended |

### Concurrency Tuning

Adjust `SEMAPHORE_LIMIT` based on your OpenAI API tier:

| Tier | Rate Limit | SEMAPHORE_LIMIT | Cost |
|------|------------|-----------------|------|
| Free | 0 RPM | 1-2 | $0/month |
| Tier 1 | 10 RPM | 3-5 | $5/month |
| Tier 2 | 60 RPM | 8-10 | $20/month |
| Tier 3 | 500 RPM | 10-15 | $100/month |
| Tier 4 | 5000 RPM | 20-50 | $250/month |

---

## Database Backend Selection

The Madeinoz Knowledge System supports two graph database backends:

| Backend | Description | Web UI | Best For |
|---------|-------------|--------|----------|
| **Neo4j** (default) | Native graph database with Cypher queries | http://localhost:7474 | Special character handling, richer queries |
| **FalkorDB** | Redis-based graph database with RediSearch | http://localhost:3000 | Simple setup, lower resources |

### Choosing a Backend

**Use Neo4j (default) when:**
- You're working with CTI/OSINT data containing hyphenated identifiers
- You want native Cypher query language
- You need the Neo4j Browser for rich graph visualization
- You're already familiar with Neo4j ecosystem

**Use FalkorDB when:**
- You want the simplest setup with minimal configuration
- You have limited system resources
- Your group_ids and data don't contain many special characters

### Backend-Specific Notes

**FalkorDB:**
- Uses RediSearch with Lucene query syntax
- Special characters (hyphens, etc.) require automatic sanitization
- Lower memory footprint (~500MB)
- Web UI at port 3000

**Neo4j:**
- Uses native Cypher query language
- No Lucene escaping needed - handles special characters natively
- Higher memory footprint (~1-2GB)
- Neo4j Browser at port 7474, Bolt protocol at port 7687

### Switching Backends

To switch backends, update your configuration:

```bash
# In your PAI .env file
MADEINOZ_KNOWLEDGE_DATABASE_TYPE=neo4j  # or falkordb

# Then restart services
bun run src/server/stop.ts
bun run src/server/run.ts
```

---

## Graph Database UI - Viewing Knowledge

Both backends include built-in web UIs for visualizing your knowledge graph, exploring entity relationships, and running queries directly.

### FalkorDB UI (Alternative Backend)

FalkorDB includes a built-in web UI for visualizing your knowledge graph.

### Accessing the UI

1. **Ensure containers are running:**
   ```bash
   docker ps | grep madeinoz-knowledge
   # or: podman ps | grep madeinoz-knowledge
   ```

2. **Open the FalkorDB Browser:**
   ```
   http://localhost:3000
   ```

3. **Connect to the graph:**
   - Host: `localhost`
   - Port: `6379` (default Redis port)
   - Graph name: `graphiti` (or your configured graph)

### Exploring Relationships

Once connected, you can visualize your knowledge graph:

**View all entities and relationships:**
```cypher
MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 100
```

**Find specific entity connections:**
```cypher
MATCH (n {name: 'your-entity-name'})-[r]-(m) RETURN n, r, m
```

**View entity types:**
```cypher
MATCH (n) RETURN DISTINCT labels(n), count(*)
```

### Screenshot

![FalkorDB Knowledge Graph UI](assets/falkordb_ui.png)

*The FalkorDB UI displays entities as nodes and relationships as edges, allowing you to visually explore how concepts connect in your knowledge graph.*

### Documentation

For more details on querying and visualization, see the [FalkorDB Documentation](https://docs.falkordb.com/).

### Neo4j Browser (Default Backend)

Neo4j Browser provides rich graph visualization for your knowledge graph.

### Accessing Neo4j Browser

1. **Ensure containers are running:**
   ```bash
   docker ps | grep madeinoz-knowledge-neo4j
   # or: podman ps | grep madeinoz-knowledge-neo4j
   ```

2. **Open the Neo4j Browser:**
   ```
   http://localhost:7474
   ```

3. **Connect to the database:**
   - Username: `neo4j` (default)
   - Password: `madeinozknowledge` (default)
   - Database: `neo4j`

### Exploring with Cypher

Neo4j uses the Cypher query language (no Lucene escaping needed):

**View all entities and relationships:**
```cypher
MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 100
```

**Find specific entity connections:**
```cypher
MATCH (n {name: 'your-entity-name'})-[r]-(m) RETURN n, r, m
```

**Search with special characters (no escaping needed):**
```cypher
MATCH (n) WHERE n.group_id = 'madeinoz-threat-intel' RETURN n
```

**View entity types:**
```cypher
MATCH (n) RETURN DISTINCT labels(n), count(*)
```

### Documentation

For more details on Cypher and Neo4j, see the [Neo4j Documentation](https://neo4j.com/docs/).

---

## Customization

### Recommended Customization

**What to Customize:** LLM model selection based on your use case

**Why:** The default gpt-4o-mini provides good quality at low cost, but complex domains may need more powerful models for accurate entity extraction and relationship mapping.

**Process:**
1. Assess your knowledge domain complexity
   - Simple: Technical documentation, procedures → gpt-4o-mini
   - Complex: Research, cross-domain connections → gpt-4o
2. Update `MODEL_NAME` in PAI config (`$PAI_DIR/.env` or `~/.claude/.env`)
3. Restart MCP server: `podman restart graphiti-knowledge-graph-mcp`
4. Test with sample knowledge capture
5. Compare extraction quality between models

**Expected Outcome:** Improved entity extraction accuracy for complex or nuanced content, with higher API costs.

---

### Optional Customization

| Customization | Configuration | Impact |
|--------------|---------------|--------|
| **Alternative LLM Provider** | PAI config: `MADEINOZ_KNOWLEDGE_LLM_PROVIDER`, `MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER` | Switch from OpenAI to Anthropic, Google Gemini, or Groq |
| **Multiple Knowledge Graphs** | PAI config: `MADEINOZ_KNOWLEDGE_GROUP_ID` | Create isolated graphs for different domains (work, personal, research) |
| **Custom Entity Types** | Graphiti configuration | Add domain-specific entity types beyond defaults (Preferences, Requirements, Procedures, etc.) |
| **Vector Embedding Model** | PAI config: `MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER` | Use different embedding models for semantic search |
| **Web UI Configuration** | `src/server/run.ts` | Change FalkorDB web UI port (default: 3000) |
| **Database Persistence** | `src/server/run.ts` | Add volume mounts for persistent data storage |

---

## Troubleshooting

### "Received request before initialization was complete"

If you see this warning in the MCP container logs:

```
WARNING - Failed to validate request: Received request before initialization was complete
```

**Cause:** This occurs when Claude Code sends MCP requests before the SSE session is fully initialized. This is a known issue with the Graphiti MCP server's SSE transport handling.

**Workaround:** Restart Claude Code. This resets the MCP connection and allows a fresh session initialization.

**Tracking:** This issue is being tracked upstream: [graphiti#840](https://github.com/getzep/graphiti/issues/840)

### Server Not Running

If knowledge operations fail with connection errors:

1. Check container status: `docker ps | grep madeinoz-knowledge`
2. Start containers if needed: `bun run src/skills/tools/start.ts`
3. Check logs for errors: `bun run src/skills/tools/logs.ts`

### Token Limit Exceeded

If you see warnings about "Output length exceeded max tokens 8192":

**Cause:** The LLM is generating too much output during entity extraction for complex content.

**Workaround:**
- Keep episode content concise (under 2000 characters)
- Split large documents into smaller chunks before importing
- Use a different LLM model with higher output limits by updating `MODEL_NAME` in your `.env` file (e.g., `gpt-4o` instead of `gpt-4o-mini`)
- The system will retry automatically, but some content may fail to process

### Lucene Query Syntax Errors

If you see errors like "Syntax error near '-'" when searching for hyphenated terms:

**Cause:** FalkorDB uses RediSearch with Lucene query syntax, which interprets hyphens as negation operators (NOT). Searching for `madeinoz-threat-intel` is parsed as "pai AND NOT threat AND NOT intel", causing syntax errors.

**Example Error:**
```
QuerySyntaxError: Syntax error near '-' in query 'group_id:madeinoz-threat-intel'
```

**Solution:** The Madeinoz Knowledge System includes automatic query sanitization that escapes special Lucene characters. The sanitization is handled by a centralized module:

**`src/server/lib/lucene.ts`** - Canonical sanitization module used by both server and hook operations

**What Gets Escaped:**
- Hyphens: `madeinoz-threat-intel` → `"madeinoz-threat-intel"`
- Other special characters: `+ - && || ! ( ) { } [ ] ^ " ~ * ? : \ /`

**Verification:**
The sanitization is automatic and happens transparently. All CTI/OSINT operations with hyphenated group_ids (e.g., `apt-28`, `tracked-actor-123`) now work correctly without manual intervention.

**If you still see errors:**
1. Verify you're using the latest version of the knowledge system
2. Check that `src/server/lib/lucene.ts` exists (the canonical sanitization module)
3. Try the search again - sanitization is applied automatically

---

## Credits

- **Original concept**: Built as part of Personal AI Infrastructure (PAI) framework
- **Knowledge graph engine**: [Graphiti](https://github.com/getzep/graphiti) by Zep AI ([GitHub](https://github.com/getzep/graphiti))
- **Graph database**: [FalkorDB](https://www.falkordb.com/) - Redis-based graph database ([GitHub](https://github.com/FalkorDB/FalkorDB))
- **Query parsing**: RediSearch with Lucene syntax (special character handling)
- **Inspired by**: Zettelkasten method, knowledge graph research, semantic search systems

---

## Related Work

- [Obsidian](https://obsidian.md) - Knowledge management with linked notes (manual linking vs automatic extraction)
- [mem0](https://github.com/mem0ai/mem0) - AI memory systems (focus on chat history vs knowledge graphs)
- [Zep](https://github.com/getzep/zep) - Long-term memory for AI applications

---

## Works Well With

- **PAI Memory System** (Built-in) - Core memory infrastructure; learnings and research are auto-synced to knowledge graph
- **PAI Research Skill** - Capture research findings into knowledge graph with entity extraction
- **Observability Dashboard** - Monitor knowledge operations in real-time via workflow notifications

---

## Memory Sync Hook Integration

The Madeinoz Knowledge System includes a **Memory Sync Hook** that automatically bridges the PAI Memory System with the knowledge graph. This creates a seamless flow where learnings and research captured during sessions are automatically enriched with semantic search and entity extraction.

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                    MEMORY → KNOWLEDGE FLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Session Work                                                   │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ PAI Memory System (hooks)                               │   │
│  │ • Captures learnings and insights                       │   │
│  │ • Tracks ratings and signals                            │   │
│  │ • Writes markdown with YAML frontmatter                 │   │
│  └──────────────────────┬──────────────────────────────────┘   │
│                         │                                       │
│                         ▼                                       │
│  ~/.claude/MEMORY/                                              │
│  ├── LEARNING/ALGORITHM/2026-01/*.md  ◄── HIGH VALUE          │
│  ├── LEARNING/SYSTEM/2026-01/*.md     ◄── HIGH VALUE          │
│  └── RESEARCH/2026-01/*.md            ◄── HIGH VALUE          │
│                         │                                       │
│  ═══════════════════════════════════════════════════════════   │
│                         │                                       │
│  Next Session Start     │                                       │
│       │                 │                                       │
│       ▼                 ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ sync-memory-to-knowledge.ts (SessionStart hook)         │   │
│  │ • Parses YAML frontmatter (capture_type, timestamp)     │   │
│  │ • Maps to knowledge API (name, episode_body, group_id)  │   │
│  │ • Calls add_memory() for each unsynced file             │   │
│  │ • Tracks synced files to avoid duplicates               │   │
│  └──────────────────────┬──────────────────────────────────┘   │
│                         │                                       │
│                         ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Graphiti Knowledge Graph                                │   │
│  │ • LLM extracts entities from synced content             │   │
│  │ • Creates vector embeddings for semantic search         │   │
│  │ • Maps relationships between concepts                   │   │
│  │ • Preserves temporal context from original capture      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### What Gets Synced

| Memory Category | Synced | Rationale |
|-----------------|--------|-----------|
| `LEARNING/ALGORITHM/` | ✅ Yes | Task execution learnings and insights |
| `LEARNING/SYSTEM/` | ✅ Yes | PAI/tooling learnings |
| `RESEARCH/` | ✅ Yes | Agent research outputs |
| `LEARNING/SIGNALS/` | ❌ No | JSONL format, not markdown |
| `WORK/` | ❌ No | Work tracking, different structure |

### Metadata Mapping

The hook extracts YAML frontmatter from memory files and maps it to the knowledge API:

| Memory Frontmatter | Knowledge API | Purpose |
|---------------------|---------------|---------|
| `capture_type` | `group_id` + `name` prefix | Organizes by type in graph |
| `timestamp` | `reference_timestamp` | Preserves temporal context |
| `session_id` | `source_description` | Links to original session |
| `executor` | `source_description` | Identifies agent/main |
| Markdown body | `episode_body` | Content for entity extraction |

### Manual Sync

You can manually trigger a sync or check status:

```bash
# Sync all unsynced files
bun run ~/.config/pai/hooks/knowledge/sync-memory-to-knowledge.ts

# Dry run (see what would be synced)
bun run ~/.config/pai/hooks/knowledge/sync-memory-to-knowledge.ts --dry-run

# Verbose output
bun run ~/.config/pai/hooks/knowledge/sync-memory-to-knowledge.ts --verbose

# Re-sync all files (including already synced)
bun run ~/.config/pai/hooks/knowledge/sync-memory-to-knowledge.ts --all
```

### Sync State

The hook tracks synced files in `~/.claude/MEMORY/STATE/knowledge-sync/sync-state.json`:

```json
{
  "version": "1.0.0",
  "last_sync": "2026-01-04T10:30:00.000Z",
  "synced_files": [
    {
      "filepath": "/path/to/learning.md",
      "synced_at": "2026-01-04T10:30:00.000Z",
      "episode_uuid": "abc-123",
      "capture_type": "LEARNING",
      "content_hash": "sha256-abc123def456..."
    }
  ]
}
```

**SyncedFile Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `filepath` | string | Absolute path to the synced file |
| `synced_at` | string | ISO timestamp when file was synced |
| `episode_uuid` | string? | UUID of the created episode (if available) |
| `capture_type` | string | Type: LEARNING, RESEARCH, DECISION, etc. |
| `content_hash` | string? | SHA-256 hash of episode_body for content-level deduplication |

### Resilience

The hook is designed for graceful degradation:

- **MCP Offline**: If the knowledge server is unavailable, the hook exits gracefully. Files remain in memory and will be synced on the next session start when MCP is available.
- **Sync Tracking**: Already-synced files are skipped, preventing duplicates.
- **Non-Blocking**: The hook runs asynchronously and won't delay session startup.

---

## Recommended

- **OpenAI API Key** - Required for LLM-based entity extraction and embeddings (get started with $5 credit)
- **Podman** - Container runtime for isolated Graphiti server (or Docker with minor modifications)

---

## Relationships

### Parent Of
*None specified.*

### Child Of
- **Personal AI Infrastructure (PAI)** - Core framework that provides skill system, workflow routing, and tool integration

### Sibling Of
- **PAI Memory System** - Core memory infrastructure that captures learnings, research, and signals
- **PAI Research Skill** - Research workflows that can feed into knowledge graph

### Part Of Collection
- **PAI Core Skills Bundle** - Essential skills for personal AI infrastructure

---

## Changelog

### 1.0.0 - 2025-01-03
- Initial release
- Complete MCP server with Graphiti + FalkorDB
- PAI skill with 7 workflows (Capture, Search, Facts, Recent, Status, Clear, BulkImport)
- Automatic entity extraction and relationship mapping
- Semantic search with vector embeddings
- Temporal context tracking
- End-to-end complete with installation and verification

### 1.0.1 - 2025-01-11
- Added Lucene query sanitization for hyphenated identifiers
- Implemented `src/server/lib/lucene.ts` as the canonical sanitization module
- Fixed CTI/OSINT operations with hyphenated group_ids (e.g., `apt-28`, `tracked-actor-123`)
- Root cause analysis: Hyphens interpreted as negation operators in Lucene syntax
- All special Lucene characters now automatically escaped: `+ - && || ! ( ) { } [ ] ^ " ~ * ? : \ /`

### 1.2.2 - 2026-01-19
- Fixed `search_nodes` formatter to use `labels` array instead of `entity_type` field
- Removed content truncation from all formatters to preserve complete knowledge
- Facts now display full text (was truncated at 70 chars)
- Episodes now display full content (was truncated at 60 chars)
- Node summaries increased to 120 chars for better context
- Token savings maintained: search_nodes 85.5%, search_facts 81.8%, get_episodes 74.4%

### 1.2.1 - 2026-01-19
- Fixed `search_facts` formatter to match actual MCP response structure
- Added support for new fact format (name/fact fields) with legacy fallback
- search_facts now achieves 83.6% token savings (was 0%)
- Version tracking: SKILL.md `version:` field is single source of truth
- Upgrade detection compares SKILL.md version with pack version

### 1.2.0 - 2026-01-18
- Added `knowledge` CLI for token-efficient MCP operations
- New compact output format reduces token usage by up to 70%
- Token metrics tracking with `--metrics` flag for cost monitoring
- Database-aware Lucene sanitization (only applies to FalkorDB backend)
- Consolidated sanitization module at `src/server/lib/lucene.ts`
- Updated all 7 workflows to use the new knowledge CLI
- Added output formatter system (`src/server/lib/output-formatter.ts`)
- Added token metrics system (`src/server/lib/token-metrics.ts`)
- Comprehensive test suite: unit tests for lucene, output-formatter, token-metrics
- Integration benchmark tests for wrapper performance validation
- Renamed MCP wrapper to `knowledge` CLI for clarity
- **Upgrade support**: Version detection and comparison for existing installations
- Automatic backup with manifest before upgrade (stored in `~/.madeinoz-backup/`)
- SKILL.md frontmatter `version:` field is single source of truth for installed version
- Skip reinstall if same version (use `--force` to override)
- Added VERIFY.md Section 3.6 for version verification

### 1.1.0 - 2026-01-13
- Added Neo4j as alternative database backend
- FalkorDB remains the default backend
- Added `docker-compose-neo4j.yml` and `config-neo4j.yaml` for Neo4j deployment
- Updated `install.ts` with database backend selection step
- Added backend-specific container orchestration in `run.ts`
- Neo4j uses native Cypher queries (no Lucene escaping needed)
- Updated all documentation (README, INSTALL, VERIFY) with backend selection
- Conditional Lucene sanitization: only applied for FalkorDB backend
- Added search-all-groups functionality for Neo4j backend
- Enhanced installation and configuration documentation
