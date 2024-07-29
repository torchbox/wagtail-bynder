import io
import logging
import math
import os

from dataclasses import dataclass
from datetime import datetime
from mimetypes import guess_type
from tempfile import NamedTemporaryFile
from typing import Any

from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile, UploadedFile
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.documents.models import AbstractDocument, Document
from wagtail.images.models import (
    IMAGE_FORMAT_EXTENSIONS,
    AbstractImage,
    Filter,
    Image,
)
from wagtail.models import Collection, CollectionMember
from wagtail.search import index

from wagtail_bynder import utils

from .exceptions import BynderAssetDataError


logger = logging.getLogger("wagtail.images")


@dataclass(frozen=True)
class ConvertedImageDetails:
    width: int
    height: int
    file_size: int
    image_format: str
    mime_type: str


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
        **kwargs,
    ) -> None:
        """
        Update this object (without saving) to reflect values in `asset_data`,
        which is a representation of the related asset from the Bynder API.

        NOTE: Although this base implementation does nothing with them currently,
        for compatibility reasons, ``**kwargs`` should always be accepted by all
        implementations of this method.
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

    def update_from_asset_data(
        self, asset_data: dict[str, Any], *, force_download: bool = False, **kwargs
    ) -> None:
        """
        Overrides ``BynderAssetMixin.update_from_asset_data()`` to explicitly
        handle the ``force_download`` option that can be provided by management
        commands, and to initiate downloading of the source file when it has
        changed in some way.
        """
        super().update_from_asset_data(asset_data, **kwargs)
        if force_download or not self.file or self.asset_file_has_changed(asset_data):
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
        file = self.download_file(source_url)
        processed_file = self.process_downloaded_file(file, asset_data)

        self.file = processed_file if processed_file is not None else file

        # Used to trigger additional updates on save()
        self._file_changed = True

        # Update supplementary field values
        self.source_filename = utils.filename_from_url(source_url)
        self.original_filesize = int(asset_data["fileSize"])

    def download_file(self, source_url: str) -> UploadedFile:
        raise NotImplementedError

    def process_downloaded_file(
        self, file: UploadedFile, asset_data: dict[str, Any]
    ) -> UploadedFile:
        """
        A hook to allow subclasses to apply additional analysis/customisation
        of asset files downloaded from Bynder BEFORE they are used to set the
        object's ``file`` field value. The return value is an ``UploadedFile``
        object that should be used to set the new field value.

        The provided `file` object is considered mutable, so may be modified
        directly and returned, or used purely as source data to create and
        return an entirely new ``UploadedFile`` instance.

        By default, the provided ``file`` is returned as is, without taking
        any further action.
        """
        return file


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

    class Meta(AbstractImage.Meta):
        abstract = True

    def save(self, *args, **kwargs):
        if getattr(self, "_file_changed", False):
            self._set_image_file_metadata()
        if self.pk and (
            getattr(self, "_file_changed", False)
            or getattr(self, "_focal_point_changed", False)
        ):
            # wagtail.images.forms.BaseImageForm usually takes care of this when
            # updating via the UI. But, if updating objects directly, we must
            # delete stale renditions ourselves.
            self.renditions.all().delete()
        super().save(*args, **kwargs)

    def update_from_asset_data(
        self, asset_data: dict[str, Any], *, force_download: bool = False, **kwargs
    ) -> None:
        """
        Overrides ``BynderAssetWithFileMixin.update_from_asset_data()`` to
        handle conversion of focal points to focal areas.
        """

        # Update the file and other field values without saving the changes
        super().update_from_asset_data(
            asset_data, force_download=force_download, **kwargs
        )

        # Update the focal area if a focus point is set
        current_focal_point = self.get_focal_point()
        self._focal_point_changed = False
        focus_point = asset_data.get("activeOriginalFocusPoint")
        if focus_point:
            self.set_focal_area_from_focus_point(
                int(focus_point["x"]),
                int(focus_point["y"]),
                int(asset_data["height"]),
                int(asset_data["width"]),
            )
            self._focal_point_changed = (
                current_focal_point is None
                or self.get_focal_point() != current_focal_point
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

    def download_file(self, source_url: str) -> UploadedFile:
        return utils.download_image(source_url)

    def process_downloaded_file(
        self,
        file: UploadedFile,
        asset_data: dict[str, Any] | None = None,
    ) -> UploadedFile:
        """
        Overrides ``BynderAssetWithFileMixin.process_downloaded_file()`` to
        pass the downloaded image to ``convert_downloaded_image()`` before using it as
        a value for this object's ``file`` field.
        """

        # Write to filesystem to avoid using memory for the same image
        tmp = NamedTemporaryFile(mode="w+b", dir=settings.FILE_UPLOAD_TEMP_DIR)
        details = self.convert_downloaded_image(file, tmp)

        # The original file is now redundant and can be deleted, making
        # more memory available
        del file.file

        # Load the converted image into memory to speed up the additional
        # reads and writes performed by Wagtail
        new_file = io.BytesIO()
        tmp.seek(0)
        with open(tmp.name, "rb") as source:
            for line in source:
                new_file.write(line)

        name_minus_extension, _ = os.path.splitext(file.name)
        new_extension = IMAGE_FORMAT_EXTENSIONS[details.image_format]

        # Return replacement InMemoryUploadedFile
        return InMemoryUploadedFile(
            new_file,
            field_name="file",
            name=f"{name_minus_extension}{new_extension}",
            content_type=details.mime_type,
            size=details.file_size,
            charset=None,
        )

    def get_source_image_filter_string(self, original_format: str, is_animated: bool):
        """
        Return a string for ``convert_downloaded_image()`` to use to create a
        ``wagtail.images.models.Filter`` object that can be used for source image
        conversion.
        """

        # Retreieve maximum height and width from settings
        max_width = int(getattr(settings, "BYNDER_MAX_SOURCE_IMAGE_WIDTH", 3500))
        max_height = int(getattr(settings, "BYNDER_MAX_SOURCE_IMAGE_HEIGHT", 3500))

        filter_str = f"max-{max_width}x{max_height}"
        if (
            utils.get_output_image_format(original_format, is_animated=is_animated)
            == "jpeg"
        ):
            # Since this will be a source image, use a higher JPEG quality than normal
            filter_str += " format-jpeg jpegquality-90"

        return filter_str

    def convert_downloaded_image(
        self, source_file, target_file
    ) -> ConvertedImageDetails:
        """
        Handles the conversion of the supplied ``file`` into something
        ``process_downloaded_file()`` can use to successfully assemble a
        new ``InMemoryUploadedFile``.

        ``target_file`` must be a writable file-like object, and is where the
        new file contents is written to.

        The return value is a ``ConvertedImageDetails`` object, which allows
        ``process_downloaded_file()`` to determine the height, width,
        format, mime-type and file size of the newly generated image without
        having to perform any more file operations.
        """

        width, height, original_format, is_animated = utils.get_image_info(source_file)
        filter_str = self.get_source_image_filter_string(original_format, is_animated)

        # Filter.run() expects the object's width and height to reflect
        # the image we're formatting, so we update them temporarily
        original_width, original_height = self.width, self.height
        self.width, self.height = width, height
        try:
            # Use wagtail built-ins to resize/reformat the image
            willow_image = Filter(filter_str).run(
                self,
                target_file,
                source_file,
            )
        finally:
            # Always restore original field values
            self.width, self.height = original_width, original_height

        # Gather up all of the useful data about the new image
        final_width, final_height = willow_image.get_size()
        return ConvertedImageDetails(
            final_width,
            final_height,
            target_file.tell(),
            willow_image.format_name,
            willow_image.mime_type,
        )

    def set_focal_area_from_focus_point(
        self, x: int, y: int, original_height: int, original_width: int
    ) -> None:
        """
        Using the provided focus point coordinates, generate a
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

        # Draw a rectangle around the centre point
        # For the width, span outwards until we hit the left or right bounds
        rect_width = min(x, self.width - x) * 2
        # Restrict rectangle width to 40% of the image height
        rect_width = min(rect_width, math.floor(self.width * 0.4))

        # For the height, span outwards until we hit the top or bottom bounds
        rect_height = min(y, self.height - y) * 2
        # Restrict rectangle height to 40% of the image height
        rect_height = min(rect_height, math.floor(self.height * 0.4))

        # Use the shortest side to make a square
        width = min(rect_width, rect_height)
        self.focal_point_width = width
        self.focal_point_height = width

    @staticmethod
    def extract_file_source(asset_data: dict[str, Any]) -> str:
        # For images, we store and use the source derivative filename,
        # because the 'original' isn't always present
        asset_id = asset_data["id"]
        key = getattr(settings, "BYNDER_IMAGE_SOURCE_THUMBNAIL_NAME", "WagtailSource")
        thumbnails = asset_data["thumbnails"]
        try:
            return thumbnails[key]
        except KeyError as e:
            raise BynderAssetDataError(
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

    class Meta(AbstractDocument.Meta):
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
            raise BynderAssetDataError(
                f"'original' is missing from the API representation for document asset '{asset_id}'. "
                "This is likely because the asset is marked as 'private' in Bynder. Wagtail needs the "
                "'original' asset URL in order to download and save its own copy."
            ) from e

    def download_file(self, source_url: str) -> UploadedFile:
        return utils.download_document(source_url)


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
        verbose_name = _("video")
        verbose_name_plural = _("videos")

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
        **kwargs,
    ) -> None:
        """
        Overrides ``BynderAssetMixin.update_from_asset_data()`` to handle
        setting of video-specific field values.
        """

        primary_derivative_name = getattr(
            settings, "BYNDER_VIDEO_PRIMARY_DERIVATIVE_NAME", "WebPrimary"
        )
        fallback_derivative_name = getattr(
            settings, "BYNDER_VIDEO_FALLBACK_DERIVATIVE_NAME", "WebFallback"
        )
        poster_image_derivative_name = getattr(
            settings, "BYNDER_VIDEO_POSTER_IMAGE_DERIVATIVE_NAME", "webimage"
        )

        derivatives = {v.split("/")[-2]: v for v in asset_data["videoPreviewURLs"]}
        try:
            self.primary_source_url = derivatives[primary_derivative_name]
        except KeyError as e:
            raise BynderAssetDataError(
                "'videoPreviewURLs' does not contain a URL matching the derivative name "
                f"'{primary_derivative_name}'. You might need to update the "
                "'BYNDER_VIDEO_PRIMARY_DERIVATIVE_NAME' setting value to reflect the derivative "
                "names set by Bynder for your instance. The available derivatives for this "
                f"asset are: {list(derivatives.keys())}"
            ) from e
        else:
            self.source_filename = utils.filename_from_url(self.primary_source_url)

        self.fallback_source_url = derivatives.get(fallback_derivative_name)

        thumbnails = asset_data["thumbnails"]
        try:
            self.poster_image_url = thumbnails[poster_image_derivative_name]
        except KeyError as e:
            raise BynderAssetDataError(
                f"The '{poster_image_derivative_name}' derivative is missing from 'thumbnails' for "
                f"video asset '{self.bynder_id}'. You might need to update the "
                "'BYNDER_VIDEO_POSTER_IMAGE_DERIVATIVE_NAME' setting value to reflect the "
                "derivative names set by Bynder for you instance. The available derivative names "
                f"for this asset are: {list(thumbnails.keys())}"
            ) from e

        self.original_filesize = int(asset_data["fileSize"])
        self.original_width = int(asset_data["width"])
        self.original_height = int(asset_data["height"])

        super().update_from_asset_data(asset_data, **kwargs)
