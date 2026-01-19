---
title: "Backup & Restore"
description: "Complete backup and restore procedures for protecting your knowledge graph data across Neo4j and FalkorDB backends"
---

# Backup & Restore Guide

Your knowledge graph is stored in Neo4j (the default) or FalkorDB. Here's how to protect and migrate your data.

**Note:** The instructions below show both Neo4j (default) and FalkorDB commands. Use the section that matches your configured backend.

## Quick Backup

Create a backup of your entire knowledge graph:

**Neo4j (Default) - Podman:**
```bash
# Navigate to pack directory
cd ~/.config/pai/Packs/madeinoz-knowledge-system

# Create backup directory
mkdir -p backups

# Backup Neo4j data directory
podman exec madeinoz-knowledge-neo4j neo4j-admin database dump neo4j --to-stdout > ./backups/knowledge-$(date +%Y%m%d-%H%M%S).dump

echo "✓ Backup created"
```

**Neo4j (Default) - Docker:**
```bash
cd ~/.config/pai/Packs/madeinoz-knowledge-system
mkdir -p backups

docker exec madeinoz-knowledge-neo4j neo4j-admin database dump neo4j --to-stdout > ./backups/knowledge-$(date +%Y%m%d-%H%M%S).dump

echo "✓ Backup created"
```

**FalkorDB Backend - Podman:**
```bash
cd ~/.config/pai/Packs/madeinoz-knowledge-system
mkdir -p backups

# Backup the FalkorDB data (RDB snapshot)
podman exec madeinoz-knowledge-falkordb redis-cli BGSAVE
sleep 2  # Wait for save to complete
podman cp madeinoz-knowledge-falkordb:/data/dump.rdb ./backups/knowledge-$(date +%Y%m%d-%H%M%S).rdb

echo "✓ Backup created"
```

**FalkorDB Backend - Docker:**
```bash
cd ~/.config/pai/Packs/madeinoz-knowledge-system
mkdir -p backups

docker exec madeinoz-knowledge-falkordb redis-cli BGSAVE
sleep 2
docker cp madeinoz-knowledge-falkordb:/data/dump.rdb ./backups/knowledge-$(date +%Y%m%d-%H%M%S).rdb

echo "✓ Backup created"
```

## Scheduled Backups

Create a cron job for automatic daily backups:

**Neo4j (Default) - Podman:**
```bash
# Edit crontab
crontab -e

# Add this line for daily backup at 2 AM
0 2 * * * cd ~/.config/pai/Packs/madeinoz-knowledge-system && podman exec madeinoz-knowledge-neo4j neo4j-admin database dump neo4j --to-stdout > ./backups/knowledge-$(date +\%Y\%m\%d).dump
```

**Neo4j (Default) - Docker:**
```bash
crontab -e

# Add this line for daily backup at 2 AM
0 2 * * * cd ~/.config/pai/Packs/madeinoz-knowledge-system && docker exec madeinoz-knowledge-neo4j neo4j-admin database dump neo4j --to-stdout > ./backups/knowledge-$(date +\%Y\%m\%d).dump
```

**FalkorDB Backend - Podman:**
```bash
crontab -e

# Add this line for daily backup at 2 AM
0 2 * * * cd ~/.config/pai/Packs/madeinoz-knowledge-system && podman exec madeinoz-knowledge-falkordb redis-cli BGSAVE && sleep 2 && podman cp madeinoz-knowledge-falkordb:/data/dump.rdb ./backups/knowledge-$(date +\%Y\%m\%d).rdb
```

**FalkorDB Backend - Docker:**
```bash
crontab -e

# Add this line for daily backup at 2 AM
0 2 * * * cd ~/.config/pai/Packs/madeinoz-knowledge-system && docker exec madeinoz-knowledge-falkordb redis-cli BGSAVE && sleep 2 && docker cp madeinoz-knowledge-falkordb:/data/dump.rdb ./backups/knowledge-$(date +\%Y\%m\%d).rdb
```

## Restore from Backup

To restore your knowledge graph from a backup:

**Neo4j (Default) - Podman:**
```bash
cd ~/.config/pai/Packs/madeinoz-knowledge-system

# 1. Stop the running containers
bun run stop

# 2. Find your backup file
ls -la backups/

# 3. Restore using neo4j-admin
podman run --rm -v ./backups:/backups:ro -v madeinoz-knowledge-neo4j-data:/data neo4j:2025.12.1 \
    neo4j-admin database load neo4j --from-stdin < ./backups/knowledge-YYYYMMDD-HHMMSS.dump --overwrite-destination

# 4. Restart the knowledge system
bun run start

# 5. Verify restoration
bun run status
```

**Neo4j (Default) - Docker:**
```bash
cd ~/.config/pai/Packs/madeinoz-knowledge-system

# 1. Stop the running containers
bun run stop

# 2. Find your backup file
ls -la backups/

# 3. Restore using neo4j-admin
docker run --rm -v ./backups:/backups:ro -v madeinoz-knowledge-neo4j-data:/data neo4j:2025.12.1 \
    neo4j-admin database load neo4j --from-stdin < ./backups/knowledge-YYYYMMDD-HHMMSS.dump --overwrite-destination

# 4. Restart the knowledge system
bun run start

# 5. Verify restoration
bun run status
```

Replace `knowledge-YYYYMMDD-HHMMSS.dump` with your actual backup filename.

**FalkorDB Backend - Podman:**
```bash
cd ~/.config/pai/Packs/madeinoz-knowledge-system

# 1. Stop the running containers
bun run stop

# 2. Find your backup file
ls -la backups/

# 3. Start a temporary container to restore data
podman run --rm -v ./backups:/backups:ro -v madeinoz-knowledge-data:/data falkordb/falkordb:latest \
    sh -c "cp /backups/knowledge-YYYYMMDD-HHMMSS.rdb /data/dump.rdb"

# 4. Restart the knowledge system
bun run start

# 5. Verify restoration
bun run status
```

**FalkorDB Backend - Docker:**
```bash
cd ~/.config/pai/Packs/madeinoz-knowledge-system

# 1. Stop the running containers
bun run stop

# 2. Find your backup file
ls -la backups/

# 3. Start a temporary container to restore data
docker run --rm -v ./backups:/backups:ro -v madeinoz-knowledge-data:/data falkordb/falkordb:latest \
    sh -c "cp /backups/knowledge-YYYYMMDD-HHMMSS.rdb /data/dump.rdb"

# 4. Restart the knowledge system
bun run start

# 5. Verify restoration
bun run status
```

Replace `knowledge-YYYYMMDD-HHMMSS.rdb` with your actual backup filename.

## Export to JSON (Portable Backup)

For a human-readable backup or migration to another system:

**Neo4j (Default) - Podman/Docker:**
```bash
# Connect to Neo4j and export graph data using cypher-shell
podman exec madeinoz-knowledge-neo4j cypher-shell -u neo4j -p password \
    "MATCH (n)-[r]->(m) RETURN n, r, m" > backups/knowledge-export.txt

# Export all nodes
podman exec madeinoz-knowledge-neo4j cypher-shell -u neo4j -p password \
    "MATCH (n) RETURN n" > backups/nodes-export.txt

# Export all relationships
podman exec madeinoz-knowledge-neo4j cypher-shell -u neo4j -p password \
    "MATCH ()-[r]->() RETURN r" > backups/relationships-export.txt
```

**FalkorDB Backend - Podman:**
```bash
# Connect to FalkorDB and export graph data
podman exec madeinoz-knowledge-falkordb redis-cli GRAPH.QUERY graphiti \
    "MATCH (n)-[r]->(m) RETURN n, r, m" > backups/knowledge-export.txt

# Export all nodes
podman exec madeinoz-knowledge-falkordb redis-cli GRAPH.QUERY graphiti \
    "MATCH (n) RETURN n" > backups/nodes-export.txt

# Export all relationships
podman exec madeinoz-knowledge-falkordb redis-cli GRAPH.QUERY graphiti \
    "MATCH ()-[r]->() RETURN r" > backups/relationships-export.txt
```

**FalkorDB Backend - Docker:**
```bash
# Connect to FalkorDB and export graph data
docker exec madeinoz-knowledge-falkordb redis-cli GRAPH.QUERY graphiti \
    "MATCH (n)-[r]->(m) RETURN n, r, m" > backups/knowledge-export.txt

# Export all nodes
docker exec madeinoz-knowledge-falkordb redis-cli GRAPH.QUERY graphiti \
    "MATCH (n) RETURN n" > backups/nodes-export.txt

# Export all relationships
docker exec madeinoz-knowledge-falkordb redis-cli GRAPH.QUERY graphiti \
    "MATCH ()-[r]->() RETURN r" > backups/relationships-export.txt
```

## Full Volume Backup

For a complete backup including all container data:

**Podman:**
```bash
cd ~/.config/pai/Packs/madeinoz-knowledge-system

# 1. Stop containers
bun run stop

# 2. Export the entire volume
podman volume export madeinoz-knowledge-data > backups/volume-$(date +%Y%m%d-%H%M%S).tar

# 3. Restart containers
bun run start

echo "✓ Full volume backup created"
```

**Docker:**
```bash
cd ~/.config/pai/Packs/madeinoz-knowledge-system

# 1. Stop containers
bun run stop

# 2. Export the entire volume (Docker requires a helper container)
docker run --rm -v madeinoz-knowledge-data:/data -v $(pwd)/backups:/backup alpine \
    tar cvf /backup/volume-$(date +%Y%m%d-%H%M%S).tar -C /data .

# 3. Restart containers
bun run start

echo "✓ Full volume backup created"
```

## Restore from Volume Backup

**Podman:**
```bash
cd ~/.config/pai/Packs/madeinoz-knowledge-system

# 1. Stop containers
bun run stop

# 2. Remove existing volume (WARNING: destroys current data)
podman volume rm madeinoz-knowledge-data

# 3. Create new volume and restore
podman volume create madeinoz-knowledge-data
podman volume import madeinoz-knowledge-data < backups/volume-YYYYMMDD-HHMMSS.tar

# 4. Restart containers
bun run start

# 5. Verify
bun run status
```

**Docker:**
```bash
cd ~/.config/pai/Packs/madeinoz-knowledge-system

# 1. Stop containers
bun run stop

# 2. Remove existing volume (WARNING: destroys current data)
docker volume rm madeinoz-knowledge-data

# 3. Create new volume and restore
docker volume create madeinoz-knowledge-data
docker run --rm -v madeinoz-knowledge-data:/data -v $(pwd)/backups:/backup alpine \
    sh -c "cd /data && tar xvf /backup/volume-YYYYMMDD-HHMMSS.tar"

# 4. Restart containers
bun run start

# 5. Verify
bun run status
```

## Migration to New Machine

To move your knowledge graph to a new computer:

**Podman - On the old machine:**
```bash
cd ~/.config/pai/Packs/madeinoz-knowledge-system

# Create portable backup
bun run stop
podman volume export madeinoz-knowledge-data > knowledge-migration.tar
bun run start

# Transfer the file
scp knowledge-migration.tar user@newmachine:~/
```

**Podman - On the new machine:**
```bash
# After installing madeinoz-knowledge-system
cd ~/.config/pai/Packs/madeinoz-knowledge-system

# Import the volume
podman volume create madeinoz-knowledge-data
podman volume import madeinoz-knowledge-data < ~/knowledge-migration.tar

# Start the system
bun run start
bun run status
```

**Docker - On the old machine:**
```bash
cd ~/.config/pai/Packs/madeinoz-knowledge-system

# Create portable backup
bun run stop
docker run --rm -v madeinoz-knowledge-data:/data -v $(pwd):/backup alpine \
    tar cvf /backup/knowledge-migration.tar -C /data .
bun run start

# Transfer the file
scp knowledge-migration.tar user@newmachine:~/
```

**Docker - On the new machine:**
```bash
# After installing madeinoz-knowledge-system
cd ~/.config/pai/Packs/madeinoz-knowledge-system

# Import the volume
docker volume create madeinoz-knowledge-data
docker run --rm -v madeinoz-knowledge-data:/data -v ~/:/backup alpine \
    sh -c "cd /data && tar xvf /backup/knowledge-migration.tar"

# Start the system
bun run start
bun run status
```

## Backup Best Practices

| Practice | Recommendation |
|----------|---------------|
| **Frequency** | Daily for active use, weekly for light use |
| **Retention** | Keep at least 7 daily + 4 weekly backups |
| **Location** | Store backups outside the container (local disk, cloud) |
| **Verification** | Test restore from backup periodically |
| **Before upgrades** | Always backup before upgrading the system |

## Quick Reference

**Neo4j (Default) - Podman:**
```bash
# Backup commands
podman exec madeinoz-knowledge-neo4j neo4j-admin database dump neo4j --to-stdout > backup.dump
podman volume export madeinoz-knowledge-neo4j-data > volume-backup.tar

# Restore commands
podman volume import madeinoz-knowledge-neo4j-data < volume-backup.tar

# Verification
podman exec madeinoz-knowledge-neo4j cypher-shell -u neo4j -p password "MATCH (n) RETURN count(n)"
```

**Neo4j (Default) - Docker:**
```bash
# Backup commands
docker exec madeinoz-knowledge-neo4j neo4j-admin database dump neo4j --to-stdout > backup.dump

# Restore commands
docker run --rm -v madeinoz-knowledge-neo4j-data:/data -v $(pwd):/backup alpine \
    sh -c "cd /data && tar xvf /backup/volume-backup.tar"

# Verification
docker exec madeinoz-knowledge-neo4j cypher-shell -u neo4j -p password "MATCH (n) RETURN count(n)"
```

**FalkorDB Backend - Podman:**
```bash
# Backup commands
podman exec madeinoz-knowledge-falkordb redis-cli BGSAVE              # Trigger save
podman cp madeinoz-knowledge-falkordb:/data/dump.rdb ./backup.rdb     # Copy backup
podman volume export madeinoz-knowledge-data > volume-backup.tar       # Full volume

# Restore commands
podman volume import madeinoz-knowledge-data < volume-backup.tar       # Restore volume
podman cp ./backup.rdb madeinoz-knowledge-falkordb:/data/dump.rdb     # Restore RDB

# Verification
podman exec madeinoz-knowledge-falkordb redis-cli DBSIZE              # Check DB size
podman exec madeinoz-knowledge-falkordb redis-cli GRAPH.LIST          # List graphs
```

**FalkorDB Backend - Docker:**
```bash
# Backup commands
docker exec madeinoz-knowledge-falkordb redis-cli BGSAVE              # Trigger save
docker cp madeinoz-knowledge-falkordb:/data/dump.rdb ./backup.rdb     # Copy backup
docker run --rm -v madeinoz-knowledge-data:/data -v $(pwd):/backup alpine \
    tar cvf /backup/volume-backup.tar -C /data .                 # Full volume

# Restore commands
docker run --rm -v madeinoz-knowledge-data:/data -v $(pwd):/backup alpine \
    sh -c "cd /data && tar xvf /backup/volume-backup.tar"        # Restore volume
docker cp ./backup.rdb madeinoz-knowledge-falkordb:/data/dump.rdb     # Restore RDB

# Verification
docker exec madeinoz-knowledge-falkordb redis-cli DBSIZE              # Check DB size
docker exec madeinoz-knowledge-falkordb redis-cli GRAPH.LIST          # List graphs
```

## Related Documentation

- Return to [advanced usage](advanced.md) for other expert-level patterns
- Review [basic usage](basic-usage.md) for fundamental operations
- Learn more about [how the system works](../concepts/knowledge-graph.md)
- Troubleshoot issues in the [troubleshooting guide](../troubleshooting/common-issues.md)
