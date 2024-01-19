from django import forms
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from wagtail.admin.staticfiles import versioned_static
from wagtail.admin.widgets import BaseChooser, BaseChooserAdapter
from wagtail.telepath import register

from wagtail_bynder import get_video_model


class AdminVideoChooser(BaseChooser):
    choose_one_text = _("Choose a video")
    choose_another_text = _("Change video")
    link_to_chosen_text = _("Edit this video")
    chooser_modal_url_name = "bynder_video_chooser:choose"
    icon = "media"
    classname = "video-chooser"
    js_constructor = "VideoChooser"

    def __init__(self, **kwargs):
        self.model = get_video_model()
        super().__init__(**kwargs)

    def get_chooser_modal_url(self):
        return reverse(
            self.model.snippet_viewset.chooser_viewset.get_url_name("choose")
        )

    @property
    def media(self):
        return forms.Media(
            js=[
                versioned_static("wagtailsnippets/js/snippet-chooser.js"),
                versioned_static("bynder/js/video-chooser.js"),
            ]
        )


class VideoChooserAdapter(BaseChooserAdapter):
    js_constructor = "wagtail_bynder.widgets.VideoChooser"

    @cached_property
    def media(self):
        return forms.Media(
            js=[
                versioned_static("bynder/js/video-chooser-telepath.js"),
            ]
        )


register(VideoChooserAdapter(), AdminVideoChooser)
