# Madeinoz Knowledge System - Custom Docker Image
# Builds on zepai/knowledge-graph-mcp:standalone with our patches applied
# Supports both Neo4j and FalkorDB backends

FROM zepai/knowledge-graph-mcp:standalone

LABEL description="Madeinoz Knowledge System - Graphiti MCP with Ollama/OpenRouter support, Neo4j + FalkorDB"
LABEL version="1.0.1"

# Copy patches from src/server directory
COPY src/server/patches/factories.patch /tmp/
COPY src/server/patches/graphiti_mcp_server.patch /tmp/
RUN cat /tmp/factories.patch > /app/mcp/src/services/factories.py && \
    cat /tmp/graphiti_mcp_server.patch > /app/mcp/src/graphiti_mcp_server.py && \
    rm /tmp/*.patch

# Copy both Neo4j and FalkorDB configs
COPY src/server/config-neo4j.yaml /tmp/config-neo4j.yaml
COPY src/server/config-falkordb.yaml /tmp/config-falkordb.yaml

# Copy and configure entrypoint script for prefix mapping and config selection
COPY src/server/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Set default environment variables (can be overridden at runtime)
ENV GRAPHITI_GROUP_ID=main \
    SEMAPHORE_LIMIT=10 \
    GRAPHITI_TELEMETRY_ENABLED=false \
    SEARCH_ALL_GROUPS=true \
    DATABASE_TYPE=neo4j

# Expose ports
EXPOSE 8000

# Set entrypoint to handle MADEINOZ_KNOWLEDGE_* prefix mapping and config selection
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -sf --max-time 5 http://localhost:8000/health || exit 1

# Run the server (passed as args to entrypoint.sh)
CMD ["uv", "run", "main.py"]
