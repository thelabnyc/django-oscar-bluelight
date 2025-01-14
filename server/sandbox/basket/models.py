from decimal import Decimal
from typing import Any

from oscar.apps.basket.abstract_models import AbstractBasket, AbstractLine

from oscarbluelight.mixins import BluelightBasketLineMixin, BluelightBasketMixin
from oscarbluelight.offer.groups import (
    pre_offer_group_apply_receiver,
    register_system_offer_group,
)


class Basket(BluelightBasketMixin, AbstractBasket):
    pass


class Line(BluelightBasketLineMixin, AbstractLine):
    pass


# Create a system offer group for post-tax offers. Then we'll use signals to
# make sure tax is applied before this offer group's offers are evaluated.
offer_group_post_tax_offers = register_system_offer_group("post-tax-offers")


@pre_offer_group_apply_receiver(
    "post-tax-offers", dispatch_uid="calculate_basket_taxes"
)
def calculate_basket_taxes(sender: Any, basket: Basket, **kwargs: Any) -> None:
    """
    Do some fake tax calculation here.
    """
    for line in basket.all_lines():
        line.purchase_info.price.tax = Decimal("1.00") * line.quantity


from oscar.apps.basket.models import *  # type:ignore[assignment] # NOQA
