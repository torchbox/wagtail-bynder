import mimetypes
import os

from tempfile import NamedTemporaryFile

import requests

from asgiref.local import Local
from bynder_sdk import BynderClient
from django.conf import settings
from django.core.files.uploadedfile import TemporaryUploadedFile
from wagtail.models import Collection


_DEFAULT_COLLECTION = Local()


def download_file(url: str) -> TemporaryUploadedFile:
    basename = os.path.basename(url)
    name, ext = os.path.splitext(basename)
    content_type, charset = mimetypes.guess_type(name)

    # Download file contents to the server. 'delete=False' is used to prevent deletion
    # during all of the reopening and closing that happens as part of setting a file field
    # value and saving the changes.

    # NOTE: SpooledTemporaryFile could be more performant for smaller files, but doesn't
    # support the 'delete=False' option
    with NamedTemporaryFile(
        mode="w+b",
        suffix=f"download{ext}",
        dir=settings.FILE_UPLOAD_TEMP_DIR,
        delete=False,
    ) as tmp:
        for chunk in requests.get(
            url,
            stream=True,
            timeout=getattr(settings, "BYNDER_ASSET_DOWNLOAD_TIMEOUT", 20),
        ).iter_content(
            chunk_size=getattr(settings, "BYNDER_ASSET_DOWNLOAD_CHUNK_SIZE", 512)
        ):
            # Stream to filesystem in chunks to avoid memory spikes
            tmp.write(chunk)
            # Before closing, use the file pointer position to tell us the file size
            file_size = tmp.tell()

    # We want to treat the download as a 'user-uploaded file', so wrap the system file
    # in one of Django's built-in 'file upload' classes. `TemporaryUploadedFile` uses a
    # a `NamedTemporaryFile` instance natively underneath, so is a good fit for our needs
    f = TemporaryUploadedFile(basename, content_type, file_size, charset)

    # TemporaryUploadedFile defines it's own (empty) inner file, but we already have one
    # to hand (with 'delete=False' applied!), so let's delete and replace that.
    try:
        # Trash unused file
        os.unlink(f.file.name)
    except FileNotFoundError:
        pass
    else:
        # Replace with downloaded one
        f.file = tmp

    return f


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
