from decimal import Decimal as D
from oscarbluelight.offer.models import Condition, ConditionalOffer, Range, Benefit, CompoundCondition
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
