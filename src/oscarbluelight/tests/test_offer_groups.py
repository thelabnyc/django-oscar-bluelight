from django.test import TestCase
from oscarbluelight.offer.models import (
    OfferGroup,
    Benefit,
    Range,
    Condition,
    ConditionalOffer
)
from oscarbluelight.voucher.models import Voucher


class TestOfferGroup(TestCase):
    def setUp(self):
        self.all_products = Range()
        self.all_products.includes_all_products = True
        self.all_products.save()
        self.condition = Condition(name='test1')
        self.condition.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        self.condition.value = 2
        self.condition.range = self.all_products
        self.condition.save()
        self.benefit = Benefit()
        self.benefit.proxy_class = 'oscarbluelight.offer.benefits.BluelightShippingFixedPriceBenefit'
        self.benefit.value = 0
        self.benefit.save()
        self.offer1 = ConditionalOffer()
        self.offer1.condition = self.condition
        self.offer1.benefit = self.benefit
        self.offer1.save()
        self.offer2 = ConditionalOffer(name='test cond 2')
        self.offer2.condition = self.condition
        self.offer2.benefit = self.benefit
        self.offer2.save()

        self.offer_group1 = OfferGroup(
            name='test',
            order=1
        )
        self.offer_group1.save()
        self.offer_group1.offers.add(self.offer1)


    def test_create_offer_group(self):
        self.assertIsNotNone(self.offer_group1)
        self.assertEqual(self.offer_group1.name, 'test')
        self.assertEqual(self.offer_group1.order, 1)
        self.assertIn(self.offer1, self.offer_group1.offers.all() )

    def test_add_to_offer_group(self):
        condition = Condition()
        condition.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        condition.value = 5
        condition.range = self.all_products
        condition.save()
        benefit = Benefit()
        benefit.proxy_class = 'oscarbluelight.offer.benefits.BluelightShippingFixedPriceBenefit'
        benefit.value = 1
        benefit.save()
        offer = ConditionalOffer(name='test2')
        offer.condition = condition
        offer.benefit = benefit
        offer.save()
        self.offer_group1.offers.add(offer)
        self.assertIsNotNone(offer.offer_group)
        self.assertIn(offer, self.offer_group1.offers.all())

    def test_offer_group_order(self):
        offer_group1 = OfferGroup.objects.create(
            name='test offer group 1',
            order=2
        )
        offer_group1.save()
        offer_group2 = OfferGroup.objects.create(
            name='test offer group 2',
            order=3
        )
        offer_group2.save()
        offer_group3 = OfferGroup.objects.create(
            name='test offer group 3',
            order=4
        )
        offer_group3.save()
        condition = Condition(name='test condition 2')
        condition.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        condition.value = 5
        condition.range = self.all_products
        condition.save()
        benefit = Benefit()
        benefit.proxy_class = 'oscarbluelight.offer.benefits.BluelightShippingFixedPriceBenefit'
        benefit.value = 1
        benefit.save()
        offer = ConditionalOffer(name='test3')
        offer.condition = condition
        offer.benefit = benefit
        offer.save()
