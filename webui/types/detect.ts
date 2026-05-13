export type EvidenceItem = {
  record_id: string;
  source: string;
  summary: string;
  category: string;
  patterns: string[];
  risk_keywords: string[];
  score: number;
  retrieval_mode: string;
  matched_keywords: string[];
};

export type DetectionResult = {
  is_scam: boolean;
  confidence: number;
  reason: string;
  evidence_refs: string[];
};

export type DetectRequest = {
  text: string;
  keyword_top_k?: number;
  vector_top_k?: number;
  return_evidence: boolean;
};

export type DetectResponse = {
  keyword_hits: EvidenceItem[];
  vector_hits: EvidenceItem[];
  fused_hits: EvidenceItem[];
  detection: DetectionResult;
};
