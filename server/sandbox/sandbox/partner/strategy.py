from oscar.core.loading import get_class
from oscar.apps.partner.strategy import US as BaseUS

UnavailablePrice = get_class("partner.prices", "Unavailable")
FixedPrice = get_class("partner.prices", "FixedPrice")
Applicator = get_class("offer.applicator", "Applicator")


class US(BaseUS):
    def pricing_policy(self, product, stockrecord):
        if not stockrecord or stockrecord.price is None:
            return UnavailablePrice()
        return FixedPrice(
            currency=stockrecord.price_currency,
            excl_tax=stockrecord.price,
            get_cosmetic_excl_tax=lambda: Applicator().get_cosmetic_price(
                self, product
            ),
        )


class Selector(object):
    def strategy(self, request=None, user=None, **kwargs):
        return US(request)
