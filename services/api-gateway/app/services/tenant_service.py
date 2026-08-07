from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.repositories.tenant_repository import tenant_repository    
from app.schemas.tenant import TenantCreate

class TenantService:

    def create(
            self,
            db:Session,
            data: TenantCreate,
    ):
        existing = tenant_repository.get_by_slug(
            db,
            data.slug,
        )

        if existing:
            raise ValueError("Slug already exists")

        tenant = Tenant(
            name = data.name,
            slug =  data.slug,
        )

        return tenant_repository.create(
            db, 
            tenant,
        )

tenant_service = TenantService()