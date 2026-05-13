from pydantic import BaseModel, Field


class ScamAnalysis(BaseModel):
    summary: str = Field(default="")
    category: str = Field(default="未知")
    patterns: list[str] = Field(default_factory=list)
    risk_keywords: list[str] = Field(default_factory=list)


class KnowledgeRecord(BaseModel):
    record_id: str
    source: str
    original_text: str
    analysis: ScamAnalysis
    created_at: str
