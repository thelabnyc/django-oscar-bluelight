from decimal import Decimal as D
from django.test import TestCase
from oscar.test import factories
from oscar.test.basket import add_product
from django_redis import get_redis_connection
from oscarbluelight.offer.models import (
    Condition,
    ConditionalOffer,
    Range,
    Benefit,
    CompoundCondition,
    BluelightCountCondition,
    BluelightFixedPricePerItemBenefit,
)
from oscarbluelight.offer.constants import Conjunction
from .base import BaseTest
from unittest import mock


class TestAFixedPricePerItemDiscountAppliedWithCountCondition(TestCase):
    def setUp(self):
        # Flush the cache
        conn = get_redis_connection("redis")
        conn.flushall()

        range = Range.objects.create(name="All products", includes_all_products=True)
        self.condition = BluelightCountCondition.objects.create(
            range=range,
            proxy_class="oscarbluelight.offer.conditions.BluelightCountCondition",
            value=3,
        )
        self.benefit = BluelightFixedPricePerItemBenefit.objects.create(
            range=range,
            proxy_class="oscarbluelight.offer.benefits.BluelightFixedPricePerItemBenefit",
            value=D("20.00"),
        )
        self.offer = mock.Mock()
        self.basket = factories.create_basket(empty=True)

    def test_name(self):
        self.assertEqual(
            self.benefit.name,
            "The products in the range are sold for $20.00 each; no maximum",
        )

    def test_description(self):
        self.assertEqual(
            self.benefit.description,
            "The products in the range are sold for $20.00 each; no maximum",
        )

    def test_description_with_max_items(self):
        self.benefit.max_affected_items = 1
        self.assertEqual(
            self.benefit.description,
            "The products in the range are sold for $20.00 each; maximum 1 item(s)",
        )

    def test_applies_correctly_to_empty_basket(self):
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("0.00"), result.discount)
        self.assertEqual(0, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

    def test_applies_correctly_to_items_which_are_worth_less_than_value(self):
        add_product(self.basket, D("6.00"), 3)
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("0.00"), result.discount)
        self.assertEqual(0, self.basket.num_items_with_discount)
        self.assertEqual(3, self.basket.num_items_without_discount)

    def test_applies_correctly_to_items_which_are_worth_the_same_as_value(self):
        add_product(self.basket, D("20.00"), 4)
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("0.00"), result.discount)
        self.assertEqual(0, self.basket.num_items_with_discount)
        self.assertEqual(4, self.basket.num_items_without_discount)

    def test_applies_correctly_to_items_which_are_more_than_value(self):
        add_product(self.basket, D("40.00"), 4)
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("80.00"), result.discount)
        self.assertEqual(4, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

    def test_obeys_max_discount_setting(self):
        self.benefit.max_discount = D("30.00")
        self.benefit.save()
        add_product(self.basket, D("40.00"), 4)
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("30.00"), result.discount)
        self.assertEqual(4, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

    def test_applies_correctly_to_items_which_are_more_than_value_and_max_affected_items_set(
        self,
    ):
        self.benefit.max_affected_items = 3
        self.benefit.save()
        add_product(self.basket, D("40.00"), 4)
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("60.00"), result.discount)
        self.assertEqual(3, self.basket.num_items_with_discount)
        self.assertEqual(1, self.basket.num_items_without_discount)

    def test_records_reason_for_discount_no_voucher(self):
        self.offer.name = "My Offer Name"
        self.offer.description = "My Offer Description"
        self.offer.get_voucher = mock.Mock()
        self.offer.get_voucher.return_value = None

        add_product(self.basket, D("40.00"), 5)
        # Apply benefit twice to simulate how Applicator will actually do it
        self.benefit.apply(self.basket, self.condition, self.offer)
        self.benefit.apply(self.basket, self.condition, self.offer)

        line = self.basket.all_lines()[0]
        descrs = line.get_discount_descriptions()
        self.assertEqual(len(descrs), 1)
        self.assertEqual(descrs[0].amount, D("100.00"))
        self.assertEqual(descrs[0].offer_name, "My Offer Name")
        self.assertEqual(descrs[0].offer_description, "My Offer Description")
        self.assertIsNone(descrs[0].voucher_name)
        self.assertIsNone(descrs[0].voucher_code)

    def test_records_reason_for_discount_with_voucher(self):
        voucher = mock.Mock()
        voucher.name = "My Voucher"
        voucher.code = "SWEETDEAL"
        self.offer.name = "Offer for Voucher"
        self.offer.description = ""
        self.offer.get_voucher = mock.Mock()
        self.offer.get_voucher.return_value = voucher

        add_product(self.basket, D("40.00"), 5)
        # Apply benefit twice to simulate how Applicator will actually do it
        self.benefit.apply(self.basket, self.condition, self.offer)
        self.benefit.apply(self.basket, self.condition, self.offer)

        line = self.basket.all_lines()[0]
        descrs = line.get_discount_descriptions()
        self.assertEqual(len(descrs), 1)
        self.assertEqual(descrs[0].amount, D("100.00"))
        self.assertEqual(descrs[0].offer_name, "Offer for Voucher")
        self.assertEqual(descrs[0].offer_description, "")
        self.assertEqual(descrs[0].voucher_name, "My Voucher")
        self.assertEqual(descrs[0].voucher_code, "SWEETDEAL")


class FixedPriceBenefitCompoundConditionTest(BaseTest):
    def test_apply_with_compound_condition(self):
        basket = self._build_basket()

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
        condition.conjunction = Conjunction.OR
        condition.save()
        condition.subconditions.set([cond_a, cond_b])
        condition.save()

        benefit = Benefit()
        benefit.proxy_class = (
            "oscarbluelight.offer.benefits.BluelightFixedPricePerItemBenefit"
        )
        benefit.value = 0
        benefit.range = all_products
        benefit.max_affected_items = 3
        benefit.save()

        offer = ConditionalOffer()
        offer.condition = condition
        offer.benefit = benefit
        offer.save()

        line = basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 0)
        self.assertEqual(line.quantity_without_discount, 5)

        discount = offer.apply_benefit(basket)

        line = basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 3)
        self.assertEqual(line.quantity_without_discount, 2)

        self.assertEqual(discount.discount, D("30.00"))
        self.assertEqual(basket.total_excl_tax_excl_discounts, D("50.00"))
        self.assertEqual(basket.total_excl_tax, D("20.00"))
