from unittest import mock

from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse, reverse_lazy
from testapp.factories import CustomImageFactory
from wagtail.test.utils import WagtailTestUtils

from .utils import TEST_ASSET_ID


class TestImageChooseView(TestCase, WagtailTestUtils):
    url = reverse_lazy("wagtailimages_chooser:choose")

    def test_view_loads_without_errors(self):
        user = self.create_test_user()
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)


class TestImageChosenView(TransactionTestCase, WagtailTestUtils):
    url = reverse_lazy("wagtailimages_chooser:chosen", args=[TEST_ASSET_ID])

    def setUp(self):
        # Always log in as an admin user
        self.user = self.create_test_user()
        self.client.force_login(self.user)
        super().setUp()

    def test_creates_image_if_asset_id_not_recognised(self):
        # For expediency and predictability, have create_object()
        # return a test image instead of creating its own
        image = CustomImageFactory.create()
        with mock.patch(
            "wagtail_bynder.views.image.ImageChosenView.create_object",
            return_value=image,
        ) as create_object_mock:
            response = self.client.get(str(self.url))

        # Assertions
        create_object_mock.assert_called_once()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "step": "chosen",
                "result": {
                    "id": str(image.id),
                    "title": image.title,
                    "preview": mock.ANY,
                    "edit_url": reverse("wagtailimages:edit", args=[image.id]),
                },
            },
        )

    @mock.patch("wagtail_bynder.views.image.ImageChosenView.update_object")
    def test_uses_existing_image_without_updating(self, update_object_mock):
        # Create an image with a matching bynder_id
        image = CustomImageFactory.create(bynder_id=TEST_ASSET_ID)

        # Make a request to the view
        response = self.client.get(str(self.url))

        # update_object() should NOT have been called, because
        # 'refresh on choose' is disabled by default
        update_object_mock.assert_not_called()

        # Check response content
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "step": "chosen",
                "result": {
                    "id": str(image.id),
                    "title": image.title,
                    "preview": mock.ANY,
                    "edit_url": reverse("wagtailimages:edit", args=[image.id]),
                },
            },
        )

    @override_settings(BYNDER_SYNC_EXISTING_IMAGES_ON_CHOOSE=True)
    @mock.patch("wagtail_bynder.views.image.ImageChosenView.update_object")
    def test_uses_existing_image_and_updates_it(self, update_object_mock):
        # Create an image with a matching bynder_id
        image = CustomImageFactory.create(bynder_id=TEST_ASSET_ID)

        # Make a request to the view
        response = self.client.get(str(self.url))

        # update_object() should have been called this time
        update_object_mock.assert_called_once()

        # Check response content
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "step": "chosen",
                "result": {
                    "id": str(image.id),
                    "title": image.title,
                    "preview": mock.ANY,
                    "edit_url": reverse("wagtailimages:edit", args=[image.id]),
                },
            },
        )
