/**
 * RAG-specific TypeScript types for LKAP (Feature 022)
 * Local Knowledge Augmentation Platform
 */

// Domain classification values
export type Domain = "embedded" | "software" | "security" | "cloud" | "standards";

// Document type classification values
export type DocumentType = "pdf" | "markdown" | "text" | "html";

// Sensitivity levels
export type Sensitivity = "public" | "internal" | "confidential" | "restricted";

// Confidence bands for classification
export type ConfidenceBand = "high" | "medium" | "low";

// Fact types for Knowledge Graph promotion
export type FactType =
  | "Constraint"
  | "Erratum"
  | "Workaround"
  | "API"
  | "BuildFlag"
  | "ProtocolRule"
  | "Detection"
  | "Indicator";

// Conflict resolution strategies
export type ResolutionStrategy =
  | "detect_only"
  | "keep_both"
  | "prefer_newest"
  | "reject_incoming";

// Ingestion status
export type IngestionStatus =
  | "pending"
  | "processing"
  | "completed"
  | "failed"
  | "review_required";

// Document metadata
export interface DocumentMetadata {
  domain?: Domain;
  type?: DocumentType;
  vendor?: string;
  component?: string;
  version?: string;
  projects?: string[];
  sensitivity?: Sensitivity;
}

// Search result filters
export interface SearchFilters {
  domain?: Domain;
  type?: DocumentType;
  component?: string;
  project?: string;
  version?: string;
}

// Search result from RAGFlow
export interface SearchResult {
  chunk_id: string;
  text: string;
  source_document: string;
  page_section: string;
  confidence: number;
  metadata: DocumentMetadata & {
    provenance?: ProvenanceReference[];
  };
}

// Provenance reference (chunk used as evidence)
export interface ProvenanceReference {
  fact_id: string;
  fact_type: FactType;
}

// Document chunk
export interface Chunk {
  chunk_id: string;
  text: string;
  document: {
    doc_id: string;
    filename: string;
    path: string;
    upload_date: string;
  };
  position: number;
  token_count: number;
  page_section?: string;
  metadata: DocumentMetadata;
}

// Fact in Knowledge Graph
export interface Fact {
  fact_id: string;
  type: FactType;
  entity: string;
  value: string;
  scope?: string;
  version?: string;
  valid_until?: string;
  conflict_id?: string;
  evidence_ids: string[];
  created_at: string;
  deprecated_at?: string;
  deprecated_by?: string;
}

// Conflict record
export interface Conflict {
  conflict_id: string;
  facts: Fact[];
  detection_date: string;
  resolution_strategy: ResolutionStrategy;
  status: "open" | "resolved" | "deferred";
  resolved_at?: string;
  resolved_by?: string;
}

// Ingestion state
export interface IngestionState {
  doc_id: string;
  status: IngestionStatus;
  confidence_band?: ConfidenceBand;
  chunks_processed: number;
  chunks_total?: number;
  error_message?: string;
  last_update: string;
}

// Classification result
export interface Classification {
  classification_id: string;
  doc_id: string;
  field_name: string;
  value: string;
  confidence: number;
  signal_sources: string[];
  user_override: boolean;
  created_at: string;
}

// Evidence (chunk → fact link)
export interface Evidence {
  evidence_id: string;
  chunk_id: string;
  fact_ids: string[];
  confidence: number;
  created_at: string;
}

// Promote from evidence request
export interface PromoteFromEvidenceRequest {
  evidence_id: string;
  fact_type: FactType;
  value: string;
  scope?: string;
  version?: string;
}

// Promote from query request
export interface PromoteFromQueryRequest {
  query: string;
  fact_type: FactType;
  top_k?: number;
}

// Review conflicts request
export interface ReviewConflictsRequest {
  entity?: string;
  fact_type?: FactType;
  status?: "open" | "resolved" | "deferred";
  limit?: number;
}

// Provenance graph result
export interface ProvenanceGraph {
  fact: Fact;
  evidence_chain: EvidenceChain[];
  documents: DocumentReference[];
}

export interface EvidenceChain {
  evidence_id: string;
  chunk_id: string;
  chunk_text: string;
  confidence: number;
}

export interface DocumentReference {
  doc_id: string;
  filename: string;
  path: string;
  page_section: string;
}
