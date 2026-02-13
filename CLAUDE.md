# madeinoz-knowledge-system Development Guidelines

Personal knowledge management system using Graphiti knowledge graph with Neo4j/FalkorDB.

## Quick Reference

| Resource | Location |
|----------|----------|
| Full docs | `docs/` or https://madeinoz67.github.io/madeinoz-knowledge-system/ |
| Memory Decay | `docs/usage/memory-decay.md` |
| LKAP Quickstart | `docs/usage/lkap-quickstart.md` |
| Configuration | `docs/reference/configuration.md` |
| CLI Reference | `docs/reference/cli.md` |
| Observability | `docs/reference/observability.md` |

## Commands

```bash
bun run build              # Build TypeScript
bun run typecheck          # Type check only
bun test                   # Run tests
bun run server-cli start   # Start containers
bun run server-cli stop    # Stop containers
bun run server-cli status  # Check status
```

## Architecture

```
src/
├── server/           # MCP server orchestration, container management
├── skills/           # PAI Skill definition and workflows
├── hooks/            # Session lifecycle hooks (memory sync)
└── config/           # Environment configuration

docker/
├── patches/          # Python MCP server code (graphiti patches)
└── Dockerfile        # Container build

config/
├── decay-config.yaml # Memory decay settings (180-day half-life)
└── sync-sources.json # Memory sync configuration
```

## Technical Details

- **Runtime**: Bun (ES modules, target: bun)
- **TypeScript**: Strict mode, path aliases (`@server/*`, `@lib/*`)
- **Database**: Neo4j (default, port 7474/7687) or FalkorDB (port 3000/6379)
- **Python**: 3.11+ in container for MCP server patches

**LLM Compatibility**:
- Working: gpt-4o-mini, gpt-4o, Claude 3.5 Haiku, Gemini 2.0 Flash
- Failing: All Llama/Mistral variants (Pydantic validation errors)

## Container Development (CRITICAL)

After modifying `docker/patches/*.py`, you MUST rebuild:

```bash
docker build -f docker/Dockerfile -t madeinoz-knowledge-system:local .
bun run server-cli stop
bun run server-cli start --dev
```

**If changes don't appear**: Docker caching issue. Stop containers fully before restart.

## CLI Profile Usage (CRITICAL)

**MUST use `--profile development` when testing against dev containers.**

```bash
# CORRECT - testing against dev containers
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts --profile development health
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts --profile development run_maintenance

# WRONG - omitting profile hits PRODUCTION data
bun run ~/.claude/skills/Knowledge/tools/knowledge-cli.ts health
```

| Profile | Container | Use Case |
|---------|-----------|----------|
| `production` (default) | Production | Live data |
| `development` | `--dev` containers | Testing |

**Rules**: Never reconfigure profiles. Always pass `--profile development` for dev work.

## Releases (CRITICAL)

**⚠️ NEVER use `gh release create` directly** - it creates the tag via GitHub API without triggering the CI workflow. The release job will never run, leaving you with a broken release (no Docker image pushed, no docs deployed).

**Release checklist - follow these steps exactly:**

```bash
# === PRE-RELEASE CHECKS ===
# 1. Check you're on main branch
git branch --show-current  # Should output: main

# 2. Pull latest changes
git pull origin main

# 3. Verify working tree is clean (no uncommitted changes)
git status  # Should show: "nothing to commit, working tree clean"

# 4. Verify latest CI passed
gh run list --limit 1  # Check status is "completed success"

# === CREATE RELEASE ===
# 5. Create annotated tag with release description
git tag -a v1.x.x -m "Release v1.x.x" -m "Description of what's in this release"
# Or for multi-line descriptions, omit -m to open your editor:
git tag -a v1.x.x
# Then write your description in the editor (same format as commit messages)

# 6. Push tag to trigger CI workflow
git push origin v1.x.x

# === VERIFY RELEASE ===
# 7. Watch workflow run
gh run watch

# 8. Confirm release created
gh release view v1.x.x
```

**What the CI workflow does automatically:**
- Generates changelog from git-cliff using conventional commits
- Updates CHANGELOG.md on main branch
- Builds and pushes multi-arch Docker image to GHCR
- Creates GitHub Release with formatted release notes
- Deploys documentation to GitHub Pages

**Recovering from a bad release:**

```bash
# If you accidentally used gh release create or created via web UI:
gh release delete v1.x.x --yes
git tag -d v1.x.x
git push origin :refs/tags/v1.x.x
# Then follow the correct process above
```

**Why this matters:** The release job (`.github/workflows/ci.yml:195`) only triggers on `push` events for tags matching `v*`. Tags created via GitHub web UI or `gh release create` generate a `ReleaseEvent`, not a `push` event, so the workflow never runs.

## Active Technologies
- JSON (Grafana dashboard configuration) + Grafana (provisioned), Prometheus (data source), existing metrics from PR #34 (013-prompt-cache-dashboard)
- N/A (dashboard configuration only) (013-prompt-cache-dashboard)
- Python 3.11+ + OpenTelemetry Prometheus exporter, Graphiti MCP server (015-memory-access-metrics)
- Neo4j / FalkorDB (existing graph database) (015-memory-access-metrics)
- PromQL (Prometheus Query Language), JSON (Grafana dashboard format) + Grafana 10.x, Prometheus (scraping OpenTelemetry metrics) (016-prometheus-dashboard-fixes)
- Python 3.11+ + OpenTelemetry Prometheus exporter, threading.Lock for thread safety, Grafana dashboard JSON (017-queue-metrics)
- Python 3.11+ (MCP server), TypeScript/Bun (CLI) + FastMCP (Python), Graphiti Core (knowledge graph), mcp-client (TypeScript) (020-investigative-search)
- Neo4j (default) or FalkorDB with graph traversal suppor (020-investigative-search)
- Python 3.11+ (Docker container for MCP server), Bun/TypeScript (CLI tools) + Docling (PDF ingestion), RAGFlow (vector DB + search), Ollama (local embeddings/LLM), Graphiti (knowledge graph), FastMCP (MCP protocol) (022-self-hosted-rag)
- Neo4j (default) or FalkorDB (knowledge graph), RAGFlow vector DB (embeddings), Local filesystem (documents: inbox/, processed/) (022-self-hosted-rag)
- Python 3.11+ (Docker container for MCP server), Bun/TypeScript (CLI tools) + Docling (PDF ingestion), RAGFlow (vector DB + search), Ollama (local embeddings/LLM, optional), Graphiti (knowledge graph), FastMCP (MCP protocol) (022-self-hosted-rag)

## Recent Changes
- 022-self-hosted-rag: Local Knowledge Augmentation Platform (LKAP) - RAGFlow vector database, Ollama embeddings, document ingestion, semantic search
- 017-queue-metrics: Queue processing metrics for monitoring queue depth, latency, consumer health, and failure tracking
- 013-prompt-cache-dashboard: Added JSON (Grafana dashboard configuration) + Grafana (provisioned), Prometheus (data source), existing metrics from PR #34

## LKAP - Local Knowledge Augmentation Platform (Feature 022)

LKAP adds RAG (Retrieval-Augmented Generation) capabilities to the knowledge graph system. It provides a two-tier memory model: Document Memory (transient, high-volume) and Knowledge Memory (durable, curated).

### Environment Variables

```bash
# RAGFlow Configuration
MADEINOZ_KNOWLEDGE_RAGFLOW_API_URL=http://ragflow:9380
MADEINOZ_KNOWLEDGE_RAGFLOW_API_KEY=                    # Optional authentication
MADEINOZ_KNOWLEDGE_RAGFLOW_EMBEDDING_DIMENSION=1024     # 1024+ recommended
MADEINOZ_KNOWLEDGE_RAGFLOW_EMBEDDING_MODEL=ollama       # ollama or openai
MADEINOZ_KNOWLEDGE_RAGFLOW_CONFIDENCE_THRESHOLD=0.70    # Minimum confidence for results
MADEINOZ_KNOWLEDGE_RAGFLOW_CHUNK_SIZE_MIN=512
MADEINOZ_KNOWLEDGE_RAGFLOW_CHUNK_SIZE_MAX=768
MADEINOZ_KNOWLEDGE_RAGFLOW_CHUNK_OVERLAP=100
MADEINOZ_KNOWLEDGE_RAGFLOW_LOG_LEVEL=INFO

# OpenRouter API Key (for OpenAI text-embedding-3-large)
MADEINOZ_KNOWLEDGE_OPENROUTER_API_KEY=sk-your-openrouter-key

# Ollama Configuration (optional - for fully local operation)
MADEINOZ_KNOWLEDGE_OLLAMA_BASE_URL=http://ollama:11434
MADEINOZ_KNOWLEDGE_OLLAMA_EMBEDDING_MODEL=bge-large-en-v1.5
MADEINOZ_KNOWLEDGE_OLLAMA_MODELS=bge-large-en-v1.5
MADEINOZ_KNOWLEDGE_OLLAMA_NUM_GPU=0
MADEINOZ_KNOWLEDGE_OLLAMA_NUM_THREAD=4
```

### Docker Commands

```bash
# Start RAGFlow vector database
docker compose -f docker/docker-compose-ragflow.yml up -d

# Start Ollama (optional - for fully local embeddings)
docker compose -f docker/docker-compose-ollama.yml up -d

# Full LKAP stack (Neo4j + RAGFlow + Ollama)
docker compose -f src/skills/server/docker-compose-neo4j.yml up -d
docker compose -f docker/docker-compose-ragflow.yml up -d
docker compose -f docker/docker-compose-ollama.yml up -d
```

### Usage Examples

```bash
# CLI wrapper for RAGFlow operations
bun run src/skills/server/lib/rag-cli.ts search "GPIO configuration"
bun run src/skills/server/lib/rag-cli.ts get-chunk <chunk-id>
bun run src/skills/server/lib/rag-cli.ts list
bun run src/skills/server/lib/rag-cli.ts health

# MCP Tools (available to Claude)
rag.search(query, filters, topK)       # Semantic search across documents
rag.getChunk(chunkId)                  # Retrieve specific chunk by ID
kg.promoteFromEvidence(evidenceId)     # Promote fact from evidence
kg.promoteFromQuery(query)             # Search and promote in one operation
kg.getProvenance(factId)               # Trace fact to source documents
```

### Document Storage

- **Inbox**: `knowledge/inbox/` - Drop PDFs, markdown, text files here for automatic ingestion
- **Processed**: `knowledge/processed/` - Canonical storage after successful ingestion

### Architecture

```
LKAP Two-Tier Memory Model:
┌─────────────────────────────────────────────────────────────┐
│ Document Memory (RAGFlow)                                   │
│ - High-volume, versioned, citation-centric                  │
│ - Semantic search with confidence scores                    │
│ - Chunks: 512-768 tokens, heading-aware                    │
├─────────────────────────────────────────────────────────────┤
│ Knowledge Memory (Graphiti)                                 │
│ - Low-volume, high-signal, typed                            │
│ - Evidence-backed facts with provenance                     │
│ - Conflict-aware, version-aware                             │
└─────────────────────────────────────────────────────────────┘
```

### Quick Reference

| Task | Command |
|------|---------|
| Search documents | `bun run rag-cli.ts search "<query>"` |
| Get chunk details | `bun run rag-cli.ts get-chunk <id>` |
| List documents | `bun run rag-cli.ts list` |
| Check health | `bun run rag-cli.ts health` |
| Start RAGFlow | `docker compose -f docker/docker-compose-ragflow.yml up -d` |

### Two-Tier Memory Model

1. **Document Memory (RAG)**: Fast semantic search across PDFs, markdown, and text documents. Returns relevant chunks with citations and confidence scores. Best for exploring new information and finding evidence.

2. **Knowledge Memory (KG)**: Durable, typed facts extracted from documents and promoted to the knowledge graph. Includes provenance links to source documents. Best for verified constraints, errata, APIs, and other high-signal information.

See [docs/usage/lkap-quickstart.md](docs/usage/lkap-quickstart.md) for the complete quickstart guide.
