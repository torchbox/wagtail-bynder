from wagtail_bynder import get_video_model

from .base import BaseBynderSyncCommand


class Command(BaseBynderSyncCommand):
    model = get_video_model()
    bynder_asset_type: str = "video"
    page_size: int = 200
