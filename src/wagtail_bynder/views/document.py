from typing import TYPE_CHECKING

from django.conf import settings
from django.views.generic import UpdateView
from wagtail import VERSION as WAGTAIL_VERSION
from wagtail.admin.modal_workflow import render_modal_workflow
from wagtail.documents import get_document_model
from wagtail.documents.views import chooser as chooser_views


if WAGTAIL_VERSION < (6, 3):
    from wagtail.documents.views.documents import DeleteView
    from wagtail.documents.views.documents import edit as document_edit
else:
    from wagtail.documents.views.documents import DeleteView, EditView

from wagtail_bynder.exceptions import BynderAssetDownloadError

from .mixins import BynderAssetCopyMixin, RedirectToBynderMixin


if TYPE_CHECKING:
    from django.http import HttpRequest, JsonResponse


if WAGTAIL_VERSION < (6, 3):

    class ClassBasedDocumentEditView(UpdateView):
        """
        A class-based view that mimics the behaviour of wagtail's function-based
        document edit view, and can be extended with view mixins.
        """

        # TODO: Use class from Wagtail once the documents app views are refactored
        model = get_document_model()
        pk_url_kwarg = "document_id"

        def get(self, request, *args, **kwargs):
            return document_edit(request, *args, **kwargs)

        def post(self, request, *args, **kwargs):
            return document_edit(request, *args, **kwargs)

    class DocumentEditView(RedirectToBynderMixin, ClassBasedDocumentEditView):
        pass
else:

    class DocumentEditView(RedirectToBynderMixin, EditView):
        pass


class DocumentDeleteView(RedirectToBynderMixin, DeleteView):
    pass


class DocumentChooseView(chooser_views.DocumentChooseView):
    choose_one_text = chooser_views.DocumentChooserViewSet.choose_one_text
    choose_another_text = chooser_views.DocumentChooserViewSet.choose_another_text
    page_title = choose_one_text
    permission_policy = chooser_views.DocumentChooserViewSet.permission_policy
    icon = chooser_views.DocumentChooserViewSet.icon
    template_name = "wagtailadmin/chooser/chooser-bynder.html"

    register_widget = False

    def __init__(self, *args, **kwargs):
        self.create_url_name = chooser_views.viewset.get_url_name("create")
        self.results_url_name = chooser_views.viewset.get_url_name("choose_results")
        self.collections = []
        super().__init__(*args, **kwargs)


class DocumentChosenView(BynderAssetCopyMixin, chooser_views.DocumentChosenView):
    model = get_document_model()

    def get(self, request: "HttpRequest", pk: str) -> "JsonResponse":
        try:
            try:
                obj = self.model.objects.get(bynder_id=pk)
            except self.model.DoesNotExist:
                obj = self.create_object(pk)
            else:
                if getattr(settings, "BYNDER_SYNC_EXISTING_DOCUMENTS_ON_CHOOSE", False):
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
                    "error_message": f"<strong>Failed to download document from Bynder:</strong> {str(e)} Please try again later.",
                },
            )
        return self.get_chosen_response(obj)
