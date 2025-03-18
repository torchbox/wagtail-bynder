# Bynder integration for Wagtail

[![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD--3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![PyPI version](https://img.shields.io/pypi/v/wagtail-bynder.svg?style=flat)](https://pypi.org/project/wagtail-bynder)
[![Build status](https://img.shields.io/github/actions/workflow/status/torchbox/wagtail-bynder/test.yml?branch=main)](https://github.com/torchbox/wagtail-bynder/actions)

## Links

- [Documentation](https://github.com/torchbox/wagtail-bynder/blob/main/README.md)
- [Changelog](https://github.com/torchbox/wagtail-bynder/blob/main/CHANGELOG.md)
- [Contributing](https://github.com/torchbox/wagtail-bynder/blob/main/CONTRIBUTING.md)
- [Discussions](https://github.com/torchbox/wagtail-bynder/discussions)
- [Security](https://github.com/torchbox/wagtail-bynder/security)

[Bynder](https://www.bynder.com) is a Digital Asset Management System (DAMS) and platform that allows organisations
to manage their digital assets, which includes the images and documents used in Wagtail content.

The data flow is one way: Bynder assets are always treated as the source of truth, and Wagtail uses read-only API access
to create copies of assets and keep them up-to-date.

## How it works

The main points of integration are Wagtail's image and document chooser views, which are patched by this app to show an
asset selection UI for Bynder instead of a list of Wagtail images or documents.

When an asset is selected, Wagtail silently downloads the file and related metadata, and saves it as an `Image` or
`Document` object, allowing it to be used in a typical way. The ID of the selected asset (as well as a few other bits of data)
are saved on the object when this happens, helping Wagtail to recognise when it already has a copy of an asset,
and to help keep them up-to-date with changes made in Bynder.

Currently, changes are synced from Bynder back to Wagtail via a few well-optimised management commands,
intended to be run regularly (via a cron job):

- `python manage.py update_stale_images`
- `python manage.py update_stale_documents`
- `python manage.py update_stale_videos`

By default, these commands only fetch data for assets updated within the last 24 hours. However, you can use the `minutes`, `hours` or `days` options to narrow or widen this timespan. For example:

To sync images updated within the last 30 minutes only:

```sh
$ python manage.py update_stale_images --minutes=30
```

To sync images updated within the last three hours only:

```sh
$ python manage.py update_stale_images --hours=3
```

To sync images updated within the last three days:

```sh
$ python manage.py update_stale_images --days=3
```

### Automatic conversion and downsizing of images

When the `BYNDER_IMAGE_SOURCE_THUMBNAIL_NAME` derivative for an image is successfully downloaded by Wagtail, it is passed to the `convert_downloaded_image()` method of your custom image model in order to convert it into something more suitable for Wagtail.

Firstly, downloaded images are converted to the most appropriate type, according to your project's `WAGTAILIMAGES_FORMAT_CONVERSIONS` setting and Wagtail's default preferences. For example, by default, `BMP` and `WebP` image are converted to `PNG`.

Secondly, images are downsized according to the `BYNDER_MAX_SOURCE_IMAGE_WIDTH` and `BYNDER_MAX_SOURCE_IMAGE_HEIGHT` setting values, in a way that preserves their original aspect ratio. Whilst Bynder is expected to address this on their side by generating appropriately-sized derivatives - this isn't always a possibile with their basic offering.

Ensuring source images only have enough pixels to meet the rendition-generation requirements of your project has an enormous long-term benefit for a Wagtail project (especially one with image-heavy content pages), as it provides efficiency gains **every single time** a new rendition is generated.

## What to ask of Bynder

When communicating with Bynder about configuring a new instance for compatibility with Wagtail, there are a few things you'll want to be clear about:

1. Document assets should be fully enabled
2. A custom derivative must to be configured for image assets
3. A couple of custom derivatives must be configured for video assets

### Why are custom derivatives needed?

It is common for assets to be uploaded to a DAMS in formats that preserve as much quality as possible. For example, high-resolution uncompressed TIFF images are common for digital photography. While great for print and other media, such formats are simply overkill for most websites. Not only are images likely to be shown at much smaller dimensions in a web browser, but they are also likely to be converted to more web-friendly formats like AVIF or WebP by Wagtail, where the image quality of an uncompressed TIFF is unlikely to shine through.

Over time, unnecessarily large source images will have a compounding impact on website performance. Editors will need to wait longer for Wagtail to download the images from Bynder. And, every time a new rendition is needed, the original must be loaded into memory from wherever it is stored, consuming more precious system memory than necessary, and blocking system I/O operations for longer whilst the file is read from storage.

#### 'WagtailSource' derivative for images

What Wagtail really needs is a reliable, high quality derivative, which it can use as a 'source' to generate renditions from. This should strike the right balance between:

- Being large enough to use in most website contexts (Think full-width hero images that need to look decent on a large high-resolution display). A maximum width or height of **3500 pixels** is usually enough for this.
- Retaining as much visual quality as possible, whilst keeping file sizes reasonable. Individual images will naturally vary, but somewhere **between 4MB and 6MB** is a reasonable target.

In most cases, `JPG` will probably the best option. But, for fine art images with lots of uniform colour and sharp edges, `PNG` might be a better fit.

Once configured, URLs for the new derivative should appear under `"thumbnails"` in the API representation for image assets, like so:

```json
"thumbnails": {
  "mini": "https://orgname.bynder.com/m/3ece125489f192fa/YourGroovyImage.png",
  "thul": "https://orgname.bynder.com/m/3ece125489f192fa/thul-YourGroovyImage.png",
  "webimage": "https://orgname.bynder.com/m/3ece125489f192fa/webimage-YourGroovyImage.png",
  "WagtailSource": "https://orgname.bynder.com/m/3ece125489f192fa/WagtailSource-YourGroovyImage.jpg",
}
```

### 'WebPrimary' and 'WebFallback' derivatives for videos

The goal here is to ensure video can be seen by the widest possibly audience (Wagtail doesn't take a copy of video media like it does for image - as it isn't well equipped for re-encoding it).

Support for media container formats, video and audio codecs has become more consistant over the years. The general consensus is that video on the web should be provided in two different formats in order to work for the widest audience. So, we recommend that Bynder generate **two** custom derivatives for videos:

**WebPrimary**: A derivative using a WebM container, the VP9 codec for video and the Opus codec for audio. These are all open, royalty-free formats which are generally well-supported, although only in quite recent browsers, which is why a fallback is a good idea.

**WebFallback**: A derivative using an MP4 container and the AVC (H.264) video codec, ideally with the AAC codec for audio. This combination has great support in every major browser, and the quality is typically good for most use cases.

Once configured, URLs for the new derivatives should appear under `"videoPreviewURLs"` in the API representation for video assets, like so:

```json
"videoPreviewURLs": [
  "https://orgname.bynder.com/asset/52477218-06f5-4e55-ad55-049bf33b105f/WebPrimary/WebPrimary-YourGroovyVideo.web",
  "https://orgname.bynder.com/asset/52477218-06f5-4e55-ad55-049bf33b105f/WebFallback/WebFallback-YourGroovyVideo.mp4",
]
```

NOTE: The proposed 'WebPrimary' and 'WebFallback' names do not include 'Wagtail' in the name, because there really isn't anything Wagtail-specific about them. They should be useful in any 'web' context.

## Installation

In your project's Django settings, add the app your `INSTALLED_APPS` list (at the end is fine):

```python
INSTALLED_APPS = [
  # ...
  "wagtail_bynder",
]
```

Then add the following to the `MIDDLEWARE` list (at the end is fine):

```python
MIDDLEWARE = [
  #...
  "wagtail_bynder.middleware.PatchWagtailURLsMiddleware",
]
```

Import the abstract `BynderSyncedImage` model and have your project's custom image model definition subclass it instead
of `wagtail.images.models.AbstractImage`. For example

```python
# yourproject/images/models.py
from wagtail_bynder.models import BynderSyncedImage


class CustomImage(BynderSyncedImage):
    pass
```

Import the abstract `BynderSyncedDocument` model and have your project's custom document model definition subclass it instead of
`wagtail.documents.models.AbstractDocument`. For example:

```python
# yourproject/documents/models.py
from wagtail_bynder.models import BynderSyncedDocument


class CustomDocument(BynderSyncedDocument):
    pass
```

Finally, run Django's `makemigrations` and `migrate` commands to apply any model field changes to your project

```sh
$ python manage.py makemigrations
$ python manage.py migrate
```

### Optional: To use videos from Bynder

To use videos from Bynder in content across the site, this app includes a specialised model to help store relevant data for videos,
plus blocks and chooser widgets to help use them in your project. However, because not all projects use video,
and project-specific requirements around video usage can be a little more custom,
the model is `abstract` - you need to subclass it in order to use the functionality.

First, ensure you have `wagtail.snippets` in your project's `INSTALLED_APPS`:

```python: highlight-line=7
INSTALLED_APPS = [
  # ...
  "wagtail.users",
  "wagtail.admin",
  "wagtail.documents",
  "wagtail.images",
  "wagtail.snippets",
  "wagtail",
   # ...
]
```

Next, import the abstract `BynderSyncedVideo` model and subclass it within your project to create a concrete model.
For example:

```python
# yourproject/videos/models.py
from wagtail_bynder.models import BynderSyncedVideo


class Video(BynderSyncedVideo):
    pass
```

Then, in your project's Django settings, add a `BYNDER_VIDEO_MODEL` item to establish your custom model as the 'official'
video model. The value should be a string in the format `"app_label.Model"`. For example:

```python
BYNDER_VIDEO_MODEL = "videos.Video"
```

Finally, run Django's `makemigrations` and `migrate` commands to create and apply the model changes in your project.

```sh
$ python manage.py makemigrations
$ python manage.py migrate
```

## Configuration

You can use the following settings to configure the integration:

### `BYNDER_DOMAIN`

Example: `"your-org.bynder.com"`

Default: `None`

The Bynder instance you want the environment to use.

### `BYNDER_API_TOKEN`

Example: `"60ae04f68460cfed1b289c4c1db4c9b273b238dx2030c51298dcad245b5ff1f8"`

Default: `None`

An API token for the back end to use when talking to the Bynder API.
NOTE: This could be more permissive than `BYNDER_COMPACTVIEW_API_TOKEN`, so should be kept separate to avoid surfacing to Wagtail users.

### `BYNDER_COMPACTVIEW_API_TOKEN`

Example: `"64ae04f71460cfed1b289c4c1db4c9b273b238dx2030c51298dcad245b5ff1f8"`

Default: `None`

An API token for Bynder's JavaScript 'compact view' to use. The value is injected into the `admin_base.html` template for Wagtail
for the JavaScript to pick up, exposing it to Wagtail users. Because of this, it should be different to `BYNDER_API_TOKEN`
and only needs to have basic read permissions.

### `BYNDER_MAX_DOCUMENT_FILE_SIZE`

Example: `10485760`

Default: `5242880`

The maximum acceptable file size (in Bytes) when downloading a 'Document' asset from Bynder. This is safety measure to protect projects against memory spikes when file contents is loaded into memory, and can be tweaked on a project/environment basis to reflect:

- How much RAM is available in the host infrastructure
- How large the documents are that editors want to feature in content
- Whether you are doing anything particularly memory intensive with document files in your project (e.g. text/content analysis)

### `BYNDER_IMAGE_SOURCE_THUMBNAIL_NAME`

Default: `"WagtailSource"`

The name of the automatically generated derivative that should be downloaded and used as the `file` value for the
representative Wagtail image (as it appears in `thumbnails` in the API representation).

WARNING: It's important to get this right, because if the specified derivative is NOT present in the response for an
image for any reason, the ORIGINAL will be downloaded - which will lead to slow chooser response times and higher memory
usage when generating renditions.

### `BYNDER_MAX_IMAGE_FILE_SIZE`

Example: `10485760`

Default: `5242880`

The maximum acceptable file size (in Bytes) when downloading an 'Image' asset from Bynder. This is safety measure to protect projects against memory spikes when file contents is loaded into memory.

This setting is provided separately to `BYNDER_MAX_DOCUMENT_FILE_SIZE`, because it often needs to be set to a lower value, even if enough RAM is available to hold the orignal file in memory. This is because server-size image libraries have to understand the individual pixel values of the image, which often requires much more memory than that of the original contents.

As with `BYNDER_MAX_DOCUMENT_FILE_SIZE`, this can be tweaked for individual projects/environments to reflect how much RAM is available in the host infrastructure.

### `BYNDER_MAX_SOURCE_IMAGE_WIDTH`

Example: `5000`

Default: `3500`

Used to restrict the **width** of images downloaded from Bynder before they are used as source images for objects in Wagtail's image library.

### `BYNDER_MAX_SOURCE_IMAGE_HEIGHT`

Example: `5000`

Default: `3500`

Used to restrict the **height** of images downloaded from Bynder before they are used as source images for objects in Wagtail's image library.

### `BYNDER_VIDEO_MODEL`

Example: `"video.Video"`

Default: `None`

### `BYNDER_VIDEO_PRIMARY_DERIVATIVE_NAME`

Default: `"WebPrimary"`

### `BYNDER_VIDEO_FALLBACK_DERIVATIVE_NAME`

Default: `"WebFallback"`

### `BYNDER_VIDEO_POSTER_IMAGE_DERIVATIVE_NAME`

Default: `"webimage"`

### `BYNDER_SYNC_EXISTING_IMAGES_ON_CHOOSE`

Example: `True`

Default: `False`

When `True`, local copies of images will be refreshed from the Bynder API representation whenever they are selected in
the chooser interface. This slows down the chooser experience slightly, but can be useful for seeing up-to-date data in
environments that might not be using the management commands or other means to keep images up-to-date with their Bynder counterparts.

### `BYNDER_SYNC_EXISTING_DOCUMENTS_ON_CHOOSE`

Example: `True`

Default: `False`

As `BYNDER_SYNC_EXISTING_IMAGES_ON_CHOOSE`, but for documents.

### `BYNDER_SYNC_EXISTING_VIDEOS_ON_CHOOSE`

Example: `True`

Default: `False`

As `BYNDER_SYNC_EXISTING_IMAGES_ON_CHOOSE`, but for videos.

### `BYNDER_DISABLE_WAGTAIL_EDITING_FOR_ASSETS`

Example: `True`

Default: `False`

When `True`, hitting Wagtail's built-in edit view for an image or document will result in a redirect to the asset
detail view in the Bynder interface.

The default is value is `False`, because it can be useful to use the Wagtail representation to check that file, metadata
and focal points are being accurately reflected.

## Contributing

All contributions are welcome! See [CONTRIBUTING.md](https://github.com/torchbox/wagtail-bynder/blob/main/CONTRIBUTING.md)

Supported versions:

- Python 3.11, 3.12, 3.13
- Django 4.2, 5.0, 5.1
- Wagtail 5.2 (LTS), 6.3 (LTS), 6.4
