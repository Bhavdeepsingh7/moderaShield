from fastapi import APIRouter

from app.api.v1.endpoints import tenant

router = APIRouter()

router.include_router(
    tenant.router,
    prefix = "/tenants",
    tags = ["tenants"],
)

