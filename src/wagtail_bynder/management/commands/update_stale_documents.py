from django.utils.translation import gettext_lazy as _
from wagtail.documents import get_document_model

from .base import BaseBynderSyncCommand


class Command(BaseBynderSyncCommand):
    help = _(
        "Update stale Wagtail document library items to reflect recent asset updates in Bynder."
    )
    model = get_document_model()
    bynder_asset_type: str = "document"
    page_size: int = 200
