from django.utils.translation import gettext_lazy as _
from wagtail.images import get_image_model

from .base import BaseBynderRefreshCommand


class Command(BaseBynderRefreshCommand):
    help = _(
        "Update ALL Wagtail image library items to reflect the latest data from Bynder."
    )
    model = get_image_model()
