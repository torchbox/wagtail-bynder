import mimetypes
import os
from io import BytesIO

import requests
from asgiref.local import Local
from bynder_sdk import BynderClient
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from wagtail.models import Collection

_DEFAULT_COLLECTION = Local()


class DownloadedFile(BytesIO):
    name: str
    content_type: str
    charset: str
    size: int


def download_file(url: str) -> DownloadedFile:
    raw_bytes = requests.get(url).content
    f = DownloadedFile(raw_bytes)
    f.name = os.path.basename(url)
    f.size = len(raw_bytes)
    f.content_type, f.charset = mimetypes.guess_type(f.name)
    return f


def download_document(url: str) -> InMemoryUploadedFile:
    f = download_file(url)
    uploadedfile = InMemoryUploadedFile(
        f,
        name=f.name,
        field_name="file",
        size=f.size,
        charset=f.charset,
        content_type=f.content_type,
    )
    return uploadedfile


def download_image(url: str) -> InMemoryUploadedFile:
    f = download_file(url)
    uploadedfile = InMemoryUploadedFile(
        f,
        name=f.name,
        field_name="file",
        size=f.size,
        charset=f.charset,
        content_type=f.content_type,
    )
    return uploadedfile


def get_bynder_client() -> BynderClient:
    return BynderClient(
        domain=getattr(settings, "BYNDER_DOMAIN", ""),
        permanent_token=getattr(settings, "BYNDER_API_TOKEN", ""),
    )


def get_default_collection() -> Collection:
    """
    Return a Collection object that should be used as the default for images and
    documents created to represent Bynder assets.

    The result is cached for the current thread / asyncio task.
    """
    try:
        return _DEFAULT_COLLECTION.value
    except AttributeError:
        pass

    name = "Imported from Bynder"
    try:
        # Use existing collection
        collection = Collection.objects.get(name=name)
    except Collection.DoesNotExist:
        # Create a new one
        collection = Collection.get_first_root_node().add_child(name=name)

    # Cache result for the current thread / asyncio task
    _DEFAULT_COLLECTION.value = collection
    return collection
