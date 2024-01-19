from django.conf import settings
from django.db import models
from wagtail.images.models import AbstractRendition

from wagtail_bynder.models import BynderSyncedDocument, BynderSyncedImage, BynderSyncedVideo


class CustomDocument(BynderSyncedDocument):
    if settings.BYNDER_DOMAIN:
        # We do not currently need documents to be searchable, because any
        # user-facing search functionality is provided by Bynder.
        search_fields = []


class CustomImage(BynderSyncedImage):
    if settings.BYNDER_DOMAIN:
        # We do not currently need documents to be searchable, because any
        # user-facing search functionality is provided by Bynder.
        search_fields = []


class Rendition(AbstractRendition):
    image = models.ForeignKey(
        "CustomImage", related_name="renditions", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = (("image", "filter_spec", "focal_point_key"),)


class Video(BynderSyncedVideo):
    search_fields = []
