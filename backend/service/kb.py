from fastapi import APIRouter

from backend.core.ingest import IngestPipeline
from backend.models.api import IngestRequest, IngestResponse

router = APIRouter(prefix="/kb", tags=["knowledge-base"])


@router.post("/ingest", response_model=IngestResponse)
def ingest_knowledge(req: IngestRequest) -> IngestResponse:
    pipeline = IngestPipeline()
    results, errors = pipeline.ingest_items(req.items, retry_times=req.retry_times)
    return IngestResponse(
        total=len(req.items),
        success=len(results),
        failed=len(errors),
        results=results,
        errors=errors,
    )
