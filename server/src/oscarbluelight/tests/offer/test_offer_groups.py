from datetime import datetime, timedelta
from decimal import Decimal as D
from django.contrib.auth.models import User
from django.test import TestCase
from django.test import Client
from django.core.urlresolvers import reverse
from oscar.core.loading import get_model, get_class
from oscar.test.factories import create_basket, create_product, create_stockrecord

OfferGroup = get_model('offer', 'OfferGroup')
Benefit = get_model('offer', 'Benefit')
Range = get_model('offer', 'Range')
Condition = get_model('offer', 'Condition')
CompoundCondition = get_model('offer', 'CompoundCondition')
ConditionalOffer = get_model('offer', 'ConditionalOffer')
Voucher = get_model('voucher', 'Voucher')

Applicator = get_class('offer.applicator', 'Applicator')
BasketDiscount = get_class('offer.results', 'BasketDiscount')
OfferGroupForm = get_class('dashboard.offers.forms', 'OfferGroupForm')



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

        self.offer_group1 = OfferGroup(name='test', priority=1)
        self.offer_group1.save()
        self.offer_group1.offers.add(self.offer1)


    def test_create_offer_group(self):
        self.assertIsNotNone(self.offer_group1)
        self.assertEqual(self.offer_group1.name, 'test')
        self.assertEqual(self.offer_group1.priority, 1)
        self.assertIn(self.offer1, self.offer_group1.offers.all())


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
        offer_group1 = OfferGroup.objects.create(name='test offer group 1', priority=2)
        offer_group1.save()

        offer_group2 = OfferGroup.objects.create(name='test offer group 2', priority=3)
        offer_group2.save()

        offer_group3 = OfferGroup.objects.create(name='test offer group 3', priority=4)
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
        offer_group = OfferGroup(name='test', priority=1)
        with self.assertRaises(Exception):
            offer_group.save()



class ConsumeOfferGroupOfferTest(TestCase):
    def setUp(self):
        self.all_products = Range()
        self.all_products.includes_all_products = True
        self.all_products.save()

        item_price = 200.0
        item_quantity = 5
        product = create_product()
        create_stockrecord(product, item_price, num_in_stock=item_quantity * 2)

        self.basket = create_basket(empty=True)
        self.basket.add_product(product, quantity=item_quantity)

        self.offer_group_elvis = OfferGroup.objects.create(name='test offer group elvis', priority=3)
        self.offer_group_elvis.save()

        self.offer_group_beatles = OfferGroup.objects.create(name='test offer group beatles', priority=2)
        self.offer_group_beatles.save()

        self.offer_group_stones = OfferGroup.objects.create(name='test offer group stones', priority=1)
        self.offer_group_stones.save()

        condition1 = Condition()
        condition1.proxy_class = 'oscarbluelight.offer.conditions.BluelightValueCondition'
        condition1.value = 3.45
        condition1.range = self.all_products
        condition1.save()

        condition2 = Condition()
        condition2.proxy_class = 'oscarbluelight.offer.conditions.BluelightCoverageCondition'
        condition2.range = self.all_products
        condition2.save()

        benefit1 = Benefit()
        benefit1.proxy_class = 'oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit'
        benefit1.value = 22
        benefit1.range = self.all_products
        benefit1.save()

        benefit2 = Benefit()
        benefit2.proxy_class = 'oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit'
        benefit2.value = 23
        benefit2.range = self.all_products
        benefit2.save()

        benefit3 = Benefit()
        benefit3.proxy_class = 'oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit'
        benefit3.value = 24
        benefit3.range = self.all_products
        benefit3.save()

        benefit4 = Benefit()
        benefit4.proxy_class = 'oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit'
        benefit4.value = 32
        benefit4.range = self.all_products
        benefit4.save()

        self.offer_elvis = ConditionalOffer(name='cond offer test 1')
        self.offer_elvis.condition = condition1
        self.offer_elvis.benefit = benefit1
        self.offer_elvis.priority = 1
        self.offer_elvis.save()
        self.offer_group_elvis.offers.add(self.offer_elvis)

        self.offer_memphis = ConditionalOffer(name='cond offer test 2')
        self.offer_memphis.condition = condition1
        self.offer_memphis.benefit = benefit2
        self.offer_memphis.priority = 2
        self.offer_memphis.save()
        self.offer_group_elvis.offers.add(self.offer_memphis)

        self.offer_beatles = ConditionalOffer(name='cond offer test 3')
        self.offer_beatles.condition = condition1
        self.offer_beatles.benefit = benefit3
        self.offer_beatles.priority = 3
        self.offer_beatles.save()
        self.offer_group_beatles.offers.add(self.offer_beatles)

        self.offer_stones = ConditionalOffer(name='cond offer test stones')
        self.offer_stones.condition = condition2
        self.offer_stones.benefit = benefit4
        self.offer_stones.priority = 4
        self.offer_stones.save()
        self.offer_group_beatles.offers.add(self.offer_stones)

        self.voucher = Voucher.objects.create(
            name='Test Voucher',
            code='test-voucher',
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now() + timedelta(seconds=120),
            limit_usage_by_group=False)
        self.voucher.offers.add(self.offer_stones)


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

        # Make sure group ordering is correct
        self.assertEqual(qs[0], self.offer_group_elvis)
        self.assertEqual(qs[1], self.offer_group_beatles)
        self.assertEqual(qs[2], self.offer_group_stones)

        offers = qs[0].offers.all()

        line = self.basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 0)
        self.assertEqual(line.quantity_without_discount, 5)

        offer = offers[0]  # offer_memphis
        self.assertEqual(offer, self.offer_memphis)

        discount = offer.apply_benefit(self.basket)
        self.assertEqual(discount.discount, D('23.0'))

        line = self.basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 5)
        self.assertEqual(line.quantity_without_discount, 0)

        offer = offers[1]  # offer_elvis
        self.assertEqual(offer, self.offer_elvis)

        discount = offer.apply_benefit(self.basket)
        self.assertEqual(discount.discount, D('0.0'))

        line = self.basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 5)
        self.assertEqual(line.quantity_without_discount, 0)

        offer = qs[1].offers.first()  # offer_stones
        self.assertEqual(offer, self.offer_stones)

        discount = offer.apply_benefit(self.basket)
        self.assertEqual(discount.discount, D('0.0'))

        line = self.basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 5)
        self.assertEqual(line.quantity_without_discount, 0)


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

        qs = OfferGroup.objects.all()
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



class OfferGroupApplicatorTest(TestCase):
    def setUp(self):
        self.all_products = Range()
        self.all_products.includes_all_products = True
        self.all_products.save()
        self.user = User.objects.create_user('john', 'lennon@thebeatles.com', 'johnpassword')


    def test_apply_offers(self):
        condition1 = Condition()
        condition1.proxy_class = 'oscarbluelight.offer.conditions.BluelightValueCondition'
        condition1.range = self.all_products
        condition1.value = 5.32
        condition1.save()

        condition2 = Condition()
        condition2.proxy_class = 'oscarbluelight.offer.conditions.BluelightValueCondition'
        condition2.range = self.all_products
        condition2.value = 6.32
        condition2.save()

        benefit1 = Benefit()
        benefit1.proxy_class = 'oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit'
        benefit1.value = 10.02
        benefit1.range = self.all_products
        benefit1.save()

        benefit2 = Benefit()
        benefit2.proxy_class = 'oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit'
        benefit2.value = 15.02
        benefit2.range = self.all_products
        benefit2.save()

        offer = ConditionalOffer(name='cond offer no offergroup')
        offer.condition = condition1
        offer.benefit = benefit1
        offer.priority = 2
        offer.save()

        offer_stooges = ConditionalOffer(name='offer stooges')
        offer_stooges.condition = condition2
        offer_stooges.benefit = benefit2
        offer_stooges.priority = 1
        offer_stooges.save()

        offer_group_stooges = OfferGroup.objects.create(name='test offer group stooges', priority=1)
        offer_group_stooges.save()
        offer_group_stooges.offers.add(offer_stooges)

        product = create_product()
        create_stockrecord(product, D('200.00'), num_in_stock=100)

        basket = create_basket(empty=True)
        basket.add_product(product, quantity=2)

        # Ensure nothing is discounted yet
        lines = basket.all_lines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].quantity, 2)
        self.assertEqual(lines[0]._affected_quantity, 0)
        self.assertEqual(lines[0].quantity_with_discount, 0)
        self.assertEqual(lines[0].quantity_without_discount, 2)

        # Apply offers to the basket
        offers = ConditionalOffer.objects.all()
        Applicator().apply(basket, self.user, list(offers))

        # Ensure discount affected both items in the line
        lines = basket.all_lines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].quantity, 2)
        self.assertEqual(lines[0]._affected_quantity, 2)
        self.assertEqual(lines[0].quantity_with_discount, 2)
        self.assertEqual(lines[0].quantity_without_discount, 0)

        # Confirm basket price is correct
        self.assertEqual(basket.total_discount, D('94.13'))
        self.assertEqual(basket.total_excl_tax, D('305.87'))

        # Test that both discounts resulted in the correct discount amount, thereby confirming application order
        applied_offfers = basket.offer_applications.offers
        self.assertEqual(len(applied_offfers), 2)
        self.assertEqual(applied_offfers[offer_stooges.pk], offer_stooges)
        self.assertEqual(applied_offfers[offer.pk], offer)

        # Test that offer_stooges was applied first and subtracted $60.08 from the line price, bringing
        # the remaining line price to $339.92
        application = basket.offer_applications.applications[offer_stooges.pk]
        self.assertIsNone(application['description'])
        self.assertEqual(application['discount'], D('60.08'))
        self.assertEqual(application['freq'], 1)
        self.assertEqual(application['name'], 'offer stooges')
        self.assertEqual(application['offer'], offer_stooges)
        self.assertIsInstance(application['result'], BasketDiscount)
        self.assertEqual(application['result'].discount, D('60.08'))
        self.assertIsNone(application['voucher'])

        # Test that offer was applied second and subtracted another $34.05 from the line price, bringing the
        # remaining line price to $305.87.
        application = basket.offer_applications.applications[offer.pk]
        self.assertIsNone(application['description'])
        self.assertEqual(application['discount'], D('34.05'))
        self.assertEqual(application['freq'], 1)
        self.assertEqual(application['name'], 'cond offer no offergroup')
        self.assertEqual(application['offer'], offer)
        self.assertIsInstance(application['result'], BasketDiscount)
        self.assertEqual(application['result'].discount, D('34.05'))
        self.assertIsNone(application['voucher'])


    def test_line_prices_never_become_negative(self):
        condition_require_one_product = Condition()
        condition_require_one_product.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        condition_require_one_product.range = self.all_products
        condition_require_one_product.value = 1
        condition_require_one_product.save()

        condition_require_two_products = Condition()
        condition_require_two_products.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        condition_require_two_products.range = self.all_products
        condition_require_two_products.value = 2
        condition_require_two_products.save()

        benefit_one_product_free = Benefit()
        benefit_one_product_free.proxy_class = 'oscarbluelight.offer.benefits.BluelightMultibuyDiscountBenefit'
        benefit_one_product_free.value = None
        benefit_one_product_free.range = self.all_products
        benefit_one_product_free.save()

        benefit_300_dollars_off = Benefit()
        benefit_300_dollars_off.proxy_class = 'oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit'
        benefit_300_dollars_off.value = 300
        benefit_300_dollars_off.range = self.all_products
        benefit_300_dollars_off.save()

        offer_group1 = OfferGroup.objects.create(name='Offer Group 1', priority=1)
        offer_group2 = OfferGroup.objects.create(name='Offer Group 2', priority=2)

        offer_300_dollars_off = ConditionalOffer(name='Sitewide $300 Off!')
        offer_300_dollars_off.condition = condition_require_one_product
        offer_300_dollars_off.benefit = benefit_300_dollars_off
        offer_300_dollars_off.offer_group = offer_group1
        offer_300_dollars_off.priority = 1
        offer_300_dollars_off.save()

        offer_bogo = ConditionalOffer(name='Buy One Product, Get One Free')
        offer_bogo.condition = condition_require_two_products
        offer_bogo.benefit = benefit_one_product_free
        offer_bogo.offer_group = offer_group2
        offer_bogo.priority = 1
        offer_bogo.save()

        product = create_product()
        create_stockrecord(product, D('100.00'), num_in_stock=100)

        basket = create_basket(empty=True)
        basket.add_product(product, quantity=2)

        # Ensure nothing is discounted yet
        lines = basket.all_lines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].quantity, 2)
        self.assertEqual(lines[0]._affected_quantity, 0)
        self.assertEqual(lines[0].quantity_with_discount, 0)
        self.assertEqual(lines[0].quantity_without_discount, 2)

        # Basket price should be $200
        self.assertEqual(basket.total_excl_tax_excl_discounts, D('200.00'))
        self.assertEqual(basket.total_excl_tax, D('200.00'))
        self.assertEqual(basket.total_discount, D('0.00'))

        # Apply offers to the basket
        offers = ConditionalOffer.objects.all()
        Applicator().apply(basket, self.user, list(offers))

        # Ensure discount affected both items in the line
        lines = basket.all_lines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].quantity, 2)
        self.assertEqual(lines[0]._affected_quantity, 2)
        self.assertEqual(lines[0].quantity_with_discount, 2)
        self.assertEqual(lines[0].quantity_without_discount, 0)

        # Basket price should be $0
        self.assertEqual(basket.total_excl_tax_excl_discounts, D('200.00'))
        self.assertEqual(basket.total_excl_tax, D('0.00'))
        self.assertEqual(basket.total_discount, D('200.00'))

        # Both offers should have been applied
        applied_offfers = basket.offer_applications.offers
        self.assertEqual(len(applied_offfers), 2)

        # Test that offer_bogo was applied first and subtracted $100 from the line price, bringing
        # the remaining line price to $100
        application = basket.offer_applications.applications[offer_bogo.pk]
        self.assertIsNone(application['description'])
        self.assertEqual(application['discount'], D('100.00'))
        self.assertEqual(application['freq'], 1)
        self.assertEqual(application['name'], 'Buy One Product, Get One Free')
        self.assertEqual(application['offer'], offer_bogo)
        self.assertIsInstance(application['result'], BasketDiscount)
        self.assertEqual(application['result'].discount, D('100.00'))
        self.assertIsNone(application['voucher'])

        # Test that offer_300_dollars_off was applied second and subtracted another $100 from the
        # line price, bringing the remaining line price to $0
        application = basket.offer_applications.applications[offer_300_dollars_off.pk]
        self.assertIsNone(application['description'])
        self.assertEqual(application['discount'], D('100.00'))
        self.assertEqual(application['freq'], 1)
        self.assertEqual(application['name'], 'Sitewide $300 Off!')
        self.assertEqual(application['offer'], offer_300_dollars_off)
        self.assertIsInstance(application['result'], BasketDiscount)
        self.assertEqual(application['result'].discount, D('100.00'))
        self.assertIsNone(application['voucher'])

        # Set tax on the line
        lines = basket.all_lines()
        self.assertEqual(len(lines), 1)
        lines[0].purchase_info.price.tax = D('1.00')

        # Ensure the price breakdown still returns tax, even though the rest of the line is free.
        self.assertEqual(lines[0].quantity, 2)
        price_breakdown = lines[0].get_price_breakdown()
        self.assertEqual(len(price_breakdown), 1)
        self.assertEqual(price_breakdown[0], (D('2.00'), D('0.00'), 2))


    def test_price_breakdown_distributes_tax_evenly(self):
        condition_require_two_products = Condition()
        condition_require_two_products.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        condition_require_two_products.range = self.all_products
        condition_require_two_products.value = 2
        condition_require_two_products.save()

        benefit_one_product_free = Benefit()
        benefit_one_product_free.proxy_class = 'oscarbluelight.offer.benefits.BluelightMultibuyDiscountBenefit'
        benefit_one_product_free.value = None
        benefit_one_product_free.range = self.all_products
        benefit_one_product_free.save()

        offer_bogo = ConditionalOffer(name='Buy One Product, Get One Free')
        offer_bogo.condition = condition_require_two_products
        offer_bogo.benefit = benefit_one_product_free
        offer_bogo.priority = 1
        offer_bogo.save()

        product = create_product()
        create_stockrecord(product, D('100.00'), num_in_stock=100)

        basket = create_basket(empty=True)
        basket.add_product(product, quantity=2)

        # Basket price should be $200
        self.assertEqual(basket.total_excl_tax_excl_discounts, D('200.00'))
        self.assertEqual(basket.total_excl_tax, D('200.00'))
        self.assertEqual(basket.total_discount, D('0.00'))

        # Apply offers to the basket
        offers = ConditionalOffer.objects.all()
        Applicator().apply(basket, self.user, list(offers))

        # Basket price should be $100
        self.assertEqual(basket.total_excl_tax_excl_discounts, D('200.00'))
        self.assertEqual(basket.total_excl_tax, D('100.00'))
        self.assertEqual(basket.total_discount, D('100.00'))

        # Set tax on the line
        lines = basket.all_lines()
        self.assertEqual(len(lines), 1)
        lines[0].purchase_info.price.tax = D('1.00')

        # Basket price should be $102
        self.assertEqual(basket.total_excl_tax_excl_discounts, D('200.00'))
        self.assertEqual(basket.total_incl_tax_excl_discounts, D('202.00'))
        self.assertEqual(basket.total_excl_tax, D('100.00'))
        self.assertEqual(basket.total_incl_tax, D('102.00'))
        self.assertEqual(basket.total_discount, D('100.00'))

        # Ensure the price breakdown distributes tax evenly based on post-discount unit price ratios
        self.assertEqual(lines[0].quantity, 2)
        price_breakdown = lines[0].get_price_breakdown()
        self.assertEqual(len(price_breakdown), 2)

        # First entry in breakdown should be free item (due to the buy one get one free offer)
        self.assertEqual(price_breakdown[0], (D('0.00'), D('0.00'), 1))

        # Second entry in breakdown should be the other item at full price, plus all the tax
        self.assertEqual(price_breakdown[1], (D('102.00'), D('100.00'), 1))


    def test_offers_cannot_compound_within_a_group(self):
        condition_require_one_product = Condition()
        condition_require_one_product.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        condition_require_one_product.range = self.all_products
        condition_require_one_product.value = 1
        condition_require_one_product.save()

        condition_require_two_products = Condition()
        condition_require_two_products.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        condition_require_two_products.range = self.all_products
        condition_require_two_products.value = 2
        condition_require_two_products.save()

        benefit_one_product_free = Benefit()
        benefit_one_product_free.proxy_class = 'oscarbluelight.offer.benefits.BluelightMultibuyDiscountBenefit'
        benefit_one_product_free.value = None
        benefit_one_product_free.range = self.all_products
        benefit_one_product_free.save()

        benefit_300_dollars_off = Benefit()
        benefit_300_dollars_off.proxy_class = 'oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit'
        benefit_300_dollars_off.value = 300
        benefit_300_dollars_off.range = self.all_products
        benefit_300_dollars_off.save()

        offer_group1 = OfferGroup.objects.create(name='Offer Group 1', priority=1)

        offer_300_dollars_off = ConditionalOffer(name='Sitewide $300 Off!')
        offer_300_dollars_off.condition = condition_require_one_product
        offer_300_dollars_off.benefit = benefit_300_dollars_off
        offer_300_dollars_off.offer_group = offer_group1
        offer_300_dollars_off.priority = 1
        offer_300_dollars_off.save()

        offer_bogo = ConditionalOffer(name='Buy One Product, Get One Free')
        offer_bogo.condition = condition_require_two_products
        offer_bogo.benefit = benefit_one_product_free
        offer_bogo.offer_group = offer_group1
        offer_bogo.priority = 2
        offer_bogo.save()

        product = create_product()
        create_stockrecord(product, D('100.00'), num_in_stock=100)

        basket = create_basket(empty=True)
        basket.add_product(product, quantity=2)

        # Basket price should be $200
        self.assertEqual(basket.total_excl_tax_excl_discounts, D('200.00'))
        self.assertEqual(basket.total_excl_tax, D('200.00'))
        self.assertEqual(basket.total_discount, D('0.00'))

        # Apply offers to the basket. The BOGO offer should apply first and consume both items, preventing the $300
        # off discount from applying at all.
        offers = ConditionalOffer.objects.all()
        Applicator().apply(basket, self.user, list(offers))

        # Basket price should be $100
        self.assertEqual(basket.total_excl_tax_excl_discounts, D('200.00'))
        self.assertEqual(basket.total_excl_tax, D('100.00'))
        self.assertEqual(basket.total_discount, D('100.00'))

        # Test that the BOGO Offer was applied
        applied_offfers = basket.offer_applications.offers
        self.assertEqual(len(applied_offfers), 1)

        application = basket.offer_applications.applications[offer_bogo.pk]
        self.assertIsNone(application['description'])
        self.assertEqual(application['discount'], D('100.00'))
        self.assertEqual(application['freq'], 1)
        self.assertEqual(application['name'], 'Buy One Product, Get One Free')
        self.assertEqual(application['offer'], offer_bogo)
        self.assertIsInstance(application['result'], BasketDiscount)
        self.assertEqual(application['result'].discount, D('100.00'))
        self.assertIsNone(application['voucher'])

        # Test that $300 Off offer was not applied
        self.assertTrue(offer_300_dollars_off.pk not in basket.offer_applications.applications)


    def test_sibling_offers_can_coexist_within_a_group(self):
        condition_require_one_product = Condition()
        condition_require_one_product.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        condition_require_one_product.range = self.all_products
        condition_require_one_product.value = 1
        condition_require_one_product.save()

        condition_require_two_products = Condition()
        condition_require_two_products.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        condition_require_two_products.range = self.all_products
        condition_require_two_products.value = 2
        condition_require_two_products.save()

        benefit_one_product_free = Benefit()
        benefit_one_product_free.proxy_class = 'oscarbluelight.offer.benefits.BluelightMultibuyDiscountBenefit'
        benefit_one_product_free.value = None
        benefit_one_product_free.range = self.all_products
        benefit_one_product_free.save()

        benefit_300_dollars_off = Benefit()
        benefit_300_dollars_off.proxy_class = 'oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit'
        benefit_300_dollars_off.value = 300
        benefit_300_dollars_off.range = self.all_products
        benefit_300_dollars_off.save()

        offer_group1 = OfferGroup.objects.create(name='Offer Group 1', priority=1)

        offer_300_dollars_off = ConditionalOffer(name='Sitewide $300 Off!')
        offer_300_dollars_off.condition = condition_require_one_product
        offer_300_dollars_off.benefit = benefit_300_dollars_off
        offer_300_dollars_off.offer_group = offer_group1
        offer_300_dollars_off.priority = 1
        offer_300_dollars_off.save()

        offer_bogo = ConditionalOffer(name='Buy One Product, Get One Free')
        offer_bogo.condition = condition_require_two_products
        offer_bogo.benefit = benefit_one_product_free
        offer_bogo.offer_group = offer_group1
        offer_bogo.priority = 2
        offer_bogo.save()

        product = create_product()
        create_stockrecord(product, D('100.00'), num_in_stock=100)

        basket = create_basket(empty=True)
        basket.add_product(product, quantity=3)

        # Basket price should be $300
        self.assertEqual(basket.total_excl_tax_excl_discounts, D('300.00'))
        self.assertEqual(basket.total_excl_tax, D('300.00'))
        self.assertEqual(basket.total_discount, D('0.00'))

        # Apply offers to the basket. The BOGO offer should apply first and consume the first two items. Then
        # the $300 Off offer should apply and reduce the price of the 3rd line to $0.
        offers = ConditionalOffer.objects.all()
        Applicator().apply(basket, self.user, list(offers))

        # Basket price should be $100
        self.assertEqual(basket.total_excl_tax_excl_discounts, D('300.00'))
        self.assertEqual(basket.total_excl_tax, D('100.00'))
        self.assertEqual(basket.total_discount, D('200.00'))

        # Test that the BOGO Offer was applied
        applied_offfers = basket.offer_applications.offers
        self.assertEqual(len(applied_offfers), 2)

        application = basket.offer_applications.applications[offer_bogo.pk]
        self.assertIsNone(application['description'])
        self.assertEqual(application['discount'], D('100.00'))
        self.assertEqual(application['freq'], 1)
        self.assertEqual(application['name'], 'Buy One Product, Get One Free')
        self.assertEqual(application['offer'], offer_bogo)
        self.assertIsInstance(application['result'], BasketDiscount)
        self.assertEqual(application['result'].discount, D('100.00'))
        self.assertIsNone(application['voucher'])

        # Test that $300 Off offer was also applied
        application = basket.offer_applications.applications[offer_300_dollars_off.pk]
        self.assertIsNone(application['description'])
        self.assertEqual(application['discount'], D('100.00'))
        self.assertEqual(application['freq'], 1)
        self.assertEqual(application['name'], 'Sitewide $300 Off!')
        self.assertEqual(application['offer'], offer_300_dollars_off)
        self.assertIsInstance(application['result'], BasketDiscount)
        self.assertEqual(application['result'].discount, D('100.00'))
        self.assertIsNone(application['voucher'])



class OfferGroupFormTest(TestCase):
    def setUp(self):
        self.all_products = Range()
        self.all_products.includes_all_products = True
        self.all_products.save()

        condition = Condition()
        condition.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        condition.value = 5
        condition.range = self.all_products
        condition.save()

        benefit = Benefit()
        benefit.proxy_class = 'oscarbluelight.offer.benefits.BluelightShippingFixedPriceBenefit'
        benefit.value = 1
        benefit.save()

        self.offer = ConditionalOffer(name="123 test")
        self.offer.condition = condition
        self.offer.benefit = benefit
        self.offer.save()

        self.offer_group = OfferGroup.objects.create(name="An Offer Group", priority=5)
        self.offer_group.offers.add(self.offer)


    def test_form_valid(self):
        data = {
            'name': self.offer_group.name,
            'priority': self.offer_group.priority + 1,
            'offers': [
                self.offer.pk,
            ]
        }
        form = OfferGroupForm(data=data)
        self.assertTrue(form.is_valid())


    def test_form_invalid(self):
        # No priority
        data = {
            'name': self.offer_group.name,
            'offer': 'lorem ipsum'
        }
        form = OfferGroupForm(data=data)
        self.assertFalse(form.is_valid())

        # Bad priority
        data = {
            'name': self.offer_group.name,
            'priority': 'lorem ipsum',
            'offer': 'lorem ipsum'
        }
        form = OfferGroupForm(data=data)
        self.assertFalse(form.is_valid())

        # Duplicate priority
        data = {
            'name': self.offer_group.name,
            'priority': self.offer_group.priority,
            'offer': self.offer,
        }
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

        data = {
            'name': "A New Name",
            'priority': 4567,
            'offers': [
                offer.pk,
            ]
        }
        form = OfferGroupForm(data=data)
        self.assertTrue(form.is_valid())
        form.save()

        qs = OfferGroup.objects.all()
        self.assertIsInstance(qs.first(), OfferGroup)


    def test_create_offer_offer_group(self):
        data = {
            'name': "A New Name",
            'priority': 4567,
            'offers': [
                self.offer.pk,
            ]
        }
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

        all_products = Range()
        all_products.includes_all_products = True
        all_products.save()

        condition = Condition()
        condition.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
        condition.value = 5
        condition.range = all_products
        condition.save()

        benefit = Benefit()
        benefit.proxy_class = 'oscarbluelight.offer.benefits.BluelightShippingFixedPriceBenefit'
        benefit.value = 1
        benefit.save()

        self.offer = ConditionalOffer(name="Some Offer")
        self.offer.condition = condition
        self.offer.benefit = benefit
        self.offer.save()

        self.offer_group = OfferGroup.objects.create(name="someName", priority=5)
        self.offer_group.offers.add(self.offer)

        User.objects.create_user('john', 'lennon@thebeatles.com', 'johnpassword', is_staff=True)


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
        response = self.client.post(reverse('dashboard:offergroup-create'), data)
        self.assertEqual(response.status_code, 302)
        qs = OfferGroup.objects.filter(name='test offergroup')
        self.assertIsInstance(qs.first(), OfferGroup)
        self.assertEqual(qs.first().name, 'test offergroup')
        self.assertEqual(qs.first().priority, 1234)


    def test_delete(self):
        self.client.login(username='john', password='johnpassword')
        response = self.client.post(reverse('dashboard:offergroup-delete', args=[self.offer_group.pk]))
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
        response = self.client.post(reverse('dashboard:offergroup-update', args=[self.offer_group.pk]), data)
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
            limit_usage_by_group=False)
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
        response = self.client.post(reverse('dashboard:offergroup-update', args=[self.offer_group.pk]), data)
        self.assertEqual(response.status_code, 200)
        qs = Voucher.objects.filter(name='Test Voucher')
        self.assertEqual(qs.count(), 1)
