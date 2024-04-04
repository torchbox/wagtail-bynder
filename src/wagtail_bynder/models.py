import logging
import math

from datetime import datetime
from mimetypes import guess_type
from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.documents.models import AbstractDocument, Document
from wagtail.images.models import AbstractImage, Image
from wagtail.models import Collection, CollectionMember
from wagtail.search import index

from wagtail_bynder import utils


logger = logging.getLogger("wagtail.images")


class BynderAssetMixin(models.Model):
    # Fields relevant to the Bynder integration only
    bynder_id = models.CharField(
        verbose_name=_("Bynder asset ID"),
        max_length=36,
        blank=True,
        unique=True,
        editable=False,
        db_index=True,
        null=True,
    )
    bynder_last_modified = models.DateTimeField(
        null=True, editable=False, db_index=True
    )
    source_filename = models.CharField(
        verbose_name=_("source filename"),
        max_length=255,
        blank=True,
        editable=False,
    )
    original_filesize = models.IntegerField(
        verbose_name=_("original filesize"), editable=False, null=True
    )

    # Fields for broader use
    description = models.TextField(verbose_name=_("description"), blank=True)
    copyright = models.TextField(verbose_name=_("copyright info"), blank=True)
    is_archived = models.BooleanField(
        verbose_name=_("asset is archived"), default=False
    )
    is_limited_use = models.BooleanField(
        verbose_name=_("asset is marked as 'limited use'"),
        default=False,
    )
    is_public = models.BooleanField(
        verbose_name=_("asset is marked as public"), default=False
    )

    extra_admin_form_fields = (
        "description",
        "copyright",
        "is_archived",
        "is_limited_use",
        "is_public",
    )

    extra_search_fields = [
        index.SearchField("bynder_id", boost=3),
        index.SearchField("description"),
        index.SearchField("copyright"),
        index.AutocompleteField("bynder_id"),
        index.AutocompleteField("description"),
        index.AutocompleteField("copyright"),
    ]

    class Meta:
        abstract = True

    def is_up_to_date(self, asset_data: dict[str, Any]) -> bool:
        """
        Return a `bool` indicating whether if, based on the supplied `asset_data`,
        this object needs to be updated to reflect possible changes and resaved.
        """
        return (
            not self.bynder_last_modified
            or self.bynder_last_modified
            >= datetime.fromisoformat(asset_data["dateModified"])
        )

    def update_from_asset_data(
        self,
        asset_data: dict[str, Any],
    ) -> None:
        """
        Update this object (without saving) to reflect values in `asset_data`,
        which is a representation of the related asset from the Bynder API.
        """
        self.title = asset_data.get("name", self.title)
        self.copyright = asset_data.get("copyright", self.copyright)
        self.description = asset_data.get("description", self.description)
        self.collection = self.get_target_collection(asset_data)
        self.bynder_last_modified = asset_data["dateModified"]
        self.is_archived = bool(asset_data.get("archive", 0))
        self.is_limited_use = bool(asset_data.get("limited", 0))
        self.is_public = bool(asset_data.get("isPublic", 0))

    def get_target_collection(self, asset_data: dict[str, Any]) -> Collection:
        return utils.get_default_collection()


class BynderAssetWithFileMixin(BynderAssetMixin):
    extra_search_fields = BynderAssetMixin.extra_search_fields + [
        index.SearchField("file", boost=1),
        index.AutocompleteField("file"),
    ]

    class Meta:
        abstract = True

    @staticmethod
    def extract_file_source(asset_data: dict[str, Any]) -> str:
        raise NotImplementedError

    def update_from_asset_data(self, asset_data: dict[str, Any]) -> None:
        super().update_from_asset_data(asset_data)
        if not self.file or self.asset_file_has_changed(asset_data):
            self.update_file(asset_data)

    def asset_file_has_changed(self, asset_data: dict[str, Any]) -> bool:
        source_url = self.extract_file_source(asset_data)
        filename = utils.filename_from_url(source_url)
        return (
            self.source_filename != filename
            or self.original_filesize is None
            or self.original_filesize != int(asset_data["fileSize"])
        )

    def update_file(self, asset_data: dict[str, Any]) -> None:
        source_url = self.extract_file_source(asset_data)
        self.file = utils.download_asset(source_url)

        # Used to trigger additional updates on save()
        self._file_changed = True

        # Update supplementary field values
        self.source_filename = utils.filename_from_url(source_url)
        self.original_filesize = int(asset_data["fileSize"])


class BynderSyncedImage(BynderAssetWithFileMixin, AbstractImage):
    admin_form_fields = (
        Image.admin_form_fields + BynderAssetMixin.extra_admin_form_fields
    )

    original_width = models.IntegerField(
        verbose_name=_("original width"), null=True, editable=False
    )
    original_height = models.IntegerField(
        verbose_name=_("original height"), null=True, editable=False
    )

    search_fields = (
        AbstractImage.search_fields + BynderAssetWithFileMixin.extra_search_fields
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if getattr(self, "_file_changed", False):
            self._set_image_file_metadata()
        super().save(*args, **kwargs)

    def update_from_asset_data(
        self,
        asset_data: dict[str, Any],
    ) -> None:
        # Update the file and other field values without saving the changes
        super().update_from_asset_data(asset_data)

        # Update the focal area if a focus point is set
        focus_point = asset_data.get("activeOriginalFocusPoint")
        if focus_point:
            self.set_focal_area_from_focus_point(
                int(focus_point["x"]),
                int(focus_point["y"]),
                int(asset_data["height"]),
                int(asset_data["width"]),
            )

    def asset_file_has_changed(self, asset_data: dict[str, Any]) -> bool:
        return (
            super().asset_file_has_changed(asset_data)
            or (self.original_height or 0) != int(asset_data["height"])
            or (self.original_width or 0) != int(asset_data["width"])
        )

    def update_file(self, asset_data: dict[str, Any]) -> None:
        self.original_width = int(asset_data["width"])
        self.original_height = int(asset_data["height"])
        return super().update_file(asset_data)

    def set_focal_area_from_focus_point(
        self, x: int, y: int, original_height: int, original_width: int
    ) -> None:
        """
        Using the provided center-point coordinates, generate a
        2D focal area for the downloaded image.
        """
        if x < 0 or y < 0 or x > original_width or y > original_height:
            raise ValueError(
                "Focus point coordinates must be inside the original image bounds"
            )

        # Scale the coordinates to reflect the dimensions of the image that
        # was actually downloaded
        if self.height != original_height:
            scale = original_height / self.height
            x = math.floor(x / scale)
            y = math.floor(y / scale)

        # Set the centre point
        self.focal_point_x = x
        self.focal_point_y = y

        # For the width, span outwards until we hit the left or right bounds
        self.focal_point_width = min(x, self.width - x) * 2

        # For the height, span outwards until we hit the top or bottom bounds
        self.focal_point_height = min(y, self.height - y) * 2

    @staticmethod
    def extract_file_source(asset_data: dict[str, Any]) -> str:
        # For images, we store and use the source derivative filename,
        # because the 'original' isn't always present
        asset_id = asset_data["id"]
        key = getattr(settings, "BYNDER_IMAGE_SOURCE_THUMBNAIL_NAME", "webimage")
        thumbnails = asset_data["thumbnails"]
        try:
            return thumbnails[key]
        except KeyError as e:
            raise ImproperlyConfigured(
                f"The '{key}' derivative is missing from 'thumbnails' for image asset '{asset_id}'. "
                "You might need to update the 'BYNDER_IMAGE_SOURCE_THUMBNAIL_NAME' setting value to reflect "
                "derivative names used in your Bynder instance. The available derivatives for this asset "
                f"are: {list(thumbnails.keys())}"
            ) from e


class BynderSyncedDocument(BynderAssetWithFileMixin, AbstractDocument):
    admin_form_fields = (
        Document.admin_form_fields + BynderAssetMixin.extra_admin_form_fields
    )

    search_fields = (
        AbstractDocument.search_fields + BynderAssetWithFileMixin.extra_search_fields
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if getattr(self, "_file_changed", False):
            self._set_document_file_metadata()
        super().save(*args, **kwargs)

    @staticmethod
    def extract_file_source(asset_data: dict[str, Any]) -> str:
        asset_id = asset_data["id"]
        try:
            return asset_data["original"]
        except KeyError as e:
            raise KeyError(
                f"'original' is missing from the API representation for document asset '{asset_id}'. "
                "This is likely because the asset is marked as 'private' in Bynder. Wagtail needs the "
                "'original' asset URL in order to download and save its own copy."
            ) from e


class BynderSyncedVideo(
    BynderAssetMixin, CollectionMember, index.Indexed, models.Model
):
    title = models.CharField(max_length=255, verbose_name=_("title"))
    created_at = models.DateTimeField(
        verbose_name=_("created at"), auto_now_add=True, db_index=True
    )
    updated_at = models.DateTimeField(
        verbose_name=_("last updated at"), auto_now=True, db_index=True
    )
    original_width = models.IntegerField(
        verbose_name=_("original width"), null=True, editable=False
    )
    original_height = models.IntegerField(
        verbose_name=_("original height"), null=True, editable=False
    )
    primary_source_url = models.URLField(
        verbose_name=_("primary source URL"),
        help_text=_(
            "A derivative using a WebM container using the VP9 codec for video and the Opus codec "
            "for audio. These are all open, royalty-free formats which are generally "
            "well-supported, although only in quite recent browsers, which is why a fallback is a "
            "good idea."
        ),
    )
    fallback_source_url = models.URLField(
        blank=True,
        verbose_name=_("fallback source URL"),
        help_text=(
            "A derivative using an MP4 container and the AVC (H.264) video codec, ideally with "
            "AAC as your audio codec. This is because the MP4 container with AVC and AAC codecs "
            "within is a broadly-supported combination—by every major browser, in fact—and the "
            "quality is typically good for most use cases."
        ),
    )
    poster_image_url = models.URLField(verbose_name=_("poster image URL"))

    search_fields = [
        index.SearchField("title", boost=3),
        index.AutocompleteField("title"),
        index.SearchField("primary_source_url", boost=1),
        index.AutocompleteField("primary_source_url"),
    ] + BynderAssetMixin.extra_search_fields

    panels = [
        FieldPanel("title"),
        FieldPanel("description"),
        FieldPanel("primary_source_url"),
        FieldPanel("fallback_source_url"),
        FieldPanel("poster_image_url"),
        FieldPanel("copyright", read_only=True),
        MultiFieldPanel(
            heading=_("Status flags"),
            children=[
                FieldPanel("is_archived", read_only=True),
                FieldPanel("is_limited_use", read_only=True),
                FieldPanel("is_public", read_only=True),
            ],
        ),
        MultiFieldPanel(
            heading=_("Further information"),
            children=[
                FieldPanel("original_filesize", read_only=True),
                FieldPanel("original_height", read_only=True),
                FieldPanel("original_width", read_only=True),
            ],
        ),
    ]

    class Meta:
        abstract = True

    def __str__(self):
        return self.title

    @cached_property
    def primary_source_mimetype(self) -> str:
        if not self.primary_source_url:
            return ""
        return guess_type(self.primary_source_url)[0]

    @cached_property
    def fallback_source_mimetype(self) -> str:
        if not self.fallback_source_url:
            return ""
        return guess_type(self.fallback_source_url)[0]

    def update_from_asset_data(
        self,
        asset_data: dict[str, Any],
    ) -> None:
        super().update_from_asset_data(asset_data)

        primary_derivative_name = getattr(
            settings, "BYNDER_VIDEO_PRIMARY_DERIVATIVE_NAME", "Web-Primary"
        )
        fallback_derivative_name = getattr(
            settings, "BYNDER_VIDEO_FALLBACK_DERIVATIVE_NAME", "Web-Fallback"
        )
        poster_image_derivative_name = getattr(
            settings, "BYNDER_VIDEO_POSTER_IMAGE_DERIVATIVE_NAME", "webimage"
        )

        derivatives = {v.split("/")[-2]: v for v in asset_data["videoPreviewURLs"]}
        try:
            self.primary_source_url = derivatives[primary_derivative_name]
        except KeyError:
            raise ImproperlyConfigured(
                "'videoPreviewURLs' does not contain a URL matching the derivative name "
                f"'{primary_derivative_name}'. You might need to update the "
                "'BYNDER_VIDEO_PRIMARY_DERIVATIVE_NAME' setting value to reflect the derivative "
                "names set by Bynder for your instance. The available derivatives for this "
                f"asset are: {derivatives}"
            ) from None
        else:
            self.source_filename = utils.filename_from_url(self.primary_source_url)

        self.fallback_source_url = derivatives.get(fallback_derivative_name)

        thumbnails = asset_data["thumbnails"]
        try:
            self.poster_image_url = thumbnails[poster_image_derivative_name]
        except KeyError as e:
            raise ImproperlyConfigured(
                f"The '{poster_image_derivative_name}' derivative is missing from 'thumbnails' for "
                f"video asset '{self.bynder_id}'. You might need to update the "
                "'BYNDER_VIDEO_POSTER_IMAGE_DERIVATIVE_NAME' setting value to reflect the "
                "derivative names set by Bynder for you instance. The available derivative names "
                f"for this asset are: {thumbnails.keys()}"
            ) from e

        self.original_filesize = int(asset_data["fileSize"])
        self.original_width = int(asset_data["width"])
        self.original_height = int(asset_data["height"])
