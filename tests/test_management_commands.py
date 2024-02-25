import datetime

from io import StringIO
from typing import Type
from unittest import mock

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from freezegun import freeze_time
from testapp.factories import CustomDocumentFactory, CustomImageFactory, VideoFactory

from wagtail_bynder.management.commands.update_stale_documents import (
    Command as UpdateStaleDocuments,
)
from wagtail_bynder.management.commands.update_stale_images import (
    Command as UpdateStaleImages,
)
from wagtail_bynder.management.commands.update_stale_videos import (
    Command as UpdateStaleVideos,
)
from wagtail_bynder.models import BynderAssetMixin

from .utils import TEST_ASSET_ID, get_test_asset_data


TEST_ASSET_DATA = get_test_asset_data(id=TEST_ASSET_ID)


class SyncCommandTestsMixin:
    """
    A mixin class for testing 'update_stale_images', 'update_stale_documents' and
    'update_stale_videos' commands, which uses mocking to patch out interactions
    with the Bynder API and the database.
    """

    command_name: str = ""
    command_class: Type = None
    uses_media_info_for_individual_assets: bool = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model_class = cls.command_class.model
        cls.asset_type = cls.command_class.bynder_asset_type

    def setUp(self) -> None:
        super().setUp()

        # Define a mock to stand-in for the Bynder API client
        self.mock_api_client = mock.Mock()
        self.mock_api_client.asset_bank_client.media_list.return_value = [
            TEST_ASSET_DATA
        ]
        self.mock_api_client.asset_bank_client.media_info.return_value = TEST_ASSET_DATA

        # Create an in-memory instance of the target model class, so that
        # the command is acting on a 'real' object
        self.patched_obj = self.model_class(
            id=1,
            title="Test asset",
            bynder_id=TEST_ASSET_ID,
            bynder_last_modified=datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC),
            collection_id=1,
        )

        # Patch update_from_asset_data() to allow us to check if/how it is called
        self.patched_obj.update_from_asset_data = mock.Mock(
            spec=self.patched_obj.update_from_asset_data
        )

        # Patch save() to prevent unnecessary database writes
        self.patched_obj.save = mock.Mock()

        # Create an iterable containing the patched object
        # To be returned by a patched get_stale_objects() method
        self.mock_stale_objects = (self.patched_obj,)

    def call_command(self, *args, **kwargs):
        """
        Calls the command with the provided arguments, whilst also also mocking
        out the Bynder API client and `get_stale_objects` method, so that we
        can test the command in isolation and check that interactions happen as
        expected.
        """
        out = StringIO()

        with (
            mock.patch(
                "wagtail_bynder.management.commands.base.get_bynder_client",
                return_value=self.mock_api_client,
            ),
            mock.patch(
                "wagtail_bynder.management.commands.base.BaseBynderSyncCommand.get_stale_objects",
                return_value=self.mock_stale_objects,
            ),
        ):
            call_command(
                self.command_name,
                *args,
                stdout=out,
                stderr=StringIO(),
                **kwargs,
            )
        return out.getvalue()

    def assertCommandRunOutcome(
        self,
        output: StringIO,
        mocked_client: mock.Mock,
        model_instance: BynderAssetMixin,
        expected_datemodified: datetime.datetime,
        expected_timespan_description: str,
    ):
        """
        Assert that the command output indicates success, and that the mocked
        API client and `get_stale_objects` method were called as expected.
        """
        self.assertIn(
            f"Looking for {self.asset_type} assets modified within the last {expected_timespan_description}",
            output,
        )
        self.assertIn("Processing batch 1 (1 assets)...", output)
        self.assertIn("1 stale objects were found for this batch", output)
        self.assertIn(f"Updating object for asset '{TEST_ASSET_ID}'", output)

        # Test that 'media_list' was called as expected
        mocked_client.asset_bank_client.media_list.assert_called_once_with(
            {
                "dateModified": expected_datemodified.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "orderBy": "dateModified desc",
                "page": 1,
                "limit": self.command_class.page_size,
                "type": self.asset_type,
            }
        )

        # Conditionally test that 'media_info' was called as expected
        if self.uses_media_info_for_individual_assets:
            mocked_client.asset_bank_client.media_info.assert_called_once_with(
                TEST_ASSET_ID
            )

        # Check the patched object was updated and saved as expected
        model_instance.update_from_asset_data.assert_called_once_with(TEST_ASSET_DATA)
        model_instance.save.assert_called_once()

    @freeze_time()
    def test_default(self):
        expected_datemodified = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        expected_timespan_description = "1 day"
        output = self.call_command()

        self.assertCommandRunOutcome(
            output,
            self.mock_api_client,
            self.patched_obj,
            expected_datemodified,
            expected_timespan_description,
        )

    @freeze_time()
    def test_minutes(self):
        expected_datemodified = datetime.datetime.utcnow() - datetime.timedelta(
            minutes=30
        )
        expected_timespan_description = "30 minute(s)"
        output = self.call_command(minutes=30)

        self.assertCommandRunOutcome(
            output,
            self.mock_api_client,
            self.patched_obj,
            expected_datemodified,
            expected_timespan_description,
        )

    @freeze_time()
    def test_hours(self):
        expected_datemodified = datetime.datetime.utcnow() - datetime.timedelta(hours=3)
        expected_timespan_description = "3 hour(s)"

        # NOTE: 'minutes' should be ignored when hours is provided
        output = self.call_command(hours=3, minutes=99999)

        self.assertCommandRunOutcome(
            output,
            self.mock_api_client,
            self.patched_obj,
            expected_datemodified,
            expected_timespan_description,
        )

    @freeze_time()
    def test_days(self):
        expected_datemodified = datetime.datetime.utcnow() - datetime.timedelta(days=3)
        expected_timespan_description = "3 day(s)"

        # NOTE: 'hours' and 'minutes' should be ignored when days is provided
        output = self.call_command(days=3, hours=99999, minutes=99999)

        self.assertCommandRunOutcome(
            output,
            self.mock_api_client,
            self.patched_obj,
            expected_datemodified,
            expected_timespan_description,
        )


class UpdateStaleImagesTestCase(SyncCommandTestsMixin, SimpleTestCase):
    """
    Unit tests for the 'update_stale_images' management command.
    """

    command_name = "update_stale_images"
    command_class = UpdateStaleImages
    uses_media_info_for_individual_assets = True


class UpdateStaleDocumentsTestCase(SyncCommandTestsMixin, SimpleTestCase):
    """
    Unit tests for the 'update_stale_documents' management command.
    """

    command_name = "update_stale_documents"
    command_class = UpdateStaleDocuments
    uses_media_info_for_individual_assets = False


class UpdateStaleVideosTestCase(SyncCommandTestsMixin, SimpleTestCase):
    """
    Unit tests for the 'update_stale_videos' management command.
    """

    command_name = "update_stale_videos"
    command_class = UpdateStaleVideos
    uses_media_info_for_individual_assets = False


class TestGetStaleObjects(TestCase):
    """
    Unit tests for the `get_stale_objects` method, which is mocked out in
    the test cases above.
    """

    stale_dt = datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC)
    fresh_dt = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
    fake_asset_batch = {TEST_ASSET_ID: TEST_ASSET_DATA}

    def test_update_stale_images(self):
        # Save a matching object that we is out-of-date
        stale_image = CustomImageFactory(
            bynder_id=TEST_ASSET_ID, bynder_last_modified=self.stale_dt
        )

        # Call the `get_stale_objects` method directly
        command_instance = UpdateStaleImages()
        result = list(command_instance.get_stale_objects(self.fake_asset_batch))
        self.assertEqual(result, [stale_image])

        # Delete the stale object and create one we know is fresh
        stale_image.delete()
        CustomImageFactory(bynder_id=TEST_ASSET_ID, bynder_last_modified=self.fresh_dt)

        # Now call `get_stale_objects` again and test the result
        self.assertFalse(
            list(command_instance.get_stale_objects(self.fake_asset_batch))
        )

    def test_update_stale_documents(self):
        # Save a matching object that we is out-of-date
        stale_document = CustomDocumentFactory(
            bynder_id=TEST_ASSET_ID, bynder_last_modified=self.stale_dt
        )

        # Call the `get_stale_objects` method directly
        command_instance = UpdateStaleDocuments()
        result = list(command_instance.get_stale_objects(self.fake_asset_batch))
        self.assertEqual(result, [stale_document])

        # Delete the stale object and create one we know is fresh
        stale_document.delete()
        CustomDocumentFactory(
            bynder_id=TEST_ASSET_ID, bynder_last_modified=self.fresh_dt
        )

        # Now call `get_stale_objects` again and test the result
        self.assertFalse(
            list(command_instance.get_stale_objects(self.fake_asset_batch))
        )

    def test_update_stale_videos(self):
        # Save a matching object that we is out-of-date
        stale_video = VideoFactory(
            bynder_id=TEST_ASSET_ID, bynder_last_modified=self.stale_dt
        )

        # Call the `get_stale_objects` method directly
        command_instance = UpdateStaleVideos()
        result = list(command_instance.get_stale_objects(self.fake_asset_batch))
        self.assertEqual(result, [stale_video])

        # Delete the stale object and create one we know is fresh
        stale_video.delete()
        VideoFactory(bynder_id=TEST_ASSET_ID, bynder_last_modified=self.fresh_dt)

        # Now call `get_stale_objects` again and test the result
        self.assertFalse(
            list(command_instance.get_stale_objects(self.fake_asset_batch))
        )
