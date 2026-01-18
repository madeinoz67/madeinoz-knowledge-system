# Documentation Index

Quick navigation for the Madeinoz Knowledge System user documentation.

## Getting Started

Start here if you're new to the system:

1. **[Overview and Quick Start](README.md)** - What the system does and your first steps
2. **[Installation Guide](installation.md)** - Step-by-step setup instructions
3. **[Usage Guide](usage.md)** - How to use all features with examples

## Deep Dive

For understanding how everything works:

4. **[Key Concepts](concepts.md)** - Understanding episodes, entities, facts, and graphs
5. **[Troubleshooting](troubleshooting.md)** - Fix common issues

## Documentation Structure

### README.md (Start Here)
- What is the Madeinoz Knowledge System?
- What can you do with it?
- Quick start tutorial
- Common use cases
- Key concepts overview
- Tips for success

**Read this if:** You're new and want to understand what this system does.

### installation.md
- Prerequisites and requirements
- Step-by-step installation
- Configuration options
- Starting and stopping the server
- Verification steps
- Optional features

**Read this if:** You need to install or set up the system.

### usage.md
- Capturing knowledge (all methods)
- Searching your knowledge base
- Finding connections between concepts
- Reviewing recent additions
- Managing your knowledge
- Advanced usage patterns
- Best practices and tips

**Read this if:** You want to know how to use specific features.

### concepts.md
- What is a knowledge graph?
- Episodes, entities, facts explained
- Groups and organization
- How knowledge flows through the system
- Technical architecture
- Embeddings and semantic search
- Design decisions and trade-offs
- Limitations and performance

**Read this if:** You want to understand how the system works internally.

### troubleshooting.md
- Quick diagnostics
- Common problems and solutions
- Error messages explained
- Performance issues
- API and cost management
- Diagnostic commands
- Getting help

**Read this if:** Something isn't working correctly.

## By Topic

### Installation and Setup
- [Prerequisites](installation.md#what-youll-need)
- [Getting an API Key](installation.md#step-1-get-your-api-key)
- [Installing Podman](installation.md#step-2-check-if-you-have-podman)
- [Configuring the System](installation.md#step-5-configure-your-api-key)
- [Starting the Server](installation.md#step-6-start-the-knowledge-system)
- [Memory Sync Setup](installation.md#step-9-install-memory-sync-hook-optional-but-recommended)

### Basic Usage
- [Capturing Knowledge](usage.md#capturing-knowledge)
- [Searching](usage.md#searching-knowledge)
- [Finding Connections](usage.md#finding-connections)
- [Recent Additions](usage.md#reviewing-your-knowledge)
- [Getting Status](usage.md#getting-system-status)

### Advanced Features
- [Bulk Import](usage.md#bulk-import)
- [Backup and Restore](usage.md#backup-and-restore)
- [Multiple Knowledge Graphs](usage.md#working-with-multiple-knowledge-graphs)
- [Memory System Integration](usage.md#integration-with-other-pai-systems)
- [Custom Models](installation.md#using-a-different-ai-model)

### Understanding the System
- [What is a Knowledge Graph?](concepts.md#the-knowledge-graph)
- [Episodes Explained](concepts.md#1-episodes)
- [Entity Types](concepts.md#2-entities)
- [Relationships](concepts.md#3-facts-relationships)
- [How Search Works](concepts.md#searching-knowledge)
- [Vector Embeddings](concepts.md#5-embeddings)

### Troubleshooting
- [Connection Issues](troubleshooting.md#cannot-connect-to-server-or-connection-refused)
- [API Key Problems](troubleshooting.md#api-key-not-configured-or-invalid-api-key)
- [Poor Extraction Quality](troubleshooting.md#no-entities-extracted-or-poor-extraction-quality)
- [Server Won't Start](troubleshooting.md#container-wont-start)
- [Search Issues](troubleshooting.md#search-returns-no-results)
- [Rate Limits](troubleshooting.md#rate-limit-exceeded-or-api-errors)

## Quick Reference

### Common Commands

**Server Management:**
```bash
# Check status
bun run src/server/status.ts

# Start server
bun run src/server/start.ts

# Stop server
bun run src/server/stop.ts

# View logs
bun run src/server/logs.ts
```

**Memory Sync:**
```bash
# Manual sync
bun run src/hooks/sync-memory-to-knowledge.ts

# Dry run (see what would sync)
bun run src/hooks/sync-memory-to-knowledge.ts --dry-run

# Verbose output
bun run src/hooks/sync-memory-to-knowledge.ts --verbose
```

**Backup and Restore - Neo4j (Default):**
```bash
# Podman
podman exec madeinoz-knowledge-neo4j neo4j-admin database dump neo4j --to-stdout > backups/knowledge-backup.dump
podman volume export madeinoz-knowledge-neo4j-data > backups/volume-backup.tar

# Docker
docker exec madeinoz-knowledge-neo4j neo4j-admin database dump neo4j --to-stdout > backups/knowledge-backup.dump
```

**Backup and Restore - FalkorDB Backend:**
```bash
# Podman
podman exec madeinoz-knowledge-falkordb redis-cli BGSAVE
podman cp madeinoz-knowledge-falkordb:/data/dump.rdb ./backups/knowledge-backup.rdb
podman volume export madeinoz-knowledge-data > backups/volume-backup.tar

# Docker
docker exec madeinoz-knowledge-falkordb redis-cli BGSAVE
docker cp madeinoz-knowledge-falkordb:/data/dump.rdb ./backups/knowledge-backup.rdb
```

### Natural Language Commands

**Capture:**
- "Remember that..."
- "Store this..."
- "Add to my knowledge..."

**Search:**
- "What do I know about X?"
- "Search my knowledge for X"
- "Find information about X"

**Relationships:**
- "How are X and Y related?"
- "What's the connection between X and Y?"

**Recent:**
- "What did I learn recently?"
- "Show me recent knowledge"

**Status:**
- "Knowledge graph status"
- "Show me stats"

## File Locations

**Configuration:**
- All config: `$PAI_DIR/.env` (defaults to `~/.claude/.env`)
- MCP settings: `~/.claude.json`
- Config template: `config/.env.example` (reference only)

**Server Scripts:**
- Run: `src/server/run.ts`
- Start: `src/server/start.ts`
- Stop: `src/server/stop.ts`
- Status: `src/server/status.ts`
- Logs: `src/server/logs.ts`

**Skills and Workflows:**
- Main skill: `src/skills/SKILL.md`
- Workflows: `src/skills/workflows/*.md`
- Tools: `src/skills/tools/*.md`

**Hooks:**
- Sync hook: `src/hooks/sync-memory-to-knowledge.ts`
- Realtime sync: `src/hooks/sync-learning-realtime.ts`
- Hook libraries: `src/hooks/lib/*.ts`

## Related Documentation

**Technical Documentation:**
- [Main README](../README.md) - Technical overview
- [Installation Instructions](../INSTALL.md) - Detailed installation
- [Verification Guide](../VERIFY.md) - Installation verification

**External Resources:**
- [Graphiti Documentation](https://help.getzep.com/graphiti)
- [Neo4j Documentation](https://neo4j.com/docs/)
- [FalkorDB Documentation](https://docs.falkordb.com/)
- [OpenAI API Documentation](https://platform.openai.com/docs)

## Need Help?

1. Check [Troubleshooting Guide](troubleshooting.md)
2. Review relevant concept in [Concepts](concepts.md)
3. Look for examples in [Usage Guide](usage.md)
4. Check the technical [README](../README.md)

## Quick Start Path

For fastest setup:

1. Read [README.md](README.md) - 5 minutes
2. Follow [installation.md](installation.md#step-by-step-installation) - 15 minutes
3. Try examples in [usage.md](usage.md#capturing-knowledge) - 10 minutes
4. Reference [troubleshooting.md](troubleshooting.md) if needed

Total time to get started: 30 minutes
