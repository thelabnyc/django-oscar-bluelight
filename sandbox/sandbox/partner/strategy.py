from decimal import Decimal as D
from oscar.core.loading import get_class
from oscar.apps.partner.strategy import Default as BaseDefault

UnavailablePrice = get_class('partner.prices', 'Unavailable')
FixedPrice = get_class('partner.prices', 'FixedPrice')
Applicator = get_class('offer.applicator', 'Applicator')


class Default(BaseDefault):
    def pricing_policy(self, product, stockrecord):
        if not stockrecord or stockrecord.price_excl_tax is None:
            return UnavailablePrice()

        cosmetic_excl_tax = Applicator().get_cosmetic_price(product, stockrecord.price_excl_tax)
        return FixedPrice(
            currency=stockrecord.price_currency,
            excl_tax=stockrecord.price_excl_tax,
            cosmetic_excl_tax=cosmetic_excl_tax,
            tax=D('0.00'))


class Selector(object):
    def strategy(self, request=None, user=None, **kwargs):
        return Default(request)
