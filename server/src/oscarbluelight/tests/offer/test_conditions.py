from datetime import timedelta
from decimal import Decimal as D
from unittest.mock import patch
from urllib.parse import urlencode

from django.contrib.auth.models import User
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from oscar.test.factories import create_basket, create_product, create_stockrecord

from oscarbluelight.dashboard.offers.views import ConditionListView
from oscarbluelight.offer.applicator import Applicator
from oscarbluelight.offer.constants import Conjunction
from oscarbluelight.offer.models import (
    Benefit,
    CompoundCondition,
    Condition,
    ConditionalOffer,
    Range,
)
from oscarbluelight.voucher.models import Voucher

from .base import BaseTest


class CountConditionTest(BaseTest):
    def test_consume_items(self):
        basket = self._build_basket()
        offer = self._build_offer(
            "oscarbluelight.offer.conditions.BluelightCountCondition", 2
        )

        line = basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 0)
        self.assertEqual(line.quantity_without_discount, 5)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, [])
        self.assertEqual(len(affected_lines), 1, "Consumed 1 line")
        self.assertEqual(affected_lines[0][2], 2, "Consumed quantity of 2")
        line = basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 2)
        self.assertEqual(line.quantity_without_discount, 3)

        affected_lines = offer.condition.proxy().consume_items(
            offer, basket, affected_lines
        )
        self.assertEqual(len(affected_lines), 1, "Consumed 1 line")
        self.assertEqual(affected_lines[0][2], 2, "Consumed quantity of 2")
        line = basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 2)
        self.assertEqual(line.quantity_without_discount, 3)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, [])
        self.assertEqual(len(affected_lines), 1, "Consumed 1 line")
        self.assertEqual(affected_lines[0][2], 2, "Consumed quantity of 2")
        line = basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 4)
        self.assertEqual(line.quantity_without_discount, 1)

    def test_consume_items_when_benefit_consumes_other_items(self):
        # Create two products, each in a different product class
        product_main = create_product(product_class="Expensive Stuff")
        create_stockrecord(product_main, D("5000.00"), num_in_stock=100)

        product_accessory = create_product(product_class="Less Expensive Stuff")
        create_stockrecord(product_accessory, D("100.00"), num_in_stock=100)

        # Create two ranges, one for each product we just made
        range_main = Range.objects.create(name="Expensive Stuff")
        range_main.add_product(product_main)

        range_accessories = Range.objects.create(name="Less Expensive Stuff")
        range_accessories.add_product(product_accessory)

        # Create an offer which gives $5 off an accessory product when the basket contains a main product.
        # This offer, when applied, should consume the main and the accessory products. Not just the accessory.
        cond_has_main = Condition()
        cond_has_main.proxy_class = (
            "oscarbluelight.offer.conditions.BluelightCountCondition"
        )
        cond_has_main.value = 1
        cond_has_main.range = range_main
        cond_has_main.save()

        benefit_5off_accessory = Benefit()
        benefit_5off_accessory.proxy_class = (
            "oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit"
        )
        benefit_5off_accessory.value = 5
        benefit_5off_accessory.range = range_accessories
        benefit_5off_accessory.save()

        offer = ConditionalOffer()
        offer.condition = cond_has_main
        offer.benefit = benefit_5off_accessory
        offer.save()

        basket = create_basket(empty=True)
        basket.add_product(product_main, quantity=1)
        basket.add_product(product_accessory, quantity=1)

        self.assertEqual(basket.total_excl_tax_excl_discounts, D("5100.00"))
        self.assertEqual(basket.total_excl_tax, D("5100.00"))
        self.assertEqual(basket.num_items_without_discount, 2)
        self.assertEqual(basket.num_items_with_discount, 0)

        Applicator().apply_offers(basket, [offer])

        self.assertEqual(basket.total_excl_tax_excl_discounts, D("5100.00"))
        self.assertEqual(basket.total_excl_tax, D("5095.00"))
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.num_items_with_discount, 2)

    def test_is_partially_satisfied(self):
        # Create three products for two different ranges
        product_a = create_product()
        create_stockrecord(product_a, D("100.00"), num_in_stock=10)
        product_b = create_product()
        create_stockrecord(product_b, D("100.00"), num_in_stock=10)
        product_c = create_product()
        create_stockrecord(product_c, D("100.00"), num_in_stock=10)

        range_main = Range.objects.create(name="BOGO Select Pillows")
        range_main.add_product(product_a)
        range_main.add_product(product_b)

        range_accessories = Range.objects.create(name="Sheets")
        range_accessories.add_product(product_c)

        condition = Condition()
        condition.proxy_class = (
            "oscarbluelight.offer.conditions.BluelightCountCondition"
        )
        condition.value = 2
        condition.range = range_main
        condition.save()

        benefit = Benefit()
        benefit.proxy_class = (
            "oscarbluelight.offer.benefits.BluelightMultibuyDiscountBenefit"
        )
        benefit.range = range_accessories
        benefit.save()

        offer = ConditionalOffer()
        offer.condition = condition
        offer.benefit = benefit
        offer.save()

        basket = create_basket(empty=True)
        # Should not be satisfied partially because the basket is empty
        self.assertFalse(offer.is_condition_partially_satisfied(basket))

        basket.add_product(product_c, quantity=1)
        # Should not be satisfied partially because no product from the range_main is added
        self.assertFalse(offer.is_condition_partially_satisfied(basket))

        basket.add_product(product_a, quantity=1)
        # Should be satisfied partially because the count value is not reached
        self.assertTrue(offer.is_condition_partially_satisfied(basket))

        basket.add_product(product_c, quantity=1)
        # Should be satisfied partially because the count value is not reached
        self.assertTrue(offer.is_condition_partially_satisfied(basket))

        basket.add_product(product_b, quantity=1)
        # Should not be satisfied partially because the condition is satisfied
        self.assertFalse(offer.is_condition_partially_satisfied(basket))

        basket.add_product(product_a, quantity=1)
        # Should not be satisfied partially because the condition is satisfied
        self.assertFalse(offer.is_condition_partially_satisfied(basket))


class ValueConditionTest(BaseTest):
    def test_consume_items(self):
        basket = self._build_basket()
        offer = self._build_offer(
            "oscarbluelight.offer.conditions.BluelightValueCondition", D("15.00")
        )

        line = basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 0)
        self.assertEqual(line.quantity_without_discount, 5)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, [])
        self.assertEqual(len(affected_lines), 1, "Consumed 1 line")
        self.assertEqual(affected_lines[0][2], 2, "Consumed quantity of 2")
        line = basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 2)
        self.assertEqual(line.quantity_without_discount, 3)

        affected_lines = offer.condition.proxy().consume_items(
            offer, basket, affected_lines
        )
        self.assertEqual(len(affected_lines), 1, "Consumed 1 line")
        self.assertEqual(affected_lines[0][2], 2, "Consumed quantity of 2")
        line = basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 2)
        self.assertEqual(line.quantity_without_discount, 3)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, [])
        self.assertEqual(len(affected_lines), 1, "Consumed 1 line")
        self.assertEqual(affected_lines[0][2], 2, "Consumed quantity of 2")
        line = basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 4)
        self.assertEqual(line.quantity_without_discount, 1)

    def test_consume_items_when_benefit_consumes_other_items(self):
        # Create two products, each in a different product class
        product_main = create_product(product_class="Expensive Stuff")
        create_stockrecord(product_main, D("5000.00"), num_in_stock=100)

        product_accessory = create_product(product_class="Less Expensive Stuff")
        create_stockrecord(product_accessory, D("100.00"), num_in_stock=100)

        # Create two ranges, one for each product we just made
        range_main = Range.objects.create(name="Expensive Stuff")
        range_main.add_product(product_main)

        range_accessories = Range.objects.create(name="Less Expensive Stuff")
        range_accessories.add_product(product_accessory)

        # Create an offer which gives $5 off an accessory product when the basket contains a main product.
        # This offer, when applied, should consume the main and the accessory products. Not just the accessory.
        cond_has_main = Condition()
        cond_has_main.proxy_class = (
            "oscarbluelight.offer.conditions.BluelightValueCondition"
        )
        cond_has_main.value = 1
        cond_has_main.range = range_main
        cond_has_main.save()

        benefit_5off_accessory = Benefit()
        benefit_5off_accessory.proxy_class = (
            "oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit"
        )
        benefit_5off_accessory.value = 5
        benefit_5off_accessory.range = range_accessories
        benefit_5off_accessory.save()

        offer = ConditionalOffer()
        offer.condition = cond_has_main
        offer.benefit = benefit_5off_accessory
        offer.save()

        basket = create_basket(empty=True)
        basket.add_product(product_main, quantity=1)
        basket.add_product(product_accessory, quantity=1)

        self.assertEqual(basket.total_excl_tax_excl_discounts, D("5100.00"))
        self.assertEqual(basket.total_excl_tax, D("5100.00"))
        self.assertEqual(basket.num_items_without_discount, 2)
        self.assertEqual(basket.num_items_with_discount, 0)

        Applicator().apply_offers(basket, [offer])

        self.assertEqual(basket.total_excl_tax_excl_discounts, D("5100.00"))
        self.assertEqual(basket.total_excl_tax, D("5095.00"))
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.num_items_with_discount, 2)

    def test_is_partially_satisfied(self):
        # Create three products for two different ranges
        product_a = create_product()
        create_stockrecord(product_a, D("150.00"), num_in_stock=10)
        product_b = create_product()
        create_stockrecord(product_b, D("100.00"), num_in_stock=10)
        product_c = create_product()
        create_stockrecord(product_c, D("10.00"), num_in_stock=10)

        range_main = Range.objects.create(name="Expensive Stuff")
        range_main.add_product(product_a)
        range_main.add_product(product_b)

        range_accessories = Range.objects.create(name="Less Expensive Stuff")
        range_accessories.add_product(product_c)

        condition = Condition()
        condition.proxy_class = (
            "oscarbluelight.offer.conditions.BluelightValueCondition"
        )
        condition.value = D("259.00")
        condition.range = range_main
        condition.save()

        benefit = Benefit()
        benefit.proxy_class = (
            "oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit"
        )
        benefit.range = range_accessories
        benefit.save()

        offer = ConditionalOffer()
        offer.condition = condition
        offer.benefit = benefit
        offer.save()

        basket = create_basket(empty=True)
        # Should not be satisfied partially because the basket is empty
        self.assertFalse(offer.is_condition_partially_satisfied(basket))

        basket.add_product(product_c, quantity=1)
        # Should not be satisfied partially because no product from the range_main is added
        self.assertFalse(offer.is_condition_partially_satisfied(basket))

        basket.add_product(product_a, quantity=1)
        # Should be satisfied partially because the count value is not reached
        self.assertTrue(offer.is_condition_partially_satisfied(basket))

        basket.add_product(product_b, quantity=1)
        # Should be satisfied partially because the count value is not reached
        self.assertTrue(offer.is_condition_partially_satisfied(basket))

        basket.add_product(product_a, quantity=1)
        # Should not be satisfied partially because the condition is satisfied
        self.assertFalse(offer.is_condition_partially_satisfied(basket))


class CoverageConditionTest(BaseTest):
    def test_consume_items(self):
        basket = create_basket(empty=True)
        for i in range(5):
            product = create_product()
            create_stockrecord(product, D("10.00"), num_in_stock=10)
            basket.add_product(product, quantity=5)

        offer = self._build_offer(
            "oscarbluelight.offer.conditions.BluelightCoverageCondition", 2
        )

        affected_lines = offer.condition.proxy().consume_items(offer, basket, [])
        self.assertEqual(len(affected_lines), 2, "Consumed 2 lines")
        self.assertEqual(affected_lines[0][2], 1, "Consumed quantity of 1")
        self.assertEqual(affected_lines[1][2], 1, "Consumed quantity of 1")
        self.assertEqual(basket.all_lines()[0].quantity_with_discount, 1)
        self.assertEqual(basket.all_lines()[0].quantity_without_discount, 4)
        self.assertEqual(basket.all_lines()[1].quantity_with_discount, 1)
        self.assertEqual(basket.all_lines()[1].quantity_without_discount, 4)
        self.assertEqual(basket.all_lines()[2].quantity_with_discount, 0)
        self.assertEqual(basket.all_lines()[2].quantity_without_discount, 5)

        affected_lines = offer.condition.proxy().consume_items(
            offer, basket, affected_lines
        )
        self.assertEqual(len(affected_lines), 2, "Consumed 2 lines")
        self.assertEqual(affected_lines[0][2], 1, "Consumed quantity of 1")
        self.assertEqual(affected_lines[1][2], 1, "Consumed quantity of 1")
        self.assertEqual(basket.all_lines()[0].quantity_with_discount, 1)
        self.assertEqual(basket.all_lines()[0].quantity_without_discount, 4)
        self.assertEqual(basket.all_lines()[1].quantity_with_discount, 1)
        self.assertEqual(basket.all_lines()[1].quantity_without_discount, 4)
        self.assertEqual(basket.all_lines()[2].quantity_with_discount, 0)
        self.assertEqual(basket.all_lines()[2].quantity_without_discount, 5)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, [])
        self.assertEqual(len(affected_lines), 2, "Consumed 2 lines")
        self.assertEqual(affected_lines[0][2], 1, "Consumed quantity of 1")
        self.assertEqual(affected_lines[1][2], 1, "Consumed quantity of 1")
        self.assertEqual(basket.all_lines()[0].quantity_with_discount, 2)
        self.assertEqual(basket.all_lines()[0].quantity_without_discount, 3)
        self.assertEqual(basket.all_lines()[1].quantity_with_discount, 2)
        self.assertEqual(basket.all_lines()[1].quantity_without_discount, 3)
        self.assertEqual(basket.all_lines()[2].quantity_with_discount, 0)
        self.assertEqual(basket.all_lines()[2].quantity_without_discount, 5)

    def test_consume_items_when_benefit_consumes_other_items(self):
        # Create two products, each in a different product class
        product_main = create_product(product_class="Expensive Stuff")
        create_stockrecord(product_main, D("5000.00"), num_in_stock=100)

        product_accessory = create_product(product_class="Less Expensive Stuff")
        create_stockrecord(product_accessory, D("100.00"), num_in_stock=100)

        # Create two ranges, one for each product we just made
        range_main = Range.objects.create(name="Expensive Stuff")
        range_main.add_product(product_main)

        range_accessories = Range.objects.create(name="Less Expensive Stuff")
        range_accessories.add_product(product_accessory)

        # Create an offer which gives $5 off an accessory product when the basket contains a main product.
        # This offer, when applied, should consume the main and the accessory products. Not just the accessory.
        cond_has_main = Condition()
        cond_has_main.proxy_class = (
            "oscarbluelight.offer.conditions.BluelightCoverageCondition"
        )
        cond_has_main.value = 1
        cond_has_main.range = range_main
        cond_has_main.save()

        benefit_5off_accessory = Benefit()
        benefit_5off_accessory.proxy_class = (
            "oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit"
        )
        benefit_5off_accessory.value = 5
        benefit_5off_accessory.range = range_accessories
        benefit_5off_accessory.save()

        offer = ConditionalOffer()
        offer.condition = cond_has_main
        offer.benefit = benefit_5off_accessory
        offer.save()

        basket = create_basket(empty=True)
        basket.add_product(product_main, quantity=1)
        basket.add_product(product_accessory, quantity=1)

        self.assertEqual(basket.total_excl_tax_excl_discounts, D("5100.00"))
        self.assertEqual(basket.total_excl_tax, D("5100.00"))
        self.assertEqual(basket.num_items_without_discount, 2)
        self.assertEqual(basket.num_items_with_discount, 0)

        Applicator().apply_offers(basket, [offer])

        self.assertEqual(basket.total_excl_tax_excl_discounts, D("5100.00"))
        self.assertEqual(basket.total_excl_tax, D("5095.00"))
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.num_items_with_discount, 2)

    def test_is_partially_satisfied(self):
        # Create five products for two different ranges
        product_a = create_product()
        create_stockrecord(product_a, D("150.00"), num_in_stock=10)
        product_b = create_product()
        create_stockrecord(product_b, D("100.00"), num_in_stock=10)
        product_c = create_product()
        create_stockrecord(product_c, D("125.00"), num_in_stock=10)
        product_d = create_product()
        create_stockrecord(product_d, D("10.00"), num_in_stock=10)
        product_e = create_product()
        create_stockrecord(product_e, D("20.00"), num_in_stock=10)

        range_main = Range.objects.create(name="Expensive Stuff")
        range_main.add_product(product_a)
        range_main.add_product(product_b)
        range_main.add_product(product_c)

        range_accessories = Range.objects.create(name="Less Expensive Stuff")
        range_accessories.add_product(product_d)
        range_accessories.add_product(product_e)

        condition = Condition()
        condition.proxy_class = (
            "oscarbluelight.offer.conditions.BluelightCoverageCondition"
        )
        condition.value = 3
        condition.range = range_main
        condition.save()

        benefit = Benefit()
        benefit.proxy_class = (
            "oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit"
        )
        benefit.range = range_accessories
        benefit.save()

        offer = ConditionalOffer()
        offer.condition = condition
        offer.benefit = benefit
        offer.save()

        basket = create_basket(empty=True)
        # Should not be satisfied partially because the basket is empty
        self.assertFalse(offer.is_condition_partially_satisfied(basket))

        basket.add_product(product_e, quantity=1)
        # Should not be satisfied partially because no product from the range_main is added
        self.assertFalse(offer.is_condition_partially_satisfied(basket))

        basket.add_product(product_a, quantity=1)
        # Should be satisfied partially because the count value is not reached
        self.assertTrue(offer.is_condition_partially_satisfied(basket))

        basket.add_product(product_b, quantity=2)
        # Should be satisfied partially because the count value is not reached
        self.assertTrue(offer.is_condition_partially_satisfied(basket))

        basket.add_product(product_d, quantity=1)
        # Should be satisfied partially because the count value is not reached
        self.assertTrue(offer.is_condition_partially_satisfied(basket))

        basket.add_product(product_c, quantity=1)
        # Should not be satisfied partially because the condition is satisfied
        self.assertFalse(offer.is_condition_partially_satisfied(basket))


class CompoundConditionTest(BaseTest):
    def _build_offer(self, conjunction=Conjunction.AND):
        all_products = Range()
        all_products.name = "site"
        all_products.includes_all_products = True
        all_products.save()

        cond_a = Condition()
        cond_a.proxy_class = "oscarbluelight.offer.conditions.BluelightValueCondition"
        cond_a.value = 10
        cond_a.range = all_products
        cond_a.save()

        cond_b = Condition()
        cond_b.proxy_class = "oscarbluelight.offer.conditions.BluelightCountCondition"
        cond_b.value = 2
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

    def test_children(self):
        offer = self._build_offer()
        c = offer.condition.proxy()
        self.assertEqual(len(c.children), 2)
        self.assertEqual(
            c.children[0].proxy_class,
            "oscarbluelight.offer.conditions.BluelightValueCondition",
        )
        self.assertEqual(
            c.children[1].proxy_class,
            "oscarbluelight.offer.conditions.BluelightCountCondition",
        )

    def test_name_and(self):
        offer = self._build_offer(Conjunction.AND)
        c = offer.condition.proxy()
        self.assertEqual(
            c.name,
            "Basket includes $10.00 (tax-exclusive) from site and Cart includes 2 item(s) from site",
        )

    def test_name_or(self):
        offer = self._build_offer(Conjunction.OR)
        c = offer.condition.proxy()
        self.assertEqual(
            c.name,
            "Basket includes $10.00 (tax-exclusive) from site or Cart includes 2 item(s) from site",
        )

    def test_description_and(self):
        offer = self._build_offer(Conjunction.AND)
        c = offer.condition.proxy()
        self.assertEqual(
            c.description,
            "Basket includes $10.00 (tax-exclusive) from site and Cart includes 2 item(s) from site",
        )

    def test_description_or(self):
        offer = self._build_offer(Conjunction.OR)
        c = offer.condition.proxy()
        self.assertEqual(
            c.description,
            "Basket includes $10.00 (tax-exclusive) from site or Cart includes 2 item(s) from site",
        )

    def test_is_satisfied_and(self):
        offer = self._build_offer(Conjunction.AND)

        product = create_product()
        create_stockrecord(product, D("1.00"), num_in_stock=10)
        basket = create_basket(empty=True)
        self.assertFalse(offer.condition.is_satisfied(offer, basket))
        basket.add_product(product, quantity=5)
        self.assertFalse(offer.condition.is_satisfied(offer, basket))
        basket.add_product(product, quantity=5)
        self.assertTrue(offer.condition.is_satisfied(offer, basket))

        product = create_product()
        create_stockrecord(product, D("20.00"), num_in_stock=10)
        basket = create_basket(empty=True)
        self.assertFalse(offer.condition.is_satisfied(offer, basket))
        basket.add_product(product, quantity=1)
        self.assertFalse(offer.condition.is_satisfied(offer, basket))
        basket.add_product(product, quantity=1)
        self.assertTrue(offer.condition.is_satisfied(offer, basket))

    def test_is_satisfied_or(self):
        offer = self._build_offer(Conjunction.OR)

        product = create_product()
        create_stockrecord(product, D("1.00"), num_in_stock=10)
        basket = create_basket(empty=True)
        self.assertFalse(offer.condition.is_satisfied(offer, basket))
        basket.add_product(product, quantity=1)
        self.assertFalse(offer.condition.is_satisfied(offer, basket))
        basket.add_product(product, quantity=1)
        self.assertTrue(offer.condition.is_satisfied(offer, basket))

        product = create_product()
        create_stockrecord(product, D("10.00"), num_in_stock=10)
        basket = create_basket(empty=True)
        self.assertFalse(offer.condition.is_satisfied(offer, basket))
        basket.add_product(product, quantity=1)
        self.assertTrue(offer.condition.is_satisfied(offer, basket))

    def test_is_partially_satisfied_and(self):
        offer = self._build_offer(Conjunction.AND)

        product = create_product()
        create_stockrecord(product, D("1.00"), num_in_stock=10)
        basket = create_basket(empty=True)
        self.assertFalse(offer.condition.is_partially_satisfied(offer, basket))
        basket.add_product(product, quantity=1)
        self.assertTrue(offer.condition.is_partially_satisfied(offer, basket))

    def test_is_partially_satisfied_or(self):
        offer = self._build_offer(Conjunction.OR)

        product = create_product()
        create_stockrecord(product, D("1.00"), num_in_stock=10)
        basket = create_basket(empty=True)
        self.assertFalse(offer.condition.is_partially_satisfied(offer, basket))
        basket.add_product(product, quantity=1)
        self.assertTrue(offer.condition.is_partially_satisfied(offer, basket))

    def test_get_upsell_message_and(self):
        offer = self._build_offer(Conjunction.AND)

        product = create_product()
        create_stockrecord(product, D("1.00"), num_in_stock=10)

        basket = create_basket(empty=True)
        basket.add_product(product, quantity=1)
        self.assertEqual(
            offer.condition.proxy().get_upsell_message(offer, basket),
            "Spend $9.00 more from site and Buy 1 more product from site",
        )

        basket.add_product(product, quantity=1)
        self.assertEqual(
            offer.condition.proxy().get_upsell_message(offer, basket),
            "Spend $8.00 more from site",
        )

    def test_get_upsell_message_or(self):
        offer = self._build_offer(Conjunction.OR)

        product = create_product()
        create_stockrecord(product, D("1.00"), num_in_stock=10)

        basket = create_basket(empty=True)
        basket.add_product(product, quantity=1)
        self.assertEqual(
            offer.condition.proxy().get_upsell_message(offer, basket),
            "Spend $9.00 more from site or Buy 1 more product from site",
        )

    def test_consume_items(self):
        basket = self._build_basket()
        offer = self._build_offer(Conjunction.OR)

        line = basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 0)
        self.assertEqual(line.quantity_without_discount, 5)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, [])
        self.assertEqual(len(affected_lines), 2)
        self.assertEqual(affected_lines[0][2], 1)
        self.assertEqual(affected_lines[1][2], 1)
        line = basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 2)
        self.assertEqual(line.quantity_without_discount, 3)

        affected_lines = offer.condition.proxy().consume_items(
            offer, basket, affected_lines
        )
        self.assertEqual(len(affected_lines), 2)
        self.assertEqual(affected_lines[0][2], 1)
        self.assertEqual(affected_lines[1][2], 1)
        line = basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 2)
        self.assertEqual(line.quantity_without_discount, 3)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, [])
        self.assertEqual(len(affected_lines), 2)
        self.assertEqual(affected_lines[0][2], 1)
        self.assertEqual(affected_lines[1][2], 1)
        line = basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 4)
        self.assertEqual(line.quantity_without_discount, 1)

    def test_create_compound_from_vanilla_condition(self):
        a = Condition()
        a.proxy_class = "oscarbluelight.offer.conditions.CompoundCondition"
        a.conjunction = Conjunction.OR
        a.save()

        self.assertEqual(a.conjunction, Conjunction.OR)

        b = Condition.objects.get(pk=a.pk)
        self.assertIsNotNone(b.compoundcondition)
        self.assertEqual(b.compoundcondition.conjunction, Conjunction.OR)

        # Saving the original model should work ok
        a.save()

        # Saving the proxy instance  should work too
        b.save()

    def test_consume_items_when_benefit_consumes_other_items(self):
        # Create three products, each in a different product class
        product_main = create_product(product_class="Expensive Stuff")
        create_stockrecord(product_main, D("5000.00"), num_in_stock=100)

        product_accessory = create_product(product_class="Less Expensive Stuff")
        create_stockrecord(product_accessory, D("100.00"), num_in_stock=100)

        product_addon = create_product(product_class="Cheap Stuff")
        create_stockrecord(product_addon, D("10.00"), num_in_stock=100)

        # Create 3 ranges, one for each product we just made
        range_main = Range.objects.create(name="Expensive Stuff")
        range_main.add_product(product_main)

        range_accessories = Range.objects.create(name="Less Expensive Stuff")
        range_accessories.add_product(product_accessory)

        range_addons = Range.objects.create(name="Cheap Stuff")
        range_addons.add_product(product_addon)

        # Create an offer which gives $5 off an add-on product when the basket contains both a main
        # and an accessory product. This offer, when applied, should consume the main, accessory, and
        # add-on product. Not just the add-on.
        cond_has_main = Condition()
        cond_has_main.proxy_class = (
            "oscarbluelight.offer.conditions.BluelightCountCondition"
        )
        cond_has_main.value = 1
        cond_has_main.range = range_main
        cond_has_main.save()

        cond_has_accessory = Condition()
        cond_has_accessory.proxy_class = (
            "oscarbluelight.offer.conditions.BluelightCountCondition"
        )
        cond_has_accessory.value = 1
        cond_has_accessory.range = range_accessories
        cond_has_accessory.save()

        cond_has_main_and_accessory = CompoundCondition()
        cond_has_main_and_accessory.proxy_class = (
            "oscarbluelight.offer.conditions.CompoundCondition"
        )
        cond_has_main_and_accessory.conjunction = Conjunction.AND
        cond_has_main_and_accessory.save()
        cond_has_main_and_accessory.subconditions.set(
            [cond_has_main, cond_has_accessory]
        )

        benefit_5off_addon = Benefit()
        benefit_5off_addon.proxy_class = (
            "oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit"
        )
        benefit_5off_addon.value = 5
        benefit_5off_addon.range = range_addons
        benefit_5off_addon.save()

        offer = ConditionalOffer()
        offer.condition = cond_has_main_and_accessory
        offer.benefit = benefit_5off_addon
        offer.save()

        basket = create_basket(empty=True)
        basket.add_product(product_main, quantity=1)
        basket.add_product(product_accessory, quantity=1)
        basket.add_product(product_addon, quantity=1)

        self.assertEqual(basket.total_excl_tax_excl_discounts, D("5110.00"))
        self.assertEqual(basket.total_excl_tax, D("5110.00"))
        self.assertEqual(basket.num_items_without_discount, 3)
        self.assertEqual(basket.num_items_with_discount, 0)

        Applicator().apply_offers(basket, [offer])

        self.assertEqual(basket.total_excl_tax_excl_discounts, D("5110.00"))
        self.assertEqual(basket.total_excl_tax, D("5105.00"))
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.num_items_with_discount, 3)

    def test_consume_items_when_child_conditions_differ_in_type(self):
        # Create two products, each in a different product class
        product_main = create_product(product_class="Expensive Stuff")
        create_stockrecord(product_main, D("5000.00"), num_in_stock=100)

        product_accessory = create_product(product_class="Less Expensive Stuff")
        create_stockrecord(product_accessory, D("100.00"), num_in_stock=100)

        # Create two ranges, one for each product we just made
        range_main = Range.objects.create(name="Expensive Stuff")
        range_main.add_product(product_main)

        range_accessories = Range.objects.create(name="Less Expensive Stuff")
        range_accessories.add_product(product_accessory)

        # Create an offer which gives $50 off an accessory product when the basket contains a main
        # product and the basket is over $7,000.
        cond_has_main = Condition()
        cond_has_main.proxy_class = (
            "oscarbluelight.offer.conditions.BluelightCountCondition"
        )
        cond_has_main.value = 1
        cond_has_main.range = range_main
        cond_has_main.save()

        cond_over_7000 = Condition()
        cond_over_7000.proxy_class = (
            "oscarbluelight.offer.conditions.BluelightValueCondition"
        )
        cond_over_7000.value = D("7000.00")
        cond_over_7000.range = range_main
        cond_over_7000.save()

        cond_has_main_and_over_7000 = CompoundCondition()
        cond_has_main_and_over_7000.proxy_class = (
            "oscarbluelight.offer.conditions.CompoundCondition"
        )
        cond_has_main_and_over_7000.conjunction = Conjunction.AND
        cond_has_main_and_over_7000.save()
        cond_has_main_and_over_7000.subconditions.set([cond_has_main, cond_over_7000])

        benefit_50off_addon = Benefit()
        benefit_50off_addon.proxy_class = (
            "oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit"
        )
        benefit_50off_addon.value = 50
        benefit_50off_addon.range = range_accessories
        benefit_50off_addon.save()

        offer = ConditionalOffer()
        offer.condition = cond_has_main_and_over_7000
        offer.benefit = benefit_50off_addon
        offer.save()

        basket = create_basket(empty=True)
        basket.add_product(product_main, quantity=1)
        basket.add_product(product_accessory, quantity=1)

        self.assertEqual(basket.total_excl_tax_excl_discounts, D("5100.00"))
        self.assertEqual(basket.total_excl_tax, D("5100.00"))
        self.assertEqual(basket.num_items_without_discount, 2)
        self.assertEqual(basket.num_items_with_discount, 0)

        Applicator().apply_offers(basket, [offer])

        self.assertEqual(basket.total_excl_tax_excl_discounts, D("5100.00"))
        self.assertEqual(basket.total_excl_tax, D("5100.00"))
        self.assertEqual(basket.num_items_without_discount, 2)
        self.assertEqual(basket.num_items_with_discount, 0)

        basket.add_product(product_main, quantity=1)

        self.assertEqual(basket.total_excl_tax_excl_discounts, D("10100.00"))
        self.assertEqual(basket.total_excl_tax, D("10100.00"))
        self.assertEqual(basket.num_items_without_discount, 3)
        self.assertEqual(basket.num_items_with_discount, 0)

        Applicator().apply_offers(basket, [offer])

        self.assertEqual(basket.total_excl_tax_excl_discounts, D("10100.00"))
        self.assertEqual(basket.total_excl_tax, D("10050.00"))
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.num_items_with_discount, 3)


class ConditionURL(TestCase):
    def setUp(self):
        self.client = Client()
        self.all_products = Range()
        self.all_products.includes_all_products = True
        self.all_products.save()
        self.condition = Condition()
        self.condition.proxy_class = (
            "oscarbluelight.offer.conditions.BluelightCountCondition"
        )
        self.condition.value = 5
        self.condition.range = self.all_products
        self.condition.save()
        self.user = User.objects.create_user(
            "john", "lennon@thebeatles.com", "johnpassword", is_staff=True
        )
        self.user.save()

    def test_get(self):
        self.client.login(username="john", password="johnpassword")
        response = self.client.get(reverse("dashboard:condition-list"))
        self.assertEqual(response.status_code, 200)


class ConditionListViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "john", "john@example.com", "password", is_staff=True, is_superuser=True
        )
        self.client = Client()
        self.client.login(username="john", password="password")
        self.base_url = reverse("dashboard:condition-list")
        self.view = ConditionListView()

        all_products = Range()
        all_products.name = "site"
        all_products.includes_all_products = True
        all_products.save()

        self.cond = Condition()
        self.cond.proxy_class = (
            "oscarbluelight.offer.conditions.BluelightValueCondition"
        )
        self.cond.value = 10
        self.cond.range = all_products
        self.cond.save()

        benefit = Benefit()
        benefit.proxy_class = (
            "oscarbluelight.offer.benefits.BluelightShippingFixedPriceBenefit"
        )
        benefit.value = 0
        benefit.save()

        start_dt = timezone.now() - timedelta(days=1)
        end_dt = timezone.now() + timedelta(days=1)

        for i in range(1, 4):
            ConditionalOffer.objects.create(
                pk=i,
                name=f"Non-Voucher Offer {i}",
                condition=self.cond,
                benefit=benefit,
                offer_type=ConditionalOffer.SITE,
                start_datetime=start_dt,
                end_datetime=end_dt,
            )

        for i in range(4, 9):
            offer = ConditionalOffer.objects.create(
                pk=i,
                name=f"Voucher Offer {i}",
                condition=self.cond,
                benefit=benefit,
                offer_type=ConditionalOffer.VOUCHER,
                start_datetime=start_dt,
                end_datetime=end_dt,
            )
            voucher = Voucher.objects.create(
                pk=i,
                name=f"Voucher {i}",
                code=f"voucher-{i}",
                usage=Voucher.MULTI_USE,
                start_datetime=start_dt,
                end_datetime=end_dt,
            )
            voucher.offers.add(offer)

    def test__get_items_for_condition(self):
        result = self.view._get_items_for_condition(self.cond.pk, "non_voucher_offers")
        self.assertDictEqual(
            result,
            {
                "items": [
                    {"pk": 1, "name": "Non-Voucher Offer 1"},
                    {"pk": 2, "name": "Non-Voucher Offer 2"},
                    {"pk": 3, "name": "Non-Voucher Offer 3"},
                ],
                "has_next": False,
            },
        )
        result = self.view._get_items_for_condition(self.cond.pk, "vouchers")
        self.assertDictEqual(
            result,
            {
                "items": [
                    {"pk": 4, "name": "Voucher 4"},
                    {"pk": 5, "name": "Voucher 5"},
                    {"pk": 6, "name": "Voucher 6"},
                    {"pk": 7, "name": "Voucher 7"},
                    {"pk": 8, "name": "Voucher 8"},
                ],
                "has_next": False,
            },
        )
        self.view.items_per_object = 2
        result = self.view._get_items_for_condition(
            self.cond.pk, "non_voucher_offers", 1
        )
        self.assertDictEqual(
            result,
            {
                "items": [
                    {"pk": 1, "name": "Non-Voucher Offer 1"},
                    {"pk": 2, "name": "Non-Voucher Offer 2"},
                ],
                "has_next": True,
            },
        )
        result = self.view._get_items_for_condition(self.cond.pk, "vouchers", 2)
        self.assertDictEqual(
            result,
            {
                "items": [
                    {"pk": 6, "name": "Voucher 6"},
                    {"pk": 7, "name": "Voucher 7"},
                ],
                "has_next": True,
            },
        )

    def test_get_missing_parameters_with_ajax_request(self):
        resp = self.client.get(
            f"{self.base_url}?{urlencode({'condition_pk': self.cond.pk})}",
            headers={"x-requested-with": "XMLHttpRequest"},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json(), {"error": "Missing required parameters: condition_pk, type"}
        )
        resp = self.client.get(
            f"{self.base_url}?{urlencode({'type': 'vouchers'})}",
            headers={"x-requested-with": "XMLHttpRequest"},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json(), {"error": "Missing required parameters: condition_pk, type"}
        )

    def test_get_invalid_item_type_with_ajax_request(self):
        resp = self.client.get(
            f"{self.base_url}?{urlencode({'condition_pk': self.cond.pk, 'type': 'invalid_type'})}",
            headers={"x-requested-with": "XMLHttpRequest"},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json(), {"error": "Invalid item type for Condition: invalid_type"}
        )

    def test_get_valid_request_with_ajax_request(self):
        resp = self.client.get(
            f"{self.base_url}?{urlencode({'condition_pk': self.cond.pk, 'type': 'non_voucher_offers'})}",
            headers={"x-requested-with": "XMLHttpRequest"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertDictEqual(
            data,
            {
                "items": [
                    {"pk": 1, "name": "Non-Voucher Offer 1"},
                    {"pk": 2, "name": "Non-Voucher Offer 2"},
                    {"pk": 3, "name": "Non-Voucher Offer 3"},
                ],
                "has_next": False,
            },
        )
        ConditionListView.items_per_object = 1
        resp = self.client.get(
            f"{self.base_url}?{urlencode({'condition_pk': self.cond.pk, 'type': 'non_voucher_offers', 'page': 3})}",
            headers={"x-requested-with": "XMLHttpRequest"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertDictEqual(
            data,
            {
                "items": [{"pk": 3, "name": "Non-Voucher Offer 3"}],
                "has_next": False,
            },
        )

    def test_get_context_data(self):
        self.view.items_per_object = 3
        request = RequestFactory().get(
            f"{self.base_url}?{urlencode({'condition_pk': self.cond.pk, 'type': 'non_voucher_offers'})}",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        request.user = self.user
        self.view.request = request
        self.view.object_list = self.view.get_queryset()
        context = self.view.get_context_data()
        self.assertIn("queryset_description", context)
        self.assertIn("form", context)
        self.assertIn("is_filtered", context)
        self.assertEqual(len(context["conditions"]), 1)
        self.assertDictEqual(
            context["conditions"][0].initial_offers,
            {
                "items": [
                    {"pk": 1, "name": "Non-Voucher Offer 1"},
                    {"pk": 2, "name": "Non-Voucher Offer 2"},
                    {"pk": 3, "name": "Non-Voucher Offer 3"},
                ],
                "has_next": False,
            },
        )
        self.assertDictEqual(
            context["conditions"][0].initial_vouchers,
            {
                "items": [
                    {"pk": 4, "name": "Voucher 4"},
                    {"pk": 5, "name": "Voucher 5"},
                    {"pk": 6, "name": "Voucher 6"},
                ],
                "has_next": True,
            },
        )

    def test_get_with_non_ajax_request(self):
        with patch("django.views.generic.ListView.get") as mock_super_class_get:
            mock_super_class_get.return_value = HttpResponse("<h1>Test</h1>")
            self.client.get(self.base_url)
            mock_super_class_get.assert_called_once()
            mock_super_class_get.reset_mock()
            self.client.get(
                f"{self.base_url}?{urlencode({'condition_pk': self.cond.pk, 'type': 'non_voucher_offers'})}",
                headers={"x-requested-with": "XMLHttpRequest"},
            )
            mock_super_class_get.assert_not_called()
