from oscar.core import prices
from oscar.apps.partner.prices import FixedPrice as BaseFixedPrice


class FixedPrice(BaseFixedPrice):
    """
    Just like the default FixedPrice, but with added cosmetic_excl_tax
    and cosmetic_incl_tax properties
    """
    def __init__(self, *args, cosmetic_excl_tax=None, **kwargs):
        super().__init__(*args, **kwargs)
        if cosmetic_excl_tax:
            self.cosmetic_excl_tax = cosmetic_excl_tax
        else:
            self.cosmetic_excl_tax = self.excl_tax


    @property
    def cosmetic_incl_tax(self):
        if self.is_tax_known:
            return self.cosmetic_excl_tax + self.tax
        raise prices.TaxNotKnown("Can't calculate price.incl_tax as tax isn't known")
