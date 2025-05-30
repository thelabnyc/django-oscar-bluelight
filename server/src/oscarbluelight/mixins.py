from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any, NamedTuple
import itertools

from django.utils.translation import gettext_lazy as _
from oscar.core.utils import round_half_up

if TYPE_CHECKING:
    from oscar.apps.basket.abstract_models import AbstractBasket, AbstractLine

    from .offer import results
    from .offer.models import ConditionalOffer
    from .offer.upsells import OfferUpsell
    from .voucher.models import Voucher
else:

    class AbstractBasket:
        pass

    class AbstractLine:
        pass


class PriceBreakdownStackEntry(NamedTuple):
    quantity_with_discount: int
    discount_delta_unit: Decimal


class LineDiscountDescription(NamedTuple):
    amount: Decimal
    offer_name: str
    offer_description: str
    voucher_name: str | None
    voucher_code: str | None


class LinePriceBreakdownItem(NamedTuple):
    unit_price_incl_tax: Decimal
    unit_price_excl_tax: Decimal
    quantity: int


class BluelightBasketMixin(AbstractBasket):
    @property
    def offer_post_order_actions(self) -> list[results.PostOrderAction]:
        """
        Return post order actions from offers
        """
        return self.offer_applications.offer_post_order_actions

    @property
    def voucher_post_order_actions(self) -> list[results.PostOrderAction]:
        """
        Return post order actions from offers
        """
        return self.offer_applications.voucher_post_order_actions

    def clear_offer_upsells(self) -> None:
        for line in self.all_lines():
            line.clear_offer_upsells()

    def add_offer_upsell(self, offer_upsell: OfferUpsell) -> None:
        for line in self.all_lines():
            if line.product and offer_upsell.is_relevant_to_product(line.product):
                line.add_offer_upsell(offer_upsell)

    def get_offer_upsells(self) -> list[OfferUpsell]:
        offer_upsells = set()
        for line in self.all_lines():
            for upsell in line.get_offer_upsells():
                offer_upsells.add(upsell)
        return list(offer_upsells)


class BluelightBasketLineMixin(AbstractLine):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # Keep track of the discount amount at the start of offer group application, so that we can tell what
        # the current offer group has accomplished, versus previous offer groups.
        self._offer_group_starting_discount = Decimal("0.00")

        # Used to record a "stack" of prices as they decrease via offer group application, used when calculating the price breakdown.
        self._price_breakdown_stack: list[PriceBreakdownStackEntry] = []

        # Used to track descriptions of why discounts where applied to the line.
        self._discount_descriptions: list[LineDiscountDescription] = []

        # Used to track offer upsell messages
        self._offer_upsells: list[OfferUpsell] = []

    @property
    def unit_effective_price(self) -> Decimal:
        """
        The price to use for offer calculations.

        We have to override this so that the price used to calculate offers takes into account
        previously applied, compounding discounts.

        Description of logic:

        During offer application, because of the existence of OfferGroup, discount may be > 0 even
        when ``self.discounts.num_consumed`` is 0. This is because Applicator resets the affected quantity
        to 0 when progressing onto the next OfferGroup, so that the it may affect the same lines that
        the previous OfferGroup just did, e.g. compounding offers. However, since by default Offers
        all calculate their discounts using the full unit price excluding discounts, this has the
        possibility of creating negatively priced lines. For instance:

        ==  ========  ==========  ===========
        Basket
        -------------------------------------
        ID  Quantity  Unit Price  Total Price
        ==  ========  ==========  ===========
        1   2         $100        $200
        ==  ========  ==========  ===========

        1. Applicator applies Offer Group 1:
            1. A MultibuyDiscountBenefit makes one item free. Total is now $100 and affected quantity of
               line 1 is 1.
            2. Applicator resets affected quantity of line 1 to 0
        2. Applicator applies Offer Group 2:
            1. A $300 AbsoluteDiscountBenefit subtracts $200 from the line. Total is now -$100 and
               affected quantity of line 1 is 2.
            2. Applicator resets affected quantity of line 1 to 0.
        3. Applicator sets affected quantity of line 1 to 2 (min of the *line 1's quantity* and the *internal
           line 1 affected counter*).

        Point 2.1 occurs because this method, unit_effective_price, always returns the full item price, $100.
        The correct functionality is:

        1. Applicator applies Offer Group 1:
            1. A MultibuyDiscountBenefit makes one item free. Total is now $100 and affected quantity of
               line 1 is 1.
            2. Applicator resets affected quantity of line 1 to 0
        2. Applicator applies Offer Group 2:
            1. A $300 AbsoluteDiscountBenefit subtracts $100 from the line. Total is now $0 and
               affected quantity of line 1 is 2.
            2. Applicator resets affected quantity of line 1 to 0.
        3. Applicator sets affected quantity of line 1 to 2 (min of the *line 1's quantity* and the *internal
           line 1 affected counter*).

        In order for point 2.1 to work that way and subtract $100 instead of $200, it must start with the already
        discounted line price of $100, which equates to a unit_effective_price of $50.
        """
        if self._discount_incl_tax > Decimal("0.00"):
            raise RuntimeError(
                _("Bluelight does not support tax-inclusive discounting.")
            )

        # Protect against divide by 0 errors and comparing None with Decimal errors (price field in
        # StockRecord is allowed to be null, which means effective_price may occasionally be None).
        if self.quantity == 0 or self.purchase_info.price.effective_price is None:
            return Decimal("0.00")

        # Figure out the per-unit discount by taking the discount at the start of offer group application and
        # dividing it by the line quantity.
        per_unit_discount = self._offer_group_starting_discount / self.quantity
        unit_price_full = self.purchase_info.price.effective_price
        unit_price_discounted = unit_price_full - per_unit_discount
        return unit_price_discounted

    @property
    def line_price_incl_tax_incl_discounts(self) -> Decimal | None:
        if self.line_price_incl_tax is not None:
            return Decimal(
                max(0, round_half_up(self.line_price_incl_tax - self.discount_value))
            )
        return None

    def clear_discount(self) -> None:
        """
        Remove any discounts from this line.
        """
        super().clear_discount()
        self._offer_group_starting_discount = Decimal("0.00")
        self._price_breakdown_stack = []
        self._discount_descriptions = []

    def discount(
        self,
        discount_value: Decimal,
        affected_quantity: int,
        incl_tax: bool = True,
        offer: ConditionalOffer | None = None,
    ) -> None:
        """
        Apply a discount to this line.

        Blocks any discounts with include tax since Bluelight does not support this behavior, due
        to the challenges of OfferGroup compounding offers.
        """
        if incl_tax:
            raise RuntimeError(
                _(
                    "Attempting to discount the tax-inclusive price of a line "
                    "when tax-exclusive discounts are already applied"
                )
            )
        if self._discount_incl_tax > 0:
            raise RuntimeError(
                _(
                    "Attempting to discount the tax-exclusive price of a line "
                    "when tax-inclusive discounts are already applied"
                )
            )

        # Increment tracking counters
        self.discounts.discount(discount_value, affected_quantity, incl_tax, offer)

        # Push description of discount onto the stack
        if offer:
            voucher: Voucher | None = offer.get_voucher()
            descr = LineDiscountDescription(
                amount=discount_value,
                offer_name=offer.name,
                offer_description=offer.description,
                voucher_name=voucher.name if voucher else None,
                voucher_code=voucher.code if voucher else None,
            )
            self._discount_descriptions.append(descr)

    def get_discount_descriptions(self) -> list[LineDiscountDescription]:
        return self._discount_descriptions

    def begin_offer_group_application(self) -> None:
        """
        Signal that the Applicator will begin to apply a new group of offers.

        Since line consumption is name-spaced within each offer group, we record the discount
        amount at the start of application and we reset the ``_affected_quantity`` property to 0.
        This allows offers to re-consume lines already consumed by previous offer groups while
        still calculating their discount amounts correctly.
        """
        self.discounts.begin_offer_group_application()
        self._offer_group_starting_discount = self.discount_value

    def end_offer_group_application(self) -> None:
        """
        Signal that the Applicator has finished applying a group of offers.
        """
        discounted_quantity = self.discounts.discounted()
        if discounted_quantity > 0:
            delta_line = self.discount_value - self._offer_group_starting_discount
            delta_unit = delta_line / discounted_quantity
            item = PriceBreakdownStackEntry(
                quantity_with_discount=discounted_quantity,
                discount_delta_unit=delta_unit,
            )
            self._price_breakdown_stack.append(item)
            self.discounts.end_offer_group_application()

    def finalize_offer_group_applications(self) -> None:
        """
        Signal that all offer groups (and therefore all offers) have now been applied.
        """
        self.discounts.finalize_offer_group_applications()
        self._offer_group_starting_discount = self.discount_value

    def clear_offer_upsells(self) -> None:
        self._offer_upsells = []

    def add_offer_upsell(self, offer_upsell: OfferUpsell) -> None:
        self._offer_upsells.append(offer_upsell)

    def get_offer_upsells(self) -> list[OfferUpsell]:
        return self._offer_upsells

    def get_price_breakdown(self) -> list[LinePriceBreakdownItem]:
        """
        Return a breakdown of line prices after discounts have been applied.

        Returns a list of (unit_price_incl_tax, unit_price_excl_tax, quantity) tuples.
        """
        if not self.is_tax_known:
            raise RuntimeError(
                _("A price breakdown can only be determined when taxes are known")
            )

        # Create an array of the pre-discount unit prices with length equal to the line quantity
        item_prices: list[Decimal] = []
        for i in range(self.quantity):
            item_prices.append(self.unit_price_excl_tax)

        # Make sure _price_breakdown_stack adequately describes the total discount applied (in-case
        # somehow we applied a benefit but didn't call ``end_offer_group_application``. If it was
        # called, this is a no-op.
        self.end_offer_group_application()

        # Based on the discounts and affected quantities recorded in the _price_breakdown_stack, decrease each
        # unit price in the line until the full discount amount is exhausted.
        for discount_group in self._price_breakdown_stack:
            remaining_qty_affected = discount_group.quantity_with_discount
            iterations = 0
            while remaining_qty_affected > 0 and iterations <= self.quantity:
                for i in range(self.quantity):
                    if item_prices[i] >= discount_group.discount_delta_unit:
                        item_prices[i] -= discount_group.discount_delta_unit
                        remaining_qty_affected -= 1

                    if remaining_qty_affected <= 0:
                        break
                iterations += 1

        # Remove the duplicate unit prices, resulting in a list of tuples containing a unit price and the quantity at that unit price
        price_qtys = []
        for price, _prices in itertools.groupby(sorted(item_prices)):
            qty = len(list(_prices))
            price_qty = (price, qty)
            price_qtys.append(price_qty)

        # Return a list of (unit_price_incl_tax, unit_price_excl_tax, quantity)
        prices: list[LinePriceBreakdownItem] = []
        line_price_excl_tax_incl_discounts = self.line_price_excl_tax_incl_discounts
        line_tax = self.line_tax

        # Avoid a divide by 0 error when the line is completely free, but still has tax applied to it.
        free = Decimal("0.00")
        if line_price_excl_tax_incl_discounts <= free:
            prices.append(
                LinePriceBreakdownItem(
                    unit_price_incl_tax=line_tax,
                    unit_price_excl_tax=free,
                    quantity=self.quantity,
                )
            )
            return prices

        # When the line isn't free, distribute tax evenly based on what share of the total line price this unit prices accounts for.
        for unit_price_excl_tax, quantity in price_qtys:
            unit_tax = (
                unit_price_excl_tax / line_price_excl_tax_incl_discounts
            ) * line_tax
            unit_price_incl_tax = (unit_price_excl_tax + unit_tax).quantize(
                unit_price_excl_tax
            )
            prices.append(
                LinePriceBreakdownItem(
                    unit_price_incl_tax=unit_price_incl_tax,
                    unit_price_excl_tax=unit_price_excl_tax,
                    quantity=quantity,
                )
            )

        return prices
