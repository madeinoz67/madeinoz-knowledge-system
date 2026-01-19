---
title: "Installation Verification"
description: "Comprehensive verification checklist for Madeinoz Knowledge System installation"
---

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

## Section 2: MCP Server Verification

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

### 3.2 SKILL.md Frontmatter

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

## Section 4: Configuration Verification

Verify all configuration is correct.

> **PAI .env is the ONLY source of truth.**
>
> All MADEINOZ_KNOWLEDGE_* configuration lives in `${PAI_DIR}/.env`.

### 4.1 PAI Global Configuration

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

### 4.2 MCP Server Configuration

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

## Section 5: End-to-End Functionality

> **FOR AI AGENTS:** This is the CRITICAL verification section. It tests actual knowledge operations.
> ALL tests MUST pass for the installation to be considered complete.

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

**Expected result:** JSON response with search results

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

**Expected result:** JSON response with facts/relationships

---

## Section 6: Integration Verification

Verify integration with PAI system and Claude Code.

### 6.1 PAI Skill Recognition

- [ ] **Claude Code recognizes the skill**

**Verification:**
1. Restart Claude Code
2. In Claude Code, type: `What is the Madeinoz Knowledge System?`
3. Check if Claude mentions the skill

**Expected result:** Claude is aware of the Madeinoz Knowledge System skill

---

### 6.2 Workflow Invocation

- [ ] **Workflows can be invoked via natural language**

**Verification:**
In Claude Code, try each trigger phrase:

1. "Show the knowledge graph status" → Should invoke GetStatus
2. "Remember that this is a test" → Should invoke CaptureEpisode
3. "What do I know about PAI?" → Should invoke SearchKnowledge

**Expected result:** Claude Code follows the workflow instructions

---

## Section 7: Memory Sync Hook Verification

Verify the memory sync hook is properly installed for syncing learnings and research to the knowledge graph.

### 7.1 Hook Files Installed

- [ ] **Hook scripts exist in PAI hooks directory**
- [ ] **Hook lib files exist**

**Verification commands:**
```bash
PAI_HOOKS="$HOME/.claude/hooks"
ls -la "$PAI_HOOKS/"
ls -la "$PAI_HOOKS/lib/"
```

**Expected result:** sync-memory-to-knowledge.ts, sync-learning-realtime.ts, and lib/ directory with support files

---

### 7.2 Hooks Registered in settings.json

- [ ] **SessionStart hook registered** (sync-memory-to-knowledge.ts)
- [ ] **Stop hook registered** (sync-learning-realtime.ts)
- [ ] **SubagentStop hook registered** (sync-learning-realtime.ts)

**Verification commands:**
```bash
SETTINGS="$HOME/.claude/settings.json"
if [ -f "$SETTINGS" ]; then
    echo "Checking hooks in settings.json..."

    if grep -q "sync-memory-to-knowledge" "$SETTINGS"; then
        echo "✓ SessionStart: sync-memory-to-knowledge.ts registered"
    else
        echo "✗ SessionStart: sync-memory-to-knowledge.ts NOT registered"
    fi

    if grep -q '"Stop"' "$SETTINGS" && grep -q "sync-learning-realtime" "$SETTINGS"; then
        echo "✓ Stop: sync-learning-realtime.ts registered"
    else
        echo "✗ Stop: sync-learning-realtime.ts NOT registered"
    fi
fi
```

**Expected result:** All three hooks registered

---

## Section 8: Documentation Verification

Verify all documentation is complete and accurate.

### 8.1 README.md Completeness

- [ ] **README.md has all required sections**
- [ ] **README.md has proper YAML frontmatter**

**Verification commands:**
```bash
grep "^##" README.md | head -20
head -35 README.md | grep "^---"
```

**Expected result:** All major sections listed, frontmatter present

---

## Verification Summary

### Pass Criteria

For a successful installation, you must have:

**Critical (ALL must pass):**
- Database backend detected (Section 0)
- All files in correct locations (Section 1)
- MCP server running and accessible (Section 2)
- PAI skill installed (Section 3)
- Configuration complete with valid API key (Section 4)
- End-to-end functionality working (Section 5)
- MCP configured in ~/.claude.json (Section 4.2)

**Important (at least 80% pass):**
- Integration with Claude Code (Section 6)
- Memory sync hook installed (Section 7)
- Documentation complete (Section 8)

---

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
