from django.utils.functional import cached_property
from wagtail.blocks import ChooserBlock


class VideoChooserBlock(ChooserBlock):
    @cached_property
    def target_model(self):
        from wagtail_bynder import get_video_model

        return get_video_model()

    @cached_property
    def widget(self):
        from wagtail_bynder.widgets import AdminVideoChooser

        return AdminVideoChooser()

    def render_basic(self, value, context=None):
        return ""

    class Meta:
        icon = "media"
