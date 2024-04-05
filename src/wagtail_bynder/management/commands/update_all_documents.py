from django.utils.translation import gettext_lazy as _
from wagtail.documents import get_document_model

from .base import BaseBynderRefreshCommand


class Command(BaseBynderRefreshCommand):
    help = _(
        "Update ALL Wagtail document library items to reflect the latest data from Bynder."
    )
    model = get_document_model()
