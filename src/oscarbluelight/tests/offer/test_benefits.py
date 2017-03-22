from decimal import Decimal as D
from oscarbluelight.offer.models import (
    Range,
    ConditionalOffer,
    Condition,
    CompoundCondition,
    Benefit,
)
from .base import BaseTest


def _build_offer_with_benefit(benefit_class, benefit_value=None):
    all_products, _ = Range.objects.get_or_create(
        name='site',
        includes_all_products=True)

    condition = Condition()
    condition.proxy_class = 'oscarbluelight.offer.conditions.BluelightCountCondition'
    condition.value = 1
    condition.range = all_products
    condition.save()

    benefit = Benefit()
    benefit.proxy_class = benefit_class
    benefit.value = benefit_value
    benefit.range = all_products
    benefit.save()

    offer = ConditionalOffer()
    offer.condition = condition
    offer.benefit = benefit
    offer.save()

    return offer



class BenefitTest(BaseTest):
    def test_get_applicable_lines(self):
        basket = self._build_basket(item_quantity=1)
        offer = _build_offer_with_benefit('oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit', D('10.0'))
        benefit = offer.benefit

        # Basket is pristine still.
        self.assertEqual(basket.num_items_with_discount, 0)
        self.assertEqual(basket.num_items_without_discount, 1)

        # Turn off applicable_to_discounted_lines.
        offer.applicable_to_discounted_lines = False
        offer.save()

        # Make sure the basket line is returned as applicable
        lines = benefit.get_applicable_lines(offer, basket)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0][0], D('10.00'))
        self.assertEqual(lines[0][1], basket.all_lines()[0])

        # Turn on applicable_to_discounted_lines.
        offer.applicable_to_discounted_lines = True
        offer.save()

        # Make sure the basket line is returned as applicable
        lines = benefit.get_applicable_lines(offer, basket)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0][0], D('10.00'))
        self.assertEqual(lines[0][1], basket.all_lines()[0])

        # Apply an offer.
        discount = offer.apply_benefit(basket)

        # Make sure no lines exist without a discount.
        self.assertEqual(basket.num_items_with_discount, 1)
        self.assertEqual(basket.num_items_without_discount, 0)

        # Turn off applicable_to_discounted_lines.
        offer.applicable_to_discounted_lines = False
        offer.save()

        # Make sure nothing gets returned from the benefit as being applicable.
        lines = benefit.get_applicable_lines(offer, basket)
        self.assertEqual(len(lines), 0)

        # Turn on applicable_to_discounted_lines.
        offer.applicable_to_discounted_lines = True
        offer.save()

        # Make sure the basket line is returned as applicable, even though it's already discounted.
        lines = benefit.get_applicable_lines(offer, basket)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0][0], D('9.00'))
        self.assertEqual(lines[0][1], basket.all_lines()[0])



class BluelightPercentageDiscountBenefitTest(BaseTest):
    def test_apply_with_applicable_to_discounted_lines_off(self):
        basket = self._build_basket(item_quantity=1)
        offer = _build_offer_with_benefit('oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit', D('10.0'))
        offer.applicable_to_discounted_lines = False
        offer.save()

        self.assertEqual(basket.num_items_with_discount, 0)
        self.assertEqual(basket.num_items_without_discount, 1)
        self.assertEqual(basket.total_excl_tax, D('10.00'))

        result = offer.apply_benefit(basket)
        self.assertEqual(result.discount, D('1.00'))
        self.assertEqual(basket.num_items_with_discount, 1)
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.total_excl_tax, D('9.00'))

        result = offer.apply_benefit(basket)
        self.assertEqual(result.discount, D('0.00'))
        self.assertEqual(basket.num_items_with_discount, 1)
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.total_excl_tax, D('9.00'))


    def test_apply_with_applicable_to_discounted_lines_on(self):
        basket = self._build_basket(item_quantity=1)
        offer = _build_offer_with_benefit('oscarbluelight.offer.benefits.BluelightPercentageDiscountBenefit', D('10.0'))
        offer.applicable_to_discounted_lines = True
        offer.save()

        self.assertEqual(basket.num_items_with_discount, 0)
        self.assertEqual(basket.num_items_without_discount, 1)
        self.assertEqual(basket.total_excl_tax, D('10.00'))

        result = offer.apply_benefit(basket)
        self.assertEqual(result.discount, D('1.00'))
        self.assertEqual(basket.num_items_with_discount, 1)
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.total_excl_tax, D('9.00'))

        result = offer.apply_benefit(basket)
        self.assertEqual(result.discount, D('1.00'))
        self.assertEqual(basket.num_items_with_discount, 1)
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.total_excl_tax, D('8.00'))



class BluelightAbsoluteDiscountBenefitTest(BaseTest):
    def test_apply_with_applicable_to_discounted_lines_off(self):
        basket = self._build_basket(item_quantity=1)
        offer = _build_offer_with_benefit('oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit', D('1.25'))
        offer.applicable_to_discounted_lines = False
        offer.save()

        self.assertEqual(basket.num_items_with_discount, 0)
        self.assertEqual(basket.num_items_without_discount, 1)
        self.assertEqual(basket.total_excl_tax, D('10.00'))

        result = offer.apply_benefit(basket)
        self.assertEqual(result.discount, D('1.25'))
        self.assertEqual(basket.num_items_with_discount, 1)
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.total_excl_tax, D('8.75'))

        result = offer.apply_benefit(basket)
        self.assertEqual(result.discount, D('0.00'))
        self.assertEqual(basket.num_items_with_discount, 1)
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.total_excl_tax, D('8.75'))


    def test_apply_with_applicable_to_discounted_lines_on(self):
        basket = self._build_basket(item_quantity=1)
        offer = _build_offer_with_benefit('oscarbluelight.offer.benefits.BluelightAbsoluteDiscountBenefit', D('1.25'))
        offer.applicable_to_discounted_lines = True
        offer.save()

        self.assertEqual(basket.num_items_with_discount, 0)
        self.assertEqual(basket.num_items_without_discount, 1)
        self.assertEqual(basket.total_excl_tax, D('10.00'))

        result = offer.apply_benefit(basket)
        self.assertEqual(result.discount, D('1.25'))
        self.assertEqual(basket.num_items_with_discount, 1)
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.total_excl_tax, D('8.75'))

        result = offer.apply_benefit(basket)
        self.assertEqual(result.discount, D('1.25'))
        self.assertEqual(basket.num_items_with_discount, 1)
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.total_excl_tax, D('7.50'))



class BluelightFixedPriceBenefitTest(BaseTest):
    def test_apply_with_compound_condition(self):
        basket = self._build_basket()

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
        condition.conjunction = CompoundCondition.OR
        condition.save()
        condition.subconditions = [cond_a, cond_b]
        condition.save()

        benefit = Benefit()
        benefit.proxy_class = 'oscarbluelight.offer.benefits.BluelightFixedPriceBenefit'
        benefit.value = 0
        benefit.range = all_products
        benefit.max_affected_items = 3
        benefit.save()

        offer = ConditionalOffer()
        offer.condition = condition
        offer.benefit = benefit
        offer.save()

        line = basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 0)
        self.assertEqual(line.quantity_without_discount, 5)

        discount = offer.apply_benefit(basket)

        line = basket.all_lines()[0]
        self.assertEqual(line.quantity_with_discount, 3)
        self.assertEqual(line.quantity_without_discount, 2)

        self.assertEqual(discount.discount, D('30.00'))
        self.assertEqual(basket.total_excl_tax_excl_discounts, D('50.00'))
        self.assertEqual(basket.total_excl_tax, D('20.00'))


    def test_apply_with_applicable_to_discounted_lines_off(self):
        basket = self._build_basket(item_quantity=1)
        offer = _build_offer_with_benefit('oscarbluelight.offer.benefits.BluelightFixedPriceBenefit', D('8.00'))
        offer.applicable_to_discounted_lines = False
        offer.save()

        self.assertEqual(basket.num_items_with_discount, 0)
        self.assertEqual(basket.num_items_without_discount, 1)
        self.assertEqual(basket.total_excl_tax, D('10.00'))

        result = offer.apply_benefit(basket)
        self.assertEqual(result.discount, D('2.00'))
        self.assertEqual(basket.num_items_with_discount, 1)
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.total_excl_tax, D('8.00'))

        result = offer.apply_benefit(basket)
        self.assertEqual(result.discount, D('0.00'))
        self.assertEqual(basket.num_items_with_discount, 1)
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.total_excl_tax, D('8.00'))


    def test_apply_with_applicable_to_discounted_lines_on(self):
        basket = self._build_basket(item_quantity=1)
        offer = _build_offer_with_benefit('oscarbluelight.offer.benefits.BluelightFixedPriceBenefit', D('8.00'))
        offer.applicable_to_discounted_lines = True
        offer.save()

        self.assertEqual(basket.num_items_with_discount, 0)
        self.assertEqual(basket.num_items_without_discount, 1)
        self.assertEqual(basket.total_excl_tax, D('10.00'))

        result = offer.apply_benefit(basket)
        self.assertEqual(result.discount, D('2.00'))
        self.assertEqual(basket.num_items_with_discount, 1)
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.total_excl_tax, D('8.00'))

        result = offer.apply_benefit(basket)
        self.assertEqual(result.discount, D('0.00'))
        self.assertEqual(basket.num_items_with_discount, 1)
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.total_excl_tax, D('8.00'))



class BluelightMultibuyDiscountBenefitTest(BaseTest):
    def test_apply_with_applicable_to_discounted_lines_off(self):
        basket = self._build_basket(item_quantity=1)
        offer = _build_offer_with_benefit('oscarbluelight.offer.benefits.BluelightMultibuyDiscountBenefit')
        offer.applicable_to_discounted_lines = False
        offer.save()

        self.assertEqual(basket.num_items_with_discount, 0)
        self.assertEqual(basket.num_items_without_discount, 1)
        self.assertEqual(basket.total_excl_tax, D('10.00'))

        result = offer.apply_benefit(basket)
        self.assertEqual(result.discount, D('10.00'))
        self.assertEqual(basket.num_items_with_discount, 1)
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.total_excl_tax, D('0.00'))

        result = offer.apply_benefit(basket)
        self.assertEqual(result.discount, D('0.00'))
        self.assertEqual(basket.num_items_with_discount, 1)
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.total_excl_tax, D('0.00'))


    def test_apply_with_applicable_to_discounted_lines_on(self):
        basket = self._build_basket(item_quantity=1)
        offer = _build_offer_with_benefit('oscarbluelight.offer.benefits.BluelightMultibuyDiscountBenefit')
        offer.applicable_to_discounted_lines = True
        offer.save()

        self.assertEqual(basket.num_items_with_discount, 0)
        self.assertEqual(basket.num_items_without_discount, 1)
        self.assertEqual(basket.total_excl_tax, D('10.00'))

        result = offer.apply_benefit(basket)
        self.assertEqual(result.discount, D('10.00'))
        self.assertEqual(basket.num_items_with_discount, 1)
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.total_excl_tax, D('0.00'))

        result = offer.apply_benefit(basket)
        self.assertEqual(result.discount, D('0.00'))
        self.assertEqual(basket.num_items_with_discount, 1)
        self.assertEqual(basket.num_items_without_discount, 0)
        self.assertEqual(basket.total_excl_tax, D('0.00'))
