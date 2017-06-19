from decimal import Decimal as D
from oscarbluelight.offer.models import Condition, ConditionalOffer, Range, Benefit, CompoundCondition
from oscarbluelight.offer.applicator import Applicator
from oscar.test.factories import create_basket, create_product, create_stockrecord
from .base import BaseTest
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import Client


class CountConditionTest(BaseTest):
    def test_consume_items(self):
        basket = self._build_basket()
        offer = self._build_offer('oscarbluelight.offer.conditions.BluelightCountCondition', 2)

        line = basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 0)
        self.assertEqual(line.quantity_without_discount, 5)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, [])
        self.assertEqual(len(affected_lines), 1, 'Consumed 1 line')
        self.assertEqual(affected_lines[0][2], 2, 'Consumed quantity of 2')
        line = basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 2)
        self.assertEqual(line.quantity_without_discount, 3)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, affected_lines)
        self.assertEqual(len(affected_lines), 1, 'Consumed 1 line')
        self.assertEqual(affected_lines[0][2], 2, 'Consumed quantity of 2')
        line = basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 2)
        self.assertEqual(line.quantity_without_discount, 3)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, [])
        self.assertEqual(len(affected_lines), 1, 'Consumed 1 line')
        self.assertEqual(affected_lines[0][2], 2, 'Consumed quantity of 2')
        line = basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 4)
        self.assertEqual(line.quantity_without_discount, 1)


    def test_consume_items_when_benefit_consumes_other_items(self):
        # Create two products, each in a different product class
        product_main = create_product(product_class='Expensive Stuff')
        create_stockrecord(product_main, D('5000.00'), num_in_stock=100)

        product_accessory = create_product(product_class='Less Expensive Stuff')
        create_stockrecord(product_accessory, D('100.00'), num_in_stock=100)

        # Create two ranges, one for each product we just made
        range_main = Range.objects.create(name='Expensive Stuff')
        range_main.add_product(product_main)

        range_accessories = Range.objects.create(name='Less Expensive Stuff')
        range_accessories.add_product(product_accessory)

        # Create an offer which gives $5 off an accessory product when the basket contains a main product.
        # This offer, when applied, should consume the main and the accessory products. Not just the accessory.
        cond_has_main = Condition()
        cond_has_main.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        cond_has_main.value = 1
        cond_has_main.range = range_main
        cond_has_main.save()

        benefit_5off_accessory = Benefit()
        benefit_5off_accessory.proxy_class = 'oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit'
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

        self.assertEqual(basket.total_excl_tax_excl_discounts, D('5100.00'))
        self.assertEqual(basket.total_excl_tax, D('5100.00'))
        self.assertEqual(basket.num_items_without_discount, 2)
        self.assertEqual(basket.num_items_with_discount, 0)

        Applicator().apply_offers(basket, [offer])

        self.assertEqual(basket.total_excl_tax_excl_discounts, D('5100.00'))
        self.assertEqual(basket.total_excl_tax, D('5095.00'))
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.num_items_with_discount, 2)


class ValueConditionTest(BaseTest):
    def test_consume_items(self):
        basket = self._build_basket()
        offer = self._build_offer('oscarbluelight.offer.conditions.BluelightValueCondition', D('15.00'))

        line = basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 0)
        self.assertEqual(line.quantity_without_discount, 5)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, [])
        self.assertEqual(len(affected_lines), 1, 'Consumed 1 line')
        self.assertEqual(affected_lines[0][2], 2, 'Consumed quantity of 2')
        line = basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 2)
        self.assertEqual(line.quantity_without_discount, 3)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, affected_lines)
        self.assertEqual(len(affected_lines), 1, 'Consumed 1 line')
        self.assertEqual(affected_lines[0][2], 2, 'Consumed quantity of 2')
        line = basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 2)
        self.assertEqual(line.quantity_without_discount, 3)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, [])
        self.assertEqual(len(affected_lines), 1, 'Consumed 1 line')
        self.assertEqual(affected_lines[0][2], 2, 'Consumed quantity of 2')
        line = basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 4)
        self.assertEqual(line.quantity_without_discount, 1)


    def test_consume_items_when_benefit_consumes_other_items(self):
        # Create two products, each in a different product class
        product_main = create_product(product_class='Expensive Stuff')
        create_stockrecord(product_main, D('5000.00'), num_in_stock=100)

        product_accessory = create_product(product_class='Less Expensive Stuff')
        create_stockrecord(product_accessory, D('100.00'), num_in_stock=100)

        # Create two ranges, one for each product we just made
        range_main = Range.objects.create(name='Expensive Stuff')
        range_main.add_product(product_main)

        range_accessories = Range.objects.create(name='Less Expensive Stuff')
        range_accessories.add_product(product_accessory)

        # Create an offer which gives $5 off an accessory product when the basket contains a main product.
        # This offer, when applied, should consume the main and the accessory products. Not just the accessory.
        cond_has_main = Condition()
        cond_has_main.proxy_class = 'oscarbluelight.offer.conditions.BluelightValueCondition'
        cond_has_main.value = 1
        cond_has_main.range = range_main
        cond_has_main.save()

        benefit_5off_accessory = Benefit()
        benefit_5off_accessory.proxy_class = 'oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit'
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

        self.assertEqual(basket.total_excl_tax_excl_discounts, D('5100.00'))
        self.assertEqual(basket.total_excl_tax, D('5100.00'))
        self.assertEqual(basket.num_items_without_discount, 2)
        self.assertEqual(basket.num_items_with_discount, 0)

        Applicator().apply_offers(basket, [offer])

        self.assertEqual(basket.total_excl_tax_excl_discounts, D('5100.00'))
        self.assertEqual(basket.total_excl_tax, D('5095.00'))
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.num_items_with_discount, 2)


class CoverageConditionTest(BaseTest):
    def test_consume_items(self):
        basket = create_basket(empty=True)
        for i in range(5):
            product = create_product()
            create_stockrecord(product, D('10.00'), num_in_stock=10)
            basket.add_product(product, quantity=5)

        offer = self._build_offer('oscarbluelight.offer.conditions.BluelightCoverageCondition', 2)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, [])
        self.assertEqual(len(affected_lines), 2, 'Consumed 2 lines')
        self.assertEqual(affected_lines[0][2], 1, 'Consumed quantity of 1')
        self.assertEqual(affected_lines[1][2], 1, 'Consumed quantity of 1')
        self.assertEqual(basket.all_lines()[0].quantity_with_discount, 1)
        self.assertEqual(basket.all_lines()[0].quantity_without_discount, 4)
        self.assertEqual(basket.all_lines()[1].quantity_with_discount, 1)
        self.assertEqual(basket.all_lines()[1].quantity_without_discount, 4)
        self.assertEqual(basket.all_lines()[2].quantity_with_discount, 0)
        self.assertEqual(basket.all_lines()[2].quantity_without_discount, 5)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, affected_lines)
        self.assertEqual(len(affected_lines), 2, 'Consumed 2 lines')
        self.assertEqual(affected_lines[0][2], 1, 'Consumed quantity of 1')
        self.assertEqual(affected_lines[1][2], 1, 'Consumed quantity of 1')
        self.assertEqual(basket.all_lines()[0].quantity_with_discount, 1)
        self.assertEqual(basket.all_lines()[0].quantity_without_discount, 4)
        self.assertEqual(basket.all_lines()[1].quantity_with_discount, 1)
        self.assertEqual(basket.all_lines()[1].quantity_without_discount, 4)
        self.assertEqual(basket.all_lines()[2].quantity_with_discount, 0)
        self.assertEqual(basket.all_lines()[2].quantity_without_discount, 5)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, [])
        self.assertEqual(len(affected_lines), 2, 'Consumed 2 lines')
        self.assertEqual(affected_lines[0][2], 1, 'Consumed quantity of 1')
        self.assertEqual(affected_lines[1][2], 1, 'Consumed quantity of 1')
        self.assertEqual(basket.all_lines()[0].quantity_with_discount, 2)
        self.assertEqual(basket.all_lines()[0].quantity_without_discount, 3)
        self.assertEqual(basket.all_lines()[1].quantity_with_discount, 2)
        self.assertEqual(basket.all_lines()[1].quantity_without_discount, 3)
        self.assertEqual(basket.all_lines()[2].quantity_with_discount, 0)
        self.assertEqual(basket.all_lines()[2].quantity_without_discount, 5)

    def test_consume_items_when_benefit_consumes_other_items(self):
        # Create two products, each in a different product class
        product_main = create_product(product_class='Expensive Stuff')
        create_stockrecord(product_main, D('5000.00'), num_in_stock=100)

        product_accessory = create_product(product_class='Less Expensive Stuff')
        create_stockrecord(product_accessory, D('100.00'), num_in_stock=100)

        # Create two ranges, one for each product we just made
        range_main = Range.objects.create(name='Expensive Stuff')
        range_main.add_product(product_main)

        range_accessories = Range.objects.create(name='Less Expensive Stuff')
        range_accessories.add_product(product_accessory)

        # Create an offer which gives $5 off an accessory product when the basket contains a main product.
        # This offer, when applied, should consume the main and the accessory products. Not just the accessory.
        cond_has_main = Condition()
        cond_has_main.proxy_class = 'oscarbluelight.offer.conditions.BluelightCoverageCondition'
        cond_has_main.value = 1
        cond_has_main.range = range_main
        cond_has_main.save()

        benefit_5off_accessory = Benefit()
        benefit_5off_accessory.proxy_class = 'oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit'
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

        self.assertEqual(basket.total_excl_tax_excl_discounts, D('5100.00'))
        self.assertEqual(basket.total_excl_tax, D('5100.00'))
        self.assertEqual(basket.num_items_without_discount, 2)
        self.assertEqual(basket.num_items_with_discount, 0)

        Applicator().apply_offers(basket, [offer])

        self.assertEqual(basket.total_excl_tax_excl_discounts, D('5100.00'))
        self.assertEqual(basket.total_excl_tax, D('5095.00'))
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.num_items_with_discount, 2)


class CompoundConditionTest(BaseTest):
    def _build_offer(self, conjunction=CompoundCondition.AND):
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
        condition.conjunction = conjunction
        condition.save()
        condition.subconditions = [cond_a, cond_b]
        condition.save()

        benefit = Benefit()
        benefit.proxy_class = 'oscarbluelight.offer.benefits.BluelightShippingFixedPriceBenefit'
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
        self.assertEqual(c.children[0].proxy_class, 'oscarbluelight.offer.conditions.BluelightValueCondition')
        self.assertEqual(c.children[1].proxy_class, 'oscarbluelight.offer.conditions.BluelightCountCondition')

    def test_name_and(self):
        offer = self._build_offer(CompoundCondition.AND)
        c = offer.condition.proxy()
        self.assertEqual(c.name, 'Cart includes $10.00 from site and Cart includes 2 item(s) from site')

    def test_name_or(self):
        offer = self._build_offer(CompoundCondition.OR)
        c = offer.condition.proxy()
        self.assertEqual(c.name, 'Cart includes $10.00 from site or Cart includes 2 item(s) from site')

    def test_description_and(self):
        offer = self._build_offer(CompoundCondition.AND)
        c = offer.condition.proxy()
        self.assertEqual(c.description, 'Cart includes $10.00 from site and Cart includes 2 item(s) from site')

    def test_description_or(self):
        offer = self._build_offer(CompoundCondition.OR)
        c = offer.condition.proxy()
        self.assertEqual(c.description, 'Cart includes $10.00 from site or Cart includes 2 item(s) from site')

    def test_is_satisfied_and(self):
        offer = self._build_offer(CompoundCondition.AND)

        product = create_product()
        create_stockrecord(product, D('1.00'), num_in_stock=10)
        basket = create_basket(empty=True)
        self.assertFalse( offer.condition.is_satisfied(offer, basket) )
        basket.add_product(product, quantity=5)
        self.assertFalse( offer.condition.is_satisfied(offer, basket) )
        basket.add_product(product, quantity=5)
        self.assertTrue( offer.condition.is_satisfied(offer, basket) )

        product = create_product()
        create_stockrecord(product, D('20.00'), num_in_stock=10)
        basket = create_basket(empty=True)
        self.assertFalse( offer.condition.is_satisfied(offer, basket) )
        basket.add_product(product, quantity=1)
        self.assertFalse( offer.condition.is_satisfied(offer, basket) )
        basket.add_product(product, quantity=1)
        self.assertTrue( offer.condition.is_satisfied(offer, basket) )

    def test_is_satisfied_or(self):
        offer = self._build_offer(CompoundCondition.OR)

        product = create_product()
        create_stockrecord(product, D('1.00'), num_in_stock=10)
        basket = create_basket(empty=True)
        self.assertFalse( offer.condition.is_satisfied(offer, basket) )
        basket.add_product(product, quantity=1)
        self.assertFalse( offer.condition.is_satisfied(offer, basket) )
        basket.add_product(product, quantity=1)
        self.assertTrue( offer.condition.is_satisfied(offer, basket) )

        product = create_product()
        create_stockrecord(product, D('10.00'), num_in_stock=10)
        basket = create_basket(empty=True)
        self.assertFalse( offer.condition.is_satisfied(offer, basket) )
        basket.add_product(product, quantity=1)
        self.assertTrue( offer.condition.is_satisfied(offer, basket) )

    def test_is_partially_satisfied_and(self):
        offer = self._build_offer(CompoundCondition.AND)

        product = create_product()
        create_stockrecord(product, D('1.00'), num_in_stock=10)
        basket = create_basket(empty=True)
        self.assertFalse( offer.condition.is_partially_satisfied(offer, basket) )
        basket.add_product(product, quantity=1)
        self.assertTrue( offer.condition.is_partially_satisfied(offer, basket) )

    def test_is_partially_satisfied_or(self):
        offer = self._build_offer(CompoundCondition.OR)

        product = create_product()
        create_stockrecord(product, D('1.00'), num_in_stock=10)
        basket = create_basket(empty=True)
        self.assertFalse( offer.condition.is_partially_satisfied(offer, basket) )
        basket.add_product(product, quantity=1)
        self.assertTrue( offer.condition.is_partially_satisfied(offer, basket) )

    def test_get_upsell_message_and(self):
        offer = self._build_offer(CompoundCondition.AND)

        product = create_product()
        create_stockrecord(product, D('1.00'), num_in_stock=10)

        basket = create_basket(empty=True)
        basket.add_product(product, quantity=1)
        self.assertEqual(offer.condition.proxy().get_upsell_message(offer, basket), 'Spend $9.00 more from site and Buy 1 more product from site')

        basket.add_product(product, quantity=1)
        self.assertEqual(offer.condition.proxy().get_upsell_message(offer, basket), 'Spend $8.00 more from site')

    def test_get_upsell_message_or(self):
        offer = self._build_offer(CompoundCondition.OR)

        product = create_product()
        create_stockrecord(product, D('1.00'), num_in_stock=10)

        basket = create_basket(empty=True)
        basket.add_product(product, quantity=1)
        self.assertEqual(offer.condition.proxy().get_upsell_message(offer, basket), 'Spend $9.00 more from site or Buy 1 more product from site')

    def test_consume_items(self):
        basket = self._build_basket()
        offer = self._build_offer(CompoundCondition.OR)

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

        affected_lines = offer.condition.proxy().consume_items(offer, basket, affected_lines)
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
        a.proxy_class = 'oscarbluelight.offer.conditions.CompoundCondition'
        a.conjunction = CompoundCondition.OR
        a.save()

        self.assertEqual(a.conjunction, CompoundCondition.OR)

        b = Condition.objects.get(pk=a.pk)
        self.assertIsNotNone(b.compoundcondition)
        self.assertEqual(b.compoundcondition.conjunction, CompoundCondition.OR)

        # Saving the original model should work ok
        a.save()

        # Saving the proxy instance  should work too
        b.save()

    def test_consume_items_when_benefit_consumes_other_items(self):
        # Create three products, each in a different product class
        product_main = create_product(product_class='Expensive Stuff')
        create_stockrecord(product_main, D('5000.00'), num_in_stock=100)

        product_accessory = create_product(product_class='Less Expensive Stuff')
        create_stockrecord(product_accessory, D('100.00'), num_in_stock=100)

        product_addon = create_product(product_class='Cheap Stuff')
        create_stockrecord(product_addon, D('10.00'), num_in_stock=100)

        # Create 3 ranges, one for each product we just made
        range_main = Range.objects.create(name='Expensive Stuff')
        range_main.add_product(product_main)

        range_accessories = Range.objects.create(name='Less Expensive Stuff')
        range_accessories.add_product(product_accessory)

        range_addons = Range.objects.create(name='Cheap Stuff')
        range_addons.add_product(product_addon)

        # Create an offer which gives $5 off an add-on product when the basket contains both a main
        # and an accessory product. This offer, when applied, should consume the main, accessory, and
        # add-on product. Not just the add-on.
        cond_has_main = Condition()
        cond_has_main.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        cond_has_main.value = 1
        cond_has_main.range = range_main
        cond_has_main.save()

        cond_has_accessory = Condition()
        cond_has_accessory.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        cond_has_accessory.value = 1
        cond_has_accessory.range = range_accessories
        cond_has_accessory.save()

        cond_has_main_and_accessory = CompoundCondition()
        cond_has_main_and_accessory.proxy_class = 'oscarbluelight.offer.conditions.CompoundCondition'
        cond_has_main_and_accessory.conjunction = CompoundCondition.AND
        cond_has_main_and_accessory.save()
        cond_has_main_and_accessory.subconditions = [cond_has_main, cond_has_accessory]

        benefit_5off_addon = Benefit()
        benefit_5off_addon.proxy_class = 'oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit'
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

        self.assertEqual(basket.total_excl_tax_excl_discounts, D('5110.00'))
        self.assertEqual(basket.total_excl_tax, D('5110.00'))
        self.assertEqual(basket.num_items_without_discount, 3)
        self.assertEqual(basket.num_items_with_discount, 0)

        Applicator().apply_offers(basket, [offer])

        self.assertEqual(basket.total_excl_tax_excl_discounts, D('5110.00'))
        self.assertEqual(basket.total_excl_tax, D('5105.00'))
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.num_items_with_discount, 3)


    def test_consume_items_when_child_conditions_differ_in_type(self):
        # Create two products, each in a different product class
        product_main = create_product(product_class='Expensive Stuff')
        create_stockrecord(product_main, D('5000.00'), num_in_stock=100)

        product_accessory = create_product(product_class='Less Expensive Stuff')
        create_stockrecord(product_accessory, D('100.00'), num_in_stock=100)

        # Create two ranges, one for each product we just made
        range_main = Range.objects.create(name='Expensive Stuff')
        range_main.add_product(product_main)

        range_accessories = Range.objects.create(name='Less Expensive Stuff')
        range_accessories.add_product(product_accessory)

        # Create an offer which gives $50 off an accessory product when the basket contains a main
        # product and the basket is over $7,000.
        cond_has_main = Condition()
        cond_has_main.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        cond_has_main.value = 1
        cond_has_main.range = range_main
        cond_has_main.save()

        cond_over_7000 = Condition()
        cond_over_7000.proxy_class = 'oscarbluelight.offer.conditions.BluelightValueCondition'
        cond_over_7000.value = D('7000.00')
        cond_over_7000.range = range_main
        cond_over_7000.save()

        cond_has_main_and_over_7000 = CompoundCondition()
        cond_has_main_and_over_7000.proxy_class = 'oscarbluelight.offer.conditions.CompoundCondition'
        cond_has_main_and_over_7000.conjunction = CompoundCondition.AND
        cond_has_main_and_over_7000.save()
        cond_has_main_and_over_7000.subconditions = [cond_has_main, cond_over_7000]

        benefit_50off_addon = Benefit()
        benefit_50off_addon.proxy_class = 'oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit'
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

        self.assertEqual(basket.total_excl_tax_excl_discounts, D('5100.00'))
        self.assertEqual(basket.total_excl_tax, D('5100.00'))
        self.assertEqual(basket.num_items_without_discount, 2)
        self.assertEqual(basket.num_items_with_discount, 0)

        Applicator().apply_offers(basket, [offer])

        self.assertEqual(basket.total_excl_tax_excl_discounts, D('5100.00'))
        self.assertEqual(basket.total_excl_tax, D('5100.00'))
        self.assertEqual(basket.num_items_without_discount, 2)
        self.assertEqual(basket.num_items_with_discount, 0)

        basket.add_product(product_main, quantity=1)

        self.assertEqual(basket.total_excl_tax_excl_discounts, D('10100.00'))
        self.assertEqual(basket.total_excl_tax, D('10100.00'))
        self.assertEqual(basket.num_items_without_discount, 3)
        self.assertEqual(basket.num_items_with_discount, 0)

        Applicator().apply_offers(basket, [offer])

        self.assertEqual(basket.total_excl_tax_excl_discounts, D('10100.00'))
        self.assertEqual(basket.total_excl_tax, D('10050.00'))
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.num_items_with_discount, 3)


class ConditionURL(TestCase):
    def setUp(self):
        self.client = Client()
        self.all_products = Range()
        self.all_products.includes_all_products = True
        self.all_products.save()
        self.condition = Condition()
        self.condition.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        self.condition.value = 5
        self.condition.range = self.all_products
        self.condition.save()
        self.user = User.objects.create_user('john', 'lennon@thebeatles.com', 'johnpassword', is_staff=True)
        self.user.save()

    def test_get(self):
        self.client.login(username='john', password='johnpassword')
        response = self.client.get(reverse('dashboard:condition-list'))
        self.assertEqual(response.status_code, 200)
