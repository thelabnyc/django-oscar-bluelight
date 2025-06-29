from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from django.utils.translation import gettext_lazy as _
from oscar.templatetags.currency_filters import currency

from .utils import human_readable_conjoin

if TYPE_CHECKING:
    from django_stubs_ext import StrOrPromise
    from oscar.apps.catalogue.models import Product

    from ..mixins import BluelightBasketMixin as Basket
    from .models import ConditionalOffer, Range


class OfferUpsell:
    _cta_tmpl: StrOrPromise = ""
    _reward_tmpl = _("to qualify for the %(offer_name)s special offer.")

    def __init__(self, offer: ConditionalOffer, basket: Basket) -> None:
        self.type_code = self.__class__.__name__
        self.offer = offer
        self.basket = basket
        self.group_priority = offer.offer_group.priority if offer.offer_group else None
        self.offer_priority = offer.priority

    def is_relevant_to_product(self, product: Product) -> bool:
        return False

    def get_cta_text(self) -> StrOrPromise:
        context = self.get_summary_tmpl_context()
        return self.get_cta_tmpl() % context

    def get_reward_text(self) -> StrOrPromise:
        context = self.get_summary_tmpl_context()
        return self.get_reward_tmpl() % context

    def get_summary(self) -> StrOrPromise:
        return _("%(cta)s %(reward)s") % {
            "cta": self.get_cta_text(),
            "reward": self.get_reward_text(),
        }

    def get_summary_tmpl_context(self) -> dict[str, str | Decimal]:
        return {
            "offer_name": self.offer.name,
            "offer_url": self.offer.get_absolute_url(),
        }

    def get_cta_tmpl(self) -> StrOrPromise:
        return self._cta_tmpl

    def get_reward_tmpl(self) -> StrOrPromise:
        return self._reward_tmpl


class SimpleUpsell(OfferUpsell):
    _cta_tmpl_plural: StrOrPromise = ""

    def __init__(
        self,
        product_range: Range,
        delta: Decimal,
        offer: ConditionalOffer,
        basket: Basket,
    ):
        super().__init__(offer, basket)
        self.product_range = product_range
        self.delta = delta

    def is_relevant_to_product(self, product: Product) -> bool:
        return self.product_range.contains_product(product)

    def get_summary_tmpl_context(self) -> dict[str, str | Decimal]:
        ctx = super().get_summary_tmpl_context()
        ctx["range"] = self.product_range.name
        ctx["delta"] = self.delta
        return ctx

    def get_cta_tmpl(self) -> StrOrPromise:
        if self.delta > 1 and self._cta_tmpl_plural is not None:
            return self._cta_tmpl_plural
        return super().get_cta_tmpl()


class QuantityUpsell(SimpleUpsell):
    """
    Represent an upsell message which asks the customer to add an additional
    quantity of products to their cart. Used in conjunction with
    CountCondition.
    """

    _cta_tmpl = _("Buy %(delta)d more product from %(range)s")
    _cta_tmpl_plural = _("Buy %(delta)d more products from %(range)s")


class CoverageUpsell(SimpleUpsell):
    """
    Represent an upsell message which asks the customer to add an additional
    quantity of different products to their cart. Used in conjunction with
    CoverageCondition.
    """

    _cta_tmpl = _("Buy %(delta)d more product from %(range)s")
    _cta_tmpl_plural = _("Buy %(delta)d more products from %(range)s")


class AmountUpsell(SimpleUpsell):
    """
    Represent an upsell message which asks the customer to add an additional
    dollar value of products to their cart. Used in conjunction with
    ValueCondition.
    """

    _cta_tmpl = _("Spend %(delta)s more from %(range)s")

    def get_summary_tmpl_context(self) -> dict[str, str | Decimal]:
        ctx = super().get_summary_tmpl_context()
        ctx["delta"] = currency(self.delta, self.basket.currency)
        return ctx


class CompoundUpsell(OfferUpsell):
    """
    Represent an upsell message which asks the customer to do several things.
    Used in conjunction with CompoundCondition.
    """

    def __init__(
        self,
        conjunction: str,
        subupsells: list[OfferUpsell],
        offer: ConditionalOffer,
        basket: Basket,
    ):
        super().__init__(offer, basket)
        self.conjunction = conjunction
        self.subupsells = subupsells

    def is_relevant_to_product(self, product: Product) -> bool:
        for upsell in self.subupsells:
            if upsell.is_relevant_to_product(product):
                return True
        return False

    def get_summary(self) -> StrOrPromise:
        ctas = [upsell.get_cta_text() for upsell in self.subupsells]
        return _("%(cta)s %(reward)s") % {
            "cta": human_readable_conjoin(self.conjunction, ctas),
            "reward": self.get_reward_text(),
        }
