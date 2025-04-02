from typing import Any

from django.contrib.auth.models import User
from django.http import HttpRequest
from oscar.apps.catalogue.models import Product
from oscar.apps.partner.prices import Base as BasePrice
from oscar.apps.partner.prices import Unavailable as UnavailablePrice
from oscar.apps.partner.strategy import US as BaseUS

from oscarbluelight.offer.applicator import Applicator

from .models import StockRecord
from .prices import FixedPrice


class US(BaseUS):
    def pricing_policy(self, product: Product, stockrecord: StockRecord) -> BasePrice:
        if not stockrecord or stockrecord.price is None:
            return UnavailablePrice()
        return FixedPrice(
            currency=stockrecord.price_currency,
            excl_tax=stockrecord.price,
            get_cosmetic_excl_tax=lambda: Applicator().get_cosmetic_price(
                self, product
            ),
        )


class Selector:
    def strategy(
        self,
        request: HttpRequest | None = None,
        user: User | None = None,
        **kwargs: Any,
    ) -> US:
        return US(request)
