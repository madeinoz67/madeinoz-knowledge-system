# Install Knowledge System

Workflow for installing and configuring the Madeinoz Knowledge System.

## When to Use

Use this workflow when the user requests:
- "install knowledge"
- "setup knowledge system"
- "configure knowledge graph"
- "install knowledge system"

## Prerequisites Check

Before installation, verify:

1. **Container runtime available:**
   ```bash
   command -v podman || command -v docker
   ```

2. **Bun runtime installed:**
   ```bash
   command -v bun
   ```

3. **API key configured:**
   - Check for `MADEINOZ_KNOWLEDGE_OPENAI_API_KEY` in PAI config (`$PAI_DIR/.env` or `~/.claude/.env`)
   - Legacy `OPENAI_API_KEY` is also supported but `MADEINOZ_KNOWLEDGE_*` prefix is preferred

4. **Neo4j connection configured (for Neo4j backend):**
   - Add to PAI config (`~/.claude/.env`):
     ```bash
     MADEINOZ_KNOWLEDGE_NEO4J_URI=bolt://neo4j:7687
     MADEINOZ_KNOWLEDGE_NEO4J_USER=neo4j
     MADEINOZ_KNOWLEDGE_NEO4J_PASSWORD=madeinozknowledge
     ```
   - Note: Use `bolt://neo4j:7687` (container hostname) not `bolt://localhost:7687`

## Installation Steps

### Step 1: Start MCP Server

```bash
cd /path/to/madeinoz-knowledge-system
bun run server-cli start
```

### Step 2: Verify Server Health

```bash
curl -s http://localhost:8000/health
```

Expected: `{"status":"healthy"}`

### Step 3: Install Skill

```bash
PAI_SKILLS_DIR="${PAI_DIR:-$HOME/.claude}/skills"
cp -r src/skills "$PAI_SKILLS_DIR/Knowledge"
```

### Step 4: Configure MCP in Claude

Add to `~/.claude.json`:
```json
{
  "mcpServers": {
    "madeinoz-knowledge": {
      "type": "http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

### Step 5: Restart Claude Code

Restart Claude Code to load the MCP configuration.

## Verification

After installation, test with:

1. **Check status:** "Show knowledge graph status"
2. **Capture test:** "Remember that Madeinoz Knowledge System is now installed"
3. **Search test:** "What do I know about PAI?"

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Server won't start | Check logs: `bun run server-cli logs` |
| MCP tools not available | Verify `~/.claude.json` has madeinoz-knowledge entry |
| API errors (401) | Check API key is valid and has quota |
| Neo4j connection errors | Verify `MADEINOZ_KNOWLEDGE_NEO4J_URI=bolt://neo4j:7687` in `~/.claude/.env` |
| Env file has wrong URI | Run `bun run stop && bun run start` to regenerate env files |

## Related

- `INSTALL.md` - Full installation guide in pack root
- `VERIFY.md` - Complete verification checklist
- `diagnose.ts` - Diagnostic tool for troubleshooting
