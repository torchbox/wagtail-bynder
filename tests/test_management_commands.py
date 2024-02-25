import datetime

from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from freezegun import freeze_time
from testapp.factories import CustomDocumentFactory, CustomImageFactory, VideoFactory
from wagtail.documents import get_document_model
from wagtail.images import get_image_model

from wagtail_bynder import get_video_model
from wagtail_bynder.management.commands.update_stale_documents import (
    Command as UpdateStaleDocuments,
)
from wagtail_bynder.management.commands.update_stale_images import (
    Command as UpdateStaleImages,
)
from wagtail_bynder.management.commands.update_stale_videos import (
    Command as UpdateStaleVideos,
)

from .utils import TEST_ASSET_ID, get_test_asset_data


TEST_ASSET_DATA = get_test_asset_data(id=TEST_ASSET_ID)


class BaseSyncCommandTestCase(SimpleTestCase):
    """
    A base class for testing 'update_stale_images', 'update_stale_documents' and
    'update_stale_videos' commands, which uses mocking to patch out interactions
    with the Bynder API and the database.
    """

    command_name: str = ""
    model_class = None

    def setUp(self) -> None:
        super().setUp()
        self.mock_api_client = mock.Mock()
        self.mock_api_client.asset_bank_client.media_list.return_value = [
            TEST_ASSET_DATA
        ]

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


@freeze_time()
class UpdateStaleImagesTestCase(BaseSyncCommandTestCase):
    """
    Unit tests for the 'update_stale_images' management command.
    """

    command_name = "update_stale_images"
    model_class = get_image_model()
    common_api_kwargs = {
        "orderBy": "dateModified desc",
        "page": 1,
        "limit": 200,
        "type": "image",
    }

    def setUp(self) -> None:
        super().setUp()
        # NOTE: update_stale_images overrides update_object() to fetch the
        # full asset details to pass to the super() implementation, therefore
        # we need to mock the media_info() method too
        self.mock_api_client.asset_bank_client.media_info.return_value = TEST_ASSET_DATA

    def test_default(self):
        expected_datemodified = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        output = self.call_command()

        # Check the command output
        self.assertIn("Looking for image assets modified in the last 1 day(s)", output)

        # Check the mocked API client was called as expected
        self.mock_api_client.asset_bank_client.media_list.assert_called_once_with(
            {
                "dateModified": expected_datemodified.strftime("%Y-%m-%dT%H:%M:%SZ"),
                **self.common_api_kwargs,
            }
        )
        self.mock_api_client.asset_bank_client.media_info.assert_called_once_with(
            TEST_ASSET_ID
        )

        # Check the patched object was updated and saved as expected
        self.patched_obj.update_from_asset_data.assert_called_once_with(TEST_ASSET_DATA)
        self.patched_obj.save.assert_called_once()

    def test_minutes(self):
        expected_datemodified = datetime.datetime.utcnow() - datetime.timedelta(
            minutes=30
        )
        output = self.call_command(minutes=30)

        # Check the command output
        self.assertIn(
            "Looking for image assets modified in the last 30 minute(s)", output
        )

        # Check the mocked API client was called as expected
        self.mock_api_client.asset_bank_client.media_list.assert_called_once_with(
            {
                "dateModified": expected_datemodified.strftime("%Y-%m-%dT%H:%M:%SZ"),
                **self.common_api_kwargs,
            }
        )
        self.mock_api_client.asset_bank_client.media_info.assert_called_once_with(
            TEST_ASSET_ID
        )

        # Check the patched object was updated and saved as expected
        self.patched_obj.update_from_asset_data.assert_called_once_with(TEST_ASSET_DATA)
        self.patched_obj.save.assert_called_once()

    def test_hours(self):
        expected_datemodified = datetime.datetime.utcnow() - datetime.timedelta(hours=3)
        output = self.call_command(hours=3)

        # Check the command output
        self.assertIn("Looking for image assets modified in the last 3 hour(s)", output)

        # Check the mocked API was called as expected
        self.mock_api_client.asset_bank_client.media_list.assert_called_once_with(
            {
                "dateModified": expected_datemodified.strftime("%Y-%m-%dT%H:%M:%SZ"),
                **self.common_api_kwargs,
            }
        )
        self.mock_api_client.asset_bank_client.media_info.assert_called_once_with(
            TEST_ASSET_ID
        )

        # Check the patched object was updated and saved as expected
        self.patched_obj.update_from_asset_data.assert_called_once_with(TEST_ASSET_DATA)
        self.patched_obj.save.assert_called_once()

    def test_days(self):
        expected_datemodified = datetime.datetime.utcnow() - datetime.timedelta(days=3)
        output = self.call_command(days=3)

        # Check the command output
        self.assertIn("Looking for image assets modified in the last 3 day(s)", output)

        # Check the mocked API was called as expected
        self.mock_api_client.asset_bank_client.media_list.assert_called_once_with(
            {
                "dateModified": expected_datemodified.strftime("%Y-%m-%dT%H:%M:%SZ"),
                **self.common_api_kwargs,
            }
        )
        self.mock_api_client.asset_bank_client.media_info.assert_called_once_with(
            TEST_ASSET_ID
        )

        # Check the patched object was updated and saved as expected
        self.patched_obj.update_from_asset_data.assert_called_once_with(TEST_ASSET_DATA)
        self.patched_obj.save.assert_called_once()


@freeze_time()
class UpdateStaleDocumentsTestCase(BaseSyncCommandTestCase):
    """
    Unit tests for the 'update_stale_documents' management command.
    """

    command_name = "update_stale_documents"
    model_class = get_document_model()
    common_api_kwargs = {
        "orderBy": "dateModified desc",
        "page": 1,
        "limit": 200,
        "type": "document",
    }

    def test_default(self):
        expected_datemodified = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        output = self.call_command()

        # Check the command output
        self.assertIn(
            "Looking for document assets modified in the last 1 day(s)", output
        )

        # Check the mocked API was called as expected
        self.mock_api_client.asset_bank_client.media_list.assert_called_once_with(
            {
                "dateModified": expected_datemodified.strftime("%Y-%m-%dT%H:%M:%SZ"),
                **self.common_api_kwargs,
            }
        )

        # Check the patched object was updated and saved as expected
        self.patched_obj.update_from_asset_data.assert_called_once_with(TEST_ASSET_DATA)
        self.patched_obj.save.assert_called_once()

    def test_minutes(self):
        expected_datemodified = datetime.datetime.utcnow() - datetime.timedelta(
            minutes=30
        )
        output = self.call_command(minutes=30)

        # Check the command output
        self.assertIn(
            "Looking for document assets modified in the last 30 minute(s)", output
        )

        # Check the mocked API was called as expected
        self.mock_api_client.asset_bank_client.media_list.assert_called_once_with(
            {
                "dateModified": expected_datemodified.strftime("%Y-%m-%dT%H:%M:%SZ"),
                **self.common_api_kwargs,
            }
        )

        # Check the patched object was updated and saved as expected
        self.patched_obj.update_from_asset_data.assert_called_once_with(TEST_ASSET_DATA)
        self.patched_obj.save.assert_called_once()

    def test_hours(self):
        expected_datemodified = datetime.datetime.utcnow() - datetime.timedelta(hours=3)
        output = self.call_command(hours=3)

        # Check the command output
        self.assertIn(
            "Looking for document assets modified in the last 3 hour(s)", output
        )

        # Check the mocked API was called as expected
        self.mock_api_client.asset_bank_client.media_list.assert_called_once_with(
            {
                "dateModified": expected_datemodified.strftime("%Y-%m-%dT%H:%M:%SZ"),
                **self.common_api_kwargs,
            }
        )

        # Check the patched object was updated and saved as expected
        self.patched_obj.update_from_asset_data.assert_called_once_with(TEST_ASSET_DATA)
        self.patched_obj.save.assert_called_once()

    def test_days(self):
        expected_datemodified = datetime.datetime.utcnow() - datetime.timedelta(days=3)
        output = self.call_command(days=3)

        # Check the command output
        self.assertIn(
            "Looking for document assets modified in the last 3 day(s)", output
        )

        # Check the mocked API was called as expected
        self.mock_api_client.asset_bank_client.media_list.assert_called_once_with(
            {
                "dateModified": expected_datemodified.strftime("%Y-%m-%dT%H:%M:%SZ"),
                **self.common_api_kwargs,
            }
        )

        # Check the patched object was updated and saved as expected
        self.patched_obj.update_from_asset_data.assert_called_once_with(TEST_ASSET_DATA)
        self.patched_obj.save.assert_called_once()


@freeze_time()
class UpdateStaleVideosTestCase(BaseSyncCommandTestCase):
    """
    Unit tests for the 'update_stale_videos' management command.
    """

    command_name = "update_stale_videos"
    model_class = get_video_model()
    common_api_kwargs = {
        "orderBy": "dateModified desc",
        "page": 1,
        "limit": 200,
        "type": "video",
    }

    def test_default(self):
        expected_datemodified = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        output = self.call_command()

        # Check the command output
        self.assertIn("Looking for video assets modified in the last 1 day(s)", output)

        # Check the mocked API was called as expected
        self.mock_api_client.asset_bank_client.media_list.assert_called_once_with(
            {
                "dateModified": expected_datemodified.strftime("%Y-%m-%dT%H:%M:%SZ"),
                **self.common_api_kwargs,
            }
        )

        # Check the patched object was updated and saved as expected
        self.patched_obj.update_from_asset_data.assert_called_once_with(TEST_ASSET_DATA)
        self.patched_obj.save.assert_called_once()

    def test_minutes(self):
        expected_datemodified = datetime.datetime.utcnow() - datetime.timedelta(
            minutes=30
        )
        output = self.call_command(minutes=30)

        # Check the command output
        self.assertIn(
            "Looking for video assets modified in the last 30 minute(s)", output
        )

        # Check the mocked API was called as expected
        self.mock_api_client.asset_bank_client.media_list.assert_called_once_with(
            {
                "dateModified": expected_datemodified.strftime("%Y-%m-%dT%H:%M:%SZ"),
                **self.common_api_kwargs,
            }
        )

        # Check the patched object was updated and saved as expected
        self.patched_obj.update_from_asset_data.assert_called_once_with(TEST_ASSET_DATA)
        self.patched_obj.save.assert_called_once()

    def test_hours(self):
        expected_datemodified = datetime.datetime.utcnow() - datetime.timedelta(hours=3)
        output = self.call_command(hours=3)

        # Check the command output
        self.assertIn("Looking for video assets modified in the last 3 hour(s)", output)

        # Check the mocked API was called as expected
        self.mock_api_client.asset_bank_client.media_list.assert_called_once_with(
            {
                "dateModified": expected_datemodified.strftime("%Y-%m-%dT%H:%M:%SZ"),
                **self.common_api_kwargs,
            }
        )

        # Check the patched object was updated and saved as expected
        self.patched_obj.update_from_asset_data.assert_called_once_with(TEST_ASSET_DATA)
        self.patched_obj.save.assert_called_once()

    def test_days(self):
        expected_datemodified = datetime.datetime.utcnow() - datetime.timedelta(days=3)
        output = self.call_command(days=3)

        # Check the command output
        self.assertIn("Looking for video assets modified in the last 3 day(s)", output)

        # Check the mocked API was called as expected
        self.mock_api_client.asset_bank_client.media_list.assert_called_once_with(
            {
                "dateModified": expected_datemodified.strftime("%Y-%m-%dT%H:%M:%SZ"),
                **self.common_api_kwargs,
            }
        )

        # Check the patched object was updated and saved as expected
        self.patched_obj.update_from_asset_data.assert_called_once_with(TEST_ASSET_DATA)
        self.patched_obj.save.assert_called_once()


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
