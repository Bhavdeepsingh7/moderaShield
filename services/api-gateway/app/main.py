from fastapi import FastAPI
from app.core.config import settings

from app.api.v1.router import router as api_router

app = FastAPI(
    title=settings.APP_NAME,
    description="API Gateway for ModeraShield",
    version=settings.APP_VERSION,
)


@app.get("/")
async def root():
    return {
        "service": settings.APP_NAME,
        "status": "healthy",
        "version": settings.APP_VERSION,
    }


@app.get("/health")
async def health():
    return {
        "status": "ok"
    }

app.include_router(
    api_router,
    prefix = "/api/v1",
)