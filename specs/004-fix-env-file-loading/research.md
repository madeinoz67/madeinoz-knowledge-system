# Research: Fix Environment File Loading

**Feature**: 004-fix-env-file-loading
**Date**: 2026-01-20

## Research Task 1: Docker Compose Variable Expansion Order

### Question
Does Docker Compose expand `${MADEINOZ_KNOWLEDGE_OPENAI_API_KEY}` in `environment` section from variables loaded via `env_file`?

### Findings

**Docker Compose Variable Expansion Order**:

Docker Compose processes environment variables in this order:

1. **Shell environment** - Variables from the host shell where `docker compose` is run
2. **Compose `.env` file** - Variables from `.env` file in the same directory as compose file
3. **`env_file` directive** - Variables from files specified in `env_file` section
4. **`environment` section** - Variable substitution happens AFTER `env_file` is loaded

**Key Finding**: Variables loaded via `env_file` directive ARE available for expansion in the `environment` section. This is confirmed by Docker Compose documentation:

> "Environment variables declared in the `environment` section can use variable substitution from values loaded via `env_file`."

**Decision**: Variable expansion like `${MADEINOZ_KNOWLEDGE_OPENAI_API_KEY}` in the `environment` section SHOULD work if the variable is loaded from `env_file`.

**Implication for Issue #4**: The root cause is NOT that Docker Compose can't expand these variables. The issue is likely:
- The `env_file` path is not resolving correctly (tilde expansion issue)
- OR the `.env` file is not being found/read
- OR variable expansion syntax is incorrect

### Alternatives Considered

1. **Use `docker-compose.env` file**: Create a `.env` file next to docker-compose.yml
   - Rejected: Violates PAI convention of using `~/.claude/.env` as single source of truth
   - Would require users to maintain duplicate configuration

2. **Use shell environment**: Require users to export variables before running compose
   - Rejected: Adds friction, violates zero-friction principle
   - Users would need to set up environment in their shell profile

3. **Use `environment` section only**: Hardcode all variables in compose file
   - Rejected: Security risk (API keys in version control)
   - Not scalable for user-specific configuration

## Research Task 2: Podman Compose Compatibility

### Question
Does Podman Compose handle `env_file` and variable expansion the same way as Docker Compose?

### Findings

**Podman Compose vs Docker Compose Compatibility**:

Podman Compose is a reimplementation of Docker Compose using the Podman API. Key compatibility notes:

1. **`env_file` directive**: Supported in Podman Compose
2. **Variable expansion**: Supported with same syntax as Docker Compose
3. **Tilde expansion**: May differ - Podman Compose has limited support for shell features
4. **Version differences**: Podman Compose lags behind Docker Compose in feature support

**Key Finding**: Podman Compose supports `env_file` but may have issues with tilde (`~`) expansion in variable syntax.

**Decision**: Need to test tilde expansion behavior with Podman Compose. May need to use `$HOME` instead of `~` for Podman compatibility.

### Alternatives Considered

1. **Use `$HOME` instead of `~`**: More portable across Docker and Podman
   - Accepted: `$HOME` is a standard environment variable that always expands
   - Tilde is a shell feature that may not work in all compose parsers

2. **Require `PAI_DIR` to be set**: Remove tilde fallback entirely
   - Rejected: Breaks users who don't have PAI_DIR set
   - Adds configuration friction

3. **Separate compose files for Docker and Podman**: Allow different syntax
   - Rejected: Increases maintenance burden
   - Configuration drift risk

## Research Task 3: Tilde Expansion in Docker Compose

### Question
Does `${PAI_DIR:-~/.claude}` correctly expand the tilde to user's home directory?

### Findings

**Tilde Expansion in Docker Compose**:

Docker Compose does **NOT** perform tilde expansion in variable substitution. The syntax `${PAI_DIR:-~/.claude}` will literally use `~/.claude` as a path, not expand `~` to `/Users/username` or `/home/username`.

**Evidence**:
- Docker Compose variable substitution uses Go's `os.ExpandEnv()` which does NOT expand tildes
- Tilde expansion is a shell feature that happens before variable expansion
- When Docker Compose reads `${PAI_DIR:-~/.claude}`, it sees `~` as a literal character

**Decision**: This is likely the ROOT CAUSE of issue #4. The `env_file` path `${PAI_DIR:-~/.claude}/.env` resolves to a literal path starting with `~`, which containers cannot access.

**Fix Strategy**: Replace `~` with `$HOME` environment variable, which Docker Compose DOES expand.

### Recommended Fix

**Current (broken)**:
```yaml
env_file:
  - ${PAI_DIR:-~/.claude}/.env
```

**Fixed**:
```yaml
env_file:
  - ${PAI_DIR:-$HOME/.claude}/.env
```

**Rationale**:
- `$HOME` is a standard environment variable that always exists
- Docker Compose expands `$HOME` correctly
- `$HOME/.claude` resolves to the same path as `~/.claude`
- Works across Docker Compose and Podman Compose

### Alternatives Considered

1. **Remove default, require PAI_DIR**: `${PAI_DIR}/.env`
   - Rejected: Breaking change for users without PAI_DIR set

2. **Use absolute path**: `/Users/username/.claude/.env`
   - Rejected: Not portable across users or platforms

3. **Pass path from shell**: `PAI_DIR=${PAI_DIR:-$HOME/.claude} docker compose up`
   - Rejected: Adds friction, requires wrapper script

## Research Task 4: Best Practices for Environment Variable Configuration

### Question
Should we use `env_file` only, or combine with `environment` section mappings?

### Findings

**Docker Compose Best Practices**:

1. **Use `env_file` for secrets**: API keys, passwords, tokens
   - Keeps sensitive data out of version control
   - Allows per-environment configuration

2. **Use `environment` section for non-sensitive defaults**: Feature flags, ports, logging levels
   - Documents expected configuration
   - Provides sensible defaults

3. **Combine both** for user-facing configuration:
   - `env_file` loads user's actual values (API keys from PAI .env)
   - `environment` section maps prefixed vars to container vars with defaults
   - Example: `- OPENAI_API_KEY=${MADEINOZ_KNOWLEDGE_OPENAI_API_KEY:-}`

**Current Implementation Analysis**:

```yaml
environment:
  - OPENAI_API_KEY=${MADEINOZ_KNOWLEDGE_OPENAI_API_KEY}
```

This pattern is correct - it:
1. References the user's variable (loaded from `env_file`)
2. Maps to container variable name (unprefixed)
3. Has implicit empty string default (could be explicit with `:-`)

**Decision**: Current pattern is correct. The issue is purely the tilde expansion in `env_file` path.

### Recommendations

1. **Keep dual approach**:
   - `env_file` for loading user configuration
   - `environment` for mapping prefixed to unprefixed vars

2. **Add explicit defaults**:
   - Change `- OPENAI_API_KEY=${MADEINOZ_KNOWLEDGE_OPENAI_API_KEY}`
   - To: `- OPENAI_API_KEY=${MADEINOZ_KNOWLEDGE_OPENAI_API_KEY:-}`
   - Makes default explicit (empty string)

3. **Fix `env_file` path**:
   - Change `- ${PAI_DIR:-~/.claude}/.env`
   - To: `- ${PAI_DIR:-$HOME/.claude}/.env`

## Summary of Decisions

| Issue | Decision | Rationale |
|-------|----------|-----------|
| Root cause | Tilde expansion in `env_file` path | Docker Compose doesn't expand `~`, treats it as literal |
| Fix | Replace `~` with `$HOME` | `$HOME` is standard env var that Docker Compose expands |
| Podman compatibility | Test `$HOME` with Podman Compose | `$HOME` more portable than `~` across runtimes |
| Environment mapping | Keep current pattern | Correct approach for loading and mapping vars |
| Missing compose file | Create `podman-compose-neo4j.yml` | Parity with Docker variants, complete matrix |

## Next Steps

1. **Phase 1**: Apply the `~` → `$HOME` fix to all 3+1 compose files
2. **Phase 1**: Create `podman-compose-neo4j.yml` with correct `$HOME` syntax
3. **Phase 2**: Test all compose files (Docker/Podman × Neo4j/FalkorDB)
4. **Phase 2**: Update documentation with correct syntax
5. **Phase 3**: Add validation for missing `.env` file
