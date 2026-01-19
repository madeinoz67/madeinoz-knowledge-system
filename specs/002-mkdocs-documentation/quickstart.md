# Quickstart Guide - MkDocs Material Documentation Site

**Feature**: 002-mkdocs-documentation
**Date**: 2026-01-19
**Time to Complete**: ~15 minutes

## Prerequisites

- Git repository cloned locally
- Python 3.x installed
- Basic familiarity with Markdown

## Quick Setup (5 Steps)

### Step 1: Install MkDocs Material

```bash
pip install mkdocs-material
```

### Step 2: Create Directory Structure

```bash
mkdir -p docs/{getting-started,installation,usage,concepts,troubleshooting,reference,assets/images}
```

### Step 3: Create mkdocs.yml

Create `mkdocs.yml` in the repository root:

```yaml
site_name: Madeinoz Knowledge System
theme:
  name: material
  palette:
    - scheme: default
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - scheme: slate
      toggle:
        icon: material/brightness-4
        name: Switch to light mode

nav:
  - Home: index.md
  - Getting Started:
    - Overview: getting-started/overview.md
    - Quick Reference: getting-started/quick-reference.md
  - Installation:
    - Guide: installation/index.md
    - Requirements: installation/requirements.md
    - Verification: installation/verification.md
  - Usage:
    - Basic Usage: usage/basic-usage.md
    - Advanced: usage/advanced.md
  - Concepts:
    - Architecture: concepts/architecture.md
    - Knowledge Graph: concepts/knowledge-graph.md
  - Troubleshooting:
    - Common Issues: troubleshooting/common-issues.md
  - Reference:
    - CLI: reference/cli.md
    - Configuration: reference/configuration.md
    - Model Guide: reference/model-guide.md
    - Benchmarks: reference/benchmarks.md
```

### Step 4: Migrate Existing Files

Move existing documentation to new locations:

| From | To |
|------|-----|
| `docs/README.md` | `docs/getting-started/overview.md` |
| `docs/QUICK_REFERENCE.md` | `docs/getting-started/quick-reference.md` |
| `INSTALL.md` | `docs/installation/index.md` |
| `docs/installation.md` | `docs/installation/requirements.md` |
| `VERIFY.md` | `docs/installation/verification.md` |
| `docs/usage.md` | `docs/usage/basic-usage.md` |
| `docs/concepts.md` | `docs/concepts/knowledge-graph.md` |
| `docs/troubleshooting.md` | `docs/troubleshooting/common-issues.md` |
| `docs/OLLAMA-MODEL-GUIDE.md` | `docs/reference/model-guide.md` |
| `docs/MODEL-BENCHMARK-RESULTS.md` | `docs/reference/benchmarks.md` |

### Step 5: Test Locally

```bash
# Build with strict mode (fails on broken links)
mkdocs build --strict

# Serve locally for preview
mkdocs serve
```

Visit `http://127.0.0.1:8000` to preview the site.

## Verification Checklist

- [ ] `mkdocs build --strict` passes without errors
- [ ] All navigation items load correctly
- [ ] Dark/light mode toggle works
- [ ] Search returns relevant results
- [ ] Internal links don't 404

## Common Issues

**"File not found" errors**: Ensure all files listed in `nav:` exist in `docs/`

**Missing images**: Move `docs/assets/` content and update image paths

**Build warnings**: Address all warnings for `--strict` mode to pass

## Next Steps

1. Create `docs/index.md` homepage
2. Add GitHub Actions workflow for auto-deploy
3. Configure GitHub Pages in repository settings
4. Push changes to trigger deployment

## Full Documentation

- See `research.md` for detailed analysis
- See `data-model.md` for configuration schemas
- See `contracts/` for exact implementation specs
