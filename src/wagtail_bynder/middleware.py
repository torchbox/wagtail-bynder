from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from wagtail.admin.auth import require_admin_access

from wagtail_bynder.views import document as document_views
from wagtail_bynder.views import image as image_views


class PatchWagtailURLsMiddleware(MiddlewareMixin):
    @classmethod
    def get_overrides(cls) -> dict[str, callable]:
        overrides = {}
        if getattr(settings, "BYNDER_DOMAIN", ""):
            overrides.update(
                {
                    "wagtailimages_chooser:choose": image_views.ImageChooseView.as_view(),
                    "wagtailimages_chooser:chosen": image_views.ImageChosenView.as_view(),
                    "wagtaildocs_chooser:choose": document_views.DocumentChooseView.as_view(),
                    "wagtaildocs_chooser:chosen": document_views.DocumentChosenView.as_view(),
                }
            )
            if getattr(settings, "BYNDER_DISABLE_WAGTAIL_EDITING_FOR_ASSETS", False):
                overrides.update(
                    {
                        "wagtailimages:edit": image_views.ImageEditView.as_view(),
                        "wagtailimages:delete": image_views.ImageDeleteView.as_view(),
                        "wagtaildocs:edit": document_views.DocumentEditView.as_view(),
                        "wagtaildocs:delete": document_views.DocumentDeleteView.as_view(),
                    }
                )
        return overrides

    def process_view(self, request, view_func, view_args, view_kwargs):
        overrides = self.get_overrides()
        replacement_view = overrides.get(request.resolver_match.view_name)
        if replacement_view:
            view = require_admin_access(replacement_view)
            return view(request, *view_args, **view_kwargs)
