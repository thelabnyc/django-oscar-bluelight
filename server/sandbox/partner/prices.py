from collections.abc import Callable
from decimal import Decimal

from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from oscar.apps.partner.prices import FixedPrice as BaseFixedPrice
from oscar.core import prices


class FixedPrice(BaseFixedPrice):
    """
    Just like the default FixedPrice, but with added cosmetic_excl_tax
    and cosmetic_incl_tax properties
    """

    excl_tax: Decimal  # type:ignore[assignment]
    _get_cosmetic_excl_tax: Callable[[], Decimal]

    def __init__(
        self,
        currency: str,
        excl_tax: Decimal,
        tax: Decimal | None = None,
        tax_code: str | None = None,
        get_cosmetic_excl_tax: Callable[[], Decimal] | None = None,
    ):
        super().__init__(
            currency=currency,
            excl_tax=excl_tax,
            tax=tax,
            tax_code=tax_code,
        )
        self._get_cosmetic_excl_tax = (
            get_cosmetic_excl_tax
            if get_cosmetic_excl_tax is not None
            else lambda: self.excl_tax
        )

    @cached_property
    def cosmetic_excl_tax(self) -> Decimal:
        return self._get_cosmetic_excl_tax()

    @cached_property
    def cosmetic_incl_tax(self) -> Decimal:
        if self.is_tax_known and self.tax is not None:
            return self.cosmetic_excl_tax + self.tax
        raise prices.TaxNotKnown(_("Can't calculate price.incl_tax as tax isn't known"))
