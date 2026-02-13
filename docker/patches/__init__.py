"""
LKAP (Feature 022) Python Modules
Local Knowledge Augmentation Platform

This package extends the Graphiti MCP server with RAG capabilities:
- ragflow_client: RAGFlow HTTP REST API client wrapper (search operations only)
- lkap_models: Entity models for Document Memory (RAG) and Knowledge Memory (Graph) tiers
- lkap_schema: Neo4j/FalkorDB schema definitions for Fact, Evidence, Conflict nodes
- promotion: Evidence-to-Knowledge Graph fact promotion with provenance tracking
- embedding_service: OpenRouter and Ollama embedding model support

NOTE: RAGFlow-native architecture - documents managed via RAGFlow UI at http://localhost:9380
The system no longer includes custom ingestion code (docling_ingester, chunking_service, classification).
"""

__version__ = "0.1.0"
