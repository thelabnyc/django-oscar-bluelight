from decimal import Decimal as D
from django.test import TestCase
from oscarbluelight.offer.models import Condition, ConditionalOffer, Range, Benefit, CompoundCondition
from oscar.test.factories import create_basket, create_product, create_stockrecord


class BaseTest(TestCase):
    def _build_basket(self, item_price=D('10.00'), item_quantity=5):
        basket = create_basket(empty=True)
        product = create_product()
        create_stockrecord(product, item_price, num_in_stock=item_quantity * 2)
        basket.add_product(product, quantity=item_quantity)
        return basket

    def _build_offer(self, cond_type, cond_value):
        all_products = Range()
        all_products.includes_all_products = True
        all_products.save()
        condition = Condition()
        condition.type = cond_type
        condition.value = cond_value
        condition.range = all_products
        condition.save()
        benefit = Benefit()
        benefit.type = Benefit.SHIPPING_FIXED_PRICE
        benefit.value = 0
        benefit.save()
        offer = ConditionalOffer()
        offer.condition = condition
        offer.benefit = benefit
        offer.save()
        return offer


class CountConditionTest(BaseTest):
    def test_consume_items(self):
        basket = self._build_basket()
        offer = self._build_offer(Condition.COUNT, 2)

        line = basket.all_lines()[0]
        self.assertEquals(line.quantity_with_discount, 0)
        self.assertEquals(line.quantity_without_discount, 5)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, [])
        self.assertEquals(len(affected_lines), 1, 'Consumed 1 line')
        self.assertEquals(affected_lines[0][2], 2, 'Consumed quantity of 2')
        line = basket.all_lines()[0]
        self.assertEquals(line.quantity_with_discount, 2)
        self.assertEquals(line.quantity_without_discount, 3)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, affected_lines)
        self.assertEquals(len(affected_lines), 1, 'Consumed 1 line')
        self.assertEquals(affected_lines[0][2], 2, 'Consumed quantity of 2')
        line = basket.all_lines()[0]
        self.assertEquals(line.quantity_with_discount, 2)
        self.assertEquals(line.quantity_without_discount, 3)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, [])
        self.assertEquals(len(affected_lines), 1, 'Consumed 1 line')
        self.assertEquals(affected_lines[0][2], 2, 'Consumed quantity of 2')
        line = basket.all_lines()[0]
        self.assertEquals(line.quantity_with_discount, 4)
        self.assertEquals(line.quantity_without_discount, 1)


class ValueConditionTest(BaseTest):
    def test_consume_items(self):
        basket = self._build_basket()
        offer = self._build_offer(Condition.VALUE, D('15.00'))

        line = basket.all_lines()[0]
        self.assertEquals(line.quantity_with_discount, 0)
        self.assertEquals(line.quantity_without_discount, 5)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, [])
        self.assertEquals(len(affected_lines), 1, 'Consumed 1 line')
        self.assertEquals(affected_lines[0][2], 2, 'Consumed quantity of 2')
        line = basket.all_lines()[0]
        self.assertEquals(line.quantity_with_discount, 2)
        self.assertEquals(line.quantity_without_discount, 3)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, affected_lines)
        self.assertEquals(len(affected_lines), 1, 'Consumed 1 line')
        self.assertEquals(affected_lines[0][2], 2, 'Consumed quantity of 2')
        line = basket.all_lines()[0]
        self.assertEquals(line.quantity_with_discount, 2)
        self.assertEquals(line.quantity_without_discount, 3)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, [])
        self.assertEquals(len(affected_lines), 1, 'Consumed 1 line')
        self.assertEquals(affected_lines[0][2], 2, 'Consumed quantity of 2')
        line = basket.all_lines()[0]
        self.assertEquals(line.quantity_with_discount, 4)
        self.assertEquals(line.quantity_without_discount, 1)


class CoverageConditionTest(BaseTest):
    def test_consume_items(self):
        basket = create_basket(empty=True)
        for i in range(5):
            product = create_product()
            create_stockrecord(product, D('10.00'), num_in_stock=10)
            basket.add_product(product, quantity=5)

        offer = self._build_offer(Condition.COVERAGE, 2)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, [])
        self.assertEquals(len(affected_lines), 2, 'Consumed 2 lines')
        self.assertEquals(affected_lines[0][2], 1, 'Consumed quantity of 1')
        self.assertEquals(affected_lines[1][2], 1, 'Consumed quantity of 1')
        self.assertEquals(basket.all_lines()[0].quantity_with_discount, 1)
        self.assertEquals(basket.all_lines()[0].quantity_without_discount, 4)
        self.assertEquals(basket.all_lines()[1].quantity_with_discount, 1)
        self.assertEquals(basket.all_lines()[1].quantity_without_discount, 4)
        self.assertEquals(basket.all_lines()[2].quantity_with_discount, 0)
        self.assertEquals(basket.all_lines()[2].quantity_without_discount, 5)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, affected_lines)
        self.assertEquals(len(affected_lines), 2, 'Consumed 2 lines')
        self.assertEquals(affected_lines[0][2], 1, 'Consumed quantity of 1')
        self.assertEquals(affected_lines[1][2], 1, 'Consumed quantity of 1')
        self.assertEquals(basket.all_lines()[0].quantity_with_discount, 1)
        self.assertEquals(basket.all_lines()[0].quantity_without_discount, 4)
        self.assertEquals(basket.all_lines()[1].quantity_with_discount, 1)
        self.assertEquals(basket.all_lines()[1].quantity_without_discount, 4)
        self.assertEquals(basket.all_lines()[2].quantity_with_discount, 0)
        self.assertEquals(basket.all_lines()[2].quantity_without_discount, 5)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, [])
        self.assertEquals(len(affected_lines), 2, 'Consumed 2 lines')
        self.assertEquals(affected_lines[0][2], 1, 'Consumed quantity of 1')
        self.assertEquals(affected_lines[1][2], 1, 'Consumed quantity of 1')
        self.assertEquals(basket.all_lines()[0].quantity_with_discount, 2)
        self.assertEquals(basket.all_lines()[0].quantity_without_discount, 3)
        self.assertEquals(basket.all_lines()[1].quantity_with_discount, 2)
        self.assertEquals(basket.all_lines()[1].quantity_without_discount, 3)
        self.assertEquals(basket.all_lines()[2].quantity_with_discount, 0)
        self.assertEquals(basket.all_lines()[2].quantity_without_discount, 5)


class CompoundConditionTest(BaseTest):
    def _build_offer(self, conjunction=CompoundCondition.AND):
        all_products = Range()
        all_products.name = 'site'
        all_products.includes_all_products = True
        all_products.save()

        cond_a = Condition()
        cond_a.type = Condition.VALUE
        cond_a.value = 10
        cond_a.range = all_products
        cond_a.save()

        cond_b = Condition()
        cond_b.type = Condition.COUNT
        cond_b.value = 2
        cond_b.range = all_products
        cond_b.save()

        condition = CompoundCondition()
        condition.type = Condition.COMPOUND
        condition.conjunction = conjunction
        condition.save()
        condition.subconditions = [cond_a, cond_b]
        condition.save()

        benefit = Benefit()
        benefit.type = Benefit.SHIPPING_FIXED_PRICE
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
        self.assertEqual(c.children[0].type, Condition.VALUE)
        self.assertEqual(c.children[1].type, Condition.COUNT)

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
        self.assertEquals(line.quantity_with_discount, 0)
        self.assertEquals(line.quantity_without_discount, 5)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, [])
        self.assertEquals(len(affected_lines), 2)
        self.assertEquals(affected_lines[0][2], 1)
        self.assertEquals(affected_lines[1][2], 1)
        line = basket.all_lines()[0]
        self.assertEquals(line.quantity_with_discount, 2)
        self.assertEquals(line.quantity_without_discount, 3)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, affected_lines)
        self.assertEquals(len(affected_lines), 2)
        self.assertEquals(affected_lines[0][2], 1)
        self.assertEquals(affected_lines[1][2], 1)
        line = basket.all_lines()[0]
        self.assertEquals(line.quantity_with_discount, 2)
        self.assertEquals(line.quantity_without_discount, 3)

        affected_lines = offer.condition.proxy().consume_items(offer, basket, [])
        self.assertEquals(len(affected_lines), 2)
        self.assertEquals(affected_lines[0][2], 1)
        self.assertEquals(affected_lines[1][2], 1)
        line = basket.all_lines()[0]
        self.assertEquals(line.quantity_with_discount, 4)
        self.assertEquals(line.quantity_without_discount, 1)
