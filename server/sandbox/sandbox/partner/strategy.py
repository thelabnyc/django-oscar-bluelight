from oscar.core.loading import get_class
from oscar.apps.partner.strategy import US as BaseUS

UnavailablePrice = get_class('partner.prices', 'Unavailable')
FixedPrice = get_class('partner.prices', 'FixedPrice')
Applicator = get_class('offer.applicator', 'Applicator')


class US(BaseUS):
    def pricing_policy(self, product, stockrecord):
        if not stockrecord or stockrecord.price_excl_tax is None:
            return UnavailablePrice()

        cosmetic_excl_tax = Applicator().get_cosmetic_price(product, stockrecord.price_excl_tax)
        return FixedPrice(
            currency=stockrecord.price_currency,
            excl_tax=stockrecord.price_excl_tax,
            cosmetic_excl_tax=cosmetic_excl_tax)


class Selector(object):
    def strategy(self, request=None, user=None, **kwargs):
        return US(request)
