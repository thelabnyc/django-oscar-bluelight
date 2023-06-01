from __future__ import absolute_import
from datetime import datetime
from django.db import connection, transaction
from celery import shared_task
from oscar.core.loading import get_model
from .applicator import pricing_cache_ns
from .signals import range_product_set_view_updated
import logging

RangeProductSet = get_model("offer", "RangeProductSet")
RangeProductSetRefreshLog = get_model("offer", "RangeProductSetRefreshLog")

logger = logging.getLogger(__name__)


@shared_task(ignore_result=True)
def recalculate_offer_application_totals():
    ConditionalOffer = get_model("offer", "ConditionalOffer")
    ConditionalOffer.recalculate_offer_application_totals()


@shared_task(ignore_result=True)
@transaction.atomic
def refresh_rps_view(requested_on_timestamp):
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
    def _on_commit():
        pricing_cache_ns.invalidate()
        range_product_set_view_updated.send(sender=RangeProductSet)

    transaction.on_commit(_on_commit)
    logger.info("Finished refreshing RangeProductSet view")
