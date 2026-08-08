from uuid import UUID

from sqlalchemy.orm import Session

from app.core.security import generate_api_key, hash_api_key
from app.models.api_key import ApiKey
from app.repositories.api_key_repository import api_key_repository
from app.repositories.tenant_repository import tenant_repository
from app.schemas.api_key import ApiKeyCreate

class ApiKeyService:

    def create_api_key(
            self,
            db:Session,
            tenant_id: UUID,
            data: ApiKeyCreate,
    ):

        tenant = tenant_repository.get_by_id(db, tenant_id)

        if not tenant:
            raise ValueError("Tenant not found")

        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)

        api_key = ApiKey(
            tenant_id = tenant_id,
            name = data.name,
            key_hash = key_hash,
        )

        saved_key = api_key_repository.create(db, api_key)

        return saved_key, raw_key


api_key_service = ApiKeyService()