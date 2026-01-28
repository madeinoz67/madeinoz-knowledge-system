<!-- AI-FRIENDLY SUMMARY
Document: Verification Checklist
Purpose: Post-installation verification for Madeinoz Knowledge System
Target Audience: AI agents verifying installation completeness

Verification Sections (run in order):
0. Database Backend Detection (Neo4j or FalkorDB)
1. Directory Structure (pack files, skills, hooks, config)
2. MCP Server (containers running, health endpoint, database connection)
3. PAI Skill (installed to ~/.claude/skills/Knowledge/)
4. Configuration (env vars, MCP config, port availability)
5. End-to-End Functionality (add_memory, search_nodes, search_facts, get_episodes)
6. Neo4j Cypher Verification (Neo4j backend only)
7. Integration (Claude Code recognition, workflow invocation)
8. Memory Sync Hook (hook files, registration, config file)
9. Documentation (README, INSTALL, VERIFY completeness)
10. End-to-End Completeness (no "beyond scope" gaps)
11. Optional (performance, persistence, error handling)

Critical Pass Criteria:
- ALL sections 0-6 MUST pass
- Section 8 (hooks) MUST pass for automatic sync
- Any critical failure = installation NOT complete

Installed File Locations:
- Skill: ~/.claude/skills/Knowledge/
  - workflows/: 8 workflow files
  - tools/: CLI tools (server-cli.ts, knowledge-cli.ts)
  - lib/: shared utilities
  - server/: compose files, install.ts, diagnose.ts
- Hook: ~/.claude/hooks/sync-memory-to-knowledge.ts
- Hook lib: ~/.claude/hooks/lib/
- Config: ~/.claude/config/sync-sources.json
- MCP: ~/.claude.json (madeinoz-knowledge server entry)

Verification Commands:
- bun run server-cli status (container status)
- curl http://localhost:8000/health (MCP health)
- bun run ~/.claude/hooks/sync-memory-to-knowledge.ts --dry-run (hook test)

AI AGENT INSTRUCTIONS - Issue Tracking:
During verification, track ALL issues encountered for post-verification RCA:
- Verification steps that fail unexpectedly
- Commands that don't match documented behavior
- Missing files or incorrect paths in checklist
- Checks that pass but with warnings or anomalies
- Documentation inconsistencies (VERIFY vs INSTALL vs README)
- False positives/negatives in verification logic
- Unclear or ambiguous verification criteria

At verification completion, perform Root Cause Analysis:
1. List all issues encountered with severity (critical/warning/minor)
2. Note the section and check where each issue occurred
3. Distinguish between installation problems vs verification doc problems
4. Document any manual interventions required
5. Recommend fixes for future releases (installation OR verification)
6. Report findings to user for GitHub issue creation if warranted
-->

# Madeinoz Knowledge System - Verification Checklist

Mandatory verification checklist for the Knowledge pack installation.

**Use this checklist to verify that your installation is complete and functional.**

> **FOR AI AGENTS:** This checklist MUST be completed after installation. Follow these rules:
> 1. **Run EVERY check** - Do not skip any verification step
> 2. **Mark each item PASS or FAIL** - Keep track of results
> 3. **Stop on failures** - If a section fails, troubleshoot before continuing
> 4. **All sections must pass** - Installation is NOT complete until all checks pass
> 5. **Report failures clearly** - Tell the user which specific checks failed
> 6. **Detect database backend FIRST** - Run Section 0 to determine which backend is configured

---

## Verification Overview

This checklist ensures:
- All components are installed
- System is properly configured
- All integrations are working
- End-to-end functionality is operational

**Supports two database backends:**
- **Neo4j** (default): Native graph database with Cypher queries
- **FalkorDB**: Redis-based graph database with RediSearch

**Run through each section in order. Mark items as PASS or FAIL.**

---

## Section 0: Database Backend Detection

> **FOR AI AGENTS:** Run this FIRST to determine which backend is configured.
> The result affects which checks to run in subsequent sections.

### 0.1 Determine Configured Backend

- [ ] **Database backend identified**

**Verification commands:**
```bash
# Check PAI config for DATABASE_TYPE
grep "MADEINOZ_KNOWLEDGE_DATABASE_TYPE" "${PAI_DIR:-$HOME/.claude}/.env" 2>/dev/null

# Or check running containers
podman ps --format "{{.Names}}" | grep madeinoz-knowledge
# For Docker:
docker ps --format "{{.Names}}" | grep madeinoz-knowledge
```

**Results:**
- If `DATABASE_TYPE=neo4j` OR container `madeinoz-knowledge-neo4j` is running → **Neo4j Backend**
- If `DATABASE_TYPE=falkordb` OR container `madeinoz-knowledge-falkordb` is running → **FalkorDB Backend**
- Default (not set) → **Neo4j Backend**

**Record your backend:** [ ] FalkorDB / [ ] Neo4j

---

### 0.2 Backend-Specific Verification Notes

Based on your detected backend:

**FalkorDB Backend:**
- Check ports: 3000 (UI), 8000 (MCP)
- Skip query syntax testing (handled internally)
- Skip Neo4j-specific checks in Section 2

**Neo4j Backend:**
- Check ports: 7474 (Browser), 7687 (Bolt), 8000 (MCP)
- Query syntax is handled internally
- Run Section 6-ALT (Neo4j Cypher tests)

---

## Section 1: Directory Structure Verification

Verify all required files and directories are present.

### 1.1 Pack Root Files

- [ ] **README.md** exists in pack root
- [ ] **INSTALL.md** exists in pack root
- [ ] **VERIFY.md** exists in pack root (this file)
- [ ] **package.json** exists in pack root

**Verification commands:**
```bash
cd /path/to/madeinoz-knowledge-system
ls -la README.md INSTALL.md VERIFY.md package.json
```

**Expected result:** All four files listed

---

### 1.1b Installed Skill Root Files

- [ ] **SKILL.md** exists in installed skill directory
- [ ] **STANDARDS.md** exists in installed skill directory

**Verification commands:**
```bash
PAI_SKILLS="${PAI_DIR:-$HOME/.claude}/skills/Knowledge"
ls -la "$PAI_SKILLS/SKILL.md" "$PAI_SKILLS/STANDARDS.md"
```

**Expected result:** Both skill definition files listed

---

### 1.2 Installed Skill Directory Structure

- [ ] **workflows/** directory exists with workflow files
- [ ] **tools/** directory exists with CLI tools
- [ ] **server/** directory exists with compose files
- [ ] **lib/** directory exists with shared utilities

**Verification commands:**
```bash
PAI_SKILLS="${PAI_DIR:-$HOME/.claude}/skills/Knowledge"
ls -la "$PAI_SKILLS/workflows/"
ls -la "$PAI_SKILLS/tools/"
ls -la "$PAI_SKILLS/server/"
ls -la "$PAI_SKILLS/lib/"
```

**Expected result:** All directories exist with their respective files

---

### 1.3 Installed Workflow Files

All required workflows must be present in installed skill:

- [ ] `CaptureEpisode.md` - Add knowledge to graph
- [ ] `SearchKnowledge.md` - Search entities and summaries
- [ ] `SearchFacts.md` - Find relationships
- [ ] `SearchByDate.md` - Search with temporal filtering
- [ ] `GetRecent.md` - Retrieve recent knowledge
- [ ] `GetStatus.md` - Check system health
- [ ] `ClearGraph.md` - Delete all knowledge
- [ ] `BulkImport.md` - Import multiple documents

**Verification commands:**
```bash
PAI_SKILLS="${PAI_DIR:-$HOME/.claude}/skills/Knowledge"
ls -1 "$PAI_SKILLS/workflows/"
```

**Expected result:** All 8 workflow files listed

---

### 1.4 Installed Tool Files

Required tool files in installed skill:

- [ ] `Install.md` - Installation workflow (triggered by skill)
- [ ] `README.md` - Tools documentation
- [ ] `server-cli.ts` - Unified server CLI (start, stop, restart, status, logs)
- [ ] `knowledge-cli.ts` - Knowledge operations CLI (add, search, get)

**Verification commands:**
```bash
PAI_SKILLS="${PAI_DIR:-$HOME/.claude}/skills/Knowledge"
ls -1 "$PAI_SKILLS/tools/"
```

**Expected result:** Install.md, README.md, knowledge-cli.ts, server-cli.ts

---

### 1.5 Installed Library Files

Required shared library files in installed skill:

- [ ] `cli.ts` - CLI output utilities
- [ ] `container.ts` - Container management
- [ ] `config.ts` - Configuration loader
- [ ] `mcp-client.ts` - MCP client library

**Verification commands:**
```bash
PAI_SKILLS="${PAI_DIR:-$HOME/.claude}/skills/Knowledge"
ls -1 "$PAI_SKILLS/lib/"
```

**Expected result:** cli.ts, config.ts, container.ts, mcp-client.ts, and other utility files

---

### 1.6 Installed Server Infrastructure Files

Server infrastructure files in installed skill:

- [ ] `install.ts` - Interactive installation wizard
- [ ] `diagnose.ts` - Diagnostic and troubleshooting tool
- [ ] `podman-compose-falkordb.yml` - Podman compose file (FalkorDB)
- [ ] `docker-compose-falkordb.yml` - Docker compose file (FalkorDB)
- [ ] `podman-compose-neo4j.yml` - Podman compose file (Neo4j)
- [ ] `docker-compose-neo4j.yml` - Docker compose file (Neo4j)
- [ ] `config-neo4j.yaml` - Neo4j backend configuration
- [ ] `config-falkordb.yaml` - FalkorDB backend configuration

**Verification commands:**
```bash
PAI_SKILLS="${PAI_DIR:-$HOME/.claude}/skills/Knowledge"
ls -la "$PAI_SKILLS/server/"
```

**Expected result:** install.ts, diagnose.ts, compose files for both backends, config YAML files

---

### 1.7 Configuration Files

- [ ] `config/.env.example` exists
- [ ] `config/.mcp.json` exists
- [ ] Environment variables use `MADEINOZ_KNOWLEDGE_*` prefix

**Verification commands:**
```bash
ls -la config/
grep "MADEINOZ_KNOWLEDGE_" config/.env.example | head -5
```

**Expected result:** Config files exist with MADEINOZ_KNOWLEDGE_ prefixed variables

---

### 1.8 Installed Hook Files

- [ ] `~/.claude/hooks/sync-memory-to-knowledge.ts` exists (consolidated sync hook)
- [ ] `~/.claude/hooks/lib/` directory exists with support files
- [ ] `~/.claude/config/sync-sources.json` exists (sync configuration)

**Verification commands:**
```bash
PAI_DIR="${PAI_DIR:-$HOME/.claude}"
ls -la "$PAI_DIR/hooks/sync-memory-to-knowledge.ts"
ls -la "$PAI_DIR/hooks/lib/"
ls -la "$PAI_DIR/config/sync-sources.json"
```


---

## Section 2: MCP Server Verification

> **FOR AI AGENTS:** This section verifies the MCP server is operational. ALL checks must pass.
> If server is not running, go back to INSTALL.md Step 3 and start the server.
> **Important:** Run database-specific checks (2.3/2.4) based on your backend from Section 0.

Verify the Graphiti MCP server is running and accessible.

### 2.1 Container Status

- [ ] **Containers are running**

**Verification commands:**
```bash
# For Podman
podman ps | grep madeinoz-knowledge

# For Docker
docker ps | grep madeinoz-knowledge

# Or use the status script
PAI_SKILLS="${PAI_DIR:-$HOME/.claude}/skills/Knowledge"
bun run "$PAI_SKILLS/tools/server-cli.ts" status
```

**Expected result (FalkorDB backend):**
- Containers `madeinoz-knowledge-graph-mcp` and `madeinoz-knowledge-falkordb` listed with status "Up"

**Expected result (Neo4j backend):**
- Containers `madeinoz-knowledge-graph-mcp` and `madeinoz-knowledge-neo4j` listed with status "Up"

---

### 2.1b Image Version Match (CRITICAL)

- [ ] **Running container image version matches installed pack version**

> **FOR AI AGENTS:** This check is CRITICAL. A version mismatch means the container is running
> outdated code. If versions don't match, the user must pull the new image and restart containers.

**Verification commands:**
```bash
PAI_SKILLS="${PAI_DIR:-$HOME/.claude}/skills/Knowledge"

# Get installed pack version from SKILL.md
INSTALLED_VERSION=$(grep "^version:" "$PAI_SKILLS/SKILL.md" | head -1 | sed 's/version:[[:space:]]*//')
echo "Installed pack version: $INSTALLED_VERSION"

# Get running MCP container image version
# For Podman:
IMAGE_VERSION=$(podman ps --format "{{.Image}}" --filter "name=madeinoz-knowledge-graph-mcp" 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
# For Docker (if podman not available):
[ -z "$IMAGE_VERSION" ] && IMAGE_VERSION=$(docker ps --format "{{.Image}}" --filter "name=madeinoz-knowledge-graph-mcp" 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)

echo "Running image version: $IMAGE_VERSION"

# Compare versions
if [ "$INSTALLED_VERSION" = "$IMAGE_VERSION" ]; then
    echo "✓ Versions match: $INSTALLED_VERSION"
else
    echo "✗ VERSION MISMATCH!"
    echo "  Installed pack: $INSTALLED_VERSION"
    echo "  Running image:  $IMAGE_VERSION"
    echo ""
    echo "  To fix: Pull new image and restart containers:"
    echo "    podman pull ghcr.io/madeinoz67/madeinoz-knowledge-system:$INSTALLED_VERSION"
    echo "    bun run server-cli restart"
    exit 1
fi
```

**Expected result:** `✓ Versions match: X.Y.Z`

**If FAIL:**
1. Pull the correct image version:
   ```bash
   podman pull ghcr.io/madeinoz67/madeinoz-knowledge-system:$INSTALLED_VERSION
   # or for Docker:
   docker pull ghcr.io/madeinoz67/madeinoz-knowledge-system:$INSTALLED_VERSION
   ```
2. Update compose file image tag if needed
3. Restart containers: `bun run server-cli restart`

---

### 2.2 MCP Health Endpoint Access

- [ ] **MCP health endpoint is accessible and returns healthy status**

**Verification commands:**
```bash
curl -s http://localhost:8000/health --max-time 2
```

**Expected result:** JSON response indicating healthy status:
```json
{"status":"healthy","service":"graphiti-mcp"}
```

This confirms the MCP server is running and accepting connections.

---

### 2.3 Database Connection (FalkorDB)

> **Skip this if using Neo4j backend** - go to 2.3-ALT instead.

- [ ] **FalkorDB is responding**

**Verification commands:**
```bash
# For Podman
podman exec madeinoz-knowledge-falkordb redis-cli -p 6379 PING

# For Docker
docker exec madeinoz-knowledge-falkordb redis-cli -p 6379 PING
```

**Expected result:** `PONG`

---

### 2.3-ALT Database Connection (Neo4j)

> **Only run this if using Neo4j backend.**

- [ ] **Neo4j is responding**

**Verification commands:**
```bash
# Check Neo4j HTTP endpoint
curl -s -o /dev/null -w "%{http_code}" http://localhost:7474

# Check Neo4j Bolt protocol port
lsof -i :7687 | grep -i listen
```

**Expected result:** HTTP returns 200, port 7687 shows listening process

---

### 2.4 Database UI Access (FalkorDB)

> **Skip this if using Neo4j backend** - go to 2.4-ALT instead.

- [ ] **FalkorDB web UI is accessible on port 3000**

**Verification commands:**
```bash
# Check if port 3000 is listening
lsof -i :3000 | grep -i listen

# Or test HTTP response
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
```

**Expected result:** Port 3000 shows listening process, HTTP returns 200 or 302

**Browser verification:**
1. Open http://localhost:3000 in your browser
2. FalkorDB Browser interface should load
3. Connect using Host: `localhost`, Port: `6379`

---

### 2.4-ALT Database UI Access (Neo4j)

> **Only run this if using Neo4j backend.**

- [ ] **Neo4j Browser is accessible on port 7474**

**Verification commands:**
```bash
# Check if port 7474 is listening
lsof -i :7474 | grep -i listen

# Or test HTTP response
curl -s -o /dev/null -w "%{http_code}" http://localhost:7474
```

**Expected result:** Port 7474 shows listening process, HTTP returns 200 or 302

**Browser verification:**
1. Open http://localhost:7474 in your browser
2. Neo4j Browser interface should load
3. Connect using: bolt://localhost:7687
4. Login with neo4j / (your configured password, default: madeinozknowledge)

---

### 2.5 Server Logs (No Errors)

- [ ] **No critical errors in logs**

**Verification commands:**
```bash
PAI_SKILLS="${PAI_DIR:-$HOME/.claude}/skills/Knowledge"
bun run "$PAI_SKILLS/tools/server-cli.ts" logs 2>&1 | grep -i "error\|critical\|fatal" | head -10
```

**Expected result:** No output (or only warnings, not errors)

---

## Section 3: PAI Skill Verification

Verify the PAI skill is properly installed and formatted.

### 3.1 Skill Installation

- [ ] **Skill directory exists in PAI installation**

**Verification commands:**
```bash
# Check standard location
ls -la ~/.claude/skills/Knowledge/

# Or if using custom PAI_DIR
ls -la ${PAI_DIR:-$HOME/.claude}/skills/Knowledge/
```

**Expected result:** Directory exists with SKILL.md, STANDARDS.md, workflows/, tools/, lib/, server/

---

### 3.2 Installed Skill Structure

The installed skill should have the following structure:

- [ ] `Knowledge/SKILL.md` exists
- [ ] `Knowledge/STANDARDS.md` exists
- [ ] `Knowledge/workflows/` directory exists with 8 workflow files
- [ ] `Knowledge/tools/` directory exists with management scripts
- [ ] `Knowledge/lib/` directory exists with shared utilities
- [ ] `Knowledge/server/` directory exists with compose files and install scripts

**Verification commands:**
```bash
PAI_SKILLS="${PAI_DIR:-$HOME/.claude}/skills"
ls -la "$PAI_SKILLS/Knowledge/"
ls -la "$PAI_SKILLS/Knowledge/workflows/"
ls -la "$PAI_SKILLS/Knowledge/tools/"
ls -la "$PAI_SKILLS/Knowledge/lib/"
ls -la "$PAI_SKILLS/Knowledge/server/"
```

**Expected result:** Structure includes SKILL.md, STANDARDS.md, workflows/, tools/, lib/, server/

---

### 3.3 SKILL.md Frontmatter

- [ ] **SKILL.md has valid YAML frontmatter**
- [ ] **Frontmatter contains 'name' field**
- [ ] **Frontmatter contains 'description' field**
- [ ] **Description includes 'USE WHEN' clause**

**Verification commands:**
```bash
head -10 ~/.claude/skills/Knowledge/SKILL.md
```

**Expected result:** YAML frontmatter with name and description containing "USE WHEN"

---

### 3.4 Workflow Routing Table

- [ ] **SKILL.md contains workflow routing table**
- [ ] **All 7 workflows are listed in table**
- [ ] **Each workflow has trigger phrases**

**Verification commands:**
```bash
grep -A 20 "## Workflow Routing" ~/.claude/skills/Knowledge/SKILL.md
```

**Expected result:** Table with workflows and their triggers

---

### 3.5 Workflow Files Accessible

- [ ] **All workflow files are readable**
- [ ] **Workflow files have proper titles**
- [ ] **Workflow files follow PAI conventions**

**Verification commands:**
```bash
for file in ~/.claude/skills/Knowledge/workflows/*.md; do
    echo "Checking: $file"
    head -5 "$file"
done
```

**Expected result:** All files are readable with markdown headers

---

### 3.6 Version Tracking

- [ ] **SKILL.md has version in frontmatter**
- [ ] **Version matches pack README.md**

**Verification commands:**
```bash
PAI_SKILLS="${PAI_DIR:-$HOME/.claude}/skills"
SKILL_FILE="$PAI_SKILLS/Knowledge/SKILL.md"

# Check SKILL.md version (primary source of truth)
INSTALLED_VERSION=$(grep -E "^version:" "$SKILL_FILE" 2>/dev/null | head -1 | sed 's/version:[[:space:]]*//')
if [ -n "$INSTALLED_VERSION" ]; then
    echo "✓ Installed version: $INSTALLED_VERSION"
else
    echo "✗ No version in SKILL.md frontmatter (pre-1.2.0 or corrupted)"
fi

# Compare with pack version (if in pack directory)
if [ -f "README.md" ]; then
    PACK_VERSION=$(grep -E "^version:" README.md | head -1 | sed 's/version:[[:space:]]*//')
    echo "Pack version: $PACK_VERSION"

    if [ "$INSTALLED_VERSION" = "$PACK_VERSION" ]; then
        echo "✓ Versions match"
    else
        echo "⚠ Version mismatch: installed=$INSTALLED_VERSION, pack=$PACK_VERSION"
    fi
fi
```

**Expected result:**
- SKILL.md frontmatter contains `version: X.Y.Z`
- Version matches the pack's README.md version field
- Pre-1.2.0 installations will not have version field

---

## Section 4: Configuration Verification

Verify all configuration is correct.

> **PAI .env is the ONLY source of truth.**
>
> All MADEINOZ_KNOWLEDGE_* configuration lives in `${PAI_DIR}/.env`.
> Docker reads directly from PAI .env via the PAI_DIR environment variable.

### 4.1 Pack Environment Variables

Check the pack's local configuration:

- [ ] `config/.env.example` exists with documented variables
- [ ] Variables use `MADEINOZ_KNOWLEDGE_*` prefix

**Verification commands:**
```bash
grep "^MADEINOZ_KNOWLEDGE_" config/.env.example
```

**Expected result:** Variables like MADEINOZ_KNOWLEDGE_OPENAI_API_KEY, MADEINOZ_KNOWLEDGE_MODEL_NAME, etc.

---

### 4.2 PAI Global Configuration

Check PAI's global .env for required variables:

- [ ] **API key is set** (OPENAI_API_KEY or MADEINOZ_KNOWLEDGE_OPENAI_API_KEY)
- [ ] **LLM provider is configured**

**Verification commands:**
```bash
PAI_ENV="${PAI_DIR:-$HOME/.claude}/.env"
if [ -f "$PAI_ENV" ]; then
    echo "Checking: $PAI_ENV"
    grep -E "(OPENAI_API_KEY|MADEINOZ_KNOWLEDGE_)" "$PAI_ENV" | grep -v "^#" | sed 's/=.*/=<SET>/'
else
    echo "PAI .env not found at: $PAI_ENV"
fi
```

**Expected result:** API key shows as SET (value hidden)

---

### 4.3 PAI Configuration Verification

Verify PAI .env has the required MADEINOZ_KNOWLEDGE_* variables:

- [ ] **PAI .env exists**
- [ ] **MADEINOZ_KNOWLEDGE_* variables are set**
- [ ] **EMBEDDER_DIMENSIONS matches EMBEDDER_MODEL**

**Verification commands:**
```bash
PAI_ENV="${PAI_DIR:-$HOME/.claude}/.env"

echo "Verifying PAI .env configuration..."
echo ""
echo "PAI .env location: $PAI_ENV"
echo ""

# Step 1: Verify PAI .env exists
if [ ! -f "$PAI_ENV" ]; then
    echo "✗ PAI .env not found at: $PAI_ENV"
    echo "  Run installation from INSTALL.md Step 2"
    exit 1
fi

echo "✓ PAI .env exists"
echo ""

# Step 2: Check for MADEINOZ_KNOWLEDGE_* variables
PAI_KNOWLEDGE_VARS=$(grep "^MADEINOZ_KNOWLEDGE_" "$PAI_ENV" 2>/dev/null | wc -l | tr -d ' ')
if [ "$PAI_KNOWLEDGE_VARS" -gt 0 ]; then
    echo "✓ Found $PAI_KNOWLEDGE_VARS MADEINOZ_KNOWLEDGE_* variables"
else
    echo "✗ No MADEINOZ_KNOWLEDGE_* variables found"
    echo "  Run installation from INSTALL.md Step 2"
    exit 1
fi

# Step 3: Check key variables
echo ""
echo "Key variables:"
for var in MADEINOZ_KNOWLEDGE_LLM_PROVIDER MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS OPENAI_API_KEY MODEL_NAME; do
    VAL=$(grep "^$var=" "$PAI_ENV" 2>/dev/null | cut -d= -f2-)
    if [ -n "$VAL" ]; then
        if [[ "$var" == *"API_KEY"* ]]; then
            echo "  ✓ $var: <SET>"
        else
            echo "  ✓ $var: $VAL"
        fi
    else
        echo "  ⚠️  $var: NOT SET"
    fi
done

# Step 4: Validate embedding dimensions
echo ""
echo "Embedding validation:"
EMBEDDER_MODEL=$(grep "^MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL=" "$PAI_ENV" | cut -d= -f2-)
EMBEDDER_DIMS=$(grep "^MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS=" "$PAI_ENV" | cut -d= -f2-)

# Fall back to non-prefixed if needed
[ -z "$EMBEDDER_MODEL" ] && EMBEDDER_MODEL=$(grep "^EMBEDDER_MODEL=" "$PAI_ENV" | cut -d= -f2-)
[ -z "$EMBEDDER_DIMS" ] && EMBEDDER_DIMS=$(grep "^EMBEDDER_DIMENSIONS=" "$PAI_ENV" | cut -d= -f2-)

case "$EMBEDDER_MODEL" in
    "mxbai-embed-large")
        [ "$EMBEDDER_DIMS" = "1024" ] && echo "  ✓ $EMBEDDER_MODEL: 1024 dims (correct)" || echo "  ✗ $EMBEDDER_MODEL requires 1024, got: $EMBEDDER_DIMS"
        ;;
    "nomic-embed-text")
        [ "$EMBEDDER_DIMS" = "768" ] && echo "  ✓ $EMBEDDER_MODEL: 768 dims (correct)" || echo "  ✗ $EMBEDDER_MODEL requires 768, got: $EMBEDDER_DIMS"
        ;;
    "text-embedding-3-small")
        [ "$EMBEDDER_DIMS" = "1536" ] && echo "  ✓ $EMBEDDER_MODEL: 1536 dims (correct)" || echo "  ✗ $EMBEDDER_MODEL requires 1536, got: $EMBEDDER_DIMS"
        ;;
    *)
        echo "  ⚠️  Unknown model: $EMBEDDER_MODEL (verify dimensions manually)"
        ;;
esac

echo ""
echo "Docker reads directly from: $PAI_ENV"
echo "To update: Edit PAI .env, then restart containers"
```

**Expected result:** All MADEINOZ_KNOWLEDGE_* variables set, embedding dimensions match model

**Note:** If EMBEDDER_DIMENSIONS doesn't match your EMBEDDER_MODEL, searches will fail with "vector dimension mismatch" errors. See `docs/troubleshooting.md` → "Vector Dimension Mismatch Error" for fix instructions.

---

### 4.4 MCP Server Configuration

- [ ] **MCP server configured in ~/.claude.json**
- [ ] **madeinoz-knowledge server entry exists**
- [ ] **HTTP transport configured**

**Verification commands:**
```bash
if [ -f ~/.claude.json ]; then
    grep -A 5 "madeinoz-knowledge" ~/.claude.json
else
    echo "~/.claude.json not found"
fi
```

**Expected result:**
```json
"madeinoz-knowledge": {
  "type": "http",
  "url": "http://localhost:8000/mcp"
}
```

---

### 4.5 Port Availability

**Common port (both backends):**
- [ ] **Port 8000 is available** (or MCP server is listening)

**FalkorDB backend ports:**
- [ ] **Port 3000 is available** (or FalkorDB UI is listening)
- [ ] **Port 6379 is internal** (FalkorDB on container network)

**Neo4j backend ports:**
- [ ] **Port 7474 is available** (or Neo4j Browser is listening)
- [ ] **Port 7687 is available** (or Neo4j Bolt is listening)

**Verification commands:**
```bash
# Check MCP server port (both backends)
lsof -i :8000

# FalkorDB backend
lsof -i :3000

# Neo4j backend
lsof -i :7474
lsof -i :7687
```

**Expected result:** Either no output (port available) or madeinoz-knowledge process listed (using port)

---

## Section 5: End-to-End Functionality

> **FOR AI AGENTS:** This is the CRITICAL verification section. It tests actual knowledge operations.
> ALL tests MUST pass for the installation to be considered complete.
> If any test fails, the knowledge system is NOT functional - troubleshoot before proceeding.

Verify the complete system works end-to-end using the knowledge CLI.

> **Note:** The MCP server uses Streamable HTTP transport which requires session management.
> The `knowledge-cli.ts` handles this internally. Raw curl commands require session initialization.

### 5.1 Knowledge Capture (add_memory)

- [ ] **Can capture knowledge to graph**

**Verification commands:**
```bash
PAI_SKILLS="${PAI_DIR:-$HOME/.claude}/skills/Knowledge"
bun run "$PAI_SKILLS/tools/knowledge-cli.ts" add_episode \
    "PAI Verification Test" \
    "Madeinoz Knowledge System verification test completed successfully." \
    "verification test"
```

**Expected result:** `✓ Episode 'PAI Verification Test' queued for processing in group 'main'`

---

### 5.2 Knowledge Search (search_nodes)

- [ ] **Can search knowledge graph nodes**

**Verification commands:**
```bash
PAI_SKILLS="${PAI_DIR:-$HOME/.claude}/skills/Knowledge"
bun run "$PAI_SKILLS/tools/knowledge-cli.ts" search_nodes "verification" 5
```

**Expected result:** `Found N entities for "verification":` followed by entity list

---

### 5.3 Relationship Search (search_facts)

- [ ] **Can search relationships/facts**

**Verification commands:**
```bash
PAI_SKILLS="${PAI_DIR:-$HOME/.claude}/skills/Knowledge"
bun run "$PAI_SKILLS/tools/knowledge-cli.ts" search_facts "PAI" 5
```

**Expected result:** `Found N facts for "PAI":` followed by relationship list

---

### 5.4 Recent Episodes (get_episodes)

- [ ] **Can retrieve recent episodes**

**Verification commands:**
```bash
PAI_SKILLS="${PAI_DIR:-$HOME/.claude}/skills/Knowledge"
bun run "$PAI_SKILLS/tools/knowledge-cli.ts" get_episodes 5
```

**Expected result:** `Recent episodes (5):` followed by episode list (includes test episode from 5.1)

---

## Section 6: Neo4j Cypher Verification (Neo4j Only)

> **FOR AI AGENTS:** This section is ONLY for Neo4j backend.
> **Skip this section if using FalkorDB backend** - you should have run Section 6 instead.
> Neo4j uses Cypher queries which handle special characters natively without sanitization.

Verify that Neo4j Cypher queries work correctly with various identifiers.

### 6-ALT.1 Hyphenated Group ID Capture

- [ ] **Can capture knowledge with hyphenated group_id (no sanitization needed)**

**Verification commands:**
```bash
curl -s -X POST http://localhost:8000/mcp/ \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc":"2.0",
        "id":5,
        "method":"tools/call",
        "params":{
            "name":"add_memory",
            "arguments":{
                "name":"Neo4j Cypher Test",
                "episode_body":"Testing Neo4j Cypher with hyphenated group_id",
                "source":"text",
                "source_description":"cypher test",
                "group_id":"test-group-123"
            }
        }
    }' | head -20
```

**Expected result:** JSON response with success indication, no errors

**Why this works:** Neo4j uses Cypher query language which handles special characters in string parameters natively. No escaping or sanitization is required.

---

### 6-ALT.2 Search with Hyphenated Group ID

- [ ] **Can search knowledge using hyphenated group_id**

**Verification commands:**
```bash
curl -s -X POST http://localhost:8000/mcp/ \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc":"2.0",
        "id":6,
        "method":"tools/call",
        "params":{
            "name":"search_memory_nodes",
            "arguments":{
                "query":"cypher test",
                "max_nodes":5,
                "group_ids":["test-group-123"]
            }
        }
    }' | head -20
```

**Expected result:** JSON response with search results, no query syntax errors

---

### 6-ALT.3 Verify Neo4j Connection via Browser

- [ ] **Can execute Cypher queries in Neo4j Browser**

**Verification:**
1. Open http://localhost:7474 in your browser
2. Login with your credentials (default: neo4j / madeinozknowledge)
3. Execute a test query:
   ```cypher
   MATCH (n) RETURN count(n) as nodeCount
   ```

**Expected result:** Query returns a count of nodes in the database

---

### 6-ALT.4 Special Characters in Group ID

- [ ] **Can handle various special characters in group_id**

**Verification commands:**
```bash
curl -s -X POST http://localhost:8000/mcp/ \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc":"2.0",
        "id":8,
        "method":"tools/call",
        "params":{
            "name":"add_memory",
            "arguments":{
                "name":"Special Character Test",
                "episode_body":"Testing special characters with Neo4j Cypher",
                "source":"text",
                "source_description":"special char test",
                "group_id":"test--multiple---hyphens_and_underscores"
            }
        }
    }' | head -20
```

**Expected result:** JSON response with success indication, no errors

**Note:** Neo4j handles special characters natively in Cypher queries.

---

## Section 7: Integration Verification

Verify integration with PAI system and Claude Code.

### 7.1 PAI Skill Recognition

- [ ] **Claude Code recognizes the skill**

**Verification:**
1. Restart Claude Code
2. In Claude Code, type: `What is the Madeinoz Knowledge System?`
3. Check if Claude mentions the skill

**Expected result:** Claude is aware of the Madeinoz Knowledge System skill

---

### 7.2 Workflow Invocation

- [ ] **Workflows can be invoked via natural language**

**Verification:**
In Claude Code, try each trigger phrase:

1. "Show the knowledge graph status" → Should invoke GetStatus
2. "Remember that this is a test" → Should invoke CaptureEpisode
3. "What do I know about PAI?" → Should invoke SearchKnowledge

**Expected result:** Claude Code follows the workflow instructions

---

### 7.3 MCP Tool Access

- [ ] **Claude Code can access MCP tools**

**Verification:**
In Claude Code, the workflows reference MCP server tools. If workflows execute successfully, MCP integration is working.

Check that these tools are available:
- `mcp__madeinoz-knowledge__add_memory`
- `mcp__madeinoz-knowledge__search_memory_nodes`
- `mcp__madeinoz-knowledge__search_memory_facts`
- `mcp__madeinoz-knowledge__get_episodes`
- `mcp__madeinoz-knowledge__clear_graph`

**Expected result:** Workflows complete without MCP connection errors

---

## Section 8: Memory Sync Hook Verification

Verify the memory sync hook is properly installed for syncing learnings and research to the knowledge graph.

### 8.1 Hook Files Installed

- [ ] **Hook script exists in PAI hooks directory**
- [ ] **Hook lib files exist**
- [ ] **Config file exists in PAI config directory**

**Verification commands:**
```bash
PAI_HOOKS="$HOME/.claude/hooks"
PAI_CONFIG="$HOME/.claude/config"
ls -la "$PAI_HOOKS/"
ls -la "$PAI_HOOKS/lib/"
ls -la "$PAI_CONFIG/sync-sources.json"
```

**Expected result:**
- sync-memory-to-knowledge.ts (consolidated sync hook)
- lib/ directory with: frontmatter-parser.ts, knowledge-client.ts, sync-state.ts, sync-config.ts, anti-loop-patterns.ts
- config/sync-sources.json (sync source paths and custom exclude patterns)

---

### 8.2 Hook Registered in settings.json

- [ ] **SessionStart hook registered** (sync-memory-to-knowledge.ts)

**Verification commands:**
```bash
SETTINGS="$HOME/.claude/settings.json"
if [ -f "$SETTINGS" ]; then
    echo "Checking hooks in settings.json..."
    echo ""

    # Check SessionStart hook
    if grep -q "sync-memory-to-knowledge" "$SETTINGS"; then
        echo "✓ SessionStart: sync-memory-to-knowledge.ts registered"
    else
        echo "✗ SessionStart: sync-memory-to-knowledge.ts NOT registered"
    fi
else
    echo "✗ settings.json not found at: $SETTINGS"
fi
```

**Expected result:** SessionStart hook registered - syncs memory to knowledge graph at session start

---

### 8.3 Sync State Directory

- [ ] **Sync state directory exists**

**Verification commands:**
```bash
MEMORY_DIR="$HOME/.claude/MEMORY"
ls -la "$MEMORY_DIR/STATE/knowledge-sync/" 2>/dev/null || echo "Sync state directory not yet created (will be created on first sync)"
```

**Expected result:** Directory exists or will be created on first sync

---

### 8.4 Hook Dry Run

- [ ] **Hook runs without errors in dry-run mode**

**Verification commands:**
```bash
bun run ~/.claude/hooks/sync-memory-to-knowledge.ts --dry-run --verbose
```

**Expected result:** Hook completes without errors, shows what would be synced

---

## Section 9: Documentation Verification

Verify all documentation is complete and accurate.

### 9.1 README.md Completeness

- [ ] **README.md has all required sections**
- [ ] **README.md has proper YAML frontmatter**
- [ ] **Architecture diagrams are present**
- [ ] **Example usage is documented**

**Verification commands:**
```bash
grep "^##" README.md | head -20
head -35 README.md | grep "^---"
```

**Expected result:** All major sections listed, frontmatter present

---

### 9.2 INSTALL.md Completeness

- [ ] **INSTALL.md has pre-installation analysis**
- [ ] **INSTALL.md has step-by-step instructions**
- [ ] **INSTALL.md has troubleshooting section**
- [ ] **INSTALL.md references TypeScript files (not .sh)**

**Verification commands:**
```bash
grep "^##" INSTALL.md
grep "bun run" INSTALL.md | head -5
```

**Expected result:** Sections for Prerequisites, Pre-Installation, Steps, Troubleshooting; uses `bun run` commands

---

### 9.3 Workflow Documentation

- [ ] **Each workflow has clear purpose**
- [ ] **Each workflow has usage examples**
- [ ] **Each workflow has MCP tool references**

**Verification:**
Open and review each workflow file in `~/.claude/skills/Knowledge/workflows/`

**Expected result:** All workflows are well-documented

---

## Section 10: End-to-End Completeness

Verify the pack has no missing components (Template Requirement).

### 10.1 Chain Test

**The Chain Test:** Trace every data flow to ensure no "beyond scope" gaps.

**Data Flow 1: User Input → Knowledge Graph**
- [ ] User triggers skill (Claude Code)
- [ ] Workflow executes (SKILL.md routing)
- [ ] MCP server receives request (HTTP to localhost:8000)
- [ ] Graphiti processes episode (LLM extraction)
- [ ] Database stores data (FalkorDB or Neo4j - graph persistence)

**Verification:** All components are included in pack

---

**Data Flow 2: Knowledge Graph → User Output**
- [ ] User searches knowledge (Claude Code)
- [ ] Workflow executes (SearchKnowledge)
- [ ] MCP server receives request (HTTP)
- [ ] Graphiti searches graph (vector embeddings)
- [ ] Database returns results (FalkorDB RediSearch or Neo4j Cypher query)
- [ ] Results formatted and returned (workflow output)

**Verification:** All components are included in pack

---

### 10.2 No "Beyond Scope" Statements

- [ ] **README has no "beyond scope" statements**
- [ ] **INSTALL has no "implement your own" statements**
- [ ] **All referenced components are included**

**Verification commands:**
```bash
grep -i "beyond.*scope\|implement.*your.*own\|left as.*exercise" \
    README.md \
    INSTALL.md
```

**Expected result:** No matches (all components are included)

---

### 10.3 Complete Component List

- [ ] **MCP Server included** (server-cli.ts and compose files in installed skill)
- [ ] **FalkorDB compose files included** (`server/docker-compose-falkordb.yml`, `server/podman-compose-falkordb.yml`)
- [ ] **Neo4j compose files included** (`server/docker-compose-neo4j.yml`, `server/podman-compose-neo4j.yml`)
- [ ] **PAI Skill included** (`SKILL.md` with workflows at `~/.claude/skills/Knowledge/`)
- [ ] **Workflows included** (8 workflow files in `~/.claude/skills/Knowledge/workflows/`)
- [ ] **Skill tools included** (server-cli.ts, knowledge-cli.ts in `~/.claude/skills/Knowledge/tools/`)
- [ ] **Server tools included** (install.ts, diagnose.ts in `~/.claude/skills/Knowledge/server/`)
- [ ] **Hooks included** (sync-memory-to-knowledge.ts in `~/.claude/hooks/`, consolidated sync hook)
- [ ] **Installation included** (`INSTALL.md` with all steps and database backend selection)
- [ ] **Configuration included** (`config/.env.example` with all variables for both backends, `config/sync-sources.json` for sync configuration)
- [ ] **Documentation included** (README, INSTALL, VERIFY)
- [ ] **Tests included** (`tests/` directory with unit and integration tests)
- [ ] **No external dependencies** beyond documented prerequisites

**Verification:** Manual review of pack contents

---

## Section 11: Optional Verification

Optional but recommended checks.

### 11.1 Performance Test

- [ ] **Knowledge capture completes in < 30 seconds**
- [ ] **Search completes in < 10 seconds**
- [ ] **Server responds to health check in < 1 second**

**Verification:**
```bash
time curl -s http://localhost:8000/health
```

---

### 11.2 Data Persistence

- [ ] **Knowledge persists across container restarts**

**Verification:**
1. Add test knowledge
2. Restart containers: `bun run ~/.claude/skills/Knowledge/tools/server-cli.ts restart`
3. Search for test knowledge
4. Verify it's still there

---

### 11.3 Error Handling

- [ ] **Invalid API key returns clear error**
- [ ] **Server unavailable handled gracefully in workflows**
- [ ] **Empty search results handled gracefully**

**Verification:**
Test error scenarios and verify helpful error messages

---

### 11.4 Run Tests

- [ ] **Unit tests pass**
- [ ] **Integration tests pass**

**Verification commands:**
```bash
cd /path/to/madeinoz-knowledge-system
bun test
```

**Expected result:** All tests pass

---

## Verification Summary

> **FOR AI AGENTS:** Review this summary to confirm installation success.
> - ALL "Critical" items MUST pass - no exceptions
> - Report the final status clearly to the user
> - If any critical item fails, installation is NOT complete

### Pass Criteria

For a successful installation, you must have:

**Critical (ALL must pass):**
- Database backend detected (Section 0)
- All files in correct locations (Section 1)
- MCP server running and accessible (Section 2)
- **Image version matches installed pack version (Section 2.1b)**
- Database container running (Section 2.3 for FalkorDB OR 2.3-ALT for Neo4j)
- PAI skill installed with flat structure (Section 3)
- Configuration complete with valid API key (Section 4)
- End-to-end functionality working (Section 5)
- Query handling verified (Section 6 for Neo4j Cypher)
- MCP configured in ~/.claude.json (Section 4.3)
- No "beyond scope" gaps (Section 10)

**Important (at least 80% pass):**
- Integration with Claude Code (Section 7)
- Memory sync hook installed (Section 8) - for automatic knowledge sync
- Documentation complete (Section 9)

### Failure Actions

If any critical item fails:

1. **Review logs:** `bun run ~/.claude/skills/Knowledge/tools/server-cli.ts logs`
2. **Check configuration:** Verify PAI .env has required MADEINOZ_KNOWLEDGE_* variables
3. **Re-run installation:** Follow `INSTALL.md` steps again
4. **Check troubleshooting:** Review troubleshooting section in `INSTALL.md`
5. **Run diagnostics:** `bun run ~/.claude/skills/Knowledge/server/diagnose.ts`

### Final Verification

Once all checks pass:

- [ ] **Create a test episode** in Claude Code: "Remember that I've successfully installed the Madeinoz Knowledge System"
- [ ] **Search for it**: "What do I know about the Madeinoz Knowledge System installation?"
- [ ] **Verify it's returned**: The search should find your test episode

**If all three steps work, your installation is complete and verified!**

---

**Verification completed:** _______________

**Verified by:** _______________

**Database backend:** [ ] FalkorDB / [ ] Neo4j

**Result:** PASS / FAIL

---

**Next Steps:**
- If PASS: Start using the Madeinoz Knowledge System!
- If FAIL: Review failed items, re-install as needed, and re-verify
