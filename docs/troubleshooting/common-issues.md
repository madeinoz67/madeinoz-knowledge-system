---
title: "Troubleshooting Guide"
description: "Step-by-step solutions for common issues with the Madeinoz Knowledge System, organized by symptom"
---

# Troubleshooting Guide

This guide helps you fix common issues with the Madeinoz Knowledge System. Problems are organized by symptom with step-by-step solutions.

## Quick Diagnostics

Before diving into specific problems, run these checks:

### 1. Check if Services are Running

```bash
cd ~/.config/pai/Packs/madeinoz-knowledge-system
bun run server-cli status
```

Expected output:

```
Madeinoz Knowledge System Status:

Containers:
  madeinoz-knowledge-graph-mcp: running
  madeinoz-knowledge-neo4j: running

MCP Server: http://localhost:8000/sse
  Status: healthy
```

### 2. Check Logs

```bash
bun run server-cli logs
```

Look for errors (lines with ERROR or WARN).

### 3. Test Connectivity

```bash
curl http://localhost:8000/sse -H "Accept: text/event-stream"
```

Should see some response about the endpoint.

## Common Problems

### "Cannot connect to server" or "Connection refused"

**Symptom:** Commands fail with connection errors

**Possible Causes:**

1. Server not running
2. Wrong port
3. Firewall blocking connection

**Solutions:**

**Check if server is running:**

```bash
podman ps | grep madeinoz-knowledge
```

If nothing shows up, the server isn't running.

**Start the server:**

```bash
cd ~/.config/pai/Packs/madeinoz-knowledge-system
bun run server-cli start
```

**Check if port 8000 is in use:**

```bash
lsof -i :8000
```

If another service is using port 8000, you need to either stop that service or change the knowledge system port.

**To change the port:**

Edit the Docker Compose files (`docker-compose-neo4j.yml` or `docker-compose-falkordb.yml`) and change the port number, then restart.

### "API key not configured" or "Invalid API key"

**Symptom:** Error messages about API keys

**Check your configuration:**

```bash
cat "${PAI_DIR:-$HOME/.claude}/.env" | grep MADEINOZ_KNOWLEDGE_OPENAI_API_KEY
```

**If the key is missing or wrong:**

1. Edit the config file:

```bash
nano "${PAI_DIR:-$HOME/.claude}/.env"
```

1. Add or fix your API key:

```
MADEINOZ_KNOWLEDGE_OPENAI_API_KEY=sk-your-actual-key-here
```

1. Save (Ctrl+O, Enter, Ctrl+X)

2. Restart the server:

```bash
bun run server-cli restart
```

**Verify your key has credits:**
Visit <https://platform.openai.com/usage> to check your API usage and credits.

### "No entities extracted" or Poor Extraction Quality

**Symptom:** System captures knowledge but extracts no or few entities

**Causes:**

1. Content too short or vague
2. Model not powerful enough
3. Content lacks clear concepts

**Solutions:**

**Add more detail:**

Instead of:

```
Remember Docker
```

Try:

```
Remember that Docker is a container runtime that requires a daemon
process running as root, which manages container lifecycles and images.
```

**Use a better model:**

Edit your PAI config (`$PAI_DIR/.env` or `~/.claude/.env`):

```bash
MADEINOZ_KNOWLEDGE_MODEL_NAME=gpt-4o
```

Note: gpt-4o costs more but extracts entities better than gpt-4o-mini.

Restart the server after changing.

**Be explicit about relationships:**

Instead of:

```
Remember Podman and Docker
```

Try:

```
Remember that Podman is an alternative to Docker, designed to be
daemonless and rootless for better security.
```

### Container Won't Start

**Symptom:** Server fails to start, containers exit immediately

**Check Docker/Podman is running:**

```bash
podman ps
# or
docker ps
```

**If "Cannot connect to Podman socket":**

On macOS:

```bash
podman machine start
```

Wait 30 seconds, then try starting the server again.

**Check logs for specific errors:**

```bash
bun run server-cli logs
```

**Common specific issues:**

**Error: "port already in use"**
Another service is using port 8000 or 7687 (Neo4j) or 6379 (FalkorDB).

Find what's using the port:

```bash
lsof -i :8000
lsof -i :7687  # Neo4j Bolt
lsof -i :6379  # FalkorDB/Redis
```

Kill the process or change the knowledge system ports.

**Error: "image not found"**
The container image needs to be pulled:

```bash
podman pull falkordb/graphiti-knowledge-graph-mcp:latest
```

**Error: "network not found"**
Recreate the network:

```bash
podman network rm madeinoz-knowledge-net
```

Then start the server again (it will recreate the network).

### Search Returns No Results

**Symptom:** Searches return empty or "No knowledge found"

**Check if knowledge has been captured:**

```bash
# In your AI assistant
Show me recent knowledge additions
```

If nothing recent, you need to capture knowledge first.

**Try a broader search:**

Instead of:

```
What do I know about Podman volume mounting syntax?
```

Try:

```
What do I know about Podman?
```

**Check you're searching the right group:**

If you've set a custom group ID, make sure searches use the same group.

Verify your group setting:

```bash
grep MADEINOZ_KNOWLEDGE_GROUP_ID "${PAI_DIR:-$HOME/.claude}/.env"
```

**Verify entities were extracted:**

Look at a recent capture - did it show "Entities extracted: 0"? If so, see the "No entities extracted" section above.

### Vector Dimension Mismatch Error

**Symptom:** Search queries fail with error: `Invalid input for 'vector.similarity.cosine()': The supplied vectors do not have the same number of dimensions`

**Cause:** Data was indexed with one embedding model, but searches use a different model with incompatible vector dimensions.

**Common scenarios that cause this:**

1. Changed `EMBEDDER_MODEL` in config after data was already indexed
2. Tested multiple embedding models without clearing data between tests
3. Migrated from one embedding provider to another

**Embedding model dimensions:**

| Model | Provider | Dimensions |
|-------|----------|------------|
| mxbai-embed-large | Ollama | 1024 |
| nomic-embed-text | Ollama | 768 |
| text-embedding-3-small | OpenAI | 1536 |
| text-embedding-3-large | OpenAI | 3072 |
| text-embedding-ada-002 | OpenAI | 1536 |

**The fix: Clear mismatched data**

Neo4j requires all vectors in an index to have the same dimensions. You must clear data indexed with the old model.

**Option 1: Clear specific groups (preserves other data)**

If you know which groups have mismatched embeddings:

```bash
# Via Claude Code / MCP
clear_graph with group_ids: ["group1", "group2"]
```

Or identify test groups by checking episodes:

```bash
# Via Claude Code / MCP
get_episodes with max_episodes: 50
```

Look for groups with different `group_id` values, then clear those specific groups.

**Option 2: Clear entire graph (nuclear option)**

If unsure which data is affected:

```bash
# Via Claude Code / MCP
clear_graph
```

This deletes ALL data. You'll need to re-add any knowledge you want to keep.

**Verify the fix:**

After clearing, test that searches work:

```bash
# Via Claude Code / MCP
search_nodes with query: "test"
```

Should return `"No relevant nodes found"` (empty but no error), not a dimension mismatch error.

**Prevention:**

1. **Choose an embedding model and stick with it** - Changing models requires re-indexing all data
2. **Use separate group_ids for testing** - e.g., `test-llama`, `test-openai`, then clear test groups after
3. **Document your embedding config** - Note which model was used to index production data
4. **Keep `EMBEDDER_DIMENSIONS` in sync** - Must match your model:

   ```bash
   # Example for mxbai-embed-large
   EMBEDDER_MODEL=mxbai-embed-large
   EMBEDDER_DIMENSIONS=1024
   ```

**If you MUST change embedding models:**

1. Export important knowledge (manually note key facts)
2. Clear the entire graph
3. Update `EMBEDDER_MODEL` and `EMBEDDER_DIMENSIONS` in config
4. Restart the server
5. Re-add your knowledge

There's no way to "migrate" vectors - the embeddings are fundamentally different representations.

### "Rate limit exceeded" or API Errors

**Symptom:** Errors about too many requests or rate limits

**Immediate fix:**

Reduce concurrent requests in your PAI config (`$PAI_DIR/.env` or `~/.claude/.env`):

```bash
MADEINOZ_KNOWLEDGE_SEMAPHORE_LIMIT=3
```

Lower number = fewer parallel requests.

Restart the server after changing.

**Permanent solution:**

Check your OpenAI tier at <https://platform.openai.com/account/rate-limits>

Adjust SEMAPHORE_LIMIT based on your tier:

- Free tier: 1-2
- Tier 1: 3-5
- Tier 2: 8
- Tier 3+: 10-15

**If you're hitting rate limits constantly:**
Consider upgrading your OpenAI tier or capturing knowledge less frequently.

### "SSE endpoint not responding"

**Symptom:** MCP connection fails, mentions SSE

**This is the MCP transport layer having issues.**

**Quick fix:**

1. Stop the server: `bun run server-cli stop`
2. Wait 10 seconds
3. Start again: `bun run server-cli start`
4. Restart your AI assistant (Claude Code, etc.)

**If that doesn't work:**

Check if the SSE endpoint responds at all:

```bash
curl -N -H "Accept: text/event-stream" http://localhost:8000/sse
```

Should see event-stream data.

**If curl fails:**
The MCP server isn't running properly. Check logs:

```bash
bun run server-cli logs
```

Look for startup errors.

### Knowledge Not Syncing from Memory

**Symptom:** Memory captures aren't appearing in knowledge graph

**Check if the hook is installed:**

```bash
cat ~/.claude/settings.json | grep sync-memory-to-knowledge
```

Should see a hook definition.

**If nothing shows:**
The hook isn't installed. Install it:

```bash
cd ~/.claude/skills/Knowledge
bun run tools/install.ts
```

**Manually trigger sync:**

```bash
bun run ~/.claude/hooks/sync-memory-to-knowledge.ts --verbose
```

This shows what's being synced (or why not).

**Check sync state:**

```bash
cat ~/.claude/MEMORY/STATE/knowledge-sync/sync-state.json
```

Shows what's already been synced.

**Force re-sync everything:**

```bash
rm ~/.claude/MEMORY/STATE/knowledge-sync/sync-state.json
bun run ~/.claude/hooks/sync-memory-to-knowledge.ts --all --verbose
```

### High API Costs

**Symptom:** Your OpenAI bill is higher than expected

**Check usage:**
<https://platform.openai.com/usage>

**Reduce costs:**

**1. Use cheaper model:**

In your PAI config (`$PAI_DIR/.env` or `~/.claude/.env`):

```bash
MADEINOZ_KNOWLEDGE_MODEL_NAME=gpt-4o-mini
```

(gpt-4o-mini is 10x cheaper than gpt-4o)

**2. Capture less:**
Only capture truly valuable knowledge, not every conversation.

**3. Reduce concurrency:**

```bash
MADEINOZ_KNOWLEDGE_SEMAPHORE_LIMIT=3
```

**4. Monitor usage:**
Check your API usage weekly to catch cost spikes early.

**Typical costs:**

- Light use: $0.50-1.00/month
- Moderate use: $1.00-3.00/month
- Heavy use: $3.00-10.00/month

Using gpt-4o-mini, not gpt-4o.

### Database Web UI Not Accessible

**Symptom:** Can't access database UI (Neo4j: <http://localhost:7474>, FalkorDB: <http://localhost:3000>)

**Check if database container is running:**

```bash
# For Neo4j (default)
podman ps | grep neo4j

# For FalkorDB
podman ps | grep falkordb
```

**If not running:**

```bash
bun run server-cli start
```

**Check ports aren't blocked:**

```bash
lsof -i :7474  # Neo4j Browser
lsof -i :3000  # FalkorDB UI
```

**Try accessing the graph directly:**

```bash
# For Neo4j (default)
podman exec madeinoz-knowledge-neo4j cypher-shell -u neo4j -p password "RETURN 1"

# For FalkorDB
podman exec madeinoz-knowledge-falkordb redis-cli PING
```

Should respond with `1` (Neo4j) or "PONG" (FalkorDB).

### Memory or Performance Issues

**Symptom:** System is slow or running out of memory

**Check system resources:**

```bash
podman stats
```

Shows CPU and memory usage of containers.

**If memory usage is high:**

**Option 1: Restart containers**

```bash
bun run server-cli restart
```

**Option 2: Clear old data**
If you have a lot of episodes you no longer need:

```
# In your AI assistant
Clear my knowledge graph
```

(Warning: This deletes everything!)

**Option 3: Add memory limits**
Edit container configuration to limit memory usage.

### EdgeDuplicate or ExtractedEntities Pydantic Validation Errors

**Symptom:** Container logs show errors like:

```
3 validation errors for EdgeDuplicate
duplicate_facts: Field required [type=missing, input_value={'properties': {'duplicat...}]
contradicted_facts: Field required [type=missing]
fact_type: Field required [type=missing]
```

Or similar errors for `ExtractedEntities`, `EntitySummary`, or other Pydantic models.

**Root Cause:**

The LLM returns a JSON schema definition instead of actual field values. This happens because:

1. Some LLM providers don't fully support structured output/parse API
2. The `OpenAIGenericClient` uses basic `json_object` mode which is less strict
3. Complex multi-entity content triggers edge deduplication which is more prone to this error

**Which models are affected:**

| Model | Status | Notes |
|-------|--------|-------|
| gpt-4o-mini | ✅ Works | Occasional errors, retry recovers |
| gpt-4o | ✅ Works | Occasional errors, retry recovers |
| gemini-2.0-flash | ✅ Works | Occasional errors, retry recovers |
| claude-3.5-haiku | ⚠️ Auth issues | Requires different API routing |
| llama/mistral variants | ❌ Fails | Consistent Pydantic errors |

**Solution: Use OpenAIClient for Cloud Providers**

The Madeinoz Knowledge System v1.2.4+ includes a patch that uses `OpenAIClient` (with parse API) for cloud providers instead of `OpenAIGenericClient` (basic json_object mode).

**Verify the patch is active:**

Check container logs after startup:

```bash
podman logs madeinoz-knowledge-graph-mcp 2>&1 | grep "Patch v3"
```

Should show:

```
Madeinoz Patch v3: Using OpenAIClient for cloud openrouter
```

**If errors persist:**

1. **Check your model is supported** - Llama and Mistral models consistently fail
2. **Errors are expected occasionally** - The built-in retry logic (2 attempts) usually recovers
3. **Simpler content works better** - Break very complex episodes into smaller chunks

**Tracking:**

This issue is tracked at: <https://github.com/getzep/graphiti/issues/912>

**Technical Details:**

The fix differentiates between:

- **Cloud providers** (OpenRouter, Together, etc.) → Use `OpenAIClient` with parse API
- **Local endpoints** (Ollama) → Use `OpenAIGenericClient` with json_object mode

The parse API provides stricter schema enforcement, which prevents the LLM from returning JSON schema definitions instead of actual values.

**Note:** This fix is applied at Docker image build time as part of the container configuration.

### "Initialization not complete" Warning

**Symptom:** MCP logs show "Received request before initialization was complete"

**Cause:** This is a known issue with the Graphiti MCP server - Claude Code sometimes sends requests before the SSE session fully initializes.

**Workaround:**
Restart your AI assistant (Claude Code). This resets the MCP connection.

**Tracking:**
This issue is tracked at: <https://github.com/getzep/graphiti/issues/840>

**Not a critical issue:**
This warning usually doesn't break functionality, but restarting helps if you see repeated failures.

### Query Syntax Errors with Special Characters (FalkorDB Backend)

**Note:** This issue is specific to the FalkorDB backend. Neo4j (the default) handles special characters more gracefully.

**Symptom:** Search queries fail with syntax errors, especially when searching for content containing hyphens, at-signs, or other special characters. Error messages may include "QuerySyntaxError" or mention unexpected tokens.

**Root Cause:**

FalkorDB uses RediSearch for fulltext indexing, which interprets certain characters as Lucene query operators:

| Character | Lucene Interpretation |
|-----------|----------------------|
| `-` | Negation (NOT operator) |
| `+` | Required term (AND) |
| `@` | Field prefix |
| `#` | Tag field |
| `*` `?` | Wildcards |
| `"` | Phrase query |
| `( )` | Grouping |
| `{ }` `[ ]` | Range queries |
| `~` | Fuzzy/proximity |
| `:` | Field specifier |
| `\|` | OR operator |
| `&` | AND operator |
| `!` | NOT operator |
| `%` | Fuzzy threshold |
| `< > =` | Comparison operators |
| `$` | Variable reference |
| `/` | Regex delimiter |

**Example of the bug:**

When you search for `madeinoz-threat-intel`:

- RediSearch interprets this as: `pai AND NOT threat AND NOT intel`
- This returns wrong results or a syntax error

**The Graphiti Bug:**

Graphiti's FalkorDB driver has a `sanitize()` method that replaces special characters with whitespace. However, this sanitization is **not applied to group_ids** in search queries. When you use a group_id like `my-knowledge-base`, the hyphen is passed directly to RediSearch and interpreted as negation.

**Related Issues:**

- [RediSearch #2628](https://github.com/RediSearch/RediSearch/issues/2628) - Can't search text with hyphens
- [RediSearch #4092](https://github.com/RediSearch/RediSearch/issues/4092) - Escaping filter values
- [Graphiti #815](https://github.com/getzep/graphiti/issues/815) - FalkorDB query syntax errors
- [Graphiti #1118](https://github.com/getzep/graphiti/pull/1118) - Fix forward slash handling

**Our Solution:**

The Madeinoz Knowledge System Docker container handles sanitization automatically at runtime:

1. **For group_ids:** Special characters are properly escaped in queries
   - `madeinoz-threat-intel` → `pai_threat_intel`
   - This avoids the Graphiti bug where group_ids aren't escaped

2. **For search queries:** Special characters are handled by the container's query processor

**Note:** The sanitization is built into the Docker container and applied automatically.

**If you encounter syntax errors:**

1. Check if your group_id contains special characters:

   ```bash
   grep MADEINOZ_KNOWLEDGE_GROUP_ID "${PAI_DIR:-$HOME/.claude}/.env"
   ```

2. Use underscores instead of hyphens in group_ids:
   - Bad: `my-knowledge-base`
   - Good: `my_knowledge_base`

3. The sanitization is automatic for MCP tool calls, but if you're calling Graphiti directly, ensure you sanitize inputs.

**Recommendation:** For the best experience with special characters, consider using the Neo4j backend instead of FalkorDB, as Neo4j handles special characters natively.

## Diagnostic Commands Summary

Quick reference for troubleshooting:

```bash
# Check status
bun run server-cli status

# View logs
bun run server-cli logs

# Restart everything
bun run server-cli restart

# Check configuration
cat "${PAI_DIR:-$HOME/.claude}/.env" | grep MADEINOZ_KNOWLEDGE

# Test MCP endpoint
curl http://localhost:8000/sse -H "Accept: text/event-stream"

# Check containers
podman ps | grep madeinoz-knowledge

# Check ports
lsof -i :8000    # MCP Server
lsof -i :7687    # Neo4j Bolt (default)
lsof -i :7474    # Neo4j Browser (default)
lsof -i :6379    # FalkorDB/Redis
lsof -i :3000    # FalkorDB UI

# Manual sync test
bun run ~/.claude/hooks/sync-memory-to-knowledge.ts --dry-run --verbose

# View container logs directly
podman logs madeinoz-knowledge-graph-mcp
podman logs madeinoz-knowledge-neo4j       # Neo4j (default)
podman logs madeinoz-knowledge-falkordb    # FalkorDB backend
```

## Getting More Help

If these solutions don't work:

1. **Check the main README:**
   `/Users/seaton/.config/pai/Packs/madeinoz-knowledge-system/README.md`

2. **Check installation guide:**
   `docs/installation.md`

3. **Review verification:**
   `/Users/seaton/.config/pai/Packs/madeinoz-knowledge-system/VERIFY.md`

4. **Check Graphiti documentation:**
   <https://help.getzep.com/graphiti>

5. **Check FalkorDB documentation:**
   <https://docs.falkordb.com/>

## Still Stuck?

Create a diagnostic report:

```bash
cd ~/.config/pai/Packs/madeinoz-knowledge-system

echo "=== System Status ===" > diagnostic.txt
bun run server-cli status >> diagnostic.txt

echo "\n=== Configuration ===" >> diagnostic.txt
cat "${PAI_DIR:-$HOME/.claude}/.env" | grep MADEINOZ_KNOWLEDGE | grep -v API_KEY >> diagnostic.txt

echo "\n=== Recent Logs ===" >> diagnostic.txt
bun run server-cli logs | tail -100 >> diagnostic.txt

echo "\n=== Container Info ===" >> diagnostic.txt
podman ps --all | grep madeinoz-knowledge >> diagnostic.txt

echo "\n=== Port Status ===" >> diagnostic.txt
lsof -i :8000 >> diagnostic.txt
lsof -i :6379 >> diagnostic.txt

echo "Diagnostic report saved to diagnostic.txt"
```

Share `diagnostic.txt` when asking for help (remove any sensitive info first!).
