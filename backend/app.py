from fastapi import FastAPI

from backend.core.settings import settings
from backend.service.health import router as health_router
from backend.service.kb import router as kb_router


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.include_router(health_router)
    app.include_router(kb_router)
    return app


app = create_app()
