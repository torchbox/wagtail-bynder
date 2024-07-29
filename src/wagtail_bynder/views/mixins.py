import contextlib

from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.db import IntegrityError
from django.shortcuts import redirect

from wagtail_bynder.models import BynderAssetMixin
from wagtail_bynder.utils import get_bynder_client


if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


class BynderAssetCopyMixin:
    model = type[BynderAssetMixin]

    def setup(self, *args, **kwargs):
        super().setup(*args, **kwargs)
        bynder_client = get_bynder_client()
        self.asset_client = bynder_client.asset_bank_client

    def build_object_from_data(self, asset_data: dict[str, Any]) -> BynderAssetMixin:
        obj = self.model(bynder_id=asset_data["id"])
        obj.update_from_asset_data(asset_data)
        return obj

    def create_object(self, asset_id: str) -> BynderAssetMixin:
        data = self.asset_client.media_info(asset_id)
        obj = self.build_object_from_data(data)
        try:
            # If the asset finished saving in a different thread during the download/update process,
            # return the pre-existing object
            return self.model.objects.get(bynder_id=asset_id)
        except self.model.DoesNotExist:
            try:
                # Save the new object, triggering transfer of the file to media storage
                obj.save()
            except IntegrityError as integrity_error:
                # It's likely the asset finished saving in a different thread while the file was
                # being transferred to media storage
                try:
                    # Lookup the existing object
                    pre_existing = self.model.objects.get(bynder_id=asset_id)
                except self.model.DoesNotExist:
                    # The IntegrityError must have been caused by a custom field, so reraise
                    raise integrity_error from None
                else:
                    # If the newly-downloaded file was successfully copied to storage, delete it
                    with contextlib.suppress(ValueError, FileNotFoundError):
                        if obj.file.path != pre_existing.file.path:
                            obj.file.delete()
                return pre_existing
        return obj

    def update_object(self, asset_id: str, obj: BynderAssetMixin) -> BynderAssetMixin:
        data = self.asset_client.media_info(asset_id)
        if not obj.is_up_to_date(data):
            obj.update_from_asset_data(data)
            obj.save()
        return obj


class RedirectToBynderMixin:
    def setup(self, request, *args, **kwargs) -> None:
        if self.pk_url_kwarg != "pk":
            kwargs["pk"] = kwargs[self.pk_url_kwarg]
        super().setup(request, *args, **kwargs)

    def get(self, request: "HttpRequest", *args, **kwargs) -> "HttpResponse":
        self.object = self.get_object()
        if asset_id := self.object.bynder_id:
            return redirect(
                "https://" + settings.BYNDER_DOMAIN + f"/media/?mediaId={asset_id}"
            )
        return super().get(request, *args, **kwargs)

    def post(self, request: "HttpRequest", *args, **kwargs) -> "HttpResponse":
        self.object = self.get_object()
        if asset_id := self.object.bynder_id:
            return redirect(
                "https://" + settings.BYNDER_DOMAIN + f"/media/?mediaId={asset_id}"
            )
        return super().post(request, *args, **kwargs)
