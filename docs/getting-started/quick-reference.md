---
title: "Quick Reference Card"
description: "One-page reference guide for common commands and configurations in the Madeinoz Knowledge System"
---

# Quick Reference Card

One-page reference for the Madeinoz Knowledge System.

## Natural Language Commands

### Capture Knowledge
```
"Remember that [your knowledge]"
"Store this: [information]"
"Add to my knowledge: [details]"
"Save this: [content]"
```

### Search Knowledge
```
"What do I know about [topic]?"
"Search my knowledge for [subject]"
"Find information about [concept]"
"What have I learned about [theme]?"
```

### Filter by Entity Type
```
"Find my procedures about [topic]"
"Search for learnings about [subject]"
"Show research about [concept]"
"What decisions have I made about [theme]?"
"Find my preferences for [setting]"
```

### Find Connections
```
"How are [X] and [Y] related?"
"What's the connection between [A] and [B]?"
"Show me relationships with [topic]"
```

### Review Recent
```
"What did I learn recently?"
"Show me recent knowledge"
"Latest additions about [topic]"
```

### System Status
```
"Knowledge graph status"
"Show me knowledge stats"
"Is the system healthy?"
```

## Server Management

### Status
```bash
cd ~/.config/pai/Packs/madeinoz-knowledge-system
bun run server-cli status
```

### Start
```bash
bun run server-cli start
```

### Stop
```bash
bun run server-cli stop
```

### Logs
```bash
bun run server-cli logs
```

### Restart
```bash
bun run server-cli restart
```

## Configuration File

Location: `$PAI_DIR/.env` (defaults to `~/.claude/.env`)

Key settings:
```bash
# Required: Your API key
MADEINOZ_KNOWLEDGE_OPENAI_API_KEY=sk-your-key-here

# Model selection (cost vs quality)
MADEINOZ_KNOWLEDGE_MODEL_NAME=gpt-4o-mini

# Concurrency (lower = fewer rate limits)
MADEINOZ_KNOWLEDGE_SEMAPHORE_LIMIT=10

# Knowledge graph group
MADEINOZ_KNOWLEDGE_GROUP_ID=main
```

## Entity Types

The system automatically extracts:

**Core Types:**

- **Person** - Individual people
- **Organization** - Companies, teams
- **Location** - Places, servers
- **Concept** - Ideas, technologies
- **Procedure** - How-to guides
- **Preference** - Your choices
- **Requirement** - Specifications
- **Event** - Occurrences
- **Document** - Files, articles

**Memory-Derived Types (from PAI Memory sync):**

- **Learning** - Knowledge from learning sessions
- **Research** - Findings from research
- **Decision** - Architectural/strategic choices
- **Feature** - Feature implementations

Use these types to filter searches: "Find my procedures about X"

## Knowledge Flow

```
1. You say "remember this"
       ↓
2. PAI Skill captures intent
       ↓
3. MCP Server receives content
       ↓
4. LLM extracts entities (gpt-4o-mini)
       ↓
5. LLM maps relationships
       ↓
6. Embedding model creates vectors (text-embedding-3-small)
       ↓
7. Stored in Neo4j graph (default) or FalkorDB
```

## LLM Roles

| Stage | Model | Purpose |
|-------|-------|---------|
| **Capture** | gpt-4o-mini | Entity extraction, relationship mapping |
| **Embeddings** | text-embedding-3-small | Convert text to searchable vectors |
| **Search** | text-embedding-3-small | Convert query to vector for matching |

**Cost per operation:**

- Capture: ~$0.01 (gpt-4o-mini) or ~$0.03 (gpt-4o)
- Search: ~$0.0001

## Search Caching

- **Search results cached for 5 minutes** (speeds up repeated queries)
- **Writes are never cached** (always save to database)
- **Cache clears automatically** after TTL expires

**If new knowledge doesn't appear in search:**

- Wait 5 minutes for cache refresh, **or**
- Ask a slightly different question

---

## Troubleshooting Checklist

### Issue: Can't connect
```bash
# Check if running
bun run server-cli status

# Start if needed
bun run server-cli start

# Check endpoint
curl http://localhost:8000/sse
```

### Issue: Poor extraction

- Add more detail to your captures
- Use explicit relationships
- Consider upgrading to gpt-4o model
- Provide 50+ words of context

### Issue: No search results

- Try broader search terms
- Check if knowledge was captured
- Verify you're in the right group
- Review recent additions

### Issue: Rate limits

- Reduce SEMAPHORE_LIMIT in config
- Use gpt-4o-mini instead of gpt-4o
- Check your API tier

## Best Practices

1. **Be Specific**

       - Bad: "Remember Docker"
       - Good: "Remember that Docker requires a daemon process running as root"

2. **Add Context**

       - Bad: "Remember that config"
       - Good: "Remember my VS Code config: 2-space tabs, auto-save enabled"

3. **State Relationships**

       - Bad: "Remember Podman and Docker"
       - Good: "Remember that Podman is an alternative to Docker"

4. **Review Regularly**

       - Weekly: "What did I learn this week?"
       - Monthly: Review knowledge graph status

5. **Capture Immediately**

       - Don't wait to remember details
       - Capture while context is fresh

## Costs

Typical monthly costs (gpt-4o-mini):

- Light use: $0.50-1.00
- Moderate use: $1.00-3.00
- Heavy use: $3.00-10.00

Per operation:

- Capture: ~$0.01
- Search: ~$0.0001
- Embedding: ~$0.0001

## URLs

- MCP Server: http://localhost:8000/sse
- Neo4j Browser: http://localhost:7474 (default backend)
- FalkorDB UI: http://localhost:3000 (if using FalkorDB)
- OpenAI Usage: https://platform.openai.com/usage

## File Locations

**Configuration:**

- `$PAI_DIR/.env` (defaults to `~/.claude/.env`) - All configuration

**Installed Skill Directory:**

```
~/.claude/skills/Knowledge/
├── SKILL.md                 # Skill definition with routing
├── config/.env.example      # Configuration template (reference only)
├── tools/                   # Server and CLI tools
│   ├── server-cli.ts       # Unified server CLI (start, stop, restart, status, logs)
│   ├── knowledge-cli.ts    # Knowledge CLI (add, search, status)
│   └── install.ts          # Interactive installer
├── workflows/               # Workflow definitions
│   ├── CaptureEpisode.md   # Store knowledge
│   ├── SearchKnowledge.md  # Search entities
│   ├── SearchFacts.md      # Find relationships
│   ├── SearchByDate.md     # Temporal search
│   ├── GetRecent.md        # Recent additions
│   ├── GetStatus.md        # System health
│   ├── ClearGraph.md       # Clear knowledge
│   └── BulkImport.md       # Bulk import
├── docker/                  # Container configuration
│   ├── docker-compose-*.yml
│   └── podman-compose-*.yml
└── lib/                     # Shared libraries
```

## Keyboard Shortcuts

When editing config:

- `Ctrl+O` - Save file
- `Enter` - Confirm filename
- `Ctrl+X` - Exit editor

## Docker vs Podman

The system works with both:
```bash
# Check which you have
podman --version
# or
docker --version
```

Commands are the same, the system auto-detects which to use.

## Memory Integration

PAI Memory System syncs automatically:

**Auto-sync on session start:**

Learnings and research automatically sync from `~/.claude/MEMORY/` to knowledge graph.

**Manual sync:**

```bash
bun run ~/.claude/hooks/sync-memory-to-knowledge.ts
```

**Check what will sync:**

```bash
bun run ~/.claude/hooks/sync-memory-to-knowledge.ts --dry-run
```

## Backup and Restore

### Neo4j (Default Backend)

**Podman:**
```bash
cd ~/.config/pai/Packs/madeinoz-knowledge-system
mkdir -p backups
podman exec madeinoz-knowledge-neo4j neo4j-admin database dump neo4j --to-stdout > ./backups/knowledge-backup.dump
```

**Docker:**

```bash
cd ~/.config/pai/Packs/madeinoz-knowledge-system
mkdir -p backups
docker exec madeinoz-knowledge-neo4j neo4j-admin database dump neo4j --to-stdout > ./backups/knowledge-backup.dump
```

**Verify:**

```bash
podman exec madeinoz-knowledge-neo4j cypher-shell -u neo4j -p password "MATCH (n) RETURN count(n)"
```

### FalkorDB Backend

**Podman:**

```bash
cd ~/.config/pai/Packs/madeinoz-knowledge-system
mkdir -p backups
podman exec madeinoz-knowledge-falkordb redis-cli BGSAVE
podman cp madeinoz-knowledge-falkordb:/data/dump.rdb ./backups/knowledge-backup.rdb
```

**Docker:**

```bash
cd ~/.config/pai/Packs/madeinoz-knowledge-system
mkdir -p backups
docker exec madeinoz-knowledge-falkordb redis-cli BGSAVE
docker cp madeinoz-knowledge-falkordb:/data/dump.rdb ./backups/knowledge-backup.rdb
```

**Verify:**

```bash
podman exec madeinoz-knowledge-falkordb redis-cli DBSIZE
podman exec madeinoz-knowledge-falkordb redis-cli GRAPH.LIST
```

See the [Backup & Restore Guide](../usage/backup-restore.md) for detailed instructions.

## Common Errors

**"Connection refused"**
→ Server not running. Run: `bun run server-cli start`

**"API key invalid"**
→ Check PAI config (`$PAI_DIR/.env`) has correct key

**"Port already in use"**
→ Stop other service using port 8000/7687 (Neo4j) or 6379 (FalkorDB)

**"No entities extracted"**
→ Add more detail to your capture

**"Rate limit exceeded"**
→ Reduce SEMAPHORE_LIMIT in PAI config

## Getting Help

1. Check logs: `bun run server-cli logs`
2. Read the [Troubleshooting Guide](../troubleshooting/common-issues.md)
3. Review the [Knowledge Graph Concepts](../concepts/knowledge-graph.md)
4. Check the [Architecture](../concepts/architecture.md)

## Version Info

System: Madeinoz Knowledge System v1.1.0
Components:
- Graphiti (MCP server)
- Neo4j (default graph database) or FalkorDB
- OpenAI (LLM and embeddings)

---

**Pro Tip:** Bookmark this page for quick reference while using the system!
