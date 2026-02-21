# AI Image Generation Style Guide

This document defines the visual style for AI-generated images in the Madeinoz Knowledge System documentation.

## Visual Style: Excalidraw Architect

All technical diagrams use the **Excalidraw Architect** style - clean, hand-drawn technical diagrams created by an architect-artist aesthetic.

## Color Palette

```
Background:    Sepia #EAE9DF (pure, no grid/texture)
Primary:       Charcoal #2D2D2D (text, labels)
Accent 1:      Purple #4A148C (key insights, callouts)
Accent 2:      Teal #00796B (flows, arrows, connections)
Structure:     White/Grey shades (boxes, components)
```

## Typography System

### Headers (Valkyrie-style)
- **Style:** Elegant wedge-serif italic (like Palatino but refined)
- **Size:** Large, 3-4x body text
- **Color:** Black #000000
- **Position:** Top-left, left-justified

### Labels (Concourse T3-style)
- **Style:** Geometric sans-serif (like Avenir/Futura but warmer)
- **Size:** Medium, readable
- **Color:** Charcoal #2D2D2D
- **Use:** Box labels, node names, technical identifiers

### Insights (Advocate-style)
- **Style:** Condensed italic sans-serif (sporty editorial)
- **Size:** Smaller, 60-70% of labels
- **Color:** Purple #4A148C
- **Format:** Always italic with asterisks: `*insight text*`

## Diagram Rules

### Must Have
- ✅ Pure sepia #EAE9DF background (NO grid, NO texture)
- ✅ Title and subtitle in top-left
- ✅ 1-3 insight callouts in purple italic
- ✅ Hand-drawn Excalidraw aesthetic
- ✅ Architect/artist quality

### Must NOT Have
- ❌ Grid lines or texture on background
- ❌ Generic or cartoonish styling
- ❌ Over-coloring (80% grey/black, color is accent only)
- ❌ Dark backgrounds (always sepia)

## Generation Command

```bash
bun run ~/.claude/skills/Art/Tools/Generate.ts \
  --model nano-banana-pro \
  --size 2K \
  --aspect-ratio 16:9 \
  --prompt "Technical diagram in Excalidraw architect style. Pure sepia #EAE9DF background with NO grid lines.

TITLE: '[Title]' - Elegant wedge-serif italic, top-left
SUBTITLE: '[Subtitle]' - Wedge-serif regular below title

[Diagram content description]

STYLE: Hand-drawn Excalidraw look, architect artist quality. Geometric sans-serif labels. White/grey boxes with charcoal labels. Teal arrows for flow. Purple accents for insights.

INSIGHT: '*[key insight text]*' - Condensed italic, purple" \
  --output docs/assets/[filename].jpg
```

## Example Prompts

### Architecture Diagram
```
TITLE: 'Document Memory (RAG)'
SUBTITLE: 'Semantic search with Qdrant vector database'

Flow: inbox → Docling Parser → Semantic Chunking → Ollama Embeddings → Qdrant → Search Results
Boxes in white/grey, teal arrows between components.
```

### Two-Tier Model
```
TITLE: 'LKAP Two-Tier Memory Model'
SUBTITLE: 'Document Memory + Knowledge Memory'

Vertical stack:
- TOP: Tier 1 box (Document Memory, Qdrant) - subtle blue tint
- ARROW: dotted teal, pointing down, labeled "Promote with evidence"
- BOTTOM: Tier 2 box (Knowledge Memory, Graphiti) - subtle green tint

INSIGHTS:
- '*Documents are evidence*' near top
- '*Knowledge is curated truth*' near bottom
```

## Aspect Ratios

| Use Case | Ratio | Flag |
|----------|-------|------|
| Standard diagram | 16:9 | `--aspect-ratio 16:9` |
| Square/portrait | 1:1 | `--aspect-ratio 1:1` |
| Wide system diagram | 21:9 | `--aspect-ratio 21:9` |

## File Locations

- **Generated images:** `docs/assets/`
- **Reference diagrams:** `docs/images/`
- **Workflow source:** `~/.claude/skills/Art/Workflows/TechnicalDiagrams.md`
