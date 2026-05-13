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
    results: list[IngestResult]
    errors: list[str]
