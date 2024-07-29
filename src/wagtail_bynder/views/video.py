from typing import TYPE_CHECKING

from django.conf import settings
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from wagtail.admin.views.generic.chooser import ChooseView
from wagtail.snippets.views.chooser import SnippetChooserViewSet, SnippetChosenView
from wagtail.snippets.views.snippets import EditView, SnippetViewSet

from wagtail_bynder import get_video_model

from .mixins import BynderAssetCopyMixin, RedirectToBynderMixin


if TYPE_CHECKING:
    from django.http import HttpRequest, JsonResponse


class VideoEditView(EditView, RedirectToBynderMixin):
    model = get_video_model()
    pk_url_kwarg = "pk"


class VideoChooseView(ChooseView):
    filter_form_class = None
    page_title = _("Choose")
    template_name = "wagtailadmin/chooser/chooser-bynder.html"

    @property
    def page_subtitle(self):
        return self.model._meta.verbose_name


class VideoChosenView(BynderAssetCopyMixin, SnippetChosenView):
    def get(self, request: "HttpRequest", pk: str) -> "JsonResponse":
        try:
            obj = self.model.objects.get(bynder_id=pk)
        except self.model.DoesNotExist:
            obj = self.create_object(pk)
        else:
            if getattr(settings, "BYNDER_SYNC_EXISTING_VIDEOS_ON_CHOOSE", False):
                self.update_object(pk, obj)
        return self.get_chosen_response(obj)


class VideoChooserViewSet(SnippetChooserViewSet):
    choose_one_text = _("Choose a video")
    choose_another_text = _("Choose another video")
    edit_item_text = _("Edit this video")

    choose_view_class = VideoChooseView
    chosen_view_class = VideoChosenView

    @cached_property
    def widget_class(self):
        from wagtail_bynder.widgets import AdminVideoChooser

        return AdminVideoChooser(icon=self.icon)


class VideoViewSet(SnippetViewSet):
    icon = "media"
    edit_view_class = VideoEditView
    chooser_viewset_class = VideoChooserViewSet
    chooser_per_page = 50
    list_display = ["title", "bynder_id", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        self.model = get_video_model()
        super().__init__(*args, **kwargs)
