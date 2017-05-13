from datetime import datetime, timedelta
from decimal import Decimal as D
from django.test import TestCase, RequestFactory
from django.test import Client
from django.core.urlresolvers import reverse
from oscarbluelight.offer.models import (
    OfferGroup,
    Benefit,
    Range,
    Condition,
    CompoundCondition,
    ConditionalOffer
)
from oscarbluelight.dashboard.offers.forms import OfferGroupForm
from oscarbluelight.voucher.models import Voucher
from django.contrib.auth.models import User, Group
from oscar.test.factories import create_basket, create_product, create_stockrecord


class OfferGroupModelTest(TestCase):
    def setUp(self):
        self.all_products = Range()
        self.all_products.includes_all_products = True
        self.all_products.save()
        self.condition = Condition()
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
            priority=1
        )
        self.offer_group1.save()
        self.offer_group1.offers.add(self.offer1)


    def test_create_offer_group(self):
        self.assertIsNotNone(self.offer_group1)
        self.assertEqual(self.offer_group1.name, 'test')
        self.assertEqual(self.offer_group1.priority, 1)
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
            priority=2
        )
        offer_group1.save()
        offer_group2 = OfferGroup.objects.create(
            name='test offer group 2',
            priority=3
        )
        offer_group2.save()
        offer_group3 = OfferGroup.objects.create(
            name='test offer group 3',
            priority=4
        )
        offer_group3.save()
        condition1 = Condition()
        condition1.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        condition1.value = 3
        condition1.range = self.all_products
        condition1.save()
        benefit1 = Benefit()
        benefit1.proxy_class = 'oscarbluelight.offer.benefits.BluelightShippingFixedPriceBenefit'
        benefit1.value = 1
        benefit1.save()
        offer1 = ConditionalOffer(name='test3')
        offer1.condition = condition1
        offer1.benefit = benefit1
        offer1.save()
        benefit1 = Benefit()
        benefit1.proxy_class = 'oscarbluelight.offer.benefits.BluelightShippingFixedPriceBenefit'
        benefit1.value = 1
        benefit1.save()
        offer1 = ConditionalOffer(name='test4')
        offer1.condition = condition1
        offer1.benefit = benefit1
        offer1.priority = 10
        offer1.save()

        offer_group1.offers.add(offer1)
        self.assertEqual(offer1.offer_group.priority, 2)

        offer2 = ConditionalOffer(name='test5')
        offer2.condition = condition1
        offer2.benefit = benefit1
        offer2.priority = 20
        offer2.save()
        offer_group2.offers.add(offer2)
        self.assertEqual(offer2.offer_group.priority, 3)

        condition2 = Condition()
        condition2.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        condition2.value = 5
        condition2.range = self.all_products
        condition2.save()
        benefit2 = Benefit()
        benefit2.proxy_class = 'oscarbluelight.offer.benefits.BluelightShippingFixedPriceBenefit'
        benefit2.value = 12
        benefit2.save()
        offer3 = ConditionalOffer(name='test 234')
        offer3.condition = condition1
        offer3.benefit = benefit1
        offer3.priority = 30
        offer3.save()

        offer_group3.offers.add(offer3)
        self.assertEqual(offer3.offer_group.priority, 4)

    def test_unique_priority(self):
        offer_group = OfferGroup(
            name='test',
            priority=1
        )
        with self.assertRaises(Exception):
            offer_group.save()


class ConsumeOfferGroupOfferTest(TestCase):
    def setUp(self):
        '''
        offer_groups elvis, beatles, stones with ascending order (application order)
        offers elvis, memphis, beatles and stones
        offers elvis and memphis -> offer_group Elvis
        offer beatles -> offer_groupbeatles
        offer stones -> offer_group stones
        '''
        self.all_products = Range()
        self.all_products.includes_all_products = True
        self.all_products.save()
        item_price = 200.0
        item_quantity = 5
        self.basket = create_basket(empty=True)
        self.product = create_product()
        create_stockrecord(self.product, item_price, num_in_stock=item_quantity * 2)
        self.basket.add_product(self.product, quantity=item_quantity)

        self.offer_group_elvis = OfferGroup.objects.create(
            name='test offer group elvis',
            priority=1
        )
        self.offer_group_elvis.save()

        self.offer_group_beatles = OfferGroup.objects.create(
            name='test offer group beatles',
            priority=2
        )
        self.offer_group_beatles.save()

        self.offer_group_stones = OfferGroup.objects.create(
            name='test offer group stones',
            priority=3
        )
        self.offer_group_stones.save()

        self.condition1 = Condition()
        self.condition1.proxy_class = 'oscarbluelight.offer.conditions.BluelightValueCondition'
        self.condition1.value = 3.45
        self.condition1.range = self.all_products
        self.condition1.save()
        self.benefit1 = Benefit()
        self.benefit1.proxy_class = 'oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit'
        self.benefit1.value = 22
        self.benefit1.range = self.all_products
        self.benefit1.save()
        self.offer_elvis = ConditionalOffer(name='cond offer test 1')
        self.offer_elvis.condition = self.condition1
        self.offer_elvis.benefit = self.benefit1
        self.offer_elvis.priority = 1
        self.offer_elvis.save()

        self.offer_group_elvis.offers.add(self.offer_elvis)


        self.benefit2 = Benefit()
        self.benefit2.proxy_class = 'oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit'
        self.benefit2.value = 23
        self.benefit2.range = self.all_products
        self.benefit2.save()
        self.offer_memphis = ConditionalOffer(name='cond offer test 2')
        self.offer_memphis.condition = self.condition1
        self.offer_memphis.benefit = self.benefit2
        self.offer_memphis.priority = 2
        self.offer_memphis.save()

        self.offer_group_elvis.offers.add(self.offer_memphis)

        self.benefit3 = Benefit()
        self.benefit3.proxy_class = 'oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit'
        self.benefit3.value = 24
        self.benefit3.range = self.all_products
        self.benefit3.save()
        self.offer_beatles = ConditionalOffer(name='cond offer test 3')
        self.offer_beatles.condition = self.condition1
        self.offer_beatles.benefit = self.benefit3
        self.offer_beatles.save()
        self.offer_beatles.priority = 3
        self.offer_group_beatles.offers.add(self.offer_beatles)

        self.value_condition = Condition()
        self.value_condition.proxy_class = 'oscarbluelight.offer.conditions.BluelightCoverageCondition'
        self.value_condition.range = self.all_products
        self.value_condition.save()
        self.fixed_price_benefit = Benefit()
        self.fixed_price_benefit.proxy_class = 'oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit'
        self.fixed_price_benefit.value = 32
        self.fixed_price_benefit.range = self.all_products
        self.fixed_price_benefit.save()
        self.offer_stones = ConditionalOffer(name='cond offer test stones')
        self.offer_stones.condition = self.value_condition
        self.offer_stones.benefit = self.fixed_price_benefit
        self.offer_stones.priority = 4
        self.offer_stones.save()

        self.offer_group_stones.offers.add(self.offer_stones)

        self.user = User.objects.create_user(
            username='bob', email='bob@example.com', password='foo')

        self.customer = Group.objects.create(name='Customers')
        self.csrs = Group.objects.create(name='Customer Service Reps')

        self.voucher = Voucher.objects.create(
            name='Test Voucher',
            code='test-voucher',
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now() + timedelta(seconds=120),
            limit_usage_by_group=False
        )
        self.voucher.offers.add(self.offer_stones)
        self.offer_group_beatles.offers.add(self.voucher.offers.first())

    def test_voucher_order(self):
        self.assertEqual(self.voucher.offers.first().name, 'cond offer test stones')
        self.assertEqual(self.voucher.offers.first().offer_group.priority, 2)

    def test_offer_group_elvis(self):
        qs = ConditionalOffer.objects.filter(offer_group=self.offer_group_elvis)
        self.assertIn(self.offer_elvis, qs)
        self.assertIn(self.offer_memphis, qs)
        qs = OfferGroup.objects.all()
        self.assertIn(self.offer_elvis, qs[0].offers.all())
        self.assertIn(self.offer_memphis, qs[0].offers.all())

    def test_apply_offer_group(self):
        qs = OfferGroup.objects.all()
        offers = qs[0].offers.all()
        offer = offers[0]  # offer_elvis
        line = self.basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 0)
        self.assertEqual(line.quantity_without_discount, 5)

        discount = offer.apply_benefit(self.basket)
        self.assertEqual(discount.discount, D('220.0'))
        self.assertEqual(line.quantity_with_discount, 0)  # !
        self.assertEqual(line.quantity_without_discount, 5)  # !

        offer = offers[1]  # offer memphis
        discount = offer.apply_benefit(self.basket)
        self.assertEqual(discount.discount, D('0.0'))  # !
        self.assertEqual(line.quantity_with_discount, 0)  # !
        self.assertEqual(line.quantity_without_discount, 5)  # !

        offer = qs[1].offers.first()  # offer beatles
        discount = offer.apply_benefit(self.basket)
        self.assertEqual(discount.discount, D('0.0'))  # !
        self.assertEqual(line.quantity_with_discount, 0)  # !
        self.assertEqual(line.quantity_without_discount, 5)  # !



    def test_add_another_offer_group(self):
        cond_a = Condition()
        cond_a.proxy_class = 'oscarbluelight.offer.conditions.BluelightValueCondition'
        cond_a.value = 10
        cond_a.range = self.all_products
        cond_a.save()

        cond_b = Condition()
        cond_b.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        cond_b.value = 2
        cond_b.range = self.all_products
        cond_b.save()

        condition = CompoundCondition()
        condition.proxy_class = 'oscarbluelight.offer.conditions.CompoundCondition'
        condition.conjunction = CompoundCondition.OR
        condition.save()
        condition.subconditions = [cond_a, cond_b]
        condition.save()

        benefit = Benefit()
        benefit.proxy_class = 'oscarbluelight.offer.benefits.BluelightFixedPriceBenefit'
        benefit.value = 0
        benefit.range = self.all_products
        benefit.max_affected_items = 3
        benefit.save()

        offer = ConditionalOffer()
        offer.condition = condition
        offer.benefit = benefit
        offer.name = 'test cond offer 5'
        offer.priority = 1
        offer.save()

        self.offer_group_stones.offers.add(offer)

        qs = OfferGroup.objects.all().order_by('priority')
        self.assertEqual(qs.first(), self.offer_group_elvis)

        qs = qs.last().offers.all().order_by('priority')

        self.assertEqual(qs[0], offer)

        line = self.basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 0)
        self.assertEqual(line.quantity_without_discount, 5)

        discount = offer.apply_benefit(self.basket)

        line = self.basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 3)
        self.assertEqual(line.quantity_without_discount, 2)

        self.assertEqual(discount.discount, D('600.00'))
        self.assertEqual(self.basket.total_excl_tax_excl_discounts, D('1000.00'))
        self.assertEqual(self.basket.total_excl_tax, D('400.00'))

        discount = qs[0].apply_benefit(self.basket)

        line = self.basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 5)
        self.assertEqual(line.quantity_without_discount, 0)

        self.assertEqual(discount.discount, D('400.00'))
        self.assertEqual(self.basket.total_excl_tax_excl_discounts, D('1000.00'))
        self.assertEqual(self.basket.total_excl_tax, D('0.00'))

        qs = OfferGroup.objects.filter(name='test offer group beatles')
        voucher = qs.first().offers.all()

        discount = voucher[0].apply_benefit(self.basket)
        self.assertEqual(discount.discount, D('0.00'))
        self.assertEqual(self.basket.total_excl_tax_excl_discounts, D('1000.00'))
        self.assertEqual(self.basket.total_excl_tax, D('0.00'))


class OfferGroupFormTest(TestCase):
    def setUp(self):
        self.offer_group = OfferGroup.objects.create(
            name="An Offer Group",
            priority=5
        )
        self.all_products = Range()
        self.all_products.includes_all_products = True
        self.all_products.save()
        self.condition = Condition()
        self.condition.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        self.condition.value = 5
        self.condition.range = self.all_products
        self.condition.save()
        self.benefit = Benefit()
        self.benefit.proxy_class = 'oscarbluelight.offer.benefits.BluelightShippingFixedPriceBenefit'
        self.benefit.value = 1
        self.benefit.save()
        self.offer = ConditionalOffer(name="123 test")
        self.offer.condition = self.condition
        self.offer.benefit = self.benefit
        self.offer.save()
        self.offer_group.offers.add(self.offer)


    def test_form_valid(self):
        data = {'name': self.offer_group.name, 'priority': self.offer_group.priority + 1, 'offers': [self.offer.pk]}
        form = OfferGroupForm(
            data=data
        )
        self.assertTrue(form.is_valid())

    def test_form_invalid(self):
        # no priority
        data = {'name': self.offer_group.name, 'offer': 'lorem ipsum'}
        form = OfferGroupForm(data=data)
        self.assertFalse(form.is_valid())
        # bad priority
        data = {'name': self.offer_group.name, 'priority': 'lorem ipsum', 'offer': 'lorem ipsum'}
        form = OfferGroupForm(data=data)
        self.assertFalse(form.is_valid())
        # dupe priority
        data = {'name': self.offer_group.name, 'priority': self.offer_group.priority, 'offer': self.offer}
        form = OfferGroupForm(data=data)
        self.assertFalse(form.is_valid())

    def test_create_offer_group(self):
        condition = Condition()
        condition.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        condition.value = 2
        condition.range = self.all_products
        condition.save()
        benefit = Benefit()
        benefit.proxy_class = 'oscarbluelight.offer.benefits.BluelightShippingFixedPriceBenefit'
        benefit.value = 3
        benefit.save()
        offer = ConditionalOffer(name='testing ABC')
        offer.condition = condition
        offer.benefit = benefit
        offer.save()

        data = {'name': "A New Name", 'priority': 4567, 'offers': [offer.pk]}
        form = OfferGroupForm(data=data)

        self.assertTrue(form.is_valid())
        form.save()
        qs = OfferGroup.objects.all()
        self.assertIsInstance(qs.first(), OfferGroup)

    def test_create_offer_offer_group(self):
        data = {'name': "A New Name", 'priority': 4567, 'offers': [self.offer.pk]}
        form = OfferGroupForm(data=data)
        self.assertTrue(form.is_valid())
        form.save()

        qs = OfferGroup.objects.all()
        self.assertIsInstance(qs.first(), OfferGroup)
        qs.first().offers.add(self.offer)
        self.assertIn(self.offer, qs.first().offers.all())


class OfferGroupViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.name = 'An Offer Group'
        self.priority = 5
        self.all_products = Range()
        self.all_products.includes_all_products = True
        self.all_products.save()
        self.condition = Condition()
        self.condition.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        self.condition.value = 5
        self.condition.range = self.all_products
        self.condition.save()
        self.benefit = Benefit()
        self.benefit.proxy_class = 'oscarbluelight.offer.benefits.BluelightShippingFixedPriceBenefit'
        self.benefit.value = 1
        self.benefit.save()
        self.offer = ConditionalOffer(name="Some Offer")
        self.offer.condition = self.condition
        self.offer.benefit = self.benefit
        self.offer.save()
        self.offer_group = OfferGroup.objects.create(
            name="someName",
            priority=5
        )
        self.offer_group.offers.add(self.offer)
        self.user = User.objects.create_user('john', 'lennon@thebeatles.com', 'johnpassword', is_staff=True)
        self.user.save()

    def test_get_list(self):
        self.client.login(username='john', password='johnpassword')
        response = self.client.get(reverse('dashboard:offergroup-list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data.get('offergroup_list')[0].name, 'someName')
        self.assertEqual(response.context_data.get('offergroup_list')[0].priority, 5)

    def test_create(self):
        self.client.login(username='john', password='johnpassword')
        resp_get = self.client.get(reverse('dashboard:offergroup-create'))
        self.assertEqual(resp_get.status_code, 200)
        form = resp_get.context['form']
        data = form.initial
        data['name'] = 'test offergroup'
        data['priority'] = 1234
        data['offers'] = [self.offer.pk]

        response = self.client.post(
            reverse('dashboard:offergroup-create'), data
        )
        self.assertEqual(response.status_code, 302)
        qs = OfferGroup.objects.filter(name='test offergroup')
        self.assertIsInstance(qs.first(), OfferGroup)
        self.assertEqual(qs.first().name, 'test offergroup')
        self.assertEqual(qs.first().priority, 1234)

    def test_delete(self):
        self.client.login(username='john', password='johnpassword')
        response = self.client.post(
            reverse('dashboard:offergroup-delete', args=[self.offer_group.pk])
        )
        self.assertEqual(response.status_code, 302)
        qs = OfferGroup.objects.filter(name='someName')
        self.assertEqual(qs.count(), 0)

    def test_update(self):
        self.client.login(username='john', password='johnpassword')
        resp_get = self.client.get(reverse('dashboard:offergroup-update', args=[self.offer_group.pk]))
        self.assertEqual(resp_get.status_code, 200)
        form = resp_get.context['form']
        data = form.initial
        self.assertEqual(data.get('name'), 'someName')
        self.assertEqual(data.get('priority'), 5)
        data['name'] = 'another test'
        data['priority'] = 2345
        data['offers'] = [self.offer.pk]
        response = self.client.post(
            reverse('dashboard:offergroup-update', args=[self.offer_group.pk]), data
        )
        self.assertEqual(response.status_code, 302)
        qs = OfferGroup.objects.filter(name='another test')
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().priority, 2345)

    def test_update_voucher(self):
        voucher = Voucher.objects.create(
            name='Test Voucher',
            code='test-voucher',
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now() + timedelta(seconds=120),
            limit_usage_by_group=False
        )
        voucher.offers.add(self.offer)
        self.offer_group.offers.add(voucher.offers.first())
        self.client.login(username='john', password='johnpassword')
        resp_get = self.client.get(reverse('dashboard:offergroup-update', args=[self.offer_group.pk]))
        self.assertEqual(resp_get.status_code, 200)
        form = resp_get.context['form']
        data = form.initial
        self.assertEqual(data.get('name'), 'someName')
        self.assertEqual(data.get('priority'), 5)
        data['priority'] = 2345
        data['offers'] = [self.offer.pk, voucher]
        response = self.client.post(
            reverse('dashboard:offergroup-update', args=[self.offer_group.pk]), data
        )
        self.assertEqual(response.status_code, 200)

        qs = Voucher.objects.filter(name='Test Voucher')
        self.assertEqual(qs.count(), 1)
