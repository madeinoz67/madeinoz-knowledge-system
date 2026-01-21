# Release Process

## Overview

This project uses GitHub Actions to automate Docker image builds and releases. The custom `madeinoz-knowledge-system:fixed` image is published to GitHub Container Registry (GHCR) and optionally Docker Hub.

## Release Workflows

### 1. Docker Build Workflow

**File:** `.github/workflows/docker-build.yml`

**Triggers:**
- Push to `main` branch (builds and pushes `latest` + `fixed` tags)
- Push tags matching `v*.*.*` (builds and pushes version tags)
- Pull requests (builds only, no push)
- Manual dispatch via GitHub UI

**What it does:**
1. Builds Docker image for `linux/amd64` and `linux/arm64` platforms
2. Tests the image (verifies entrypoint execution)
3. Pushes to GitHub Container Registry (`ghcr.io/madeinoz67/madeinoz-knowledge-system`)
4. Optionally pushes to Docker Hub (if `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets are configured)
5. Tags images with multiple formats:
   - `latest` - most recent main branch build
   - `fixed` - alias for latest (used in code references)
   - `v1.0.1` - semantic version from git tag
   - `1.0` - major.minor from version
   - `1` - major version only
   - `sha-abc123` - git commit SHA

**Image locations:**
```bash
# GitHub Container Registry (always available)
ghcr.io/madeinoz67/madeinoz-knowledge-system:latest
ghcr.io/madeinoz67/madeinoz-knowledge-system:fixed
ghcr.io/madeinoz67/madeinoz-knowledge-system:v1.0.1

# Docker Hub (if configured)
madeinoz-knowledge-system:latest
madeinoz-knowledge-system:fixed
madeinoz-knowledge-system:v1.0.1
```

### 2. Release Workflow

**File:** `.github/workflows/release.yml`

**Trigger:** Manual dispatch only (via GitHub UI)

**Required Input:**
- `version` - Semantic version (e.g., `1.0.2`)
- `prerelease` - Mark as pre-release (optional, default: false)

**What it does:**
1. Validates version format (`X.Y.Z`)
2. Checks if tag already exists
3. Updates `LABEL version` in Dockerfile
4. Generates changelog from git commits
5. Creates git tag (`v1.0.2`)
6. Pushes tag to GitHub
7. Creates GitHub Release with auto-generated notes
8. Triggers Docker build workflow (via tag push)
9. Updates documentation with release info

## How to Create a Release

### Prerequisites

1. **Permissions:** You need write access to the repository
2. **Clean state:** Ensure all changes are committed and pushed to `main`
3. **Changelog:** Recent commits should have clear messages

### Step-by-Step Process

#### 1. Navigate to Actions

Go to: `https://github.com/madeinoz67/madeinoz-knowledge-system/actions`

#### 2. Select Release Workflow

- Click on "Release" in the left sidebar
- Click "Run workflow" button (top right)

#### 3. Fill in Release Details

- **Branch:** Select `main`
- **Version:** Enter semantic version (e.g., `1.0.2`)
  - Must be in format `X.Y.Z`
  - Must not already exist as a tag
- **Pre-release:** Check if this is a pre-release (beta, rc, etc.)

#### 4. Click "Run workflow"

The workflow will:
- ✅ Validate version format
- ✅ Update Dockerfile with new version
- ✅ Create git tag `v1.0.2`
- ✅ Generate release notes from commits
- ✅ Create GitHub Release
- ✅ Trigger Docker build (automatically via tag push)
- ✅ Push images to registries

#### 5. Monitor Progress

- **Release workflow:** `https://github.com/madeinoz67/madeinoz-knowledge-system/actions/workflows/release.yml`
- **Docker build:** `https://github.com/madeinoz67/madeinoz-knowledge-system/actions/workflows/docker-build.yml`

#### 6. Verify Release

**Check GitHub Release:**
```
https://github.com/madeinoz67/madeinoz-knowledge-system/releases/tag/v1.0.2
```

**Pull the image:**
```bash
# From GHCR
docker pull ghcr.io/madeinoz67/madeinoz-knowledge-system:1.0.2
docker pull ghcr.io/madeinoz67/madeinoz-knowledge-system:latest

# Verify version
docker run --rm ghcr.io/madeinoz67/madeinoz-knowledge-system:1.0.2 \
  sh -c 'grep "LABEL version" /Dockerfile || echo "Version: 1.0.2"'
```

## Version Numbering

We follow [Semantic Versioning](https://semver.org/) (SemVer):

```
MAJOR.MINOR.PATCH
1.0.2
```

- **MAJOR** - Incompatible API changes or major features
- **MINOR** - Backward-compatible functionality additions
- **PATCH** - Backward-compatible bug fixes

### When to Bump Each Number

**MAJOR (1.x.x → 2.0.0):**
- Breaking changes to environment variables
- Incompatible Docker compose file changes
- Migration to official upstream images (when patches are no longer needed)
- Major refactoring requiring user action

**MINOR (1.0.x → 1.1.0):**
- New features (new patches, new backend support)
- New MCP tools or capabilities
- New configuration options (backward-compatible)

**PATCH (1.0.1 → 1.0.2):**
- Bug fixes (password typo, network alias, volume mount issues)
- Documentation improvements
- Dependency updates
- Performance improvements

## Docker Hub Configuration (Optional)

To enable Docker Hub publishing:

### 1. Create Docker Hub Account
- Go to: https://hub.docker.com
- Create account or sign in

### 2. Create Access Token
- Settings → Security → New Access Token
- Name: `madeinoz-knowledge-system-github`
- Permissions: Read, Write, Delete

### 3. Add GitHub Secrets
- Go to: `https://github.com/madeinoz67/madeinoz-knowledge-system/settings/secrets/actions`
- Add two secrets:
  - `DOCKERHUB_USERNAME` - Your Docker Hub username
  - `DOCKERHUB_TOKEN` - The access token from step 2

### 4. Verify in Next Build
The workflow will automatically detect the secrets and push to Docker Hub.

## Rollback a Release

If a release has critical issues:

### 1. Mark as Pre-release (Quick Fix)

```bash
# Via GitHub UI
1. Go to Releases
2. Click "Edit" on problematic release
3. Check "This is a pre-release"
4. Save
```

### 2. Create Hotfix Release

```bash
# Via GitHub Actions
1. Fix the issue in a branch
2. Merge to main
3. Run release workflow with new version (e.g., 1.0.3)
4. New version becomes latest
```

### 3. Delete Release (Nuclear Option)

```bash
# Delete GitHub Release (via UI)
1. Go to Releases
2. Click "Delete" on problematic release

# Delete git tag
git push --delete origin v1.0.2
git tag -d v1.0.2

# Note: Docker images cannot be deleted from GHCR/Docker Hub easily
# Instead, create a new release that supersedes the bad one
```

## Changelog Generation

The release workflow automatically generates changelogs from git commit messages.

### Writing Good Commit Messages

Use conventional commit format for better changelogs:

```bash
# Features
git commit -m "feat: add Neo4j health check retry logic"

# Bug fixes
git commit -m "fix: correct password typo in docker-compose-neo4j.yml"

# Documentation
git commit -m "docs: add developer notes for custom image"

# Chores
git commit -m "chore: bump version to 1.0.2"

# Breaking changes
git commit -m "feat!: migrate to official upstream image

BREAKING CHANGE: Custom MADEINOZ_KNOWLEDGE_* prefixes no longer supported"
```

**Prefixes:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `chore:` - Maintenance
- `refactor:` - Code refactoring
- `test:` - Tests
- `perf:` - Performance improvement
- `ci:` - CI/CD changes

## Monitoring Releases

### Check Latest Version

```bash
# Via GitHub API
curl -s https://api.github.com/repos/madeinoz67/madeinoz-knowledge-system/releases/latest | jq -r .tag_name

# Via Docker
docker pull ghcr.io/madeinoz67/madeinoz-knowledge-system:latest
docker inspect ghcr.io/madeinoz67/madeinoz-knowledge-system:latest | jq -r '.[0].Config.Labels.version'
```

### Subscribe to Releases

1. Go to: `https://github.com/madeinoz67/madeinoz-knowledge-system`
2. Click "Watch" → "Custom" → "Releases"
3. You'll receive notifications for new releases

### RSS Feed

Subscribe to releases RSS feed:
```
https://github.com/madeinoz67/madeinoz-knowledge-system/releases.atom
```

## Troubleshooting

### Build Fails with "Permission Denied"

**Problem:** GitHub Actions can't push images or create releases

**Solution:** Check repository settings:
```
Settings → Actions → General → Workflow permissions
✓ Read and write permissions
```

### Docker Hub Push Fails

**Problem:** Missing or invalid Docker Hub credentials

**Solution:**
1. Verify secrets exist: `Settings → Secrets → Actions`
2. Ensure `DOCKERHUB_TOKEN` is an access token (not password)
3. Regenerate token if needed

### Tag Already Exists

**Problem:** Version tag already exists in git

**Solution:**
```bash
# Delete remote tag
git push --delete origin v1.0.2

# Delete local tag
git tag -d v1.0.2

# Try release again
```

### Image Not Found After Release

**Problem:** Docker pull fails after successful release

**Solution:**
```bash
# Check if tag exists on GHCR
curl -s https://ghcr.io/v2/madeinoz67/madeinoz-knowledge-system/tags/list | jq .

# Verify workflow completed
# Go to: Actions → Docker Build and Publish
# Check for green checkmark

# Try full image path
docker pull ghcr.io/madeinoz67/madeinoz-knowledge-system:1.0.2
```

---

**See Also:**
- [Developer Notes](developer-notes.md) - Custom image rationale
- [Configuration Reference](configuration.md) - Environment variables
- [Installation Guide](../installation/index.md) - Setup instructions
