from django.utils.translation import gettext_lazy as _

from wagtail_bynder import get_video_model

from .base import BaseBynderSyncCommand


class Command(BaseBynderSyncCommand):
    help = _(
        "Update stale Wagtail video library items to reflect recent asset updates in Bynder."
    )
    model = get_video_model()
    bynder_asset_type: str = "video"
    page_size: int = 200
