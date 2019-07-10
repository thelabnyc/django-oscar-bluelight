from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from oscar.core import prices
from oscar.apps.partner.prices import FixedPrice as BaseFixedPrice


class FixedPrice(BaseFixedPrice):
    """
    Just like the default FixedPrice, but with added cosmetic_excl_tax
    and cosmetic_incl_tax properties
    """
    def __init__(self, *args, get_cosmetic_excl_tax=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._get_cosmetic_excl_tax = get_cosmetic_excl_tax
        if self._get_cosmetic_excl_tax is None:
            self._get_cosmetic_excl_tax = lambda: self.excl_tax


    @cached_property
    def cosmetic_excl_tax(self):
        return self._get_cosmetic_excl_tax()


    @cached_property
    def cosmetic_incl_tax(self):
        if self.is_tax_known:
            return self.cosmetic_excl_tax + self.tax
        raise prices.TaxNotKnown(_("Can't calculate price.incl_tax as tax isn't known"))
