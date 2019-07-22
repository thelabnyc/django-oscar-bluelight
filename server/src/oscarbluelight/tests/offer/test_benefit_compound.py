from decimal import Decimal as D
from django.test import TestCase
from oscar.test import factories
from oscarbluelight.offer.models import (
    Condition,
    Range,
    Benefit,
    BluelightCountCondition,
    BluelightAbsoluteDiscountBenefit,
    CompoundBenefit,
)
from django_redis import get_redis_connection
import mock


class TestCompoundAbsoluteBenefitDiscount(TestCase):
    def setUp(self):
        # Flush the cache
        conn = get_redis_connection('redis')
        conn.flushall()

        self.range_all = Range.objects.create(
            name="All products", includes_all_products=True)
        self.range_slippers = Range.objects.create(name="Slippers")
        self.range_pillows = Range.objects.create(name="Pillows")

        self.slipper = factories.create_product(title='Slippers', price=D('50.00'))
        self.pillow = factories.create_product(title='Pillow', price=D('100.00'))

        self.range_slippers.add_product(self.slipper)
        self.range_pillows.add_product(self.pillow)

        self.condition = BluelightCountCondition.objects.create(
            range=self.range_all,
            type=Condition.COUNT,
            value=1)

        self.benefit_slippers = BluelightAbsoluteDiscountBenefit.objects.create(
            range=self.range_slippers,
            type=Benefit.FIXED,
            value=D('13.00'))
        self.benefit_pillows = BluelightAbsoluteDiscountBenefit.objects.create(
            range=self.range_pillows,
            type=Benefit.FIXED,
            value=D('27.00'))

        self.benefit_compound = CompoundBenefit.objects.create()
        self.benefit_compound.subbenefits.set([
            self.benefit_slippers,
            self.benefit_pillows,
        ])

        self.offer = mock.Mock()
        self.basket = factories.create_basket(empty=True)


    def test_applies_correctly(self):
        self.basket.add_product(self.slipper, 1)
        self.basket.add_product(self.pillow, 1)

        result = self.benefit_compound.apply(self.basket, self.condition, self.offer)

        self.assertEqual(D('40.00'), result.discount)

        line_discounts = [line.discount_value for line in self.basket.all_lines()]
        self.assertEqual(len(line_discounts), 2)
        self.assertEqual(line_discounts[0], D('13.00'))
        self.assertEqual(line_discounts[1], D('27.00'))
