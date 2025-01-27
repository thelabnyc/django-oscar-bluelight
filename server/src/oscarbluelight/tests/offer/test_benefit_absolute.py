from decimal import Decimal as D
from unittest import mock

from django.core import exceptions
from django.test import TestCase, TransactionTestCase
from django_redis import get_redis_connection
from oscar.apps.offer.utils import Applicator
from oscar.test import factories
from oscar.test.basket import add_product, add_products

from oscarbluelight.offer.models import (
    Benefit,
    BluelightAbsoluteDiscountBenefit,
    BluelightCountCondition,
    BluelightValueCondition,
    ConditionalOffer,
    Range,
)


class TestAnAbsoluteDiscountAppliedWithCountConditionOnDifferentRange(
    TransactionTestCase
):
    def setUp(self):
        # Flush the cache
        conn = get_redis_connection("redis")
        conn.flushall()

        self.condition_product = factories.ProductFactory()
        condition_range = factories.RangeFactory()
        condition_range.add_product(self.condition_product)
        self.condition = BluelightCountCondition.objects.create(
            range=condition_range,
            proxy_class="oscarbluelight.offer.conditions.BluelightCountCondition",
            value=2,
        )

        self.benefit_product = factories.ProductFactory()
        benefit_range = factories.RangeFactory()
        benefit_range.add_product(self.benefit_product)
        self.benefit = BluelightAbsoluteDiscountBenefit.objects.create(
            range=benefit_range,
            proxy_class="oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit",
            value=D("3.00"),
        )

        self.offer = ConditionalOffer(
            id=1, condition=self.condition, benefit=self.benefit
        )
        self.basket = factories.create_basket(empty=True)

        self.applicator = Applicator()

    def test_succcessful_application_consumes_correctly(self):
        add_product(self.basket, product=self.condition_product, quantity=2)
        add_product(self.basket, product=self.benefit_product, quantity=1)

        self.applicator.apply_offers(self.basket, [self.offer])

        discounts = self.basket.offer_applications.offer_discounts
        self.assertEqual(len(discounts), 1)
        self.assertEqual(discounts[0]["freq"], 1)

    def test_condition_is_consumed_correctly(self):
        # Testing an error case reported on the mailing list
        add_product(self.basket, product=self.condition_product, quantity=3)
        add_product(self.basket, product=self.benefit_product, quantity=2)

        self.applicator.apply_offers(self.basket, [self.offer])

        discounts = self.basket.offer_applications.offer_discounts
        self.assertEqual(len(discounts), 1)
        self.assertEqual(discounts[0]["freq"], 1)


class TestAnAbsoluteDiscountAppliedWithCountCondition(TestCase):
    def setUp(self):
        # Flush the cache
        conn = get_redis_connection("redis")
        conn.flushall()

        range = Range.objects.create(name="All products", includes_all_products=True)
        self.condition = BluelightCountCondition.objects.create(
            range=range,
            proxy_class="oscarbluelight.offer.conditions.BluelightCountCondition",
            value=2,
        )
        self.offer = mock.Mock()
        self.benefit = BluelightAbsoluteDiscountBenefit.objects.create(
            range=range,
            proxy_class="oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit",
            value=D("3.00"),
        )
        self.basket = factories.create_basket(empty=True)

    def test_applies_correctly_to_empty_basket(self):
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("0.00"), result.discount)
        self.assertEqual(0, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

    def test_applies_correctly_to_basket_which_matches_condition_with_one_line(self):
        add_product(self.basket, price=D("12.00"), quantity=2)
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("3.00"), result.discount)
        self.assertEqual(2, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

        # Check the discount is applied equally to each item in the line
        line = self.basket.all_lines()[0]
        prices = line.get_price_breakdown()
        self.assertEqual(1, len(prices))
        self.assertEqual(D("10.50"), prices[0][0])

    def test_applies_correctly_to_basket_which_matches_condition_with_multiple_lines(
        self,
    ):
        # Use a basket with 2 lines
        add_products(self.basket, [(D("12.00"), 1), (D("12.00"), 1)])
        result = self.benefit.apply(self.basket, self.condition, self.offer)

        self.assertTrue(result.is_successful)
        self.assertFalse(result.is_final)
        self.assertEqual(D("3.00"), result.discount)
        self.assertEqual(2, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

        # Check the discount is applied equally to each line
        for line in self.basket.all_lines():
            self.assertEqual(D("1.50"), line.discount_value)

    def test_applies_correctly_to_basket_which_matches_condition_with_multiple_lines_and_lower_total_value(
        self,
    ):
        # Use a basket with 2 lines
        add_products(self.basket, [(D("1.00"), 1), (D("1.50"), 1)])
        result = self.benefit.apply(self.basket, self.condition, self.offer)

        self.assertTrue(result.is_successful)
        self.assertFalse(result.is_final)
        self.assertEqual(D("2.50"), result.discount)
        self.assertEqual(2, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

    def test_applies_correctly_to_basket_which_exceeds_condition(self):
        add_products(self.basket, [(D("12.00"), 2), (D("10.00"), 2)])
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("3.00"), result.discount)
        self.assertEqual(4, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

    def test_applies_correctly_to_basket_which_exceeds_condition_with_smaller_prices_than_discount(
        self,
    ):
        add_products(self.basket, [(D("2.00"), 2), (D("4.00"), 2)])
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("3.00"), result.discount)
        self.assertEqual(4, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

    def test_applies_correctly_to_basket_which_exceeds_condition_with_smaller_prices_than_discount_and_higher_prices_first(
        self,
    ):
        add_products(self.basket, [(D("2.00"), 2), (D("4.00"), 2)])
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("3.00"), result.discount)
        self.assertEqual(4, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)


class TestAnAbsoluteDiscount(TestCase):
    def setUp(self):
        # Flush the cache
        conn = get_redis_connection("redis")
        conn.flushall()

        range = Range.objects.create(name="All products", includes_all_products=True)
        self.condition = BluelightCountCondition.objects.create(
            range=range,
            proxy_class="oscarbluelight.offer.conditions.BluelightCountCondition",
            value=2,
        )
        self.benefit = BluelightAbsoluteDiscountBenefit.objects.create(
            range=range,
            proxy_class="oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit",
            value=D("4.00"),
        )
        self.offer = mock.Mock()
        self.basket = factories.create_basket(empty=True)

    def test_applies_correctly_when_discounts_need_rounding(self):
        # Split discount across 3 lines
        for price in [D("2.00"), D("2.00"), D("2.00")]:
            add_product(self.basket, price)
        result = self.benefit.apply(self.basket, self.condition, self.offer)

        self.assertEqual(D("4.00"), result.discount)
        # Check the discount is applied equally to each line
        line_discounts = [line.discount_value for line in self.basket.all_lines()]
        self.assertEqual(len(line_discounts), 3)
        for i, v in enumerate([D("1.33"), D("1.33"), D("1.34")]):
            self.assertEqual(line_discounts[i], v)

    def test_obeys_max_discount_setting(self):
        self.benefit.max_discount = D("3.00")
        self.benefit.save()

        add_product(self.basket, D("5.00"))
        # Apply benefit twice to simulate how Applicator will actually do it
        self.benefit.apply(self.basket, self.condition, self.offer)
        self.benefit.apply(self.basket, self.condition, self.offer)

        line = self.basket.all_lines()[0]
        descrs = line.get_discount_descriptions()
        self.assertEqual(len(descrs), 1)
        self.assertEqual(descrs[0].amount, D("3.00"))

    def test_records_reason_for_discount_no_voucher(self):
        self.offer.name = "My Offer Name"
        self.offer.description = "My Offer Description"
        self.offer.get_voucher = mock.Mock()
        self.offer.get_voucher.return_value = None

        add_product(self.basket, D("5.00"))
        # Apply benefit twice to simulate how Applicator will actually do it
        self.benefit.apply(self.basket, self.condition, self.offer)
        self.benefit.apply(self.basket, self.condition, self.offer)

        line = self.basket.all_lines()[0]
        descrs = line.get_discount_descriptions()
        self.assertEqual(len(descrs), 1)
        self.assertEqual(descrs[0].amount, D("4.00"))
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

        add_product(self.basket, D("5.00"))
        # Apply benefit twice to simulate how Applicator will actually do it
        self.benefit.apply(self.basket, self.condition, self.offer)
        self.benefit.apply(self.basket, self.condition, self.offer)

        line = self.basket.all_lines()[0]
        descrs = line.get_discount_descriptions()
        self.assertEqual(len(descrs), 1)
        self.assertEqual(descrs[0].amount, D("4.00"))
        self.assertEqual(descrs[0].offer_name, "Offer for Voucher")
        self.assertEqual(descrs[0].offer_description, "")
        self.assertEqual(descrs[0].voucher_name, "My Voucher")
        self.assertEqual(descrs[0].voucher_code, "SWEETDEAL")


class TestAnAbsoluteDiscountWithMaxItemsSetAppliedWithCountCondition(TestCase):
    def setUp(self):
        # Flush the cache
        conn = get_redis_connection("redis")
        conn.flushall()

        range = Range.objects.create(name="All products", includes_all_products=True)
        self.condition = BluelightCountCondition.objects.create(
            range=range,
            proxy_class="oscarbluelight.offer.conditions.BluelightCountCondition",
            value=2,
        )
        self.benefit = BluelightAbsoluteDiscountBenefit.objects.create(
            range=range,
            proxy_class="oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit",
            value=D("3.00"),
            max_affected_items=1,
        )
        self.offer = mock.Mock()
        self.basket = factories.create_basket(empty=True)

    def test_applies_correctly_to_empty_basket(self):
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("0.00"), result.discount)
        self.assertEqual(0, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

    def test_applies_correctly_to_basket_which_matches_condition(self):
        add_product(self.basket, D("12.00"), 2)
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("3.00"), result.discount)
        self.assertEqual(2, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

    def test_applies_correctly_to_basket_which_exceeds_condition(self):
        add_products(self.basket, [(D("12.00"), 2), (D("10.00"), 2)])
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("3.00"), result.discount)
        self.assertEqual(2, self.basket.num_items_with_discount)
        self.assertEqual(2, self.basket.num_items_without_discount)

    def test_applies_correctly_to_basket_which_exceeds_condition_but_with_smaller_prices_than_discount(
        self,
    ):
        add_products(self.basket, [(D("2.00"), 2), (D("1.00"), 2)])
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("1.00"), result.discount)
        self.assertEqual(2, self.basket.num_items_with_discount)
        self.assertEqual(2, self.basket.num_items_without_discount)


class TestAnAbsoluteDiscountAppliedWithValueCondition(TestCase):
    def setUp(self):
        # Flush the cache
        conn = get_redis_connection("redis")
        conn.flushall()

        range = Range.objects.create(name="All products", includes_all_products=True)
        self.condition = BluelightValueCondition.objects.create(
            range=range,
            proxy_class="oscarbluelight.offer.conditions.BluelightValueCondition",
            value=D("10.00"),
        )
        self.benefit = BluelightAbsoluteDiscountBenefit.objects.create(
            range=range,
            proxy_class="oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit",
            value=D("3.00"),
        )
        self.offer = mock.Mock()
        self.basket = factories.create_basket(empty=True)

    def test_applies_correctly_to_empty_basket(self):
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("0.00"), result.discount)
        self.assertEqual(0, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

    def test_applies_correctly_to_single_item_basket_which_matches_condition(self):
        add_products(self.basket, [(D("10.00"), 1)])
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("3.00"), result.discount)
        self.assertEqual(1, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

    def test_applies_correctly_to_multi_item_basket_which_matches_condition(self):
        add_products(self.basket, [(D("5.00"), 2)])
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("3.00"), result.discount)
        self.assertEqual(2, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

    def test_applies_correctly_to_multi_item_basket_which_exceeds_condition(self):
        add_products(self.basket, [(D("4.00"), 3)])
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("3.00"), result.discount)
        self.assertEqual(3, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

    def test_applies_correctly_to_multi_item_basket_which_exceeds_condition_but_matches_boundary(
        self,
    ):
        add_products(self.basket, [(D("5.00"), 3)])
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("3.00"), result.discount)
        self.assertEqual(3, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)


class TestAnAbsoluteDiscountWithMaxItemsSetAppliedWithValueCondition(TestCase):
    def setUp(self):
        # Flush the cache
        conn = get_redis_connection("redis")
        conn.flushall()

        range = Range.objects.create(name="All products", includes_all_products=True)
        self.condition = BluelightValueCondition.objects.create(
            range=range,
            proxy_class="oscarbluelight.offer.conditions.BluelightValueCondition",
            value=D("10.00"),
        )
        self.benefit = BluelightAbsoluteDiscountBenefit.objects.create(
            range=range,
            proxy_class="oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit",
            value=D("3.00"),
            max_affected_items=1,
        )
        self.offer = mock.Mock()
        self.basket = factories.create_basket(empty=True)

    def test_applies_correctly_to_empty_basket(self):
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("0.00"), result.discount)
        self.assertEqual(0, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

    def test_applies_correctly_to_single_item_basket_which_matches_condition(self):
        add_products(self.basket, [(D("10.00"), 1)])
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("3.00"), result.discount)
        self.assertEqual(1, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

    def test_applies_correctly_to_multi_item_basket_which_matches_condition(self):
        add_products(self.basket, [(D("5.00"), 2)])
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("3.00"), result.discount)
        self.assertEqual(2, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

    def test_applies_correctly_to_multi_item_basket_which_exceeds_condition(self):
        add_products(self.basket, [(D("4.00"), 3)])
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("3.00"), result.discount)
        self.assertEqual(3, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

    def test_applies_correctly_to_multi_item_basket_which_exceeds_condition_but_matches_boundary(
        self,
    ):
        add_products(self.basket, [(D("5.00"), 3)])
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("3.00"), result.discount)
        self.assertEqual(2, self.basket.num_items_with_discount)
        self.assertEqual(1, self.basket.num_items_without_discount)

    def test_applies_correctly_to_multi_item_basket_which_matches_condition_but_with_lower_prices_than_discount(
        self,
    ):
        add_products(self.basket, [(D("2.00"), 6)])
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("2.00"), result.discount)
        self.assertEqual(5, self.basket.num_items_with_discount)
        self.assertEqual(1, self.basket.num_items_without_discount)


class TestAnAbsoluteDiscountBenefit(TestCase):
    def test_requires_a_benefit_value(self):
        rng = Range.objects.create(name="", includes_all_products=True)
        benefit = Benefit.objects.create(
            proxy_class="oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit",
            range=rng,
        )
        with self.assertRaises(exceptions.ValidationError):
            benefit.clean()
