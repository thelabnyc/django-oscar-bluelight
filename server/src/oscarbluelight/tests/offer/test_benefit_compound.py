from decimal import Decimal as D
from django.test import TestCase
from oscar.test import factories
from oscarbluelight.offer.models import (
    Range,
    BluelightCountCondition,
    BluelightAbsoluteDiscountBenefit,
    BluelightPercentageDiscountBenefit,
    CompoundBenefit,
)
from django_redis import get_redis_connection
from unittest import mock


class TestCompoundAbsoluteBenefitDiscount(TestCase):
    def setUp(self):
        # Flush the cache
        conn = get_redis_connection("redis")
        conn.flushall()

        self.range_all = Range.objects.create(
            name="All products", includes_all_products=True
        )
        self.range_slippers = Range.objects.create(name="Slippers")
        self.range_pillows = Range.objects.create(name="Pillows")

        self.slipper = factories.create_product(title="Slippers", price=D("50.00"))
        self.pillow = factories.create_product(title="Pillow", price=D("100.00"))

        self.range_slippers.add_product(self.slipper)
        self.range_pillows.add_product(self.pillow)

        self.condition = BluelightCountCondition.objects.create(
            range=self.range_all,
            proxy_class="oscarbluelight.offer.conditions.BluelightCountCondition",
            value=1,
        )

        self.benefit_slippers = BluelightAbsoluteDiscountBenefit.objects.create(
            range=self.range_slippers,
            proxy_class="oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit",
            value=D("13.00"),
        )
        self.benefit_pillows = BluelightAbsoluteDiscountBenefit.objects.create(
            range=self.range_pillows,
            proxy_class="oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit",
            value=D("27.00"),
        )

        self.benefit_compound = CompoundBenefit.objects.create()
        self.benefit_compound.subbenefits.set(
            [
                self.benefit_slippers,
                self.benefit_pillows,
            ]
        )

        self.offer = mock.Mock()
        self.basket = factories.create_basket(empty=True)

    def test_applies_correctly(self):
        self.basket.add_product(self.slipper, 1)
        self.basket.add_product(self.pillow, 1)

        result = self.benefit_compound.apply(self.basket, self.condition, self.offer)

        self.assertEqual(D("40.00"), result.discount)

        line_discounts = [line.discount_value for line in self.basket.all_lines()]
        self.assertEqual(len(line_discounts), 2)
        self.assertEqual(line_discounts[0], D("13.00"))
        self.assertEqual(line_discounts[1], D("27.00"))

    def test_obeys_max_discount_setting(self):
        self.benefit_compound.max_discount = D("35.00")
        self.benefit_compound.save()

        self.basket.add_product(self.slipper, 1)
        self.basket.add_product(self.pillow, 1)

        result = self.benefit_compound.apply(self.basket, self.condition, self.offer)

        self.assertEqual(D("35.00"), result.discount)

        line_discounts = [line.discount_value for line in self.basket.all_lines()]
        self.assertEqual(len(line_discounts), 2)
        self.assertEqual(line_discounts[0], D("13.00"))
        self.assertEqual(line_discounts[1], D("22.00"))


class TestCompoundBluelightPercentageBenefitDiscount(TestCase):
    def setUp(self):
        # Flush the cache
        conn = get_redis_connection("redis")
        conn.flushall()

        self.range_mattresses = Range.objects.create(name="Mattresses")
        self.range_mattress_protectors = Range.objects.create(
            name="Mattress Protectors"
        )
        self.range_slippers = Range.objects.create(name="Slippers")
        self.range_pillows = Range.objects.create(name="Pillows")

        self.mattress = factories.create_product(title="Mattress", price=D("2999.00"))
        self.mattress_protector = factories.create_product(
            title="Mattress Protector", price=D("149.00")
        )
        self.slipper = factories.create_product(title="Slipper", price=D("78.00"))
        self.pillow = factories.create_product(title="Pillow", price=D("79.00"))

        self.range_mattresses.add_product(self.mattress)
        self.range_mattress_protectors.add_product(self.mattress_protector)
        self.range_slippers.add_product(self.slipper)
        self.range_pillows.add_product(self.pillow)

        self.condition = BluelightCountCondition.objects.create(
            range=self.range_mattresses,
            proxy_class="oscarbluelight.offer.conditions.BluelightCountCondition",
            value=1,
        )

        self.benefit_mattress_protector = BluelightPercentageDiscountBenefit.objects.create(
            range=self.range_mattress_protectors,
            proxy_class="oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit",
            value=D("100.00"),
            max_affected_items=1,
        )
        self.benefit_slippers = BluelightPercentageDiscountBenefit.objects.create(
            range=self.range_slippers,
            proxy_class="oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit",
            value=D("100.00"),
            max_affected_items=1,
        )
        self.benefit_pillows = BluelightPercentageDiscountBenefit.objects.create(
            range=self.range_pillows,
            proxy_class="oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit",
            value=D("100.00"),
            max_affected_items=2,
        )

        self.benefit_compound = CompoundBenefit.objects.create()
        self.benefit_compound.subbenefits.set(
            [
                self.benefit_mattress_protector,
                self.benefit_slippers,
                self.benefit_pillows,
            ]
        )

        self.offer = mock.Mock()
        self.basket = factories.create_basket(empty=True)

    def test_applies_correctly_one_instance(self):
        self.basket.add_product(self.mattress, 1)
        self.basket.add_product(self.mattress_protector, 1)
        self.basket.add_product(self.slipper, 1)
        self.basket.add_product(self.pillow, 2)

        self.assertEqual(
            self.condition.proxy().is_satisfied(self.offer, self.basket), True
        )

        result = self.benefit_compound.apply(self.basket, self.condition, self.offer)

        self.assertEqual(result.is_successful, True)
        self.assertEqual(result.is_final, False)
        self.assertEqual(result.discount, D("385.00"))

        self.assertEqual(
            self.condition.proxy().is_satisfied(self.offer, self.basket), False
        )

        line_discounts = [line.discount_value for line in self.basket.all_lines()]
        self.assertEqual(len(line_discounts), 4)
        self.assertEqual(line_discounts[0], D("0.00"))
        self.assertEqual(line_discounts[1], D("149.00"))
        self.assertEqual(line_discounts[2], D("78.00"))
        self.assertEqual(line_discounts[3], D("158.00"))

        self.assertEqual(self.basket.total_excl_tax, D("2999.00"))

    def test_applies_correctly_two_instances(self):
        self.basket.add_product(self.mattress, 2)
        self.basket.add_product(self.mattress_protector, 2)
        self.basket.add_product(self.slipper, 2)
        self.basket.add_product(self.pillow, 4)

        self.assertEqual(
            self.condition.proxy().is_satisfied(self.offer, self.basket), True
        )

        result = self.benefit_compound.apply(self.basket, self.condition, self.offer)
        self.assertEqual(result.is_successful, True)
        self.assertEqual(result.is_final, False)
        self.assertEqual(result.discount, D("385.00"))

        self.assertEqual(
            self.condition.proxy().is_satisfied(self.offer, self.basket), True
        )

        result = self.benefit_compound.apply(self.basket, self.condition, self.offer)
        self.assertEqual(result.is_successful, True)
        self.assertEqual(result.is_final, False)
        self.assertEqual(result.discount, D("385.00"))

        self.assertEqual(
            self.condition.proxy().is_satisfied(self.offer, self.basket), False
        )

        line_discounts = [line.discount_value for line in self.basket.all_lines()]
        self.assertEqual(len(line_discounts), 4)
        self.assertEqual(line_discounts[0], D("0.00"))
        self.assertEqual(line_discounts[1], D("298.00"))
        self.assertEqual(line_discounts[2], D("156.00"))
        self.assertEqual(line_discounts[3], D("316.00"))

        self.assertEqual(self.basket.total_excl_tax, D("5998.00"))

    def test_consumes_items_correctly_when_all_child_benefits_satisfied(self):
        # Add products
        line_1, _ = self.basket.add_product(self.mattress, 1)
        line_2, _ = self.basket.add_product(self.mattress_protector, 1)
        line_3, _ = self.basket.add_product(self.slipper, 1)
        line_4, _ = self.basket.add_product(self.pillow, 2)
        # Mock the condition.consume_items so we can check it's input
        self.condition.consume_items = mock.MagicMock()
        self.condition.consume_items.assert_not_called()
        # Check the condition is satisfied
        self.assertEqual(
            self.condition.proxy().is_satisfied(self.offer, self.basket), True
        )
        # Apply the benefit
        result = self.benefit_compound.apply(self.basket, self.condition, self.offer)
        # Check Result
        self.assertEqual(result.is_successful, True)
        self.assertEqual(result.is_final, False)
        self.assertEqual(result.discount, D("385.00"))
        # Check that lines were consumed correctly
        self.condition.consume_items.assert_called_once_with(
            self.offer,
            self.basket,
            [
                (line_2, D("149.00"), 1),
                (line_3, D("78.00"), 1),
                (line_4, D("158.00"), 2),
            ],
        )

    def test_consumes_items_correctly_when_not_all_child_benefits_satisfied(self):
        # Add products, but not a pillow (leaving part of the compound benefit unused)
        line_1, _ = self.basket.add_product(self.mattress, 1)
        line_2, _ = self.basket.add_product(self.mattress_protector, 1)
        line_3, _ = self.basket.add_product(self.slipper, 1)
        # Mock the condition.consume_items so we can check it's input
        self.condition.consume_items = mock.MagicMock()
        self.condition.consume_items.assert_not_called()
        # Check the condition is satisfied
        self.assertEqual(
            self.condition.proxy().is_satisfied(self.offer, self.basket), True
        )
        # Apply the benefit
        result = self.benefit_compound.apply(self.basket, self.condition, self.offer)
        # Check Result
        self.assertEqual(result.is_successful, True)
        self.assertEqual(result.is_final, False)
        self.assertEqual(result.discount, D("227.00"))
        # Check that lines were consumed correctly
        self.condition.consume_items.assert_called_once_with(
            self.offer,
            self.basket,
            [
                (line_2, D("149.00"), 1),
                (line_3, D("78.00"), 1),
            ],
        )
