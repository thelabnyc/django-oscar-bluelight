from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import ANY, MagicMock, patch

from django.test import TestCase, override_settings


class TestQueueRecalculateOfferApplicationTotals(TestCase):
    """Test the signal handler that enqueues recalculate_offer_application_totals."""

    def _call_handler(self) -> None:
        """Import and call the handler directly (avoids signal wiring complexity)."""
        from oscarbluelight.offer.handlers import (
            queue_recalculate_offer_application_totals,
        )

        queue_recalculate_offer_application_totals(sender=MagicMock())

    @override_settings(BLUELIGHT_OFFER_RECALC_DELAY=timedelta(minutes=5))
    @patch("oscarbluelight.offer.handlers.transaction")
    @patch("oscarbluelight.offer.handlers.tasks")
    def test_nonzero_delay_uses_run_after(
        self,
        mock_tasks: MagicMock,
        mock_transaction: MagicMock,
    ) -> None:
        """A non-zero delay is forwarded as run_after via .using()."""
        mock_transaction.on_commit.side_effect = lambda fn: fn()

        mock_using = MagicMock()
        mock_tasks.recalculate_offer_application_totals.using.return_value = mock_using

        self._call_handler()

        mock_tasks.recalculate_offer_application_totals.using.assert_called_once()
        call_kwargs = (
            mock_tasks.recalculate_offer_application_totals.using.call_args.kwargs
        )
        run_after = call_kwargs["run_after"]
        self.assertIsInstance(run_after, datetime)
        self.assertIsNotNone(run_after.tzinfo)
        mock_using.enqueue.assert_called_once_with(ANY)

    @override_settings(BLUELIGHT_OFFER_RECALC_DELAY=timedelta(minutes=15))
    @patch("oscarbluelight.offer.handlers.transaction")
    @patch("oscarbluelight.offer.handlers.tasks")
    def test_custom_delay_from_settings(
        self,
        mock_tasks: MagicMock,
        mock_transaction: MagicMock,
    ) -> None:
        """A custom BLUELIGHT_OFFER_RECALC_DELAY is forwarded as run_after."""
        mock_transaction.on_commit.side_effect = lambda fn: fn()

        mock_using = MagicMock()
        mock_tasks.recalculate_offer_application_totals.using.return_value = mock_using

        before = datetime.now(timezone.utc)
        self._call_handler()
        after = datetime.now(timezone.utc)

        call_kwargs = (
            mock_tasks.recalculate_offer_application_totals.using.call_args.kwargs
        )
        run_after = call_kwargs["run_after"]
        # run_after should be ~15 minutes from now
        self.assertGreaterEqual(run_after, before + timedelta(minutes=15))
        self.assertLessEqual(run_after, after + timedelta(minutes=15))
        mock_using.enqueue.assert_called_once_with(ANY)

    @override_settings(BLUELIGHT_OFFER_RECALC_DELAY=timedelta(seconds=0))
    @patch("oscarbluelight.offer.handlers.transaction")
    @patch("oscarbluelight.offer.handlers.tasks")
    def test_zero_delay_skips_using(
        self,
        mock_tasks: MagicMock,
        mock_transaction: MagicMock,
    ) -> None:
        """Setting delay to zero enqueues directly without .using(run_after=...)."""
        mock_transaction.on_commit.side_effect = lambda fn: fn()

        self._call_handler()

        mock_tasks.recalculate_offer_application_totals.using.assert_not_called()
        mock_tasks.recalculate_offer_application_totals.enqueue.assert_called_once_with(
            ANY,
        )

    @override_settings(BLUELIGHT_OFFER_RECALC_DELAY=timedelta(minutes=5))
    @patch("oscarbluelight.offer.handlers.transaction")
    @patch("oscarbluelight.offer.handlers.tasks")
    def test_enqueue_passes_timestamp(
        self,
        mock_tasks: MagicMock,
        mock_transaction: MagicMock,
    ) -> None:
        """The current timestamp is passed to the enqueue call."""
        mock_transaction.on_commit.side_effect = lambda fn: fn()

        mock_using = MagicMock()
        mock_tasks.recalculate_offer_application_totals.using.return_value = mock_using

        self._call_handler()

        mock_using.enqueue.assert_called_once()
        (timestamp,), _ = mock_using.enqueue.call_args
        self.assertIsInstance(timestamp, float)
