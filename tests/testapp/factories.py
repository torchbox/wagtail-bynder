from wagtail_factories.factories import (
    CollectionMemberFactory,
    DocumentFactory,
    ImageFactory,
)

from .models import CustomDocument, CustomImage, Video


class CustomDocumentFactory(DocumentFactory):
    class Meta:
        model = CustomDocument


class CustomImageFactory(ImageFactory):
    class Meta:
        model = CustomImage


class VideoFactory(CollectionMemberFactory):
    title = "A video"

    class Meta:
        model = Video
