from collections import defaultdict


class BluelightLineOfferConsumer(object):
    """
    Version of ``oscar.app.basket.utils.LineOfferConsumer`` which supports OfferGroups.
    """
    def __init__(self, line):
        self.__line = line
        self.__offers = dict()
        self.__affected_quantity = 0
        self.__consumptions = defaultdict(int)

        # The built-in __affected_quantity property simply tracks how many items in the line aren't available
        # for use by offers. This property tracks what subset of that number was actually discounted (versus
        # just marked as unavailable for discount)
        self.__discounted_quantity = 0

        # The built-in __affected_quantity property refers to affected quantity within an offer group.
        # This property refers to the affected quantity global of OfferGroups
        self.__global_affected_quantity = 0


    def __cache(self, offer):
        self.__offers[offer.pk] = offer


    def __update_affected_quantity(self, quantity):
        available_in_group = int(self.__line.quantity - self.__affected_quantity)
        available_global = int(self.__line.quantity - self.__global_affected_quantity)
        self.__affected_quantity += min(available_in_group, quantity)
        self.__global_affected_quantity += min(available_global, quantity)


    def consume(self, quantity, offer=None):
        """
        Mark a basket line as consumed by an offer in the current offer group.

        If offer is None, the specified quantity of items on this basket line is consumed for *any*
        offer, else only for the specified offer.
        """
        self.__update_affected_quantity(quantity)
        if offer:
            self.__cache(offer)
            available = self.available(offer)
            self.__consumptions[offer.pk] += min(available, quantity)


    def consumed(self, offer=None):
        """
        Check how many items on this line have been consumed by an offer in the current offer group.

        If offer is not None, only the number of items marked with the specified ConditionalOffer are returned.
        """
        if not offer:
            return self.__affected_quantity
        return int(self.__consumptions[offer.pk])


    def available(self, offer=None):
        """
        Check how many items are available for offers
        """
        if offer:
            exclusive = any([x.exclusive for x in self.__offers.values()])
            exclusive |= bool(offer.exclusive)
        else:
            exclusive = True

        if exclusive:
            offer = None

        consumed = self.consumed(offer)
        return int(self.__line.quantity - consumed)


    def discount(self, quantity):
        """
        Update the discounted quantity.
        """
        self.__discounted_quantity += quantity


    def discounted(self):
        """
        Get the number of items that have been discounted in the current offer group.
        """
        return self.__discounted_quantity


    def begin_offer_group_application(self):
        """
        Signal that the Applicator will begin to apply a new group of offers.

        Since line consumption is name-spaced within each offer group, we reset the ``_affected_quantity`` property
        to 0. This allows offers to re-consume lines already consumed by previous offer groups while still calculating
        their discount amounts correctly.
        """
        self.__affected_quantity = 0
        self.__discounted_quantity = 0


    def end_offer_group_application(self):
        """
        Signal that the Applicator has finished applying a group of offers.
        """
        self.__discounted_quantity = 0


    def finalize_offer_group_applications(self):
        """
        Signal that all offer groups (and therefore all offers) have now been applied.
        """
        self.__affected_quantity = min(self.__line.quantity, self.__global_affected_quantity)
