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

### 1.1b Skill Root Files (src/skills/)

- [ ] **SKILL.md** exists in src/skills/
- [ ] **STANDARDS.md** exists in src/skills/ (usage standards)

**Verification commands:**
```bash
ls -la src/skills/SKILL.md src/skills/STANDARDS.md
```

**Expected result:** Both skill definition files listed

---

### 1.2 Source Directory Structure

- [ ] **src/skills/workflows/** directory exists
- [ ] **src/skills/tools/** directory exists
- [ ] **src/server/** directory exists
- [ ] **src/hooks/** directory exists
- [ ] **config/** directory exists

**Verification commands:**
```bash
ls -la src/skills/workflows/
ls -la src/skills/tools/
ls -la src/server/
ls -la src/hooks/
ls -la config/
```

**Expected result:** Directories exist with workflow, tool, server, and hook files

---

### 1.3 Workflow Files

All required workflows must be present:

- [ ] `CaptureEpisode.md` - Add knowledge to graph
- [ ] `SearchKnowledge.md` - Search entities and summaries
- [ ] `SearchFacts.md` - Find relationships
- [ ] `GetRecent.md` - Retrieve recent knowledge
- [ ] `GetStatus.md` - Check system health
- [ ] `ClearGraph.md` - Delete all knowledge
- [ ] `BulkImport.md` - Import multiple documents

**Verification commands:**
```bash
ls -1 src/skills/workflows/
```

**Expected result:** All 7 workflow files listed

---

### 1.4 Skill Tool Files

Required tool files in `src/skills/tools/` (installed with skill):

- [ ] `Install.md` - Installation workflow (triggered by skill)
- [ ] `README.md` - Tools documentation
- [ ] `start.ts` - Start containers
- [ ] `stop.ts` - Stop containers
- [ ] `status.ts` - Show container status
- [ ] `logs.ts` - View container logs

**Verification commands:**
```bash
ls -1 src/skills/tools/
```

**Expected result:** Install.md, README.md, logs.ts, start.ts, status.ts, stop.ts

---

### 1.5 Skill Library Files

Required shared library in `src/skills/lib/` (installed with skill):

- [ ] `cli.ts` - CLI output utilities
- [ ] `container.ts` - Container management

**Verification commands:**
```bash
ls -1 src/skills/lib/
```

**Expected result:** cli.ts, container.ts

---

### 1.6 Server Infrastructure Files

Pack-level files in `src/server/` (not installed with skill):

- [ ] `server-cli.ts` - Unified server CLI (start, stop, restart, status, logs)
- [ ] `install.ts` - Interactive installation wizard
- [ ] `diagnose.ts` - Diagnostic and troubleshooting tool
- [ ] `mcp-wrapper.ts` - MCP protocol wrapper
- [ ] `podman-compose-falkordb.yml` - Podman compose file (FalkorDB)
- [ ] `docker-compose-falkordb.yml` - Docker compose file (FalkorDB)
- [ ] `podman-compose-neo4j.yml` - Podman compose file (Neo4j)
- [ ] `docker-compose-neo4j.yml` - Docker compose file (Neo4j)
- [ ] `config-neo4j.yaml` - Neo4j backend configuration
- [ ] `lib/` - Full library (cli, config, container, mcp-client)

**Verification commands:**
```bash
ls -la src/server/
ls -la src/server/lib/
```

**Expected result:** server-cli.ts, install.ts, diagnose.ts, mcp-wrapper.ts, compose files for both backends, config-neo4j.yaml, and lib/ directory

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

### 1.8 Hook Files

- [ ] `src/hooks/sync-memory-to-knowledge.ts` exists
- [ ] `src/hooks/sync-learning-realtime.ts` exists
- [ ] `src/hooks/lib/` directory exists with support files

**Verification commands:**
```bash
ls -la src/hooks/
ls -la src/hooks/lib/
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
bun run src/skills/tools/status.ts
```

**Expected result (FalkorDB backend):**
- Containers `madeinoz-knowledge-graph-mcp` and `madeinoz-knowledge-falkordb` listed with status "Up"

**Expected result (Neo4j backend):**
- Containers `madeinoz-knowledge-graph-mcp` and `madeinoz-knowledge-neo4j` listed with status "Up"

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
bun run src/skills/tools/logs.ts 2>&1 | grep -i "error\|critical\|fatal" | head -10
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

**Expected result:** Directory exists with SKILL.md, STANDARDS.md, workflows/, tools/

---

### 3.2 Installed Skill Structure

The installed skill is a copy of `src/skills/` directory:

- [ ] `Knowledge/SKILL.md` exists
- [ ] `Knowledge/STANDARDS.md` exists
- [ ] `Knowledge/workflows/` directory exists with 7 workflow files
- [ ] `Knowledge/tools/` directory exists with management scripts
- [ ] `Knowledge/lib/` directory exists with shared utilities

**Verification commands:**
```bash
PAI_SKILLS="${PAI_DIR:-$HOME/.claude}/skills"
ls -la "$PAI_SKILLS/Knowledge/"
ls -la "$PAI_SKILLS/Knowledge/workflows/"
ls -la "$PAI_SKILLS/Knowledge/tools/"
ls -la "$PAI_SKILLS/Knowledge/lib/"
```

**Expected result:** Structure matches `src/skills/` with SKILL.md, STANDARDS.md, workflows/, tools/, lib/

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

Verify the complete system works end-to-end using the actual MCP tools.

### 5.1 Knowledge Capture (add_memory)

- [ ] **Can capture knowledge to graph**

**Verification commands:**
```bash
curl -s -X POST http://localhost:8000/mcp/ \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc":"2.0",
        "id":1,
        "method":"tools/call",
        "params":{
            "name":"add_memory",
            "arguments":{
                "name":"PAI Verification Test",
                "episode_body":"Madeinoz Knowledge System verification test completed successfully.",
                "source":"text",
                "source_description":"verification test"
            }
        }
    }' | head -20
```

**Expected result:** JSON response with success indication, no errors

---

### 5.2 Knowledge Search (search_memory_nodes)

- [ ] **Can search knowledge graph nodes**

**Verification commands:**
```bash
curl -s -X POST http://localhost:8000/mcp/ \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc":"2.0",
        "id":2,
        "method":"tools/call",
        "params":{
            "name":"search_memory_nodes",
            "arguments":{
                "query":"Madeinoz Knowledge System",
                "max_nodes":5
            }
        }
    }' | head -20
```

**Expected result:** JSON response with search results (may be empty if graph is new)

---

### 5.3 Relationship Search (search_memory_facts)

- [ ] **Can search relationships/facts**

**Verification commands:**
```bash
curl -s -X POST http://localhost:8000/mcp/ \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc":"2.0",
        "id":3,
        "method":"tools/call",
        "params":{
            "name":"search_memory_facts",
            "arguments":{
                "query":"PAI",
                "max_facts":5
            }
        }
    }' | head -20
```

**Expected result:** JSON response with facts/relationships (may be empty if graph is new)

---

### 5.4 Recent Episodes (get_episodes)

- [ ] **Can retrieve recent episodes**

**Verification commands:**
```bash
curl -s -X POST http://localhost:8000/mcp/ \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc":"2.0",
        "id":4,
        "method":"tools/call",
        "params":{
            "name":"get_episodes",
            "arguments":{
                "last_n":5
            }
        }
    }' | head -20
```

**Expected result:** JSON array with episodes (includes test episode from 5.1)

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

- [ ] **Hook scripts exist in PAI hooks directory**
- [ ] **Hook lib files exist**

**Verification commands:**
```bash
PAI_HOOKS="$HOME/.claude/hooks"
ls -la "$PAI_HOOKS/"
ls -la "$PAI_HOOKS/lib/"
```

**Expected result:** sync-memory-to-knowledge.ts, sync-learning-realtime.ts, and lib/ directory with:
- frontmatter-parser.ts
- knowledge-client.ts
- sync-state.ts

---

### 8.2 Hooks Registered in settings.json

- [ ] **SessionStart hook registered** (sync-memory-to-knowledge.ts)
- [ ] **Stop hook registered** (sync-learning-realtime.ts)
- [ ] **SubagentStop hook registered** (sync-learning-realtime.ts)

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

    # Check Stop hook
    if grep -q '"Stop"' "$SETTINGS" && grep -q "sync-learning-realtime" "$SETTINGS"; then
        echo "✓ Stop: sync-learning-realtime.ts registered"
    else
        echo "✗ Stop: sync-learning-realtime.ts NOT registered"
    fi

    # Check SubagentStop hook
    if grep -q '"SubagentStop"' "$SETTINGS" && grep -q "sync-learning-realtime" "$SETTINGS"; then
        echo "✓ SubagentStop: sync-learning-realtime.ts registered"
    else
        echo "✗ SubagentStop: sync-learning-realtime.ts NOT registered"
    fi
else
    echo "✗ settings.json not found at: $SETTINGS"
fi
```

**Expected result:** All three hooks registered:
- SessionStart: syncs memory at session start
- Stop: syncs learnings when execution stops
- SubagentStop: syncs when subagent completes

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
cd /path/to/madeinoz-knowledge-system
bun run src/hooks/sync-memory-to-knowledge.ts --dry-run --verbose
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
Open and review each workflow file in `src/skills/workflows/`

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

- [ ] **MCP Server included** (`src/server/server-cli.ts` and compose files)
- [ ] **FalkorDB compose files included** (`docker-compose-falkordb.yml`, `podman-compose-falkordb.yml`)
- [ ] **Neo4j compose files included** (`docker-compose-neo4j.yml`, `podman-compose-neo4j.yml`, `config-neo4j.yaml`)
- [ ] **PAI Skill included** (`SKILL.md` with workflows)
- [ ] **Workflows included** (7 complete workflows in `src/skills/workflows/`)
- [ ] **Skill tools included** (start.ts, stop.ts, status.ts, logs.ts in `src/skills/tools/`)
- [ ] **Pack tools included** (install.ts, diagnose.ts in `src/server/`)
- [ ] **Hooks included** (sync-memory-to-knowledge.ts, sync-learning-realtime.ts in `src/hooks/`)
- [ ] **Installation included** (`INSTALL.md` with all steps and database backend selection)
- [ ] **Configuration included** (`config/.env.example` with all variables for both backends)
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
2. Restart containers: `bun run src/skills/tools/stop.ts && bun run src/skills/tools/start.ts`
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

1. **Review logs:** `bun run src/skills/tools/logs.ts`
2. **Check configuration:** Verify `config/.env.example` is properly configured
3. **Re-run installation:** Follow `INSTALL.md` steps again
4. **Check troubleshooting:** Review troubleshooting section in `INSTALL.md`
5. **Run diagnostics:** `bun run src/server/diagnose.ts`

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
