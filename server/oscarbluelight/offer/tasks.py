from __future__ import annotations

from datetime import datetime
import logging

from django.db import connection, transaction

from ..tasks import task
from .applicator import pricing_cache_ns
from .models import RangeProductSet, RangeProductSetRefreshLog
from .signals import range_product_set_view_updated

logger = logging.getLogger(__name__)


@task
def recalculate_offer_application_totals() -> None:
    from .models import ConditionalOffer

    ConditionalOffer.recalculate_offer_application_totals()


@task
@transaction.atomic
def refresh_rps_view(requested_on_timestamp: float) -> None:
    # Set a short lock timeout to prevent multiple of these tasks from running (and blocking) simultaneously
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL lock_timeout = '1s'")
    # Figure out if a refresh is actually needed. E.g. If the vioew has already
    # been refreshed since this refresh request was made, then we don't need to
    # refresh the view again.
    requested_on_dt = datetime.fromtimestamp(requested_on_timestamp)
    if not RangeProductSetRefreshLog.is_refresh_needed(requested_on_dt):
        logger.info("Skipping redundant RangeProductSet view refresh")
        return
    # Refresh the view
    RangeProductSet.refresh(concurrently=True)
    RangeProductSetRefreshLog.log_view_refresh()

    # Invalidate the pricing cache (since range membership may affect pricing)
    def _on_commit() -> None:
        pricing_cache_ns.invalidate()
        range_product_set_view_updated.send(sender=RangeProductSet)

    transaction.on_commit(_on_commit)
    logger.info("Finished refreshing RangeProductSet view")
