from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import TYPE_CHECKING, Any
import copy

from django.core import exceptions
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from oscar.apps.offer import utils
from oscar.apps.offer.benefits import (
    AbsoluteDiscountBenefit,
    FixedPriceBenefit,
    MultibuyDiscountBenefit,
    PercentageDiscountBenefit,
    ShippingAbsoluteDiscountBenefit,
    ShippingBenefit,
    ShippingFixedPriceBenefit,
    ShippingPercentageDiscountBenefit,
)
from oscar.templatetags.currency_filters import currency

from oscarbluelight.offer.models import Benefit

from .constants import Conjunction
from .results import (
    ZERO_DISCOUNT,
    BasketDiscount,
    HiddenPostOrderAction,
    PostOrderAction,
    ShippingDiscount,
)
from .utils import get_conjoiner, human_readable_conjoin

if TYPE_CHECKING:
    from django_stubs_ext import StrOrPromise
    from oscar.apps.order.models import Order

    from ..mixins import BluelightBasketMixin as Basket
    from .models import Condition, ConditionalOffer
    from .types import AffectedLines

    ConsumeItems = Callable[[ConditionalOffer, Basket, AffectedLines], AffectedLines]


class BluelightPercentageDiscountBenefit(PercentageDiscountBenefit):
    """
    An offer benefit that gives a percentage discount
    """

    _description = _("%(value)s%% discount on %(range)s, %(max_affected_items)s")

    class Meta:
        app_label = "offer"
        proxy = True
        verbose_name = _("Percentage discount benefit")
        verbose_name_plural = _("Percentage discount benefits")

    @property
    def name(self) -> StrOrPromise:
        return self._append_max_discount_to_text(
            self._description
            % {
                "value": self.value,
                "range": self.range.name if self.range else _("product range"),
                "max_affected_items": (
                    (
                        ngettext(
                            "maximum %s item",
                            "maximum %s items",
                            self.max_affected_items,
                        )
                        % self.max_affected_items
                    )
                    if self.max_affected_items
                    else _("no maximum")
                ),
            }
        )

    @property
    def description(self) -> StrOrPromise:
        return self._append_max_discount_to_text(
            self._description
            % {
                "value": self.value,
                "range": (
                    utils.range_anchor(self.range) if self.range else _("product range")
                ),
                "max_affected_items": (
                    (
                        ngettext(
                            "maximum %s item",
                            "maximum %s items",
                            self.max_affected_items,
                        )
                        % self.max_affected_items
                    )
                    if self.max_affected_items
                    else _("no maximum")
                ),
            }
        )

    def _clean(self) -> None:
        if not self.range:
            raise exceptions.ValidationError(
                _("Percentage benefits require a product range")
            )
        if not self.value or self.value <= 0 or self.value > 100:
            raise exceptions.ValidationError(
                _("Percentage discount requires a value between 0 and 100")
            )

    def apply(  # type:ignore[override]
        self,
        basket: Basket,
        condition: Condition,
        offer: ConditionalOffer,
        max_total_discount: Decimal | None = None,
        consume_items: ConsumeItems | None = None,
    ) -> BasketDiscount:
        self._clean()

        discount_percent = self.value
        discount_amount_available = self._get_max_discount_amount(max_total_discount)

        line_tuples = self.get_applicable_lines(offer, basket)
        discount_percent = min(discount_percent, Decimal("100.0"))
        discount = Decimal("0.00")
        affected_items = 0
        max_affected_items = self._effective_max_affected_items()
        affected_lines: AffectedLines = []
        for price, line in line_tuples:
            if affected_items >= max_affected_items:
                break
            if discount_amount_available == 0:
                break

            quantity_affected = min(
                line.quantity_without_discount, max_affected_items - affected_items
            )
            if quantity_affected <= 0:
                continue

            line_discount = self.round(
                discount_percent / Decimal("100.0") * price * int(quantity_affected),
                currency=basket.currency,
            )

            if discount_amount_available is not None:
                line_discount = min(line_discount, discount_amount_available)
                discount_amount_available -= line_discount

            if line_discount > 0:
                line.discount(
                    line_discount, quantity_affected, incl_tax=False, offer=offer
                )
                affected_lines.append((line, line_discount, quantity_affected))
                affected_items += quantity_affected
                discount += line_discount

        if discount > 0:
            if consume_items:
                consume_items(offer, basket, affected_lines)
            else:
                condition.consume_items(offer, basket, affected_lines)
        return BasketDiscount(discount)


class BluelightAbsoluteDiscountBenefit(AbsoluteDiscountBenefit):
    """
    An offer benefit that gives an absolute discount
    """

    _description = _("%(value)s discount on %(range)s, %(max_affected_items)s")

    class Meta:
        app_label = "offer"
        proxy = True
        verbose_name = _("Absolute discount benefit")
        verbose_name_plural = _("Absolute discount benefits")

    @property
    def name(self) -> StrOrPromise:
        return self._append_max_discount_to_text(
            self._description
            % {
                "value": currency(self.value),
                "range": self.range.name.lower() if self.range else _("product range"),
                "max_affected_items": (
                    (
                        ngettext(
                            "maximum %s item",
                            "maximum %s items",
                            self.max_affected_items,
                        )
                        % self.max_affected_items
                    )
                    if self.max_affected_items
                    else _("no maximum")
                ),
            }
        )

    @property
    def description(self) -> StrOrPromise:
        return self._append_max_discount_to_text(
            self._description
            % {
                "value": currency(self.value),
                "range": (
                    utils.range_anchor(self.range) if self.range else _("product range")
                ),
                "max_affected_items": (
                    (
                        ngettext(
                            "maximum %s item",
                            "maximum %s items",
                            self.max_affected_items,
                        )
                        % self.max_affected_items
                    )
                    if self.max_affected_items
                    else _("no maximum")
                ),
            }
        )

    def _clean(self) -> None:
        if not self.range:
            raise exceptions.ValidationError(
                _("Fixed discount benefits require a product range")
            )
        if not self.value:
            raise exceptions.ValidationError(
                _("Fixed discount benefits require a value")
            )

    def apply(  # type:ignore[override]
        self,
        basket: Basket,
        condition: Condition,
        offer: ConditionalOffer,
        max_total_discount: Decimal | None = None,
        consume_items: ConsumeItems | None = None,
    ) -> BasketDiscount:
        self._clean()

        discount_amount = self.value

        # Fetch basket lines that are in the range and available to be used in
        # an offer.
        line_tuples = self.get_applicable_lines(offer, basket)

        # Determine which lines can have the discount applied to them
        max_affected_items = self._effective_max_affected_items()
        num_affected_items = 0
        affected_items_total = Decimal("0.00")
        lines_to_discount = []
        for price, line in line_tuples:
            if num_affected_items >= max_affected_items:
                break
            qty = min(
                line.quantity_without_discount, max_affected_items - num_affected_items
            )
            lines_to_discount.append((line, price, qty))
            num_affected_items += qty
            affected_items_total += qty * price

        # Ensure we don't try to apply a discount larger than the total of the
        # matching items.
        discount = min(discount_amount, affected_items_total)
        discount_amount_available = self._get_max_discount_amount(max_total_discount)
        if discount_amount_available is not None:
            discount = min(discount, discount_amount_available)

        if discount == 0:
            return ZERO_DISCOUNT

        # Apply discount equally amongst them
        affected_lines: AffectedLines = []
        applied_discount = Decimal("0.00")
        for i, (line, price, qty) in enumerate(lines_to_discount):
            if i == len(lines_to_discount) - 1:
                # If last line, then take the delta as the discount to ensure
                # the total discount is correct and doesn't mismatch due to
                # rounding.
                line_discount = discount - applied_discount
            else:
                # Calculate a weighted discount for the line
                line_discount = self.round(
                    ((price * qty) / affected_items_total) * discount,
                    currency=basket.currency,
                )
            if line_discount > 0:
                line.discount(line_discount, qty, incl_tax=False, offer=offer)
                affected_lines.append((line, line_discount, qty))
                applied_discount += line_discount

        if consume_items:
            consume_items(offer, basket, affected_lines)
        else:
            condition.consume_items(offer, basket, affected_lines)

        return BasketDiscount(discount)


class BluelightFixedPriceBenefit(FixedPriceBenefit):
    """
    An offer benefit that gives the items in the range for a fixed price.

    Oscar's default FixedPriceBenefit is unintuitive. It ignores the benefit range and
    the max_affected_items and uses the products affected by the condition instead. This
    changes the behavior to more closely follow how other benefits work. It applied, it
    gives the basket items in the benefit range for a fixed price, not the basket items
    in the condition range. It also respects the max_affected_items setting.
    """

    _description = _(
        "The products in %(range)s are sold for %(amount)s, %(max_affected_items)s"
    )

    class Meta:
        app_label = "offer"
        proxy = True
        verbose_name = _("Fixed price benefit")
        verbose_name_plural = _("Fixed price benefits")

    @property
    def name(self) -> StrOrPromise:
        return self._append_max_discount_to_text(
            self._description
            % {
                "range": self.range,
                "amount": currency(self.value),
                "max_affected_items": (
                    (
                        ngettext(
                            "maximum %s item",
                            "maximum %s items",
                            self.max_affected_items,
                        )
                        % self.max_affected_items
                    )
                    if self.max_affected_items
                    else _("no maximum")
                ),
            }
        )

    def _clean(self) -> None:
        if not self.range:
            raise exceptions.ValidationError(
                _("Fixed price benefits require a product range.")
            )

    def apply(  # type:ignore[override]
        self,
        basket: Basket,
        condition: Condition,
        offer: ConditionalOffer,
        max_total_discount: Decimal | None = None,
        consume_items: ConsumeItems | None = None,
    ) -> BasketDiscount:
        self._clean()

        # Fetch basket lines that are in the range and available to be used in an offer.
        line_tuples = self.get_applicable_lines(offer, basket)
        if not line_tuples:
            return ZERO_DISCOUNT

        # Sort from most-expensive to least-expensive
        line_tuples = line_tuples[::-1]

        # Determine the lines to consume
        num_permitted = self._effective_max_affected_items()
        num_affected = 0
        value_affected = Decimal("0.00")
        covered_lines = []
        for price, line in line_tuples:
            quantity_affected = min(
                line.quantity_without_discount, (num_permitted - num_affected)
            )
            num_affected += quantity_affected
            value_affected += quantity_affected * price
            covered_lines.append((price, line, quantity_affected))
            if num_affected >= num_permitted:
                break

        discount = max(value_affected - self.value, Decimal("0.00"))
        discount_amount_available = self._get_max_discount_amount(max_total_discount)
        discount = min(discount, discount_amount_available)
        if not discount:
            return ZERO_DISCOUNT

        # Apply discount to the affected lines
        discount_applied = Decimal("0.00")
        last_line = covered_lines[-1][1]
        for price, line, quantity in covered_lines:
            if line == last_line:
                # If last line, we just take the difference to ensure that
                # rounding doesn't lead to an off-by-one error
                line_discount = discount - discount_applied
            else:
                line_discount = self.round(
                    discount * (price * quantity) / value_affected,
                    currency=basket.currency,
                )
            if line_discount > 0:
                line.discount(line_discount, quantity, incl_tax=False, offer=offer)
                discount_applied += line_discount
        return BasketDiscount(discount)


class BluelightFixedPricePerItemBenefit(FixedPriceBenefit):
    """
    An offer benefit that gives the items in the range for a fixed price.

    Oscar's default FixedPriceBenefit is unintuitive. It ignores the benefit range and
    the max_affected_items and uses the products affected by the condition instead. This
    changes the behavior to more closely follow how other benefits work. It applied, it
    gives the basket items in the benefit range for a fixed price, not the basket items
    in the condition range. It also respects the max_affected_items setting.
    """

    _description = _(
        "The products in %(range)s are sold for %(amount)s each; %(max_affected_items)s"
    )

    class Meta:
        app_label = "offer"
        proxy = True
        verbose_name = _("Fixed price per item benefit")
        verbose_name_plural = _("Fixed price per item benefits")

    @property
    def name(self) -> StrOrPromise:
        return self._append_max_discount_to_text(
            self._description
            % {
                "range": self.range,
                "amount": currency(self.value),
                "max_affected_items": (
                    (
                        ngettext(
                            "maximum %s item",
                            "maximum %s items",
                            self.max_affected_items,
                        )
                        % self.max_affected_items
                    )
                    if self.max_affected_items
                    else _("no maximum")
                ),
            }
        )

    def _clean(self) -> None:
        if not self.range:
            raise exceptions.ValidationError(
                _("Fixed price per item benefits require a product range.")
            )

    def apply(  # type:ignore[override]
        self,
        basket: Basket,
        condition: Condition,
        offer: ConditionalOffer,
        max_total_discount: Decimal | None = None,
        consume_items: ConsumeItems | None = None,
    ) -> BasketDiscount:
        self._clean()

        # Fetch basket lines that are in the range and available to be used in an offer.
        line_tuples = self.get_applicable_lines(offer, basket)
        if not line_tuples:
            return ZERO_DISCOUNT

        # Sort from most-expensive to least-expensive
        line_tuples = line_tuples[::-1]

        # Determine the lines to consume
        num_permitted = self._effective_max_affected_items()
        num_affected = 0
        covered_lines = []
        for price, line in line_tuples:
            if price <= self.value:
                continue
            quantity_affected = min(
                line.quantity_without_discount, (num_permitted - num_affected)
            )
            if quantity_affected <= 0:
                continue
            num_affected += quantity_affected
            covered_lines.append((price, line, quantity_affected))
            if num_affected >= num_permitted:
                break
        if len(covered_lines) <= 0:
            return ZERO_DISCOUNT

        # Apply discount to the affected lines
        discount_amount_available = self._get_max_discount_amount(max_total_discount)
        discount_applied = Decimal("0.00")
        for price, line, quantity in covered_lines:
            line_discount = self.round(
                ((price - self.value) * quantity),
                currency=basket.currency,
            )
            line_discount = max(
                min(line_discount, (discount_amount_available - discount_applied)),
                Decimal("0.00"),
            )
            if line_discount > 0:
                line.discount(line_discount, quantity, incl_tax=False, offer=offer)
                discount_applied += line_discount

        return BasketDiscount(discount_applied)


class BluelightMultibuyDiscountBenefit(MultibuyDiscountBenefit):
    _description = _("Second most expensive product from %(range)s is free")

    class Meta:
        app_label = "offer"
        proxy = True
        verbose_name = _("Multibuy discount benefit")
        verbose_name_plural = _("Multibuy discount benefits")

    @property
    def name(self) -> StrOrPromise:
        return self._append_max_discount_to_text(
            self._description
            % {
                "range": self.range.name.lower() if self.range else _("product range"),
            }
        )

    @property
    def description(self) -> StrOrPromise:
        return self._append_max_discount_to_text(
            self._description
            % {
                "range": (
                    utils.range_anchor(self.range) if self.range else _("product range")
                ),
            }
        )

    def _clean(self) -> None:
        if not self.range:
            raise exceptions.ValidationError(
                _("Multibuy benefits require a product range")
            )
        if self.value:
            raise exceptions.ValidationError(
                _("Multibuy benefits don't require a value")
            )
        if self.max_affected_items:
            raise exceptions.ValidationError(
                _("Multibuy benefits don't require a 'max affected items' attribute")
            )

    def apply(  # type:ignore[override]
        self,
        basket: Basket,
        condition: Condition,
        offer: ConditionalOffer,
        max_total_discount: Decimal | None = None,
        consume_items: ConsumeItems | None = None,
    ) -> BasketDiscount:
        self._clean()

        line_tuples = self.get_applicable_lines(offer, basket)
        if not line_tuples:
            return ZERO_DISCOUNT

        # Goal is to give the second most expensive line for free
        # We check for quantity_without_discount > 1 instead of quantity_without_discount > 0 because
        # this is designed to be used on buy-one-get-one offers.
        #
        # E.g. The following rules shall be observed:
        #
        # 1. If two products in cart, highest product consumer pays for and the
        #       lowest price item is given for free
        # 2. If three products in cart, highest product consumer pays for, second
        #       highest should be free, third the consumer should pay for
        # 3. If four products are in the cart, consumer should pay full price for
        #       the highest price, then the second highest item should be free.
        #       Then the third highest consumer pays for, then the fourth item
        #       would be free.

        discount, line = None, None
        _more_expensive_items_without_discount = 0
        for _discount, _line in reversed(line_tuples):
            _more_expensive_items_without_discount += _line.quantity_without_discount
            if _more_expensive_items_without_discount > 1:
                discount, line = _discount, _line
                break

        # This must be a single line basket; use the cheapest line as a fallback.
        if not line:
            discount, line = line_tuples[0]

        # Make sure we can actually discount this line
        if line.quantity_without_discount <= 0:
            return ZERO_DISCOUNT

        discount_amount_available = self._get_max_discount_amount(max_total_discount)
        discount = min(discount, discount_amount_available)

        if discount > 0:
            line.discount(discount, 1, incl_tax=False, offer=offer)

            affected_lines: AffectedLines = [(line, discount, 1)]
            if consume_items:
                consume_items(offer, basket, affected_lines)
            else:
                condition.consume_items(offer, basket, affected_lines)

        return BasketDiscount(discount)


class BluelightShippingBenefit(ShippingBenefit):
    class Meta:
        app_label = "offer"
        proxy = True


class BluelightShippingAbsoluteDiscountBenefit(ShippingAbsoluteDiscountBenefit):
    _description = _("%(amount)s off shipping cost")

    class Meta:
        app_label = "offer"
        proxy = True
        verbose_name = _("Shipping absolute discount benefit")
        verbose_name_plural = _("Shipping absolute discount benefits")

    @property
    def name(self) -> StrOrPromise:
        return self._append_max_discount_to_text(
            self._description
            % {
                "amount": currency(self.value),
            }
        )

    def _clean(self) -> None:
        if not self.value:
            raise exceptions.ValidationError(_("A discount value is required"))
        if self.range:
            raise exceptions.ValidationError(
                _(
                    "No range should be selected as this benefit does not apply to products"
                )
            )
        if self.max_affected_items:
            raise exceptions.ValidationError(
                _("Shipping discounts don't require a 'max affected items' attribute")
            )

    def apply(  # type:ignore[override]
        self,
        basket: Basket,
        condition: Condition,
        offer: ConditionalOffer,
        max_total_discount: Decimal | None = None,
        consume_items: ConsumeItems | None = None,
    ) -> ShippingDiscount:
        self._clean()
        return super().apply(basket, condition, offer)


class BluelightShippingFixedPriceBenefit(ShippingFixedPriceBenefit):
    _description = _("Get shipping for %(amount)s")

    class Meta:
        app_label = "offer"
        proxy = True
        verbose_name = _("Fixed price shipping benefit")
        verbose_name_plural = _("Fixed price shipping benefits")

    @property
    def name(self) -> StrOrPromise:
        return self._append_max_discount_to_text(
            self._description
            % {
                "amount": currency(self.value),
            }
        )

    def _clean(self) -> None:
        if self.range:
            raise exceptions.ValidationError(
                _(
                    "No range should be selected as this benefit does not apply to products"
                )
            )
        if self.max_affected_items:
            raise exceptions.ValidationError(
                _("Shipping discounts don't require a 'max affected items' attribute")
            )

    def apply(  # type:ignore[override]
        self,
        basket: Basket,
        condition: Condition,
        offer: ConditionalOffer,
        max_total_discount: Decimal | None = None,
        consume_items: ConsumeItems | None = None,
    ) -> ShippingDiscount:
        self._clean()
        return super().apply(basket, condition, offer)


class BluelightShippingPercentageDiscountBenefit(ShippingPercentageDiscountBenefit):
    _description = _("%(value)s%% off of shipping cost")

    class Meta:
        app_label = "offer"
        proxy = True
        verbose_name = _("Shipping percentage discount benefit")
        verbose_name_plural = _("Shipping percentage discount benefits")

    @property
    def name(self) -> StrOrPromise:
        return self._append_max_discount_to_text(
            self._description
            % {
                "value": self.value,
            }
        )

    def _clean(self) -> None:
        if self.value > 100:
            raise exceptions.ValidationError(
                _("Percentage discount cannot be greater than 100")
            )
        if self.range:
            raise exceptions.ValidationError(
                _(
                    "No range should be selected as this benefit does not apply to products"
                )
            )
        if self.max_affected_items:
            raise exceptions.ValidationError(
                _("Shipping discounts don't require a 'max affected items' attribute")
            )

    def apply(  # type:ignore[override]
        self,
        basket: Basket,
        condition: Condition,
        offer: ConditionalOffer,
        max_total_discount: Decimal | None = None,
        consume_items: ConsumeItems | None = None,
    ) -> ShippingDiscount:
        self._clean()
        return super().apply(basket, condition, offer)


class CompoundBenefit(Benefit):
    conjunction = models.CharField(
        _("Sub-Benefit conjunction type"),
        choices=Conjunction.TYPE_CHOICES,
        default=Conjunction.AND,
        max_length=10,
        help_text=_(
            "Select the conjunction which will be used to logically join the sub-benefits "
            "together. An AND conjunction applies all sub-benefits. An OR conjunction "
            "applies the first benefit which results in a non-zero discount (benefits "
            "are applied in order of their value, descending)."
        ),
    )
    subbenefits = models.ManyToManyField(
        "offer.Benefit",
        related_name="parent_benefits",
        verbose_name=_("Sub-Benefits"),
        help_text=_("Select the benefits that this compound-benefit will apply."),
    )

    class Meta:
        app_label = "offer"
        verbose_name = _("Compound benefit")
        verbose_name_plural = _("Compound benefits")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.proxy_class = "{}.{}".format(
            CompoundBenefit.__module__,
            CompoundBenefit.__name__,
        )

    @property
    def children(self) -> list[Benefit]:
        if self.pk is None:
            return []
        chil = [
            c.proxy()
            for c in self.subbenefits.order_by("-value", "id").all()
            if c.id != self.id
        ]
        return chil

    @property
    def name(self) -> StrOrPromise:
        names = (c.name for c in self.children)
        name = human_readable_conjoin(self.conjunction, names, _("Empty Benefit"))
        return self._append_max_discount_to_text(name)

    @property
    def description(self) -> StrOrPromise:
        descrs = (c.description for c in self.children)
        descr = human_readable_conjoin(self.conjunction, descrs, _("Empty Benefit"))
        return self._append_max_discount_to_text(descr)

    def apply(
        self,
        basket: Basket,
        condition: Condition,
        offer: ConditionalOffer,
        max_total_discount: Decimal | None = None,
        consume_items: ConsumeItems | None = None,
    ) -> BasketDiscount:
        combined_result: BasketDiscount | None = None
        affected_lines: AffectedLines = []

        def _consume_items(
            _offer: ConditionalOffer, _basket: Basket, _affected_lines: AffectedLines
        ) -> None:
            for line in _affected_lines:
                affected_lines.append(line)

        discount_amount_available = self._get_max_discount_amount(max_total_discount)

        for child in self.children:
            result = child.apply(  # type:ignore[call-arg]
                basket,
                condition,
                offer,
                max_total_discount=max(discount_amount_available, Decimal("0.00")),
                consume_items=_consume_items,
            )
            if isinstance(result, HiddenPostOrderAction):
                # Explicitly ignore HiddenPostOrderAction so that they're the
                # one exception to the to "can't combine differing types rule".
                pass
            elif combined_result is None:
                combined_result = copy.deepcopy(result)
                discount_amount_available -= result.discount
            elif combined_result.affects == result.affects:  # type:ignore[has-type]
                combined_result.discount += result.discount
                discount_amount_available -= result.discount
            else:
                raise ValueError(_("Can not combine offer benefits of differing types"))

            # If this is an OR benefit AND this child-benefit applied a non-zero
            # discount, exit the loop.
            if self.conjunction == Conjunction.OR and result.discount > 0:
                break

        if combined_result and combined_result.discount > 0:
            if consume_items:
                consume_items(offer, basket, affected_lines)
            else:
                condition.consume_items(offer, basket, affected_lines)

        return combined_result or ZERO_DISCOUNT

    def apply_deferred(
        self,
        basket: Basket,
        order: Order,
        application: Any,
    ) -> PostOrderAction | None:
        results = []
        for child in self.children:
            result = child.apply_deferred(basket, order, application)
            if result is not None:
                # `result` should already be a string, but cast to a str() just
                # in-case a benefit is written incorrectly.
                results.append(str(result))
        if len(results) <= 0:
            return None
        descr = get_conjoiner(self.conjunction).join(results)
        return PostOrderAction(descr)

    def clean(self) -> None:
        errors = []
        if self.value:
            errors.append(_("Compound benefit should not have a value"))
        if self.range:
            errors.append(_("Compound benefit should not have a range"))
        if self.max_affected_items:
            errors.append(
                _("Compound benefit should not have a max affected items limit")
            )
        if errors:
            raise exceptions.ValidationError(errors)

    def shipping_discount(
        self, charge: Decimal, currency: str | None = None
    ) -> Decimal:
        discount = Decimal("0.00")
        for child in self.children:
            discount += child.shipping_discount(charge - discount, currency=currency)
        return discount


__all__ = [
    "BluelightAbsoluteDiscountBenefit",
    "BluelightFixedPriceBenefit",
    "BluelightFixedPricePerItemBenefit",
    "BluelightMultibuyDiscountBenefit",
    "BluelightPercentageDiscountBenefit",
    "BluelightShippingAbsoluteDiscountBenefit",
    "BluelightShippingBenefit",
    "BluelightShippingFixedPriceBenefit",
    "BluelightShippingPercentageDiscountBenefit",
    "CompoundBenefit",
]
