from unittest import mock

import responses
from django.test import TestCase
from wagtail.images import get_image_model
from wagtail_factories import ImageFactory

from wagtail_bynder.views.mixins import BynderAssetCopyMixin

from .utils import TEST_ASSET_ID, get_test_asset_data

TEST_ASSET_DATA = get_test_asset_data(id=TEST_ASSET_ID)


class BynderAssetCopyMixinTests(TestCase):
    def setUp(self):
        super().setUp()
        self.view = BynderAssetCopyMixin()
        self.view.model = get_image_model()
        # Mock out Bynder API calls
        responses.add(
            responses.GET,
            f"https://test-org.bynder.com/api/v4/media/{TEST_ASSET_ID}/",
            json=TEST_ASSET_DATA,
            status=200,
        )

    @responses.activate
    def test_create_object(self):
        # After fetching the data from bynder, the method should create a
        # new object, call update_from_asset_data() to populate some
        # fields values, then save the changes.
        with mock.patch.object(
            self.view.model, "update_from_asset_data"
        ) as update_from_asset_data_mock:
            with mock.patch.object(self.view.model, "save") as save_mock:
                # Run the code to be tested!
                obj = self.view.create_object(TEST_ASSET_ID)

        # Assertions
        update_from_asset_data_mock.assert_called_once_with(TEST_ASSET_DATA)
        save_mock.assert_called_once()
        self.assertEqual(obj.bynder_id, TEST_ASSET_ID)

    @responses.activate
    def test_update_object_when_object_is_up_to_date(self):
        # Create an object that matches the asset ID being used
        obj = ImageFactory(bynder_id=TEST_ASSET_ID)

        # After fetching the data from bynder, the method should call the object's
        # 'is_up_to_date()' method, then will only update and save the object if
        # `False` is returned
        with mock.patch.object(
            obj, "is_up_to_date", return_value=True
        ) as is_up_to_date_mock:
            with mock.patch.object(
                obj, "update_from_asset_data"
            ) as update_from_asset_data_mock:
                with mock.patch.object(obj, "save") as save_mock:
                    # Run the code to be tested!
                    self.view.update_object(TEST_ASSET_ID, obj)

        # Assertions
        is_up_to_date_mock.assert_called_once_with(TEST_ASSET_DATA)
        update_from_asset_data_mock.assert_not_called()
        save_mock.assert_not_called()

    @responses.activate
    def test_update_object_when_object_is_outdated(self):
        # Create an object that matches the asset ID being used
        obj = ImageFactory(bynder_id=TEST_ASSET_ID)

        # After fetching the data from bynder, the method should call the object's
        # 'is_up_to_date()' method, then will only update and save the object if
        # `False` is returned
        with mock.patch.object(
            obj, "is_up_to_date", return_value=False
        ) as is_up_to_date_mock:
            with mock.patch.object(
                obj, "update_from_asset_data"
            ) as update_from_asset_data_mock:
                with mock.patch.object(obj, "save") as save_mock:
                    # Run the code to be tested!
                    self.view.update_object(TEST_ASSET_ID, obj)

        is_up_to_date_mock.assert_called_once_with(TEST_ASSET_DATA)
        update_from_asset_data_mock.assert_called_once_with(TEST_ASSET_DATA)
        save_mock.assert_called_once()
