from sqlalchemy.orm import Session 

from app.models.tenant import Tenant

class TenantRepository:

    def create(
            self,
            db: Session,
            tenant: Tenant,
    ) -> Tenant:
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

        return tenant

    def get_by_id(
            self,
            db:Session,
            tenant_id,
    ):
        return (
            db.query(Tenant)
            .filter(Tenant.id == tenant_id)
            .first()
        )

    def get_by_slug(
            self,
            db:Session ,
            slug:str,
    ):
        return (
            db.query(Tenant)
            .filter(Tenant.slug == slug)
            .first()
        )

    def list(
            self,
            db:Session,
    ):
        return db.query(Tenant).all()


tenant_repository = TenantRepository()