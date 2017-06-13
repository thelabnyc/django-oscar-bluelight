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
        # Add the discount index (application order) as a key. Useful for merging the
        # basket.voucher_discounts and basket.offer_discounts lists together for display
        # in the correct order.
        self.applications[offer.id]['index'] = list(self.applications.keys()).index(offer.id)


# Have to monkey patch this in since Oscar, for some reason, doesn't use get_class for this class
results.OfferApplications = OfferApplications
