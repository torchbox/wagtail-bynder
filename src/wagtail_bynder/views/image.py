from typing import TYPE_CHECKING

from django.conf import settings
from django.utils.html import format_html
from wagtail.admin.modal_workflow import render_modal_workflow
from wagtail.images import get_image_model
from wagtail.images.views import chooser as chooser_views
from wagtail.images.views.images import DeleteView, EditView

from wagtail_bynder.exceptions import BynderAssetDownloadError

from .mixins import BynderAssetCopyMixin, RedirectToBynderMixin


if TYPE_CHECKING:
    from django.http import HttpRequest, JsonResponse


class ImageEditView(RedirectToBynderMixin, EditView):
    pass


class ImageDeleteView(RedirectToBynderMixin, DeleteView):
    pass


class ImageChooseView(chooser_views.ImageChooseView):
    choose_one_text = chooser_views.ImageChooserViewSet.choose_one_text
    choose_another_text = chooser_views.ImageChooserViewSet.choose_another_text
    page_title = choose_one_text
    permission_policy = chooser_views.ImageChooserViewSet.permission_policy
    icon = chooser_views.ImageChooserViewSet.icon
    template_name = "wagtailadmin/chooser/chooser-bynder.html"

    def __init__(self, *args, **kwargs):
        self.create_url_name = chooser_views.viewset.get_url_name("create")
        self.results_url_name = chooser_views.viewset.get_url_name("choose_results")
        self.collections = []
        super().__init__(*args, **kwargs)


class ImageChosenView(BynderAssetCopyMixin, chooser_views.ImageChosenView):
    model = get_image_model()

    def get(self, request: "HttpRequest", pk: str) -> "JsonResponse":
        try:
            try:
                obj = self.model.objects.get(bynder_id=pk)
            except self.model.DoesNotExist:
                obj = self.create_object(pk)
            else:
                if getattr(settings, "BYNDER_SYNC_EXISTING_IMAGES_ON_CHOOSE", False):
                    self.update_object(pk, obj)
        except BynderAssetDownloadError as e:
            # Return error step to display message in the chooser modal
            return render_modal_workflow(
                request,
                None,
                None,
                None,
                json_data={
                    "step": "error",
                    "error_message": format_html(
                        "<strong>Failed to download image from Bynder:</strong> {error} Please try again later.",
                        error=e,
                    ),
                },
            )
        return self.get_chosen_response(obj)
