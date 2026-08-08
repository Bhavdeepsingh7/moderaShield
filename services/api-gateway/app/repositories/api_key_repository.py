from sqlalchemy.orm import Session

from app.models.api_key import ApiKey

class ApiKeyRespository:

    def create(
            self, 
            db:Session ,
            api_key: ApiKey
    ) -> ApiKey:

        db.add(api_key)
        db.commit()
        db.refresh(api_key)
        return api_key

    def get_by_hash(
            self,
            db:Session,
            key_hash: str,
    ) -> ApiKey | None:
        return (
            db.query(ApiKey)
            .filter(ApiKey.key_hash == key_hash)
            .first()
        )


api_key_repository = ApiKeyRespository()