from django.utils.translation import gettext_lazy as _

from wagtail_bynder import get_video_model

from .base import BaseBynderRefreshCommand


class Command(BaseBynderRefreshCommand):
    help = _(
        "Update ALL Wagtail video library items to reflect the latest data from Bynder."
    )
    model = get_video_model()
