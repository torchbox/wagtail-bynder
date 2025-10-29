from typing import TYPE_CHECKING

from django.conf import settings
from django.views.generic import UpdateView
from wagtail import VERSION as WAGTAIL_VERSION
from wagtail.admin.modal_workflow import render_modal_workflow
from wagtail.images import get_image_model
from wagtail.images.views import chooser as chooser_views


if WAGTAIL_VERSION < (6, 3):
    from wagtail.images.views.images import DeleteView
    from wagtail.images.views.images import edit as image_edit
else:
    from wagtail.images.views.images import DeleteView, EditView

from wagtail_bynder.exceptions import BynderAssetDownloadError

from .mixins import BynderAssetCopyMixin, RedirectToBynderMixin


if TYPE_CHECKING:
    from django.http import HttpRequest, JsonResponse


if WAGTAIL_VERSION < (6, 3):

    class ClassBasedWagtailImageEditView(UpdateView):
        """
        A class-based view that mimics the behaviour of wagtail's function-based
        image edit view, and can be extended with view mixins.
        """

        # TODO: Use class from Wagtail once the image app views are refactored
        model = get_image_model()
        pk_url_kwarg = "image_id"

        def get(self, request, *args, **kwargs):
            return image_edit(request, *args, **kwargs)

        def post(self, request, *args, **kwargs):
            return image_edit(request, *args, **kwargs)

    class ImageEditView(RedirectToBynderMixin, ClassBasedWagtailImageEditView):
        pass
else:

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
                    "error_message": f"<strong>Failed to download image from Bynder:</strong> {str(e)} Please try again later.",
                },
            )
        return self.get_chosen_response(obj)
