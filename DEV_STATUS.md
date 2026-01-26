# Development Status Note

**Date:** 2026-01-26
**Session:** ESLint migration + CI workflow update

## Completed

### 1. ESLint Migration (from Biome)
- Removed `biome.json` configuration
- Created `eslint.config.js` matching lldap-cli project
- Updated `package.json`:
  - Replaced `@biomejs/biome` with ESLint dependencies
  - Changed `lint` script to use ESLint
- Fixed `tsconfig.json`:
  - Removed comments (invalid for ESLint parser)
  - Fixed option names (`allowUnusedLocals` → `noUnusedLocals`)
- Committed as `d4343b8`: "chore: switch from Biome to ESLint"

### 2. CI Workflow Rewrite
- Consolidated to single `.github/workflows/ci.yml` matching lldap-cli structure
- New pipeline: **security → lint → test → build → release**
- Build job now includes:
  - Docker image build
  - MkDocs documentation build
- Release job (on tags) includes:
  - Docker push to GHCR
  - GitHub Pages deployment
  - GitHub Release creation
- **Dockerfile path fixed:** `./Dockerfile` → `./docker/Dockerfile`

## Pending

### 1. Verify CI Passes
After fixing Dockerfile path:
- Push to trigger CI
- Verify all jobs pass: security → lint → test → build

## Docker File Locations

```
./docker/Dockerfile                          # Main Dockerfile
./docker/docker-compose.falkordb.yml        # FalkorDB (Docker)
./docker/docker-compose-neo4j.yml           # Neo4j (Docker)
./docker/docker-compose.custom.yml          # Custom config
./src/skills/server/docker-compose-*.yml    # Dev/test variants
```

## Reference
- Lint configuration matches: `/Users/seaton/Documents/src/lldap-cli/eslint.config.js`
- CI structure matches: `/Users/seaton/Documents/src/lldap-cli/.github/workflows/ci.yml`
