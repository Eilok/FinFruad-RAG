from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.settings import settings
from backend.service.detect import router as detect_router
from backend.service.health import router as health_router
from backend.service.kb import router as kb_router

def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.include_router(health_router)
    app.include_router(kb_router)
    app.include_router(detect_router)
    return app


app = create_app()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)