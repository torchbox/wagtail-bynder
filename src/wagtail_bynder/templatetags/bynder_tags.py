from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def bynder_domain():
    return getattr(settings, "BYNDER_DOMAIN", "")


@register.simple_tag
def bynder_compactview_api_token():
    return getattr(settings, "BYNDER_COMPACTVIEW_API_TOKEN", "")
