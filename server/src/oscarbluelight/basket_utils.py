from collections import defaultdict
from decimal import Decimal
from oscar.core.decorators import deprecated
from oscar.apps.basket.utils import DiscountApplication

ZERO = Decimal("0.00")


class BluelightLineOfferConsumer(object):
    """
    Version of ``oscar.app.basket.utils.LineOfferConsumer`` which supports OfferGroups.
    """

    def __init__(self, line):
        self._line = line
        self._offers = dict()
        self._affected_quantity = 0
        self._consumptions = defaultdict(int)

        # The built-in _affected_quantity property simply tracks how many items in the line aren't available
        # for use by offers. This property tracks what subset of that number was actually discounted (versus
        # just marked as unavailable for discount)
        self._discounted_quantity = 0

        # The built-in _affected_quantity property refers to affected quantity within an offer group.
        # This property refers to the affected quantity global of OfferGroups
        self._global_affected_quantity = 0

    def _cache(self, offer):
        self._offers[offer.pk] = offer

    def _update_affected_quantity(self, quantity):
        available_in_group = int(self._line.quantity - self._affected_quantity)
        available_global = int(self._line.quantity - self._global_affected_quantity)
        self._affected_quantity += min(available_in_group, quantity)
        self._global_affected_quantity += min(available_global, quantity)

    def consume(self, quantity, offer=None):
        """
        Mark a basket line as consumed by an offer in the current offer group.

        If offer is None, the specified quantity of items on this basket line is consumed for *any*
        offer, else only for the specified offer.
        """
        self._update_affected_quantity(quantity)
        if offer:
            self._cache(offer)
            available = self.available(offer)
            self._consumptions[offer.pk] += min(available, quantity)

    @deprecated
    def consumed(self, offer=None):
        return self.num_consumed(offer)

    def num_consumed(self, offer=None):
        """
        Check how many items on this line have been consumed by an offer in the current offer group.

        If offer is not None, only the number of items marked with the specified ConditionalOffer are returned.
        """
        if not offer:
            return self._affected_quantity
        return int(self._consumptions[offer.pk])

    @property
    def consumers(self):
        return [x for x in self._offers.values() if self.num_consumed(x)]

    def available(self, offer=None):
        """
        Check how many items are available for offers
        """
        if offer:
            exclusive = any([x.exclusive for x in self._offers.values()])
            exclusive |= bool(offer.exclusive)
        else:
            exclusive = True

        if exclusive:
            offer = None

        consumed = self.num_consumed(offer)
        return int(self._line.quantity - consumed)

    def discount(self, amount, quantity, incl_tax=True, offer=None):
        """
        Update the discounted quantity.
        """
        self._discounted_quantity += quantity

    def discounted(self):
        """
        Get the number of items that have been discounted in the current offer group.
        """
        return self._discounted_quantity

    def begin_offer_group_application(self):
        """
        Signal that the Applicator will begin to apply a new group of offers.

        Since line consumption is name-spaced within each offer group, we reset the ``_affected_quantity`` property
        to 0. This allows offers to re-consume lines already consumed by previous offer groups while still calculating
        their discount amounts correctly.
        """
        self._affected_quantity = 0
        self._discounted_quantity = 0

    def end_offer_group_application(self):
        """
        Signal that the Applicator has finished applying a group of offers.
        """
        self._discounted_quantity = 0

    def finalize_offer_group_applications(self):
        """
        Signal that all offer groups (and therefore all offers) have now been applied.
        """
        self._affected_quantity = min(
            self._line.quantity, self._global_affected_quantity
        )


class BluelightLineDiscountRegistry(BluelightLineOfferConsumer):
    def __init__(self, line):
        super().__init__(line)
        self._discounts = []
        self._discount_excl_tax = None
        self._discount_incl_tax = None

    def discount(self, amount, quantity, incl_tax=True, offer=None):
        super().discount(amount, quantity, incl_tax=incl_tax, offer=offer)
        self._discounts.append(DiscountApplication(amount, quantity, incl_tax, offer))
        self.consume(quantity, offer=offer)
        if incl_tax:
            self._discount_incl_tax = None
        else:
            self._discount_excl_tax = None

    @property
    def excl_tax(self):
        if self._discount_excl_tax is None:
            self._discount_excl_tax = sum(
                [d.amount for d in self._discounts if not d.incl_tax],
                ZERO,
            )
        return self._discount_excl_tax

    @property
    def incl_tax(self):
        if self._discount_incl_tax is None:
            self._discount_incl_tax = sum(
                [d.amount for d in self._discounts if d.incl_tax],
                ZERO,
            )
        return self._discount_incl_tax

    @property
    def total(self):
        return sum([d.amount for d in self._discounts], ZERO)

    def all(self):
        return self._discounts

    def __iter__(self):
        return iter(self._discounts)
