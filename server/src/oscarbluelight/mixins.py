from collections import namedtuple
from decimal import Decimal
import itertools



PriceBreakdownStackEntry = namedtuple('PriceBreakdownStackEntry', (
    'quantity_with_discount',
    'discount_delta_unit',
))

LineDiscountDescription = namedtuple('LineDiscountDescription', (
    'amount',
    'offer_name',
    'offer_description',
    'voucher_name',
    'voucher_code',
))



class BluelightBasketLineMixin(object):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The built-in _affected_quantity property simply tracks how many items in the line aren't available
        # for use by offers. This property tracks what subset of that number was actually discounted (versus
        # just marked as unavailable for discount)
        self._discounted_quantity = 0

        # The built-in _affected_quantity property refers to affected quantity within an offer group.
        # This property refers to the affected quantity global of OfferGroups
        self._global_affected_quantity = 0

        # Keep track of the discount amount at the start of offer group application, so that we can tell what
        # the current offer group has accomplished, versus previous offer groups.
        self._offer_group_starting_discount = Decimal('0.00')

        # Used to record a "stack" of prices as the decrease via offer group application, used when calculating
        # the price breakdown.
        self._price_breakdown_stack = []

        # Used to track descriptions of why discounts where applied to the line.
        self._discount_descriptions = []


    @property
    def unit_effective_price(self):
        """
        The price to use for offer calculations.

        We have to override this so that the price used to calculate offers takes into account
        previously applied, compounding discounts.

        Description of logic:

        During offer application, because of the existence of OfferGroup, discount may be > 0 even
        when  ``_affected_quantity`` is 0. This is because Applicator resets ``_affected_quantity``
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
            1. A MultibuyDiscountBenefit makes one item free. Total is now $100 and _affected_quantity of
               line 1 is 1.
            2. Applicator resets _affected_quantity of line 1 to 0
        2. Applicator applies Offer Group 2:
            1. A $300 AbsoluteDiscountBenefit subtracts $200 from the line. Total is now -$100 and
               _affected_quantity of line 1 is 2.
            2. Applicator resets _affected_quantity of line 1 to 0.
        3. Applicator sets _affected_quantity of line 1 to 2 (min of the *line 1's quantity* and the *internal
           line 1 affected counter*).

        Point 2.1 occurs because this method, unit_effective_price, always returns the full item price, $100.
        The correct functionality is:

        1. Applicator applies Offer Group 1:
            1. A MultibuyDiscountBenefit makes one item free. Total is now $100 and _affected_quantity of
               line 1 is 1.
            2. Applicator resets _affected_quantity of line 1 to 0
        2. Applicator applies Offer Group 2:
            1. A $300 AbsoluteDiscountBenefit subtracts $100 from the line. Total is now $0 and
               _affected_quantity of line 1 is 2.
            2. Applicator resets _affected_quantity of line 1 to 0.
        3. Applicator sets _affected_quantity of line 1 to 2 (min of the *line 1's quantity* and the *internal
           line 1 affected counter*).

        In order for point 2.1 to work that way and subtract $100 instead of $200, it must start with the already
        discounted line price of $100, which equates to a unit_effective_price of $50.
        """
        if self._discount_incl_tax > Decimal('0.00'):
            raise RuntimeError('Bluelight does not support tax-inclusive discounting.')

        # Protect against divide by 0 errors
        if self.quantity == 0:
            return Decimal('0.00')

        # Figure out the per-unit discount by taking the discount at the start of offer group application and
        # dividing it by the line quantity.
        per_unit_discount = self._offer_group_starting_discount / self.quantity
        unit_price_full = self.purchase_info.price.effective_price
        unit_price_discounted = unit_price_full - per_unit_discount
        return unit_price_discounted


    def clear_discount(self):
        """
        Remove any discounts from this line.
        """
        super().clear_discount()
        self._discounted_quantity = 0
        self._global_affected_quantity = 0
        self._offer_group_starting_discount = Decimal('0.00')
        self._price_breakdown_stack = []
        self._discount_descriptions = []


    def discount(self, discount_value, affected_quantity, incl_tax=True, source_offer=None):
        """
        Apply a discount to this line.

        Blocks any discounts with include tax since Bluelight does not support this behavior, due
        to the challenges of OfferGroup compounding offers.
        """
        if incl_tax:
            raise RuntimeError(
                "Attempting to discount the tax-inclusive price of a line "
                "when tax-exclusive discounts are already applied")
        if self._discount_incl_tax > 0:
            raise RuntimeError(
                "Attempting to discount the tax-exclusive price of a line "
                "when tax-inclusive discounts are already applied")

        # Increase the total line discount amount
        self._discount_excl_tax += discount_value

        # Increment tracking counters
        self._affected_quantity += int(affected_quantity)
        self._discounted_quantity += int(affected_quantity)
        self._global_affected_quantity += int(affected_quantity)

        # Push description of discount onto the stack
        if source_offer:
            voucher = source_offer.get_voucher()
            descr = LineDiscountDescription(
                amount=discount_value,
                offer_name=source_offer.name,
                offer_description=source_offer.description,
                voucher_name=voucher.name if voucher else None,
                voucher_code=voucher.code if voucher else None)
            self._discount_descriptions.append(descr)


    def get_discount_descriptions(self):
        return self._discount_descriptions


    def consume(self, quantity):
        """
        Mark all or part of the line as 'consumed' within an offer group

        Consumed items are no longer available to be used in offers within the same offer group. They
        can be consumed again by offers in other offer groups.
        """
        super().consume(quantity)
        if quantity > self.quantity - self._global_affected_quantity:
            inc = self.quantity - self._global_affected_quantity
        else:
            inc = quantity
        self._global_affected_quantity += int(inc)


    def begin_offer_group_application(self):
        """
        Signal that the Applicator will begin to apply a new group of offers.

        Since line consumption is name-spaced within each offer group, we record the discount
        amount at the start of application and we reset the ``_affected_quantity`` property to 0.
        This allows offers to re-consume lines already consumed by previous offer groups while
        still calculating their discount amounts correctly.
        """
        self._affected_quantity = 0
        self._discounted_quantity = 0
        self._offer_group_starting_discount = self.discount_value


    def end_offer_group_application(self):
        """
        Signal that the Applicator has finished applying a group of offers.
        """
        if self._discounted_quantity > 0:
            delta_line = self.discount_value - self._offer_group_starting_discount
            delta_unit = delta_line / self._discounted_quantity
            item = PriceBreakdownStackEntry(
                quantity_with_discount=self._discounted_quantity,
                discount_delta_unit=delta_unit)
            self._price_breakdown_stack.append(item)
            self._discounted_quantity = 0


    def finalize_offer_group_applications(self):
        """
        Signal that all offer groups (and therefore all offers) have now been applied.
        """
        self._affected_quantity = min(self.quantity, self._global_affected_quantity)


    def get_price_breakdown(self):
        """
        Return a breakdown of line prices after discounts have been applied.

        Returns a list of (unit_price_incl_tax, unit_price_excl_tax, quantity) tuples.
        """
        if not self.is_tax_known:
            raise RuntimeError("A price breakdown can only be determined when taxes are known")

        # Create an array of the pre-discount unit prices with length equal to the line quantity
        item_prices = []
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
        for price, prices in itertools.groupby(sorted(item_prices)):
            qty = len(list(prices))
            price_qty = (price, qty)
            price_qtys.append(price_qty)

        # Return a list of (unit_price_incl_tax, unit_price_excl_tax, quantity)
        prices = []
        line_price_excl_tax_incl_discounts = self.line_price_excl_tax_incl_discounts
        # TODO: Remove the ``or`` default once https://github.com/django-oscar/django-oscar/issues/2395 is resolved.
        line_tax = self.line_tax or Decimal('0.00')

        # Avoid a divide by 0 error when the line is completely free, but still has tax applied to it.
        free = Decimal('0.00')
        if line_price_excl_tax_incl_discounts <= free:
            prices.append((line_tax, free, self.quantity))
            return prices

        # When the line isn't free, distribute tax evenly based on what share of the total line price this unit prices accounts for.
        for unit_price_excl_tax, quantity in price_qtys:
            unit_tax = (unit_price_excl_tax / line_price_excl_tax_incl_discounts) * line_tax
            unit_price_incl_tax = (unit_price_excl_tax + unit_tax).quantize(unit_price_excl_tax)
            prices.append((unit_price_incl_tax, unit_price_excl_tax, quantity))

        return prices