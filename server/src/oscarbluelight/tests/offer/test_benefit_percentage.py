from decimal import Decimal as D
from django.core import exceptions
from django.test import TestCase
from oscar.test import factories
from oscar.test.basket import add_product, add_products
from django_redis import get_redis_connection
from oscarbluelight.offer.models import (
    Range,
    Benefit,
    BluelightCountCondition,
    BluelightValueCondition,
    BluelightPercentageDiscountBenefit,
)
from unittest import mock


class TestAPercentageDiscountAppliedWithCountCondition(TestCase):
    def setUp(self):
        # Flush the cache
        conn = get_redis_connection("redis")
        conn.flushall()

        range = Range.objects.create(name="All products", includes_all_products=True)
        self.condition = BluelightCountCondition(
            range=range,
            proxy_class="oscarbluelight.offer.conditions.BluelightCountCondition",
            value=2,
        )
        self.benefit = BluelightPercentageDiscountBenefit(
            range=range,
            proxy_class="oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit",
            value=20,
        )
        self.offer = mock.Mock()
        self.basket = factories.create_basket(empty=True)

    def test_applies_correctly_to_empty_basket(self):
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("0.00"), result.discount)
        self.assertEqual(0, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

    def test_applies_correctly_to_basket_with_no_discountable_products(self):
        product = factories.create_product(is_discountable=False)
        add_product(self.basket, D("12.00"), 2, product=product)
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("0.00"), result.discount)
        self.assertEqual(0, self.basket.num_items_with_discount)
        self.assertEqual(2, self.basket.num_items_without_discount)

    def test_applies_correctly_to_basket_which_matches_condition(self):
        add_product(self.basket, D("12.00"), 2)
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(2 * D("12.00") * D("0.2"), result.discount)
        self.assertEqual(2, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

    def test_applies_correctly_to_basket_which_exceeds_condition(self):
        add_product(self.basket, D("12.00"), 3)
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(3 * D("12.00") * D("0.2"), result.discount)
        self.assertEqual(3, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

    def test_obeys_max_discount_setting(self):
        self.benefit.max_discount = D("5.00")
        self.benefit.save()
        add_product(self.basket, D("12.00"), 3)
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("5.00"), result.discount)
        self.assertEqual(3, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

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
        self.assertEqual(descrs[0].amount, D("1.00"))
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
        self.assertEqual(descrs[0].amount, D("1.00"))
        self.assertEqual(descrs[0].offer_name, "Offer for Voucher")
        self.assertEqual(descrs[0].offer_description, "")
        self.assertEqual(descrs[0].voucher_name, "My Voucher")
        self.assertEqual(descrs[0].voucher_code, "SWEETDEAL")


class TestAPercentageDiscountWithMaxItemsSetAppliedWithCountCondition(TestCase):
    def setUp(self):
        # Flush the cache
        conn = get_redis_connection("redis")
        conn.flushall()

        range = Range.objects.create(name="All products", includes_all_products=True)
        self.condition = BluelightCountCondition(
            range=range,
            proxy_class="oscarbluelight.offer.conditions.BluelightCountCondition",
            value=2,
        )
        self.benefit = BluelightPercentageDiscountBenefit(
            range=range,
            proxy_class="oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit",
            value=20,
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
        self.assertEqual(1 * D("12.00") * D("0.2"), result.discount)
        self.assertEqual(2, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

    def test_applies_correctly_to_basket_which_exceeds_condition(self):
        add_products(self.basket, [(D("12.00"), 2), (D("20.00"), 2)])
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(1 * D("12.00") * D("0.2"), result.discount)
        # Should only consume the condition products
        self.assertEqual(2, self.basket.num_items_with_discount)
        self.assertEqual(2, self.basket.num_items_without_discount)


class TestAPercentageDiscountWithMultipleApplicationsWithCountCondition(TestCase):
    def setUp(self):
        # Flush the cache
        conn = get_redis_connection("redis")
        conn.flushall()

        self.range_mattresses = Range.objects.create(name="Mattresses")
        self.range_slippers = Range.objects.create(name="Slippers")

        self.mattress = factories.create_product(title="Mattress", price=D("2999.00"))
        self.slipper1 = factories.create_product(title="Slipper", price=D("78.00"))
        self.slipper2 = factories.create_product(title="Slipper", price=D("79.00"))

        self.range_mattresses.add_product(self.mattress)
        self.range_slippers.add_product(self.slipper1)
        self.range_slippers.add_product(self.slipper2)

        self.condition = BluelightCountCondition.objects.create(
            range=self.range_mattresses,
            proxy_class="oscarbluelight.offer.conditions.BluelightCountCondition",
            value=1,
        )

        self.benefit = BluelightPercentageDiscountBenefit.objects.create(
            range=self.range_slippers,
            proxy_class="oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit",
            value=D("100.00"),
            max_affected_items=1,
        )

        self.offer = mock.Mock()
        self.basket = factories.create_basket(empty=True)

    def test_applies_correctly_to_basket_which_matches_multiple_lines_multiple_times(
        self,
    ):
        # Add two different lines to the basket
        self.basket.add_product(self.mattress, 2)
        self.basket.add_product(self.slipper1, 1)
        self.basket.add_product(self.slipper2, 1)
        # Apply once
        self.assertTrue(self.condition.proxy().is_satisfied(self.offer, self.basket))
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertTrue(result.is_successful)
        self.assertEqual(result.discount, D("78.00"))
        self.assertEqual(self.basket.num_items_with_discount, 2)
        self.assertEqual(self.basket.num_items_without_discount, 2)
        # Apply second time
        self.assertTrue(self.condition.proxy().is_satisfied(self.offer, self.basket))
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertTrue(result.is_successful)
        self.assertEqual(result.discount, D("79.00"))
        self.assertEqual(self.basket.num_items_with_discount, 4)
        self.assertEqual(self.basket.num_items_without_discount, 0)
        # Can't apply a third time because the condition is no longer satisfied
        self.assertFalse(self.condition.proxy().is_satisfied(self.offer, self.basket))


class TestAPercentageDiscountAppliedWithValueCondition(TestCase):
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
        self.benefit = BluelightPercentageDiscountBenefit.objects.create(
            range=range,
            proxy_class="oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit",
            value=20,
        )
        self.offer = mock.Mock()
        self.basket = factories.create_basket(empty=True)

    def test_applies_correctly_to_empty_basket(self):
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D("0.00"), result.discount)
        self.assertEqual(0, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

    def test_applies_correctly_to_basket_which_matches_condition(self):
        add_product(self.basket, D("5.00"), 2)
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(2 * D("5.00") * D("0.2"), result.discount)
        self.assertEqual(2, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

    def test_applies_correctly_to_basket_which_exceeds_condition_but_matches_on_boundary(
        self,
    ):
        add_product(self.basket, D("5.00"), 3)
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(3 * D("5.00") * D("0.2"), result.discount)
        self.assertEqual(3, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

    def test_applies_correctly_to_basket_which_exceeds_condition(self):
        add_product(self.basket, D("4.00"), 3)
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(3 * D("4.00") * D("0.2"), result.discount)
        self.assertEqual(3, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)


class TestAPercentageDiscountWithMaxItemsSetAppliedWithValueCondition(TestCase):
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
        self.benefit = BluelightPercentageDiscountBenefit.objects.create(
            range=range,
            proxy_class="oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit",
            value=20,
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
        add_product(self.basket, D("5.00"), 2)
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(1 * D("5.00") * D("0.2"), result.discount)
        self.assertEqual(2, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)

    def test_applies_correctly_to_basket_which_exceeds_condition_but_matches_on_boundary(
        self,
    ):
        add_product(self.basket, D("5.00"), 3)
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(1 * D("5.00") * D("0.2"), result.discount)
        self.assertEqual(2, self.basket.num_items_with_discount)
        self.assertEqual(1, self.basket.num_items_without_discount)

    def test_applies_correctly_to_basket_which_exceeds_condition(self):
        add_product(self.basket, D("4.00"), 3)
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(1 * D("4.00") * D("0.2"), result.discount)
        self.assertEqual(3, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)


class TestAPercentageDiscountBenefit(TestCase):
    def setUp(self):
        # Flush the cache
        conn = get_redis_connection("redis")
        conn.flushall()

    def test_requires_a_benefit_value(self):
        rng = Range.objects.create(name="", includes_all_products=True)
        benefit = Benefit.objects.create(
            range=rng,
            proxy_class="oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit",
        )
        with self.assertRaises(exceptions.ValidationError):
            benefit.clean()
