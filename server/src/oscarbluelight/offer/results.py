from oscar.apps.offer import results
from collections import OrderedDict

BaseOfferApplications = results.OfferApplications


class OfferApplications(BaseOfferApplications):
    def __init__(self):
        # Make applications an OrderedDict so we remember the order in which discount
        # applications occurred.
        self.applications = OrderedDict()

    def add(self, offer, result):
        super().add(offer, result)
        self.applications[offer.id]["is_hidden"] = getattr(result, "is_hidden", False)
        # Add the discount index (application order) as a key. Useful for merging the
        # basket.voucher_discounts and basket.offer_discounts lists together for display
        # in the correct order.
        self.applications[offer.id]["index"] = list(self.applications.keys()).index(
            offer.id
        )

    @property
    def offer_post_order_actions(self):
        """
        Return successful offer applications which didn't lead to a discount
        """
        return [
            application
            for application in self.post_order_actions
            if not application["voucher"]
        ]

    @property
    def voucher_post_order_actions(self):
        """
        Return successful voucher applications which didn't lead to a discount
        """
        return [
            application
            for application in self.post_order_actions
            if application["voucher"]
        ]


class BasketDiscount(results.BasketDiscount):
    is_hidden = False


class ShippingDiscount(results.ShippingDiscount):
    is_hidden = False


class PostOrderAction(results.PostOrderAction):
    is_hidden = False


class HiddenPostOrderAction(results.PostOrderAction):
    """
    Just like a normal PostOrderAction, but it's hidden from the user interface.
    """

    is_hidden = True


# Have to monkey patch this in since Oscar, for some reason, doesn't use get_class for this class
results.OfferApplications = OfferApplications
