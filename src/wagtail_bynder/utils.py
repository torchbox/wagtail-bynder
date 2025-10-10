import mimetypes
import os
import re

from contextlib import suppress
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

from .exceptions import (
    BynderAssetDownloadError,
    BynderAssetFileTooLarge,
    BynderInvalidImageContentError,
)


_DEFAULT_COLLECTION = Local()


def download_file(
    url: str,
    max_filesize: int,
    max_filesize_setting_name: str,
    *,
    expect_image: bool = False,
) -> InMemoryUploadedFile:
    name = os.path.basename(url)

    try:
        response = requests.get(url, timeout=20, stream=True)
    except Exception as e:
        raise BynderAssetDownloadError(url, message=str(e)) from e

    if response.status_code != 200:
        # Consume (small) text body for context if available
        message = ""
        with suppress(Exception):
            # Only read a small slice to avoid memory blow-up
            message = response.text[:500]
        raise BynderAssetDownloadError(
            url, status_code=response.status_code, message=message
        )

    # Stream body to memory enforcing size limit
    file = BytesIO()
    for chunk in response.iter_content(chunk_size=8192):
        if not chunk:
            continue
        file.write(chunk)
        if file.tell() > max_filesize:
            file.truncate(0)
            raise BynderAssetFileTooLarge(
                f"File '{name}' exceeded the size limit enforced by the {max_filesize_setting_name} setting, which is currently set to {filesizeformat(max_filesize)}."
            )

    size = file.tell()
    file.seek(0)

    # If we expected an image but got probable HTML / JSON error page, detect early
    if expect_image:
        sample = file.read(4096)
        file.seek(0)
        # Heuristics: starts with <!DOCTYPE html or <html or JSON body or contains typical gateway phrases
        lowered = sample.lower()
        if (
            lowered.startswith((b"<!doctype html", b"<html", b"<?xml"))
            or b"<title>502" in lowered
            or b"bad gateway" in lowered
            or re.search(rb"<h1>.*(error|gateway).*</h1>", lowered)
        ):
            raise BynderInvalidImageContentError(
                url, "received HTML error page instead of image bytes"
            )

    content_type = response.headers.get("Content-Type")
    if not content_type:
        guessed, charset = mimetypes.guess_type(name)
        content_type = guessed
    else:
        # Strip charset etc
        if ";" in content_type:
            content_type = content_type.split(";")[0].strip()
        charset = None

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
    return download_file(
        url, max_filesize, max_filesize_setting_name, expect_image=True
    )


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
