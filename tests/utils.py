import io
import os

from datetime import datetime
from enum import StrEnum
from random import choice
from string import ascii_uppercase

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.text import slugify
from PIL import Image


TEST_ASSET_ID = "1A7BA172-97B9-44A4-8C0AA41D9E8AE6A2"


class ImageFormat(StrEnum):
    JPEG = "JPEG"
    GIF = "GIF"
    PNG = "PNG"
    BMP = "BMP"
    WEBP = "WebP"
    TIFF = "TIFF"


IMAGE_EXTENSION_TO_FORMAT = {
    ".jpg": (ImageFormat.JPEG, "image/jpeg"),
    ".jpeg": (ImageFormat.JPEG, "image/jpeg"),
    ".gif": (ImageFormat.GIF, "image/gif"),
    ".png": (ImageFormat.PNG, "image/png"),
    ".webp": (ImageFormat.WEBP, "image/webp"),
    ".bmp": (ImageFormat.BMP, "image/bmp"),
    ".tif": (ImageFormat.TIFF, "image/tiff"),
    ".tiff": (ImageFormat.TIFF, "image/tiff"),
}

DOCUMENT_EXTENSION_TO_FORMAT = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".xml": "text/xml",
}


def get_test_asset_data(
    id: str = TEST_ASSET_ID,
    name: str = "Test asset",
    type: str = "image",
    description: str = "",
    copyright: str = "",
    date_modified: datetime | None = None,
):
    from django.conf import settings

    id_hash = "3477c04a50a14650"

    if date_modified:
        date_modified_str = date_modified.isoformat()
    else:
        date_modified_str = "2023-10-10T09:52:05Z"

    name_slugified = slugify(name)

    if type == "document":
        extension = "pdf"
        filename = name_slugified + ".pdf"
    elif type == "video":
        extension = "mpg"
        filename = name_slugified + ".mpg"
    else:
        extension = "tif"
        filename = name_slugified + ".tif"

    thumb_base = f"https://{settings.BYNDER_DOMAIN}/m/{id_hash}"

    thumbnails = {
        "mini": f"{thumb_base}/mini-{name_slugified}.png",
        "thul": f"{thumb_base}/thul-{name_slugified}.png",
        "webimage": f"{thumb_base}/webimage-{name_slugified}.png",
    }
    if type == "image":
        derivative_name = settings.BYNDER_IMAGE_SOURCE_THUMBNAIL_NAME
        thumbnails[derivative_name] = (
            f"{thumb_base}/{derivative_name}-{name_slugified}.jpg"
        )

    data = {
        "activeOriginalFocusPoint": {"x": 541, "y": 550},
        "archive": 0,
        "brandId": "04215F17-57D6-48FB-9D64DA196B6B1E33",
        "copyright": copyright,
        "dateCreated": "2023-09-26T12:42:21Z",
        "dateModified": date_modified_str,
        "datePublished": "2005-03-11T02:08:12Z",
        "description": description,
        "ecsArchiveFiles": [],
        "extension": [extension],
        "fileSize": 18096064,
        "height": 2008,
        "id": id or TEST_ASSET_ID,
        "idHash": "3477c04a50a14650",
        "isPublic": 1,
        "limited": 0,
        "name": name,
        "orientation": "landscape",
        "original": f"{thumb_base}/original/{filename}",
        "property_Accession_Number": "A23339",
        "type": type,
        "userCreated": "Mr Test",
        "watermarked": 0,
        "width": 3000,
        "thumbnails": thumbnails,
    }

    if type == "video":
        url_base = f"https://{settings.BYNDER_DOMAIN}/asset/{data['id'].lower()}"
        primary_derivative = settings.BYNDER_VIDEO_PRIMARY_DERIVATIVE_NAME
        fallback_derivative = settings.BYNDER_VIDEO_FALLBACK_DERIVATIVE_NAME
        data["videoPreviewURLs"] = [
            f"{url_base}/{primary_derivative}/{primary_derivative}-{name_slugified}.webm",
            f"{url_base}/{fallback_derivative}/{fallback_derivative}-{name_slugified}.mp4",
        ]

    return data


def get_fake_image(
    width: int = 100, height: int = 100, image_format: ImageFormat = ImageFormat.JPEG
) -> io.BytesIO:
    thumb_io = io.BytesIO()
    with Image.new("RGB", (width, height), "blue") as thumb:
        thumb.save(thumb_io, format=image_format)
    return thumb_io


def get_fake_document(size: int = 1024) -> io.BytesIO:
    contents = "".join(choice(ascii_uppercase) for i in range(size))  # noqa: S311
    return io.BytesIO(contents.encode("utf-8"))


def get_fake_downloaded_image(
    name: str = "fake.jpg", width: int = 100, height: int = 100
) -> InMemoryUploadedFile:
    _, ext = os.path.splitext(name.lower())
    if ext not in IMAGE_EXTENSION_TO_FORMAT:
        raise ValueError(
            f"{ext} is not supported image file extension. Try one of the following: {list(IMAGE_EXTENSION_TO_FORMAT.keys())}"
        )
    image_format, content_type = IMAGE_EXTENSION_TO_FORMAT[ext]

    return InMemoryUploadedFile(
        get_fake_image(width, height, image_format),
        field_name="file",
        name=name,
        content_type=content_type,
        size=1048576,
        charset="utf-8",
    )


def get_fake_downloaded_document(
    name: str = "fake.pdf", size: int = 1024
) -> InMemoryUploadedFile:
    _, ext = os.path.splitext(name.lower())
    if ext not in DOCUMENT_EXTENSION_TO_FORMAT:
        raise ValueError(
            f"{ext} is not supported document file extension. Try one of the following: {list(DOCUMENT_EXTENSION_TO_FORMAT.keys())}"
        )

    return InMemoryUploadedFile(
        get_fake_document(size),
        field_name="file",
        name=name,
        content_type=DOCUMENT_EXTENSION_TO_FORMAT[ext],
        size=size,
        charset="utf-8",
    )
