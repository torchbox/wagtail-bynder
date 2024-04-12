from datetime import datetime

from django.utils.text import slugify


TEST_ASSET_ID = "1A7BA172-97B9-44A4-8C0AA41D9E8AE6A2"


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
