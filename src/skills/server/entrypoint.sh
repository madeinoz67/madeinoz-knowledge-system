#!/bin/sh
# Entrypoint script for Madeinoz Knowledge System
# Selects appropriate config based on DATABASE_TYPE (neo4j or falkordb)
# Environment variables are provided by docker compose via env_file

set -e

# Debug: Log that entrypoint is running
echo "ENTRYPOINT: Running Madeinoz Knowledge System entrypoint..." >&2

# ============================================================================
# Select Configuration Based on Database Type
# ============================================================================

# Determine database type from environment (default: neo4j)
DATABASE_TYPE="${DATABASE_TYPE:-neo4j}"

echo "ENTRYPOINT: DATABASE_TYPE=${DATABASE_TYPE}" >&2

# Select and copy appropriate config file
case "$DATABASE_TYPE" in
  falkordb|redis)
    echo "ENTRYPOINT: Using FalkorDB configuration" >&2
    cp /tmp/config-falkordb.yaml /app/mcp/config/config.yaml
    ;;
  neo4j|*)
    echo "ENTRYPOINT: Using Neo4j configuration (default)" >&2
    cp /tmp/config-neo4j.yaml /app/mcp/config/config.yaml
    ;;
esac

# Debug: Log key configuration
echo "ENTRYPOINT: LLM_PROVIDER=${LLM_PROVIDER:-unset}, MODEL_NAME=${MODEL_NAME:-unset}" >&2
echo "ENTRYPOINT: EMBEDDER_PROVIDER=${EMBEDDER_PROVIDER:-unset}, GRAPHITI_GROUP_ID=${GRAPHITI_GROUP_ID:-unset}" >&2

# Execute the main container command
exec "$@"
