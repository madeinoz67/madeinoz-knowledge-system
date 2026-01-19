# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Madeinoz Knowledge System is a personal knowledge management system using Graphiti knowledge graph with Neo4j (default) or FalkorDB backend. It's a PAI (Personal AI Infrastructure) Pack providing automatic entity extraction, relationship mapping, and semantic search for AI conversations and documents.

## Build and Development Commands

```bash
# Build all TypeScript to dist/
bun run build

# Type checking only (no emit)
bun run typecheck

# Development mode
bun run dev

# Run tests
bun test                      # All tests
bun test tests/unit           # Unit tests only
bun test tests/integration    # Integration tests only
bun test --watch              # Watch mode
bun test --coverage           # Coverage report

# Server management
bun run start                 # Start containers
bun run stop                  # Stop containers
bun run status                # Check container status
bun run logs                  # Tail container logs

# Installation and diagnostics
bun run install:system        # Interactive installer
bun run diagnose              # System diagnostics
```

## Architecture

```
src/
├── server/                   # MCP server orchestration
│   ├── run.ts               # Main entry - starts containers (Neo4j or FalkorDB)
│   ├── install.ts           # Interactive installer with backend selection
│   ├── diagnose.ts          # System diagnostics
│   ├── knowledge.ts         # Knowledge CLI (token-efficient wrapper)
│   ├── lib/
│   │   ├── container.ts     # Container manager (Podman/Docker abstraction)
│   │   ├── config.ts        # Config loader and validation
│   │   ├── cli.ts           # CLI utilities
│   │   └── lucene.ts        # Lucene query sanitization for special characters
│   ├── docker-compose.yml         # FalkorDB backend
│   └── docker-compose-neo4j.yml   # Neo4j backend
├── skills/                   # PAI Skill definition
│   ├── SKILL.md             # Main skill with intent routing table
│   ├── workflows/           # 7 workflows: Capture, Search, Facts, Recent, Status, Clear, BulkImport
│   └── tools/               # start.ts, stop.ts, status.ts, logs.ts
├── hooks/                    # Session lifecycle hooks
│   ├── sync-memory-to-knowledge.ts  # Auto-sync from PAI Memory System
│   └── lib/                 # Frontmatter parsing, sync state tracking
└── config/
    └── .env.example         # Complete configuration template
```

## Key Technical Details

**Runtime**: Bun (module type: "module", target: bun)
**TypeScript**: Strict mode enabled, path aliases (`@server/*`, `@lib/*`, `@tools/*`)

**Database Backends**:
- Neo4j (default): Native Cypher queries, no Lucene escaping needed, port 7474/7687
- FalkorDB: Redis-based with RediSearch/Lucene syntax, port 3000/6379

**Lucene Query Sanitization** (`src/server/lib/lucene.ts`):
Special characters (`+ - && || ! ( ) { } [ ] ^ " ~ * ? : \ /`) are automatically escaped for FalkorDB. This is critical for CTI/OSINT data with hyphenated identifiers (e.g., `apt-28`).

**MCP Tools Available**:
- `add_memory` - Store episodes
- `search_memory_nodes` - Entity search
- `search_memory_facts` - Relationship traversal
- `get_episodes` - Temporal retrieval
- `delete_episode`, `delete_entity_edge`, `clear_graph` - Management
- `get_status` - System health

**Configuration**: Uses `MADEINOZ_KNOWLEDGE_*` prefixed environment variables. See `config/.env.example` for full reference including LLM provider options (OpenAI, Anthropic, Google, Groq, OpenRouter).

## LLM Model Compatibility

Tested working with Graphiti: gpt-4o-mini, gpt-4o, Claude 3.5 Haiku, Gemini 2.0 Flash (via OpenRouter)
Known failures: All Llama/Mistral variants (Pydantic validation errors)

## Container Management

Uses Podman or Docker. Network: `madeinoz-knowledge-net` (public bridge). The `container.ts` library abstracts container runtime differences.
