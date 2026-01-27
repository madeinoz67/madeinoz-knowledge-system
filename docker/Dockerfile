# Madeinoz Knowledge System - Custom Docker Image
# Builds on zepai/knowledge-graph-mcp:standalone with our patches applied
# Supports both Neo4j and FalkorDB backends

FROM zepai/knowledge-graph-mcp:standalone

LABEL description="Madeinoz Knowledge System - Graphiti MCP with Ollama/OpenRouter support, Neo4j + FalkorDB, Lucene sanitization"
LABEL version="1.1.0"

# Apply patches by replacing original files
# factories.py - Adds Ollama/OpenRouter support (fixes GitHub #1116)
COPY docker/patches/factories.py /app/mcp/src/services/factories.py

# graphiti_mcp_server.py - Enables search across all groups
COPY docker/patches/graphiti_mcp_server.py /app/mcp/src/graphiti_mcp_server.py

# falkordb_lucene.py - Lucene query sanitization (new file, not a replacement)
COPY docker/patches/falkordb_lucene.py /app/mcp/src/utils/falkordb_lucene.py

# Install prompt caching dependencies (OpenTelemetry + Prometheus)
COPY docker/patches/requirements-cache.txt /tmp/requirements-cache.txt
RUN pip install --no-cache-dir -r /tmp/requirements-cache.txt && rm /tmp/requirements-cache.txt

# Copy both Neo4j and FalkorDB configs
COPY src/skills/server/config-neo4j.yaml /tmp/config-neo4j.yaml
COPY src/skills/server/config-falkordb.yaml /tmp/config-falkordb.yaml

# Copy and configure entrypoint script for config selection
# Note: Environment variables are provided by docker compose via env_file
# The entrypoint only selects the appropriate config file (neo4j/falkordb)
COPY src/skills/server/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Set default environment variables (can be overridden at runtime)
ENV GRAPHITI_GROUP_ID=main \
    SEMAPHORE_LIMIT=10 \
    GRAPHITI_TELEMETRY_ENABLED=false \
    GRAPHITI_SEARCH_ALL_GROUPS=true \
    DATABASE_TYPE=neo4j

# Expose ports
EXPOSE 8000

# Set entrypoint to select appropriate config based on DATABASE_TYPE
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -sf --max-time 5 http://localhost:8000/health || exit 1

# Run the server (passed as args to entrypoint.sh)
CMD ["uv", "run", "main.py"]
