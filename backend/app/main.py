from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.db.database import init_db
from backend.app.routes.documents import router as documents_router
from backend.app.routes.evals import router as evals_router
from backend.app.routes.health import router as health_router
from backend.app.routes.medical import router as medical_router
from backend.app.routes.query import router as query_router


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="CiteMind API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
            "https://citemind-six.vercel.app",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(query_router)
    app.include_router(evals_router)
    app.include_router(medical_router)

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "name": "CiteMind API",
            "status": "ok",
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()
