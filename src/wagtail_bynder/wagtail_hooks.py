from django.conf import settings
from django.templatetags.static import static
from django.utils.html import format_html
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.documents.wagtail_hooks import DocumentsSummaryItem
from wagtail.images.wagtail_hooks import ImagesSummaryItem
from wagtail.snippets.models import register_snippet

from wagtail_bynder import get_video_model
from wagtail_bynder.views.video import VideoViewSet


@hooks.register("construct_main_menu")
def hide_image_and_document_menu_items(request, menu_items):
    if domain := getattr(settings, "BYNDER_DOMAIN", ""):
        # Remove "Images" and "Documents" menu items
        menu_items[:] = [
            item for item in menu_items if item.name not in ("documents", "images")
        ]
        # Add a Bynder on in their place
        menu_items.insert(
            0,
            MenuItem(
                label="Manage assets",
                url=f"https://{domain}",
                classname="",
                icon_name="image",
                name="bynder",
                attrs={
                    "target": "_blank",
                    "title": "Manage assets in Bynder. Links open in a new tab.",
                },
                order=1000,
            ),
        )


@hooks.register("construct_homepage_summary_items")
def hide_image_and_document_summary_items(request, summary_items):
    if getattr(settings, "BYNDER_DOMAIN", ""):
        # Remove "Images" and "Documents" summary items
        summary_items[:] = [
            item
            for item in summary_items
            if not isinstance(item, ImagesSummaryItem | DocumentsSummaryItem)
        ]


@hooks.register("insert_editor_js")
def editor_js():
    if get_video_model():
        return format_html(
            """
            <script src="{0}"></script>
            """,
            static("bynder/js/video-chooser-modal.js"),
        )


if get_video_model():
    try:  # noqa: SIM105
        register_snippet(VideoViewSet)
    except Exception:  # noqa: S110
        pass
