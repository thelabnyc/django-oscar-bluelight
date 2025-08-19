"""
Tests for condition satisfaction tracking functionality.

Tests that conditions track which specific products satisfied them during evaluation.
"""

from decimal import Decimal as D

from oscar.test.factories import create_basket, create_product, create_stockrecord

from oscarbluelight.offer.constants import Conjunction
from oscarbluelight.offer.models import (
    Benefit,
    CompoundCondition,
    Condition,
    ConditionalOffer,
    Range,
)

from .base import BaseTest


class CountConditionSatisfactionTrackingTest(BaseTest):
    """Test that BluelightCountCondition tracks which products satisfied it."""

    def test_tracks_no_satisfying_products_when_not_satisfied(self):
        """When condition is not satisfied, no products should be tracked."""
        # Create offer with count condition requiring 1 item
        offer = self._build_offer(
            "oscarbluelight.offer.conditions.BluelightCountCondition", 1
        )

        # Empty basket - condition not satisfied
        basket = create_basket(empty=True)
        condition_proxy = offer.condition.proxy()
        result = condition_proxy.is_satisfied(offer, basket)

        self.assertFalse(result)
        self.assertEqual(offer.get_condition_satisfying_lines(), [])

    def test_tracks_satisfying_products_when_satisfied(self):
        """When condition is satisfied, track which products contributed."""
        # Create offer with count condition requiring 1 item
        offer = self._build_offer(
            "oscarbluelight.offer.conditions.BluelightCountCondition", 1
        )

        # Create product and basket
        product = create_product(price=D("10.00"))
        create_stockrecord(product, D("10.00"), num_in_stock=10)
        basket = create_basket(empty=True)
        basket.add_product(product, quantity=1)

        condition_proxy = offer.condition.proxy()
        result = condition_proxy.is_satisfied(offer, basket)

        self.assertTrue(result)
        satisfying_lines = offer.get_condition_satisfying_lines()
        satisfying_products = [line.product for line in satisfying_lines]
        self.assertEqual(len(satisfying_products), 1)
        self.assertIn(product, satisfying_products)

    def test_tracks_multiple_satisfying_products(self):
        """When multiple products satisfy condition, track all of them."""
        # Create offer with count condition requiring 2 items
        offer = self._build_offer(
            "oscarbluelight.offer.conditions.BluelightCountCondition", 2
        )

        # Create two products and basket
        product1 = create_product(price=D("10.00"))
        create_stockrecord(product1, D("10.00"), num_in_stock=10)
        product2 = create_product(price=D("20.00"))
        create_stockrecord(product2, D("20.00"), num_in_stock=10)

        basket = create_basket(empty=True)
        basket.add_product(product1, quantity=1)
        basket.add_product(product2, quantity=1)

        condition_proxy = offer.condition.proxy()
        result = condition_proxy.is_satisfied(offer, basket)

        self.assertTrue(result)
        satisfying_lines = offer.get_condition_satisfying_lines()
        satisfying_products = [line.product for line in satisfying_lines]
        self.assertEqual(len(satisfying_products), 2)
        self.assertIn(product1, satisfying_products)
        self.assertIn(product2, satisfying_products)

    def test_resets_tracking_on_each_evaluation(self):
        """Each call to is_satisfied should add to the tracking."""
        # Create offer with count condition requiring 1 item
        offer = self._build_offer(
            "oscarbluelight.offer.conditions.BluelightCountCondition", 1
        )

        # Create two products
        product1 = create_product(price=D("10.00"))
        create_stockrecord(product1, D("10.00"), num_in_stock=10)
        product2 = create_product(price=D("20.00"))
        create_stockrecord(product2, D("20.00"), num_in_stock=10)

        # First evaluation with product1
        basket = create_basket(empty=True)
        basket.add_product(product1, quantity=1)
        condition_proxy = offer.condition.proxy()
        condition_proxy.is_satisfied(offer, basket)

        satisfying_lines = offer.get_condition_satisfying_lines()
        first_products = [line.product for line in satisfying_lines]
        self.assertEqual(len(first_products), 1)
        self.assertIn(product1, first_products)

        # Second evaluation with different basket state
        basket.flush()
        basket.add_product(product2, quantity=1)
        condition_proxy.is_satisfied(offer, basket)

        satisfying_lines = offer.get_condition_satisfying_lines()
        second_products = [line.product for line in satisfying_lines]
        self.assertEqual(len(second_products), 2)  # Both products now tracked
        self.assertIn(product2, second_products)
        self.assertIn(product1, second_products)  # Both products retained


class CompoundConditionSatisfactionTrackingTest(BaseTest):
    """Test that CompoundCondition tracks satisfying products from subconditions."""

    def _build_compound_offer(self, conjunction=Conjunction.AND, value_a=10, count_b=2):
        """Build compound condition offer with configurable subcondition values."""
        all_products = Range()
        all_products.name = "all products"
        all_products.includes_all_products = True
        all_products.save()

        cond_a = Condition()
        cond_a.proxy_class = "oscarbluelight.offer.conditions.BluelightValueCondition"
        cond_a.value = value_a
        cond_a.range = all_products
        cond_a.save()

        cond_b = Condition()
        cond_b.proxy_class = "oscarbluelight.offer.conditions.BluelightCountCondition"
        cond_b.value = count_b
        cond_b.range = all_products
        cond_b.save()

        condition = CompoundCondition()
        condition.proxy_class = "oscarbluelight.offer.conditions.CompoundCondition"
        condition.conjunction = conjunction
        condition.save()
        condition.subconditions.set([cond_a, cond_b])
        condition.save()

        benefit = Benefit()
        benefit.proxy_class = (
            "oscarbluelight.offer.benefits.BluelightShippingFixedPriceBenefit"
        )
        benefit.value = 0
        benefit.save()

        offer = ConditionalOffer()
        offer.condition = condition
        offer.benefit = benefit
        offer.save()

        return offer

    def test_aggregates_satisfying_products_when_satisfied(self):
        """CompoundCondition should aggregate products from satisfied subconditions."""
        # Create offer needing $10 value AND 2 count
        offer = self._build_compound_offer(value_a=10, count_b=2)

        # Create products that will satisfy both conditions
        product1 = create_product(price=D("6.00"))
        create_stockrecord(product1, D("6.00"), num_in_stock=10)
        product2 = create_product(price=D("5.00"))
        create_stockrecord(product2, D("5.00"), num_in_stock=10)

        # Add products to basket ($11 value, 2 count)
        basket = create_basket(empty=True)
        basket.add_product(product1, quantity=1)
        basket.add_product(product2, quantity=1)

        condition_proxy = offer.condition.proxy()
        result = condition_proxy.is_satisfied(offer, basket)

        self.assertTrue(result)
        satisfying_lines = offer.get_condition_satisfying_lines()
        satisfying_products = [line.product for line in satisfying_lines]
        self.assertEqual(
            len(satisfying_products), 2
        )  # Both products tracked by both subconditions
        self.assertIn(product1, satisfying_products)
        self.assertIn(product2, satisfying_products)

    def test_tracks_products_from_satisfied_subconditions_only(self):
        """Only track products from subconditions that were satisfied."""
        # Create offer needing $20 value AND 1 count
        offer = self._build_compound_offer(value_a=20, count_b=1)

        # Create product that satisfies count but not value
        product = create_product(price=D("10.00"))
        create_stockrecord(product, D("10.00"), num_in_stock=10)

        basket = create_basket(empty=True)
        basket.add_product(product, quantity=1)  # $10 value, 1 count

        condition_proxy = offer.condition.proxy()
        result = condition_proxy.is_satisfied(offer, basket)

        self.assertFalse(result)  # AND condition not satisfied
        satisfying_lines = offer.get_condition_satisfying_lines()
        satisfying_products = [line.product for line in satisfying_lines]

        # Should still track product from the count subcondition that was satisfied
        self.assertEqual(len(satisfying_products), 1)
        self.assertIn(product, satisfying_products)

    def test_resets_tracking_on_each_evaluation(self):
        """CompoundCondition should add to tracking on each evaluation."""
        offer = self._build_compound_offer(value_a=5, count_b=1)

        # Create two products
        product1 = create_product(price=D("6.00"))
        create_stockrecord(product1, D("6.00"), num_in_stock=10)
        product2 = create_product(price=D("7.00"))
        create_stockrecord(product2, D("7.00"), num_in_stock=10)

        # First evaluation with product1
        basket = create_basket(empty=True)
        basket.add_product(product1, quantity=1)
        condition_proxy = offer.condition.proxy()
        condition_proxy.is_satisfied(offer, basket)

        satisfying_lines = offer.get_condition_satisfying_lines()
        first_products = [line.product for line in satisfying_lines]
        self.assertIn(product1, first_products)

        # Second evaluation with different basket
        basket.flush()
        basket.add_product(product2, quantity=1)
        condition_proxy.is_satisfied(offer, basket)

        satisfying_lines = offer.get_condition_satisfying_lines()
        second_products = [line.product for line in satisfying_lines]
        self.assertIn(product2, second_products)
        self.assertIn(product1, second_products)  # Both products retained


class ConditionalOfferSatisfactionTrackingTest(BaseTest):
    """Test that ConditionalOffer persists satisfying_lines across proxy calls."""

    def test_offer_provides_method_to_get_satisfying_lines(self):
        """Test that ConditionalOffer provides a method to get satisfying lines."""
        offer = self._build_offer(
            "oscarbluelight.offer.conditions.BluelightCountCondition", 1
        )

        # Create product and basket
        product = create_product(price=D("10.00"))
        create_stockrecord(product, D("10.00"), num_in_stock=10)
        basket = create_basket(empty=True)
        basket.add_product(product, quantity=1)

        # Evaluate condition
        condition_proxy = offer.condition.proxy()
        result = condition_proxy.is_satisfied(offer, basket)

        self.assertTrue(result)

        # ConditionalOffer should have method to get satisfying lines
        self.assertTrue(hasattr(offer, "get_condition_satisfying_lines"))
        satisfying_lines = offer.get_condition_satisfying_lines()
        self.assertEqual(len(satisfying_lines), 1)
        self.assertEqual(satisfying_lines[0].product, product)
