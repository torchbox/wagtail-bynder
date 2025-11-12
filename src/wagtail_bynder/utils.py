import mimetypes
import os

from http import HTTPStatus
from io import BytesIO

import requests

from asgiref.local import Local
from bynder_sdk import BynderClient
from django.conf import settings
from django.core.files import File
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.template.defaultfilters import filesizeformat
from wagtail.models import Collection
from willow import Image

from .exceptions import BynderAssetDownloadError, BynderAssetFileTooLarge


_DEFAULT_COLLECTION = Local()


def download_file(
    url: str, max_filesize: int, max_filesize_setting_name: str
) -> InMemoryUploadedFile:
    name = os.path.basename(url)
    response = requests.get(url, timeout=20, stream=True)

    # Make sure we don't store error responses instead of the file requested
    if response.status_code != HTTPStatus.OK:
        raise BynderAssetDownloadError(
            f"Server error downloading '{name}' from Bynder. "
        )

    file = BytesIO()
    # Stream the file to memory. We use iter_content() instead of the default iterator for requests.Response,
    # as the latter uses iter_lines() which isn't suitable for streaming binary data.
    # Get data in largish 8KB chunks, for more performant streaming while staying within CPU cache limits
    for chunk in response.iter_content(chunk_size=8192):
        file.write(chunk)
        if file.tell() > max_filesize:
            file.truncate(0)
            raise BynderAssetFileTooLarge(
                f"File '{name}' exceeded the size limit enforced by the {max_filesize_setting_name} setting, which is currently set to {filesizeformat(max_filesize)}."
            )

    size = file.tell()
    # Catch empty case where iter_content wouldn't have iterated
    if size == 0:
        raise BynderAssetDownloadError(
            f"Downloaded file '{name}' from Bynder is empty."
        )
    file.seek(0)

    content_type, charset = mimetypes.guess_type(name)
    return InMemoryUploadedFile(
        file,
        field_name="file",
        name=name,
        content_type=content_type,
        size=size,
        charset=charset,
    )


def download_document(url: str) -> InMemoryUploadedFile:
    max_filesize_setting_name = "BYNDER_MAX_DOCUMENT_FILE_SIZE"
    max_filesize = getattr(settings, max_filesize_setting_name, 5242880)
    return download_file(url, max_filesize, max_filesize_setting_name)


def download_image(url: str) -> InMemoryUploadedFile:
    max_filesize_setting_name = "BYNDER_MAX_IMAGE_FILE_SIZE"
    max_filesize = getattr(settings, max_filesize_setting_name, 5242880)
    return download_file(url, max_filesize, max_filesize_setting_name)


def get_image_info(file: File) -> tuple[int, int, str, bool]:
    willow_image = Image.open(file)
    width, height = willow_image.get_size()
    return (width, height, willow_image.format_name, willow_image.has_animation())


def get_output_image_format(original_format: str, *, is_animated: bool = False) -> str:
    conversions = {
        "avif": "png",
        "bmp": "png",
        "webp": "png",
    }
    if is_animated:
        # Convert non-animated GIFs to PNG as well
        conversions["gif"] = "png"

    # Allow the user to override the conversions
    custom_conversions = getattr(settings, "WAGTAILIMAGES_FORMAT_CONVERSIONS", {})
    conversions.update(custom_conversions)

    return conversions.get(original_format, original_format)


def filename_from_url(url: str) -> str:
    return os.path.basename(url)


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
