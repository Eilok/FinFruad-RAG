from fastapi import APIRouter, HTTPException

from backend.core.detect import DetectPipeline
from backend.models.api import DetectRequest, DetectResponse

router = APIRouter(prefix="", tags=["detection"])


@router.post("/detect", response_model=DetectResponse)
def detect_risk(req: DetectRequest) -> DetectResponse:
    pipeline = DetectPipeline()
    try:
        return pipeline.run(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Detection pipeline failed: {exc}") from exc
