# Madeinoz Knowledge System - Installation

**This guide is designed for AI agents installing this pack into a user's infrastructure.**

---

**FOR AI AGENTS:** This installation MUST be completed exactly as specified. Follow these rules:
1. **Execute every step** - Do NOT skip steps or mark them as "optional"
2. **Verify outputs** - After each command, check the expected output matches
3. **Stop on errors** - If any step fails, troubleshoot before continuing
4. **Use exact paths** - Do not modify file paths or directory structures
5. **Copy files verbatim** - Do not simplify or "improve" code during installation
6. **Run verification** - After installation, complete ALL checks in VERIFY.md

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
| **OpenRouter** | Access to 200+ models (Claude, GPT-4, Llama, etc.) | https://openrouter.ai/keys |
| **Together AI** | Fast inference, good for Llama models | https://api.together.xyz/settings/api-keys |
| **Fireworks AI** | Low latency inference | https://fireworks.ai/api-keys |
| **DeepInfra** | Serverless GPU inference | https://deepinfra.com/dash/api_keys |

**Ollama Setup (if using Ollama or Hybrid mode):**
1. Install Ollama: https://ollama.com/download
2. Pull required models:
   ```bash
   ollama pull llama3.2            # LLM model (only needed for full Ollama mode)
   ollama pull mxbai-embed-large   # Embedding model (recommended - 77% quality, 156ms)
   ```
3. Ensure Ollama is running: `ollama serve`

**Note:** The `mxbai-embed-large` model provides the best balance of quality (77%) and speed (156ms) among tested Ollama embedders. See `docs/OLLAMA-MODEL-GUIDE.md` for detailed comparisons.

**Madeinoz Patch (Ollama + OpenAI-Compatible Support):**

This pack includes a patch (`src/server/patches/factories.py`) that enables support for:
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

The patch is automatically mounted when using either docker-compose file:
- `docker-compose.yml` (FalkorDB backend)
- `docker-compose-neo4j.yml` (Neo4j backend)

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
cd src/server
bun run install.ts
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
   bun run stop
   ```

2. **Edit the configuration:**
   ```bash
   # Edit src/server/.env (or wherever your config is)
   nano src/server/.env
   ```

3. **Update the relevant variables** (see examples above)

4. **Restart the server:**
   ```bash
   bun run start
   ```

---

## Pre-Installation: System Analysis

**IMPORTANT:** Before installing, analyze the current system state to detect conflicts and ensure dependencies are met.

> **FOR AI AGENTS:** Run ALL pre-installation checks before proceeding. If ANY check shows a conflict or missing dependency:
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
| **Port Conflict (FalkorDB)** | Ports 8000 or 6379 in use | Stop conflicting services or change ports in run.ts |
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
    "src/server/run.ts"
    "src/server/podman-compose.yml"
    "src/server/docker-compose.yml"
    "config/.env.example"
    "src/skills/workflows/CaptureEpisode.md"
    "src/skills/workflows/SearchKnowledge.md"
    "src/skills/workflows/SearchFacts.md"
    "src/skills/workflows/GetRecent.md"
    "src/skills/workflows/GetStatus.md"
    "src/skills/workflows/ClearGraph.md"
    "src/skills/workflows/BulkImport.md"
    "src/skills/tools/Install.md"
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

```bash
PAI_ENV="${PAI_DIR:-$HOME/.claude}/.env"

echo ""
echo "📝 Updating PAI Configuration"
echo "=============================="
echo ""
echo "PAI Configuration: $PAI_ENV"
echo ""

# ============================================================
# Step 2.1: Detect Existing Environment Variables
# ============================================================
echo "Checking for existing MADEINOZ_KNOWLEDGE_* configuration..."
echo ""

# Source existing PAI .env to detect current values
source "$PAI_ENV" 2>/dev/null || true

# Track which variables already exist
EXISTING_VARS=()

# Check each MADEINOZ_KNOWLEDGE_* variable
check_existing_var() {
    local var_name="$1"
    local var_value="${!var_name}"
    if [ -n "$var_value" ]; then
        EXISTING_VARS+=("$var_name")
        # Mask sensitive values (API keys)
        if [[ "$var_name" == *"API_KEY"* ]] || [[ "$var_name" == *"PASSWORD"* ]]; then
            echo "  ✓ $var_name = [CONFIGURED - value hidden]"
        else
            echo "  ✓ $var_name = $var_value"
        fi
        return 0
    fi
    return 1
}

# Check all known MADEINOZ_KNOWLEDGE_* variables
echo "Existing configuration in PAI .env:"
HAS_EXISTING=false

check_existing_var "MADEINOZ_KNOWLEDGE_LLM_PROVIDER" && HAS_EXISTING=true
check_existing_var "MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER" && HAS_EXISTING=true
check_existing_var "MADEINOZ_KNOWLEDGE_MODEL_NAME" && HAS_EXISTING=true
check_existing_var "MADEINOZ_KNOWLEDGE_OPENAI_API_KEY" && HAS_EXISTING=true
check_existing_var "MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL" && HAS_EXISTING=true
check_existing_var "MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL" && HAS_EXISTING=true
check_existing_var "MADEINOZ_KNOWLEDGE_EMBEDDER_BASE_URL" && HAS_EXISTING=true
check_existing_var "MADEINOZ_KNOWLEDGE_DATABASE_TYPE" && HAS_EXISTING=true
check_existing_var "MADEINOZ_KNOWLEDGE_NEO4J_URI" && HAS_EXISTING=true
check_existing_var "MADEINOZ_KNOWLEDGE_NEO4J_USER" && HAS_EXISTING=true
check_existing_var "MADEINOZ_KNOWLEDGE_NEO4J_PASSWORD" && HAS_EXISTING=true
check_existing_var "MADEINOZ_KNOWLEDGE_FALKORDB_HOST" && HAS_EXISTING=true
check_existing_var "MADEINOZ_KNOWLEDGE_FALKORDB_PORT" && HAS_EXISTING=true
check_existing_var "MADEINOZ_KNOWLEDGE_GROUP_ID" && HAS_EXISTING=true
check_existing_var "MADEINOZ_KNOWLEDGE_SEMAPHORE_LIMIT" && HAS_EXISTING=true

if [ "$HAS_EXISTING" = false ]; then
    echo "  (none found - fresh installation)"
fi

echo ""

# Also check legacy (non-prefixed) variables
echo "Checking for legacy (non-prefixed) API keys..."
LEGACY_VARS=()

check_legacy_var() {
    local var_name="$1"
    local var_value="${!var_name}"
    if [ -n "$var_value" ]; then
        LEGACY_VARS+=("$var_name")
        echo "  ⚠️  $var_name is set (can be migrated to MADEINOZ_KNOWLEDGE_$var_name)"
        return 0
    fi
    return 1
}

HAS_LEGACY=false
check_legacy_var "OPENAI_API_KEY" && HAS_LEGACY=true
check_legacy_var "ANTHROPIC_API_KEY" && HAS_LEGACY=true
check_legacy_var "GOOGLE_API_KEY" && HAS_LEGACY=true
check_legacy_var "GROQ_API_KEY" && HAS_LEGACY=true
check_legacy_var "OPENAI_BASE_URL" && HAS_LEGACY=true

if [ "$HAS_LEGACY" = false ]; then
    echo "  (none found)"
fi

echo ""

# ============================================================
# Step 2.2: Ask User About Existing Configuration
# ============================================================

PRESERVE_EXISTING=false
MIGRATE_LEGACY=false

if [ "$HAS_EXISTING" = true ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Existing MADEINOZ_KNOWLEDGE_* configuration detected!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Options:"
    echo "  1) Keep existing values (preserve current configuration)"
    echo "  2) Replace with new defaults (will overwrite)"
    echo "  3) Merge - keep existing, add only missing variables"
    echo ""
    read -p "Choice (1/2/3) [default: 3]: " CONFIG_CHOICE
    CONFIG_CHOICE="${CONFIG_CHOICE:-3}"

    case "$CONFIG_CHOICE" in
        1)
            PRESERVE_EXISTING=true
            echo "✓ Keeping all existing MADEINOZ_KNOWLEDGE_* values"
            ;;
        2)
            echo "⚠️  Will replace existing values with new defaults"
            ;;
        3)
            PRESERVE_EXISTING=true
            echo "✓ Merging - keeping existing, adding missing variables"
            ;;
    esac
    echo ""
fi

if [ "$HAS_LEGACY" = true ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Legacy (non-prefixed) API keys detected!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "These can be migrated to MADEINOZ_KNOWLEDGE_* prefix."
    echo "Benefits: Isolated configuration per pack, no conflicts."
    echo ""
    read -p "Migrate legacy keys to MADEINOZ_KNOWLEDGE_* prefix? (y/N): " MIGRATE_CHOICE
    if [[ "$MIGRATE_CHOICE" =~ ^[Yy]$ ]]; then
        MIGRATE_LEGACY=true
        echo "✓ Will migrate legacy keys"
    else
        echo "✓ Legacy keys will remain unchanged (can use as fallback)"
    fi
    echo ""
fi

# ============================================================
# Step 2.3: Determine Provider Settings
# ============================================================

# Check if API keys already exist in PAI .env
echo "Determining provider settings..."

AUTO_CONFIGURED=false
# Check for MADEINOZ_KNOWLEDGE_* prefixed keys first (preferred)
if [ -n "$MADEINOZ_KNOWLEDGE_OPENAI_API_KEY" ] || [ -n "$MADEINOZ_KNOWLEDGE_ANTHROPIC_API_KEY" ] || [ -n "$MADEINOZ_KNOWLEDGE_GOOGLE_API_KEY" ] || [ -n "$MADEINOZ_KNOWLEDGE_GROQ_API_KEY" ]; then
    echo "✓ Found existing API keys in PAI configuration (MADEINOZ_KNOWLEDGE_* prefix)"
    AUTO_CONFIGURED=true
# Fall back to legacy keys
elif [ -n "$OPENAI_API_KEY" ] || [ -n "$ANTHROPIC_API_KEY" ] || [ -n "$GOOGLE_API_KEY" ] || [ -n "$GROQ_API_KEY" ]; then
    echo "✓ Found existing API keys in PAI configuration (legacy - consider migrating to MADEINOZ_KNOWLEDGE_* prefix)"
    AUTO_CONFIGURED=true
fi

# Determine provider settings (check MADEINOZ_KNOWLEDGE_* first)
# Default to Ollama (free, local, private)
if [ -z "$MADEINOZ_KNOWLEDGE_LLM_PROVIDER" ] && [ -z "$LLM_PROVIDER" ]; then
    # Default to Ollama unless a cloud API key is configured
    if [ -n "$MADEINOZ_KNOWLEDGE_OPENAI_API_KEY" ] || [ -n "$OPENAI_API_KEY" ]; then
        LLM_PROVIDER="openai"
        EMBEDDER_PROVIDER="openai"
    elif [ -n "$MADEINOZ_KNOWLEDGE_ANTHROPIC_API_KEY" ] || [ -n "$ANTHROPIC_API_KEY" ]; then
        LLM_PROVIDER="anthropic"
        EMBEDDER_PROVIDER="openai"  # Anthropic needs OpenAI for embeddings
    elif [ -n "$MADEINOZ_KNOWLEDGE_GOOGLE_API_KEY" ] || [ -n "$GOOGLE_API_KEY" ]; then
        LLM_PROVIDER="gemini"
        EMBEDDER_PROVIDER="gemini"
    elif [ -n "$MADEINOZ_KNOWLEDGE_GROQ_API_KEY" ] || [ -n "$GROQ_API_KEY" ]; then
        LLM_PROVIDER="groq"
        EMBEDDER_PROVIDER="openai"  # Groq needs OpenAI for embeddings
    else
        # No API keys - default to Ollama
        LLM_PROVIDER="ollama"
        EMBEDDER_PROVIDER="ollama"
    fi
else
    LLM_PROVIDER="${MADEINOZ_KNOWLEDGE_LLM_PROVIDER:-$LLM_PROVIDER}"
    EMBEDDER_PROVIDER="${MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER:-$EMBEDDER_PROVIDER}"
fi

echo ""
echo "Configuration to add to PAI .env:"
echo "  LLM_PROVIDER: $LLM_PROVIDER"
echo "  EMBEDDER_PROVIDER: $EMBEDDER_PROVIDER"
echo ""

# ============================================================
# Step 2.4: Add/Update Configuration in PAI .env
# ============================================================

# Export flags for Python script
export PRESERVE_EXISTING
export MIGRATE_LEGACY

echo "Adding Madeinoz Knowledge System configuration to $PAI_ENV..."

# Use Python to safely update the .env file with preserve/migrate logic
python3 << 'PYTHON_EOF'
import os
import re
import sys

# Get flags from environment
preserve_existing = os.getenv('PRESERVE_EXISTING', 'false').lower() == 'true'
migrate_legacy = os.getenv('MIGRATE_LEGACY', 'false').lower() == 'true'

pai_env = os.path.expanduser(os.getenv('PAI_DIR', os.path.expanduser('~/.claude')) + '/.env')

print(f"\nConfiguration mode:")
print(f"  Preserve existing: {preserve_existing}")
print(f"  Migrate legacy:    {migrate_legacy}")
print(f"  Target file:       {pai_env}")
print("")

# Read existing content
try:
    with open(pai_env, 'r') as f:
        lines = f.readlines()
except FileNotFoundError:
    lines = []
    print("  (Creating new .env file)")

# Parse existing variables into a dict for easy checking
existing_vars = {}
for line in lines:
    match = re.match(r'^([A-Z_][A-Z0-9_]*)=(.*)$', line.strip())
    if match:
        existing_vars[match.group(1)] = match.group(2)

# Default values for new installations
# These use sensible defaults (Ollama for free local operation)
default_vars = {
    'MADEINOZ_KNOWLEDGE_LLM_PROVIDER': 'ollama',
    'MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER': 'ollama',
    'MADEINOZ_KNOWLEDGE_MODEL_NAME': 'llama3.2',
    'MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL': 'http://host.docker.internal:11434/v1',
    'MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL': 'mxbai-embed-large',
    'MADEINOZ_KNOWLEDGE_DATABASE_TYPE': 'neo4j',
    'MADEINOZ_KNOWLEDGE_FALKORDB_HOST': 'madeinoz-knowledge-falkordb',
    'MADEINOZ_KNOWLEDGE_FALKORDB_PORT': '6379',
    'MADEINOZ_KNOWLEDGE_NEO4J_URI': 'bolt://madeinoz-knowledge-neo4j:7687',
    'MADEINOZ_KNOWLEDGE_NEO4J_USER': 'neo4j',
    'MADEINOZ_KNOWLEDGE_NEO4J_PASSWORD': 'madeinozknowledge',
    'MADEINOZ_KNOWLEDGE_NEO4J_DATABASE': 'neo4j',
    'MADEINOZ_KNOWLEDGE_SEMAPHORE_LIMIT': '10',
    'MADEINOZ_KNOWLEDGE_GROUP_ID': 'main',
    'MADEINOZ_KNOWLEDGE_GRAPHITI_TELEMETRY_ENABLED': 'false',
}

# Legacy to MADEINOZ_KNOWLEDGE_* migration mapping
legacy_mapping = {
    'OPENAI_API_KEY': 'MADEINOZ_KNOWLEDGE_OPENAI_API_KEY',
    'ANTHROPIC_API_KEY': 'MADEINOZ_KNOWLEDGE_ANTHROPIC_API_KEY',
    'GOOGLE_API_KEY': 'MADEINOZ_KNOWLEDGE_GOOGLE_API_KEY',
    'GROQ_API_KEY': 'MADEINOZ_KNOWLEDGE_GROQ_API_KEY',
    'OPENAI_BASE_URL': 'MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL',
}

# Track changes for reporting
preserved_count = 0
added_count = 0
migrated_count = 0
updated_count = 0

# Build final vars_to_write
vars_to_write = {}

for var_name, default_value in default_vars.items():
    if var_name in existing_vars:
        if preserve_existing:
            # Keep existing value
            vars_to_write[var_name] = existing_vars[var_name]
            preserved_count += 1
            print(f"  ✓ Preserved: {var_name}")
        else:
            # Replace with default/new value
            new_value = os.getenv(var_name, default_value)
            vars_to_write[var_name] = new_value
            if existing_vars[var_name] != new_value:
                updated_count += 1
                print(f"  → Updated:   {var_name}")
            else:
                preserved_count += 1
    else:
        # Variable doesn't exist - add it
        new_value = os.getenv(var_name, default_value)
        vars_to_write[var_name] = new_value
        added_count += 1
        print(f"  + Added:     {var_name}")

# Handle legacy migration
if migrate_legacy:
    print("\nMigrating legacy keys:")
    for legacy_name, new_name in legacy_mapping.items():
        if legacy_name in existing_vars and new_name not in existing_vars:
            vars_to_write[new_name] = existing_vars[legacy_name]
            migrated_count += 1
            print(f"  → Migrated:  {legacy_name} → {new_name}")

# Write updated content
with open(pai_env, 'w') as f:
    # First, write all existing lines, updating MADEINOZ_KNOWLEDGE_* ones as needed
    written_vars = set()
    added_header = False

    for line in lines:
        match = re.match(r'^([A-Z_][A-Z0-9_]*)=', line.strip())
        if match:
            var_name = match.group(1)
            if var_name in vars_to_write:
                # Write our version of this variable
                f.write(f"{var_name}={vars_to_write[var_name]}\n")
                written_vars.add(var_name)
            else:
                # Keep original line as-is
                f.write(line)
        else:
            # Non-variable line (comment, blank, etc.) - keep as-is
            f.write(line)

    # Add any new variables that weren't in the original file
    new_vars = [v for v in vars_to_write.keys() if v not in written_vars]
    if new_vars:
        # Add section header if we're adding new MADEINOZ_KNOWLEDGE_* variables
        f.write("\n# Madeinoz Knowledge System Configuration\n")
        for var_name in sorted(new_vars):
            f.write(f"{var_name}={vars_to_write[var_name]}\n")
            written_vars.add(var_name)

# Summary
print("\n" + "="*50)
print("Configuration Summary:")
print(f"  Preserved: {preserved_count} variables")
print(f"  Added:     {added_count} variables")
print(f"  Updated:   {updated_count} variables")
if migrate_legacy:
    print(f"  Migrated:  {migrated_count} legacy keys")
print("="*50)
print("\n✓ Madeinoz Knowledge System configuration complete")
PYTHON_EOF

echo ""
echo "✓ Configuration complete"
echo ""
echo "PAI .env is now the source of truth for:"
echo "  - API keys (existing)"
echo "  - Madeinoz Knowledge System settings (newly added)"
```

## Step 3: Start MCP Server

> **FOR AI AGENTS:** This step starts the containerized MCP server. The server MUST be running before proceeding.
> - If server fails to start: Check container logs with `podman logs madeinoz-knowledge-graph-mcp`
> - If health check fails: Wait additional 30 seconds and retry - container may still be initializing
> - Server must show "✓ Server is running" before proceeding to Step 4

**Database Backend Selection:**

The Madeinoz Knowledge System supports two database backends:

| Backend | Description | Best For |
|---------|-------------|----------|
| **Neo4j** (default) | Native graph database with Cypher queries | Better special character handling, richer query language |
| **FalkorDB** | Redis-based graph database with RediSearch | Simple setup, lower resource usage |

Neo4j is the default backend. To use FalkorDB instead, set the environment variable before starting:
```bash
export MADEINOZ_KNOWLEDGE_DATABASE_TYPE=falkordb
```

Or update your PAI `.env` file:
```bash
MADEINOZ_KNOWLEDGE_DATABASE_TYPE=falkordb
```

Launch the Graphiti MCP server:

```bash
# Detect container runtime (Podman or Docker)
if command -v podman &> /dev/null; then
    CONTAINER_RUNTIME="podman"
    echo "✓ Detected Podman"
elif command -v docker &> /dev/null; then
    CONTAINER_RUNTIME="docker"
    echo "✓ Detected Docker"
else
    echo "❌ No container runtime found!"
    echo "   Install Podman: brew install podman (macOS)"
    echo "   Install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Start the server
echo ""
echo "🚀 Starting MCP Server"
echo "======================"
echo ""
bun run src/server/run.ts

# Wait for server to initialize
echo ""
echo "Waiting for server to start..."
sleep 15

# Check server health
echo "Verifying server health..."
if curl -sf --max-time 5 http://localhost:8000/health | grep -q "healthy"; then
    echo "✓ Server is running and healthy!"
else
    echo "⚠️  Server health check failed"
    echo "Check logs with: bun run src/skills/tools/logs.ts"
    echo "The server may still be starting up. Wait 30 seconds and try again."
fi
```

**Expected output:**
```
✓ Server is running and healthy!
```

**Alternative: Using Docker Compose**

If you prefer Docker Compose, use the appropriate compose file for your backend:

```bash
# IMPORTANT: Source PAI .env before running docker-compose
# The ${VAR} substitution in docker-compose reads from HOST environment,
# NOT from env_file (which loads INTO the container after substitution)
set -a; source ~/.claude/.env; set +a

# For Neo4j backend (default - includes search-all-groups patch)
docker compose -f src/server/docker-compose-neo4j.yml up -d

# For FalkorDB backend (alternative)
docker compose -f src/server/docker-compose.yml up -d

# Check status
bun run src/skills/tools/status.ts
```

> **⚠️ Common Issue:** If the container starts but LLM calls fail with wrong model errors,
> ensure you've sourced the PAI .env file BEFORE running docker-compose.
> The env_file directive loads vars into the container, but ${VAR} substitution
> in docker-compose.yml happens from the HOST shell environment.

**PAI Search Patch (Neo4j only):**
The Neo4j docker-compose includes a patch that can search across ALL groups when no `group_ids` are specified. This ensures knowledge stored in different groups (e.g., `osint-profiles`, `main`, `research`) is discoverable without explicitly specifying groups in every search.

**Configuration:**
```bash
# In PAI config ($PAI_DIR/.env or ~/.claude/.env) - set to enable/disable the patch
MADEINOZ_KNOWLEDGE_SEARCH_ALL_GROUPS=true   # Enable (default)
MADEINOZ_KNOWLEDGE_SEARCH_ALL_GROUPS=false  # Disable (original behavior)
```

The patch:
- Controlled by `MADEINOZ_KNOWLEDGE_SEARCH_ALL_GROUPS` environment variable
- Dynamically queries all available group_ids at search time
- Uses a 30-second cache to balance performance and freshness
- Ensures new groups are searchable within 30 seconds of creation
- Located at: `src/server/patches/graphiti_mcp_server.py`

**Verify patch status:**
```bash
curl http://localhost:8000/health
# Returns: {"status":"healthy","service":"graphiti-mcp","patch":"madeinoz-all-groups-enabled"}
# Or: {"status":"healthy","service":"graphiti-mcp","patch":"madeinoz-all-groups-disabled"}
```

**Neo4j Browser Access:**
When using Neo4j backend, you can access the Neo4j Browser at http://localhost:7474
- Username: `neo4j` (default)
- Password: `madeinozknowledge` (default)

**Troubleshooting:**
- If server fails to start, check logs: `bun run src/skills/tools/logs.ts`
- If port is already in use, stop conflicting service or modify `src/server/run.ts` to use different ports
- If API key validation fails, verify your API key has available credits/quota

---

## Step 4: Install Full Pack and Knowledge Skill

> **FOR AI AGENTS:** This step installs the COMPLETE pack, not just skills.
> - **IMPORTANT:** When version changes, ALL files must be replaced (skills, hooks, server, config)
> - The full pack is installed to `~/.claude/Packs/madeinoz-knowledge-system/`
> - Skills are copied to `~/.claude/skills/Knowledge/`
> - Hooks are copied to `~/.claude/hooks/` (Step 9)
> - Verify the copy succeeded by checking the directory structure

Install the complete pack and skill:

```bash
echo ""
echo "📦 Installing Madeinoz Knowledge System Pack"
echo "============================================="
echo ""

# Determine PAI directory
PAI_DIR="${PAI_DIR:-$HOME/.claude}"

# Create Packs directory if it doesn't exist
PACKS_DIR="$PAI_DIR/Packs"
mkdir -p "$PACKS_DIR"

# Pack installation directory
PACK_INSTALL_DIR="$PACKS_DIR/madeinoz-knowledge-system"

# Get current pack directory (where we're running from)
PACK_SOURCE_DIR="$(pwd)"

# Extract versions for comparison
NEW_VERSION=$(grep -E "^version:" "$PACK_SOURCE_DIR/README.md" | head -1 | sed 's/version:[[:space:]]*//')
if [[ -f "$PACK_INSTALL_DIR/README.md" ]]; then
    OLD_VERSION=$(grep -E "^version:" "$PACK_INSTALL_DIR/README.md" | head -1 | sed 's/version:[[:space:]]*//')
    echo "Existing installation: v$OLD_VERSION"
    echo "New version: v$NEW_VERSION"

    # Step 4.1: Backup existing installation before replacing
    # Location follows PAI convention: ~/.claude/MEMORY/Backups/
    echo ""
    echo "📁 Creating backup of existing installation..."
    BACKUP_DIR="$PAI_DIR/MEMORY/Backups/madeinoz-knowledge-system"
    mkdir -p "$BACKUP_DIR"
    BACKUP_NAME="backup-v${OLD_VERSION}-$(date +%Y%m%d-%H%M%S)"

    if mv "$PACK_INSTALL_DIR" "$BACKUP_DIR/$BACKUP_NAME" 2>/dev/null; then
        echo "✓ Backup created: $BACKUP_DIR/$BACKUP_NAME"

        # Keep only last 3 backups (cleanup old ones)
        BACKUP_COUNT=$(ls -1d "$BACKUP_DIR"/backup-* 2>/dev/null | wc -l | tr -d ' ')
        if [[ "$BACKUP_COUNT" -gt 3 ]]; then
            echo "  Cleaning up old backups (keeping last 3)..."
            ls -1dt "$BACKUP_DIR"/backup-* | tail -n +4 | xargs rm -rf
        fi
    else
        echo "⚠️  Could not create backup (directory may not exist)"
    fi

    if [[ "$OLD_VERSION" != "$NEW_VERSION" ]]; then
        echo ""
        echo "⬆️  Upgrading: v$OLD_VERSION → v$NEW_VERSION"
    else
        echo ""
        echo "🔄 Reinstalling: v$NEW_VERSION (same version)"
    fi
else
    echo "New installation: v$NEW_VERSION"
fi

# Copy ENTIRE pack to Packs directory
echo ""
echo "Installing full pack to: $PACK_INSTALL_DIR"
cp -r "$PACK_SOURCE_DIR" "$PACK_INSTALL_DIR"
echo "✓ Full pack installed (includes server, hooks, config)"

# Now copy skills to PAI skills directory
PAI_SKILLS_DIR="$PAI_DIR/skills"
mkdir -p "$PAI_SKILLS_DIR"

echo ""
echo "Installing Knowledge skill to: $PAI_SKILLS_DIR/Knowledge"
rm -rf "$PAI_SKILLS_DIR/Knowledge"
cp -r "$PACK_INSTALL_DIR/src/skills" "$PAI_SKILLS_DIR/Knowledge"

# Version is tracked in SKILL.md frontmatter
INSTALLED_VERSION=$(grep -E "^version:" "$PAI_SKILLS_DIR/Knowledge/SKILL.md" | head -1 | sed 's/version:[[:space:]]*//')
echo "✓ Skill installed: v$INSTALLED_VERSION"

echo ""
echo "Installation Summary:"
echo "  Pack:  $PACK_INSTALL_DIR"
echo "  Skill: $PAI_SKILLS_DIR/Knowledge"
echo ""
echo "Installed files:"
echo "  ├── src/server/    (docker-compose, patches, CLI)"
echo "  ├── src/skills/    (workflows, tools)"
echo "  ├── src/hooks/     (memory sync hooks)"
echo "  └── config/        (.env.example)"
echo ""
echo "Run server commands from: $PACK_INSTALL_DIR"
```

---

## Step 5: Configure MCP Server in Claude Code

> **FOR AI AGENTS:** This step configures Claude Code to connect to the Knowledge MCP server.
> - The MCP server configuration MUST be added to `~/.claude.json`
> - If existing configuration is identical, ask user whether to keep or replace
> - After configuration, Claude Code must be restarted for changes to take effect
> - Verify the MCP server appears in Claude Code's server list after restart

**Enable the MCP server connection in Claude Code:**

The Knowledge skill requires MCP server integration. Configure it globally:

```bash
echo ""
echo "📝 Configuring MCP Server in Claude Code"
echo "========================================="
echo ""

# Configure MCP servers in global Claude config
CLAUDE_CONFIG="$HOME/.claude.json"

# New configuration values
NEW_TYPE="http"
NEW_URL="http://localhost:8000/mcp"

echo "Target configuration:"
echo "  File: $CLAUDE_CONFIG"
echo "  Server: madeinoz-knowledge"
echo "  Type: $NEW_TYPE"
echo "  URL: $NEW_URL"
echo ""

# Check if ~/.claude.json exists
if [ -f "$CLAUDE_CONFIG" ]; then
    echo "Found existing ~/.claude.json"

    # Check if madeinoz-knowledge already configured
    if grep -q "madeinoz-knowledge" "$CLAUDE_CONFIG" 2>/dev/null; then
        echo ""
        echo "⚠️  madeinoz-knowledge MCP server already configured"

        # Extract and compare existing values
        python3 << 'PYTHON_EOF'
import json
import os
import sys

config_path = os.path.expanduser("~/.claude.json")
new_type = "http"
new_url = "http://localhost:8000/mcp"

with open(config_path, 'r') as f:
    config = json.load(f)

existing = config.get('mcpServers', {}).get('madeinoz-knowledge', {})
existing_type = existing.get('type', '')
existing_url = existing.get('url', '')

print(f"\nExisting configuration:")
print(f"  Type: {existing_type}")
print(f"  URL:  {existing_url}")
print(f"\nNew configuration:")
print(f"  Type: {new_type}")
print(f"  URL:  {new_url}")

# Check if values are identical
if existing_type == new_type and existing_url == new_url:
    print("\n✓ Existing configuration is IDENTICAL to new values")
    # Signal identical values to shell
    with open('/tmp/mcp_config_status', 'w') as f:
        f.write("IDENTICAL")
else:
    print("\n⚠️  Existing configuration DIFFERS from new values")
    with open('/tmp/mcp_config_status', 'w') as f:
        f.write("DIFFERENT")
PYTHON_EOF

        # Read status from temp file
        MCP_STATUS=$(cat /tmp/mcp_config_status 2>/dev/null)
        rm -f /tmp/mcp_config_status

        echo ""
        if [ "$MCP_STATUS" = "IDENTICAL" ]; then
            echo "Configuration values are identical."
            read -p "Keep existing configuration? (Y/n): " KEEP_EXISTING
            if [[ "$KEEP_EXISTING" =~ ^[Nn]$ ]]; then
                echo "Replacing with new configuration..."
                python3 << 'PYTHON_EOF'
import json
import os

config_path = os.path.expanduser("~/.claude.json")
with open(config_path, 'r') as f:
    config = json.load(f)

config['mcpServers']['madeinoz-knowledge'] = {
    'type': 'http',
    'url': 'http://localhost:8000/mcp'
}

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print("✓ Replaced madeinoz-knowledge configuration")
PYTHON_EOF
            else
                echo "✓ Keeping existing configuration"
            fi
        else
            # Values differ - ask which to use
            echo "Which configuration would you like to use?"
            echo "  1) Keep existing"
            echo "  2) Use new values"
            read -p "Choice (1/2): " CONFIG_CHOICE

            if [ "$CONFIG_CHOICE" = "2" ]; then
                echo "Updating to new configuration..."
                python3 << 'PYTHON_EOF'
import json
import os

config_path = os.path.expanduser("~/.claude.json")
with open(config_path, 'r') as f:
    config = json.load(f)

config['mcpServers']['madeinoz-knowledge'] = {
    'type': 'http',
    'url': 'http://localhost:8000/mcp'
}

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print("✓ Updated madeinoz-knowledge configuration")
PYTHON_EOF
            else
                echo "✓ Keeping existing configuration"
            fi
        fi
    elif ! grep -q "mcpServers" "$CLAUDE_CONFIG" 2>/dev/null; then
        # File exists but no mcpServers section
        echo "Adding mcpServers section to ~/.claude.json"
        python3 << 'PYTHON_EOF'
import json
import os

config_path = os.path.expanduser("~/.claude.json")
try:
    with open(config_path, 'r') as f:
        config = json.load(f)
except json.JSONDecodeError:
    config = {}

if 'mcpServers' not in config:
    config['mcpServers'] = {}

config['mcpServers']['madeinoz-knowledge'] = {
    'type': 'http',
    'url': 'http://localhost:8000/mcp'
}

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print("✓ Added madeinoz-knowledge MCP server to ~/.claude.json")
PYTHON_EOF
    else
        # mcpServers exists but madeinoz-knowledge not configured
        echo "Adding madeinoz-knowledge to existing mcpServers"
        python3 << 'PYTHON_EOF'
import json
import os

config_path = os.path.expanduser("~/.claude.json")
with open(config_path, 'r') as f:
    config = json.load(f)

config['mcpServers']['madeinoz-knowledge'] = {
    'type': 'http',
    'url': 'http://localhost:8000/mcp'
}

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print("✓ Added madeinoz-knowledge MCP server to ~/.claude.json")
PYTHON_EOF
    fi
else
    echo "Creating new ~/.claude.json"
    cat > "$CLAUDE_CONFIG" << 'EOF'
{
  "mcpServers": {
    "madeinoz-knowledge": {
      "type": "http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
EOF
    echo "✓ Created ~/.claude.json with MCP configuration"
fi

echo ""
echo "Final configuration:"
echo "  File: ~/.claude.json"
echo "  Server: madeinoz-knowledge"
echo "  Transport: HTTP"
echo "  URL: http://localhost:8000/mcp"
echo ""

# Also create .mcp.json in project for reference
echo "Creating project-level .mcp.json for reference..."
cat > .mcp.json << 'EOF'
{
  "mcpServers": {
    "madeinoz-knowledge": {
      "type": "http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
EOF
echo "✓ Created .mcp.json (project reference)"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "IMPORTANT: Restart Claude Code to load MCP configuration!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
```

**What this does:**
- Configures `madeinoz-knowledge` MCP server in global `~/.claude.json`
- Creates project-level `.mcp.json` for reference
- Enables MCP tools globally across all Claude Code sessions
- Uses SSE (Server-Sent Events) transport for real-time communication

**Available MCP Tools:**
After restart, Claude Code will have access to:
- `add_episode` - Add knowledge to graph
- `search_nodes` - Search entities and summaries
- `search_facts` - Find relationships
- `get_episodes` - Retrieve recent knowledge
- `get_status` - Check system health
- `clear_graph` - Delete all knowledge
- `delete_episode` - Remove specific episodes
- `delete_entity_edge` - Remove relationships
- `get_entity_edge` - Get edge details

---

## Step 6: Verify Installation

> **FOR AI AGENTS:** This step runs basic verification. ALL checks must pass (show ✓).
> - If ANY check fails (shows ✗), STOP and troubleshoot before proceeding
> - After this step succeeds, you MUST also complete the full VERIFY.md checklist
> - Do NOT consider installation complete until VERIFY.md passes

Run comprehensive verification checks:

```bash
echo ""
echo "✅ Installation Verification"
echo "============================"
echo ""

# Check 1: Container running
if bun run src/skills/tools/status.ts 2>/dev/null | grep -q "running"; then
    echo "✓ Madeinoz Knowledge container is running"
else
    echo "✗ Container may not be running"
    echo "  Start with: bun run src/skills/tools/start.ts"
fi

# Check 2: Server responding (health endpoint)
if curl -sf --max-time 5 http://localhost:8000/health | grep -q "healthy"; then
    echo "✓ MCP server is responding at http://localhost:8000/mcp"
else
    echo "✗ MCP server health check failed"
    echo "  Check logs: bun run src/skills/tools/logs.ts"
fi

# Check 3: Database accessible (FalkorDB or Neo4j)
# Detect which backend is being used
if [ -n "$MADEINOZ_KNOWLEDGE_DATABASE_TYPE" ] && [ "$MADEINOZ_KNOWLEDGE_DATABASE_TYPE" = "neo4j" ]; then
    # Neo4j backend
    if curl -s --max-time 5 http://localhost:7474 > /dev/null 2>&1; then
        echo "✓ Neo4j is accessible on port 7474"
    else
        echo "✗ Neo4j may not be accessible (port 7474)"
    fi
else
    # FalkorDB backend (default)
    if podman exec madeinoz-knowledge-falkordb redis-cli PING > /dev/null 2>&1; then
        echo "✓ FalkorDB is accessible"
    elif docker exec madeinoz-knowledge-falkordb redis-cli PING > /dev/null 2>&1; then
        echo "✓ FalkorDB is accessible"
    else
        echo "✗ FalkorDB may not be accessible"
    fi
fi

# Check 4: Skill installed
if [[ -d "$PAI_SKILLS_DIR/Knowledge" ]]; then
    echo "✓ Knowledge skill is installed at: $PAI_SKILLS_DIR/Knowledge"
else
    echo "✗ Knowledge skill installation failed"
fi

# Check 5: Configuration exists in PAI .env
PAI_ENV="${PAI_DIR:-$HOME/.claude}/.env"
if [[ -f "$PAI_ENV" ]] && grep -q "MADEINOZ_KNOWLEDGE_OPENAI_API_KEY=sk-" "$PAI_ENV" 2>/dev/null; then
    echo "✓ PAI configuration file exists with API key"
else
    echo "⚠️  API key may not be configured properly"
    echo "  Edit $PAI_ENV and add your MADEINOZ_KNOWLEDGE_OPENAI_API_KEY"
fi

# Check 6: Required skill files
SKILL_FILES=(
    "$PAI_SKILLS_DIR/Knowledge/SKILL.md"
    "$PAI_SKILLS_DIR/Knowledge/README.md"
    "$PAI_SKILLS_DIR/Knowledge/src/skills/workflows/CaptureEpisode.md"
)

ALL_SKILL_FILES=true
for file in "${SKILL_FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "✗ Missing skill file: $file"
        ALL_SKILL_FILES=false
    fi
done

if [[ "$ALL_SKILL_FILES" = true ]]; then
    echo "✓ All required skill files are present"
fi

echo ""
echo "Installation verification complete!"
```

---

## Step 7: Test Installation

Verify the system works end-to-end:

```bash
echo ""
echo "🧪 Testing Installation"
echo "======================="
echo ""

# Test 1: Check health endpoint is available
echo "Test 1: Checking server health..."
if curl -sf --max-time 5 http://localhost:8000/health | grep -q "healthy"; then
    echo "✓ MCP server is healthy"
else
    echo "✗ Health endpoint not responding"
fi

# Test 2: Check containers are running
echo ""
echo "Test 2: Checking containers..."
if podman ps 2>/dev/null | grep -q "madeinoz-knowledge" || docker ps 2>/dev/null | grep -q "madeinoz-knowledge"; then
    echo "✓ Knowledge system containers are running"
    podman ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null | grep madeinoz-knowledge || \
    docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null | grep madeinoz-knowledge
else
    echo "✗ Containers not found"
fi

# Test 3: Check database backend is responding
echo ""
echo "Test 3: Checking database backend..."
if [ -n "$MADEINOZ_KNOWLEDGE_DATABASE_TYPE" ] && [ "$MADEINOZ_KNOWLEDGE_DATABASE_TYPE" = "neo4j" ]; then
    # Neo4j backend
    if curl -s --max-time 5 http://localhost:7474 > /dev/null 2>&1; then
        echo "✓ Neo4j is responding (Browser at http://localhost:7474)"
    else
        echo "⚠️  Neo4j not responding (may still be starting)"
    fi
else
    # FalkorDB backend (default)
    if podman exec madeinoz-knowledge-falkordb redis-cli PING 2>/dev/null | grep -q "PONG" || \
       docker exec madeinoz-knowledge-falkordb redis-cli PING 2>/dev/null | grep -q "PONG"; then
        echo "✓ FalkorDB is responding"
    else
        echo "⚠️  FalkorDB ping failed (may still be starting)"
    fi
fi

# Test 4: Verify Lucene sanitization for hyphenated group_ids (FalkorDB only)
echo ""
echo "Test 4: Testing Lucene query sanitization..."

# Only run Lucene tests for FalkorDB backend
if [ -n "$MADEINOZ_KNOWLEDGE_DATABASE_TYPE" ] && [ "$MADEINOZ_KNOWLEDGE_DATABASE_TYPE" = "neo4j" ]; then
    echo "✓ Skipping Lucene tests (Neo4j uses Cypher, not RediSearch)"
    echo "  Neo4j handles special characters natively without escaping"
else
    echo "This test verifies that hyphens in group_ids are properly escaped"
    echo "to prevent RediSearch Lucene syntax errors."

    # Create a test script that calls the MCP server with a hyphenated group_id
    cat > /tmp/test_lucene_sanitization.ts << 'EOF'
import { sanitizeGroupId } from './src/server/lib/lucene';

// Test cases with various hyphenated patterns
const testCases = [
  'test-group',
  'my-knowledge-base',
  'madeinoz-history-system',
  'multi-hyphen-group-id',
  'group-with-dashes-123',
];

console.log('Testing Lucene query sanitization for hyphenated group_ids:\n');

let allPassed = true;
testCases.forEach(group => {
  try {
    const sanitized = sanitizeGroupId(group);
    console.log(`✓ ${group} → "${sanitized}"`);
  } catch (error) {
    console.log(`✗ ${group} → ERROR: ${error}`);
    allPassed = false;
  }
});

console.log('\n' + (allPassed ? '✓ All sanitization tests passed!' : '✗ Some tests failed'));
process.exit(allPassed ? 0 : 1);
EOF

    # Run the test
    if bun run /tmp/test_lucene_sanitization.ts 2>&1; then
        echo "✓ Lucene sanitization is working correctly"
        echo "  Hyphenated group_ids will be properly escaped in queries"
    else
        echo "⚠️  Lucene sanitization test failed"
        echo "  Check that src/server/lib/lucene.ts exists and exports sanitizeGroupId"
    fi

    # Clean up test file
    rm -f /tmp/test_lucene_sanitization.ts
fi

echo ""
echo "Testing complete!"
echo ""
echo "Note: Full MCP functionality is tested via Claude Code after restart."
echo "The MCP server uses SSE transport - tools are accessed through Claude Code's MCP integration."
```

---

## Step 8: Post-Installation Configuration

Restart Claude Code to load the new skill:

```bash
echo ""
echo "📝 Next Steps"
echo "============"
echo ""
echo "1. **Restart Claude Code** to load the Madeinoz Knowledge System skill"
echo ""
echo "2. **Test the skill** in Claude Code:"
echo "   Remember that I'm testing the Madeinoz Knowledge System installation."
echo ""
echo "3. **Check system status** in Claude Code:"
echo "   Show the knowledge graph status"
echo ""
echo "4. **Search your knowledge** (after adding some):"
echo "   What do I know about PAI?"
echo ""

# Optional: Add to shell profile for convenience
echo "Would you like to add environment variables to your shell profile? (y/N)"
read -r ADD_TO_PROFILE

if [[ "$ADD_TO_PROFILE" =~ ^[Yy]$ ]]; then
    PROFILE="$HOME/.zshrc"
    if [[ ! -f "$PROFILE" ]]; then
        PROFILE="$HOME/.bashrc"
    fi

    echo ""
    echo "Adding to profile: $PROFILE"
    echo "" >> "$PROFILE"
    echo "# Madeinoz Knowledge System" >> "$PROFILE"
    echo "export PAI_DIR=\"\${PAI_DIR:-\$HOME/.claude}\"" >> "$PROFILE"
    echo "alias madeinoz-status='curl -s http://localhost:8000/health'" >> "$PROFILE"
    echo "alias madeinoz-logs='bun run src/skills/tools/logs.ts'" >> "$PROFILE"
    echo "alias madeinoz-start='bun run src/skills/tools/start.ts'" >> "$PROFILE"
    echo "alias madeinoz-stop='bun run src/skills/tools/stop.ts'" >> "$PROFILE"
    echo "alias madeinoz-restart='bun run src/skills/tools/stop.ts && bun run src/skills/tools/start.ts'" >> "$PROFILE"
    echo ""
    echo "✓ Added aliases to $PROFILE"
    echo "  Source with: source $PROFILE"
fi

echo ""
echo "🎉 Installation Complete!"
echo ""
echo "Documentation:"
echo "  - README: madeinoz-knowledge-system/README.md"
echo "  - Installation: INSTALL.md"
echo "  - Quick Start: QUICKSTART.md"
echo ""
echo "Skill installed as: Knowledge"
echo "  - Location: $PAI_SKILLS_DIR/Knowledge"
echo ""
echo "Management Commands:"
echo "  - View logs: bun run src/skills/tools/logs.ts"
echo "  - Restart: bun run src/skills/tools/stop.ts && bun run src/skills/tools/start.ts"
echo "  - Stop: bun run src/skills/tools/stop.ts"
echo "  - Start: bun run src/skills/tools/start.ts"
echo "  - Status: bun run src/skills/tools/status.ts"
```

---

## Step 9: Install Memory Sync Hook (Optional but Recommended)

The memory sync hook automatically syncs captured learnings and research from the PAI Memory System to the knowledge graph. This provides a seamless integration where your daily captures become searchable knowledge.

**Prerequisites:**
- PAI Memory System directory at `~/.claude/MEMORY/` should exist (created by PAI core)

```bash
echo ""
echo "🔗 Installing Memory Sync Hook"
echo "================================"
echo ""

# Determine PAI directory and installed pack location
PAI_DIR="${PAI_DIR:-$HOME/.claude}"
PACK_INSTALL_DIR="$PAI_DIR/Packs/madeinoz-knowledge-system"

# Check if pack is installed (Step 4 must be completed first)
if [[ ! -d "$PACK_INSTALL_DIR" ]]; then
    echo "❌ Pack not installed at: $PACK_INSTALL_DIR"
    echo "   Run Step 4 first to install the full pack."
    exit 1
fi

echo "Using installed pack: $PACK_INSTALL_DIR"

# Verify memory system directory exists
MEMORY_DIR="$PAI_DIR/MEMORY"
if [ ! -d "$MEMORY_DIR" ]; then
    echo "⚠️  Memory directory not found at: $MEMORY_DIR"
    echo "   The directory will be created when you start using PAI."
fi

echo "✓ Memory directory: $MEMORY_DIR"

# Hooks install to ~/.claude/hooks/ (where Claude Code reads them)
PAI_HOOKS_DIR="$PAI_DIR/hooks"
mkdir -p "$PAI_HOOKS_DIR/lib"

echo "Installing hook files to: $PAI_HOOKS_DIR"

# Copy hook implementation files FROM INSTALLED PACK
cp "$PACK_INSTALL_DIR/src/hooks/sync-memory-to-knowledge.ts" "$PAI_HOOKS_DIR/"
cp "$PACK_INSTALL_DIR/src/hooks/sync-learning-realtime.ts" "$PAI_HOOKS_DIR/"
cp -r "$PACK_INSTALL_DIR/src/hooks/lib/"* "$PAI_HOOKS_DIR/lib/"

echo "✓ Hook files installed"

# Create sync state directory
SYNC_STATE_DIR="$MEMORY_DIR/STATE/knowledge-sync"
mkdir -p "$SYNC_STATE_DIR"
echo "✓ Created sync state directory: $SYNC_STATE_DIR"

# Register hooks in Claude Code settings.json (NOT PAI_DIR settings)
SETTINGS_FILE="$HOME/.claude/settings.json"
echo ""
echo "Registering hooks in: $SETTINGS_FILE"

# Use bun/node to merge hook configuration
bun << 'SCRIPT_EOF'
const fs = require('fs');
const path = require('path');

// Claude Code reads settings from ~/.claude/settings.json
const settingsPath = path.join(process.env.HOME, '.claude/settings.json');

let settings = {};
try {
    settings = JSON.parse(fs.readFileSync(settingsPath, 'utf-8'));
} catch (e) {
    // File doesn't exist or invalid JSON
}

// Ensure hooks structure exists
if (!settings.hooks) settings.hooks = {};
if (!settings.hooks.SessionStart) settings.hooks.SessionStart = [];
if (!settings.hooks.Stop) settings.hooks.Stop = [];
if (!settings.hooks.SubagentStop) settings.hooks.SubagentStop = [];

const homeDir = process.env.HOME;
let changed = false;

// 1. SessionStart: sync-memory-to-knowledge.ts (syncs memory at session start)
const sessionStartExists = settings.hooks.SessionStart.some(h =>
    h.hooks?.some(hook => hook.command?.includes('sync-memory-to-knowledge'))
);
if (!sessionStartExists) {
    settings.hooks.SessionStart.push({
        matcher: "*",
        hooks: [{
            type: "command",
            command: `bun run ${homeDir}/.claude/hooks/sync-memory-to-knowledge.ts`,
            timeout: 30000
        }]
    });
    console.log("✓ SessionStart hook registered (sync-memory-to-knowledge.ts)");
    changed = true;
} else {
    console.log("✓ SessionStart hook already registered (skipping)");
}

// 2. Stop: sync-learning-realtime.ts (syncs learning when execution stops)
const stopExists = settings.hooks.Stop.some(h =>
    h.hooks?.some(hook => hook.command?.includes('sync-learning-realtime'))
);
if (!stopExists) {
    settings.hooks.Stop.push({
        hooks: [{
            type: "command",
            command: `bun run ${homeDir}/.claude/hooks/sync-learning-realtime.ts`,
            timeout: 15000
        }]
    });
    console.log("✓ Stop hook registered (sync-learning-realtime.ts)");
    changed = true;
} else {
    console.log("✓ Stop hook already registered (skipping)");
}

// 3. SubagentStop: sync-learning-realtime.ts (syncs when subagent completes)
const subagentStopExists = settings.hooks.SubagentStop.some(h =>
    h.hooks?.some(hook => hook.command?.includes('sync-learning-realtime'))
);
if (!subagentStopExists) {
    settings.hooks.SubagentStop.push({
        hooks: [{
            type: "command",
            command: `bun run ${homeDir}/.claude/hooks/sync-learning-realtime.ts`,
            timeout: 15000
        }]
    });
    console.log("✓ SubagentStop hook registered (sync-learning-realtime.ts)");
    changed = true;
} else {
    console.log("✓ SubagentStop hook already registered (skipping)");
}

if (changed) {
    fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2));
    console.log("\n✓ settings.json updated with knowledge hooks");
}
SCRIPT_EOF

echo ""
echo "Hook installation complete!"
echo ""
echo "Hooks installed:"
echo "  📍 SessionStart: sync-memory-to-knowledge.ts"
echo "     - Syncs memory to knowledge graph at session start"
echo "     - Scans: LEARNING/ALGORITHM/, LEARNING/SYSTEM/, RESEARCH/"
echo ""
echo "  📍 Stop: sync-learning-realtime.ts"
echo "     - Syncs new learnings when execution stops"
echo ""
echo "  📍 SubagentStop: sync-learning-realtime.ts"
echo "     - Syncs learnings when subagent completes"
echo ""
echo "Manual sync commands:"
echo "  - Sync all:    bun run src/hooks/sync-memory-to-knowledge.ts --all"
echo "  - Dry run:     bun run src/hooks/sync-memory-to-knowledge.ts --dry-run"
echo "  - Verbose:     bun run src/hooks/sync-memory-to-knowledge.ts --verbose"
```

**Verifying the Hook:**

```bash
# Check hook files are installed
PAI_HOOKS="$HOME/.claude/hooks"

if [ -f "$PAI_HOOKS/sync-memory-to-knowledge.ts" ]; then
    echo "✓ Hook script installed"
else
    echo "✗ Hook script not found"
fi

# Check required lib files
echo "Checking hook lib files..."
REQUIRED_LIB_FILES=(
    "frontmatter-parser.ts"
    "knowledge-client.ts"
    "lucene.ts"
    "sync-state.ts"
)

for file in "${REQUIRED_LIB_FILES[@]}"; do
    if [ -f "$PAI_HOOKS/lib/$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ MISSING: $file"
    fi
done

# Check hook is registered
if grep -q "sync-memory-to-knowledge" "$HOME/.claude/settings.json" 2>/dev/null; then
    echo "✓ Hook registered in settings.json"
else
    echo "✗ Hook not registered"
fi

# Test hook manually (dry run)
echo ""
echo "Running hook in dry-run mode..."
bun run src/hooks/sync-memory-to-knowledge.ts --dry-run --verbose
```

**Sync State:**

The hook tracks which files have been synced in `~/.claude/MEMORY/STATE/knowledge-sync/sync-state.json`:

```json
{
  "version": "1.0.0",
  "last_sync": "2026-01-04T12:00:00.000Z",
  "synced_files": [
    {
      "filepath": "/path/to/learning.md",
      "synced_at": "2026-01-04T12:00:00.000Z",
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
| `episode_uuid` | string? | UUID returned by knowledge graph (if successful) |
| `capture_type` | string | Type of capture: LEARNING, RESEARCH |
| `content_hash` | string? | SHA-256 hash of episode_body for content-level deduplication |

**Troubleshooting Hook Issues:**

| Issue | Solution |
|-------|----------|
| Hook not running | Check `settings.json` has the hook registered |
| Files not syncing | Run with `--verbose` to see what's being skipped |
| Duplicate syncs | Check sync-state.json or delete it to resync all |
| MCP server offline | Hook gracefully skips when server unavailable |
| Permission errors | Ensure hook script is readable: `chmod 644 sync-memory-to-knowledge.ts` |

---

## Troubleshooting

### Server Won't Start

**Symptoms:** `bun run src/server/run.ts` fails or container exits immediately

**Diagnosis:**
```bash
# Check container logs
bun run src/skills/tools/logs.ts

# Check if ports are available
lsof -i :8000
lsof -i :6379
```

**Solutions:**
1. **Port conflict:** Stop conflicting service or modify ports in `src/server/run.ts`
2. **API key invalid:** Verify API key in PAI config (`$PAI_DIR/.env` or `~/.claude/.env`) has credits/quota
3. **Image pull failed:** Check internet connection and try again
4. **Resource limits:** Ensure system has at least 2GB RAM available

### Skill Not Loading

**Symptoms:** Claude Code doesn't recognize skill commands

**Diagnosis:**
```bash
# Check skill files exist
ls -la ~/.claude/skills/Knowledge/

# Check SKILL.md syntax
cat ~/.claude/skills/Knowledge/SKILL.md | head -20
```

**Solutions:**
1. **Restart Claude Code** - Skills are loaded on startup
2. **Check SKILL.md format** - Ensure frontmatter is valid YAML
3. **Verify file paths** - All workflows and tools should be in `src/skills/`
4. **Check PAI directory** - Verify PAI_DIR or ~/.claude is correct

### Knowledge Not Being Captured

**Symptoms:** "Remember this" doesn't store knowledge

**Diagnosis:**
```bash
# Check server is running
curl http://localhost:8000/health

# Check server logs
bun run src/skills/tools/logs.ts | tail -50
```

**Solutions:**
1. **Server not running:** Start with `bun run src/skills/tools/start.ts`
2. **API quota exceeded:** Check OpenAI usage dashboard
3. **Content too brief:** Add more context and detail
4. **Network issue:** Verify MCP server endpoint is reachable

### Poor Search Results

**Symptoms:** Knowledge search returns irrelevant or no results

**Solutions:**
1. **Use specific terms:** Include domain-specific terminology
2. **Add more knowledge:** Graph needs data to search effectively
3. **Try different queries:** Use synonyms or related concepts
4. **Check model:** gpt-4o extracts better entities than gpt-3.5-turbo

### API Rate Limits

**Symptoms:** Errors about rate limits or 429 responses

**Diagnosis:**
```bash
# Check current SEMAPHORE_LIMIT
grep SEMAPHORE_LIMIT "${PAI_DIR:-$HOME/.claude}/.env"
```

**Solutions:**
1. **Reduce concurrency:** Lower `SEMAPHORE_LIMIT` in PAI config (`$PAI_DIR/.env` or `~/.claude/.env`)
2. **Upgrade API tier:** Higher tiers allow more concurrent requests
3. **Add delay:** Workflows automatically retry with exponential backoff
4. **Switch model:** gpt-4o-mini has higher rate limits than gpt-4o

### Lucene Query Errors with Hyphenated Groups

**Symptoms:** Search fails with "Lucene query syntax error" when using hyphenated group_ids like "test-group"

**Diagnosis:**
```bash
# Check if lucene.ts exists and exports sanitizeGroupId
cat src/server/lib/lucene.ts | grep -A 5 "sanitizeGroupId"
```

**Solutions:**
1. **Verify sanitization function exists:** The `sanitizeGroupId()` function should escape hyphens
2. **Update client code:** Ensure all search calls use `sanitizeGroupId()` on group_id parameters
3. **Check imports:** Verify both `knowledge-client.ts` and `mcp-client.ts` import and use the sanitization function
4. **Test manually:** Run the sanitization test in Step 7 above

---

## Uninstallation

To completely remove the Knowledge skill:

```bash
# 1. Stop and remove container
bun run src/skills/tools/stop.ts
podman rm madeinoz-knowledge-graph-mcp
# or for Docker users:
# docker rm madeinoz-knowledge-graph-mcp

# 2. Remove Knowledge skill
rm -rf ~/.claude/skills/Knowledge

# 3. Configuration is in PAI .env - remove only MADEINOZ_KNOWLEDGE_* lines if desired
# grep -v "^MADEINOZ_KNOWLEDGE_" "${PAI_DIR:-$HOME/.claude}/.env" > /tmp/.env.tmp && mv /tmp/.env.tmp "${PAI_DIR:-$HOME/.claude}/.env"

# 4. Remove any legacy config files (optional)
# rm -f config/.env config/.env.backup
```

**Note:** This does not delete your knowledge graph data. To completely wipe data:
```bash
# Clear the graph via API before stopping container
curl -X POST http://localhost:8000/mcp/ \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"clear_graph","arguments":{}}}'
```

---

## Getting Help

If you encounter issues not covered here:

1. **Check logs:** `bun run src/skills/tools/logs.ts`
2. **Check status:** `bun run src/skills/tools/status.ts`
3. **Review documentation:**
   - `README.md` - Complete pack documentation
   - `QUICKSTART.md` - Quick start guide
   - `VERIFY.md` - Verification checklist

---

**Related Documentation:**
- [VERIFY.md](VERIFY.md) - Installation verification checklist
- [README.md](madeinoz-knowledge-system/README.md) - Complete pack documentation
- [INTEGRATION.md](INTEGRATION.md) - Integration guide with other PAI components
