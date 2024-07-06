from unittest import mock

import responses

from django.db import IntegrityError
from django.http import HttpRequest
from django.test import TestCase
from django.utils.functional import cached_property
from django.views.generic.base import View
from testapp.factories import CustomImageFactory
from testapp.models import CustomImage
from wagtail_factories import ImageFactory

from wagtail_bynder.views.mixins import BynderAssetCopyMixin

from .utils import TEST_ASSET_ID, get_test_asset_data


TEST_ASSET_DATA = get_test_asset_data(id=TEST_ASSET_ID)


class BynderAssetCopyMixinTests(TestCase):
    def setUp(self):
        super().setUp()
        request = HttpRequest()
        request.method = ""
        request.path = "/"

        self.view = self.view_class()
        self.view.setup(request)

        # Mock out Bynder API calls
        responses.add(
            responses.GET,
            f"https://test-org.bynder.com/api/v4/media/{TEST_ASSET_ID}/",
            json=TEST_ASSET_DATA,
            status=200,
        )

    @cached_property
    def view_class(self) -> type[BynderAssetCopyMixin]:
        """
        Use the mixin to create a functioning view class
        that can be used in tests for this class.
        """

        class TestViewClass(BynderAssetCopyMixin, View):
            """A basic view class utilising BynderAssetCopyMixin"""

            model = CustomImage

        return TestViewClass

    @responses.activate
    def test_create_object(self):
        # After fetching the data from bynder, the method should create a
        # new object, call update_from_asset_data() to populate some
        # fields values, then save the changes.
        with (
            mock.patch.object(
                self.view.model, "update_from_asset_data"
            ) as update_from_asset_data_mock,
            mock.patch.object(self.view.model, "save") as save_mock,
        ):
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
        with (
            mock.patch.object(
                obj, "is_up_to_date", return_value=True
            ) as is_up_to_date_mock,
            mock.patch.object(
                obj, "update_from_asset_data"
            ) as update_from_asset_data_mock,
            mock.patch.object(obj, "save") as save_mock,
        ):
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
        with (
            mock.patch.object(
                obj, "is_up_to_date", return_value=False
            ) as is_up_to_date_mock,
            mock.patch.object(
                obj, "update_from_asset_data"
            ) as update_from_asset_data_mock,
            mock.patch.object(obj, "save") as save_mock,
        ):
            # Run the code to be tested!
            self.view.update_object(TEST_ASSET_ID, obj)

        is_up_to_date_mock.assert_called_once_with(TEST_ASSET_DATA)
        update_from_asset_data_mock.assert_called_once_with(TEST_ASSET_DATA)
        save_mock.assert_called_once()

    @responses.activate
    def test_create_object_clash_handling_after_update(self):
        # Create an image with a matching bynder_id
        existing = CustomImageFactory.create(bynder_id=TEST_ASSET_ID)

        # Trigger the test target directly
        with mock.patch.object(
            self.view.model, "update_from_asset_data"
        ) as update_from_asset_data_mock:
            result = self.view.create_object(TEST_ASSET_ID)

        # Check behavior and result
        update_from_asset_data_mock.assert_called_once_with(TEST_ASSET_DATA)
        self.assertEqual(result, existing)

    @responses.activate
    def test_create_object_clash_handling_on_save(self):
        def create_dupe_and_throw_integrity_error():
            CustomImageFactory.create(bynder_id=TEST_ASSET_ID)
            raise IntegrityError("bynder_id must be unique")

        fake_obj = mock.MagicMock()
        fake_obj.save = create_dupe_and_throw_integrity_error

        with (
            # Patch update_from_asset_data() to prevent download attempts
            # and other unnecessary work
            mock.patch.object(
                self.view.model,
                "update_from_asset_data",
            ),
            # Patch build_object_from_data to return a mock with a patched save() method
            mock.patch.object(
                self.view,
                "build_object_from_data",
                return_value=fake_obj,
            ),
        ):
            # The IntegrityError should be captured, and the object
            # that was saved previously should be found and returned
            result = self.view.create_object(TEST_ASSET_ID)

        self.assertEqual(result.bynder_id, TEST_ASSET_ID)

    @responses.activate
    def test_create_object_clash_handling_on_save_when_bynder_id_match_not_found(self):
        def throw_integrity_error():
            raise IntegrityError("Some other field must be unique")

        fake_obj = mock.MagicMock()
        fake_obj.save = throw_integrity_error

        with (
            # Patch update_from_asset_data() to prevent download attempts
            # and other unnecessary work
            mock.patch.object(
                self.view.model,
                "update_from_asset_data",
            ),
            # Patch build_object_from_data to return a mock with a patched save() method
            mock.patch.object(
                self.view,
                "build_object_from_data",
                return_value=fake_obj,
            ),
            self.assertRaises(IntegrityError),
        ):
            # With no 'bynder_id' match to be found, the error is allowed
            # to bubble up
            self.view.create_object(TEST_ASSET_ID)
