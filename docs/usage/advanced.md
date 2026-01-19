---
title: "Advanced Usage"
description: "Advanced patterns, backup strategies, and expert-level knowledge management techniques"
---

# Advanced Usage Guide

This guide covers advanced patterns, backup and restore procedures, and expert-level techniques for the Madeinoz Knowledge System.

## Advanced Usage Patterns

### Capturing Code Snippets

````
You: Remember this bash script for starting services:

```bash
#!/bin/bash
podman start madeinoz-knowledge-graph-mcp
podman start madeinoz-knowledge-falkordb
echo "Services started"
```

This starts both knowledge system containers.
````

The system captures the code and its purpose.

### Capturing Conversations

```
You: Store this conversation we just had about API design patterns.
[paste or summarize the conversation]
```

Good for preserving important discussions.

### Capturing Research

```
You: Remember this research finding: Vector embeddings using text-embedding-3-small
are 99.8% as accurate as large embeddings but 5x cheaper and 3x faster to compute.
```

Perfect for building a research knowledge base.

### Capturing Meeting Notes

```
You: Store these meeting notes from the architecture review:
- Decided on microservices architecture
- Will use gRPC for service communication
- PostgreSQL for primary database
- Redis for caching layer
Action items: Complete service design by Friday
```

### Creating Knowledge Chains

Build knowledge over time by connecting related episodes:

**Day 1:**
```
Remember: Exploring knowledge graph options. Considering Neo4j and FalkorDB.
```

**Day 2:**
```
Remember: FalkorDB is lighter than Neo4j because it's a Redis module,
not a standalone database.
```

**Day 3:**
```
Remember: Decision made - using FalkorDB for Madeinoz Knowledge System.
```

The system automatically links these episodes through their shared entities.

## Backup & Restore

For complete backup and restore procedures, see the dedicated [Backup & Restore Guide](backup-restore.md).

## Related Documentation

- Return to [basic usage](basic-usage.md) for fundamental operations
- Learn more about [how the system works](../concepts/knowledge-graph.md)
- Troubleshoot issues in the [troubleshooting guide](../troubleshooting/common-issues.md)
