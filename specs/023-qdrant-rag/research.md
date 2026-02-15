# Research: Qdrant RAG Migration

**Feature**: 023-qdrant-rag
**Date**: 2026-02-13

## Research Summary

This document captures the research decisions for replacing RAGFlow with Qdrant as the vector database for LKAP.

---

## Decision 1: Vector Database Selection

**Decision**: Qdrant

**Rationale**:
- Docker image only 69MB vs RAGFlow's 3.5GB+ (97% reduction)
- 626 QPS performance benchmark
- Official MCP server available (`qdrant/mcp-server-qdrant`)
- Native Python SDK with async support
- Built-in payload filtering for metadata queries
- Persistent storage with snapshot/restore

**Alternatives Considered**:
| Database | Size | QPS | MCP Support | Reason Rejected |
|----------|------|-----|-------------|-----------------|
| RAGFlow | 3.5GB | ~200 | No | Too resource-heavy, requires Elasticsearch |
| LanceDB | 150MB | 450 | No | Less mature, no built-in filtering |
| ChromaDB | 200MB | 300 | Community | Higher memory, slower than Qdrant |
| sqlite-vec | 50MB | 150 | No | No async, limited scale |

---

## Decision 2: Document Parsing

**Decision**: Docling

**Rationale**:
- 97.9% table extraction accuracy (highest in benchmarks)
- Native PDF structure preservation
- Markdown with heading hierarchy
- Built-in OCR fallback for scanned documents
- Python-native, no external dependencies

**Alternatives Considered**:
| Parser | Table Accuracy | OCR | Reason Rejected |
|--------|---------------|-----|-----------------|
| PyMuPDF | 92% | No | Lower accuracy, no structure |
| pdfplumber | 88% | No | Poor table handling |
| unstructured | 90% | Yes | Heavy dependency chain |

---

## Decision 3: Chunking Strategy

**Decision**: Semantic Chunking with 512-768 tokens, 10-20% overlap

**Rationale**:
- +9% retrieval improvement over fixed-size chunking
- Preserves semantic coherence within chunks
- Overlap prevents context loss at boundaries
- Token range matches embedding model context window
- Heading-aware splitting preserves document structure

**Implementation**:
1. Use LangChain's SemanticChunker with percentile breakpoint
2. Fallback to RecursiveCharacterTextSplitter for edge cases
3. Preserve heading metadata for each chunk
4. Track page numbers and character positions

---

## Decision 4: Embedding Model

**Decision**: Ollama with bge-large-en-v1.5

**Rationale**:
- 1024 dimensions (good balance of quality vs storage)
- Fully offline operation (no API keys)
- Fast inference on CPU (no GPU required)
- Strong performance on MTEB benchmarks
- Apache 2.0 license (no restrictions)

**Alternatives Considered**:
| Model | Dimensions | Offline | MTEB Score | Reason Rejected |
|-------|------------|---------|------------|-----------------|
| text-embedding-3-large | 3072 | No | 70.9 | Requires API, larger storage |
| text-embedding-3-small | 1536 | No | 66.9 | Requires API |
| nomic-embed-text | 768 | Yes | 64.9 | Lower dimension, less detail |
| mxbai-embed-large | 1024 | Yes | 66.3 | Slightly lower quality |

---

## Decision 5: MCP Tool Design

**Decision**: Three tools (rag.search, rag.getChunk, rag.ingest)

**Rationale**:
- Minimal API surface matching user stories
- Search returns SearchResult[] with confidence scores
- getChunk returns full chunk with metadata
- ingest handles file path to chunk storage pipeline
- Health check available via rag.health

**Tool Contracts**:
```
rag.search(query: str, filters?: dict, top_k?: int) -> SearchResult[]
rag.getChunk(chunk_id: str) -> Chunk
rag.ingest(file_path: str, metadata?: dict) -> IngestionResult
rag.health() -> HealthStatus
```

---

## Decision 6: CLI Design

**Decision**: TypeScript CLI wrapper using Bun

**Rationale**:
- Consistent with existing project CLI tools
- Bun provides fast startup and native TypeScript
- HTTP client to Qdrant REST API
- MCP client for tool invocation

**Commands**:
```bash
bun run rag-cli.ts search "<query>" [--filter key=value]
bun run rag-cli.ts get-chunk <chunk-id>
bun run rag-cli.ts ingest <file-path>
bun run rag-cli.ts health
```

---

## Decision 7: Ingestion Workflow

**Decision**: Batch processing with idempotency

**Rationale**:
- Document hash determines if re-ingestion needed
- Atomic batch operations for efficiency
- Error handling per-document (continue on failure)
- Move to processed/ only on success

**Flow**:
1. Watch knowledge/inbox/ (or manual trigger)
2. Calculate document hash
3. Check if hash exists in Qdrant
4. Parse with Docling
5. Chunk with SemanticChunker
6. Generate embeddings with Ollama
7. Store in Qdrant with payload
8. Move document to knowledge/processed/

---

## Technical Constraints

| Constraint | Value | Source |
|------------|-------|--------|
| Embedding dimension | 1024 | bge-large-en-v1.5 |
| Chunk min tokens | 512 | Semantic coherence |
| Chunk max tokens | 768 | Context window |
| Chunk overlap | 10-20% | Boundary preservation |
| Search latency | <500ms | User experience |
| Memory limit | 200MB | RAGFlow comparison |
| Max chunks | 100,000+ | Scale requirement |

---

## References

- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Docling GitHub](https://github.com/DS4SD/docling)
- [BGE Embeddings](https://huggingface.co/BAAI/bge-large-en-v1.5)
- [Semantic Chunking Paper](https://arxiv.org/abs/2307.02048)
