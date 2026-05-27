from fastapi import FastAPI

from backend.app.routes.documents import router as documents_router
from backend.app.routes.evals import router as evals_router
from backend.app.routes.health import router as health_router
from backend.app.routes.query import router as query_router


def create_app() -> FastAPI:
    app = FastAPI(title="CiteMind API", version="0.1.0")
    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(query_router)
    app.include_router(evals_router)
    return app


app = create_app()
