from typing import TYPE_CHECKING

from django.conf import settings
from django.db import IntegrityError
from django.shortcuts import redirect

from wagtail_bynder.models import BynderAssetMixin
from wagtail_bynder.utils import get_bynder_client


if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


class BynderAssetCopyMixin:

    model = type[BynderAssetMixin]

    def create_object(self, asset_id: str) -> BynderAssetMixin:
        client = get_bynder_client()
        obj: BynderAssetMixin = self.model(bynder_id=asset_id)
        data = client.asset_bank_client.media_info(asset_id)
        obj.update_from_asset_data(data)
        try:
            obj.save()
        except IntegrityError as ie:
            try:
                # If the 'bynder_id' is already taken, find the existing object to return
                existing = self.model.objects.get(bynder_id=asset_id)
            except self.model.DoesNotExist:
                # The error must relate to a different field, so throw the original error
                raise ie from None
            else:
                # If the new file was copied to media storage, ensure it is deleted
                try:
                    if obj.file.path != existing.file.path:
                        obj.file.delete()
                except (ValueError, FileNotFoundError):
                    pass
                return existing
        else:
            return obj

    def update_object(self, asset_id: str, obj: BynderAssetMixin) -> BynderAssetMixin:
        client = get_bynder_client()
        data = client.asset_bank_client.media_info(asset_id)
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
