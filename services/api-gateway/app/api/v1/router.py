from fastapi import APIRouter

from app.api.v1.endpoints import api_key, metrics, moderation, tenant

router = APIRouter()

router.include_router(
    tenant.router,
    prefix = "/tenants",
    tags = ["tenants"],
)

router.include_router(
    api_key.router,
    prefix = "/tenants/{tenant_id}/api-keys",
    tags = ["api-keys"],
)

router.include_router(
    moderation.router,
    prefix="/moderate",
    tags=["Moderation"]
)

router.include_router(
    metrics.router,
    prefix="/metrics",
    tags=["Metrics"],
)
