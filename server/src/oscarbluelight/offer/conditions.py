from __future__ import annotations

from decimal import ROUND_UP, Decimal
from typing import TYPE_CHECKING, Any, Literal

from django.core import exceptions
from django.db import models
from django.utils.translation import gettext_lazy as _
from oscar.apps.offer import utils
from oscar.apps.offer.conditions import (
    CountCondition,
    CoverageCondition,
    ValueCondition,
)
from oscar.templatetags.currency_filters import currency

from oscarbluelight.offer.models import Condition

from . import upsells
from .constants import Conjunction
from .utils import human_readable_conjoin

if TYPE_CHECKING:
    from django_stubs_ext import StrOrPromise

    from ..mixins import BluelightBasketLineMixin as Line
    from ..mixins import BluelightBasketMixin as Basket
    from .models import ConditionalOffer
    from .types import AffectedLines


def _default_clean(self: Condition) -> None:
    if not self.range:
        raise exceptions.ValidationError(_("Selected condition type requires a range."))
    if not self.value:
        raise exceptions.ValidationError(_("Selected condition type required a value."))


class BluelightCountCondition(CountCondition):
    _description = _("Basket includes %(count)d item(s) from %(range)s")

    class Meta:
        app_label = "offer"
        proxy = True
        verbose_name = _("Count condition")
        verbose_name_plural = _("Count conditions")

    @property
    def name(self) -> StrOrPromise:
        return self._description % {
            "count": self.value,
            "range": str(self.range).lower() if self.range else _("product range"),
        }

    @property
    def description(self) -> StrOrPromise:
        return self._description % {
            "count": self.value,
            "range": (
                utils.range_anchor(self.range) if self.range else _("product range")
            ),
        }

    def _clean(self) -> None:
        return _default_clean(self)

    def _get_num_matches(self, basket: Basket, offer: ConditionalOffer) -> int:
        if hasattr(self, "_num_matches"):
            return getattr(self, "_num_matches")
        num_matches = 0
        for line in basket.all_lines():
            if self.can_apply_condition(line):
                num_matches += line.quantity_without_offer_discount(offer)
        self._num_matches = num_matches
        return num_matches

    def get_upsell_details(
        self,
        offer: ConditionalOffer,
        basket: Basket,
    ) -> upsells.QuantityUpsell | None:
        num_matches = self._get_num_matches(basket, offer)
        delta = self.value - num_matches
        if delta > 0:
            return upsells.QuantityUpsell(
                offer=offer,
                basket=basket,
                product_range=self.range,
                delta=delta,
            )
        return None

    def consume_items(
        self,
        offer: ConditionalOffer,
        basket: Basket,
        affected_lines: AffectedLines,
    ) -> AffectedLines:
        """
        Same as CountCondition.consume_items, except that it returns a list of consumed items. This
        is needed for CompoundCondition to be able to correctly consume items.
        """
        applicable_lines = self.get_applicable_lines(
            offer, basket, most_expensive_first=True
        )
        applicable_line_ids = {line.pk for __, line in applicable_lines}

        num_consumed = 0
        affected_lines = list(affected_lines)
        for line, __, quantity in affected_lines:
            if line.pk in applicable_line_ids:
                num_consumed += quantity

        to_consume = max(0, self.value - num_consumed)
        if to_consume == 0:
            return affected_lines

        for __, line in applicable_lines:
            quantity_to_consume = min(line.quantity_without_discount, to_consume)
            line.consume(quantity_to_consume, offer=offer)
            affected_lines.append((line, Decimal("0.00"), quantity_to_consume))
            to_consume -= quantity_to_consume
            if to_consume == 0:
                break
        return affected_lines


class BluelightCoverageCondition(CoverageCondition):
    _description = _("Basket includes %(count)d distinct item(s) from %(range)s")

    class Meta:
        app_label = "offer"
        proxy = True
        verbose_name = _("Coverage Condition")
        verbose_name_plural = _("Coverage Conditions")

    @property
    def name(self) -> StrOrPromise:
        return self._description % {
            "count": self.value,
            "range": str(self.range).lower() if self.range else _("product range"),
        }

    @property
    def description(self) -> StrOrPromise:
        return self._description % {
            "count": self.value,
            "range": (
                utils.range_anchor(self.range) if self.range else _("product range")
            ),
        }

    def _get_num_covered_products(self, basket: Basket, offer: ConditionalOffer) -> int:
        covered_ids = set()
        for line in basket.all_lines():
            product = line.product
            if self.can_apply_condition(line) and line.is_available_for_offer_discount(
                offer
            ):
                covered_ids.add(product.pk)
        return len(covered_ids)

    def get_upsell_details(
        self, offer: ConditionalOffer, basket: Basket
    ) -> upsells.CoverageUpsell | None:
        num_matches = self._get_num_covered_products(basket, offer)
        delta = self.value - num_matches
        if delta > 0:
            return upsells.CoverageUpsell(
                offer=offer,
                basket=basket,
                product_range=self.range,
                delta=delta,
            )
        return None

    def _clean(self) -> None:
        return _default_clean(self)

    def consume_items(
        self,
        offer: ConditionalOffer,
        basket: Basket,
        affected_lines: AffectedLines,
    ) -> AffectedLines:
        """
        Same as CoverageCondition.consume_items, except that it returns a list of consumed items. This
        is needed for CompoundCondition to be able to correctly consume items.
        """
        applicable_lines = self.get_applicable_lines(
            offer, basket, most_expensive_first=True
        )
        applicable_line_ids = {line.pk for __, line in applicable_lines}

        consumed_products = []
        affected_lines = list(affected_lines)
        for line, __, quantity in affected_lines:
            if line.pk in applicable_line_ids:
                consumed_products.append(line.product)

        to_consume = max(0, self.value - len(consumed_products))
        if to_consume == 0:
            return affected_lines

        for line in basket.all_lines():
            product = line.product
            if not self.can_apply_condition(line):
                continue
            if product in consumed_products:
                continue
            if not line.is_available_for_offer_discount(offer):
                continue
            # Only consume a quantity of 1 from each line
            line.consume(1, offer=offer)
            affected_lines.append((line, Decimal("0.00"), 1))
            consumed_products.append(product)
            to_consume -= 1
            if to_consume == 0:
                break
        return affected_lines


class BluelightValueCondition(ValueCondition):
    _description = _("Basket includes %(amount)s (%(tax)s) from %(range)s")
    _tax_inclusive = False

    class Meta:
        app_label = "offer"
        proxy = True
        verbose_name = _("Value condition")
        verbose_name_plural = _("Value conditions")

    @property
    def name(self) -> StrOrPromise:
        return self._description % {
            "amount": currency(self.value),
            "tax": _("tax-inclusive") if self._tax_inclusive else _("tax-exclusive"),
            "range": str(self.range).lower() if self.range else _("product range"),
        }

    @property
    def description(self) -> StrOrPromise:
        return self._description % {
            "amount": currency(self.value),
            "tax": _("tax-inclusive") if self._tax_inclusive else _("tax-exclusive"),
            "range": (
                utils.range_anchor(self.range) if self.range else _("product range")
            ),
        }

    def _clean(self) -> None:
        return _default_clean(self)

    def is_satisfied(self, offer: ConditionalOffer, basket: Basket) -> bool:
        """
        Determine whether a given basket meets this condition
        """
        value_of_matches = Decimal("0.00")
        for line in basket.all_lines():
            quantity_available = line.quantity_without_offer_discount(offer)
            if self.can_apply_condition(line) and quantity_available > 0:
                price = self._get_unit_price(offer, line)
                value_of_matches += price * int(quantity_available)
            if value_of_matches >= self.value:
                return True
        return False

    def get_upsell_details(
        self,
        offer: ConditionalOffer,
        basket: Basket,
    ) -> upsells.AmountUpsell | None:
        value_of_matches = self._get_value_of_matches(offer, basket)
        delta = self.value - value_of_matches
        if delta > 0:
            return upsells.AmountUpsell(
                offer=offer,
                basket=basket,
                product_range=self.range,
                delta=delta,
            )
        return None

    def _get_value_of_matches(self, offer: ConditionalOffer, basket: Basket) -> Decimal:
        if hasattr(self, "_value_of_matches"):
            return getattr(self, "_value_of_matches")
        value_of_matches = Decimal("0.00")
        for line in basket.all_lines():
            if self.can_apply_condition(line):
                price = self._get_unit_price(offer, line)
                quantity_available = line.quantity_without_offer_discount(offer)
                value_of_matches += price * int(quantity_available)
        self._value_of_matches = value_of_matches
        return value_of_matches

    def _get_unit_price(self, offer: ConditionalOffer, line: Line) -> Decimal:
        price = utils.unit_price(offer, line)
        if self._tax_inclusive and line.is_tax_known:
            price += line.unit_tax
        return price

    def consume_items(
        self,
        offer: ConditionalOffer,
        basket: Basket,
        affected_lines: AffectedLines,
    ) -> AffectedLines:
        """
        Same as ValueCondition.consume_items, except that it returns a list of consumed items. This
        is needed for CompoundCondition to be able to correctly consume items.
        """
        applicable_lines = self.get_applicable_lines(
            offer, basket, most_expensive_first=True
        )
        applicable_line_ids = {line.pk for __, line in applicable_lines}

        value_consumed = Decimal("0.00")
        affected_lines = list(affected_lines)
        for line, __, qty in affected_lines:
            if line.pk in applicable_line_ids:
                price = self._get_unit_price(offer, line)
                value_consumed += price * qty

        to_consume = max(0, self.value - value_consumed)
        if to_consume == 0:
            return affected_lines

        for price, line in applicable_lines:
            quantity_to_consume = (to_consume / price).quantize(Decimal(1), ROUND_UP)
            quantity_to_consume = min(
                line.quantity_without_discount, quantity_to_consume
            )
            line.consume(quantity_to_consume, offer=offer)
            affected_lines.append((line, Decimal("0.00"), quantity_to_consume))
            to_consume -= price * quantity_to_consume
            if to_consume <= 0:
                break
        return affected_lines


class BluelightTaxInclusiveValueCondition(BluelightValueCondition):
    _tax_inclusive = True

    class Meta:
        app_label = "offer"
        proxy = True
        verbose_name = _("Tax-Inclusive Value Condition")
        verbose_name_plural = _("Tax-Inclusive Value Conditions")


class CompoundCondition(Condition):
    """
    An offer condition that aggregates together multiple other conditions,
    allowing the creation of compound rules for offers.
    """

    conjunction = models.CharField(
        _("Sub-Condition conjunction type"),
        choices=Conjunction.TYPE_CHOICES,
        default=Conjunction.AND,
        max_length=10,
        help_text="Select the conjunction which will be used to logically join the sub-conditions together.",
    )

    subconditions = models.ManyToManyField(
        "offer.Condition",
        related_name="parent_conditions",
        verbose_name=_("Sub-Conditions"),
        help_text=_(
            "Select the sub-conditions that this compound-condition will combine."
        ),
    )

    class Meta:
        app_label = "offer"
        verbose_name = _("Compound condition")
        verbose_name_plural = _("Compound conditions")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.proxy_class = "{}.{}".format(
            CompoundCondition.__module__,
            CompoundCondition.__name__,
        )

    @property
    def children(self) -> list[Condition]:
        if self.pk is None:
            return []
        chil = [c for c in self.subconditions.order_by("id").all() if c.pk != self.pk]
        return chil

    @property
    def name(self) -> StrOrPromise:
        names = (c.name for c in self.children)
        return human_readable_conjoin(self.conjunction, names, _("Empty Condition"))

    @property
    def description(self) -> StrOrPromise:
        descrs = (c.description for c in self.children)
        return human_readable_conjoin(self.conjunction, descrs, _("Empty Condition"))

    def _clean(self) -> None:
        if self.range:
            raise exceptions.ValidationError(
                _("Compound conditions should not have a range.")
            )
        if self.value:
            raise exceptions.ValidationError(
                _("Compound conditions should not have a value.")
            )

    def is_satisfied(self, offer: ConditionalOffer, basket: Basket) -> bool:
        return self._reduce_results(self.conjunction, "is_satisfied", offer, basket)

    def is_partially_satisfied(self, offer: ConditionalOffer, basket: Basket) -> bool:
        return self._reduce_results(
            Conjunction.OR, "is_partially_satisfied", offer, basket
        )

    def get_upsell_details(
        self,
        offer: ConditionalOffer,
        basket: Basket,
    ) -> upsells.CompoundUpsell | None:
        subupsells: list[upsells.OfferUpsell] = []
        for c in self.children:
            condition = c.proxy()
            partial = condition.is_partially_satisfied(offer, basket)
            complete = condition.is_satisfied(offer, basket)
            if not complete and partial:
                subupsell = condition.get_upsell_details(offer, basket)
                if subupsell:
                    subupsells.append(subupsell)
        if len(subupsells) > 0:
            return upsells.CompoundUpsell(
                offer=offer,
                basket=basket,
                conjunction=self.conjunction,
                subupsells=subupsells,
            )
        return None

    def get_upsell_message(
        self,
        offer: ConditionalOffer,
        basket: Basket,
    ) -> StrOrPromise:
        messages = []
        for c in self.children:
            condition = c.proxy()
            partial = condition.is_partially_satisfied(offer, basket)
            complete = condition.is_satisfied(offer, basket)
            if not complete and partial:
                messages.append(condition.get_upsell_message(offer, basket))
        return human_readable_conjoin(self.conjunction, messages)

    def consume_items(
        self,
        offer: ConditionalOffer,
        basket: Basket,
        affected_lines: AffectedLines,
    ) -> AffectedLines:
        memo = affected_lines
        for c in self.children:
            affected_lines = c.proxy().consume_items(offer, basket, memo)
            if affected_lines and getattr(affected_lines, "__iter__"):
                memo = affected_lines
        return affected_lines

    def _reduce_results(
        self,
        conjunction: str,
        method_name: Literal["is_satisfied", "is_partially_satisfied"],
        offer: ConditionalOffer,
        basket: Basket,
    ) -> bool:
        result = self._get_conjunction_root_memo(conjunction)
        for c in self.children:
            condition = c.proxy()
            fn = getattr(condition, method_name)
            subresult = fn(offer, basket)
            result = self._apply_conjunction(conjunction, result, subresult)
        return result

    def _get_conjunction_root_memo(self, conjunction: str) -> bool:
        memos = {
            Conjunction.AND: True,
            Conjunction.OR: False,
        }
        return memos[conjunction]

    def _apply_conjunction(self, conjunction: str, a: bool, b: bool) -> bool:
        fns = {
            Conjunction.AND: lambda: a and b,
            Conjunction.OR: lambda: a or b,
        }
        return fns[conjunction]()


__all__ = [
    "BluelightCountCondition",
    "BluelightCoverageCondition",
    "BluelightValueCondition",
    "CompoundCondition",
]
