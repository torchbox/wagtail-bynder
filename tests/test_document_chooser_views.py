from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse, reverse_lazy
from wagtail.test.utils import WagtailTestUtils

from testapp.factories import CustomDocumentFactory

from .utils import TEST_ASSET_ID


class TestDocumentChooseView(TestCase, WagtailTestUtils):
    url = reverse_lazy("wagtaildocs_chooser:choose")

    def test_view_loads_without_errors(self):
        user = self.create_test_user()
        self.client.force_login(user)
        response = self.client.get(str(self.url))
        self.assertEqual(response.status_code, 200)


class TestDocumentChosenView(TestCase, WagtailTestUtils):
    url = reverse_lazy("wagtaildocs_chooser:chosen", args=[TEST_ASSET_ID])

    def setUp(self):
        # Always log in as an admin user
        self.user = self.create_test_user()
        self.client.force_login(self.user)
        super().setUp()

    def test_creates_document_if_asset_id_not_recognised(self):
        # For expediency and predictability, have create_object()
        # return a test document instead of creating its own
        document = CustomDocumentFactory.create()

        with mock.patch(
            "wagtail_bynder.views.document.DocumentChosenView.create_object",
            return_value=document,
        ) as create_object_mock:
            response = self.client.get(str(self.url))

        create_object_mock.assert_called_once_with(TEST_ASSET_ID)

        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "step": "chosen",
                "result": {
                    "id": str(document.id),
                    "title": document.title,
                    "filename": mock.ANY,
                    "url": mock.ANY,
                    "edit_url": reverse("wagtaildocs:edit", args=[document.id]),
                },
            },
        )

    @mock.patch(
        "wagtail_bynder.views.document.DocumentChosenView.update_object",
    )
    def test_uses_existing_document_without_updating(self, update_object_mock):
        # Create an image with a matching bynder_id
        document = CustomDocumentFactory.create(bynder_id=TEST_ASSET_ID)

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
                    "id": str(document.id),
                    "title": document.title,
                    "filename": mock.ANY,
                    "url": mock.ANY,
                    "edit_url": reverse("wagtaildocs:edit", args=[document.id]),
                },
            },
        )

    @override_settings(BYNDER_SYNC_EXISTING_DOCUMENTS_ON_CHOOSE=True)
    @mock.patch(
        "wagtail_bynder.views.document.DocumentChosenView.update_object",
    )
    def test_uses_existing_image_and_updates_it(
        self, update_object_mock: mock.MagicMock
    ):
        # Create an image with a matching bynder_id
        document = CustomDocumentFactory.create(bynder_id=TEST_ASSET_ID)

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
                    "id": str(document.id),
                    "title": document.title,
                    "filename": mock.ANY,
                    "url": mock.ANY,
                    "edit_url": reverse("wagtaildocs:edit", args=[document.id]),
                },
            },
        )
