from fastapi import APIRouter

from backend.core.health import health_check

router = APIRouter(prefix="", tags=["health"])


@router.get("/healthz")
def get_healthz() -> dict[str, str]:
    return health_check()
