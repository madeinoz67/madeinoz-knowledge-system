# Madeinoz Knowledge System - Custom Docker Image
# Builds on zepai/knowledge-graph-mcp:standalone with our patches applied
# Supports both Neo4j and FalkorDB backends

FROM zepai/knowledge-graph-mcp:standalone

LABEL description="Madeinoz Knowledge System - Graphiti MCP with Ollama/OpenRouter support, Neo4j + FalkorDB, Lucene sanitization, Prompt Caching, Memory Decay Scoring"
LABEL version="1.8.1"

# Apply patches by replacing original files
# factories.py - Adds Ollama/OpenRouter support (fixes GitHub #1116)
COPY docker/patches/factories.py /app/mcp/src/services/factories.py

# graphiti_mcp_server.py - Enables search across all groups
COPY docker/patches/graphiti_mcp_server.py /app/mcp/src/graphiti_mcp_server.py

# falkordb_lucene.py - Lucene query sanitization (new file, not a replacement)
COPY docker/patches/falkordb_lucene.py /app/mcp/src/utils/falkordb_lucene.py

# Install prompt caching dependencies (OpenTelemetry + Prometheus)
# Add to uv project dependencies
WORKDIR /app/mcp
RUN uv add "opentelemetry-api>=1.20.0" "opentelemetry-sdk>=1.20.0" "opentelemetry-exporter-prometheus>=0.41b0" "prometheus-client>=0.17.0" "pyyaml>=6.0" "pydantic>=2.0"

# Prompt caching implementation (Feature 006)
COPY docker/patches/cache_metrics.py /app/mcp/src/utils/cache_metrics.py
COPY docker/patches/session_metrics.py /app/mcp/src/utils/session_metrics.py
COPY docker/patches/message_formatter.py /app/mcp/src/utils/message_formatter.py
COPY docker/patches/caching_wrapper.py /app/mcp/src/utils/caching_wrapper.py
COPY docker/patches/caching_llm_client.py /app/mcp/src/utils/caching_llm_client.py
# Cache bust: 2026-01-29-13-30
COPY docker/patches/metrics_exporter.py /app/mcp/src/utils/metrics_exporter.py
COPY docker/patches/diagnostic_wrapper.py /app/mcp/src/utils/diagnostic_wrapper.py

# Memory decay scoring implementation (Feature 009)
# Adds importance/stability classification, lifecycle management, and maintenance service
COPY docker/patches/decay_config.py /app/mcp/src/utils/decay_config.py
COPY docker/patches/decay_migration.py /app/mcp/src/utils/decay_migration.py
COPY docker/patches/decay_types.py /app/mcp/src/utils/decay_types.py
COPY docker/patches/importance_classifier.py /app/mcp/src/utils/importance_classifier.py
COPY docker/patches/lifecycle_manager.py /app/mcp/src/utils/lifecycle_manager.py
COPY docker/patches/maintenance_service.py /app/mcp/src/utils/maintenance_service.py
COPY docker/patches/memory_decay.py /app/mcp/src/utils/memory_decay.py
# Cache bust: 2026-01-29-13-30
COPY docker/patches/metrics_exporter.py /app/mcp/src/utils/metrics_exporter.py

# Copy both Neo4j and FalkorDB configs
COPY src/skills/server/config-neo4j.yaml /tmp/config-neo4j.yaml
COPY src/skills/server/config-falkordb.yaml /tmp/config-falkordb.yaml

# Copy Feature 009 memory decay configuration
COPY config/decay-config.yaml /tmp/decay-config.yaml

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
EXPOSE 8000 9090

# Set entrypoint to select appropriate config based on DATABASE_TYPE
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -sf --max-time 5 http://localhost:8000/health || exit 1

# Run the server (passed as args to entrypoint.sh)
CMD ["uv", "run", "main.py"]
