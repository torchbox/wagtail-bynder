from django import template
from django.conf import settings
from django.urls import reverse

from wagtail_bynder import get_video_model


register = template.Library()


@register.simple_tag
def bynder_domain():
    return getattr(settings, "BYNDER_DOMAIN", "")


@register.simple_tag
def bynder_compactview_api_token():
    return getattr(settings, "BYNDER_COMPACTVIEW_API_TOKEN", "")


@register.simple_tag
def get_image_chosen_base_url():
    url = reverse("wagtailimages_chooser:choose")
    if not url.endswith("/"):
        url += "/"
    return url


@register.simple_tag
def get_document_chosen_base_url():
    url = reverse("wagtaildocs_chooser:choose")
    if not url.endswith("/"):
        url += "/"
    return url


@register.simple_tag
def get_video_chosen_base_url():
    model = get_video_model()
    if model:
        url = model.snippet_viewset.chooser_viewset.get_url_name("choose")
        if not url.endswith("/"):
            url += "/"
        return url
    return ""
