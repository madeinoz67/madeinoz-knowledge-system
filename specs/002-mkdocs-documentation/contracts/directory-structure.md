# Contract: Directory Structure

**Feature**: 002-mkdocs-documentation
**Version**: 1.0.0

This document defines the required directory structure after implementation. All paths listed MUST exist for the feature to be considered complete.

## Required Directory Structure

```text
madeinoz-knowledge-system/
├── mkdocs.yml                              # MkDocs configuration file
├── docs/                                   # Documentation source directory
│   ├── index.md                            # Homepage
│   ├── assets/                             # Static assets
│   │   ├── logo.png                        # Site logo (from icons/)
│   │   ├── favicon.ico                     # Browser favicon
│   │   └── images/                         # Page images
│   │       └── falkordb_ui.png             # Existing FalkorDB screenshot
│   ├── getting-started/                    # Getting Started section
│   │   ├── overview.md                     # System overview
│   │   └── quick-reference.md              # Quick reference guide
│   ├── installation/                       # Installation section
│   │   ├── index.md                        # Installation guide (main)
│   │   ├── requirements.md                 # Prerequisites
│   │   └── verification.md                 # Post-install verification
│   ├── usage/                              # Usage section
│   │   ├── basic-usage.md                  # Basic usage guide
│   │   └── advanced.md                     # Advanced usage
│   ├── concepts/                           # Concepts section
│   │   ├── architecture.md                 # System architecture
│   │   └── knowledge-graph.md              # Knowledge graph concepts
│   ├── troubleshooting/                    # Troubleshooting section
│   │   └── common-issues.md                # Common issues and solutions
│   └── reference/                          # Reference section
│       ├── cli.md                          # CLI reference
│       ├── configuration.md                # Configuration options
│       ├── model-guide.md                  # AI model guide
│       └── benchmarks.md                   # Model benchmarks
└── .github/
    └── workflows/
        └── docs.yml                        # Documentation deployment workflow
```

## File Counts

| Section | Required Files |
|---------|----------------|
| Root | 2 (mkdocs.yml, docs/index.md) |
| Getting Started | 2 |
| Installation | 3 |
| Usage | 2 |
| Concepts | 2 |
| Troubleshooting | 1 |
| Reference | 4 |
| Assets | 3+ |
| Workflows | 1 |
| **Total** | **20+** |

## Source File Mapping

| Original Location | New Location | Status |
|-------------------|--------------|--------|
| `docs/INDEX.md` | `docs/index.md` | Merge |
| `docs/README.md` | `docs/getting-started/overview.md` | Move |
| `docs/QUICK_REFERENCE.md` | `docs/getting-started/quick-reference.md` | Move |
| `docs/installation.md` | `docs/installation/requirements.md` | Move |
| `INSTALL.md` | `docs/installation/index.md` | Copy |
| `VERIFY.md` | `docs/installation/verification.md` | Copy |
| `docs/usage.md` | `docs/usage/basic-usage.md` | Move |
| `docs/concepts.md` | `docs/concepts/knowledge-graph.md` | Move |
| `docs/troubleshooting.md` | `docs/troubleshooting/common-issues.md` | Move |
| `docs/OLLAMA-MODEL-GUIDE.md` | `docs/reference/model-guide.md` | Move |
| `docs/MODEL-BENCHMARK-RESULTS.md` | `docs/reference/benchmarks.md` | Move |
| `README.md` (architecture section) | `docs/concepts/architecture.md` | Extract |

## New Files to Create

| File | Content Source |
|------|----------------|
| `docs/usage/advanced.md` | Extract from `docs/usage.md` |
| `docs/reference/cli.md` | Extract from `README.md` |
| `docs/reference/configuration.md` | Extract from `INSTALL.md` |

## Validation Criteria

- [ ] All 20+ required files exist
- [ ] `mkdocs build --strict` passes without errors
- [ ] All internal links resolve correctly
- [ ] All image references resolve correctly
- [ ] Navigation structure matches `mkdocs.yml`
