# Research: Documentation and Docker Compose Updates

**Feature**: 005-docs-compose-updates
**Date**: 2026-01-26
**Phase**: 0 - Outline & Research

---

## Executive Summary

This feature requires documentation cleanup (remove Lucene references), benchmark documentation improvements, and Docker/Podman Compose file image reference updates. Research identified all affected files and current state.

## Decision Log

### Decision 1: Lucene Documentation Removal

**Status**: ✅ COMPLETE - All references identified

**Decision**: Remove ALL Lucene-specific documentation content from user-facing documentation.

**Rationale**:

- Lucene is an implementation detail of FalkorDB's RediSearch
- Users don't need to understand backend-specific query sanitization
- Confuses users about Neo4j vs FalkorDB differences
- Simplification improves documentation clarity per user requirement

**Files with Lucene references** (identified via `codanna mcp search_documents`):

1. `INSTALL.md` - Multiple sections:
   - "Lucene Query Errors with Hyphenated Groups" troubleshooting section
   - "Test 4: Verify Lucene sanitization" verification step
   - Inline code references to `lucene.ts`
   - Required lib files check listing `lucene.ts`
2. `CLAUDE.md` - Codanna section mentions Lucene (already checked - no Lucene content)
3. `README.md` - No Lucene references (already checked)
4. Compose file headers mention "no RediSearch/Lucene escaping needed" for Neo4j

**Alternatives Considered**:

- Keep Lucene docs with "FalkorDB only" labels → Rejected: Violates requirement to remove ALL Lucene content
- Move to advanced/appendix section → Rejected: Still violates complete removal requirement

**Action**: Remove all Lucene content from INSTALL.md and simplify compose file headers.

---

### Decision 2: Benchmark Documentation Reorganization

**Status**: ✅ COMPLETE - Existing benchmark data identified

**Decision**: Reorganize existing benchmark sections with real performance data at top and testing results at bottom. Add explicit LLM model recommendations.

**Rationale**:

- Users want to see actual performance first, testing methodology later
- Clear LLM recommendations help users choose providers
- Price/performance guidance is critical for cost-conscious users

**Current Benchmark Locations** (from INSTALL.md review):

- LLM Provider Comparison table (OpenRouter GPT-4o Mini recommended as "MOST STABLE")
- Embedding Options table (Ollama mxbai-embed-large recommended as "Best value")
- Multiple provider/feature-specific tables scattered through document
- No dedicated "Benchmarks" section - data is embedded in provider selection guide

**Reorganization Plan**:

1. Create new "Performance Benchmarks" section near top of INSTALL.md
2. Move LLM model recommendations to prominent position
3. Add explicit "Models to Avoid" section
4. Keep detailed testing methodology at bottom

**Alternatives Considered**:

- Create separate BENCHMARKS.md file → Rejected: User needs benchmarks visible in main installation guide
- Run new performance tests → Rejected: Out of scope per requirements

---

### Decision 3: Container Image Reference Updates

**Status**: ✅ COMPLETE - All compose files identified

**Decision**: Update all `graphiti-mcp` service image references to `ghcr.io/madeinoz67/madeinoz-knowledge-system:latest`

**Rationale**:

- GitHub Container Registry is the official image location
- Consistent image references across all compose files
- Supports both Docker and Podman deployments

**Current Image References** (needs update):

| File | Current Image | Target Image |
|------|--------------|--------------|
| `src/skills/server/docker-compose-neo4j.yml` | `madeinoz-knowledge-system:latest` | `ghcr.io/madeinoz67/madeinoz-knowledge-system:latest` |
| `src/skills/server/docker-compose-falkordb.yml` | `madeinoz-knowledge-system:latest` | `ghcr.io/madeinoz67/madeinoz-knowledge-system:latest` |
| `src/skills/server/podman-compose-neo4j.yml` | `zepai/knowledge-graph-mcp:standalone` | `ghcr.io/madeinoz67/madeinoz-knowledge-system:latest` |
| `src/skills/server/podman-compose-falkordb.yml` | `falkordb/graphiti-knowledge-graph-mcp:latest` | `ghcr.io/madeinoz67/madeinoz-knowledge-system:latest` |

**Database Images** (no changes needed):

- `neo4j:latest` - Official Neo4j image (keep as-is)
- `falkordb/falkordb:latest` - Official FalkorDB image (keep as-is)

**Additional Compose Files** (reviewed, not in scope for main changes but noted):

- `docker/docker-compose-*.yml` - Docker directory variants (check if needed)
- `src/skills/server/docker-compose-*.yml` - Dev/test variants (check if needed)
- `src/skills/server/podman-compose.yml` - Generic podman file (check if needed)

**Alternatives Considered**:

- Use Docker Hub `madeinoz-knowledge-system:latest` → Rejected: GHCR is primary registry per README
- Keep different images per backend → Rejected: Single image supports both backends via config

---

## Technical Context Findings

### Documentation Files Requiring Updates

1. **INSTALL.md** (Primary focus):
   - Remove Lucene troubleshooting section
   - Remove Lucene verification test
   - Remove lucene.ts from required files check
   - Reorganize benchmark sections
   - Add LLM model recommendations

2. **CLAUDE.md** (Review):
   - No Lucene content found
   - Already clean

3. **README.md** (Review):
   - No Lucene content found
   - Already references GHCR correctly
   - May need benchmark section cross-reference

4. **Compose File Headers** (Minor cleanup):
   - Remove "no RediSearch/Lucene escaping" comments
   - Simplify patch descriptions

### Compose Files Requiring Updates

**High Priority** (explicitly mentioned in spec):

1. `src/skills/server/docker-compose-neo4j.yml`
2. `src/skills/server/docker-compose-falkordb.yml`
3. `src/skills/server/podman-compose-neo4j.yml`
4. `src/skills/server/podman-compose-falkordb.yml`

**Review Required** (mentioned in spec as "all compose files"):
5. `src/skills/server/docker-compose.yml` (generic)
6. `src/skills/server/docker-compose-test.yml` (testing)
7. `src/skills/server/docker-compose-*-dev.yml` (dev variants)
8. `src/skills/server/podman-compose.yml` (generic)
9. `docker/docker-compose-*.yml` (docker directory variants)

### Shell Scripts Review

**Found via glob**:

- `.specify/scripts/bash/*.sh` - SpecKit scripts (no container image references expected)
- `src/skills/server/entrypoint.sh` - Container entrypoint (may have image references in comments)

**Note**: Scripts typically don't hardcode image references (use environment variables), but will review for any documentation or comments.

---

## Open Questions (Resolved)

### Q1: How should technically accurate Lucene references be handled?

**Resolution**: Remove ALL Lucene references including explanatory context per spec clarification: "prioritize simplicity over technical accuracy."

### Q2: What about compose file comments mentioning Lucene patches?

**Resolution**: Remove or simplify comments. The `falkordb_lucene.py` patch file still exists and works, but users don't need to know about it.

### Q3: Should we document that query sanitization still happens internally?

**Resolution**: No. This is an implementation detail. Users only need to know "special characters work correctly."

---

## Dependencies

### External

- GitHub Container Registry (`ghcr.io/madeinoz67/madeinoz-knowledge-system:latest`) must exist and be accessible
- No API calls or external services needed for documentation updates

### Internal

- No code changes to `lucene.ts` or query handling
- Compose file structure remains unchanged
- Environment variable system unchanged

---

## Testing Strategy

### Documentation Verification

- Manual review of all `.md` files for remaining Lucene references
- Verify benchmark section organization
- Check LLM recommendation clarity

### Compose File Verification

- Syntax validation: `docker compose -f <file> config`
- Verify image references point to GHCR
- Check for any remaining old image references

### Deployment Verification (Post-Implementation)

- Test `docker compose up` with updated files
- Verify correct image pull from GHCR
- Confirm containers start successfully

---

## Next Steps (Phase 1)

1. ✅ Complete research (this document)
2. → Generate updated documentation files
3. → Update compose files with new image references
4. → Run agent context update script
5. → Re-evaluate Constitution Check

---

**Research Status**: ✅ COMPLETE
**All clarifications resolved. Ready for Phase 1: Design & Contracts.**
