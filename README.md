# Bynder integration for Wagtail

[![Build status](https://img.shields.io/github/actions/workflow/status/torchbox/wagtail-bynder/test.yml?branch=main)](https://github.com/torchbox/wagtail-bynder/actions)
[![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD--3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![PyPI version](https://img.shields.io/pypi/v/wagtail-bynder.svg?style=flat)](https://pypi.org/project/wagtail-bynder)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

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

Currently, changes are synced from Bynder back to Wagtail via a couple of well optimised management commands,
intended to be run regularly (via a cron job):

- `python manage.py update_stale_images`
- `python manage.py update_stale_documents`

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

Finally, run Django's m`akemigrations` and `migrate` commands to apply any model field changes to your project

```shell
$ python manage.py makemigrations
$ python manage.py migrate
```

### Optional: To use videos from Bynder

To use videos from Bynder in content across the site, this app includes a specialised model to help store relevant data for videos,
plus blocks and chooser widgets to help use them in your project. However, because not all projects use video,
and project-specific requirements around video usage can be a little more custom,
the model is `abstract` - you need to subclass it in order to use the functionality.

First, import the abstract `BynderSyncedVideo` model and subclass it within your project to create a concrete model.
For example:

```python
# yourproject/videos/models.py
from wagtail_bynder.models import BynderSyncedVideo


class Video(BynderSyncedVideo):
    pass
```

Next, in your project's Django settings, add a `BYNDER_VIDEO_MODEL` item to establish your custom model as the 'official'
video model. The value should be a string in the format `"app_label.Model"`. For example:

```python
BYNDER_VIDEO_MODEL = "videos.Video"
```

Finally, run Django's `makemigrations` and `migrate` commands to create and apply the model changes in your project.

```shell
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

### `BYNDER_IMAGE_SOURCE_THUMBNAIL_NAME`

Example: `"WagtailSource"`

Default: `"webimage"`

The name of the automatically generated derivative that should be downloaded and used as the `file` value for the
representative Wagtail image (as it appears in `thumbnails` in the API representation).

WARNING: It's important to get this right, because if the specified derivative is NOT present in the response for an
image for any reason, the ORIGINAL will be downloaded - which will lead to slow chooser response times and higher memory
usage when generating renditions.

### `BYNDER_VIDEO_MODEL`

Example: `"video.Video"`

Default: `None`

### `BYNDER_VIDEO_PRIMARY_DERIVATIVE_NAME`

Default: `"Web-Primary"`

### `BYNDER_VIDEO_FALLBACK_DERIVATIVE_NAME`

Default: `"Web-Fallback"`

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

### `BYNDER_DISABLE_WAGTAIL_EDITING_FOR_ASSETS`

Example: `True`

Default: `False`

When `True`, hitting Wagtail's built-in edit view for an image or document will result in a redirect to the asset
detail view in the Bynder interface.

The default is value is `False`, because it can be useful to use the Wagtail representation to check that file, metadata
and focal points are being accurately reflected.
