from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from decimal import Decimal as D
from unittest.mock import MagicMock, patch

from django.db import OperationalError, connection, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from oscarbluelight.offer import tasks
from oscarbluelight.offer.models import (
    BluelightAbsoluteDiscountBenefit,
    BluelightCountCondition,
    ConditionalOffer,
    Range,
    RangeProductSet,
    ViewRefreshLog,
)


@contextmanager
def _held_by_other_transaction(sql: str, params: list[object]) -> Iterator[None]:
    """Run ``sql`` in a second, uncommitted transaction, keeping its locks."""
    other = connection.copy()
    try:
        other.set_autocommit(False)
        with other.cursor() as cursor:
            cursor.execute(sql, params)
        yield
    finally:
        other.rollback()
        other.close()


def _skip_log_entry(view_type: ViewRefreshLog.ViewType) -> str:
    # Logging formats the view type with %s, i.e. str()
    return (
        f"INFO:oscarbluelight.offer.tasks:Skipping {view_type!s} refresh: "
        "another transaction holds a lock it needs"
    )


def _refresh_logged(view_type: ViewRefreshLog.ViewType) -> bool:
    return ViewRefreshLog.objects.filter(view_type=view_type).exists()


class RecalculateOfferApplicationTotalsTaskTest(TransactionTestCase):
    view_type = ViewRefreshLog.ViewType.OFFER_APPLICATION_TOTALS

    def setUp(self) -> None:
        all_products_range = Range.objects.create(
            name="All products", includes_all_products=True
        )
        condition = BluelightCountCondition.objects.create(
            range=all_products_range,
            proxy_class="oscarbluelight.offer.conditions.BluelightCountCondition",
            value=1,
        )
        benefit = BluelightAbsoluteDiscountBenefit.objects.create(
            range=all_products_range,
            proxy_class="oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit",
            value=D("1.00"),
        )
        # No orders used this offer, so a recalculation resets its total to 0
        self.offer = ConditionalOffer.objects.create(
            name="Offer",
            condition=condition,
            benefit=benefit,
            total_discount=D("7.00"),
        )

    def _lock_offer_row(self) -> AbstractContextManager[None]:
        # Hold the offer's row lock the way an order placement does between
        # recording the offer's usage and committing.
        return _held_by_other_transaction(
            f"SELECT id FROM {ConditionalOffer._meta.db_table} WHERE id = %s FOR UPDATE",
            [self.offer.pk],
        )

    def test_recalculates_totals(self) -> None:
        tasks.recalculate_offer_application_totals.call(timezone.now().timestamp())

        self.offer.refresh_from_db()
        self.assertEqual(self.offer.total_discount, D("0.00"))
        self.assertTrue(_refresh_logged(self.view_type))

    def test_skips_when_offer_row_is_locked(self) -> None:
        with (
            self._lock_offer_row(),
            self.assertLogs("oscarbluelight.offer.tasks", "INFO") as logs,
        ):
            tasks.recalculate_offer_application_totals.call(timezone.now().timestamp())

        self.assertIn(_skip_log_entry(self.view_type), logs.output)
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.total_discount, D("7.00"))
        # The skipped refresh must not be logged, or the refresh the lock
        # holder queues when it commits would be skipped as redundant.
        self.assertFalse(_refresh_logged(self.view_type))

    def test_skip_leaves_enclosing_transaction_usable(self) -> None:
        with transaction.atomic():
            with self._lock_offer_row():
                tasks.recalculate_offer_application_totals.call(
                    timezone.now().timestamp()
                )
            # Would raise InternalError if the lock timeout had aborted it
            self.assertFalse(_refresh_logged(self.view_type))


class RefreshRPSViewTaskTest(TransactionTestCase):
    view_type = ViewRefreshLog.ViewType.RANGE_PRODUCT_SET

    @patch("oscarbluelight.offer.tasks.pricing_cache_ns")
    def test_skips_when_another_refresh_is_running(
        self, pricing_cache_ns: MagicMock
    ) -> None:
        with (
            _held_by_other_transaction(
                f"REFRESH MATERIALIZED VIEW CONCURRENTLY {RangeProductSet._meta.db_table}",
                [],
            ),
            self.assertLogs("oscarbluelight.offer.tasks", "INFO") as logs,
        ):
            tasks.refresh_rps_view.call(timezone.now().timestamp())

        self.assertIn(_skip_log_entry(self.view_type), logs.output)
        self.assertFalse(_refresh_logged(self.view_type))
        pricing_cache_ns.invalidate.assert_not_called()


class DoViewRefreshTest(TestCase):
    view_type = ViewRefreshLog.ViewType.OFFER_APPLICATION_TOTALS

    def _raise(self, cause: BaseException) -> None:
        raise OperationalError("boom") from cause

    def test_reraises_other_operational_errors(self) -> None:
        # 57014 = query_canceled (e.g. statement_timeout), psycopg2-style
        func = MagicMock(side_effect=lambda: self._raise(_Cause(pgcode="57014")))
        with self.assertRaises(OperationalError):
            tasks._do_view_refresh(self.view_type, timezone.now().timestamp(), func)
        self.assertFalse(_refresh_logged(self.view_type))

    def test_is_lock_timeout_reads_either_driver_sqlstate(self) -> None:
        for cause in (_Cause(sqlstate="55P03"), _Cause(pgcode="55P03")):
            with self.subTest(cause=cause):
                exc = OperationalError()
                exc.__cause__ = cause
                self.assertTrue(tasks._is_lock_timeout(exc))
        exc = OperationalError()
        exc.__cause__ = _Cause(sqlstate="57014")
        self.assertFalse(tasks._is_lock_timeout(exc))


class _Cause(Exception):
    def __init__(self, **attrs: str) -> None:
        super().__init__()
        self.__dict__.update(attrs)
