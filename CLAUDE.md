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
- Python 3.11+ (MCP server patches), TypeScript/Bun (CLI tools) + Docling (PDF parsing), Qdrant Python client, Ollama Python SDK, FastMCP (023-qdrant-rag)
- Qdrant vector database (Docker container, 69MB image, port 6333, persistent volume) (023-qdrant-rag)
- Python 3.11+ (MCP server), TypeScript/Bun (CLI) + FastMCP (Python), Graphiti Core (knowledge graph), mcp-client (TypeScript) (020-investigative-search)
- Neo4j (default) or FalkorDB with graph traversal support (020-investigative-search)
- Python 3.11+ + OpenTelemetry Prometheus exporter, threading.Lock for thread safety (017-queue-metrics)
- PromQL (Prometheus Query Language), JSON (Grafana dashboard format) + Grafana 10.x, Prometheus (016-prometheus-dashboard-fixes)

## Recent Changes
- 023-qdrant-rag: Qdrant migration - replaced RAGFlow (3.5GB+) with Qdrant (69MB), Docling + semantic chunking, Ollama embeddings
- 022-self-hosted-rag: Local Knowledge Augmentation Platform (LKAP) - document ingestion, semantic search, knowledge promotion
- 017-queue-metrics: Queue processing metrics for monitoring queue depth, latency, consumer health, and failure tracking

## LKAP - Local Knowledge Augmentation Platform (Feature 022/023)

LKAP adds RAG (Retrieval-Augmented Generation) capabilities to the knowledge graph system using Qdrant as the vector database. It provides a two-tier memory model: Document Memory (transient, high-volume) and Knowledge Memory (durable, curated).

### Environment Variables

```bash
# Qdrant Configuration (Feature 023)
MADEINOZ_KNOWLEDGE_QDRANT_URL=http://localhost:6333
MADEINOZ_KNOWLEDGE_QDRANT_API_KEY=                        # Optional authentication
MADEINOZ_KNOWLEDGE_QDRANT_COLLECTION=lkap_documents        # Collection name
MADEINOZ_KNOWLEDGE_QDRANT_EMBEDDING_DIMENSION=1024         # bge-large-en-v1.5
MADEINOZ_KNOWLEDGE_QDRANT_CONFIDENCE_THRESHOLD=0.70        # Minimum confidence
MADEINOZ_KNOWLEDGE_QDRANT_CHUNK_SIZE_MIN=512
MADEINOZ_KNOWLEDGE_QDRANT_CHUNK_SIZE_MAX=768
MADEINOZ_KNOWLEDGE_QDRANT_CHUNK_OVERLAP=100
MADEINOZ_KNOWLEDGE_QDRANT_LOG_LEVEL=INFO

# Ollama Configuration (for local embeddings)
MADEINOZ_KNOWLEDGE_OLLAMA_BASE_URL=http://localhost:11434
MADEINOZ_KNOWLEDGE_OLLAMA_EMBEDDING_MODEL=bge-large-en-v1.5
```

### Docker Commands

```bash
# Start Qdrant vector database (69MB image)
docker compose -f docker/docker-compose-qdrant.yml up -d

# Start Ollama (optional - for fully local embeddings)
docker compose -f docker/docker-compose-ollama.yml up -d

# Full LKAP stack (Neo4j + Qdrant + Ollama)
docker compose -f src/skills/server/docker-compose-neo4j.yml up -d
docker compose -f docker/docker-compose-qdrant.yml up -d
docker compose -f docker/docker-compose-ollama.yml up -d
```

### Usage Examples

```bash
# CLI wrapper for Qdrant operations
bun run src/skills/server/lib/rag-cli.ts search "GPIO configuration"
bun run src/skills/server/lib/rag-cli.ts get-chunk <chunk-id>
bun run src/skills/server/lib/rag-cli.ts ingest knowledge/inbox/
bun run src/skills/server/lib/rag-cli.ts health

# MCP Tools (available to Claude)
rag.search(query, filters, topK)       # Semantic search across documents
rag.getChunk(chunkId)                  # Retrieve specific chunk by ID
rag.ingest(path)                       # Ingest documents from path
rag.health()                           # Check Qdrant connectivity
kg.promoteFromEvidence(evidenceId)     # Promote fact from evidence
kg.getProvenance(factId)               # Trace fact to source documents
```

### Document Storage

- **Inbox**: `knowledge/inbox/` - Drop PDFs, markdown, text files here for automatic ingestion
- **Processed**: `knowledge/processed/` - Canonical storage after successful ingestion

### Architecture

```
LKAP Two-Tier Memory Model:
┌─────────────────────────────────────────────────────────────┐
│ Document Memory (Qdrant)                                    │
│ - 69MB Docker image, 626 QPS, port 6333                     │
│ - Semantic search with cosine similarity                    │
│ - Chunks: 512-768 tokens, 10-20% overlap, heading-aware     │
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
| Ingest documents | `bun run rag-cli.ts ingest <path>` |
| Check health | `bun run rag-cli.ts health` |
| Start Qdrant | `docker compose -f docker/docker-compose-qdrant.yml up -d` |

### Two-Tier Memory Model

1. **Document Memory (RAG)**: Fast semantic search across PDFs, markdown, and text documents. Returns relevant chunks with citations and confidence scores. Best for exploring new information and finding evidence.

2. **Knowledge Memory (KG)**: Durable, typed facts extracted from documents and promoted to the knowledge graph. Includes provenance links to source documents. Best for verified constraints, errata, APIs, and other high-signal information.

See [docs/usage/lkap-quickstart.md](docs/usage/lkap-quickstart.md) for the complete quickstart guide.
