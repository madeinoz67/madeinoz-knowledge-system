"""
LKAP (Feature 022/023) Python Modules
Local Knowledge Augmentation Platform

This package extends the Graphiti MCP server with RAG capabilities:

Feature 023 (Qdrant Migration):
- qdrant_client: Qdrant vector database client with search, health check, collection management
- ollama_embedder: Ollama embedding service with bge-large-en-v1.5 (1024 dimensions)
- semantic_chunker: Semantic chunking with tiktoken (512-768 tokens, 10-20% overlap)
- docling_ingester: Document ingestion with Docling parser + semantic chunking

Feature 022 (Original LKAP):
- lkap_models: Entity models for Document Memory (RAG) and Knowledge Memory (Graph) tiers
- lkap_schema: Neo4j/FalkorDB schema definitions for Fact, Evidence, Conflict nodes
- promotion: Evidence-to-Knowledge Graph fact promotion with provenance tracking
- embedding_service: OpenRouter and Ollama embedding model support

Architecture: Qdrant-native with Docling for PDF parsing and Ollama for embeddings.
"""

__version__ = "0.2.0"
