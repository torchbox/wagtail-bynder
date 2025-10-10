import io

from unittest import mock

from django.conf import settings
from django.test import SimpleTestCase, override_settings
from wagtail.documents import get_document_model
from wagtail.images import get_image_model

from wagtail_bynder import get_video_model
from wagtail_bynder.exceptions import (
    BynderAssetDataError,
    BynderAssetDownloadError,
    BynderAssetFileTooLarge,
    BynderInvalidImageContentError,
)
from wagtail_bynder.utils import filename_from_url

from .utils import (
    get_fake_downloaded_document,
    get_fake_downloaded_image,
    get_test_asset_data,
)


class BynderSyncedDocumentTests(SimpleTestCase):
    def setUp(self):
        model_class = get_document_model()
        self.asset_data = get_test_asset_data(
            name="My Groovy Document",
            type="document",
            id="7df5c640-af36-4502-84ca-c1e0005dd229",
        )
        self.obj = model_class(
            title=self.asset_data["name"],
            bynder_id=self.asset_data["id"],
            source_filename=filename_from_url(self.asset_data["original"]),
            original_filesize=self.asset_data["fileSize"],
            collection_id=1,
        )
        super().setUp()

    def test_extract_file_source(self):
        # When 'original' is present, that should be used
        self.assertIs(
            self.obj.extract_file_source(self.asset_data), self.asset_data["original"]
        )
        # When it is not present, a special KeyError should be raised
        asset_id = self.asset_data["id"]
        del self.asset_data["original"]
        with self.assertRaisesMessage(
            BynderAssetDataError,
            (
                f"'original' is missing from the API representation for document asset '{asset_id}'. "
                "This is likely because the asset is marked as 'private' in Bynder. Wagtail needs the "
                "'original' asset URL in order to download and save its own copy."
            ),
        ):
            self.obj.extract_file_source(self.asset_data)

    def test_asset_file_has_changed(self):
        # `self.obj` is initialized with values from the API representation,
        # so no changes should be reported by default
        self.assertFalse(self.obj.asset_file_has_changed(self.asset_data))
        # That should change if a change in 'fileSize' is detected
        data = self.asset_data.copy()
        data["fileSize"] = 999
        self.assertTrue(self.obj.asset_file_has_changed(data))
        # OR if a change in filename is detected
        data = self.asset_data.copy()
        data["original"] = data["original"][:-5] + "foobar" + data["original"][-5:]
        self.assertTrue(self.obj.asset_file_has_changed(data))

    def test_update_file(self):
        self.obj.source_filename = None
        self.obj.original_filesize = None
        self.assertFalse(hasattr(self.obj, "_file_changed"))

        fake_document = get_fake_downloaded_document()

        with (
            mock.patch.object(
                self.obj, "download_file", return_value=fake_document
            ) as download_file_mock,
            mock.patch.object(
                self.obj, "process_downloaded_file", return_value=fake_document
            ) as process_downloaded_file_mock,
        ):
            self.obj.update_file(self.asset_data)

        download_file_mock.assert_called_once_with(self.asset_data["original"])
        process_downloaded_file_mock.assert_called_once_with(
            fake_document, self.asset_data
        )

        self.assertTrue(self.obj._file_changed)
        self.assertEqual(
            self.obj.source_filename, filename_from_url(self.asset_data["original"])
        )
        self.assertEqual(self.obj.original_filesize, self.asset_data["fileSize"])

    def test_update_from_asset_data(self):
        self.obj.title = None
        self.obj.copyright = None
        self.obj.description = None
        self.obj.bynder_last_modified = None
        self.obj.is_archived = None
        self.obj.is_limited_use = None
        self.obj.is_public = None

        with (
            mock.patch(
                "wagtail_bynder.models.utils.get_default_collection", return_value=None
            ),
            mock.patch.object(self.obj, "update_file"),
        ):
            self.obj.update_from_asset_data(self.asset_data)
        self.assertEqual(self.obj.title, self.asset_data["name"])
        self.assertEqual(self.obj.copyright, self.asset_data["copyright"])
        self.assertEqual(self.obj.description, self.asset_data["description"])
        self.assertEqual(self.obj.bynder_last_modified, self.asset_data["dateModified"])
        self.assertEqual(self.obj.is_archived, self.asset_data["archive"] == 1)
        self.assertEqual(self.obj.is_limited_use, self.asset_data["limited"] == 1)
        self.assertEqual(self.obj.is_public, self.asset_data["isPublic"] == 1)


class BynderSyncedImageTests(SimpleTestCase):
    def setUp(self):
        model_class = get_image_model()
        self.asset_data = get_test_asset_data(
            name="My Groovy Image",
            type="image",
            id="5e1207a7-0a11-40bd-95c8-907b8233520a",
        )
        self.obj = model_class(
            title=self.asset_data["name"],
            bynder_id=self.asset_data["id"],
            height=50,
            width=50,
            source_filename=filename_from_url(
                self.asset_data["thumbnails"]["WagtailSource"]
            ),
            original_filesize=self.asset_data["fileSize"],
            original_height=self.asset_data["height"],
            original_width=self.asset_data["width"],
            collection_id=1,
        )
        super().setUp()

    def test_extract_file_source(self):
        # For images, this method should extract the URL for the derivative
        # named by the BYNDER_IMAGE_SOURCE_THUMBNAIL_NAME setting
        derivative_name = settings.BYNDER_IMAGE_SOURCE_THUMBNAIL_NAME
        self.assertIs(
            self.obj.extract_file_source(self.asset_data),
            self.asset_data["thumbnails"][derivative_name],
        )
        # When that derivative is not present, a special KeyError should be raised
        asset_id = self.asset_data["id"]
        self.asset_data["thumbnails"] = {}
        with self.assertRaisesMessage(
            BynderAssetDataError,
            (
                f"The '{derivative_name}' derivative is missing from 'thumbnails' for image asset '{asset_id}'. "
                "You might need to update the 'BYNDER_IMAGE_SOURCE_THUMBNAIL_NAME' setting value to reflect "
                "derivative names used in your Bynder instance. The available derivatives for this asset "
                "are: []"
            ),
        ):
            self.obj.extract_file_source(self.asset_data)

    def test_asset_file_has_changed(self):
        # `self.obj` is initialized with values from the API representation,
        # so no changes should be reported by default
        self.assertFalse(self.obj.asset_file_has_changed(self.asset_data))
        # That should change if a change in 'fileSize' is detected
        data = self.asset_data.copy()
        data["fileSize"] = 999
        self.assertTrue(self.obj.asset_file_has_changed(data))
        # OR if a change in filename is detected
        data = self.asset_data.copy()
        thumb = data["thumbnails"]["WagtailSource"]
        data["thumbnails"]["WagtailSource"] = thumb[:-5] + "foobar" + thumb[-5:]
        self.assertTrue(self.obj.asset_file_has_changed(data))
        # OR a change in width
        data = self.asset_data.copy()
        data["width"] += 1
        self.assertTrue(self.obj.asset_file_has_changed(data))
        # OR a change in height
        data = self.asset_data.copy()
        data["height"] += 1
        self.assertTrue(self.obj.asset_file_has_changed(data))

    def test_update_file(self):
        self.obj.source_filename = None
        self.obj.original_filesize = None
        self.obj.original_height = None
        self.obj.original_width = None
        self.assertFalse(hasattr(self.obj, "_file_changed"))

        fake_image = get_fake_downloaded_image()
        with (
            mock.patch.object(
                self.obj, "download_file", return_value=fake_image
            ) as download_file_mock,
            mock.patch.object(
                self.obj, "process_downloaded_file", return_value=fake_image
            ) as process_downloaded_file_mock,
        ):
            self.obj.update_file(self.asset_data)

        download_file_mock.assert_called_once_with(
            self.asset_data["thumbnails"]["WagtailSource"]
        )
        process_downloaded_file_mock.assert_called_once_with(
            fake_image, self.asset_data
        )

        self.assertTrue(self.obj._file_changed)
        self.assertEqual(
            self.obj.source_filename,
            filename_from_url(self.asset_data["thumbnails"]["WagtailSource"]),
        )
        self.assertEqual(self.obj.original_filesize, self.asset_data["fileSize"])
        self.assertEqual(self.obj.original_height, self.asset_data["height"])
        self.assertEqual(self.obj.original_width, self.asset_data["width"])

    def test_update_file_download_error_graceful(self):
        self.obj.source_filename = None
        self.obj.original_filesize = None
        self.obj.original_height = None
        self.obj.original_width = None

        # Simulate a download error
        with mock.patch.object(
            self.obj,
            "download_file",
            side_effect=BynderAssetDownloadError("http://example.com/bad", 502),
        ):
            # Should not raise
            self.obj.update_file(self.asset_data)

        # _file_changed should NOT be set
        self.assertFalse(hasattr(self.obj, "_file_changed"))
        # file should remain unset
        self.assertFalse(self.obj.file)

    def test_update_file_invalid_content_graceful(self):
        self.obj.source_filename = None
        self.obj.original_filesize = None
        self.obj.original_height = None
        self.obj.original_width = None

        with mock.patch.object(
            self.obj,
            "download_file",
            side_effect=BynderInvalidImageContentError(
                "http://example.com/err", "html error"
            ),
        ):
            self.obj.update_file(self.asset_data)

        self.assertFalse(hasattr(self.obj, "_file_changed"))
        self.assertFalse(self.obj.file)

    def test_update_file_too_large_graceful(self):
        self.obj.source_filename = None
        self.obj.original_filesize = None
        self.obj.original_height = None
        self.obj.original_width = None

        with mock.patch.object(
            self.obj, "download_file", side_effect=BynderAssetFileTooLarge("Too big")
        ):
            self.obj.update_file(self.asset_data)

        self.assertFalse(hasattr(self.obj, "_file_changed"))
        self.assertFalse(self.obj.file)

    def test_update_from_asset_data(self):
        self.obj.title = None
        self.obj.copyright = None
        self.obj.description = None
        self.obj.bynder_last_modified = None
        self.obj.is_archived = None
        self.obj.is_limited_use = None
        self.obj.is_public = None
        self.assertIsNone(self.obj.get_focal_point())

        with (
            mock.patch(
                "wagtail_bynder.models.utils.get_default_collection", return_value=None
            ),
            mock.patch.object(self.obj, "update_file"),
        ):
            self.obj.update_from_asset_data(self.asset_data)

        self.assertEqual(self.obj.title, self.asset_data["name"])
        self.assertEqual(self.obj.copyright, self.asset_data["copyright"])
        self.assertEqual(self.obj.description, self.asset_data["description"])
        self.assertEqual(self.obj.bynder_last_modified, self.asset_data["dateModified"])
        self.assertEqual(self.obj.is_archived, self.asset_data["archive"] == 1)
        self.assertEqual(self.obj.is_limited_use, self.asset_data["limited"] == 1)
        self.assertEqual(self.obj.is_public, self.asset_data["isPublic"] == 1)
        self.assertEqual(self.obj.focal_point_x, 13)
        self.assertEqual(self.obj.focal_point_y, 13)
        self.assertEqual(self.obj.focal_point_height, 20)
        self.assertEqual(self.obj.focal_point_width, 20)
        self.assertTrue(self.obj._focal_point_changed)

    def test_update_from_asset_data_with_focal_point_change(self):
        # First, let's set the focal point values to something semi-realistic
        self.obj.focal_point_x = 20
        self.obj.focal_point_y = 20
        self.obj.focal_point_height = 20
        self.obj.focal_point_width = 20

        current_focal_point = self.obj.get_focal_point()

        # Calling update_from_asset_data() should result in a change to these values
        with (
            mock.patch(
                "wagtail_bynder.models.utils.get_default_collection", return_value=None
            ),
            mock.patch.object(self.obj, "update_file"),
        ):
            self.obj.update_from_asset_data(self.asset_data)

        new_focal_point = self.obj.get_focal_point()
        self.assertNotEqual(new_focal_point, current_focal_point)
        self.assertTrue(self.obj._focal_point_changed)

    def test_update_from_asset_data_without_focal_point_change(self):
        # Set the focal point values to reflect the typical test outcome
        self.obj.focal_point_x = 13
        self.obj.focal_point_y = 13
        self.obj.focal_point_height = 20
        self.obj.focal_point_width = 20

        current_focal_point = self.obj.get_focal_point()

        # Calling update_from_asset_data() should result in no change to these values
        with (
            mock.patch(
                "wagtail_bynder.models.utils.get_default_collection", return_value=None
            ),
            mock.patch.object(self.obj, "update_file"),
        ):
            self.obj.update_from_asset_data(self.asset_data)

        new_focal_point = self.obj.get_focal_point()
        self.assertEqual(new_focal_point, current_focal_point)
        self.assertFalse(self.obj._focal_point_changed)

    def test_process_downloaded_file(self):
        fake_image = get_fake_downloaded_image("example.jpg", 500, 200)
        state_before = self.obj.__dict__

        # The original image data should be available via the `file` attribute
        self.assertTrue(fake_image.file)

        result = self.obj.process_downloaded_file(fake_image, self.asset_data)

        # Wagtail doesn't convert JPEGs to a differet format by default, so the
        # resulting name and content type should be the same as what was provided
        self.assertEqual(result.name, fake_image.name)
        self.assertEqual(result.content_type, fake_image.content_type)

        # The original image data should have been deleted to create headroom
        # for the converted image
        self.assertFalse(hasattr(fake_image, "file"))

        # No attribute values should on the object itself should have changed
        self.assertEqual(state_before, self.obj.__dict__)

    @override_settings(
        BYNDER_MAX_SOURCE_IMAGE_WIDTH=100,
        BYNDER_MAX_SOURCE_IMAGE_HEIGHT=100,
        WAGTAILIMAGES_FORMAT_CONVERSIONS={"gif": "png", "bmp": "png", "tiff": "jpeg"},
    )
    def test_convert_downloaded_image(self):
        for original_details, expected_details in (
            (
                ("tall.gif", "gif", "image/gif", 240, 400),
                ("tall.png", "png", "image/png", 60, 100),
            ),
            (
                ("wide.bmp", "bmp", "image/bmp", 400, 100),
                ("wide.png", "png", "image/png", 100, 25),
            ),
            (
                ("big-square.tif", "tiff", "image/tiff", 400, 400),
                ("big-square.jpg", "jpeg", "image/jpeg", 100, 100),
            ),
            (
                ("small-square.tiff", "tiff", "image/tiff", 80, 80),
                ("small-square.jpg", "jpeg", "image/jpeg", 80, 80),
            ),
        ):
            with self.subTest(f"{original_details[0]} becomes {expected_details[0]}"):
                original = get_fake_downloaded_image(
                    name=original_details[0],
                    width=original_details[3],
                    height=original_details[4],
                )
                self.assertEqual(original.content_type, original_details[2])
                result = self.obj.convert_downloaded_image(original, io.BytesIO())
                self.assertEqual(
                    (
                        result.image_format,
                        result.mime_type,
                        result.width,
                        result.height,
                    ),
                    (
                        expected_details[1],
                        expected_details[2],
                        expected_details[3],
                        expected_details[4],
                    ),
                )


class BynderSyncedVideoTests(SimpleTestCase):
    def setUp(self):
        model_class = get_video_model()
        self.asset_data = get_test_asset_data(
            name="My Groovy Video",
            type="video",
            id="5bae2917-0ea4-45dc-9eeb-02a65d9ac0a2",
        )
        self.obj = model_class(
            title=self.asset_data["name"],
            bynder_id=self.asset_data["id"],
            source_filename=filename_from_url(self.asset_data["videoPreviewURLs"][0]),
            original_height=self.asset_data["height"],
            original_width=self.asset_data["width"],
            collection_id=1,
        )
        super().setUp()

    def test_primary_source_mimetype(self):
        # When 'primary_source_url' is set, the property should return a value appropriate to the URL
        self.obj.primary_source_url = self.asset_data["videoPreviewURLs"][0]
        self.assertEqual(self.obj.primary_source_mimetype, "video/webm")
        # The cached_property decorator is used, which means the value
        # is cached per instance, even if 'primary_source_url' changes
        self.obj.primary_source_url = self.asset_data["videoPreviewURLs"][1]
        self.assertEqual(self.obj.primary_source_mimetype, "video/webm")
        # If we clear the cache and unset 'primary_source_url', we should get an empty string back
        self.obj.__dict__.pop("primary_source_mimetype")
        self.obj.primary_source_url = ""
        self.assertEqual(self.obj.primary_source_mimetype, "")

    def test_fallback_source_mimetype(self):
        # When 'fallback_source_url' is set, the property should return a value appropriate to the URL
        self.obj.fallback_source_url = self.asset_data["videoPreviewURLs"][1]
        self.assertEqual(self.obj.fallback_source_mimetype, "video/mp4")
        # The cached_property decorator is used, which means the value
        # is cached per instance, even if 'primary_source_url' changes
        self.obj.fallback_source_url = self.asset_data["videoPreviewURLs"][0]
        self.assertEqual(self.obj.fallback_source_mimetype, "video/mp4")
        # If we clear the cache and unset 'primary_source_url', we should get an empty string back
        self.obj.__dict__.pop("fallback_source_mimetype")
        self.obj.fallback_source_url = ""
        self.assertEqual(self.obj.fallback_source_mimetype, "")

    def test_update_from_asset_data(self):
        self.obj.title = None
        self.obj.copyright = None
        self.obj.description = None
        self.obj.bynder_last_modified = None
        self.obj.is_archived = None
        self.obj.is_limited_use = None
        self.obj.is_public = None
        self.obj.source_filename = None
        self.obj.original_filesize = None
        self.obj.original_height = None
        self.obj.original_width = None

        with mock.patch(
            "wagtail_bynder.models.utils.get_default_collection", return_value=None
        ):
            self.obj.update_from_asset_data(self.asset_data)

        self.assertEqual(self.obj.title, self.asset_data["name"])
        self.assertEqual(self.obj.copyright, self.asset_data["copyright"])
        self.assertEqual(self.obj.description, self.asset_data["description"])
        self.assertEqual(self.obj.bynder_last_modified, self.asset_data["dateModified"])
        self.assertEqual(self.obj.is_archived, self.asset_data["archive"] == 1)
        self.assertEqual(self.obj.is_limited_use, self.asset_data["limited"] == 1)
        self.assertEqual(self.obj.is_public, self.asset_data["isPublic"] == 1)
        self.assertEqual(
            self.obj.primary_source_url, self.asset_data["videoPreviewURLs"][0]
        )
        self.assertEqual(
            self.obj.fallback_source_url, self.asset_data["videoPreviewURLs"][1]
        )
        self.assertEqual(
            self.obj.poster_image_url, self.asset_data["thumbnails"]["webimage"]
        )
        self.assertEqual(
            self.obj.source_filename,
            filename_from_url(self.asset_data["videoPreviewURLs"][0]),
        )
        self.assertEqual(self.obj.original_filesize, self.asset_data["fileSize"])
        self.assertEqual(self.obj.original_height, self.asset_data["height"])
        self.assertEqual(self.obj.original_width, self.asset_data["width"])

    def test_missing_primary_source(self):
        del self.asset_data["videoPreviewURLs"][0]
        with self.assertRaisesMessage(
            BynderAssetDataError,
            (
                "'videoPreviewURLs' does not contain a URL matching the derivative name "
                "'WebPrimary'. You might need to update the 'BYNDER_VIDEO_PRIMARY_DERIVATIVE_NAME' "
                "setting value to reflect the derivative names set by Bynder for your instance. "
                "The available derivatives for this asset are: ['WebFallback']"
            ),
        ):
            self.obj.update_from_asset_data(self.asset_data)

    def test_missing_fallback_source(self):
        del self.asset_data["videoPreviewURLs"][1]
        with mock.patch(
            "wagtail_bynder.models.utils.get_default_collection", return_value=None
        ):
            self.obj.update_from_asset_data(self.asset_data)
        self.assertIsNone(self.obj.fallback_source_url)

    def test_missing_poster_image(self):
        asset_id = self.asset_data["id"]
        del self.asset_data["thumbnails"]["webimage"]
        with self.assertRaisesMessage(
            BynderAssetDataError,
            (
                "The 'webimage' derivative is missing from 'thumbnails' "  # noqa: S608
                f"for video asset '{asset_id}'. You might need to update the "
                "'BYNDER_VIDEO_POSTER_IMAGE_DERIVATIVE_NAME' setting value to "
                "reflect the derivative names set by Bynder for you instance. "
                "The available derivative names for this asset are: ['mini', 'thul']"
            ),
        ):
            self.obj.update_from_asset_data(self.asset_data)
