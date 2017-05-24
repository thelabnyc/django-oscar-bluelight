from decimal import Decimal as D
from django.test import TestCase
from oscar.test.basket import add_product, add_products
from oscar.test import factories
from oscarbluelight.offer.models import (
    Condition,
    Range,
    Benefit,
    BluelightCountCondition,
    BluelightMultibuyDiscountBenefit,
    BluelightValueCondition,
)
import mock


class TestAMultibuyDiscountAppliedWithCountCondition(TestCase):
    def setUp(self):
        range = Range.objects.create(
            name="All products", includes_all_products=True)
        self.condition = BluelightCountCondition.objects.create(
            range=range,
            type=Condition.COUNT,
            value=3)
        self.benefit = BluelightMultibuyDiscountBenefit.objects.create(
            range=range,
            type=Benefit.MULTIBUY,
            value=1)
        self.offer = mock.Mock()
        self.basket = factories.create_basket(empty=True)


    def test_applies_correctly_to_empty_basket(self):
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D('0.00'), result.discount)
        self.assertEqual(0, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)


    def test_applies_correctly_to_basket_which_matches_condition(self):
        add_product(self.basket, D('12.00'), 3)
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D('12.00'), result.discount)
        self.assertEqual(3, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)


    def test_applies_correctly_to_basket_which_exceeds_condition(self):
        add_products(self.basket, [
            (D('4.00'), 4), (D('2.00'), 4)])
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D('2.00'), result.discount)
        self.assertEqual(3, self.basket.num_items_with_discount)
        self.assertEqual(5, self.basket.num_items_without_discount)



class TestAMultibuyDiscountAppliedWithAValueCondition(TestCase):
    def setUp(self):
        range = Range.objects.create(
            name="All products", includes_all_products=True)
        self.condition = BluelightValueCondition.objects.create(
            range=range,
            type=Condition.VALUE,
            value=D('10.00'))
        self.benefit = BluelightMultibuyDiscountBenefit.objects.create(
            range=range,
            type=Benefit.MULTIBUY,
            value=1)
        self.offer = mock.Mock()
        self.basket = factories.create_basket(empty=True)


    def test_applies_correctly_to_empty_basket(self):
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D('0.00'), result.discount)
        self.assertEqual(0, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)


    def test_applies_correctly_to_basket_which_matches_condition(self):
        add_product(self.basket, D('5.00'), 2)
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D('5.00'), result.discount)
        self.assertEqual(2, self.basket.num_items_with_discount)
        self.assertEqual(0, self.basket.num_items_without_discount)


    def test_applies_correctly_to_basket_which_exceeds_condition(self):
        add_products(self.basket, [(D('4.00'), 2), (D('2.00'), 2)])
        result = self.benefit.apply(self.basket, self.condition, self.offer)
        self.assertEqual(D('2.00'), result.discount)
        self.assertEqual(3, self.basket.num_items_with_discount)
        self.assertEqual(1, self.basket.num_items_without_discount)
