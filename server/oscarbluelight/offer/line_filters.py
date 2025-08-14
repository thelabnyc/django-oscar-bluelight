from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..mixins import BluelightBasketMixin as Basket
    from .models import ConditionalOffer
    from .types import LinesTuple


class BaseLineFilterStrategy:
    """
    Base strategy for filtering applicable lines in offer benefits.

    Downstream projects may subclass this and implement custom filtering logic
    without needing to modify or subclass the benefit classes themselves.

    Example:
        class PriceFilterStrategy(BaseLineFilterStrategy):
            def filter_lines(self, offer, basket, line_tuples):
                # Filter out lines with price > 100.00
                return [(price, line) for price, line in line_tuples
                       if price <= Decimal('100.00')]

    Configure in settings.py:
        OSCARBLUELIGHT_LINE_FILTER_STRATEGY = 'myapp.strategies.PriceFilterStrategy'

    The strategy will be applied to all benefit types automatically via the
    Benefit.get_applicable_lines() method override.
    """

    def filter_lines(
        self, offer: ConditionalOffer, basket: Basket, line_tuples: list[LinesTuple]
    ) -> list[LinesTuple]:
        """
        Filter applicable lines based on offer context.

        This method is called by Benefit.get_applicable_lines() after the base
        implementation has determined which lines are eligible for the offer.
        Custom strategies can implement additional filtering logic here.
        """
        return line_tuples


class DefaultLineFilterStrategy(BaseLineFilterStrategy):
    """
    Default strategy that applies no filtering - returns all lines unchanged.
    """

    pass
