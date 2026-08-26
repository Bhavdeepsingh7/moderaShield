from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

from app.core.config import settings


from app.api.v1.router import router as api_router
from app.messaging.kafka import start_kafka, stop_kafka

@asynccontextmanager
async def lifespan(app: FastAPI):

    await start_kafka()

    yield

    await stop_kafka()


app = FastAPI(
    title=settings.APP_NAME,
    description="API Gateway for ModeraShield",
    version=settings.APP_VERSION,
    lifespan = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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