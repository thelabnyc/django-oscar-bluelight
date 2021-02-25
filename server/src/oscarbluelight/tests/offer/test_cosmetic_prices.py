from decimal import Decimal as D
from django_redis import get_redis_connection
from oscarbluelight.offer.models import Condition, ConditionalOffer, Range, Benefit
from oscarbluelight.offer.applicator import Applicator
from oscar.test.factories import create_basket, create_product, create_stockrecord
from django.test import TransactionTestCase


class CosmeticPricingCalculationTest(TransactionTestCase):
    def setUp(self):
        # Flush the cache
        conn = get_redis_connection("redis")
        conn.flushall()

        # Create a product
        self.product_main = create_product(product_class="Stuff")
        create_stockrecord(self.product_main, D("5000.00"), num_in_stock=100)

        # Create a range
        self.range_main = Range.objects.create(name="Stuff")
        self.range_main.add_product(self.product_main)

        # Create an offer which gives $500 off a product
        cond = Condition()
        cond.proxy_class = "oscarbluelight.offer.conditions.BluelightCountCondition"
        cond.value = 1
        cond.range = self.range_main
        cond.save()

        benefit = Benefit()
        benefit.proxy_class = (
            "oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit"
        )
        benefit.value = 500
        benefit.range = self.range_main
        benefit.save()

        offer = ConditionalOffer()
        offer.condition = cond
        offer.benefit = benefit
        offer.save()

        self.basket = create_basket(empty=True)

    def test_calculate_cosmetic_price(self):
        # Cosmetic price should reflect discount
        cosmetic_price = Applicator().get_cosmetic_price(
            self.basket.strategy, self.product_main, quantity=1
        )
        self.assertEqual(cosmetic_price, D("4500.00"))

    def test_calculate_cosmetic_price_when_offer_doesnt_affect_cosmetics(self):
        ConditionalOffer.objects.all().update(affects_cosmetic_pricing=False)
        # Cosmetic price should not reflect discount
        cosmetic_price = Applicator().get_cosmetic_price(
            self.basket.strategy, self.product_main, quantity=1
        )
        self.assertEqual(cosmetic_price, D("5000.00"))

    def test_cosmetic_price_cache_invalidation(self):
        # Populate the cache
        cosmetic_price = Applicator().get_cosmetic_price(
            self.basket.strategy, self.product_main, quantity=1
        )
        self.assertEqual(cosmetic_price, D("4500.00"))

        # Change the product price. This should invalidate the cache.
        sr = self.product_main.stockrecords.first()
        sr.price = D("4000.00")
        sr.save()

        # Check price again, make sure it's not stale.
        cosmetic_price = Applicator().get_cosmetic_price(
            self.basket.strategy, self.product_main, quantity=1
        )
        self.assertEqual(cosmetic_price, D("3500.00"))
