from pydantic import BaseModel, Field


class IngestItem(BaseModel):
    text: str = Field(min_length=1)
    source: str = Field(default="manual")


class IngestRequest(BaseModel):
    items: list[IngestItem] = Field(min_length=1)
    retry_times: int | None = Field(default=None, ge=0, le=5)


class IngestResult(BaseModel):
    record_id: str
    source: str
    summary: str
    category: str
    risk_keywords: list[str]


class IngestResponse(BaseModel):
    total: int
    success: int
    failed: int
    skipped: int = 0
    results: list[IngestResult]
    errors: list[str]
    skipped_messages: list[str] = Field(default_factory=list)


class DetectRequest(BaseModel):
    text: str = Field(min_length=1)
    keyword_top_k: int | None = Field(default=None, ge=1, le=20)
    vector_top_k: int | None = Field(default=None, ge=1, le=20)
    return_evidence: bool = True


class EvidenceItem(BaseModel):
    record_id: str
    source: str
    summary: str
    category: str
    patterns: list[str]
    risk_keywords: list[str]
    score: float
    retrieval_mode: str
    matched_keywords: list[str] = Field(default_factory=list)


class DetectionResult(BaseModel):
    is_scam: bool
    confidence: float
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)


class DetectResponse(BaseModel):
    keyword_hits: list[EvidenceItem]
    vector_hits: list[EvidenceItem]
    fused_hits: list[EvidenceItem]
    detection: DetectionResult
