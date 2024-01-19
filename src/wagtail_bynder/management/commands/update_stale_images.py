from typing import Any

from wagtail.images import get_image_model
from wagtail.images.models import AbstractImage

from .base import BaseBynderSyncCommand


class Command(BaseBynderSyncCommand):
    model = get_image_model()
    bynder_asset_type: str = "image"
    page_size: int = 200

    def update_object(self, obj: AbstractImage, asset_data: dict[str, Any]) -> None:
        """
        Overrides `BaseBynderSyncCommand.update_object()` to fetch the
        complete asset details before handing off to `obj.update_from_asset_data()`.
        (the API endpoint used by get_assets() does not include focal point data).
        """
        full_asset_data = self.bynder_client.asset_bank_client.media_info(
            asset_data["id"]
        )
        super().update_object(obj, full_asset_data)
