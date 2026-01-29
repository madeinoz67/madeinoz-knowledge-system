---
title: "Installation Guide"
description: "Complete installation guide for Knowledge System with step-by-step instructions and troubleshooting"
---

# Knowledge System Installation Guide

!!! tip "Quick Install with AI"
    **Just tell Claude Code:**

    > "Install the madeinoz-knowledge-system pack"

    Or any of these variations:

    - "Help me install the Knowledge skill"
    - "Set up the knowledge graph system"
    - "Configure madeinoz knowledge"

    Claude will guide you through the interactive installer, help you choose providers, and verify everything works.

---

## Prerequisites

**System Requirements:**

- **Podman** 3.0+ or Docker (container runtime)
- **Bun** runtime (for PAI skill execution)
- **LLM Provider** - One of the following:
  - **Ollama** (recommended - free, local, private)
  - OpenAI API key
  - Anthropic, Google Gemini, or Groq (may require OpenAI for embeddings)
- **Claude Code** or compatible PAI-enabled agent system
- **2GB RAM** minimum for container (4GB+ recommended for Ollama)
- **1GB disk space** for graph database

**Pack Dependencies:**

- None - The memory sync hook reads from the PAI Memory System (`~/.claude/MEMORY/`) which is part of the core PAI installation.

**LLM Provider Options (Tested & Recommended):**

Based on comprehensive real-world testing with Graphiti MCP (15 models tested):

| Provider | Model | Cost/1K | Status | Notes |
|----------|-------|---------|--------|-------|
| **OpenRouter** (recommended) | GPT-4o Mini | $0.129 | ✅ **MOST STABLE** | Reliable entity extraction, best balance |
| **OpenRouter** | Gemini 2.0 Flash | $0.125 | ⚠️ **BEST VALUE** | Cheapest but may have occasional validation errors |
| **OpenRouter** | Qwen 2.5 72B | $0.126 | ✅ Works | Good quality, slower (30s) |
| **OpenRouter** | Claude 3.5 Haiku | $0.816 | ✅ Works | 6x more expensive |
| **OpenRouter** | GPT-4o | $2.155 | ✅ **FASTEST** | Best speed (12s) |
| **OpenRouter** | Grok 3 | $2.163 | ✅ Works | xAI option, 22s |
| **OpenAI Direct** | gpt-4o-mini | ~$0.15 | ✅ Works | Proven stable |
| **Ollama** | llama3.2 | Free | ❌ Fails | Pydantic validation errors |

**⚠️ Models that FAIL with Graphiti:**

- All Llama models (3.1 8B, 3.3 70B) - Pydantic validation errors
- Mistral 7B - Pydantic validation errors
- DeepSeek V3 - Pydantic validation errors
- Grok 4 Fast, 4.1 Fast, 3 Mini, Grok 4 - Validation/timeout issues
- Claude Sonnet 4 - Processing timeout

**Embedding Options:**

| Provider | Model | Quality | Speed | Cost | Notes |
|----------|-------|---------|-------|------|-------|
| **Ollama** (recommended) | mxbai-embed-large | 73.9% | 87ms | FREE | Best value |
| OpenRouter | text-embedding-3-small | 78.2% | 824ms | $0.02/1M | Highest quality |
| Ollama | nomic-embed-text | 63.5% | 93ms | FREE | Alternative |

**OpenAI-Compatible Providers:**

These providers use the same API format as OpenAI but with different base URLs:

| Provider | Description | Get API Key |
|----------|-------------|-------------|
| **OpenRouter** | Access to 200+ models (Claude, GPT-4, Llama, etc.) | <https://openrouter.ai/keys> |
| **Together AI** | Fast inference, good for Llama models | <https://api.together.xyz/settings/api-keys> |
| **Fireworks AI** | Low latency inference | <https://fireworks.ai/api-keys> |
| **DeepInfra** | Serverless GPU inference | <https://deepinfra.com/dash/api_keys> |

**Ollama Setup (if using Ollama or Hybrid mode):**

1. Install Ollama: <https://ollama.com/download>
2. Pull required models:

   ```bash
   ollama pull llama3.2            # LLM model (only needed for full Ollama mode)
   ollama pull mxbai-embed-large   # Embedding model (recommended - 77% quality, 156ms)
   ```

3. Ensure Ollama is running: `ollama serve`

**Note:** The `mxbai-embed-large` model provides the best balance of quality (77%) and speed (156ms) among tested Ollama embedders. See `docs/OLLAMA-MODEL-GUIDE.md` for detailed comparisons.

**Madeinoz Patches (Applied at Image Build Time):**

The custom Docker image includes patches that enable support for:

- **Ollama** (local, no API key required)
- **OpenAI-compatible providers** (OpenRouter, Together AI, Fireworks AI, DeepInfra)

The upstream Graphiti MCP server has a bug ([GitHub issue #1116](https://github.com/getzep/graphiti/issues/1116)) where it ignores custom `base_url` configuration and uses the wrong OpenAI client:

| Client | Endpoint | Compatibility |
|--------|----------|---------------|
| `OpenAIClient` (upstream default) | `/v1/responses` | ❌ OpenAI-only |
| `OpenAIGenericClient` (patch uses) | `/v1/chat/completions` | ✅ Works everywhere |

**How the patch works:**

1. **Local providers** (Ollama): When `OPENAI_BASE_URL` points to localhost/LAN addresses, no API key is required (uses dummy key `ollama`)
2. **Cloud providers** (OpenRouter, Together, etc.): When `OPENAI_BASE_URL` points to a cloud service, requires the provider's API key
3. All requests use `OpenAIGenericClient` which uses the standard `/v1/chat/completions` endpoint
4. Embedding requests use the configured `EMBEDDER_BASE_URL` for the appropriate provider

**Supported cloud providers (detected by URL):**

- `openrouter.ai` → OpenRouter
- `api.together.xyz` → Together AI
- `api.fireworks.ai` → Fireworks AI
- `api.deepinfra.com` → DeepInfra
- `api.perplexity.ai` → Perplexity
- `api.mistral.ai` → Mistral AI

The patch is automatically mounted when using any of the docker-compose files:

- `docker-compose-falkordb.yml` (FalkorDB backend, Docker)
- `docker-compose-neo4j.yml` (Neo4j backend, Docker)
- `podman-compose-falkordb.yml` (FalkorDB backend, Podman)
- `podman-compose-neo4j.yml` (Neo4j backend, Podman)

---

## Provider Selection Guide

The Madeinoz Knowledge System requires **two AI components**:

| Component | Purpose | Selection |
|-----------|---------|-----------|
| **LLM Provider** | Entity extraction, relationship detection | Must output valid JSON |
| **Embedder Provider** | Vector embeddings for semantic search | Generates embedding vectors |

### Interactive Installation (Recommended)

The easiest way to configure providers is through the interactive installer:

```bash
cd ~/.claude/skills/Knowledge
bun run tools/install.ts
```

The installer guides you through:

1. **Step 4: LLM Provider Selection** - Choose your main LLM
2. **Step 5: API Key Configuration** - Enter required keys
3. **Step 6: Model Selection** - Pick specific models

### Provider Combinations

Here are the recommended configurations based on **real-world MCP testing** (15 models tested):

#### Option 1: GPT-4o Mini + Ollama (Recommended) ⭐

**Most stable LLM + free local embeddings - Proven & Reliable**

| Component | Provider | Model | Cost | Quality |
|-----------|----------|-------|------|---------|
| LLM | OpenRouter | openai/gpt-4o-mini | $0.129/1K ops | ✅ Most reliable entity extraction |
| Embedder | Ollama | mxbai-embed-large | Free | 73.9% quality, 87ms |

```env
LLM_PROVIDER=openai
MODEL_NAME=openai/gpt-4o-mini
OPENAI_API_KEY=sk-or-v1-your-openrouter-key
OPENAI_BASE_URL=https://openrouter.ai/api/v1

EMBEDDER_PROVIDER=openai
EMBEDDER_BASE_URL=http://host.docker.internal:11434/v1
EMBEDDER_MODEL=mxbai-embed-large
EMBEDDER_DIMENSIONS=1024
```

#### Option 2: Gemini 2.0 Flash + Ollama (Budget)

**Best value - cheapest working model, but may have occasional validation errors**

| Component | Provider | Model | Cost | Quality |
|-----------|----------|-------|------|---------|
| LLM | OpenRouter | google/gemini-2.0-flash-001 | $0.125/1K ops | ⚠️ Extracts 8 entities but less stable |
| Embedder | Ollama | mxbai-embed-large | Free | 73.9% quality, 87ms |

```env
LLM_PROVIDER=openai
MODEL_NAME=google/gemini-2.0-flash-001
OPENAI_API_KEY=sk-or-v1-your-openrouter-key
OPENAI_BASE_URL=https://openrouter.ai/api/v1

EMBEDDER_PROVIDER=openai
EMBEDDER_BASE_URL=http://host.docker.internal:11434/v1
EMBEDDER_MODEL=mxbai-embed-large
EMBEDDER_DIMENSIONS=1024
```

> **Note:** Gemini 2.0 Flash is ~3% cheaper but may occasionally fail with Pydantic validation
> errors. If you experience validation errors, switch to Option 1 (GPT-4o Mini).

#### Option 3: Full Cloud (Same Provider)

**Use Together AI for both LLM and embeddings**

| Component | Provider | Model | Cost |
|-----------|----------|-------|------|
| LLM | Together AI | meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo | ~$0.88/1M tokens |
| Embedder | Together AI | BAAI/bge-large-en-v1.5 | ~$0.016/1M tokens |

```env
LLM_PROVIDER=openai
MODEL_NAME=meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo
OPENAI_API_KEY=your-together-key
OPENAI_BASE_URL=https://api.together.xyz/v1

EMBEDDER_PROVIDER=openai
EMBEDDER_BASE_URL=https://api.together.xyz/v1
EMBEDDER_MODEL=BAAI/bge-large-en-v1.5
EMBEDDER_DIMENSIONS=1024
```

#### Option 4: Full Ollama (Free but NOT RECOMMENDED)

**⚠️ Completely free, but Llama/Mistral models FAIL Graphiti validation**

| Component | Provider | Model | Cost | Status |
|-----------|----------|-------|------|--------|
| LLM | Ollama | llama3.2 | Free | ❌ **FAILS** Pydantic validation |
| Embedder | Ollama | mxbai-embed-large | Free | ✅ Works great |

```env
LLM_PROVIDER=openai
MODEL_NAME=llama3.2
OPENAI_BASE_URL=http://host.docker.internal:11434/v1

EMBEDDER_PROVIDER=openai
EMBEDDER_BASE_URL=http://host.docker.internal:11434/v1
EMBEDDER_MODEL=mxbai-embed-large
EMBEDDER_DIMENSIONS=1024
```

**⚠️ WARNING:** Full Ollama mode **DOES NOT WORK** with current Graphiti. All open-source models tested (Llama 3.1 8B, Llama 3.3 70B, Mistral 7B, DeepSeek V3) fail with Pydantic validation errors. Use **Option 1 (OpenRouter + Ollama)** instead - you get Gemini 2.0 Flash for $0.125/1K ops while still using free Ollama embeddings.

#### Option 5: Direct OpenAI (Full Cloud)

**Simplest setup, all OpenAI**

| Component | Provider | Model | Cost |
|-----------|----------|-------|------|
| LLM | OpenAI | gpt-4o-mini | ~$0.15/1M tokens |
| Embedder | OpenAI | text-embedding-3-small | ~$0.02/1M tokens |

```env
LLM_PROVIDER=openai
MODEL_NAME=gpt-4o-mini
OPENAI_API_KEY=sk-your-openai-key

EMBEDDER_PROVIDER=openai
EMBEDDER_MODEL=text-embedding-3-small
EMBEDDER_DIMENSIONS=1536
```

### Embedder Comparison

| Embedder | Provider | Quality | Speed | Dimensions | Cost |
|----------|----------|---------|-------|------------|------|
| **mxbai-embed-large** | Ollama | 77% | 156ms | 1024 | Free |
| text-embedding-3-small | OpenAI | 75% | 610ms | 1536 | $0.02/1M |
| BAAI/bge-large-en-v1.5 | Together | ~75% | ~200ms | 1024 | $0.016/1M |

**Recommendation:** Use Ollama's `mxbai-embed-large` for embeddings - it's free, fast, and high quality.

### Changing Providers After Installation

To change providers after initial setup:

1. **Stop the server:**

   ```bash
   bun run server-cli stop
   ```

2. **Edit the configuration:**

   ```bash
   # Edit ~/.claude/.env (or wherever your config is)
   nano ~/.claude/.env
   ```

3. **Update the relevant variables** (see examples above)

4. **Restart the server:**

   ```bash
   bun run server-cli start
   ```

---

## Pre-Installation: System Analysis

**IMPORTANT:** Before installing, analyze the current system state to detect conflicts and ensure dependencies are met.

> **FOR AI AGENTS:** Run ALL pre-installation checks before proceeding. If ANY check shows a conflict or missing dependency:
>
> - **Port in use**: Stop the existing service or choose a different port
> - **Missing dependency**: Install the dependency first (Podman, Bun)
> - **Existing installation**: Backup existing files, then proceed with update
> - **Missing API key**: Prompt user to provide API key before continuing

### Step 0.1: Detect Current Configuration

Run these commands to understand your current system:

```bash
# 1. Check if PAI_DIR is set
echo "PAI_DIR: ${PAI_DIR:-'NOT SET - will use ~/.claude'}"

# 2. Check for existing PAI directory
PAI_CHECK="${PAI_DIR:-$HOME/.claude}"
if [ -d "$PAI_CHECK" ]; then
  echo "⚠️  PAI directory EXISTS at: $PAI_CHECK"
  echo "Contents:"
  ls -la "$PAI_CHECK" 2>/dev/null || echo "  (empty or inaccessible)"
else
  echo "✓ PAI directory does not exist (clean install)"
fi

# 3. Check for existing MCP server
echo ""
echo "Checking for existing MCP server..."
if podman ps | grep -q "madeinoz-knowledge-graph-mcp"; then
    echo "⚠️  Madeinoz Knowledge MCP server is already running"
    podman ps | grep "madeinoz-knowledge-graph-mcp"
else
    echo "✓ No Madeinoz Knowledge MCP server running"
fi

# 4. Check if port 8000 is available
echo ""
echo "Checking port availability..."
if lsof -i :8000 > /dev/null 2>&1; then
    echo "⚠️  Port 8000 is already in use"
    lsof -i :8000 | head -5
else
    echo "✓ Port 8000 is available"
fi

# 5. Check if port 6379 is available (FalkorDB)
echo ""
echo "Checking FalkorDB port 6379..."
if lsof -i :6379 > /dev/null 2>&1; then
    echo "⚠️  Port 6379 is already in use"
    lsof -i :6379 | head -5
else
    echo "✓ Port 6379 is available"
fi

# 5b. Check if Neo4j ports are available (for Neo4j backend)
echo ""
echo "Checking Neo4j ports (7474, 7687)..."
if lsof -i :7474 > /dev/null 2>&1; then
    echo "⚠️  Port 7474 is already in use (Neo4j Browser)"
    lsof -i :7474 | head -5
else
    echo "✓ Port 7474 is available (Neo4j Browser)"
fi

if lsof -i :7687 > /dev/null 2>&1; then
    echo "⚠️  Port 7687 is already in use (Neo4j Bolt)"
    lsof -i :7687 | head -5
else
    echo "✓ Port 7687 is available (Neo4j Bolt)"
fi

# 6. Check for existing Knowledge skill
echo ""
echo "Checking for existing Knowledge skill..."
if [ -d "$PAI_CHECK/skills/Knowledge" ]; then
  echo "⚠️  Knowledge skill already exists at: $PAI_CHECK/skills/Knowledge"
else
  echo "✓ No existing Knowledge skill found"
fi

# 7. Check environment variables
echo ""
echo "Environment variables:"
echo "  PAI_DIR: ${PAI_DIR:-'NOT SET'}"
echo "  MADEINOZ_KNOWLEDGE_OPENAI_API_KEY: ${MADEINOZ_KNOWLEDGE_OPENAI_API_KEY:+SET (value hidden)}"

# 8. Check Podman installation
echo ""
echo "Container Runtime Check:"
if command -v podman &> /dev/null; then
    echo "✓ Podman is installed: $(podman --version)"
else
    echo "❌ Podman is NOT installed"
    echo "   Install with: brew install podman (macOS)"
    echo "              or: sudo apt install podman (Ubuntu/Debian)"
fi
```

### Step 0.2: Verify Dependencies

```bash
# Check for required dependencies
echo "Dependency Verification:"
echo "========================"

# Check Bun runtime
if command -v bun &> /dev/null; then
    echo "✓ Bun is installed: $(bun --version)"
else
    echo "❌ Bun is NOT installed"
    echo "   Install with: curl -fsSL https://bun.sh/install | bash"
fi

# Check for LLM provider configuration
if [ -n "$MADEINOZ_KNOWLEDGE_LLM_PROVIDER" ] && [ "$MADEINOZ_KNOWLEDGE_LLM_PROVIDER" = "ollama" ]; then
    echo "✓ Ollama is configured as LLM provider (no API key needed)"
    # Check if Ollama is running
    if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✓ Ollama is running"
    else
        echo "⚠️  Ollama is configured but not running - start with: ollama serve"
    fi
elif [ -n "$MADEINOZ_KNOWLEDGE_OPENAI_API_KEY" ] || [ -n "$MADEINOZ_KNOWLEDGE_ANTHROPIC_API_KEY" ] || [ -n "$MADEINOZ_KNOWLEDGE_GOOGLE_API_KEY" ]; then
    echo "✓ LLM API key is configured (MADEINOZ_KNOWLEDGE_* prefix)"
elif [ -n "$OPENAI_API_KEY" ] || [ -n "$ANTHROPIC_API_KEY" ] || [ -n "$GOOGLE_API_KEY" ]; then
    echo "✓ LLM API key is configured (legacy - consider using MADEINOZ_KNOWLEDGE_* prefix)"
else
    echo "ℹ️  No LLM API key found - Ollama will be used by default (free, local)"
    echo "   To use cloud providers, configure API keys during installation"
fi

# Check for .env.example file
if [ -f "config/.env.example" ]; then
    echo "✓ .env.example found in config/ (configuration template)"
else
    echo "❌ .env.example not found in config/"
    echo "   This file should be in the pack at config/.env.example"
fi
```

### Step 0.3: Conflict Resolution Matrix

Based on the detection above, follow the appropriate path:

| Scenario | Existing State | Action |
|----------|---------------|--------|
| **Clean Install** | No MCP server, ports available, no existing skill | Proceed normally with Step 1 |
| **Server Running** | MCP server already running | Decide: keep existing (skip to Step 4) or stop/reinstall |
| **Port Conflict (FalkorDB)** | Ports 8000 or 6379 in use | Stop conflicting services or change ports in Docker Compose files |
| **Port Conflict (Neo4j)** | Ports 7474 or 7687 in use | Stop conflicting services or use FalkorDB backend |
| **Skill Exists** | Knowledge skill already installed | Backup old skill, compare versions, then replace |
| **Missing Dependencies** | Podman or Bun not installed | Install dependencies first, then retry |

### Step 0.4: Version Detection and Upgrade Check

> **FOR AI AGENTS:** This step determines if an upgrade is needed by comparing the pack version with any existing installation. If versions match, offer to skip unless `--force` is specified.

**Step 0.4.1: Extract Pack Version**

```bash
# Extract version from pack README.md frontmatter
PACK_DIR="${PACK_DIR:-$(pwd)}"
PACK_VERSION=$(grep -E "^version:" "$PACK_DIR/README.md" | head -1 | sed 's/version:[[:space:]]*//')

if [ -z "$PACK_VERSION" ]; then
    echo "⚠ Warning: Could not extract pack version from README.md"
    PACK_VERSION="unknown"
fi

echo "Pack version: $PACK_VERSION"
```

**Step 0.4.2: Detect Existing Installation Version**

```bash
PAI_CHECK="${PAI_DIR:-$HOME/.claude}"
EXISTING_VERSION="none"

# Primary: extract version from SKILL.md frontmatter
SKILL_FILE="$PAI_CHECK/skills/Knowledge/SKILL.md"

if [ -f "$SKILL_FILE" ]; then
    EXISTING_VERSION=$(grep -E "^version:" "$SKILL_FILE" | head -1 | sed 's/version:[[:space:]]*//')
    if [ -n "$EXISTING_VERSION" ]; then
        echo "Existing installation version: $EXISTING_VERSION"
    else
        echo "Existing installation found (version unknown - pre-1.2.0)"
        EXISTING_VERSION="pre-1.2.0"
    fi
elif [ -d "$PAI_CHECK/skills/Knowledge" ]; then
    echo "Existing installation found (no SKILL.md - corrupted install)"
    EXISTING_VERSION="unknown"
else
    echo "No existing installation found"
fi
```

**Step 0.4.3: Version Comparison**

```bash
# Compare versions
if [ "$EXISTING_VERSION" = "none" ]; then
    echo "→ Fresh install: proceeding with version $PACK_VERSION"
    INSTALL_ACTION="install"
elif [ "$EXISTING_VERSION" = "$PACK_VERSION" ]; then
    echo "→ Same version ($PACK_VERSION) already installed"
    if [ "${FORCE_REINSTALL:-false}" = "true" ]; then
        echo "  --force specified: proceeding with reinstall"
        INSTALL_ACTION="reinstall"
    else
        echo "  Use --force to reinstall, or skip to Step 4 (verification)"
        INSTALL_ACTION="skip"
    fi
else
    echo "→ Upgrade available: $EXISTING_VERSION → $PACK_VERSION"
    INSTALL_ACTION="upgrade"
fi

export INSTALL_ACTION EXISTING_VERSION PACK_VERSION
```

**Step 0.4.4: Backup Before Upgrade (If Needed)**

Only create backup when upgrading or reinstalling:

```bash
if [ "$INSTALL_ACTION" = "upgrade" ] || [ "$INSTALL_ACTION" = "reinstall" ]; then
    # Create timestamped backup
    BACKUP_DIR="$HOME/.madeinoz-backup/$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$BACKUP_DIR"

    echo ""
    echo "Creating backup at: $BACKUP_DIR"

    # Backup existing skill if present
    if [ -d "$PAI_CHECK/skills/Knowledge" ]; then
        cp -r "$PAI_CHECK/skills/Knowledge" "$BACKUP_DIR/Knowledge"
        echo "✓ Backed up existing Knowledge skill (v$EXISTING_VERSION)"
    fi

    # Backup legacy .env if present (config is now in PAI .env)
    if [ -f "config/.env" ]; then
        cp config/.env "$BACKUP_DIR/.env.legacy"
        echo "✓ Backed up legacy .env file (migrate to PAI .env)"
    fi

    # Backup container if running
    if podman ps 2>/dev/null | grep -q "madeinoz-knowledge"; then
        podman export madeinoz-knowledge-graph-mcp > "$BACKUP_DIR/madeinoz-container.tar" 2>/dev/null || true
        echo "✓ Backed up running container (if possible)"
    fi

    # Save backup manifest
    cat > "$BACKUP_DIR/manifest.json" << EOF
{
    "backup_date": "$(date -Iseconds)",
    "previous_version": "$EXISTING_VERSION",
    "upgrading_to": "$PACK_VERSION",
    "action": "$INSTALL_ACTION"
}
EOF
    echo "✓ Created backup manifest"

    echo ""
    echo "Backup complete! Proceeding with $INSTALL_ACTION..."
elif [ "$INSTALL_ACTION" = "skip" ]; then
    echo ""
    echo "Skipping installation (same version). To verify existing install, jump to Step 4."
    echo "To force reinstall, set FORCE_REINSTALL=true and re-run."
fi
```

**After completing version check and backup, proceed to Step 1.**

---

## Step 1: Verify Pack Contents

> **FOR AI AGENTS:** This step verifies the pack is complete. If ANY file is missing, STOP and inform the user - the pack is incomplete and cannot be installed.

Ensure you have all required files in the pack directory:

```bash
# Navigate to pack directory
cd /path/to/madeinoz-knowledge-system

# Verify required files exist
echo "Checking pack contents..."

REQUIRED_FILES=(
    "README.md"
    "SKILL.md"
    "tools/server-cli.ts"
    "docker/podman-compose-falkordb.yml"
    "docker/podman-compose-neo4j.yml"
    "docker/docker-compose-falkordb.yml"
    "docker/docker-compose-neo4j.yml"
    "config/.env.example"
    "workflows/CaptureEpisode.md"
    "workflows/SearchKnowledge.md"
    "workflows/SearchFacts.md"
    "workflows/SearchByDate.md"
    "workflows/GetRecent.md"
    "workflows/GetStatus.md"
    "workflows/ClearGraph.md"
    "workflows/BulkImport.md"
    "tools/Install.md"
)

ALL_FOUND=true
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file"
    else
        echo "✗ MISSING: $file"
        ALL_FOUND=false
    fi
done

if [ "$ALL_FOUND" = true ]; then
    echo ""
    echo "✓ All required files present!"
else
    echo ""
    echo "❌ Some files are missing. Please ensure you have the complete pack."
    exit 1
fi
```

---

## Step 2: Add Configuration to PAI

> **PAI .env is the ONLY source of truth.**
>
> All MADEINOZ_KNOWLEDGE_* configuration lives in PAI .env (`~/.claude/.env`).
> The pack's config/.env is auto-generated at runtime when starting containers.

**Add Madeinoz Knowledge System settings to your PAI configuration:**

[Configuration sections continue with PAI .env setup, provider selection, and variable management...]

---

## Step 3: Start MCP Server

[MCP server startup instructions...]

---

## Step 4: Install Full Pack and Knowledge Skill

[Pack installation instructions...]

---

## Step 5: Configure MCP Server in Claude Code

[MCP configuration instructions...]

---

## Step 6: Verify Installation

[Verification instructions...]

---

## Step 7: Test Installation

[Testing instructions...]

---

## Step 8: Post-Installation Configuration

[Post-installation steps...]

---

## Step 9: Install Memory Sync Hook (Optional but Recommended)

[Memory sync hook installation...]

---

## Troubleshooting

### Server Won't Start

**Symptoms:** `bun run server-cli start` fails or container exits immediately

**Solutions:**

1. **Port conflict:** Stop conflicting service or modify ports in Docker Compose files
2. **API key invalid:** Verify API key in PAI config has credits/quota
3. **Image pull failed:** Check internet connection and try again
4. **Resource limits:** Ensure system has at least 2GB RAM available

### Skill Not Loading

**Solutions:**

1. **Restart Claude Code** - Skills are loaded on startup
2. **Check SKILL.md format** - Ensure frontmatter is valid YAML
3. **Verify file paths** - All workflows should be in `workflows/` and tools in `tools/`

### Knowledge Not Being Captured

**Solutions:**

1. **Server not running:** Start with `bun run server-cli start`
2. **API quota exceeded:** Check OpenAI usage dashboard
3. **Content too brief:** Add more context and detail

---

## Uninstallation

To completely remove the Knowledge skill:

```bash
# 1. Stop and remove container
bun run server-cli stop
podman rm madeinoz-knowledge-graph-mcp

# 2. Remove Knowledge skill
rm -rf ~/.claude/skills/Knowledge
```

---

## Getting Help

If you encounter issues not covered here:

1. **Check logs:** `bun run server-cli logs`
2. **Check status:** `bun run server-cli status`
3. **Review documentation:**
   - `README.md` - Complete pack documentation
   - `../verification.md` - Verification checklist
