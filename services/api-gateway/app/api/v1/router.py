from fastapi import APIRouter

from app.api.v1.endpoints import tenant, api_key

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