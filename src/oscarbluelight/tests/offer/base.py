from decimal import Decimal as D
from django.test import TestCase
from oscarbluelight.offer.models import Condition, ConditionalOffer, Range, Benefit
from oscar.test.factories import create_basket, create_product, create_stockrecord


class BaseTest(TestCase):
    def _build_basket(self, item_price=D('10.00'), item_quantity=5):
        basket = create_basket(empty=True)
        product = create_product()
        create_stockrecord(product, item_price, num_in_stock=item_quantity * 2)
        basket.add_product(product, quantity=item_quantity)
        return basket

    def _build_offer(self, cls, cond_value):
        all_products = Range()
        all_products.includes_all_products = True
        all_products.save()
        condition = Condition()
        condition.proxy_class = cls
        condition.value = cond_value
        condition.range = all_products
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
