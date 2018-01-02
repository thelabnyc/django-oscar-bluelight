from decimal import Decimal as D
from django.test import TestCase
from oscar.test import factories
from oscar.test.basket import add_product, add_products
from oscarbluelight.offer.models import (
    Condition,
    ConditionalOffer,
    Range,
    Benefit,
    CompoundCondition,
    BluelightCountCondition,
    BluelightFixedPriceBenefit,
)
from .base import BaseTest
import mock


class TestAFixedPriceDiscountAppliedWithCountCondition(TestCase):
    def setUp(self):
        range = Range.objects.create(
            name="All products", includes_all_products=True)
        self.condition = BluelightCountCondition.objects.create(
            range=range,
            type=Condition.COUNT,
            value=3)
        self.benefit = BluelightFixedPriceBenefit.objects.create(
            range=range,
            type=Benefit.FIXED_PRICE,
            value=D('20.00'))
        self.offer = mock.Mock()
        self.basket = factories.create_basket(empty=True)


    def test_applies_correctly_to_empty_basket(self):
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D('0.00'), result.discount)
        self.assertEqual(0, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)


    def test_applies_correctly_to_basket_which_is_worth_less_than_value(self):
        add_product(self.basket, D('6.00'), 3)
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D('0.00'), result.discount)
        self.assertEqual(0, self.basket.num_items_with_discount)
        self.assertEqual(3, self.basket.num_items_without_discount)


    def test_applies_correctly_to_basket_which_is_worth_the_same_as_value(self):
        add_product(self.basket, D('5.00'), 4)
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D('0.00'), result.discount)
        self.assertEqual(0, self.basket.num_items_with_discount)
        self.assertEqual(4, self.basket.num_items_without_discount)


    def test_applies_correctly_to_basket_which_is_more_than_value(self):
        add_product(self.basket, D('8.00'), 4)
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D('12.00'), result.discount)
        self.assertEqual(4, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)


    def test_applies_correctly_to_basket_which_is_more_than_value_and_max_affected_items_set(self):
        self.benefit.max_affected_items = 3
        self.benefit.save()
        add_product(self.basket, D('8.00'), 4)
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D('4.00'), result.discount)
        self.assertEqual(3, self.basket.num_items_with_discount)
        self.assertEqual(1, self.basket.num_items_without_discount)


    def test_rounding_error_for_multiple_products(self):
        add_products(self.basket,
                     [(D('7.00'), 1), (D('7.00'), 1), (D('7.00'), 1)])
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D('1.00'), result.discount)
        # Make sure discount together is the same as final discount
        # Rounding error would return 0.99 instead 1.00
        cumulative_discount = sum(
            line.discount_value for line in self.basket.all_lines())
        self.assertEqual(result.discount, cumulative_discount)
        self.assertEqual(3, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)


    def test_records_reason_for_discount_no_voucher(self):
        self.offer.name = "My Offer Name"
        self.offer.description = "My Offer Description"
        self.offer.get_voucher = mock.Mock()
        self.offer.get_voucher.return_value = None

        add_product(self.basket, D('5.00'), 5)
        self.benefit.apply(self.basket, self.condition, self.offer)

        line = self.basket.all_lines()[0]
        descrs = line.get_discount_descriptions()
        self.assertEqual(len(descrs), 1)
        self.assertEqual(descrs[0].amount, D('5.00'))
        self.assertEqual(descrs[0].offer_name, 'My Offer Name')
        self.assertEqual(descrs[0].offer_description, 'My Offer Description')
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

        add_product(self.basket, D('5.00'), 5)
        self.benefit.apply(self.basket, self.condition, self.offer)

        line = self.basket.all_lines()[0]
        descrs = line.get_discount_descriptions()
        self.assertEqual(len(descrs), 1)
        self.assertEqual(descrs[0].amount, D('5.00'))
        self.assertEqual(descrs[0].offer_name, 'Offer for Voucher')
        self.assertEqual(descrs[0].offer_description, '')
        self.assertEqual(descrs[0].voucher_name, 'My Voucher')
        self.assertEqual(descrs[0].voucher_code, 'SWEETDEAL')



class FixedPriceBenefitCompoundConditionTest(BaseTest):
    def test_apply_with_compound_condition(self):
        basket = self._build_basket()

        all_products = Range()
        all_products.name = 'site'
        all_products.includes_all_products = True
        all_products.save()

        cond_a = Condition()
        cond_a.proxy_class = 'oscarbluelight.offer.conditions.BluelightValueCondition'
        cond_a.value = 10
        cond_a.range = all_products
        cond_a.save()

        cond_b = Condition()
        cond_b.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        cond_b.value = 2
        cond_b.range = all_products
        cond_b.save()

        condition = CompoundCondition()
        condition.proxy_class = 'oscarbluelight.offer.conditions.CompoundCondition'
        condition.conjunction = CompoundCondition.OR
        condition.save()
        condition.subconditions.set([cond_a, cond_b])
        condition.save()

        benefit = Benefit()
        benefit.proxy_class = 'oscarbluelight.offer.benefits.BluelightFixedPriceBenefit'
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

        self.assertEqual(discount.discount, D('30.00'))
        self.assertEqual(basket.total_excl_tax_excl_discounts, D('50.00'))
        self.assertEqual(basket.total_excl_tax, D('20.00'))
