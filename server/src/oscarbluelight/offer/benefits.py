from decimal import Decimal as D
from django.core import exceptions
from django.utils.translation import ugettext_lazy as _
from oscar.apps.offer import results, utils
from oscar.apps.offer.benefits import (
    PercentageDiscountBenefit,
    AbsoluteDiscountBenefit,
    FixedPriceBenefit,
    MultibuyDiscountBenefit,
    ShippingBenefit,
    ShippingAbsoluteDiscountBenefit,
    ShippingFixedPriceBenefit,
    ShippingPercentageDiscountBenefit,
)
from oscar.templatetags.currency_filters import currency



class BluelightPercentageDiscountBenefit(PercentageDiscountBenefit):
    """
    An offer benefit that gives a percentage discount
    """
    _description = _("%(value)s%% discount on %(range)s")

    class Meta:
        app_label = 'offer'
        proxy = True
        verbose_name = _("Percentage discount benefit")
        verbose_name_plural = _("Percentage discount benefits")


    @property
    def name(self):
        return self._description % {
            'value': self.value,
            'range': self.range.name if self.range else 'product range'}


    @property
    def description(self):
        return self._description % {
            'value': self.value,
            'range': utils.range_anchor(self.range) if self.range else 'product range'}


    def apply_cosmetic_discount(self, price_excl_tax):
        discount = (self.value / 100) * price_excl_tax
        return price_excl_tax - discount


    def _clean(self):
        if not self.range:
            raise exceptions.ValidationError(
                _("Percentage benefits require a product range"))
        if self.value > 100:
            raise exceptions.ValidationError(
                _("Percentage discount cannot be greater than 100"))


    def apply(self, basket, condition, offer, discount_percent=None, max_total_discount=None):
        self._clean()

        if discount_percent is None:
            discount_percent = self.value

        discount_amount_available = max_total_discount

        line_tuples = self.get_applicable_lines(offer, basket)
        discount_percent = min(discount_percent, D('100.0'))
        discount = D('0.00')
        affected_items = 0
        max_affected_items = self._effective_max_affected_items()
        affected_lines = []
        for price, line in line_tuples:
            if affected_items >= max_affected_items:
                break
            if discount_amount_available == 0:
                break

            quantity_affected = min(line.quantity_without_discount, max_affected_items - affected_items)
            line_discount = self.round(discount_percent / D('100.0') * price * int(quantity_affected))

            if discount_amount_available is not None:
                line_discount = min(line_discount, discount_amount_available)
                discount_amount_available -= line_discount

            line.discount(line_discount, quantity_affected, incl_tax=False, source_offer=offer)

            affected_lines.append((line, line_discount, quantity_affected))
            affected_items += quantity_affected
            discount += line_discount

        if discount > 0:
            condition.consume_items(offer, basket, affected_lines)
        return results.BasketDiscount(discount)




class BluelightAbsoluteDiscountBenefit(AbsoluteDiscountBenefit):
    """
    An offer benefit that gives an absolute discount
    """
    _description = _("%(value)s discount on %(range)s")

    class Meta:
        app_label = 'offer'
        proxy = True
        verbose_name = _("Absolute discount benefit")
        verbose_name_plural = _("Absolute discount benefits")


    @property
    def name(self):
        return self._description % {
            'value': currency(self.value),
            'range': self.range.name.lower() if self.range else 'product range'}


    @property
    def description(self):
        return self._description % {
            'value': currency(self.value),
            'range': utils.range_anchor(self.range) if self.range else 'product range'}


    def apply_cosmetic_discount(self, price_excl_tax):
        return price_excl_tax - self.value


    def _clean(self):
        if not self.range:
            raise exceptions.ValidationError(
                _("Fixed discount benefits require a product range"))
        if not self.value:
            raise exceptions.ValidationError(
                _("Fixed discount benefits require a value"))


    def apply(self, basket, condition, offer, discount_amount=None, max_total_discount=None):
        self._clean()

        if discount_amount is None:
            discount_amount = self.value

        # Fetch basket lines that are in the range and available to be used in
        # an offer.
        line_tuples = self.get_applicable_lines(offer, basket)

        # Determine which lines can have the discount applied to them
        max_affected_items = self._effective_max_affected_items()
        num_affected_items = 0
        affected_items_total = D('0.00')
        lines_to_discount = []
        for price, line in line_tuples:
            if num_affected_items >= max_affected_items:
                break
            qty = min(line.quantity_without_discount, max_affected_items - num_affected_items)
            lines_to_discount.append((line, price, qty))
            num_affected_items += qty
            affected_items_total += qty * price

        # Ensure we don't try to apply a discount larger than the total of the
        # matching items.
        discount = min(discount_amount, affected_items_total)
        if max_total_discount is not None:
            discount = min(discount, max_total_discount)

        if discount == 0:
            return results.ZERO_DISCOUNT

        # Apply discount equally amongst them
        affected_lines = []
        applied_discount = D('0.00')
        for i, (line, price, qty) in enumerate(lines_to_discount):
            if i == len(lines_to_discount) - 1:
                # If last line, then take the delta as the discount to ensure
                # the total discount is correct and doesn't mismatch due to
                # rounding.
                line_discount = discount - applied_discount
            else:
                # Calculate a weighted discount for the line
                line_discount = self.round(((price * qty) / affected_items_total) * discount)
            line.discount(line_discount, qty, incl_tax=False, source_offer=offer)
            affected_lines.append((line, line_discount, qty))
            applied_discount += line_discount

        condition.consume_items(offer, basket, affected_lines)

        return results.BasketDiscount(discount)



class BluelightFixedPriceBenefit(FixedPriceBenefit):
    """
    An offer benefit that gives the items in the range for a fixed price.

    Oscar's default FixedPriceBenefit is unintuitive. It ignores the benefit range and
    the max_affected_items and uses the products affected by the condition instead. This
    changes the behavior to more closely follow how other benefits work. It applied, it
    gives the basket items in the benefit range for a fixed price, not the basket items
    in the condition range. It also respects the max_affected_items setting.
    """
    _description = _("The products in the range are sold for %(amount)s")

    class Meta:
        app_label = 'offer'
        proxy = True
        verbose_name = _("Fixed price benefit")
        verbose_name_plural = _("Fixed price benefits")


    @property
    def name(self):
        return self._description % {
            'amount': currency(self.value)}


    def _clean(self):
        if not self.range:
            raise exceptions.ValidationError(
                _("Fixed price benefits require a product range."))


    def apply_cosmetic_discount(self, price_excl_tax):
        return self.value


    def apply(self, basket, condition, offer):
        self._clean()

        # Fetch basket lines that are in the range and available to be used in an offer.
        line_tuples = self.get_applicable_lines(offer, basket)
        if not line_tuples:
            return results.ZERO_DISCOUNT

        # Sort from most-expensive to least-expensive
        line_tuples = line_tuples[::-1]

        # Determine the lines to consume
        num_permitted = self._effective_max_affected_items()
        num_affected = 0
        value_affected = D('0.00')
        covered_lines = []
        for price, line in line_tuples:
            quantity_affected = min(line.quantity_without_discount, (num_permitted - num_affected))
            num_affected += quantity_affected
            value_affected += quantity_affected * price
            covered_lines.append((price, line, quantity_affected))
            if num_affected >= num_permitted:
                break
        discount = max(value_affected - self.value, D('0.00'))
        if not discount:
            return results.ZERO_DISCOUNT

        # Apply discount to the affected lines
        discount_applied = D('0.00')
        last_line = covered_lines[-1][1]
        for price, line, quantity in covered_lines:
            if line == last_line:
                # If last line, we just take the difference to ensure that
                # rounding doesn't lead to an off-by-one error
                line_discount = discount - discount_applied
            else:
                line_discount = self.round(
                    discount * (price * quantity) / value_affected)
            line.discount(line_discount, quantity, incl_tax=False, source_offer=offer)
            discount_applied += line_discount
        return results.BasketDiscount(discount)



class BluelightMultibuyDiscountBenefit(MultibuyDiscountBenefit):
    _description = _("Cheapest product from %(range)s is free")

    class Meta:
        app_label = 'offer'
        proxy = True
        verbose_name = _("Multibuy discount benefit")
        verbose_name_plural = _("Multibuy discount benefits")


    @property
    def name(self):
        return self._description % {
            'range': self.range.name.lower() if self.range else 'product range'}


    @property
    def description(self):
        return self._description % {
            'range': utils.range_anchor(self.range) if self.range else 'product range'}


    def _clean(self):
        if not self.range:
            raise exceptions.ValidationError(
                _("Multibuy benefits require a product range"))
        if self.value:
            raise exceptions.ValidationError(
                _("Multibuy benefits don't require a value"))
        if self.max_affected_items:
            raise exceptions.ValidationError(
                _("Multibuy benefits don't require a 'max affected items' "
                  "attribute"))


    def apply(self, basket, condition, offer):
        self._clean()

        line_tuples = self.get_applicable_lines(offer, basket)
        if not line_tuples:
            return results.ZERO_DISCOUNT

        # Cheapest line gives free product
        discount, line = line_tuples[0]
        line.discount(discount, 1, incl_tax=False, source_offer=offer)

        affected_lines = [(line, discount, 1)]
        condition.consume_items(offer, basket, affected_lines)

        return results.BasketDiscount(discount)



class BluelightShippingBenefit(ShippingBenefit):
    class Meta:
        app_label = 'offer'
        proxy = True



class BluelightShippingAbsoluteDiscountBenefit(ShippingAbsoluteDiscountBenefit):
    _description = _("%(amount)s off shipping cost")

    class Meta:
        app_label = 'offer'
        proxy = True
        verbose_name = _("Shipping absolute discount benefit")
        verbose_name_plural = _("Shipping absolute discount benefits")


    @property
    def name(self):
        return self._description % {
            'amount': currency(self.value)}


    def _clean(self):
        if not self.value:
            raise exceptions.ValidationError(
                _("A discount value is required"))
        if self.range:
            raise exceptions.ValidationError(
                _("No range should be selected as this benefit does not "
                  "apply to products"))
        if self.max_affected_items:
            raise exceptions.ValidationError(
                _("Shipping discounts don't require a 'max affected items' "
                  "attribute"))

    def apply(self, basket, condition, offer):
        self._clean()
        return super().apply(self, basket, condition, offer)



class BluelightShippingFixedPriceBenefit(ShippingFixedPriceBenefit):
    _description = _("Get shipping for %(amount)s")

    class Meta:
        app_label = 'offer'
        proxy = True
        verbose_name = _("Fixed price shipping benefit")
        verbose_name_plural = _("Fixed price shipping benefits")


    @property
    def name(self):
        return self._description % {
            'amount': currency(self.value)}


    def _clean(self):
        if self.range:
            raise exceptions.ValidationError(
                _("No range should be selected as this benefit does not "
                  "apply to products"))
        if self.max_affected_items:
            raise exceptions.ValidationError(
                _("Shipping discounts don't require a 'max affected items' "
                  "attribute"))

    def apply(self, basket, condition, offer):
        self._clean()
        return super().apply(self, basket, condition, offer)



class BluelightShippingPercentageDiscountBenefit(ShippingPercentageDiscountBenefit):
    _description = _("%(value)s%% off of shipping cost")

    class Meta:
        app_label = 'offer'
        proxy = True
        verbose_name = _("Shipping percentage discount benefit")
        verbose_name_plural = _("Shipping percentage discount benefits")


    @property
    def name(self):
        return self._description % {
            'value': self.value}


    def _clean(self):
        if self.value > 100:
            raise exceptions.ValidationError(
                _("Percentage discount cannot be greater than 100"))
        if self.range:
            raise exceptions.ValidationError(
                _("No range should be selected as this benefit does not "
                  "apply to products"))
        if self.max_affected_items:
            raise exceptions.ValidationError(
                _("Shipping discounts don't require a 'max affected items' "
                  "attribute"))

    def apply(self, basket, condition, offer):
        self._clean()
        return super().apply(self, basket, condition, offer)



__all__ = [
    'BluelightAbsoluteDiscountBenefit',
    'BluelightFixedPriceBenefit',
    'BluelightMultibuyDiscountBenefit',
    'BluelightPercentageDiscountBenefit',
    'BluelightShippingAbsoluteDiscountBenefit',
    'BluelightShippingBenefit',
    'BluelightShippingFixedPriceBenefit',
    'BluelightShippingPercentageDiscountBenefit',
]
