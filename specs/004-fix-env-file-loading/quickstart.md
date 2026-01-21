# Quickstart: Fix Environment File Loading

**Feature**: 004-fix-env-file-loading
**Date**: 2026-01-20

This guide provides quick verification and testing steps for the environment file loading fix.

## Pre-Fix Verification (Reproducing the Bug)

### Step 1: Check Current Configuration

```bash
# View current env_file path in compose files
grep -A 2 "env_file:" src/server/docker-compose*.yml src/server/podman-compose*.yml
```

**Expected Output (BROKEN)**:
```yaml
env_file:
  - ${PAI_DIR:-~/.claude}/.env  # Tilde won't expand!
```

### Step 2: Try to Start Containers (Should Fail or Show Warnings)

```bash
# Ensure .env file exists with API keys
cat ~/.claude/.env | grep MADEINOZ_KNOWLEDGE

# Try starting Neo4j backend
docker compose -f src/server/docker-compose-neo4j.yml up -d

# Check logs for "variable not set" warnings
docker logs madeinoz-knowledge-graph-mcp 2>&1 | grep -i "variable\|warning"
```

**Expected Bug Symptoms**:
- "variable not set. Defaulting to a blank string" warnings
- Services start but LLM/embedder clients fail to initialize
- API keys not accessible in container

## Post-Fix Verification (Confirming the Fix)

### Step 1: Verify Fixed Configuration

```bash
# View updated env_file path
grep -A 2 "env_file:" src/server/docker-compose*.yml src/server/podman-compose*.yml
```

**Expected Output (FIXED)**:
```yaml
env_file:
  - ${PAI_DIR:-$HOME/.claude}/.env  # $HOME expands correctly!
```

### Step 2: Verify All Compose Files Exist

```bash
# Should show 4 files with clear backend naming:
# - docker-compose-falkordb.yml (FalkorDB + Docker) - RENAMED from docker-compose.yml
# - docker-compose-neo4j.yml (Neo4j + Docker)
# - podman-compose-falkordb.yml (FalkorDB + Podman) - RENAMED from podman-compose.yml
# - podman-compose-neo4j.yml (Neo4j + Podman) ← NEW
ls -la src/server/*compose*.yml
```

### Step 3: Test Each Compose File

#### Test 1: Docker + Neo4j

```bash
# Start containers
docker compose -f src/server/docker-compose-neo4j.yml up -d

# Verify no "variable not set" warnings
docker logs madeinoz-knowledge-graph-mcp 2>&1 | grep -i "variable\|warning"
# Should be EMPTY (no warnings)

# Verify environment variables in container
docker exec madeinoz-knowledge-graph-mcp env | grep OPENAI_API_KEY
# Should show: OPENAI_API_KEY=sk-... (your actual key)

# Verify MCP server is healthy
curl -sf http://localhost:8000/health
# Should return: {"status":"healthy"}

# Cleanup
docker compose -f src/server/docker-compose-neo4j.yml down
```

#### Test 2: Docker + FalkorDB

```bash
docker compose -f src/server/docker-compose-falkordb.yml up -d
docker logs madeinoz-knowledge-graph-mcp 2>&1 | grep -i "variable\|warning"
docker exec madeinoz-knowledge-graph-mcp env | grep OPENAI_API_KEY
curl -sf http://localhost:8000/health
docker compose -f src/server/docker-compose-falkordb.yml down
```

#### Test 3: Podman + Neo4j (if Podman installed)

```bash
podman-compose -f src/server/podman-compose-neo4j.yml up -d
podman logs madeinoz-knowledge-graph-mcp 2>&1 | grep -i "variable\|warning"
podman exec madeinoz-knowledge-graph-mcp env | grep OPENAI_API_KEY
curl -sf http://localhost:8000/health
podman-compose -f src/server/podman-compose-neo4j.yml down
```

#### Test 4: Podman + FalkorDB (if Podman installed)

```bash
podman-compose -f src/server/podman-compose-falkordb.yml up -d
podman logs madeinoz-knowledge-graph-mcp 2>&1 | grep -i "variable\|warning"
podman exec madeinoz-knowledge-graph-mcp env | grep OPENAI_API_KEY
curl -sf http://localhost:8000/health
podman-compose -f src/server/podman-compose-falkordb.yml down
```

### Step 4: Test PAI_DIR Variable

```bash
# Test with PAI_DIR set
export PAI_DIR=/tmp/test-pai
mkdir -p /tmp/test-pai
cp ~/.claude/.env /tmp/test-pai/.env

docker compose -f src/server/docker-compose-neo4j.yml up -d
docker logs madeinoz-knowledge-graph-mcp 2>&1 | grep -i "variable\|warning"
# Should be EMPTY

docker compose -f src/server/docker-compose-neo4j.yml down
unset PAI_DIR
```

### Step 5: Test Graceful Degradation (Missing .env)

```bash
# Rename .env temporarily
mv ~/.claude/.env ~/.claude/.env.bak

# Try starting (should use defaults, not fail)
docker compose -f src/server/docker-compose-neo4j.yml up -d

# Check logs (should show missing API key but not crash)
docker logs madeinoz-knowledge-graph-mcp 2>&1 | tail -20

# Restore .env
mv ~/.claude/.env.bak ~/.claude/.env
docker compose -f src/server/docker-compose-neo4j.yml down
```

## Verification Checklist

- [ ] All 4 compose files exist (docker-compose-falkordb.yml, docker-compose-neo4j.yml, podman-compose-falkordb.yml, podman-compose-neo4j.yml)
- [ ] All compose files use `${PAI_DIR:-$HOME/.claude}/.env` (NOT `~/.claude`)
- [ ] No "variable not set" warnings in container logs
- [ ] Environment variables (OPENAI_API_KEY, etc.) are set correctly in containers
- [ ] MCP server health check returns `{"status":"healthy"}`
- [ ] Services start with defaults when .env is missing (graceful degradation)
- [ ] PAI_DIR environment variable works correctly when set
- [ ] All 4 compose file variants work (Docker/Podman × Neo4j/FalkorDB)

## Troubleshooting

### Still Seeing "Variable Not Set" Warnings?

1. **Verify .env file exists and has content**:
   ```bash
   cat ~/.claude/.env | head -20
   ```

2. **Check for typos in variable names**:
   ```bash
   grep MADEINOZ_KNOWLEDGE ~/.claude/.env
   ```

3. **Verify compose file syntax**:
   ```bash
   docker compose -f src/server/docker-compose-neo4j.yml config
   ```

### Tilde Still Not Expanding?

If you see `~/.claude` in actual path (not expanded):

1. Check compose file uses `$HOME` not `~`:
   ```bash
   grep "env_file:" src/server/*compose*.yml -A 1
   ```

2. Ensure no hardcoded `~` paths:
   ```bash
   grep -r "~/.claude" src/server/*compose*.yml
   ```

### Podman Compose Not Working?

1. Verify Podman Compose is installed:
   ```bash
   podman-compose --version
   ```

2. Check $HOME is set:
   ```bash
   echo $HOME
   podman exec madeinoz-knowledge-graph-mcp env | grep HOME
   ```

## Success Criteria

The fix is successful when:

1. **SC-001**: Users can start Docker/Podman Compose services with API keys loaded automatically 100% of the time
2. **SC-002**: No "variable not set" warnings appear in logs when .env is properly configured
3. **SC-003**: Containers start within 30 seconds
4. **SC-005**: Variable expansion `${PAI_DIR:-$HOME/.claude}` resolves correctly in all scenarios
5. **SC-006**: Missing .env file doesn't prevent container startup (graceful degradation)

## Next Steps After Verification

Once all verification tests pass:

1. Update documentation with correct syntax
2. Add troubleshooting guide to docs/
3. Update README with compose file selection guidance
4. Run full integration test suite
5. Create pull request with fix
