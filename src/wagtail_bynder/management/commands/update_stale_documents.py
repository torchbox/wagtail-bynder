from wagtail.documents import get_document_model

from .base import BaseBynderSyncCommand


class Command(BaseBynderSyncCommand):
    model = get_document_model()
    bynder_asset_type: str = "document"
    page_size: int = 200
