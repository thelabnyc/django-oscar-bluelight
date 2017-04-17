from django.test import TestCase
from datetime import datetime, timedelta
from django.contrib.auth.models import AnonymousUser
# from decimal import Decimal as D
from oscarbluelight.offer.models import BlackList, BlackListObject
from oscarbluelight.offer.models import Condition, ConditionalOffer, Range, Benefit
# from django.contrib.contenttypes.models import ContentType
from oscar.test.factories import create_basket, create_product, create_stockrecord
from oscarbluelight.voucher.models import Voucher
# from oscar.test.factories import create_order
# from oscar.test.factories import create_basket, create_product, create_stockrecord


class TestBlacklist(TestCase):
    def setUp(self):
        self.user = AnonymousUser()
        self.basket = create_basket()
        self.basket = create_basket(empty=True)
        self.product = create_product()
        create_stockrecord(self.product, 12.0, num_in_stock=10 * 2)
        self.basket.add_product(self.product, quantity=10)
        self.voucher1 = Voucher.objects.create(
            name='Test Voucher',
            code='test-voucher-1',
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now() + timedelta(seconds=10),
            limit_usage_by_group=False
        )
        self.voucher1.save()

        self.voucher2 = Voucher.objects.create(
            name='Test Voucher 2',
            code='test-voucher-2',
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now() + timedelta(seconds=10),
            limit_usage_by_group=False
        )
        self.voucher2.save()
        self.blacklist = BlackList.objects.create(
            classname='Voucher',
            instance_id=self.voucher1.pk
        )
        self.blacklist_obj = BlackListObject(
            classname='Voucher',
            instance_id=self.voucher2.pk)

        self.blacklist.save()
        self.blacklist_obj.save()
        self.blacklist.blacklist.add(self.blacklist_obj)
        self.blacklist.save()


    def test_create_voucher_blacklist(self):
        is_available, message = self.voucher1.is_available_to_user(self.user)
        self.assertTrue(is_available)
        self.assertIsNotNone(self.blacklist)
        self.assertTrue(self.blacklist_obj in self.blacklist.blacklist.all())
        self.assertTrue(self.blacklist.is_blacklisted('Voucher', self.voucher2))

    def test_condition_blacklist(self):
        all_products = Range()
        all_products.includes_all_products = True
        all_products.save()
        condition = Condition()
        condition.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        condition.value = 2
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
        blacklist_obj = BlackListObject(
            classname='BluelightCountCondition',
            instance_id=condition.pk
        )
        blacklist_obj.save()
        blacklist = BlackList.objects.create(
            classname='Voucher',
            instance_id=self.voucher1.pk
        )
        blacklist.save()
        blacklist.blacklist.add(blacklist_obj)
        blacklist.save()
        self.assertIsNotNone(blacklist)
        self.assertTrue(blacklist_obj in blacklist.blacklist.all())
        self.assertFalse(blacklist.is_blacklisted('Voucher', self.voucher1))
        self.assertTrue(blacklist.is_blacklisted('BluelightCountCondition', condition))

