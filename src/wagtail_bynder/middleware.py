from typing import TYPE_CHECKING

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from wagtail.admin.auth import require_admin_access

from wagtail_bynder.views import document as document_views
from wagtail_bynder.views import image as image_views


if TYPE_CHECKING:
    from django.views.generic import View


class PatchWagtailURLsMiddleware(MiddlewareMixin):
    @classmethod
    def get_overrides(cls) -> dict[str, type["View"]]:
        overrides = {}
        if getattr(settings, "BYNDER_DOMAIN", ""):
            overrides.update(
                {
                    "wagtailimages_chooser:choose": image_views.ImageChooseView,
                    "wagtailimages_chooser:chosen": image_views.ImageChosenView,
                    "wagtaildocs_chooser:choose": document_views.DocumentChooseView,
                    "wagtaildocs_chooser:chosen": document_views.DocumentChosenView,
                }
            )
            if getattr(settings, "BYNDER_DISABLE_WAGTAIL_EDITING_FOR_ASSETS", False):
                overrides.update(
                    {
                        "wagtailimages:edit": image_views.ImageEditView,
                        "wagtailimages:delete": image_views.ImageDeleteView,
                        "wagtaildocs:edit": document_views.DocumentEditView,
                        "wagtaildocs:delete": document_views.DocumentDeleteView,
                    }
                )
        return overrides

    def process_view(self, request, view_func, view_args, view_kwargs):
        overrides = self.get_overrides()
        replacement_view_class = overrides.get(request.resolver_match.view_name)
        if replacement_view_class:
            view = require_admin_access(replacement_view_class.as_view())
            return view(request, *view_args, **view_kwargs)
