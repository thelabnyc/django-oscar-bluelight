from decimal import Decimal as D
from django.utils.translation import ugettext_lazy as _
from oscar.apps.offer import results
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


class BluelightPercentageDiscountBenefit(PercentageDiscountBenefit):
    """
    An offer benefit that gives a percentage discount
    """
    class Meta:
        app_label = 'offer'
        proxy = True
        verbose_name = _("Percentage discount benefit")
        verbose_name_plural = _("Percentage discount benefits")


class BluelightAbsoluteDiscountBenefit(AbsoluteDiscountBenefit):
    """
    An offer benefit that gives an absolute discount
    """
    class Meta:
        app_label = 'offer'
        proxy = True
        verbose_name = _("Absolute discount benefit")
        verbose_name_plural = _("Absolute discount benefits")


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

    def apply(self, basket, condition, offer):
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
            line.discount(line_discount, quantity, incl_tax=False)
            discount_applied += line_discount
        return results.BasketDiscount(discount)


class BluelightMultibuyDiscountBenefit(MultibuyDiscountBenefit):
    class Meta:
        app_label = 'offer'
        proxy = True
        verbose_name = _("Multibuy discount benefit")
        verbose_name_plural = _("Multibuy discount benefits")


class BluelightShippingBenefit(ShippingBenefit):
    class Meta:
        app_label = 'offer'
        proxy = True


class BluelightShippingAbsoluteDiscountBenefit(ShippingAbsoluteDiscountBenefit):
    class Meta:
        app_label = 'offer'
        proxy = True
        verbose_name = _("Shipping absolute discount benefit")
        verbose_name_plural = _("Shipping absolute discount benefits")


class BluelightShippingFixedPriceBenefit(ShippingFixedPriceBenefit):
    class Meta:
        app_label = 'offer'
        proxy = True
        verbose_name = _("Fixed price shipping benefit")
        verbose_name_plural = _("Fixed price shipping benefits")


class BluelightShippingPercentageDiscountBenefit(ShippingPercentageDiscountBenefit):
    class Meta:
        app_label = 'offer'
        proxy = True
        verbose_name = _("Shipping percentage discount benefit")
        verbose_name_plural = _("Shipping percentage discount benefits")


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
