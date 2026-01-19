# Phase 0: Research - MkDocs Material Documentation Site

**Feature**: 002-mkdocs-documentation
**Date**: 2026-01-19
**Status**: Complete

## Executive Summary

This research phase analyzes the existing documentation structure in the madeinoz-knowledge-system repository and identifies the optimal approach for migrating to MkDocs Material with GitHub Pages deployment. The project has 11 documentation files across `docs/` and the repository root that will be consolidated into a hierarchical structure with 6+ navigation sections.

## Existing Documentation Inventory

### Repository Root Files

| File | Lines | Purpose | Migration Target |
|------|-------|---------|------------------|
| `README.md` | ~1310 | Complete pack documentation with architecture, installation prompt, configuration | Split: `index.md` (overview), `concepts/architecture.md` |
| `INSTALL.md` | ~2142 | Detailed installation guide with all steps | `installation/index.md` |
| `VERIFY.md` | (assumed) | Installation verification | `installation/verification.md` |

### docs/ Directory Files

| File | Lines | Purpose | Migration Target |
|------|-------|---------|------------------|
| `docs/INDEX.md` | ~247 | Documentation index with navigation | `index.md` (merge with README overview) |
| `docs/README.md` | (check) | User-facing overview | Merge into `index.md` |
| `docs/installation.md` | (check) | Installation steps | Merge into `installation/index.md` |
| `docs/usage.md` | (check) | Usage guide | `usage/basic-usage.md` |
| `docs/concepts.md` | (check) | Key concepts | `concepts/knowledge-graph.md` |
| `docs/troubleshooting.md` | (check) | Troubleshooting guide | `troubleshooting/common-issues.md` |
| `docs/QUICK_REFERENCE.md` | (check) | Quick reference | `getting-started/quick-reference.md` |
| `docs/OLLAMA-MODEL-GUIDE.md` | (check) | Ollama model guide | `reference/model-guide.md` |
| `docs/MODEL-BENCHMARK-RESULTS.md` | (check) | Model benchmarks | `reference/benchmarks.md` |

### Assets

| File | Purpose | Migration Action |
|------|---------|------------------|
| `docs/assets/falkordb_ui.png` | FalkorDB UI screenshot | Keep in `docs/assets/images/` |
| (repo root) | Project logo | Copy to `docs/assets/logo.png` |

## Content Consolidation Analysis

### Duplicate Content Identification

The README.md (root) and docs/README.md contain overlapping content that needs consolidation:

1. **Installation instructions** - Detailed in both README.md and docs/installation.md
2. **Quick start** - Present in INDEX.md and README.md
3. **Architecture diagrams** - ASCII art in README.md, descriptions in docs/concepts.md

### Recommended Consolidation

| Content Type | Primary Source | Keep In | Redirect From |
|--------------|----------------|---------|---------------|
| Installation | INSTALL.md | installation/index.md | README.md installation section |
| Quick Start | docs/INDEX.md | getting-started/overview.md | README.md quick start |
| Architecture | README.md | concepts/architecture.md | docs/concepts.md |
| Usage | docs/usage.md | usage/basic-usage.md | - |
| Troubleshooting | docs/troubleshooting.md | troubleshooting/common-issues.md | - |

## MkDocs Material Configuration

### Required Dependencies

```yaml
# mkdocs.yml - Key dependencies
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
  features:
    - navigation.sections
    - navigation.expand
    - navigation.top
    - search.suggest
    - search.highlight
    - content.code.copy

plugins:
  - search
  - offline  # Optional: for offline documentation

markdown_extensions:
  - admonition
  - pymdownx.highlight:
      anchor_linenums: true
  - pymdownx.superfences
  - pymdownx.tabbed:
      alternate_style: true
  - toc:
      permalink: true
```

### Navigation Structure

```yaml
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

## GitHub Actions Workflow

### Recommended Workflow

```yaml
# .github/workflows/docs.yml
name: Deploy Documentation

on:
  push:
    branches:
      - main
    paths:
      - 'docs/**'
      - 'mkdocs.yml'
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.x'
      - run: pip install mkdocs-material
      - run: mkdocs build --strict
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

## Technical Decisions

### Theme Selection: MkDocs Material

**Why Material over alternatives:**
- Industry standard for technical documentation
- Built-in search with highlighting
- Dark/light mode support
- Responsive design out of the box
- Code block copy functionality
- Admonition support for notes/warnings
- Active maintenance and community

### Build Validation

MkDocs with `--strict` flag will:
- Fail on broken internal links
- Warn on missing files
- Validate navigation structure
- Check markdown syntax

### URL Structure

| Current | New | Notes |
|---------|-----|-------|
| N/A | `/<repo>/` | Homepage |
| N/A | `/<repo>/getting-started/` | Getting started section |
| N/A | `/<repo>/installation/` | Installation section |
| `docs/README.md` | `/<repo>/` | Redirect to homepage |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Broken internal links | Medium | Medium | Use `mkdocs build --strict` in CI |
| Missing images | Low | Low | Audit assets before migration |
| Search indexing issues | Low | Medium | Test search after deployment |
| URL changes breaking external links | Low | High | Maintain redirects if needed |

## Implementation Phases

### Phase 1: Setup (Estimated: 30 min)
1. Create `mkdocs.yml` configuration
2. Set up GitHub Actions workflow
3. Create directory structure

### Phase 2: Migration (Estimated: 2 hours)
1. Reorganize existing files
2. Create new placeholder files
3. Update internal links
4. Add missing frontmatter

### Phase 3: Enhancement (Estimated: 1 hour)
1. Add MkDocs Material features (admonitions, tabs)
2. Add code copy buttons
3. Configure search
4. Add navigation features

### Phase 4: Verification (Estimated: 30 min)
1. Run `mkdocs build --strict`
2. Test locally with `mkdocs serve`
3. Verify all links work
4. Test search functionality

## Recommendations

1. **Start simple**: Use minimal mkdocs.yml configuration, add features incrementally
2. **Preserve existing content**: Don't rewrite documentation, just reorganize
3. **Test locally first**: Use `mkdocs serve` before pushing to CI
4. **Enable strict mode**: Catch broken links during build
5. **Use GitHub Pages action**: Standard deployment, no manual configuration

## Open Questions (Resolved)

1. ~~Which GitHub Pages URL will be used?~~ → Standard `<user>.github.io/<repo>/`
2. ~~Should we add a custom domain?~~ → Not in initial scope
3. ~~Is English-only acceptable?~~ → Yes, per spec assumptions

## References

- [MkDocs Material Documentation](https://squidfunk.github.io/mkdocs-material/)
- [GitHub Pages with Actions](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site#publishing-with-a-custom-github-actions-workflow)
- [MkDocs Getting Started](https://www.mkdocs.org/getting-started/)
