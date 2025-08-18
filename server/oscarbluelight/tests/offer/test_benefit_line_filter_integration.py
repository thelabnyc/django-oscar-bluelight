"""
Integration tests for benefit classes using line filter strategy.
"""

from decimal import Decimal as D
from unittest import mock

from django.test import TransactionTestCase, override_settings
from django_redis import get_redis_connection
from oscar.test import factories
from oscar.test.basket import add_product

from oscarbluelight.offer.line_filters import BaseLineFilterStrategy
from oscarbluelight.offer.models import (
    BluelightCountCondition,
    BluelightPercentageDiscountBenefit,
    Range,
)


class FilterFirstLineBeyond10Strategy(BaseLineFilterStrategy):
    """Test strategy that filters out lines with price > 10.00, keeping only the first one."""

    def filter_lines(self, offer, basket, line_tuples):
        # Filter out lines with price > 10.00, but keep the first expensive item
        expensive_lines = [
            (price, line) for price, line in line_tuples if price > D("10.00")
        ]
        cheap_lines = [
            (price, line) for price, line in line_tuples if price <= D("10.00")
        ]

        # Keep first expensive line + all cheap lines
        result = []
        if expensive_lines:
            result.append(expensive_lines[0])
        result.extend(cheap_lines)

        return result


class TestBenefitLineFilterIntegration(TransactionTestCase):
    def setUp(self):
        # Flush the cache
        conn = get_redis_connection("redis")
        conn.flushall()

        range = Range.objects.create(name="All products", includes_all_products=True)
        self.condition = BluelightCountCondition(
            range=range,
            proxy_class="oscarbluelight.offer.conditions.BluelightCountCondition",
            value=1,  # Require at least 1 item
        )
        self.benefit = BluelightPercentageDiscountBenefit(
            range=range,
            proxy_class="oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit",
            value=50,  # 50% discount for easy calculation
        )
        self.offer = mock.Mock()
        self.basket = factories.create_basket(empty=True)

    def test_default_strategy_applies_to_all_lines(self):
        """Test that with no custom strategy, all applicable lines receive discount."""
        # Add products with different prices
        product1 = factories.create_product(title="Expensive Product")
        product2 = factories.create_product(title="Medium Product")
        product3 = factories.create_product(title="Cheap Product")

        add_product(self.basket, D("20.00"), 1, product=product1)  # $20
        add_product(self.basket, D("15.00"), 1, product=product2)  # $15
        add_product(self.basket, D("5.00"), 1, product=product3)  # $5

        # Apply benefit (no custom line filter strategy)
        result = self.benefit.apply(self.basket, self.condition, self.offer)

        # All 3 lines should be discounted by 50%
        # Expected discount: (20 + 15 + 5) * 0.5 = 20.00
        self.assertEqual(D("20.00"), result.discount)
        self.assertEqual(3, self.basket.num_items_with_discount)

    @override_settings(
        OSCARBLUELIGHT_LINE_FILTER_STRATEGY="oscarbluelight.tests.offer.test_benefit_line_filter_integration.FilterFirstLineBeyond10Strategy"
    )
    def test_custom_strategy_filters_lines(self):
        """Test that custom strategy filters lines correctly."""
        # Add products with different prices
        product1 = factories.create_product(title="Expensive Product 1")
        product2 = factories.create_product(title="Expensive Product 2")
        product3 = factories.create_product(title="Cheap Product")

        add_product(
            self.basket, D("20.00"), 1, product=product1
        )  # $20 - will be second in expensive list
        add_product(
            self.basket, D("15.00"), 1, product=product2
        )  # $15 - will be first in expensive list, should be included
        add_product(
            self.basket, D("5.00"), 1, product=product3
        )  # $5  - should be included (cheap)

        # Apply benefit with custom line filter strategy
        result = self.benefit.apply(self.basket, self.condition, self.offer)

        # Oscar sorts lines cheapest first: [$5, $15, $20]
        # Strategy keeps first expensive line ($15) and all cheap lines ($5)
        # Expected discount: (15 + 5) * 0.5 = 10.00
        self.assertEqual(D("10.00"), result.discount)
        self.assertEqual(2, self.basket.num_items_with_discount)

    @override_settings(
        OSCARBLUELIGHT_LINE_FILTER_STRATEGY="oscarbluelight.tests.offer.test_benefit_line_filter_integration.FilterFirstLineBeyond10Strategy"
    )
    def test_custom_strategy_with_only_expensive_products(self):
        """Test custom strategy when all products are expensive."""
        # Add only expensive products
        product1 = factories.create_product(title="Expensive Product 1")
        product2 = factories.create_product(title="Expensive Product 2")

        add_product(
            self.basket, D("25.00"), 1, product=product1
        )  # $25 - will be second in expensive list
        add_product(
            self.basket, D("15.00"), 1, product=product2
        )  # $15 - will be first in expensive list, should be included

        # Apply benefit with custom line filter strategy
        result = self.benefit.apply(self.basket, self.condition, self.offer)

        # Oscar sorts lines cheapest first: [$15, $25]
        # Strategy keeps first expensive line ($15) only
        # Expected discount: 15 * 0.5 = 7.50
        self.assertEqual(D("7.50"), result.discount)
        self.assertEqual(1, self.basket.num_items_with_discount)

    @override_settings(
        OSCARBLUELIGHT_LINE_FILTER_STRATEGY="oscarbluelight.tests.offer.test_benefit_line_filter_integration.FilterFirstLineBeyond10Strategy"
    )
    def test_custom_strategy_with_only_cheap_products(self):
        """Test custom strategy when all products are cheap."""
        # Add only cheap products
        product1 = factories.create_product(title="Cheap Product 1")
        product2 = factories.create_product(title="Cheap Product 2")

        add_product(
            self.basket, D("8.00"), 1, product=product1
        )  # $8 - should be included
        add_product(
            self.basket, D("3.00"), 1, product=product2
        )  # $3 - should be included

        # Apply benefit with custom line filter strategy
        result = self.benefit.apply(self.basket, self.condition, self.offer)

        # Both lines should be discounted by 50%: $8 + $3
        # Expected discount: (8 + 3) * 0.5 = 5.50
        self.assertEqual(D("5.50"), result.discount)
        self.assertEqual(2, self.basket.num_items_with_discount)

    def test_benefit_with_line_filter_strategy_implemented(self):
        """Test that benefit correctly uses line filter strategy after implementation."""

        with override_settings(
            OSCARBLUELIGHT_LINE_FILTER_STRATEGY="oscarbluelight.tests.offer.test_benefit_line_filter_integration.FilterFirstLineBeyond10Strategy"
        ):
            # Add products that should be filtered
            product1 = factories.create_product(title="Expensive Product 1")
            product2 = factories.create_product(title="Expensive Product 2")

            add_product(
                self.basket, D("20.00"), 1, product=product1
            )  # Will be second in expensive list
            add_product(
                self.basket, D("15.00"), 1, product=product2
            )  # Will be first in expensive list

            # Apply benefit with line filter strategy
            result = self.benefit.apply(self.basket, self.condition, self.offer)

            # After implementation: line filter strategy is applied
            # Oscar sorts lines cheapest first: [$15, $20]
            # Strategy keeps first expensive line ($15)
            # Expected discount: 15 * 0.5 = 7.50
            self.assertEqual(D("7.50"), result.discount)
            self.assertEqual(1, self.basket.num_items_with_discount)
