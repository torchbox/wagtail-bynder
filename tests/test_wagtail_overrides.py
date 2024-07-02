from contextlib import contextmanager

from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import NoReverseMatch, reverse
from wagtail.test.utils import WagtailTestUtils

from wagtail_bynder.middleware import PatchWagtailURLsMiddleware


class TestPatchWagtailURLsMiddleware(SimpleTestCase):
    urls = (
        ("wagtailimages_chooser:choose", []),
        ("wagtailimages_chooser:chosen", ["1"]),
        ("wagtaildocs_chooser:choose", []),
        ("wagtaildocs_chooser:chosen", ["1"]),
        ("wagtailimages:edit", ["1"]),
        ("wagtaildocs:edit", ["1"]),
    )

    @contextmanager
    def assertNotRaises(self, exc_type):
        try:
            yield None
        except exc_type as e:
            raise self.failureException(f"{exc_type.__name__} raised") from e

    def test_wagtail_views_names_have_not_changed(self):
        """
        This app depends on overriding some specific Wagtail views, which are identified by url name.
        This test ensures that the current version of Wagtail is using the same view names, because
        if they change, our custom views will not be loaded.
        """
        for url_name, args in self.urls:
            with self.subTest(url_name=url_name), self.assertNotRaises(NoReverseMatch):
                reverse(url_name, args=args)

    @override_settings(
        BYNDER_DISABLE_WAGTAIL_EDITING_FOR_ASSETS=True,
    )
    def test_same_view_names_are_used_by_middleware(self):
        overrides = PatchWagtailURLsMiddleware.get_overrides()
        for url in self.urls:
            with self.subTest(url_name=url[0]):
                self.assertIn(url[0], overrides)

    @override_settings(
        BYNDER_DISABLE_WAGTAIL_EDITING_FOR_ASSETS=True,
    )
    def test_edit_views_are_overridden_when_required(self):
        overrides = PatchWagtailURLsMiddleware.get_overrides()
        self.assertIn("wagtailimages:edit", overrides)
        self.assertIn("wagtaildocs:edit", overrides)

    @override_settings(
        BYNDER_DISABLE_WAGTAIL_EDITING_FOR_ASSETS=False,
    )
    def test_edit_views_are_not_overridden_when_not_required(self):
        overrides = PatchWagtailURLsMiddleware.get_overrides()
        self.assertNotIn("wagtailimages:edit", overrides)
        self.assertNotIn("wagtaildocs:edit", overrides)


class BaseTemplateOverrideTests(TestCase, WagtailTestUtils):
    def test_admin_base_template_override_is_working(self):
        """
        We override the `admin_base.html` template to inject some JS into all Wagtail
        admin pages, allowing choosers to be loaded on any page. This test ensures
        that our override template is actually picked up and used by Wagtail.
        """
        user = self.create_test_user()
        self.client.force_login(user)
        response = self.client.get(reverse("wagtailadmin_home"))
        self.assertTemplateUsed(response, "wagtailadmin/admin_base.html")

        html = response.content.decode("utf-8")

        self.assertIn(
            f'<script src="{ settings.STATIC_URL }wagtailadmin/js/chooser-modal-handler-factory.js">',
            html,
        )
        self.assertIn(
            f'<script src="{ settings.STATIC_URL }bynder/js/compactview-v4.js">',
            html,
        )
