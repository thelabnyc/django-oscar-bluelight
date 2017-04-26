from datetime import datetime, timedelta
from decimal import Decimal as D
from django.test import TestCase
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
from oscarbluelight.dashboard.offers.forms import OfferGroupForm, RestrictionsForm
from oscarbluelight.voucher.models import Voucher
from django.contrib.auth.models import User, Group
from oscar.test.factories import create_basket, create_product, create_stockrecord


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
        condition1 = Condition(name='test condition 2')
        condition1.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        condition1.value = 5
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

        condition2 = Condition(name='test condition 2')
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


class TestConsumeOfferGroupOffer(TestCase):
    def setUp(self):
        '''
        offer_groups 1, 2 and 3 with ascending order (application order)
        offers 1, 2, 3 and 4
        offers 1 and 2 -> offer_group 1
        offer3 -> offer_group2
        offer4 -> offer_group3
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

        self.offer_group1 = OfferGroup.objects.create(
            name='test offer group 1',
            priority=3
        )
        self.offer_group1.save()

        self.offer_group2 = OfferGroup.objects.create(
            name='test offer group 2',
            priority=5
        )
        self.offer_group2.save()

        self.offer_group3 = OfferGroup.objects.create(
            name='test offer group 3',
            priority=8
        )
        self.offer_group3.save()

        self.condition1 = Condition(name='test condition 1')
        self.condition1.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        self.condition1.value = 2
        self.condition1.range = self.all_products
        self.condition1.save()
        self.benefit1 = Benefit()
        self.benefit1.proxy_class = 'oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit'
        self.benefit1.value = 20
        self.benefit1.range = self.all_products
        self.benefit1.save()
        self.offer1 = ConditionalOffer(name='cond offer test 1')
        self.offer1.condition = self.condition1
        self.offer1.benefit = self.benefit1
        self.offer1.priority = 10
        self.offer1.save()

        self.offer_group1.offers.add(self.offer1)


        self.benefit2 = Benefit()
        self.benefit2.proxy_class = 'oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit'
        self.benefit2.value = 15
        self.benefit2.range = self.all_products
        self.benefit2.save()
        self.offer2 = ConditionalOffer(name='cond offer test 2')
        self.offer2.condition = self.condition1
        self.offer2.benefit = self.benefit2
        self.offer2.priority = 20
        self.offer2.save()

        self.offer_group1.offers.add(self.offer2)

        self.offer3 = ConditionalOffer(name='cond offer test 3')
        self.offer3.condition = self.condition1
        self.offer3.benefit = self.benefit1
        self.offer3.save()
        self.offer3.priority = 30
        self.offer_group2.offers.add(self.offer3)

        self.value_condition = Condition(name='test condition 2')
        self.value_condition.proxy_class = 'oscarbluelight.offer.conditions.BluelightValueCondition'
        self.value_condition.value = 50
        self.value_condition.range = self.all_products
        self.value_condition.save()
        self.fixed_price_benefit = Benefit()
        self.fixed_price_benefit.proxy_class = 'oscarbluelight.offer.benefits.BluelightFixedPriceBenefit'
        self.fixed_price_benefit.value = 25
        self.fixed_price_benefit.range = self.all_products
        self.fixed_price_benefit.save()
        self.offer4 = ConditionalOffer(name='cond offer test 4')
        self.offer4.condition = self.condition1
        self.offer4.benefit = self.benefit1
        self.offer4.priority = 40
        self.offer4.save()

        self.offer_group3.offers.add(self.offer4)

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
        self.voucher.offers.add(self.offer3)
        self.offer_group2.offers.add(self.voucher.offers.first())


    def test_offer_group2(self):
        qs = OfferGroup.objects.filter(priority=5)
        self.assertEqual(qs.first().offers.first(), self.offer3)

    def test_voucher_order(self):
        self.assertEqual(self.voucher.offers.first().name, 'cond offer test 3')
        self.assertEqual(self.voucher.offers.first().offer_group.priority, 5)

    def test_offer_group1(self):
        qs = ConditionalOffer.objects.filter(offer_group=self.offer_group1)
        self.assertIn(self.offer1, qs)
        self.assertIn(self.offer2, qs)
        qs = OfferGroup.objects.all()
        self.assertIn(self.offer1, qs[0].offers.all())
        self.assertIn(self.offer2, qs[0].offers.all())
        qs = OfferGroup.objects.filter(priority=8)
        self.assertEqual(qs[0].offers.first().name, 'cond offer test 4')


    def test_apply_offer_group(self):
        qs = ConditionalOffer.objects.all()
        offer = qs[0]
        line = self.basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 0)
        self.assertEqual(line.quantity_without_discount, 5)

        discount = offer.apply_benefit(self.basket)
        self.assertEqual(discount.discount, D('20.0'))
        offer = qs[3]
        discount = offer.apply_benefit(self.basket)

        self.assertEqual(line.quantity_with_discount, 0)
        self.assertEqual(line.quantity_without_discount, 5)

    def test_apply_another_offer_group(self):
        '''
        run through a tested test
        '''
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

        self.offer_group3.offers.add(offer)

        qs = OfferGroup.objects.all().order_by('priority')
        self.assertEqual(qs.first(), self.offer_group1)

        qs = qs.last().offers.all().order_by('priority')

        self.assertEqual(qs[0], offer)
        self.assertEqual(qs[1], self.offer4)

        line = self.basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 0)
        self.assertEqual(line.quantity_without_discount, 5)

        discount = offer.apply_benefit(self.basket)

        line = self.basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 3)
        self.assertEqual(line.quantity_without_discount, 2)

        self.assertEqual(discount.discount, D('600.00'))
        self.assertEqual(self.basket.total_excl_tax_excl_discounts, D('1000.00'))  # 5 * 200
        self.assertEqual(self.basket.total_excl_tax, D('400.00'))

        discount = qs[1].apply_benefit(self.basket)

        line = self.basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 5)
        self.assertEqual(line.quantity_without_discount, 0)

        self.assertEqual(discount.discount, D('20.00'))
        self.assertEqual(self.basket.total_excl_tax_excl_discounts, D('1000.00'))  # 5 * 200
        self.assertEqual(self.basket.total_excl_tax, D('380.00'))

        qs = OfferGroup.objects.filter(name='test offer group 2')
        voucher = qs.first().offers.all()

        discount = voucher[0].apply_benefit(self.basket)
        self.assertEqual(discount.discount, D('0.00'))
        self.assertEqual(self.basket.total_excl_tax_excl_discounts, D('1000.00'))  # 5 * 200
        self.assertEqual(self.basket.total_excl_tax, D('380.00'))


class TestOfferGroupForm(TestCase):
    def setUp(self):
        self.name = 'An Offer Group'
        self.priority = 5
        self.all_products = Range()
        self.all_products.includes_all_products = True
        self.all_products.save()
        self.condition = Condition(name='test condition 2')
        self.condition.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        self.condition.value = 5
        self.condition.range = self.all_products
        self.condition.save()
        self.benefit = Benefit()
        self.benefit.proxy_class = 'oscarbluelight.offer.benefits.BluelightShippingFixedPriceBenefit'
        self.benefit.value = 1
        self.benefit.save()
        self.offer = ConditionalOffer(name='test3')
        self.offer.condition = self.condition
        self.offer.benefit = self.benefit
        self.offer.save()

    def test_form_valid(self):
        data = {'name': self.name, 'priority': self.priority}
        form = OfferGroupForm(data=data)
        self.assertTrue(form.is_valid())

    def test_form_invalid(self):
        data = {'name': self.name, 'offer': 'lorem ipsum'}
        form = OfferGroupForm(data=data)
        self.assertFalse(form.is_valid())

    def test_create_offer_group(self):
        data = {'name': self.name, 'priority': self.priority}
        form = OfferGroupForm(data=data)
        form.save()
        qs = OfferGroup.objects.all()
        self.assertIsInstance(qs.first(), OfferGroup)

    def test_create_offer_offer_group(self):
        data = {'name': self.name, 'priority': self.priority}
        form = OfferGroupForm(data=data)
        form.save()
        
        qs = OfferGroup.objects.all()
        self.assertIsInstance(qs.first(), OfferGroup)
        qs.first().offers.add(self.offer)
        self.assertIn(self.offer, qs.first().offers.all())

class TestOfferGroupView(TestCase):
    def setUp(self):
        self.client = Client()
        self.name = 'An Offer Group'
        self.priority = 5
        self.all_products = Range()
        self.all_products.includes_all_products = True
        self.all_products.save()
        self.condition = Condition(name='test condition 2')
        self.condition.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        self.condition.value = 5
        self.condition.range = self.all_products
        self.condition.save()
        self.benefit = Benefit()
        self.benefit.proxy_class = 'oscarbluelight.offer.benefits.BluelightShippingFixedPriceBenefit'
        self.benefit.value = 1
        self.benefit.save()
        self.offer = ConditionalOffer(name='test3')
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
        print(reverse('dashboard:offergroup-create'))
        response = self.client.post(
            reverse('dashboard:offergroup-create', 
                kwargs={'name': "another Test", 'priority': 17 }
            )
        )
        self.assertEqual(response.status_code, 201)
        qs = OfferGroup.objects.filter(name='another Test')
        self.assertIsInstance(qs.first(), OfferGroup)

    def test_delete(self):
        self.client.login(username='john', password='johnpassword')
        response = self.client.post(
            reverse('dashboard:offergroup-delete', args=[self.offer_group.pk])
        )
        self.assertEqual(response.status_code, 302)
    

