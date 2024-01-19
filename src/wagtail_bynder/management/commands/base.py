from collections.abc import Generator
from datetime import datetime
from typing import Any

from django.core.management.base import BaseCommand
from django.db.models import Model
from django.db.models.base import ModelBase
from django.db.models.query import Q, QuerySet
from django.utils import timezone
from django.utils.functional import cached_property

from wagtail_bynder.utils import get_bynder_client


class BaseBynderSyncCommand(BaseCommand):
    bynder_asset_type: str = ""
    page_size: int = 200
    model: ModelBase = None

    # Limits how far in the past to look for modified assets
    # TODO: Make this a command-line option
    modified_within_days: int = 1

    def handle(self, *args, **options):
        self.bynder_client = get_bynder_client()
        asset_dict: dict[str, dict[str, Any]] = {}

        for asset in self.get_assets():
            # Gather asset details into a large dict, using the 'id' as the key
            asset_dict[asset["id"]] = asset
            # Process the gathered assets once the batch reaches a certain size
            if len(asset_dict) == self.page_size:
                self.update_outdated_objects(asset_dict)
                # Clear this batch to start another
                asset_dict.clear()

        # Process any remaining assets
        if asset_dict:
            self.update_outdated_objects(asset_dict)

    @cached_property
    def min_date_modified(self) -> timezone.datetime:
        return timezone.now() - timezone.timedelta(days=self.modified_within_days)

    def get_assets(self) -> Generator[dict[str, Any]]:
        """
        A generator method that yields all relevant Bynder assets, one at a time.
        It silently uses pagination to ensure all possible assets are returned.
        """
        page = 1
        while True:
            query = {
                "dateModified": self.min_date_modified,
                "orderBy": "dateModified desc",
                "page": page,
                "limit": self.page_size,
            }
            if self.bynder_asset_type:
                query["type"] = self.bynder_asset_type
            results = self.bynder_client.asset_bank_client.media_list(query)
            if not results:
                break
            for asset in results:
                yield asset
            page += 1

    def get_outdated_objects(self, assets: dict[str, dict[str, Any]]) -> QuerySet:
        """
        Return a queryset of model instances that represent items in the supplied
        batch of assets, and are out-of-sync with the data in Bynder (and
        therefore should be updated).
        """
        q = Q()
        for id, asset in assets.items():
            # excluding anything where 'bynder_last_modified' value is equal to
            # that from Bynder (which means it is already up-to-date)
            q |= Q(bynder_id=id, bynder_last_modified__lt=asset["dateModified"])
        return self.model.objects.filter(q)

    def update_outdated_objects(self, assets: dict[str, dict[str, Any]]) -> None:
        """
        Identifies and updates (where needed) model objects to reflect changes
        in the supplied 'batch' of Bynder assets.
        """
        for obj in self.get_outdated_objects(assets):
            data = assets.get(obj.bynder_id)
            self.update_object(obj, data)

    def update_object(self, obj: Model, asset_data: dict[str:Any]) -> None:
        self.stdout.write("\n")
        self.stdout.write(f"Updating object for asset '{asset_data['id']}'")
        time_diff = (
            datetime.fromisoformat(asset_data["dateModified"])
            - obj.bynder_last_modified
        )
        self.stdout.write(f"{repr(obj)} is behind by: {time_diff}")
        self.stdout.write("The latest data from Bynder is:")
        for key, value in asset_data.items():
            self.stdout.write(f"  {key}: {value}")
        self.stdout.write("-" * 80)

        obj.update_from_asset_data(asset_data)
        obj.save()
