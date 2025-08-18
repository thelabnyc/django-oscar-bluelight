"""
Test line filtering strategies for offer benefits.
"""

from decimal import Decimal
from unittest.mock import Mock

from django.test import TestCase

from oscarbluelight.offer.line_filters import (
    BaseLineFilterStrategy,
    DefaultLineFilterStrategy,
)


class TestLineFilterStrategies(TestCase):
    def test_base_line_filter_strategy_returns_all_lines(self):
        """BaseLineFilterStrategy should return all lines unchanged by default."""
        strategy = BaseLineFilterStrategy()

        # Mock objects
        offer = Mock()
        basket = Mock()
        line_tuples = [
            (Decimal("10.00"), Mock()),
            (Decimal("20.00"), Mock()),
            (Decimal("30.00"), Mock()),
        ]

        # Call filter_lines
        result = strategy.filter_lines(offer, basket, line_tuples)

        # Should return all lines unchanged
        self.assertEqual(result, line_tuples)
        self.assertEqual(len(result), 3)

    def test_default_line_filter_strategy_inherits_behavior(self):
        """DefaultLineFilterStrategy should inherit base behavior."""
        strategy = DefaultLineFilterStrategy()

        # Mock objects
        offer = Mock()
        basket = Mock()
        line_tuples = [
            (Decimal("10.00"), Mock()),
            (Decimal("20.00"), Mock()),
        ]

        # Call filter_lines
        result = strategy.filter_lines(offer, basket, line_tuples)

        # Should return all lines unchanged (inherited behavior)
        self.assertEqual(result, line_tuples)
        self.assertEqual(len(result), 2)

    def test_custom_strategy_can_filter_lines(self):
        """Test that a custom strategy can filter lines based on custom logic."""

        class TestFilterStrategy(BaseLineFilterStrategy):
            def filter_lines(self, offer, basket, line_tuples):
                # Filter out lines with price > 15.00
                return [
                    (price, line)
                    for price, line in line_tuples
                    if price <= Decimal("15.00")
                ]

        strategy = TestFilterStrategy()

        # Mock objects
        offer = Mock()
        basket = Mock()
        line1, line2, line3 = Mock(), Mock(), Mock()
        line_tuples = [
            (Decimal("10.00"), line1),  # Should be included
            (Decimal("20.00"), line2),  # Should be filtered out
            (Decimal("15.00"), line3),  # Should be included
        ]

        # Call filter_lines
        result = strategy.filter_lines(offer, basket, line_tuples)

        # Should filter out the 20.00 line
        expected = [
            (Decimal("10.00"), line1),
            (Decimal("15.00"), line3),
        ]
        self.assertEqual(result, expected)
        self.assertEqual(len(result), 2)

    def test_empty_line_tuples_handling(self):
        """Test that strategies handle empty line tuples properly."""
        strategy = BaseLineFilterStrategy()

        # Mock objects
        offer = Mock()
        basket = Mock()
        line_tuples = []

        # Call filter_lines
        result = strategy.filter_lines(offer, basket, line_tuples)

        # Should return empty list
        self.assertEqual(result, [])
