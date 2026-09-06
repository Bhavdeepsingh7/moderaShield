from typing import BinaryIO
from sqlalchemy.orm import Session

from app.models.moderation_asset import ModerationAsset
from app.models.moderation import ModerationRequest
from app.services.storage.registry import get_storage_service

class AssetResolver:

    def open_asset(
            self,
            db: Session,
            request: ModerationRequest,
    ) -> BinaryIO:
        if request.asset_id is None:
            raise ValueError("Media moderationrequest has no asset")


        asset = db.get(ModerationAsset, request.asset_id)

        if asset is None: 
            raise FileNotFoundError(f"Asset not found: {request.asset_id}")

        if asset.tenant_id != request.tenant_id:
            raise PermissionError("Asset does not belong to the request tenant")

        storage = get_storage_service(asset.storage_provider)

        return storage.open(asset.object_key)