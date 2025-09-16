from typing import TYPE_CHECKING

from django.conf import settings
from wagtail.documents import get_document_model
from wagtail.documents.views import chooser as chooser_views
from wagtail.documents.views.documents import DeleteView, EditView

from .mixins import BynderAssetCopyMixin, RedirectToBynderMixin


if TYPE_CHECKING:
    from django.http import HttpRequest, JsonResponse


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
            obj = self.model.objects.get(bynder_id=pk)
        except self.model.DoesNotExist:
            obj = self.create_object(pk)
        else:
            if getattr(settings, "BYNDER_SYNC_EXISTING_DOCUMENTS_ON_CHOOSE", False):
                self.update_object(pk, obj)
        return self.get_chosen_response(obj)
