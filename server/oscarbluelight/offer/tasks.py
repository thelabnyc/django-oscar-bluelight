from collections.abc import Callable
from datetime import UTC, datetime
import logging

from django.db import OperationalError, connection, transaction
from django_tasks import task

from .applicator import pricing_cache_ns
from .models import RangeProductSet, ViewRefreshLog
from .signals import range_product_set_view_updated

logger = logging.getLogger(__name__)

# SQLSTATE raised when ``lock_timeout`` expires
LOCK_NOT_AVAILABLE = "55P03"


def _is_lock_timeout(exc: OperationalError) -> bool:
    # psycopg exposes the SQLSTATE as ``sqlstate``, psycopg2 as ``pgcode``
    cause = exc.__cause__
    sqlstate = getattr(cause, "sqlstate", None) or getattr(cause, "pgcode", None)
    return sqlstate == LOCK_NOT_AVAILABLE


def _do_view_refresh(
    view_type: ViewRefreshLog.ViewType,
    requested_on_timestamp: float | None,
    func: Callable[[], None],
) -> None:
    # Set a short lock timeout to prevent multiple of these tasks from running (and blocking) simultaneously
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL lock_timeout = '1s'")
    # Figure out if a refresh is actually needed. E.g. If the view has already
    # been refreshed since this refresh request was made, then we don't need to
    # refresh the view again.
    if requested_on_timestamp is None:
        logger.info("Skipping redundant %s refresh", view_type)
        return
    requested_on_dt = datetime.fromtimestamp(requested_on_timestamp, tz=UTC)
    if not ViewRefreshLog.is_refresh_needed(view_type, requested_on_dt):
        logger.info("Skipping redundant %s refresh", view_type)
        return
    # Refresh the view. If the lock timeout fires, whoever holds the lock is
    # usually either another refresh, which the check above would treat as
    # covering this request once it's logged, or a write (e.g. an order
    # recording its offer usage) whose commit queues a refresh of its own. So
    # skip this one, without logging it as a refresh. wrap_database_errors
    # turns errors from code that runs on the raw driver cursor (as
    # MaterializedView.refresh does) into OperationalError.
    try:
        with transaction.atomic(), connection.wrap_database_errors:
            func()
    except OperationalError as e:
        if not _is_lock_timeout(e):
            raise
        logger.info(
            "Skipping %s refresh: another transaction holds a lock it needs",
            view_type,
        )
        return
    ViewRefreshLog.log_view_refresh(view_type)
    logger.info("Finished refreshing %s view", view_type)


@task()
@transaction.atomic
def recalculate_offer_application_totals(
    requested_on_timestamp: float | None = None,
) -> None:
    def _inner() -> None:
        from .models import ConditionalOffer

        ConditionalOffer.recalculate_offer_application_totals()

    _do_view_refresh(
        ViewRefreshLog.ViewType.OFFER_APPLICATION_TOTALS,
        requested_on_timestamp,
        _inner,
    )


@task()
@transaction.atomic
def refresh_rps_view(requested_on_timestamp: float) -> None:
    # Invalidate the pricing cache (since range membership may affect pricing)
    def _on_commit() -> None:
        pricing_cache_ns.invalidate()
        range_product_set_view_updated.send(sender=RangeProductSet)

    def _inner() -> None:
        RangeProductSet.refresh(concurrently=True)
        transaction.on_commit(_on_commit)

    _do_view_refresh(
        ViewRefreshLog.ViewType.RANGE_PRODUCT_SET,
        requested_on_timestamp,
        _inner,
    )
