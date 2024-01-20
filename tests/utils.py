from datetime import datetime


TEST_ASSET_ID = "1A7BA172-97B9-44A4-8C0AA41D9E8AE6A2"


def get_test_asset_data(
    id: str = TEST_ASSET_ID,
    name: str = "Test asset",
    copyright: str = "",
    alt_text: str = "",
    date_modified: datetime | None = None,
):
    from django.conf import settings

    if date_modified:
        date_modified_str = date_modified.isoformat()
    else:
        date_modified_str = "2023-10-10T09:52:05Z"

    return {
        "activeOriginalFocusPoint": {"x": 541, "y": 550},
        "archive": 0,
        "brandId": "04215F17-57D6-48FB-9D64DA196B6B1E33",
        "copyright": copyright,
        "dateCreated": "2023-09-26T12:42:21Z",
        "dateModified": date_modified_str,
        "datePublished": "2005-03-11T02:08:12Z",
        "description": (
            "Medieval iron battleaxe. This battleaxe has a triangular blade with a reinforced edge and eared socket. "
            "The wooden handle has been added recently. This is part of a group of battleaxes and spears that were "
            "found during building works at the north end of London Bridge in the 1920s. They may have been lost in "
            "battle or thrown into the river by the victors in celebration."
        ),
        "property_Alt_text": alt_text,
        "ecsArchiveFiles": [],
        "extension": ["tif"],
        "fileSize": 18096064,
        "height": 2008,
        "id": id or TEST_ASSET_ID,
        "idHash": "3477c04a50a14650",
        "isPublic": 0,
        "limited": 0,
        "name": name,
        "orientation": "landscape",
        "original": f"https://{settings.BYNDER_DOMAIN}/m/3477c04a50a14650/original/Medieval-iron-battleaxe-11th-century.tif",
        "property_Accession_Number": "A23339",
        "thumbnails": {
            "mini": f"https://{settings.BYNDER_DOMAIN}/m/3477c04a50a14650/mini-Medieval-iron-battleaxe-11th-century.png",
            "thul": f"https://{settings.BYNDER_DOMAIN}/m/3477c04a50a14650/thul-Medieval-iron-battleaxe-11th-century.png",
            "webimage": f"https://{settings.BYNDER_DOMAIN}/m/3477c04a50a14650/webimage-Medieval-iron-battleaxe-11th-century.png",
        },
        "type": "image",
        "userCreated": "Mr Test",
        "watermarked": 0,
        "width": 3000,
    }
