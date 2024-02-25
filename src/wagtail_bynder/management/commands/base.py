from collections.abc import Generator
from datetime import datetime
from typing import Any

from django.core.management.base import BaseCommand
from django.db.models import Model
from django.db.models.base import ModelBase
from django.db.models.query import Q, QuerySet
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from wagtail_bynder.utils import get_bynder_client


class BaseBynderSyncCommand(BaseCommand):
    bynder_asset_type: str = ""
    page_size: int = 200
    model: ModelBase = None

    def add_arguments(self, parser):
        parser.add_argument(
            "--minutes",
            type=int,
            help=_(
                "The number of minutes into the past to look for asset "
                "modifications."
            ),
        )
        parser.add_argument(
            "--hours",
            type=int,
            help=_(
                "The number of hours into the past to look for asset "
                "modifications (takes precedence over 'minutes')"
            ),
        )
        parser.add_argument(
            "--days",
            type=int,
            help=_(
                "The number of days in the past to look for asset "
                "modifications (takes precedence over 'hours' and 'minutes')"
            ),
        )

    def handle(self, *args, **options):
        # Default timespan to 1 day (1440 minutes)
        minutes = options.get("minutes")
        hours = options.get("hours")
        days = options.get("days")
        if days:
            timespan = timezone.timedelta(days=days)
            timespan_desc = f"{days} day(s)"
        elif hours:
            timespan = timezone.timedelta(hours=hours)
            timespan_desc = f"{hours} hour(s)"
        elif minutes:
            timespan = timezone.timedelta(minutes=minutes)
            timespan_desc = f"{minutes} minute(s)"
        else:
            timespan = timezone.timedelta(days=1)
            timespan_desc = "1 day"

        self.date_modified_from = datetime.utcnow() - timespan

        self.stdout.write(
            f"Looking for {self.bynder_asset_type or 'all'} assets modified within the last {timespan_desc}"
        )

        self.batch_count = 1
        self.bynder_client = get_bynder_client()
        asset_dict: dict[str, dict[str, Any]] = {}

        for asset in self.get_assets():
            # Gather asset details into a large dict, using the 'id' as the key
            asset_dict[asset["id"]] = asset
            # Process the gathered assets once the batch reaches a certain size
            if len(asset_dict) == self.page_size:
                self.process_batch(asset_dict)
                # Clear this batch to start another
                asset_dict.clear()

        # Process any remaining assets
        if asset_dict:
            self.process_batch(asset_dict)

    def get_assets(self) -> Generator[dict[str, Any]]:
        """
        A generator method that yields all relevant Bynder assets, one at a time.
        It silently uses pagination to ensure all possible assets are returned.
        """
        page = 1
        while True:
            query = {
                "dateModified": self.date_modified_from.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "orderBy": "dateModified desc",
                "page": page,
                "limit": self.page_size,
            }
            if self.bynder_asset_type:
                query["type"] = self.bynder_asset_type
            results = self.bynder_client.asset_bank_client.media_list(query)
            if not results:
                break
            yield from results
            if len(results) < self.page_size:
                break
            page += 1
        return

    def process_batch(self, assets: dict[str, dict[str, Any]]) -> None:
        """
        Identifies and updates (where needed) model objects to reflect changes
        in the supplied 'batch' of Bynder assets.
        """
        self.stdout.write(
            f"Processing batch {self.batch_count} ({len(assets)} assets)..."
        )
        self.batch_count += 1

        stale = self.get_stale_objects(assets)
        self.stdout.write(f"{len(stale)} stale objects were found for this batch.")
        for obj in stale:
            data = assets.get(obj.bynder_id)
            self.update_object(obj, data)

    def get_stale_objects(self, assets: dict[str, dict[str, Any]]) -> QuerySet:
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
